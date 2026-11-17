"""TO (non-uniform) meshes for the V2-B gate-3a runs (see tomesh.py).

Three levels.  The radiator and every band dimension are designed on a 0.5 mm grid, so all levels represent the
same copper (only the port gap = one radiator-zone cell differs).
  level "s" (screening):  computational cell 0.5 mm; band and radiator zone 0.5 mm in X, Y, Z (trace 0.5 mm = 1 cell);
                          floor = 1 cell of 0.35 mm.
  level "c" (reference):  computational cell 0.25 mm; radiator zone 0.25 mm in X / Y, floor 2 x 0.175 mm,
                          0.25 mm in Z from the board to the lid top; rest of the band 0.5 mm.
  level "f" (fine):       computational cell 0.25 mm; radiator zone 0.125 mm in X / Y, floor 4 x 0.0875 mm,
                          0.125 mm in Z around the radiator plane.
Outside the band: 1.0 mm (phantom, near air), 2.0 mm (outer air + PML, 16 cells = 32 mm), as SIM-10 v1.

Difference to SIM-10 v1 (sim/rf/common/meshes.py), made to cut the run time on the shared machine:
the -z PML starts INSIDE the phantom, 20 mm below the skin plane (z = -20.35); the tissue continues into the
PML and is absorbed there (skin depth in muscle at 2.44 GHz: 22 mm).  The radiated power is therefore taken from
the five faces of the flux box that lie in air plus the air strips of the bottom face beside the phantom
(flux_regions()); power that enters the deep tissue is counted as absorbed.  Validation: validation/ (this lane).
"""
from tomesh import AxisMap, Mesh3

PML_CELLS = 16
DCOMP = {"s": 0.5, "c": 0.25, "f": 0.25}
Z_PML_BODY = -20.35
PH_X = (-20.0, 57.0)          # phantom length (as v1)
PH_Y = (-13.5, 42.5)          # phantom width: yc 14.5 +- a 28


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


def _x(level, phantom, fx0, fx1):
    lo = [(-56, -24, 2.0), (-24, -4, 1.0)] if phantom else [(-52, -20, 2.0), (-20, -4, 1.0)]
    hi = [(42, 62, 1.0), (62, 94, 2.0)] if phantom else [(42, 58, 1.0), (58, 90, 2.0)]
    if level == "s":
        mid = [(-4, 42, 0.5)]
    elif level == "c":
        mid = [(-4, fx0, 0.5), (fx0, fx1, 0.25), (fx1, 42, 0.5)]
    else:
        mid = [(-4, fx0 - 1, 0.5), (fx0 - 1, fx0, 0.25), (fx0, fx1, 0.125), (fx1, fx1 + 1, 0.25), (fx1 + 1, 42, 0.5)]
    return _axis(lo + mid + hi, DCOMP[level])


def _y(level, phantom, fy0, fy1):
    lo = [(-50, -18, 2.0), (-18, -6, 1.0)] if phantom else [(-52, -20, 2.0), (-20, -6, 1.0)]
    hi = [(36, 48, 1.0), (48, 80, 2.0)] if phantom else [(36, 50, 1.0), (50, 82, 2.0)]
    if level == "s":
        mid = [(-6, 36, 0.5)]
    elif level == "c":
        mid = [(-6, fy0, 0.5), (fy0, fy1, 0.25), (fy1, 36, 0.5)]
    else:
        mid = [(-6, fy0 - 1, 0.5), (fy0 - 1, fy0, 0.25), (fy0, fy1, 0.125), (fy1, fy1 + 1, 0.25), (fy1 + 1, 36, 0.5)]
    return _axis(lo + mid + hi, DCOMP[level])


def _z(level, phantom, zfine, ztop):
    """ztop: start of the +z PML (18 nominal; larger for the hand / dock variants)"""
    lo = [(Z_PML_BODY - 32.0, Z_PML_BODY, 2.0), (Z_PML_BODY, -8.35, 1.0)] if phantom else [(-52.35, -20.35, 2.0), (-20.35, -8.35, 1.0)]
    hi = [(6.0, ztop, 1.0), (ztop, ztop + 32.0, 2.0)]
    if level == "s":
        mid = [(-8.35, -0.35, 0.5), (-0.35, 0.0, 0.35), (0.0, 6.0, 0.5)]
    elif level == "c":
        mid = [(-8.35, -2.35, 0.5), (-2.35, -0.35, 0.25), (-0.35, 0.0, 0.175), (0.0, 4.0, 0.25), (4.0, 6.0, 0.5)]
    elif zfine <= 1.0 + 1e-9:
        mid = [(-8.35, -2.35, 0.5), (-2.35, -0.35, 0.25), (-0.35, 0.0, 0.0875), (0.0, 2.0, 0.125), (2.0, 4.0, 0.25),
               (4.0, 6.0, 0.5)]
    else:
        mid = [(-8.35, -2.35, 0.5), (-2.35, -0.35, 0.25), (-0.35, 0.0, 0.0875), (0.0, 4.0, 0.125), (4.0, 6.0, 0.5)]
    return _axis(lo + mid + hi, DCOMP[level])


def v2b_mesh(phantom=True, level="s", fine=(-2.0, 18.0, -2.0, 8.0), zfine=1.0, ztop=18.0):
    """fine = (x0, x1, y0, y1) of the radiator zone (levels c and f)"""
    return Mesh3(_x(level, phantom, fine[0], fine[1]), _y(level, phantom, fine[2], fine[3]),
                 _z(level, phantom, zfine, ztop))


def flux_regions(phantom=True, ztop=18.0):
    """list of (lo, hi, axis, weight): planar regions whose summed weighted flux is the radiated power.
    Free space: the six faces of a box one cell inside the PML.  Phantom: top + four side faces in air, plus the
    air parts of the bottom face (z = one cell above the -z PML) outside the phantom's rectangle."""
    if not phantom:
        lo, hi = (-19.0, -19.0, -19.35), (57.0, 49.0, ztop - 1.0)
    else:
        lo, hi = (-23.0, -17.0, Z_PML_BODY + 1.0), (61.0, 47.0, ztop - 1.0)
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
