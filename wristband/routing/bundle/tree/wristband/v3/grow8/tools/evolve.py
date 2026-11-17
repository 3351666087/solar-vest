"""[grow G-3 -> grow8 Q-6] Evolutionary search around the engine (evaluate.py), 8 layers with the Q-2 / Q-3 / Q-4 rules.

[grow8] Every candidate is evaluated in placement mode with RULES8 (8 layers, P-1 forbidden nets, neck 1.5 mm, In2 / In3 shielded,
the Q-4 fan-out) unless --rules overrides it. Q-4 escape halo: around the pad rings of U7, U1, U6, U15, U17 a square halo of HALO mm
(a gene, inherited and mutated in [0.3, 1.2]); only the IC's own decoupling capacitors may sit in it. Parts intruding into a halo get
extra selection weight and are pushed away from the IC; a move that increases the total halo intrusion is rejected like an illegal one.
Results rows carry halo and halo_intrusion_mm2.

  venv-python evolve.py RUNDIR [--pop 8] [--gens 3] [--workers N] [--elite 3] [--budget-h 5] [--base PLACEMENT.json] [--seed 1]
                               [--iters 60] [--smoke]

Candidate = placement (base placement + accumulated local part moves) + router weights + net-order policy.
Every generation evaluates POP new candidates in parallel (WORKERS processes, one core each; default cores - 2).
Generation 0: the base candidate (s2 weights) + POP-1 mutants of it. Later generations: children of the ELITE best evaluated so far.
Mutation: weight jitter and / or moves of 1-4 movable parts (placement 'anchor' parts never move) out of the parent's congestion
(unconnected endpoints of its final DRC + its routed copper density), then local re-legalisation: the layout lane's checker
(check_placement.py) must say LEGAL, otherwise nearby offsets / shorter moves are tried and the move is dropped if none is legal.
Results: RUNDIR/results.jsonl (one line per evaluation, appended), RUNDIR/curve.json, RUNDIR/best/ (best board so far).
Resume: run the same command again; logged evaluations are kept, finished but unlogged ones are ingested, the rest re-run
(children are rebuilt deterministically from the log and the seed). Stop: kill the process; at most the running generation is lost.
Success = 0 unconnected, 0 DRC errors, 0 placement violations (and 0 forbidden plate vias): the search stops.
"""
import argparse, json, math, os, random, shutil, subprocess, sys, time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
GROW = os.path.dirname(HERE)
V3 = os.path.dirname(GROW)
P1 = ["NTC", "NTC_ADC", "I2C_SDA", "I2C_SCL", "O2_TC", "O2_TH"]
RULES8 = dict(layers=8, forbidden_add=P1, neck=1.5, shield=["In2.Cu", "In3.Cu"])     # [grow8] Q-1 / P-1 / Q-2 / Q-3 (Q-4 fan-out is built in)
HALO_ICS = ["U7", "U1", "U6", "U15", "U17"]
HALO0, HALO_RANGE, HALO_W = 0.8, (0.4, 1.4), 4.0
PY = os.environ.get("GROW_PY", sys.executable)
ENV_PL = dict(G1_ZFILE=V3 + "/track2/work/board_zones_t2_layout.json", G1_NO_ISLAND="1", G1_VARIANT="v3f",
              G1_OPTS="gap=dru,jlc=full,ufpc", G1_ZONES="L41W34_fold1p9_fpcdwg_jointzif_raise0p15", G1_CRIT_W="200")
KO = (100.0, 130.0)          # board (0,0) in KiCad page coordinates, KiCad Y down (lgeom.KICAD_ORIGIN)
S2 = dict(iters=60, pres0=0.3, pres_mult=1.2, hist_inc=2.0, hw=1.2, via_cost_mm=1.2, l4_cost=3.0, conn_margin=3.0)
RANGE = dict(pres0=(0.12, 1.2), pres_mult=(1.08, 1.4), hist_inc=(0.8, 8.0), hw=(1.0, 1.45), via_cost_mm=(0.7, 2.0),
             l4_cost=(1.8, 5.0), conn_margin=(2.0, 6.0))
ORDERS = ["short", "long", "pins", "random"]
try:
    _PJ = json.load(open(V3 + "/design/parts.json"))["variants"]["v3f"]["parts"]
    FP = {r: q["footprint"] for r, q in _PJ.items()}
except Exception:
    _PJ, FP = {}, {}
try:
    FPG = json.load(open(V3 + "/layout/work/fpgeom_v3f.json"))
except Exception:
    FPG = {}


# ------------------------------------------------------------------------------------------------ [grow8 Q-4] escape halo
def _nets(ref):
    return {n for n in (_PJ.get(ref, {}).get("pins") or {}).values() if n and n != "GND" and not n.startswith("NC")}


CAPN = {r: _nets(r) for r in _PJ if r.startswith("C")}


def own_decoupling(parts):
    """capacitor C* is own decoupling of IC X when it shares a non-GND net with X and X is the nearest HALO_IC sharing one."""
    own = {ic: set() for ic in HALO_ICS}
    icn = {ic: _nets(ic) for ic in HALO_ICS if ic in parts}
    for c, cn in CAPN.items():
        if c not in parts:
            continue
        sh = [ic for ic in icn if icn[ic] & cn]
        if sh:
            ic = min(sh, key=lambda k: math.dist((parts[k]["x"], parts[k]["y"]), (parts[c]["x"], parts[c]["y"])))
            own[ic].add(c)
    return own


def _box(ref, q, grow=0.0):
    g = FPG.get(ref)
    if not g:
        return None
    x0, y0, x1, y1 = g["crt"]
    if int(round(q.get("rot", 0) / 90.0)) % 2:
        x0, y0, x1, y1 = y0, x0, y1, x1
    hx, hy = max(abs(x0), abs(x1)), max(abs(y0), abs(y1))
    return (q["x"] - hx - grow, q["y"] - hy - grow, q["x"] + hx + grow, q["y"] + hy + grow)


def _ring(ref):
    g = FPG.get(ref) or {}
    return max([max(abs(p["x"]) + p["w"] / 2, abs(p["y"]) + p["h"] / 2) for p in g.get("pads", [])] or [1.0])


def halo_intrusion(parts, halo):
    """per part: overlap area (mm2) of its courtyard box with the halo boxes (pad ring + halo) of the HALO_ICS, own decoupling exempt."""
    res = {}
    OWN = own_decoupling(parts)
    for ic in HALO_ICS:
        if ic not in parts:
            continue
        q = parts[ic]; r = _ring(ic) + halo
        hb = (q["x"] - r, q["y"] - r, q["x"] + r, q["y"] + r)
        for ref, o in parts.items():
            if ref == ic or ref in OWN[ic] or o.get("side") != q.get("side"):
                continue
            b = _box(ref, o)
            if not b:
                continue
            ov = max(0.0, min(b[2], hb[2]) - max(b[0], hb[0])) * max(0.0, min(b[3], hb[3]) - max(b[1], hb[1]))
            if ov > 1e-6:
                res[ref] = res.get(ref, 0.0) + ov
    return res


def halo_center(parts, ref):
    best = None
    for ic in HALO_ICS:
        if ic in parts and ref != ic:
            d = math.dist((parts[ic]["x"], parts[ic]["y"]), (parts[ref]["x"], parts[ref]["y"]))
            if best is None or d < best[0]:
                best = (d, parts[ic]["x"], parts[ic]["y"])
    return best


# ------------------------------------------------------------------------------------------------ placement legality
def check(pl_path, tag):
    r = subprocess.run([PY, "-B", HERE + "/check_placement.py", pl_path, tag + ".chk.json"], capture_output=True, text=True,
                       env=dict(os.environ, **ENV_PL))
    line = ([l for l in r.stdout.splitlines() if "LEGAL" in l] or ["?"])[0]
    return line.startswith("LEGAL")


def congestion(parent_dir):
    """points (board mm, weight): unconnected endpoints (weight 1) + routed copper samples (weight 0.02 per 0.1 mm)."""
    pts = []
    try:
        d = json.load(open(parent_dir + "/drc_final.json"))
        for u in d.get("unconnected_items", []):
            for it in u["items"]:
                pts.append((it["pos"]["x"] - KO[0], KO[1] - it["pos"]["y"], 1.0))
    except Exception:
        pass
    try:
        R = json.load(open(parent_dir + "/routes.json"))
        for r in R["routes"]:
            for s in r["segs"]:
                L = math.dist(s["a"], s["b"]); n = max(1, int(L / 0.1))
                for k in range(n):
                    t = (k + 0.5) / n
                    pts.append((s["a"][0] + t * (s["b"][0] - s["a"][0]) - KO[0], KO[1] - (s["a"][1] + t * (s["b"][1] - s["a"][1])), 0.02 * L / n / 0.1))
    except Exception:
        pass
    return pts


def mutate_placement(parent_pl, parent_dir, spec, out_pl):
    """spec: dict(nmove, seed, halo). Writes out_pl; returns the list of applied moves."""
    rng = random.Random(spec["seed"])
    pl = json.load(open(parent_pl)); parts = pl["parts"]
    mov = [r for r, q in parts.items() if not q.get("anchor")]
    halo = spec.get("halo", HALO0)
    intr = halo_intrusion(parts, halo)
    pts = congestion(parent_dir)
    hot = [(x, y, w) for x, y, w in pts if w >= 1.0] or pts
    score = {}
    for r in mov:
        q = parts[r]; s = 0.0
        for x, y, w in pts:
            d2 = (q["x"] - x) ** 2 + (q["y"] - y) ** 2
            if d2 < 9.0:
                s += w * math.exp(-d2 / (2 * 1.2 ** 2))
        score[r] = s + HALO_W * intr.get(r, 0.0)          # [grow8 Q-4] halo intruders first
    cand = sorted(mov, key=lambda r: -score[r])[:14]
    applied = []
    tag = out_pl[:-5]
    json.dump(pl, open(out_pl, "w"), indent=1)
    for _ in range(spec["nmove"]):
        if not cand:
            break
        wts = [score[r] + 1e-3 for r in cand]
        ref = rng.choices(cand, weights=wts)[0]; cand.remove(ref)
        q = parts[ref]
        # direction: away from the weighted centroid of the hot points around the part (or random, p 0.3)
        sx = sy = sw = 0.0
        for x, y, w in hot:
            d2 = (q["x"] - x) ** 2 + (q["y"] - y) ** 2
            if d2 < 9.0:
                g = w * math.exp(-d2 / 2.0); sx += g * x; sy += g * y; sw += g
        hc = halo_center(parts, ref)
        if intr.get(ref) and hc and rng.random() < 0.7:          # [grow8 Q-4] out of the halo, away from the IC
            ang = math.atan2(q["y"] - hc[2], q["x"] - hc[1]) + rng.gauss(0, 0.3)
        elif sw > 0 and rng.random() > 0.3:
            ang = math.atan2(q["y"] - sy / sw, q["x"] - sx / sw) + rng.gauss(0, 0.5)
        else:
            ang = rng.uniform(0, 2 * math.pi)
        x0, y0, r0 = q["x"], q["y"], q.get("rot", 0)
        ok = None
        # (a) swap with a movable part of the same footprint and side within 4 mm (p 0.35)
        if rng.random() < 0.35:
            fp = FP.get(ref)
            mates = [m for m in mov if m != ref and FP.get(m) == fp and parts[m]["side"] == q["side"]
                     and (parts[m]["x"] - x0) ** 2 + (parts[m]["y"] - y0) ** 2 < 16.0]
            rng.shuffle(mates)
            for m in mates[:4]:
                o = parts[m]; ox, oy, orot = o["x"], o["y"], o.get("rot", 0)
                q["x"], q["y"], q["rot"], o["x"], o["y"], o["rot"] = ox, oy, orot, x0, y0, r0
                json.dump(pl, open(out_pl, "w"), indent=1)
                if sum(halo_intrusion(parts, halo).values()) <= sum(intr.values()) + 1e-6 and check(out_pl, tag):
                    ok = ("swap", ref, m); break
                q["x"], q["y"], q["rot"], o["x"], o["y"], o["rot"] = x0, y0, r0, ox, oy, orot
        # (b) translation (and sometimes a rotation): up to 24 legal-checked targets, far and on-direction first
        if not ok:
            u = rng.random()
            drot = 180 if u < 0.12 else (rng.choice((90, 270)) if u < 0.18 else 0)
            dmax = rng.uniform(0.3, 0.9)
            tries = []
            for f in (1.0, 0.65, 0.4, 0.2):
                for da in (0.0, 0.5, -0.5, 1.0, -1.0, 1.6):
                    tries.append((x0 + f * dmax * math.cos(ang + da), y0 + f * dmax * math.sin(ang + da)))
            rots = (drot, 0) if drot else (0,)
            n = 0
            for dr in rots:
                for tx, ty in tries:
                    n += 1
                    if n > 24:
                        break
                    q["x"], q["y"], q["rot"] = round(tx, 3), round(ty, 3), (r0 + dr) % 360
                    json.dump(pl, open(out_pl, "w"), indent=1)
                    if sum(halo_intrusion(parts, halo).values()) <= sum(intr.values()) + 1e-6 and check(out_pl, tag):
                        ok = (ref, round(q["x"] - x0, 3), round(q["y"] - y0, 3), (q["rot"] - r0) % 360); break
                if ok:
                    break
        if ok:
            applied.append(ok); intr = halo_intrusion(parts, halo)
        else:
            q["x"], q["y"], q["rot"] = x0, y0, r0
            json.dump(pl, open(out_pl, "w"), indent=1)
    pl.pop("violations", None)
    json.dump(pl, open(out_pl, "w"), indent=1)
    for f in (tag + ".chk.json",):
        if os.path.exists(f):
            os.remove(f)
    return applied


def jitter(rprm, order, ojit, rng, strength):
    r = dict(rprm)
    for k, (lo, hi) in RANGE.items():
        if rng.random() < 0.5 * strength + 0.2:
            v = r.get(k, S2[k])
            v = v * math.exp(rng.gauss(0, 0.25 * strength)) if k != "pres_mult" else 1 + (v - 1) * math.exp(rng.gauss(0, 0.3 * strength))
            r[k] = round(min(hi, max(lo, v)), 4)
    if rng.random() < 0.2:
        order = rng.choice(ORDERS)
    if rng.random() < 0.3:
        ojit = round(rng.choice((0.0, 1.0, 2.0, 4.0)), 1)
    return r, order, ojit


def mut_halo(h, rng, strength):
    if rng.random() < 0.4 * strength:
        h = h * math.exp(rng.gauss(0, 0.25 * strength))
    return round(min(HALO_RANGE[1], max(HALO_RANGE[0], h)), 3)


# ------------------------------------------------------------------------------------------------ one evaluation (worker)
def work(job):
    cdir = job["dir"]; ev = cdir + "/eval"
    os.makedirs(cdir, exist_ok=True)
    t0 = time.time()
    if not os.path.exists(cdir + "/candidate.json"):
        moves = []
        if job["nmove"] > 0:
            moves = mutate_placement(job["parent_pl"], job["parent_dir"], dict(nmove=job["nmove"], seed=job["seed"], halo=job["halo"]),
                                     cdir + "/placement.json")
        else:
            shutil.copy(job["parent_pl"], cdir + "/placement.json")
        cand = dict(placement=cdir + "/placement.json", router=job["router"], order=job["order"], seed=job["seed"] % 100000 + 1,
                    halo=job["halo"], **job["rules"])
        if job.get("order_jitter"):
            cand["router"] = dict(cand["router"], order_jitter=job["order_jitter"])
        json.dump(dict(moves=moves), open(cdir + "/moves.json", "w"))
        json.dump(cand, open(cdir + "/candidate.json", "w"), indent=1)
    t_mut = time.time() - t0
    if not os.path.exists(ev + "/score.json"):
        if os.path.exists(ev):
            shutil.rmtree(ev)
        with open(cdir + "/evaluate.out", "w") as fo:
            try:
                subprocess.run([PY, "-B", HERE + "/evaluate.py", cdir + "/candidate.json", ev], stdout=fo, stderr=subprocess.STDOUT,
                               timeout=job.get("timeout", 7200))
            except subprocess.TimeoutExpired:
                fo.write("TIMEOUT\n")
    return dict(id=job["id"], t_mut=round(t_mut, 1))


def summarize(job, res):
    cdir = job["dir"]; ev = cdir + "/eval"
    cand = json.load(open(cdir + "/candidate.json")); moves = json.load(open(cdir + "/moves.json"))["moves"]
    row = dict(id=job["id"], gen=job["gen"], parent=job["parent"], nmove_req=job["nmove"], moves=moves, router=cand["router"],
               order=cand["order"], seed=cand["seed"], dir=os.path.relpath(cdir, job["rd"]), t_mut_s=res.get("t_mut"), time=time.strftime("%Y-%m-%d %H:%M:%S"),
               halo=cand.get("halo"))
    try:
        row["halo_intrusion_mm2"] = round(sum(halo_intrusion(json.load(open(cdir + "/placement.json"))["parts"], cand.get("halo", HALO0)).values()), 3)
    except Exception:
        pass
    try:
        s = json.load(open(ev + "/score.json"))
        row.update(fitness=s["fitness"], unconnected=s["unconnected"], drc_errors=s["drc_errors"], placement_violations=s["placement_violations"],
                   forbidden_vias_over_plates=s["forbidden_vias_over_plates"], overused=s["overused_cells_final"], vias=s["vias"],
                   track_mm=s["track_mm_total"], vias_over_plates_total=s["vias_over_plates_total"], runtime_s=s["runtime_s"]["total"],
                   route_s=s["runtime_s"].get("route"), unconnected_before_strip=s["unconnected_before_strip"], shield=s.get("shield"),
                   neck_mm_total=s.get("neck_mm_total"), peak_rss_mb=s.get("peak_rss_mb"))
    except Exception as e:
        row.update(fitness=1e9, error=str(e)[:200])
    if job.get("slim"):                       # keep final board, routes, DRC, score; drop the intermediate boards
        for f in ("fan.kicad_pcb", "routed.kicad_pcb", "dump.json", "drc_fan.json", "v3f_g1_fan.kicad_pcb", "v3f_g1.kicad_pcb"):
            if os.path.exists(ev + "/" + f):
                os.remove(ev + "/" + f)
        shutil.rmtree(ev + "/tmp", ignore_errors=True)
    return row


def key(r):
    return (r["fitness"], r.get("overused") or 1e9)


def success(r):
    return r["fitness"] < 1e9 and r["unconnected"] == 0 and r["drc_errors"] == 0 and (r["placement_violations"] or 0) == 0 and \
        r["forbidden_vias_over_plates"] == 0


# ------------------------------------------------------------------------------------------------ driver
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rundir"); ap.add_argument("--pop", type=int, default=8); ap.add_argument("--gens", type=int, default=3)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2)); ap.add_argument("--elite", type=int, default=0,
                    help="parents kept per generation (default max(3, pop // 8))")
    ap.add_argument("--slim", action="store_true", help="delete intermediate boards of every evaluation (about 5 MB left each)")
    ap.add_argument("--budget-h", type=float, default=1e9); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--base", default=GROW + "/work/b0_src/placement.json"); ap.add_argument("--iters", type=int, default=60)
    ap.add_argument("--base-eval", default=GROW + "/runs/a8", help="evaluation folder whose DRC / routes give the gen-0 congestion")
    ap.add_argument("--rules", default=None, help="JSON object of candidate rule keys (default RULES8)")
    ap.add_argument("--timeout", type=int, default=7200, help="seconds per evaluation")
    ap.add_argument("--seed-dir", default=None, help="start from an earlier best: folder with placement.json, candidate.json, drc_final.json, routes.json")
    ap.add_argument("--smoke", action="store_true", help="2 router iterations, for a quick install test")
    a = ap.parse_args()
    a.elite = a.elite or max(3, a.pop // 8)
    rd = os.path.abspath(a.rundir); os.makedirs(rd, exist_ok=True)
    logf = rd + "/results.jsonl"
    rows = [json.loads(l) for l in open(logf)] if os.path.exists(logf) else []
    done = {r["id"] for r in rows}
    cfg = dict(pop=a.pop, gens=a.gens, workers=a.workers, elite=a.elite, seed=a.seed, base=os.path.abspath(a.base), iters=2 if a.smoke else a.iters,
               base_router=dict(S2), base_order="short", base_ojit=0.0, base_eval=os.path.abspath(a.base_eval),
               rules=json.loads(a.rules) if a.rules else dict(RULES8), base_halo=HALO0, timeout=a.timeout)
    if a.seed_dir:
        sd = os.path.abspath(a.seed_dir); sc = json.load(open(sd + "/candidate.json"))
        cfg.update(base=sd + "/placement.json", base_eval=sd, base_order=sc.get("order", "short"))
        cfg["base_router"] = dict(S2, **sc.get("router", {})); cfg["base_ojit"] = cfg["base_router"].pop("order_jitter", 0.0)
        cfg["base_halo"] = sc.get("halo", HALO0)
    if os.path.exists(rd + "/config.json"):
        old = json.load(open(rd + "/config.json"))
        for k in ("base", "seed", "iters", "base_router", "base_order", "base_ojit", "base_eval", "rules", "base_halo"):
            if k in old:
                cfg[k] = old[k]      # a resume keeps the run's base, seed and iterations
    json.dump(cfg, open(rd + "/config.json", "w"), indent=1)
    T0 = time.time(); t_gen = []
    print("evolve: %s pop %d gens %d workers %d (logged %d)" % (rd, a.pop, a.gens, a.workers, len(rows)), flush=True)
    for g in range(a.gens):
        if any(success(r) for r in rows if r["gen"] < g):
            break
        jobs = []
        rng = random.Random(cfg["seed"] * 7919 + g)
        prev = sorted([r for r in rows if r["gen"] < g and r["fitness"] < 1e9], key=key)
        for i in range(a.pop):
            cid = "g%02d_c%02d" % (g, i)
            seed = cfg["seed"] * 100003 + g * 1009 + i * 31
            job = dict(id=cid, gen=g, dir=rd + "/gen%02d/%s" % (g, cid), seed=seed, rd=rd, slim=a.slim, rules=cfg["rules"],
                       timeout=cfg.get("timeout", 7200))
            r1 = random.Random(seed)
            if g == 0 or not prev:
                pr = dict(cfg["base_router"], iters=cfg["iters"]); po, poj = cfg["base_order"], cfg["base_ojit"]
                job.update(parent="base", parent_pl=cfg["base"], parent_dir=cfg["base_eval"])
                if i == 0:
                    job.update(router=pr, order=po, order_jitter=poj, nmove=0, halo=cfg["base_halo"])
                else:
                    kind = i % 3          # 0: both, 1: weights only, 2: moves only
                    rr, oo, oj = jitter(pr, po, poj, r1, 1.0) if kind in (0, 1) else (pr, po, poj)
                    job.update(router=rr, order=oo, order_jitter=oj, nmove=0 if kind == 1 else r1.randint(1, 4),
                               halo=mut_halo(cfg["base_halo"], r1, 1.0))
            else:
                el = prev[:a.elite]
                wts = [0.5, 0.3, 0.2] if len(el) == 3 else [1.0 / (k + 1) for k in range(len(el))]
                p = r1.choices(el, weights=wts[:len(el)])[0]
                pdir = os.path.join(rd, p["dir"])
                pc = json.load(open(pdir + "/candidate.json"))
                pr = dict(pc["router"], iters=cfg["iters"]); poj = pr.pop("order_jitter", 0.0)
                u = r1.random()
                kind = 1 if u < 0.3 else (2 if u < 0.65 else 0)
                rr, oo, oj = jitter(pr, pc["order"], poj, r1, 0.7) if kind in (0, 1) else (pr, pc["order"], poj)
                job.update(parent=p["id"], parent_pl=pdir + "/placement.json", parent_dir=pdir + "/eval", router=rr, order=oo,
                           order_jitter=oj, nmove=0 if kind == 1 else r1.randint(1, 4), halo=mut_halo(pc.get("halo", HALO0), r1, 0.7))
            jobs.append(job)
        todo = [j for j in jobs if j["id"] not in done]
        if todo:
            if time.time() - T0 + (max(t_gen) if t_gen else 0) > a.budget_h * 3600:
                print("evolve: budget reached before generation %d" % g, flush=True); break
            tg = time.time()
            with Pool(min(a.workers, len(todo))) as pool:
                for res in pool.imap_unordered(work, todo):
                    j = next(x for x in todo if x["id"] == res["id"])
                    row = summarize(j, res); rows.append(row); done.add(row["id"])
                    with open(logf, "a") as fh:
                        fh.write(json.dumps(row) + "\n")
                    print("  %s parent %s fitness %s (unc %s, drc %s, pviol %s) moves %d %s" % (row["id"], row["parent"], row["fitness"],
                          row.get("unconnected"), row.get("drc_errors"), row.get("placement_violations"), len(row["moves"]),
                          row.get("error", "")), flush=True)
            t_gen.append(time.time() - tg)
        # curve + best
        curve = []
        for gg in range(g + 1):
            gr = [r for r in rows if r["gen"] == gg and r["fitness"] < 1e9]
            sofar = [r for r in rows if r["gen"] <= gg and r["fitness"] < 1e9]
            if gr:
                b = min(gr, key=key); bs = min(sofar, key=key)
                curve.append(dict(gen=gg, best_gen=b["fitness"], best_gen_id=b["id"], best_gen_unconnected=b["unconnected"],
                                  best_gen_drc=b["drc_errors"], median_gen=sorted(r["fitness"] for r in gr)[len(gr) // 2],
                                  best_so_far=bs["fitness"], best_so_far_id=bs["id"], n=len(gr)))
        json.dump(dict(curve=curve, gen_wall_s=[round(t) for t in t_gen]), open(rd + "/curve.json", "w"), indent=1)
        best = min([r for r in rows if r["fitness"] < 1e9], key=key, default=None)
        if best:
            bdir = os.path.join(rd, best["dir"]); bd = rd + "/best"
            if not os.path.exists(bd + "/id") or open(bd + "/id").read() != best["id"]:
                shutil.rmtree(bd, ignore_errors=True); os.makedirs(bd)
                for f in os.listdir(bdir + "/eval"):
                    if f.startswith("final.") or f in ("score.json", "drc_final.json", "routes.json"):
                        shutil.copy(bdir + "/eval/" + f, bd + "/" + f)
                shutil.copy(bdir + "/candidate.json", bd + "/candidate.json"); shutil.copy(bdir + "/placement.json", bd + "/placement.json")
                open(bd + "/id", "w").write(best["id"])
            print("gen %d done: best of gen %s, best so far %s (%s) | %.0f s" % (g, curve[-1]["best_gen"] if curve else "-", best["fitness"],
                  best["id"], t_gen[-1] if t_gen else 0), flush=True)
            if success(best):
                print("SUCCESS %s" % best["id"], flush=True); break


if __name__ == "__main__":
    main()
