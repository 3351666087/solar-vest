import pcbnew, os
FP = os.path.expanduser("~/Applications/KiCad/KiCad/KiCad/KiCad.app/Contents/SharedSupport/footprints/")
b = pcbnew.BOARD()
f = pcbnew.FootprintLoad(FP + "Connector_PinSocket_2.54mm.pretty", "PinSocket_1x07_P2.54mm_Vertical"); b.Add(f)
f.SetPosition(pcbnew.VECTOR2I_MM(100, 100)); f.SetOrientationDegrees(270)
for p in list(f.Pads())[:3]: print("rot270 pad", p.GetNumber(), pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y))
f.SetOrientationDegrees(90)
for p in list(f.Pads())[:3]: print("rot90 pad", p.GetNumber(), pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y))
print([x for x in dir(pcbnew) if "Specctra" in x])
