"""[eco3] Move U19 / U20 (now SC70-5, 1.10 mm + solder) the minimum needed to a legal spot.
Geometric pre-filter (allowed zone as check_placement.allowed(), courtyard gaps P.pair_gap), candidates sorted by displacement,
each verified by check_placement.py (LEGAL and critical pairs 0). Both orders (U19 first / U20 first) are tried; the smaller total move wins.
usage: venv-python eco3_find.py IN_placement.json OUT_placement.json"""
import json, math, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from shapely.geometry import box
from shapely.ops import unary_union
from shapely.prepared import prep
import lgeom as G
import place_main as P
from autoplace import load

inp, outp = sys.argv[1:3]
SRC = json.load(open(inp))
parts, obj, nets = load()
Z, ZP = G.ZONES, G.ZP
zero = {n: ZP[n] for n, z in Z.items() if z["kind"] in G.ZERO_KINDS}
zero_u = unary_union(list(zero.values())); zero_ufpc = unary_union([p for n, p in zero.items() if n not in G.FPC_RUN])
hl = {n: (float(z["h_max_mm"]), ZP[n]) for n, z in Z.items() if z["kind"] == "height_limit"}
cadland = unary_union([ZP[n] for n, z in Z.items() if z["kind"] in ("part", "land")]) if G.CADLANDS else None


def allowed(o):
    a = G.INNER.difference(zero_ufpc if o.ref in P.UFPC_REFS else zero_u)
    if cadland is not None: a = a.difference(cadland)
    low = [p for (h, p) in hl.values() if h < o.need - 1e-9]
    if low: a = a.difference(unary_union(low))
    if o.need > G.H_GENERAL + 1e-9:
        hi = [p for (h, p) in hl.values() if h >= o.need - 1e-9 and h > G.H_GENERAL]
        a = a.intersection(unary_union(hi)) if hi else box(0, 0, 0, 0)
    return a


def check(pl, ignore=None):
    tmp = outp + ".tmp.json"; json.dump(pl, open(tmp, "w"), indent=1)
    r = subprocess.run([sys.executable, "-B", HERE + "/check_placement.py", tmp, outp + ".chk.json"], capture_output=True, text=True)
    line = ([l for l in r.stdout.splitlines() if "LEGAL" in l] or ["?"])[0]
    if ignore is None: return line.startswith("LEGAL") and "critical-pair 0 " in line, line
    h = json.load(open(outp + ".chk.json"))["hard"]          # stage 1: violations of the part not yet moved do not count
    left = [(k, it) for k, v in h.items() for it in (v.items() if isinstance(v, dict) else v) if ignore not in json.dumps(it)]
    return not left, line + " | ignoring " + ignore


def place_one(pl, ref, step=0.05, maxn=400, ignore=None):
    o = obj[ref]; x0, y0 = SRC["parts"][ref]["x"], SRC["parts"][ref]["y"]
    for r, q in pl["parts"].items():
        if r in obj: obj[r].x, obj[r].y, obj[r].r = q["x"], q["y"], q["rot"]
    al = prep(allowed(o))
    others = [r for r in obj if r != ref and obj[r].side == "F" and r in pl["parts"] and not (ignore and r == ignore)]
    cands = []
    for rot in (0, 90, 180, 270):
        blk = prep(unary_union([box(*obj[r].crt(gap=2 * P.pair_gap(ref, r, mode="full"))) for r in others]))
        for i in range(0, 801):
            for j in range(0, 681):
                x, y = i * step, j * step
                d = math.hypot(x - x0, y - y0)
                if d > 25: continue
                b = box(*o.cl(x, y, rot))
                if not al.contains(b): continue
                if blk.intersects(b): continue
                cands.append((round(d, 3), x, y, rot))
    cands.sort(); print(ref, "geometric candidates", len(cands), flush=True)
    for k, (d, x, y, rot) in enumerate(cands[:maxn]):
        t = json.loads(json.dumps(pl)); t["parts"][ref].update(x=round(x, 3), y=round(y, 3), rot=rot)
        ok, line = check(t, ignore)
        if ok: print("ACCEPT", ref, x, y, rot, "move", d, "| tried", k + 1, "|", line, flush=True); return t, d
    return None, None


best = None
for order in (("U19", "U20"), ("U20", "U19")):
    pl = json.loads(json.dumps(SRC))
    t1, d1 = place_one(pl, order[0], ignore=order[1])
    if t1 is None: continue
    t2, d2 = place_one(t1, order[1])
    if t2 is None: continue
    print("order", order, "total move", round(d1 + d2, 3))
    if best is None or d1 + d2 < best[0]: best = (d1 + d2, order, t2)
if best is None: raise SystemExit("no legal spot")
best[2]["eco3"] = dict(from_placement=inp, moved={r: dict(old=SRC["parts"][r], new=best[2]["parts"][r]) for r in ("U19", "U20")},
                       total_move_mm=round(best[0], 3), order=list(best[1]), note="U19 / U20 SC70-5 C2863637 (need 1.15 mm: PV half 1.20 only)")
json.dump(best[2], open(outp, "w"), indent=1); print("WROTE", outp, "order", best[1], "total", round(best[0], 3))
print(check(best[2])[1])
