"""plan view of the radiator candidates and the scene near the keep-out (no MEEP): results/geom_<tag>.png"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "common")); sys.dont_write_bytecode = True
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from run_v3f import setup
from geom import Box, PolyZ, PolyX
tag, case, level, cand = sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
c, v, mesh, prims, port, ant = setup(case, level, cand, {})
print(json.dumps(ant["info"]), port, mesh.ncells / 1e6, "M cells")
fig, ax = plt.subplots(1, 2, figsize=(15, 7))
for k, (lim) in enumerate([(-4, 45, -14, 48), (0, 10, 0, 8)]):
    a = ax[k]
    for p in prims:
        if p.mat.pec and isinstance(p, PolyZ):
            for q in (p.poly.geoms if hasattr(p.poly, "geoms") else [p.poly]):
                a.fill(*q.exterior.xy, alpha=0.35, color="r" if p.tag.startswith("ant") else "gray", lw=0.3, ec="k")
        elif p.mat.pec and isinstance(p, Box):
            a.add_patch(plt.Rectangle(p.lo[:2], max(p.hi[0] - p.lo[0], 0.05), max(p.hi[1] - p.lo[1], 0.05), alpha=0.35, color="b"))
    for q in (ant["fcu"].geoms if hasattr(ant["fcu"], "geoms") else [ant["fcu"]]):
        a.plot(*q.exterior.xy, "r-", lw=1.5)
    a.add_patch(plt.Rectangle((port["x0"], port["y_gap0"]), port["x1"] - port["x0"], port["y_gap1"] - port["y_gap0"], color="g"))
    a.set_xlim(lim[0], lim[1]); a.set_ylim(lim[2], lim[3]); a.set_aspect("equal"); a.grid(True, lw=0.3)
fig.savefig(os.path.join(HERE, "results", f"geom_{tag}.png"), dpi=110)
