"""[G1 session 2] Plot one board_zones file (board frame, sky view): free area by height class, lands / parts, no-part zones, cut-outs.
usage: python3 -B plot_zones.py [zone file ...]   (default: every out/options/board_zones_*.json)
-> out/options/plots/zones_<tag>.png
"""
import glob, json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
HERE = os.path.dirname(os.path.abspath(__file__))
OPTD = os.path.normpath(os.path.join(HERE, "..", "out", "options")); PLOTS = os.path.join(OPTD, "plots"); os.makedirs(PLOTS, exist_ok=True)
COL = dict(height_limit=None, land="#d9a441", part="#c77d2e", no_parts="#d9534f", keepout="#8c8c8c", keepout_all_layers="#555555", cutout="#ffffff",
           keepout_except="#b08fc7")
HCOL = [(0.36, "#f4c7c3"), (0.56, "#bfe3f2"), (0.76, "#9fd3a8"), (0.91, "#6fbf7f"), (9.0, "#eef6e6")]


def hcol(h):
    return next(c for lim, c in HCOL if h <= lim)


def plot(path):
    bz = json.load(open(path)); tag = bz["meta"].get("tag") or os.path.basename(path)[12:-5]
    W, H = bz["board"]["W"], bz["board"]["H"]
    fig, ax = plt.subplots(figsize=(W / 3.2, H / 3.2 + 0.9), dpi=130)
    ax.add_patch(MPoly(bz["board"]["outline_board"], closed=True, fc=hcol(bz["meta"]["general_zone_h_max"]), ec="k", lw=1.2, zorder=0))
    order = ["height_limit", "keepout_except", "no_parts", "keepout", "keepout_all_layers", "land", "part", "cutout"]
    for kind in order:
        for z in bz["zones"]:
            if z["kind"] != kind:
                continue
            fc = hcol(z["h_max_mm"]) if kind == "height_limit" else COL[kind]
            for p in z["poly_board"]:
                ax.add_patch(MPoly(p, closed=True, fc=fc, ec="k", lw=0.4, alpha=0.95 if kind != "height_limit" else 1.0, zorder=1 + order.index(kind)))
            x0, y0, x1, y1 = z["rect_board"]
            if z["area_mm2"] >= 9 and (kind != "height_limit" or z["name"].startswith("under_fpc")):
                lab = z["name"] + (f"\n<= {z['h_max_mm']:g}" if kind in ("height_limit", "part") and z["h_max_mm"] else "")
                ax.text((x0 + x1) / 2, (y0 + y1) / 2, lab, ha="center", va="center", fontsize=4.6, zorder=20)
    for z in bz["zones"]:
        if z["kind"] == "height_limit" and not z["name"].startswith("under_fpc"):
            x0, y0, x1, y1 = z["rect_board"]
            ax.text(x0 + 0.4, y1 - 0.5, f"{z['name']} <= {z['h_max_mm']:g}", fontsize=4.6, va="top", zorder=20)
    ax.set_xlim(-1, W + 1); ax.set_ylim(-1, H + 1); ax.set_aspect("equal")
    ax.set_xlabel("board X, mm (0 = elbow end on a left wrist)", fontsize=6); ax.set_ylabel("board Y, mm (0 = antenna edge)", fontsize=6)
    ax.tick_params(labelsize=5)
    ax.set_title(f"{tag}: board {W:g} x {H:g} mm, sky side. green = free (darker = lower limit), red = no parts, amber = lands / parts, white = cut-out; "
                 f"general zone <= {bz['meta']['general_zone_h_max']:g} mm", fontsize=5.5)
    out = os.path.join(PLOTS, f"zones_{tag}.png"); fig.tight_layout(); fig.savefig(out); plt.close(fig)
    return out


if __name__ == "__main__":
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(OPTD, "board_zones_*.json")))
    for f in files:
        print(plot(f))
