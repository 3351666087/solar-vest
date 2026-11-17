"""[finish] picture of the unconnected pairs of a maze dump: overview + one zoom per pair, copper coloured by layer.
usage: venv-python plot_pairs.py DUMP.json OUT.png TITLE"""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP, Circle

d = json.load(open(sys.argv[1]))
COL = {"F.Cu": "#c83434", "In2.Cu": "#2e8b57", "In3.Cu": "#8a2be2", "In5.Cu": "#d2a000", "In6.Cu": "#1e90ff", "B.Cu": "#3050c0",
       "In1.Cu": "#999999", "In4.Cu": "#bbbbbb"}
pairs = d["pairs"]
n = len(pairs)
fig = plt.figure(figsize=(16, 4 + 4 * ((n + 3) // 4)))
gs = fig.add_gridspec(1 + (n + 3) // 4, 4)


def draw(ax, box=None, lw=1.0):
    ol = d["outline"]; ax.plot([p[0] for p in ol] + [ol[0][0]], [p[1] for p in ol] + [ol[0][1]], "k-", lw=0.8)
    for pg in d["plates"]:
        ax.add_patch(MP(pg, closed=True, fc="#d8e8ff", ec="none", zorder=0))
    for c in d["dots"]:
        ax.add_patch(Circle(c, 1.0, fc="none", ec="#4060ff", ls=":", zorder=1))
    if box is None:
        return
    x0, y0, x1, y1 = box
    hot = {p[0]["net"] for p in pairs}
    for it in d["items"]:
        if it["k"] == "seg":
            xs = (it["a"][0], it["b"][0]); ys = (it["a"][1], it["b"][1])
            if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1:
                continue
            ax.plot(xs, ys, "-", color=COL.get(it["layer"], "k"), lw=lw * (2.5 if it["net"] in hot else 1.2), alpha=0.9 if it["net"] in hot else 0.45,
                    solid_capstyle="round", zorder=3 if it["net"] in hot else 2)
        elif it["k"] == "via":
            if x0 <= it["c"][0] <= x1 and y0 <= it["c"][1] <= y1:
                ax.add_patch(Circle(it["c"], it["r"], fc="#444444" if it["net"] not in hot else "#ff00ff", ec="none", alpha=0.7, zorder=4))
        elif it["k"] == "poly" and "zone" not in it and it["layer"] == "F.Cu":
            pts = it["pts"]
            if any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for p in pts):
                ax.add_patch(MP(pts, closed=True, fc="#e0a080" if it["net"] not in hot else "#ff60ff", ec="k", lw=0.2, alpha=0.8, zorder=2))
    for pd in d["pads"]:
        if x0 <= pd["c"][0] <= x1 and y0 <= pd["c"][1] <= y1 and pd["net"] in hot:
            ax.text(pd["c"][0], pd["c"][1], "%s.%s" % (pd["ref"], pd["num"]), fontsize=6, zorder=6)
    ax.set_xlim(x0, x1); ax.set_ylim(y1, y0)


ax = fig.add_subplot(gs[0, :])
draw(ax)
for i, (a, b) in enumerate(pairs):
    ax.plot([a["p"][0], b["p"][0]], [a["p"][1], b["p"][1]], "-o", ms=3, lw=1.5, color="C%d" % (i % 10))
    ax.text((a["p"][0] + b["p"][0]) / 2, (a["p"][1] + b["p"][1]) / 2, " %d %s" % (i + 1, a["net"]), fontsize=8, color="C%d" % (i % 10))
ax.set_aspect("equal"); ax.invert_yaxis(); ax.set_title(sys.argv[3] + " (KiCad mm; board = (x-100, 130-y); plates shaded, dot keep-outs dotted)")
for i, (a, b) in enumerate(pairs):
    ax = fig.add_subplot(gs[1 + i // 4, i % 4])
    x0, x1 = sorted((a["p"][0], b["p"][0])); y0, y1 = sorted((a["p"][1], b["p"][1]))
    m = 1.2
    draw(ax, (x0 - m, y0 - m, x1 + m, y1 + m), lw=0.8)
    ax.plot([a["p"][0], b["p"][0]], [a["p"][1], b["p"][1]], "k--", lw=1, zorder=7)
    ax.set_aspect("equal"); ax.set_title("%d %s %s-%s" % (i + 1, a["net"], a["kind"], b["kind"]), fontsize=9)
    ax.tick_params(labelsize=6)
h = [plt.Line2D([], [], color=c, lw=3, label=l) for l, c in COL.items() if l not in ("In1.Cu", "In4.Cu")]
fig.legend(handles=h, loc="lower center", ncol=6)
fig.savefig(sys.argv[2], dpi=130, bbox_inches="tight")
print("wrote", sys.argv[2])
