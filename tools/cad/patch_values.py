"""Change component values / LCSC numbers on an already-routed board (footprints unchanged, routing kept).
usage: kicad-python patch_values.py <board> REF=value,LCSC ..."""
import sys, pcbnew
brd = pcbnew.LoadBoard(sys.argv[1])
for arg in sys.argv[2:]:
    ref, rest = arg.split("="); val, lcsc = rest.split(",")
    f = brd.FindFootprintByReference(ref); assert f, ref
    old = f.GetValue(); f.SetValue(val)
    for fld in f.GetFields():
        if fld.GetName() == "LCSC": fld.SetText(lcsc)
    print(f"{ref}: {old} -> {val} ({lcsc}) footprint {f.GetFPIDAsString()}")
brd.Save(sys.argv[1])
