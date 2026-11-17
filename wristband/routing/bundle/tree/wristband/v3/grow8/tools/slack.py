"""Remaining slack of a legal placement: how many more 0402 capacitors (courtyard 1.64 x 0.86 mm, 0.60 mm body) and 0201 resistors
(1.10 x 0.64 mm, 0.26 mm body) could still be placed legally (same rules as the run: zones, edge band, pairwise gap incl. the JLC
table if jlc=full). Greedy fill on a 0.1 mm grid: a lower bound of what fits, comparable between option sets.
usage: [env] venv-python slack.py placement.json [out.json]"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lgeom as G, place_main as P
from autoplace import load, Zones
from legalize import counts

DUMMY = {"C0402": dict(w=1.64, h=0.86, need=0.65, area=1.41), "R0201": dict(w=1.10, h=0.64, need=0.31, area=0.704)}
STEP = 0.1


def gap_to(ref):
    """gap between a dummy chip passive and an existing part (centre-line boxes)"""
    g = P.BASE_GAP
    if P.JLC_MODE == "full":
        c = P.jclass(ref)
        if c:
            g = max(g, P.JLC_T.get(("chip", c), P.JLC_T.get((c, "chip"))) - 0.15 - P.margin(ref))
    return g


def fill(obj, ZN, d):
    xs = np.arange(0.5, G.BOARD_W - 0.5 + 1e-9, STEP); ys = np.arange(0.5, G.BOARD_H - 0.5 + 1e-9, STEP)
    X, Y = np.meshgrid(xs, ys)
    lim = ZN.lim
    S = G.integral(lim < d["need"] - 1e-9)
    boxes = [(obj[r].cl(), gap_to(r)) for r in obj if obj[r].side == "F"]
    ok = []
    dims = [(d["w"] / 2, d["h"] / 2), (d["h"] / 2, d["w"] / 2)]
    for hw, hh in dims:
        m = counts(S, (X - hw).ravel(), (Y - hh).ravel(), (X + hw).ravel(), (Y + hh).ravel()).reshape(X.shape) < 0.5
        for c, g in boxes:
            m &= ~((X + hw + g > c[0] + 1e-9) & (X - hw - g < c[2] - 1e-9) & (Y + hh + g > c[1] + 1e-9) & (Y - hh - g < c[3] - 1e-9))
        ok.append(m)
    n = 0; placed = []
    ny, nx = X.shape
    for j in range(ny):
        for i in range(nx):
            for k in (0, 1):
                if not ok[k][j, i]:
                    continue
                hw, hh = dims[k]
                n += 1; placed.append((float(xs[i]), float(ys[j]), k))
                for k2 in (0, 1):
                    hw2, hh2 = dims[k2]
                    di = int(np.ceil((hw + hw2 + P.BASE_GAP) / STEP - 1e-6)); dj = int(np.ceil((hh + hh2 + P.BASE_GAP) / STEP - 1e-6))
                    ok[k2][max(0, j - dj + 1):j + dj, max(0, i - di + 1):i + di] = False
                break
    return n, placed


def main():
    pl = json.load(open(sys.argv[1]))
    parts, obj, nets = load()
    for r, q in pl["parts"].items():
        if r in obj:
            obj[r].x, obj[r].y, obj[r].r = q["x"], q["y"], q["rot"]
    ZN = Zones(obj)
    res = dict(placement=os.path.basename(sys.argv[1]), zones=G.ZTAG, opts=G.OPTS, method="greedy fill, 0.1 mm grid, same legality rules as the run")
    for name, d in DUMMY.items():
        n, placed = fill(obj, ZN, d)
        res[name] = dict(extra_parts=n, extra_courtyard_mm2=round(n * d["area"], 1))
    if len(sys.argv) > 2:
        json.dump(res, open(sys.argv[2], "w"), indent=1)
    print("slack: +%d x C0402 (%.1f mm2) or +%d x R0201 (%.1f mm2) still fit" % (res["C0402"]["extra_parts"], res["C0402"]["extra_courtyard_mm2"],
                                                                                    res["R0201"]["extra_parts"], res["R0201"]["extra_courtyard_mm2"]))


if __name__ == "__main__":
    main()
