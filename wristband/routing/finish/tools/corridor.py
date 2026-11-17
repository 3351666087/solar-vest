"""[finish] windows string for rip.py along a polyline: squares of half-size H every STEP mm.  usage: corridor.py H x0,y0 x1,y1 [...]"""
import math, sys
H = float(sys.argv[1]); P = [tuple(map(float, a.split(","))) for a in sys.argv[2:]]
out = []
for a, b in zip(P, P[1:]):
    n = max(1, int(math.dist(a, b) / H))
    for k in range(n + 1):
        x = a[0] + (b[0] - a[0]) * k / n; y = a[1] + (b[1] - a[1]) * k / n
        out.append("%.2f,%.2f,%.2f,%.2f" % (x - H, y - H, x + H, y + H))
print(";".join(out))
