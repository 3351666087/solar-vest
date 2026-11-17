"""[S2e] apply the two RF-corner fan-out fixes of fanout_planes.py to an already routed board (in place):
remove the GND fan-out track of AE1 pad 2 (it ran into the pocket rule area; the pad sits in the RF_GND_EDGE pour) and replace the
L204.1 -> feed-junction track (0.05 mm from AE1's GND pad) by an L204.1 -> C215.2 track (0.17 mm, F.Cu).
usage: kicad-python rf_patch_s2e.py BOARD.kicad_pcb [OUT.kicad_pcb]"""
import math, sys
import pcbnew

MM, TO = pcbnew.FromMM, pcbnew.ToMM
b = pcbnew.LoadBoard(sys.argv[1])
pad = lambda r, n: [q for q in b.FindFootprintByReference(r).Pads() if q.GetNumber() == n][0]
ae2, l1, c2 = pad("AE1", "2"), pad("L204", "1"), pad("C215", "2")
gone = 0
TR = list(b.GetTracks()); keep = []
for t in TR:
    if t.GetClass() != "PCB_TRACK" or t.GetLayer() != pcbnew.F_Cu:
        continue
    ends = (t.GetStart(), t.GetEnd())
    if t.GetNetname() == "GND" and any(ae2.HitTest(e) for e in ends) and TO(t.GetLength()) > 1.0:
        b.Remove(t); gone += 1; continue
    elif t.GetNetname() == "ANT_FEED" and any(l1.HitTest(e) for e in ends) and not any(c2.HitTest(e) for e in ends):
        b.Remove(t); gone += 1; continue
    keep.append(t)
if not any(t.GetNetname() == "ANT_FEED" and l1.HitTest(t.GetStart()) and c2.HitTest(t.GetEnd()) for t in keep):
    t = pcbnew.PCB_TRACK(b); t.SetStart(l1.GetPosition()); t.SetEnd(c2.GetPosition()); t.SetWidth(MM(0.17)); t.SetLayer(pcbnew.F_Cu)
    t.SetNet(b.FindNet("ANT_FEED")); t.SetLocked(True); b.Add(t)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
print("rf patch: removed", gone, "tracks, L204.1-C215.2 present")
