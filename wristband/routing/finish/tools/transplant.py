"""[finish] copy the router copper of a routed board (tracks / vias not on its own fan-out board) onto a new fan-out board (same
placement except a small part move), leaving out the copper that touches the windows.
usage: kicad-python transplant.py ROUTED.kicad_pcb OLD_FAN.kicad_pcb NEW_FAN.kicad_pcb OUT.kicad_pcb "x0,y0,x1,y1;..." """
import sys
import pcbnew

rt, of, nf, out, wins = sys.argv[1:6]
W = [tuple(float(v) for v in w.split(",")) for w in wins.split(";")]
T = pcbnew.ToMM
key = lambda t: (t.GetClass(), t.GetLayer(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y)
ks = {key(t) for t in pcbnew.LoadBoard(of).GetTracks()}
src = pcbnew.LoadBoard(rt); dst = pcbnew.LoadBoard(nf)
nets = dst.GetNetsByName()


def hit(t):
    a = (T(t.GetStart().x), T(t.GetStart().y)); b = (T(t.GetEnd().x), T(t.GetEnd().y))
    n = max(2, int(max(abs(a[0] - b[0]), abs(a[1] - b[1])) / 0.02) + 1)
    return any(w[0] <= a[0] + (b[0] - a[0]) * k / n <= w[2] and w[1] <= a[1] + (b[1] - a[1]) * k / n <= w[3] for k in range(n + 1) for w in W)


n_add = n_skip = 0
for t in src.GetTracks():
    if key(t) in ks:
        continue
    if hit(t):
        n_skip += 1; continue
    c = t.Duplicate(); c.SetParent(dst)
    nm = t.GetNetname()
    if nm in nets:
        c.SetNet(nets[nm])
    dst.Add(c); n_add += 1
pcbnew.ZONE_FILLER(dst).Fill(dst.Zones())
pcbnew.SaveBoard(out, dst)
print("transplanted %d router items, %d left out (windows)" % (n_add, n_skip))
