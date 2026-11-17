"""[grow8] Summary of one evaluate.py run: counts, layers, plate vias of the forbidden nets, where the unconnected items are.
usage: venv-python summarize.py RUNDIR [RUNDIR ...]   -> RUNDIR/summary.json and a short print"""
import collections, json, sys


def near_parts(p, fps, k=2):
    d = sorted(fps, key=lambda f: (f[1] - p[0]) ** 2 + (f[2] - p[1]) ** 2)
    return [f[0] for f in d[:k]]


for run in sys.argv[1:]:
    s = json.load(open(run + "/score.json"))
    d = json.load(open(run + "/drc_final.json"))
    forb = set(json.load(open(run + "/plate_forbidden_nets.json")))
    dump = json.load(open(run + "/dump.json"))
    fps = []
    for it in dump["items"]:
        pass
    un = []
    for v in d.get("unconnected_items", []):
        its = v["items"]
        net = its[0]["description"].split("[")[1].split("]")[0] if "[" in its[0]["description"] else "?"
        un.append(dict(net=net, a=(round(its[0]["pos"]["x"], 2), round(its[0]["pos"]["y"], 2)),
                       b=(round(its[1]["pos"]["x"], 2), round(its[1]["pos"]["y"], 2)) if len(its) > 1 else None,
                       what=[it["description"][:60] for it in its]))
    by_net = collections.Counter(u["net"] for u in un)
    vop = s["vias_over_plates"]
    forb_vias = {k: {n: c for n, c in v.items() if n in forb} for k, v in vop.items()}
    out = dict(run=run, unconnected=s["unconnected"], drc_errors=s["drc_errors"], drc_errors_by_type=s["drc_errors_by_type"],
               before_strip=[s["unconnected_before_strip"], s["drc_errors_before_strip"]], placement_violations=s["placement_violations"],
               track_mm=s["track_mm"], track_mm_total=s["track_mm_total"], vias=s["vias"], new_vias=s["new_vias"],
               vias_over_plates=vop, vias_over_plates_total=s["vias_over_plates_total"], forbidden_vias_over_plates=forb_vias,
               runtime_s=s["runtime_s"], route_s=s["router"]["t_route_s"], iterations=s["router"]["iterations"], cells=s["router"]["cells"],
               overuse_last=s["overused_cells_last_iteration"], unconnected_by_net=dict(by_net.most_common()), unconnected_items=un)
    json.dump(out, open(run + "/summary.json", "w"), indent=1)
    print(run, "| unconnected", out["unconnected"], "errors", out["drc_errors"], out["drc_errors_by_type"], "| before strip", out["before_strip"],
          "| route s", out["route_s"], "it", out["iterations"], "| total s", s["runtime_s"].get("total"))
    print("  track", out["track_mm"], "total", out["track_mm_total"], "vias", out["vias"], "new", out["new_vias"])
    print("  plate vias", out["vias_over_plates_total"], "forbidden-net plate vias", forb_vias)
    print("  unconnected by net", dict(by_net.most_common(20)))
