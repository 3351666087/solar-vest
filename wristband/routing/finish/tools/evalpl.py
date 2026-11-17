"""Cost breakdown of a placement (wirelength, pairs, overlap area, zone area). usage: [env] venv-python evalpl.py placement.json"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import lgeom as G, place_main as P
from autoplace import load, Zones, gap_matrix
pl = json.load(open(sys.argv[1]))["parts"]
parts, obj, nets = load()
for r, q in pl.items():
    if r in obj: obj[r].x, obj[r].y, obj[r].r = q["x"], q["y"], q["rot"]
ZN = Zones(obj)
wl = 0.0; wlw = 0.0
for n, pins in nets.items():
    pts = [obj[r].pad(num) for r, num in pins]
    h = (max(p[0] for p in pts) - min(p[0] for p in pts)) + (max(p[1] for p in pts) - min(p[1] for p in pts))
    wl += h; wlw += P.NET_W.get(n, 1.0) * h
pc = 0.0; pd = []
for (pp, ic, pad, w) in P.PAIRS:
    tx, ty = obj[ic].pad(pad)
    d = min(math.hypot(px - tx, py - ty) for px, py in (obj[pp].pad(k) for k in obj[pp].pads0))
    pc += w * d; pd.append((round(d, 2), pp, ic))
fside = [q for q in sorted(obj) if obj[q].side == "F"]
R = np.array([obj[q].crt() for q in fside]); GM = gap_matrix(fside)
ova = 0.0; nov = 0
for i, r in enumerate(fside):
    c = R[i]; g = GM[i]
    w = np.minimum(R[:, 2], c[2]) - np.maximum(R[:, 0], c[0]) + g
    h = np.minimum(R[:, 3], c[3]) - np.maximum(R[:, 1], c[1]) + g
    a = np.where((w > 1e-9) & (h > 1e-9), w * h, 0.0); a[i] = 0
    ova += a.sum() / 2; nov += int((a > 1e-9).sum())
za = sum(ZN.area(obj[r]) for r in fside if r not in P.ANCHORS)
crit = []
for (pp, ic, pad, dm) in P.CRIT:
    tx, ty = obj[ic].pad(pad)
    d = min(math.hypot(px - tx, py - ty) for px, py in (obj[pp].pad(k) for k in obj[pp].pads0))
    if d > dm + 1e-6: crit.append((pp, ic, round(d, 2), dm))
print("critical pairs beyond their limit: %d of %d %s" % (len(crit), len(P.CRIT), crit[:12]))
pd.sort(reverse=True)
print("HPWL %.1f mm (weighted %.1f), pairs cost %.1f (mean distance %.2f mm, worst %s), overlap area %.3f mm2 (%d pair hits), zone area %.3f mm2" % (
    wl, wlw, pc, sum(d for d, _, _ in pd) / len(pd), pd[:6], ova, nov // 2, za))
