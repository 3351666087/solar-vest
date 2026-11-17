"""TO meshes for the V3-F gate-3a runs (case frame X / Y, z = Z_case - 0.35); from v2/gates/g3a/common/mesh_v2b.py.
Levels: c (computational 0.25; radiator zone 0.25 mm in X / Y; 0.25 mm in z from the board to the lid top, floor 2 x 0.175;
band 0.5 mm) and f (radiator zone 0.125 mm, z 0.125 mm from the board to z 2, floor 4 x 0.0875).
The 0.5 mm band covers the pod, the lugs, the roots and the wing / capsule on the wrist (Y -13..47).
Outside: 1.0 mm, then 2.0 mm air + 16-cell PML (32 mm).  Body case: the -z PML starts in the phantom 20 mm under the skin
(as V2-B); radiated power = flux through the faces in air (flux_regions)."""
from tomesh import AxisMap, Mesh3

PML_CELLS = 16
DCOMP = {"c": 0.25, "f": 0.25}
Z_PML_BODY = -20.35
PH_X = (-20.0, 61.0)
PH_Y = (17.0 - 28.0, 17.0 + 28.0)
BAND_X = (-4.0, 45.0)
BAND_Y = (-13.0, 47.0)


def _merge(segs):
    out = []
    for s in segs:
        if out and abs(out[-1][2] - s[2]) < 1e-12 and abs(out[-1][1] - s[0]) < 1e-12:
            out[-1] = (out[-1][0], s[1], s[2])
        else:
            out.append(s)
    return out


def _axis(segs, dcomp):
    segs = _merge(segs)
    n = sum(round((b - a) / h) for a, b, h in segs)
    if n % 2:
        a3, b3, h3 = segs[-1]
        segs = segs[:-1] + [(a3, b3 + h3, h3)]
    return AxisMap(segs, dcomp)


def _mid(level, b0, b1, f0, f1):
    if level == "c":
        return [(b0, f0, 0.5), (f0, f1, 0.25), (f1, b1, 0.5)]
    return [(b0, f0 - 1, 0.5), (f0 - 1, f0, 0.25), (f0, f1, 0.125), (f1, f1 + 1, 0.25), (f1 + 1, b1, 0.5)]


def _x(level, phantom, f0, f1):
    lo = [(-56, -24, 2.0), (-24, BAND_X[0], 1.0)] if phantom else [(-52, -20, 2.0), (-20, BAND_X[0], 1.0)]
    hi = [(BAND_X[1], 65, 1.0), (65, 97, 2.0)] if phantom else [(BAND_X[1], 61, 1.0), (61, 93, 2.0)]
    return _axis(lo + _mid(level, BAND_X[0], BAND_X[1], f0, f1) + hi, DCOMP[level])


def _y(level, phantom, f0, f1):
    lo = [(-57, -25, 2.0), (-25, BAND_Y[0], 1.0)] if phantom else [(-53, -21, 2.0), (-21, BAND_Y[0], 1.0)]
    hi = [(BAND_Y[1], 59, 1.0), (59, 91, 2.0)] if phantom else [(BAND_Y[1], 55, 1.0), (55, 87, 2.0)]
    return _axis(lo + _mid(level, BAND_Y[0], BAND_Y[1], f0, f1) + hi, DCOMP[level])


def _z(level, phantom, ztop):
    lo = [(Z_PML_BODY - 32.0, Z_PML_BODY, 2.0), (Z_PML_BODY, -8.35, 1.0)] if phantom else [(-52.35, -20.35, 2.0), (-20.35, -8.35, 1.0)]
    hi = [(6.0, ztop, 1.0), (ztop, ztop + 32.0, 2.0)]
    if level == "c":
        mid = [(-8.35, -2.35, 0.5), (-2.35, -0.35, 0.25), (-0.35, 0.0, 0.175), (0.0, 4.5, 0.25), (4.5, 6.0, 0.5)]
    else:
        mid = [(-8.35, -2.35, 0.5), (-2.35, -0.35, 0.25), (-0.35, 0.0, 0.0875), (0.0, 2.0, 0.125), (2.0, 4.5, 0.25),
               (4.5, 6.0, 0.5)]
    return _axis(lo + mid + hi, DCOMP[level])


def v3f_mesh(phantom=True, level="c", fine=(0.0, 8.5, 0.0, 6.0), ztop=18.0):
    return Mesh3(_x(level, phantom, fine[0], fine[1]), _y(level, phantom, fine[2], fine[3]), _z(level, phantom, ztop))


def flux_regions(phantom=True, ztop=18.0):
    """planar regions (lo, hi, axis, weight) one cell inside the PML; body: no bottom face except its air parts"""
    if not phantom:
        lo, hi = (-19.0, -20.0, -19.35), (60.0, 54.0, ztop - 1.0)
    else:
        lo, hi = (-23.0, -24.0, Z_PML_BODY + 1.0), (64.0, 58.0, ztop - 1.0)
    R = []
    for ax in range(3):
        for side, wgt in ((0, -1), (1, +1)):
            if phantom and ax == 2 and side == 0:
                continue
            a = list(lo); b = list(hi)
            a[ax] = b[ax] = (lo, hi)[side][ax]
            R.append((tuple(a), tuple(b), ax, wgt))
    if phantom:
        z = lo[2]
        x0, x1 = PH_X; y0, y1 = PH_Y
        for (xa, ya, xb, yb) in ((lo[0], lo[1], hi[0], y0), (lo[0], y1, hi[0], hi[1]),
                                 (lo[0], y0, x0, y1), (x1, y0, hi[0], y1)):
            R.append(((xa, ya, z), (xb, yb, z), 2, -1))
    return R
