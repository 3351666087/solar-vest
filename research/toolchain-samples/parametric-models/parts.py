"""Parametric placeholders for parts with no vendor CAD. Every dimension is a named parameter so
the real measured value (calipers / nameplate) replaces it in one place."""
from build123d import *
import glob

def lipo(L=50, W=34, T=5.2, pcm=6):                       # 523450: 5.2 x 34 x 50 mm pouch + PCM fold
    cell = fillet(Box(W, L, T).edges().filter_by(Axis.Y), radius=T*0.45)
    tab = Pos(0, L/2 + pcm/2, 0) * Box(W*0.8, pcm, T*0.8)
    return cell + tab

def supercap(D=10, H=30, lead=3.5, pitch=5):              # 2.7 V 10 F radial can (typ. 10x30 or 12.5x20 mm)
    can = Cylinder(D/2, H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    leads = [Pos(x, 0, -lead) * Cylinder(0.3, lead, align=(Align.CENTER, Align.CENTER, Align.MIN)) for x in (-pitch/2, pitch/2)]
    return can + leads[0] + leads[1]

def panel(L=220, W=175, T=3.0, jbox=(40, 30, 10)):        # 6 V 6 W rigid panel: placeholder until nameplate
    p = Box(L, W, T)
    jb = Pos(0, -W/2 + 30, -T/2 - jbox[2]/2) * Box(*jbox)
    return p + jb

def module(L, W, T=1.6, comp_h=4):                        # generic breakout module (CN3791 / INA226 boards)
    return Box(L, W, T) + Pos(0, 0, T/2 + comp_h/2) * Box(L*0.5, W*0.5, comp_h)

xiao = import_step(glob.glob("xiao/*.step")[0])
ina = import_step(glob.glob("lib/sw.3dshapes/MSOP-10*.step")[0])
parts = {"lipo_523450": lipo(), "supercap_10F": supercap(), "panel_6V6W": panel(),
         "cn3791_module": module(45, 20), "ina226_module": module(25, 20)}
for k, v in parts.items():
    export_step(v, f"out/{k}.step"); bb = v.bounding_box()
    print(f"{k:15s} bbox {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:5.1f} mm")
bb = xiao.bounding_box(); print(f"{'xiao (vendor)':15s} bbox {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:5.1f} mm")
bb = ina.bounding_box(); print(f"{'INA226 (LCSC)':15s} bbox {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:5.1f} mm")
# mini assembly: back unit (panel + battery + charger + XIAO) -> STEP + GLB for the web viewer
asm = Compound(children=[
    parts["panel_6V6W"],
    Pos(-40, 10, -20) * parts["lipo_523450"],
    Pos(40, 10, -16) * parts["cn3791_module"],
    Pos(40, -25, -16) * Rot(-90, 0, 0) * xiao,   # vendor STEP is Y-up: lay it flat
])
export_step(asm, "out/back_unit_demo.step"); export_gltf(asm, "out/back_unit_demo.glb", binary=True)
print("assembly ok")
