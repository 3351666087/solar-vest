"""Assemble v3/layout/G1.md from tools/G1_head.md + the generated tables + tools/G1_tail.md.
usage: venv-python make_g1.py   (run collect_results.py first; routing trials: analyze_route.py per run directory)"""
import json, os, re
D = "/path/to/SolarVest_work/wristband/v3/layout"; WK = D + "/work"; T = D + "/tools"
TRIALS = [
 ("1", "route_S0A_B_s13_t1", "S0A", "L3 closed over the plates; net-class clearances capped at 0.20 mm; Freerouting defaults (own fan-out stage, neck-down), 20 passes asked"),
 ("2", "route_S0A_B_s13_t2", "S0A", "L3 closed over the plates; every class at 0.09 mm clearance (JLC minimum), class track widths kept; Freerouting defaults, 8 passes"),
 ("3", "route_S0A_B_s13_t3", "S0A", "as trial 2, Freerouting fan-out stage off, neck-down off, hole clearance 0.20 mm, copper to edge 0.20 mm, 10 passes"),
 ("4", "route_S0A_B_s13_t4", "S0A", "as trial 3 with L3 open over the plates (vias over the plates counted afterwards), 8 passes"),
 ("5", "route_S2W34A3_B_s13_t5", "S2-34A3 (41 x 34)", "as trial 3 on the 41 x 34 mm neighbour, 8 passes"),
]
def passes(run):
    f = f"{WK}/{run}/freerouting.log"
    if not os.path.exists(f):
        return None
    s = open(f).read()
    base = re.search(r"baseline score [0-9.]+ for (\d+) unrouted", s)
    ps = [(int(a), int(b)) for a, b in re.findall(r"Auto-routing pass #(\d+) on board .*?\((\d+) unrouted", s)]
    return dict(baseline=int(base.group(1)) if base else None, passes=len(ps), best=min(b for _, b in ps) if ps else None, last=ps[-1][1] if ps else None,
                timeout="TIMEOUT" in s)
rows = ["| Trial | Set | Settings | Freerouting: connections at start | Best pass: unrouted | KiCad DRC of the result (JLC rule deck): errors | Unconnected (KiCad) | of which GND / VDD_1V8 | Vias (all / over the plates, not GND) | Result |",
        "|---|---|---|---|---|---|---|---|---|---|"]
RJ = {}
for tid, run, st, what in TRIALS:
    p = passes(run); f = f"{WK}/{run}/route_summary.json"
    if p is None:
        continue
    if os.path.exists(f):
        r = json.load(open(f)); RJ[tid] = dict(run=run, freerouting=p, **{k: r[k] for k in ("drc_counts", "errors", "unconnected", "vias_total", "vias_over_plates", "unrouted_by_net", "track_length_mm")})
        errs = ", ".join("%s %d" % (k.split("/")[-1], v) for k, v in r["drc_counts"].items() if k.startswith("violations/error")) or "0"
        u = r["unrouted_by_net"]
        rows.append("| %s | %s | %s | %s | %s (of %d passes) | %s | %d | %d / %d | %d / %d | FAIL: not routed |" % (
            tid, st, what, p["baseline"], p["best"], p["passes"], errs, r["unconnected"], u.get("GND", 0), u.get("VDD_1V8", 0), r["vias_total"],
            sum(v for k, v in r["vias_over_plates"].items() if k.startswith("signal"))))
    else:
        RJ[tid] = dict(run=run, freerouting=p)
        rows.append("| %s | %s | %s | %s | %s (of %d passes) | no result file: stopped by the %d s limit before Freerouting wrote one | - | - | - | NOT_RUN to the end |" % (
            tid, st, what, p["baseline"], p["best"], p["passes"], 1500))
json.dump(RJ, open(WK + "/g1_routing.json", "w"), indent=1)
head = open(T + "/G1_head.md").read(); tail = open(T + "/G1_tail.md").read()
sets = open(WK + "/g1_sets.md").read()
out = head.replace("{{SETS_TABLE}}", sets).replace("{{ROUTE_TABLE}}", "\n".join(rows) + "\n") + tail
open(D + "/G1.md", "w").write(out)
print("wrote", D + "/G1.md", len(out.splitlines()), "lines;", len(rows) - 2, "routing rows")
