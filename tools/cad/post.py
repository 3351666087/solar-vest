"""Post-route cleanup on a routed board (routing untouched):
  - refill GND zones with island removal + thermal settings
  - move every visible reference designator / board label to the nearest spot that clears pads, other silk and the edge
usage: kicad-python post.py <b>
"""
import os, sys, importlib, pcbnew
B = sys.argv[1]; HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
plc = importlib.import_module("place_" + B)
P = os.path.join(HERE, "out", B, f"{B}.kicad_pcb")
brd = pcbnew.LoadBoard(P); MM = pcbnew.FromMM; ToMM = pcbnew.ToMM
for z in brd.Zones():
    z.SetThermalReliefGap(MM(0.3)); z.SetThermalReliefSpokeWidth(MM(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)

edge = brd.GetBoardEdgesBoundingBox(); edge.Inflate(-MM(0.6))
class Box:
    def __init__(s, b, pad=0.0): s.l, s.t, s.r, s.b = ToMM(b.GetLeft()) - pad, ToMM(b.GetTop()) - pad, ToMM(b.GetRight()) + pad, ToMM(b.GetBottom()) + pad
    def hit(s, o): return not (s.r <= o.l or o.r <= s.l or s.b <= o.t or o.b <= s.t)
# obstacles: all front pads (+0.15 mm), all footprint silk graphics, mounting holes
obst = []
for f in brd.GetFootprints():
    for p in f.Pads():
        if p.IsOnLayer(pcbnew.F_Cu) or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH: obst.append(Box(p.GetBoundingBox(), 0.15))
    for g in f.GraphicalItems():
        if g.GetLayer() != pcbnew.F_SilkS or g.GetClass() == "PCB_TEXT": continue
        if g.GetShape() == pcbnew.SHAPE_T_RECT:          # a rectangle outline only blocks its four edges
            s0, s1 = g.GetStart(), g.GetEnd(); w2 = MM(0.1)
            for a, b in (((s0.x, s0.y), (s1.x, s0.y)), ((s1.x, s0.y), (s1.x, s1.y)), ((s1.x, s1.y), (s0.x, s1.y)), ((s0.x, s1.y), (s0.x, s0.y))):
                bx = pcbnew.BOX2I(pcbnew.VECTOR2I(min(a[0], b[0]) - w2, min(a[1], b[1]) - w2), pcbnew.VECTOR2L(abs(a[0] - b[0]) + 2 * w2, abs(a[1] - b[1]) + 2 * w2))
                obst.append(Box(bx, 0.0))
        else: obst.append(Box(g.GetBoundingBox(), 0.1))
placed = []
def inside(b): return b.l >= ToMM(edge.GetLeft()) and b.r <= ToMM(edge.GetRight()) and b.t >= ToMM(edge.GetTop()) and b.b <= ToMM(edge.GetBottom())
def free(t):
    b = Box(t.GetBoundingBox(), 0.05)
    return inside(b) and not any(b.hit(o) for o in obst) and not any(b.hit(o) for o in placed)
def settle(t, candidates):
    for x, y, ang in candidates:
        t.SetPosition(pcbnew.VECTOR2I(int(x), int(y))); t.SetTextAngleDegrees(ang)
        if free(t): placed.append(Box(t.GetBoundingBox(), 0.05)); return True
    return False

moved, failed = [], []
# 1) board labels first (they carry the connector names), nudged in a growing spiral
for t in [d for d in brd.GetDrawings() if isinstance(d, pcbnew.PCB_TEXT) and d.GetLayer() == pcbnew.F_SilkS]:
    x0, y0 = t.GetPosition().x, t.GetPosition().y; a = t.GetTextAngleDegrees()
    cands = [(x0, y0, a)] + [(x0 + MM(dx * 0.25), y0 + MM(dy * 0.25), a) for r in range(1, 30) for dx in range(-r, r + 1) for dy in (-r, r)] \
            + [(x0 + MM(dx * 0.25), y0 + MM(dy * 0.25), a) for r in range(1, 30) for dy in range(-r + 1, r) for dx in (-r, r)]
    cands.sort(key=lambda c: (c[0] - x0) ** 2 + (c[1] - y0) ** 2)
    if settle(t, cands): moved.append(t.GetText()) if (t.GetPosition().x, t.GetPosition().y) != (x0, y0) else None
    else: t.SetPosition(pcbnew.VECTOR2I(x0, y0)); failed.append(t.GetText() + " (left in place)")
# 2) reference designators: try the four sides of the footprint body, then a spiral
for f in sorted(brd.GetFootprints(), key=lambda f: -f.GetBoundingBox(False).GetArea()):
    t = f.Reference()
    if f.GetReference().startswith("H"): t.SetVisible(False)
    if not t.IsVisible(): continue
    bb = f.GetBoundingBox(False); cx, cy = bb.GetCenter().x, bb.GetCenter().y
    g = MM(0.75)
    cands = [(t.GetPosition().x, t.GetPosition().y, t.GetTextAngleDegrees()),
             (cx, bb.GetTop() - g, 0), (cx, bb.GetBottom() + g, 0), (bb.GetLeft() - g, cy, 90), (bb.GetRight() + g, cy, 90),
             (bb.GetLeft() - MM(1.2), cy, 0), (bb.GetRight() + MM(1.2), cy, 0)]
    cands += [(cx + MM(dx * 0.4), cy + MM(dy * 0.4), ang) for r in range(2, 10) for dx in range(-r, r + 1) for dy in range(-r, r + 1)
              if max(abs(dx), abs(dy)) == r for ang in (0, 90)]
    old = (t.GetPosition().x, t.GetPosition().y)
    if settle(t, cands):
        if (t.GetPosition().x, t.GetPosition().y) != old: moved.append(f.GetReference())
    else:
        t.SetPosition(pcbnew.VECTOR2I(*old)); t.SetLayer(pcbnew.F_Fab); failed.append(f.GetReference() + "->Fab")
pcbnew.ZONE_FILLER(brd).Fill(brd.Zones()); brd.Save(P)
print(f"{B}: moved {len(moved)} {moved} | no room (moved to Fab layer): {failed}")
