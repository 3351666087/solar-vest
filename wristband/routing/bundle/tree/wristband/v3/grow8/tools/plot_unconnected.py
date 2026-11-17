"""[S2e] picture of the remaining unconnected pairs (ratsnest lines over the board outline, plates and courtyards).
usage: venv-python plot_unconnected.py DRC.json GEOM.json PLACEMENT_CHK_OR_NONE OUT.png TITLE"""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = json.load(open(sys.argv[1])); G = json.load(open(sys.argv[2]))["G"]
OX, OY = G["KICAD_ORIGIN"]
fig, ax = plt.subplots(figsize=(10, 8))
ol = G["OUTLINE"]; ax.plot([p[0] for p in ol] + [ol[0][0]], [p[1] for p in ol] + [ol[0][1]], "k-", lw=1)
for key in ("plate_E1", "plate_E2"):
    for pg in G["SKIN"][key]["poly_board"]:
        ax.fill([p[0] for p in pg], [p[1] for p in pg], color="#d8e8ff", zorder=0)
nets = {}
for u in d.get("unconnected_items", []):
    ps = [(it["pos"]["x"] - OX, OY - it["pos"]["y"]) for it in u["items"]]
    de = u["items"][0]["description"]; n = de[de.find("[") + 1:de.find("]")] if "[" in de else "?"
    nets[n] = nets.get(n, 0) + 1
    if len(ps) == 2:
        ax.plot([ps[0][0], ps[1][0]], [ps[0][1], ps[1][1]], "r-", lw=1.2)
        ax.plot([ps[0][0], ps[1][0]], [ps[0][1], ps[1][1]], "r.", ms=4)
        ax.text((ps[0][0] + ps[1][0]) / 2, (ps[0][1] + ps[1][1]) / 2, n, fontsize=5, color="darkred")
ax.set_aspect("equal"); ax.set_xlabel("board X (mm)"); ax.set_ylabel("board Y (mm)")
ax.set_title("%s: %d unconnected items in %d nets (plates shaded)" % (sys.argv[5], sum(nets.values()), len(nets)))
fig.savefig(sys.argv[4], dpi=160, bbox_inches="tight")
print("wrote", sys.argv[4])
