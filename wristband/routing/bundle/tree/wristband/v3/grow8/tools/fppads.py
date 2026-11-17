"""Print every pad (number, x, y, size, shape) of the given footprints, KiCad footprint frame (y down)."""
import sys, pcbnew
LIB = "@SVROOT@/wristband/design/lib/easyeda_rev.pretty"
for name in sys.argv[1:]:
    f = pcbnew.FootprintLoad(LIB, name)
    print("==", name)
    for p in f.Pads():
        s = p.GetSize(pcbnew.F_Cu) if hasattr(p, "GetSize") else None
        try: s = p.GetSize()
        except TypeError: s = p.GetSize(pcbnew.F_Cu)
        print(f"  {p.GetNumber():>4} {pcbnew.ToMM(p.GetPosition().x):7.3f} {pcbnew.ToMM(p.GetPosition().y):7.3f}  {pcbnew.ToMM(s.x):.3f}x{pcbnew.ToMM(s.y):.3f} sh{p.GetShape()} ang{p.GetOrientationDegrees():.0f} attr{p.GetAttribute()}")
