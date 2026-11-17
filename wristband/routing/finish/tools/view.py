"""Render a V3-F placement with courtyards, CAD zones and pads -> PNG (inspection aid).
usage: venv-python view.py placement.json out.png ["title"]"""
import json, math, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lgeom as G
import place_main as P
from autoplace import Part, rot_pt, load

KCOL = {"keepout": ("#ff9a9a", "r"), "keepout_all_layers": ("#ffb0b0", "r"), "no_parts": ("#ffd9b0", "#c60"), "cutout": ("#ffffff", "k"),
        "keepout_except": ("#f3c6f3", "#a0a")}


def main():
    pl = json.load(open(sys.argv[1])); out = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else ""
    parts, obj, nets = load()
    viol = pl.get("violations", {})
    fig, ax = plt.subplots(figsize=(20, 16.5))
    ax.add_patch(Polygon(G.outline(), closed=True, fc="#f4f8f0", lw=1.6, ec="k"))
    def rect(z, **kw):
        ax.add_patch(Rectangle((z[0], z[1]), z[2] - z[0], z[3] - z[1], **kw))
    def poly(p, **kw):
        ax.add_patch(Polygon(p, closed=True, **kw))
    # height-limit zones
    for n, z in G.ZONES.items():
        if z["kind"] == "height_limit":
            for p in z["poly_board"]:
                poly(p, fc="#dfeeff" if z["h_max_mm"] >= 0.7 else "#c9d9ff", ec="#36c", lw=0.5, ls=":", alpha=0.55)
            r = z["rect_board"]
            ax.text(r[0] + 0.15, r[3] - 0.32, "%s: h <= %.2f" % (n, z["h_max_mm"]), fontsize=5.5, color="#36c")
    for nm, pg in (("E1", G.SKIN["plate_E1"]), ("E2", G.SKIN["plate_E2"])):
        for p in pg["poly_board"]:
            poly(p, fill=False, ec="purple", lw=1.0, ls="--")
        r = pg["rect_board"]
        ax.text(r[0] + 0.2, r[1] + 0.15, "plate %s (skin face): B.Cu + L5 void, no signal via" % nm, fontsize=5.5, color="purple")
    for p in G.SKIN["cap"]["poly_board"]:
        poly(p, fill=False, ec="g", lw=1.0, ls="--")
    ax.text(G.CAP[0] + 0.2, G.CAP[3] - 0.35, "optical cap (skin face)", fontsize=5.5, color="g")
    for n, z in G.ZONES.items():
        if z["kind"] in KCOL:
            fc, ec = KCOL[z["kind"]]
            for p in z["poly_board"]:
                poly(p, fc=fc, ec=ec, lw=0.5, alpha=0.75 if z["kind"] != "cutout" else 1.0)
            if z.get("area_mm2", 0) > 4 and z["kind"] != "keepout":
                r = z["rect_board"]
                ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, n, fontsize=5.5, ha="center", va="center", color=ec)
        elif z["kind"] in ("part", "land"):
            for p in z["poly_board"]:
                poly(p, fill=False, ec="#888", lw=0.6, ls="-.")
    for ref, q in pl["parts"].items():
        if ref not in obj:
            continue
        p = obj[ref]
        p.x, p.y, p.r = q["x"], q["y"], q["rot"]
        c = p.cl()
        pp = parts[ref]
        if q["side"] == "B":
            rect(c, fill=False, ec="#06c", lw=0.8, ls="--")
            ax.text(p.x, c[1] - 0.22, ref, fontsize=4.2, ha="center", va="center", color="#06c", clip_on=True)
            continue
        if ref in viol:
            col = "#ff3030"
        elif pp.get("dnp"):
            col = "#dddddd"
        elif not pp.get("jlc_placed"):
            col = "#ffe9a0"
        elif (pp.get("height_max_mm") or 0) > 0.70:
            col = "#f0a000"
        elif (pp.get("height_max_mm") or 0) > 0.50:
            col = "#8fc0ff"
        else:
            col = "#b8e0b8"
        rect(c, fc=col, ec="k" if q.get("anchor") else "#555", lw=1.1 if q.get("anchor") else 0.4, alpha=0.85)
        for num, (px, py) in p.pads0.items():
            dx, dy = rot_pt(px, py, p.r)
            ax.plot(p.x + dx, p.y + dy, ".", ms=1.5, color="#a00" if num in ("1", "A1") else "#333")
        ax.text(p.x, p.y, ref, fontsize=3.9 if len(ref) > 3 else 4.3, ha="center", va="center", clip_on=True)
    ax.set_xlim(-1.0, G.BOARD_W + 1.2); ax.set_ylim(-1.2, G.BOARD_H + 1.0); ax.set_aspect("equal")
    ax.set_xticks(range(0, int(G.BOARD_W) + 1, 1)); ax.set_yticks(range(0, int(G.BOARD_H) + 1, 1)); ax.grid(lw=0.2)
    ax.tick_params(labelsize=5)
    nv = len(viol)
    ax.set_title("%s   [variant %s, zones %s, opts %s, gap rule %s]   %s" % (title, G.VARIANT, G.ZTAG, ",".join(G.OPTS) or "-", G.GAPMODE,
                 ("NOT PLACED / violations %d: %s" % (nv, list(viol)[:14])) if nv else "no placer violation"), fontsize=8)
    ax.text(-0.8, -1.0, "green = JLC part <= 0.50 mm, blue = 0.51-0.70 mm, orange = taller than 0.70 mm, yellow = copper-only lands (hand-solder / test / fiducial), grey = DNP land, red = no legal spot; "
            "dashed blue = skin-face parts; pink / red = keep-out, orange = no-part zone (FPC, tails); view from the sky (F.Cu), X = 0 elbow / antenna end", fontsize=5.5)
    fig.savefig(out, dpi=110, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    main()
