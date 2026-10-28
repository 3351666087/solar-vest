"""3D models missing from the KiCad library, built in footprint coordinates (mm, KiCad: +y = down on the board;
STEP uses the same X, Y flipped by KiCad when it loads models, so we model with Y up = board -y)."""
from build123d import *
OUT = "lib/hw.3dshapes/"
def jst_ph_sm(n):
    w = (n - 1) * 2.0 + 3.9; y_rear, y_front, h = 4.4, -3.6, 4.75        # KiCad pads at y=-2.85 (rear) → model y=+2.85
    body = Pos(0, (y_rear + y_front) / 2, h / 2) * Box(w, y_rear - y_front, h)
    body -= Pos(0, y_front + 2.5, 1.0 + 1.6) * Box(w - 1.2, 5.0, 3.2)  # mating cavity opening at the front
    pins = [Pos(-(n - 1) + 2.0 * i, 3.6, 0.15) * Box(0.6, 2.0, 0.3) for i in range(n)]
    tabs = [Pos(s * (w / 2 + 0.5), -2.9, 0.6) * Box(1.0, 3.0, 1.2) for s in (-1, 1)]
    c = Compound(children=[body] + pins + tabs)
    body.color = Color(0.95, 0.95, 0.92)
    for p in pins + tabs: p.color = Color(0.8, 0.8, 0.8)
    return c
def pptc_1812():
    b = Pos(0, 0, 0.55) * Box(4.5, 3.2, 1.1); b.color = Color(0.85, 0.75, 0.3); return b
def supercap_flat():
    L, D, gap = 25.0, 10.0, 2.5
    body = Pos(-gap - L / 2, 0, D / 2) * Rot(0, 90, 0) * Cylinder(D / 2, L); body.color = Color(0.12, 0.13, 0.30)
    leads = []
    for y in (2.5, -2.5):
        leads.append(Pos(-gap / 2, y, D / 2) * Rot(0, 90, 0) * Cylinder(0.3, gap))
        leads.append(Pos(0, y, D / 4) * Cylinder(0.3, D / 2 + 1.6, align=(Align.CENTER, Align.CENTER, Align.CENTER)))
    for l in leads: l.color = Color(0.7, 0.7, 0.7)
    return Compound(children=[body] + leads)
for name, shape in (("JST_PH_S2B-PH-SM4-TB", jst_ph_sm(2)), ("JST_PH_S5B-PH-SM4-TB", jst_ph_sm(5)),
                    ("Fuse_1812_4532Metric", pptc_1812()), ("SuperCap_D10_L25_Flat", supercap_flat())):
    export_step(shape, OUT + name + ".step"); print(name, shape.bounding_box().size)
