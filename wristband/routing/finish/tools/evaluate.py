"""[grow G-2] Evaluate one candidate headless: (placement) -> plane fan-out -> PathFinder routing -> KiCad DRC -> score.json.

  venv-python evaluate.py CANDIDATE.json OUTDIR

Candidate file (JSON; every key optional except one board source):
  "board":      fanned board .kicad_pcb (its folder holds geom.json, plate_forbidden_nets.json, chk.json)   -- start from it, or
  "placement":  placement .json (+ "moves": [[ref, dx_mm, dy_mm, drot_deg], ...])  -- legal check, build, plane fan-out, or
  "place_seed": integer -- full placement chain of the layout lane (autoplace, legalise, refine x2, nudge) with that seed
  "router":     parameters of pfroute.DEF (iters, pres0, pres_mult, hist_inc, hw, via_cost_mm, l4_cost, conn_margin, net_margin, ...)
  "order":      net-order policy "short" | "long" | "pins" | "random" | [net names first]
  "seed":       integer (order "random" and order_jitter)
  "strip":      true (default) -> remove the copper named by DRC errors (errors-only strip) and re-check
  "layers":     6 (default) | 8  -- [grow8 G-6] 8: the fanned 6-layer board is converted by to8l.py (plan B stack, v3/planb); a board
                that already has 8 copper layers is used as it is. The router follows the board's layer count (dump "nl").
  "forbidden_add": [net, ...]  -- [grow8 P-1] nets added to plate_forbidden_nets.json and to the DRU R-2 rules before routing
  "neck":       1.5  -- [grow8 Q-2] neck-down at pads: rule areas + DRU rules (neck_areas.py), router neck radius = neck - 0.1 mm
  "shield":     ["In2.Cu", "In3.Cu"]  -- [grow8 Q-3] plate-forbidden nets may run on these layers over the plates (router + DRU);
                the In4 plane under them is checked (shield_check.py -> shield.json, score "shield")
  "fanout":     {...}  -- [grow8 Q-4] options of fanout_planes.py (env FANOUT_OPTS, JSON), placement modes only
Writes OUTDIR/score.json, OUTDIR/final.kicad_pcb (+ .kicad_pro/.kicad_dru), logs. Everything lives in OUTDIR (own TMPDIR, own KiCad config).
"""
import json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = "/path/to/SolarVest_work/wristband/v3"   # [eco3] tools copied to v3/eco3/tools_t2: absolute v3 root
PY = os.environ.get("GROW_PY", "python3")           # [grow G-4] overridable (rented Linux box)
KPY = os.environ.get("GROW_KPY", "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3")
KCLI = os.environ.get("GROW_KCLI", "kicad-cli")
ZFILE = V3 + "/track2/work/board_zones_t2_layout.json"   # [track2] 40 x 34
sys.path.insert(0, HERE)


def copy_board(src_pcb, dst_pcb):
    bi, bo = src_pcb[:-10], dst_pcb[:-10]
    shutil.copy(src_pcb, dst_pcb)
    for ext in (".kicad_pro", ".kicad_dru"):
        txt = open(bi + ext).read().replace(os.path.basename(bi) + ".kicad_pro", os.path.basename(bo) + ".kicad_pro")
        open(bo + ext, "w").write(txt)


def main(candf, out):
    T0 = time.time()
    cand = json.load(open(candf))
    out = os.path.abspath(out); os.makedirs(out + "/tmp", exist_ok=True)
    shutil.copy(candf, out + "/candidate.json")
    env = dict(os.environ, TMPDIR=out + "/tmp", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1",
               KICAD_CONFIG_HOME=out + "/tmp/kicfg", G1_ZFILE=cand.get("zfile", ZFILE), G1_NO_ISLAND="1", G1_VARIANT="v3f",
               G1_OPTS="gap=dru,jlc=full,ufpc", G1_ZONES="L41W34_fold1p9_fpcdwg_jointzif_raise0p15", G1_CRIT_W=str(cand.get("crit_w", 200)))
    os.environ.update({k: env[k] for k in ("TMPDIR", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")})
    log = open(out + "/evaluate.log", "a"); tm = {}

    def sh(name, cmd, **kw):
        t = time.time(); log.write("== %s: %s\n" % (name, " ".join(cmd))); log.flush()
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=dict(env, **kw.get("extra", {})), cwd=out)
        tm[name] = round(time.time() - t + tm.get(name, 0), 1)
        if r.returncode != 0 and not kw.get("ok_fail"):
            raise SystemExit("step %s failed (see %s/evaluate.log)" % (name, out))

    def drc(pcb, rep):
        os.makedirs(env["KICAD_CONFIG_HOME"] + "/10.0", exist_ok=True)
        kc = env["KICAD_CONFIG_HOME"] + "/10.0/kicad_common.json"
        if not os.path.exists(kc):
            open(kc, "w").write('{"system": {"language": "English"}}')
        sh("drc", [KCLI, "pcb", "drc", "--refill-zones", "--severity-all", "--format", "json", "--units", "mm", "-o", rep, pcb], ok_fail=True)
        d = json.load(open(rep)); errs = {}
        for v in d["violations"]:
            if v["severity"] == "error":
                errs[v["type"]] = errs.get(v["type"], 0) + 1
        return len(d.get("unconnected_items", [])), errs

    fan = out + "/fan.kicad_pcb"
    chk = None
    # ---------------------------------------------------------------- board source
    if cand.get("board"):
        src = os.path.abspath(cand["board"]); sd = os.path.dirname(src)
        copy_board(src, fan)
        for f in ("geom.json", "plate_forbidden_nets.json", "chk.json"):
            if os.path.exists(sd + "/" + f):
                shutil.copy(sd + "/" + f, out + "/" + f)
        chk = out + "/chk.json" if os.path.exists(out + "/chk.json") else None
    else:
        if cand.get("place_seed") is not None:
            s = str(cand["place_seed"]); pe = dict(extra=dict(G1_HOVR="D14:1.0", G1_TAG="grow"))
            sh("place", [PY, "-B", HERE + "/autoplace.py", "--iters", str(cand.get("place_iters", 1500000)), "--seed", s, "--out", out + "/pl.json"], **pe)
            sh("place", [PY, "-B", HERE + "/legalize.py", out + "/pl.json", out + "/pl_L.json"], **pe)
            sh("place", [PY, "-B", HERE + "/refine.py", out + "/pl_L.json", out + "/pl_R.json", "--iters", "2000000", "--seed", s], **pe)
            sh("place", [PY, "-B", HERE + "/refine.py", out + "/pl_R.json", out + "/placement.json", "--iters", "1500000", "--seed", "9", "--t0", "0.3"], **pe)
        else:
            pl = json.load(open(cand["placement"]))
            for ref, dx, dy, dr in cand.get("moves", []):
                p = pl["parts"][ref]
                p["x"] = round(p["x"] + dx, 4); p["y"] = round(p["y"] + dy, 4); p["rot"] = (p.get("rot", 0) + dr) % 360
            json.dump(pl, open(out + "/placement.json", "w"), indent=1)
        sh("check", [PY, "-B", HERE + "/check_placement.py", out + "/placement.json", out + "/chk.json"], ok_fail=True)
        chk = out + "/chk.json"
        sh("board", [PY, "-B", HERE + "/dump_geom.py", out + "/geom.json"])
        sh("board", [KPY, "-B", HERE + "/build_board.py", out + "/placement.json", out, "--l4-net", "VDD_1V8", "--pmic-no-pour", "--plates-open"],
           extra=dict(G1_GEOM=out + "/geom.json"))
        sh("fanout", [KPY, "-B", HERE + "/fanout_planes.py", out], extra=dict(FANOUT_OPTS=json.dumps(cand.get("fanout", {}))))
        sh("fanout", [KPY, "-B", HERE + "/rf_patch_s2e.py", out + "/v3f_g1_fan.kicad_pcb"], ok_fail=True)
        copy_board(out + "/v3f_g1_fan.kicad_pcb", fan)
    # ---------------------------------------------------------------- [grow8] P-1 forbidden nets, 8-layer conversion
    if cand.get("forbidden_add"):
        import forb_dru
        fl = sorted(set(json.load(open(out + "/plate_forbidden_nets.json"))) | set(cand["forbidden_add"]))
        json.dump(fl, open(out + "/plate_forbidden_nets.json", "w"), indent=0)
        txt = forb_dru.rewrite(open(fan[:-10] + ".kicad_dru").read(), fl)          # [grow8] read before the file is truncated
        open(fan[:-10] + ".kicad_dru", "w").write(txt)
    if int(cand.get("layers", 6)) == 8 and "(14 \"In6.Cu\" signal)" not in open(fan).read(4000):
        os.rename(fan, out + "/fan6.kicad_pcb")
        for ext in (".kicad_pro", ".kicad_dru"):
            os.rename(fan[:-10] + ext, out + "/fan6" + ext)
        sh("to8l", [KPY, "-B", HERE + "/to8l.py", out + "/fan6.kicad_pcb", fan, out + "/plate_forbidden_nets.json"])
    if cand.get("shield"):                                                 # [grow8 Q-3]
        import forb_dru
        txt = forb_dru.shield(open(fan[:-10] + ".kicad_dru").read(), cand["shield"])
        open(fan[:-10] + ".kicad_dru", "w").write(txt)
    if cand.get("neck"):                                                   # [grow8 Q-2]
        sh("neck", [KPY, "-B", HERE + "/neck_areas.py", fan, str(cand["neck"])])
    pviol = None
    if chk:
        h = json.load(open(chk)).get("hard", {})
        pviol = sum(len(v) for v in h.values())
    # ---------------------------------------------------------------- route
    un0, e0 = drc(fan, out + "/drc_fan.json")
    sh("dump", [KPY, "-B", HERE + "/maze_finish.py", "dump", fan, out + "/drc_fan.json", out + "/geom.json", out + "/plate_forbidden_nets.json", out + "/dump.json"])
    if os.environ.get("EVAL_STOP_FAN"):                                   # [finish] rebuild the fan-out board of a candidate only
        print("FAN unconnected %d errors %s placement_violations %s | %.0f s" % (un0, e0, pviol, time.time() - T0)); return
    import pfroute
    prm = dict(cand.get("router", {}))
    if cand.get("neck"):
        prm.setdefault("neck", float(cand["neck"]) - 0.1)
    if cand.get("shield"):
        prm.setdefault("shield", list(cand["shield"]))
    prm["order"] = cand.get("order", prm.get("order", "short")); prm["seed"] = cand.get("seed", prm.get("seed", 1))
    t = time.time()
    rs = pfroute.main(out + "/dump.json", out + "/routes.json", prm)
    tm["route"] = round(time.time() - t, 1)
    sh("apply", [KPY, "-B", HERE + "/maze_finish.py", "apply", fan, out + "/routes.json", out + "/routed.kicad_pcb"])
    un1, e1 = drc(out + "/routed.kicad_pcb", out + "/drc_routed.json")
    final = out + "/routed.kicad_pcb"; un2, e2 = un1, e1
    if cand.get("strip", True) and e1:
        sh("strip", [KPY, "-B", HERE + "/maze_finish.py", "strip", final, out + "/drc_routed.json", out + "/final.kicad_pcb"], extra=dict(MAZE_STRIP_ERRORS_ONLY="1"))
        final = out + "/final.kicad_pcb"
        un2, e2 = drc(final, out + "/drc_final.json")
    else:
        copy_board(final, out + "/final.kicad_pcb"); final = out + "/final.kicad_pcb"
        shutil.copy(out + "/drc_routed.json", out + "/drc_final.json")
    sh("stats", [KPY, "-B", HERE + "/board_stats.py", final, out + "/geom.json", out + "/board_stats.json"])
    bs = json.load(open(out + "/board_stats.json"))
    shield = None
    if cand.get("shield"):
        sh("shield", [KPY, "-B", HERE + "/shield_check.py", final, out + "/plate_forbidden_nets.json", out + "/shield.json", ",".join(cand["shield"])], ok_fail=True)
        if os.path.exists(out + "/shield.json"):
            shield = json.load(open(out + "/shield.json"))["total"]
    forb = set(json.load(open(out + "/plate_forbidden_nets.json")))
    vop = bs["vias_over_plates"]
    score = dict(unconnected=un2, drc_errors=sum(e2.values()), drc_errors_by_type=e2, placement_violations=pviol,
                 overused_cells_final=rs["final_overused_nodes"], overused_cells_last_iteration=rs["per_iteration"][-1]["overused"] if rs["per_iteration"] else None,
                 unconnected_before_strip=un1, drc_errors_before_strip=sum(e1.values()), unconnected_fanout=un0,
                 track_mm=bs["track_mm"], track_mm_total=bs["track_mm_total"], vias=bs["vias"], new_vias=rs["new_vias"],
                 vias_over_plates=vop, vias_over_plates_total=bs["vias_over_plates_total"],
                 forbidden_vias_over_plates=sum(c for k in vop for n, c in vop[k].items() if n in forb),
                 router=dict((k, rs[k]) for k in ("cells", "connections", "nets", "routed", "joined_elsewhere", "unrouted", "dropped", "iterations",
                                                    "final_overused_nodes", "t_prep_s", "t_route_s", "per_iteration")),
                 runtime_s=dict(tm, total=round(time.time() - T0, 1)), candidate=cand, board=final, shield=shield,
                 neck_mm_total=rs.get("neck_mm_total"), neck_mm=rs.get("neck_mm"),
                 peak_rss_mb=round(__import__("resource").getrusage(__import__("resource").RUSAGE_SELF).ru_maxrss / (1 << 20 if sys.platform == "darwin" else 1 << 10), 1))
    score["fitness"] = score["unconnected"] + 10 * score["drc_errors"] + 100 * (pviol or 0) + score["forbidden_vias_over_plates"] * 10
    json.dump(score, open(out + "/score.json", "w"), indent=1)
    print("SCORE unconnected %d drc_errors %d placement_violations %s | before strip %d / %d | %.0f s" % (
        score["unconnected"], score["drc_errors"], pviol, un1, sum(e1.values()), time.time() - T0))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
