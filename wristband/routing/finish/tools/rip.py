"""[finish] targeted rip-up: remove router copper (tracks / vias that are not on the fan-out board MAZE_KEEP_FROM, not locked) of the
nets not in KEEP inside one or more windows; the cut runs become unconnected pairs for the next pfroute pass.
usage: kicad-python rip.py IN.kicad_pcb OUT.kicad_pcb "x0,y0,x1,y1[;x0,y0,x1,y1...]" [KEEP_NETS comma list] [ONLY_NETS comma list]
  KEEP default "GND,VDD_1V8" (plane-net copper stays). ONLY_NETS: rip only these nets (empty = every net in the window)."""
import os, sys
import pcbnew

src, dst, wins = sys.argv[1], sys.argv[2], sys.argv[3]
keep = set((sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else "GND,VDD_1V8").split(","))
only = set(sys.argv[5].split(",")) if len(sys.argv) > 5 and sys.argv[5] else None
W = [tuple(float(v) for v in w.split(",")) for w in wins.split(";")]
brd = pcbnew.LoadBoard(src)
ks = set()
for t in pcbnew.LoadBoard(os.environ["MAZE_KEEP_FROM"]).GetTracks():
    ks.add((t.GetClass(), t.GetLayer(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y))
T = pcbnew.ToMM


def hit(t):
    a = (T(t.GetStart().x), T(t.GetStart().y)); b = (T(t.GetEnd().x), T(t.GetEnd().y))
    n = max(2, int(max(abs(a[0] - b[0]), abs(a[1] - b[1])) / 0.02) + 1)
    for k in range(n + 1):
        x = a[0] + (b[0] - a[0]) * k / n; y = a[1] + (b[1] - a[1]) * k / n
        if any(w[0] <= x <= w[2] and w[1] <= y <= w[3] for w in W):
            return True
    return False


rm = []
for t in brd.GetTracks():
    if t.IsLocked() or t.GetNetname() in keep or (only is not None and t.GetNetname() not in only):
        continue
    if (t.GetClass(), t.GetLayer(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y) in ks:
        continue
    if hit(t):
        rm.append(t)
nets = {}
for t in rm:
    nets[t.GetNetname()] = nets.get(t.GetNetname(), 0) + 1
    brd.Remove(t)
pcbnew.SaveBoard(dst, brd)
print("ripped %d items in %d nets: %s" % (len(rm), len(nets), ",".join("%s:%d" % kv for kv in sorted(nets.items()))))
