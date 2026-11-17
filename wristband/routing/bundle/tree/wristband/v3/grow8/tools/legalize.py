"""Greedy minimum-displacement legaliser for an annealed V3-F placement (autoplace.py output); v1 / V2-B algorithm with the
rastered V3-F zones.

Parts are committed one by one (most restricted first: NO_PLATE parts, then tall parts, then by area) at the legal position
nearest to their annealed position: centre-line courtyard only on cells the part may use (edge band, keep-outs, no-part zones,
height limit, plates for NO_PLATE parts, skin-face pads for NO_BSHADOW parts), no overlap of the overlap boxes (gap rule of
lgeom.GAPMODE), R-ECG-1 >= 8 mm. Candidates: grid around the annealed spot (expanding window), all four rotations; ties broken by the
weighted wirelength to already committed parts. Deterministic.
usage: venv-python legalize.py IN.json OUT.json
"""
import json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lgeom as G
import place_main as P
from autoplace import Part, load, Zones, GAP


def counts(S, x0, y0, x1, y1):
    """vectorised lgeom.rect_count"""
    i0 = np.clip(np.floor((x0 - G.X0) / G.RES + 1e-6).astype(int), 0, G.NX); i1 = np.clip(np.ceil((x1 - G.X0) / G.RES - 1e-6).astype(int), 0, G.NX)
    j0 = np.clip(np.floor((y0 - G.Y0) / G.RES + 1e-6).astype(int), 0, G.NY); j1 = np.clip(np.ceil((y1 - G.Y0) / G.RES - 1e-6).astype(int), 0, G.NY)
    return S[j1, i1] - S[j0, i1] - S[j1, i0] + S[j0, i0]


def covered(x0, y0, x1, y1, zs):
    s = np.zeros_like(x0)
    for z in zs:
        w = np.minimum(x1, z[2]) - np.maximum(x0, z[0]); h = np.minimum(y1, z[3]) - np.maximum(y0, z[1])
        s += np.where((w > 0) & (h > 0), w * h, 0.0)
    return s


def main():
    src, dst = sys.argv[1], sys.argv[2]
    pl = json.load(open(src))
    pl = pl.get("parts", pl)
    parts, obj, nets = load()
    for r, q in pl.items():
        if r in obj and r not in P.ANCHORS:
            obj[r].x, obj[r].y, obj[r].r = q["x"], q["y"], q["rot"]
    anchors = set(P.ANCHORS)
    ZN = Zones(obj)
    occ = [obj[r].crt(gap=0.0) for r in anchors if obj[r].side == "F"]
    occ_ref = [r for r in anchors if obj[r].side == "F"]
    movable = [r for r in obj if r not in anchors and obj[r].side == "F"]
    pw = {}
    for (pp, ic, pad, w) in P.PAIRS:
        pw[pp] = max(pw.get(pp, 0), w)
    # big / tall parts first (most restricted), then the parts tied to an IC pin by a proximity pair (strongest first), then by area
    order = sorted(movable, key=lambda r: (0 if (obj[r].area() >= 5.0 or obj[r].need > 0.75 + 1e-9) else 1, 0 if r in P.NO_PLATE else 1,
                                           -obj[r].area() if obj[r].area() >= 5.0 else 0, -pw.get(r, 0), -obj[r].area(), r))
    netsof = {}
    for n, pins in nets.items():
        for (r, num) in pins:
            netsof.setdefault(r, []).append(n)
    done = set(anchors)
    moved, failed = {}, []
    sw_set = set(P.SWITCHERS) | set(P.FIXED_AGGR)
    ecg_refs = {it for it in P.ECG_ITEMS if not isinstance(it, tuple)}
    ecg_pts_fixed = []                      # ECG items already committed (anchors + U7 pins once U7 is placed)
    def ecg_points():
        pts = []
        for it in P.ECG_ITEMS:
            ref = it[0] if isinstance(it, tuple) else it
            if ref in done:
                pts.append(obj[ref].pad(it[1]) if isinstance(it, tuple) else (obj[ref].x, obj[ref].y))
        return pts
    for r in order:
        o = obj[r]
        ax, ay = o.x, o.y
        S = ZN.integral(o)
        best = None
        for win, st in ((0.5, 0.05), (1.0, 0.05), (2.0, 0.1), (3.5, 0.1), (6.0, 0.2), (10.0, 0.25), (45.0, 0.25)):
            xs = np.arange(ax - win, ax + win + 1e-9, st)
            ys = np.arange(ay - win, ay + win + 1e-9, st)
            xs = xs[(xs > -1) & (xs < G.BOARD_W + 1)]; ys = ys[(ys > -1) & (ys < G.BOARD_H + 1)]
            if len(xs) == 0 or len(ys) == 0:
                continue
            X, Y = np.meshgrid(xs, ys)
            X = X.ravel(); Y = Y.ravel()
            O = np.array(occ)
            GV = np.array([P.pair_gap(r, q) for q in occ_ref])
            reach = win + 8.0
            sel = (O[:, 2] > ax - reach) & (O[:, 0] < ax + reach) & (O[:, 3] > ay - reach) & (O[:, 1] < ay + reach)
            O = O[sel]; GV = GV[sel]
            if len(O) == 0:
                O = np.array([[-99, -99, -98, -98]]); GV = np.array([0.0])
            for rot in (o.r, (o.r + 90) % 360, (o.r + 180) % 360, (o.r + 270) % 360):
                c = Part.cl(o, 0, 0, rot)
                zx0, zy0, zx1, zy1 = X + c[0], Y + c[1], X + c[2], Y + c[3]
                ok = counts(S, zx0, zy0, zx1, zy1) < 0.5
                if not ok.any():
                    continue
                if r in P.NO_PLATE:
                    ok &= counts(ZN.plate, zx0, zy0, zx1, zy1) < 0.5
                if r in P.NO_BSHADOW:
                    ok &= covered(zx0, zy0, zx1, zy1, ZN.bshadow) <= 1e-9
                if r in P.ON_PLATE:
                    ok &= counts(ZN.offplate, zx0, zy0, zx1, zy1) < 0.5
                b = Part.crt(o, 0, 0, rot, gap=0.0)
                gx0, gy0, gx1, gy1 = X + b[0], Y + b[1], X + b[2], Y + b[3]
                for k in range(0, len(O), 64):
                    blk = O[k:k + 64]; gv = GV[k:k + 64]
                    w = np.minimum(gx1[:, None], blk[None, :, 2]) - np.maximum(gx0[:, None], blk[None, :, 0]) + gv[None, :]
                    h = np.minimum(gy1[:, None], blk[None, :, 3]) - np.maximum(gy0[:, None], blk[None, :, 1]) + gv[None, :]
                    ok &= ~(((w > 1e-6) & (h > 1e-6)).any(axis=1))
                    if not ok.any():
                        break
                if not ok.any():
                    continue
                if r in ecg_refs or r == "U7":
                    for s in sw_set & done:
                        if r == "U7":
                            for pin in ("3", "4"):
                                px, py = Part.pad(o, pin, 0, 0, rot)
                                ok &= np.hypot(X + px - obj[s].x, Y + py - obj[s].y) >= P.ECG_MIN
                        elif not (s == "J16" and r in P.E3_TIED):
                            ok &= np.hypot(X - obj[s].x, Y - obj[s].y) >= P.ECG_MIN
                if r in sw_set:
                    for (qx, qy) in ecg_points():
                        ok &= np.hypot(X - qx, Y - qy) >= P.ECG_MIN
                if not ok.any():
                    continue
                idx = np.nonzero(ok)[0]
                d2 = (X[idx] - ax) ** 2 + (Y[idx] - ay) ** 2
                wl = np.zeros_like(d2)
                for n in netsof.get(r, []):
                    pts = [obj[q].pad(num) for (q, num) in nets[n] if q in done and q != r]
                    if not pts:
                        continue
                    cx = np.mean([p[0] for p in pts]); cy = np.mean([p[1] for p in pts])
                    wl += P.NET_W.get(n, 1.0) * (np.abs(X[idx] - cx) + np.abs(Y[idx] - cy))
                cost = d2 * 10 + wl * 0.05 + (0 if rot == o.r else 0.5)
                j = int(np.argmin(cost))
                cand = (float(cost[j]), float(X[idx][j]), float(Y[idx][j]), rot)
                if best is None or cand[0] < best[0]:
                    best = cand
            if best:
                break
        if best is None:                                # last resort: every 0.05 mm position of the board, both orientations
            xs = np.arange(0.4, G.BOARD_W - 0.4 + 1e-9, 0.05); ys = np.arange(0.4, G.BOARD_H - 0.4 + 1e-9, 0.05)
            X, Y = np.meshgrid(xs, ys); X = X.ravel(); Y = Y.ravel()
            O = np.array(occ); GV = np.array([P.pair_gap(r, q) for q in occ_ref])
            for rot in (o.r, (o.r + 90) % 360):
                c = Part.cl(o, 0, 0, rot)
                zx0, zy0, zx1, zy1 = X + c[0], Y + c[1], X + c[2], Y + c[3]
                ok = counts(S, zx0, zy0, zx1, zy1) < 0.5
                if r in P.NO_PLATE:
                    ok &= counts(ZN.plate, zx0, zy0, zx1, zy1) < 0.5
                if r in P.NO_BSHADOW:
                    ok &= covered(zx0, zy0, zx1, zy1, ZN.bshadow) <= 1e-9
                if r in ecg_refs:
                    for s in sw_set & done:
                        if not (s == "J16" and r in P.E3_TIED):
                            ok &= np.hypot(X - obj[s].x, Y - obj[s].y) >= P.ECG_MIN
                if r in sw_set:
                    for (qx, qy) in ecg_points():
                        ok &= np.hypot(X - qx, Y - qy) >= P.ECG_MIN
                ii = np.nonzero(ok)[0]
                if len(ii) == 0:
                    continue
                Xi, Yi = X[ii], Y[ii]; keep = np.ones(len(ii), dtype=bool)
                for k in range(0, len(O), 32):
                    blk = O[k:k + 32]; gv = GV[k:k + 32]
                    w = np.minimum((Xi + c[2])[:, None], blk[None, :, 2]) - np.maximum((Xi + c[0])[:, None], blk[None, :, 0]) + gv[None, :]
                    h = np.minimum((Yi + c[3])[:, None], blk[None, :, 3]) - np.maximum((Yi + c[1])[:, None], blk[None, :, 1]) + gv[None, :]
                    keep &= ~(((w > 1e-6) & (h > 1e-6)).any(axis=1))
                    if not keep.any():
                        break
                if keep.any():
                    d2 = (Xi[keep] - ax) ** 2 + (Yi[keep] - ay) ** 2
                    j = int(np.argmin(d2))
                    cand = (float(d2[j]), float(Xi[keep][j]), float(Yi[keep][j]), rot)
                    if best is None or cand[0] < best[0]:
                        best = cand
        if best is None:
            failed.append(r)
            continue
        o.x, o.y, o.r = round(best[1], 3), round(best[2], 3), best[3]
        moved[r] = round(math.hypot(o.x - ax, o.y - ay), 3)
        occ.append(o.crt(gap=0.0)); occ_ref.append(r)
        done.add(r)
    out = {r: dict(x=obj[r].x, y=obj[r].y, rot=obj[r].r, side=obj[r].side, need=obj[r].need, anchor=r in anchors) for r in obj}
    big = {r: d for r, d in moved.items() if d > 1.0}
    viol = {r: dict(no_legal_spot=True, area=round(obj[r].area(), 2)) for r in failed}
    json.dump(dict(parts=out, cost=0.0, violations=viol, legalised_from=os.path.basename(src), moved_over_1mm=big,
                   variant=G.VARIANT, zones=G.ZTAG, opts=G.OPTS), open(dst, "w"), indent=1)
    print("legalised %d of %d; NO LEGAL SPOT for %d: %s (area %.1f mm2); moved > 1 mm: %d, max %.2f mm, mean %.3f mm" % (
        len(moved), len(movable), len(failed), failed, sum(obj[r].area() for r in failed), len(big),
        max(moved.values()) if moved else 0, sum(moved.values()) / max(1, len(moved))))


if __name__ == "__main__":
    main()
