"""6 V / 6 W framed panel — dimensions from the user's photos (no calipers).

source of each number (photos 2026-10-08, bank card 85.60 x 53.98 mm as scale, tape measure in photo 6):
  length 261.8 mm    tape measure laid on the frame edge (5.95 px/mm), both frame ends visible
  width  171 mm      length / aspect ratio 1.531 (photos 3 and 5 agree within 0.6 %); card-scale check after
                     height correction gives 170.5 mm
  frame depth ~15 mm tape reading across the frame edge (13-17 mm along the bar because of perspective)
  cells  12 = 2 x 6, each ~67.4 x 32.4 mm (dark-pixel segmentation, photo 3)
  junction box ~38 x 48 mm, centred across the width, centre ~20 % of the length from the cable end,
               recessed inside the frame depth (photo 6 shows it does not protrude)
accuracy: about ±2 mm on outline, ±2 mm on depth — every interface around it is designed with ≥3 mm play.
"""
from build123d import *
L, W, D = 261.8, 171.0, 15.0
FRAME_LIP, FRAME_WALL, GLASS = 6.0, 1.2, 3.2
CELL = (67.4, 32.4); COLS, ROWS = 2, 6; GAP_C, PITCH_R = 2.8, 36.0
MARGIN_TOP = 22.5
JB = dict(w=38.0, l=48.0, h=11.0, y_frac=0.20)
ALU, GLASSC, CELLC, BACK, BLACK = Color(0.78, 0.79, 0.80), Color(0.85, 0.90, 0.95, 0.35), Color(0.06, 0.07, 0.12), Color(0.93, 0.93, 0.93), Color(0.08, 0.08, 0.08)
def tag(s, n, c): s.label = n; s.color = c; return s
outer = Box(W, L, D, align=(Align.CENTER, Align.CENTER, Align.MIN))
frame = outer - Pos(0, 0, -1) * Box(W - 2*FRAME_LIP, L - 2*FRAME_LIP, D + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
frame -= Pos(0, 0, FRAME_WALL) * Box(W - 2*FRAME_WALL, L - 2*FRAME_WALL, D - 2*FRAME_WALL, align=(Align.CENTER, Align.CENTER, Align.MIN))
glass = Pos(0, 0, D - FRAME_WALL - GLASS) * Box(W - 2*FRAME_WALL, L - 2*FRAME_WALL, GLASS, align=(Align.CENTER, Align.CENTER, Align.MIN))
backsheet = Pos(0, 0, D - FRAME_WALL - GLASS - 1.0) * Box(W - 2*FRAME_WALL, L - 2*FRAME_WALL, 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
cells = []
for r in range(ROWS):
    for c in range(COLS):
        x = (c - 0.5) * (CELL[0] + GAP_C); y = L/2 - MARGIN_TOP - CELL[1]/2 - r*PITCH_R
        cells.append(Pos(x, y, D - FRAME_WALL - GLASS - 0.05) * Box(CELL[0], CELL[1], 0.3, align=(Align.CENTER, Align.CENTER, Align.MIN)))
jb_y = L/2 - JB["y_frac"]*L
jbox = Pos(0, jb_y, D - FRAME_WALL - GLASS - 1.0 - JB["h"]) * Box(JB["w"], JB["l"], JB["h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
cable = sweep(Pos(0, jb_y - JB["l"]/2, D - FRAME_WALL - GLASS - 1.0 - JB["h"]/2) * (Rot(90, 0, 0) * Circle(2.5)),
              path=Polyline((0, jb_y - JB["l"]/2, D - FRAME_WALL - GLASS - 1.0 - JB["h"]/2), (0, jb_y - JB["l"]/2 - 30, 5), (W/2 + 40, jb_y - 60, 5)))
panel = Compound(children=[tag(frame, "frame", ALU), tag(backsheet, "backsheet", BACK), tag(Compound(children=cells), "cells_2x6", CELLC),
                           tag(glass, "glass", GLASSC), tag(jbox, "junction_box", BLACK), tag(cable, "cable", BLACK)], label="panel_6V6W_photo")
cap = Compound(children=[tag(Cylinder(5.0, 25.0, align=(Align.CENTER, Align.CENTER, Align.MIN)), "supercap_body", Color(0.12, 0.13, 0.30)),
                         tag(Pos(-2.5, 0, -4) * Cylinder(0.3, 4, align=(Align.CENTER, Align.CENTER, Align.MIN)), "lead_neg", Color(0.7, 0.7, 0.7)),
                         tag(Pos(2.5, 0, -4) * Cylinder(0.3, 4, align=(Align.CENTER, Align.CENTER, Align.MIN)), "lead_pos", Color(0.7, 0.7, 0.7))], label="supercap_10F_10x25")
for n, s in (("panel_6V6W_photo", panel), ("supercap_10F_10x25", cap)):
    b = s.bounding_box(); print(f"{n}: {b.size.X:.1f} x {b.size.Y:.1f} x {b.size.Z:.1f} mm"); export_step(s, n + ".step"); export_gltf(s, n + ".glb", binary=True)
