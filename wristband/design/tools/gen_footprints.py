"""Custom copper-only footprints (not JLC-placed) for the main board (lib/solarband.pretty) and the PV-board
footprints drawn from the ANYSOLAR datasheet drawings (lib/pv.pretty). Units mm, KiCad footprint frame (y down).
"""
import os, uuid, json
LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
U = lambda: str(uuid.uuid4())

def prop(name, val, x, y, layer="F.SilkS", hide=False, size=0.8):
    return (f'  (property "{name}" "{val}" (at {x:.3f} {y:.3f} 0) (layer "{layer}"){" (hide yes)" if hide else ""} (uuid "{U()}")\n'
            f'    (effects (font (size {size} {size}) (thickness {size*0.15:.3f}))))\n')

def line(x1, y1, x2, y2, layer="F.SilkS", w=0.15):
    return f'  (fp_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) (stroke (width {w}) (type solid)) (layer "{layer}") (uuid "{U()}"))\n'

def rect(x1, y1, x2, y2, layer, w=0.05):
    return f'  (fp_rect (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) (stroke (width {w}) (type solid)) (fill no) (layer "{layer}") (uuid "{U()}"))\n'

def text(t, x, y, layer="F.SilkS", size=0.8):
    return (f'  (fp_text user "{t}" (at {x:.3f} {y:.3f} 0) (layer "{layer}") (uuid "{U()}")\n'
            f'    (effects (font (size {size} {size}) (thickness {size*0.15:.3f}))))\n')

def pad(num, x, y, w, h, shape="rect", layers=("F.Cu", "F.Mask"), drill=None, mask_margin=None, rr=None):
    kind = "thru_hole" if drill else "smd"
    extra = f" (drill {drill})" if drill else ""
    if rr is not None and shape == "roundrect": extra += f" (roundrect_rratio {rr})"
    if mask_margin is not None: extra += f" (solder_mask_margin {mask_margin})"
    ls = " ".join(f'"{l}"' for l in layers)
    return f'  (pad "{num}" {kind} {shape} (at {x:.3f} {y:.3f}) (size {w:.3f} {h:.3f}){extra} (layers {ls}) (uuid "{U()}"))\n'

def fp(lib, name, descr, body, attr="smd exclude_from_pos_files exclude_from_bom", ref_y=-2.0, val_y=2.0, extra_head=""):
    s = (f'(footprint "{name}" (version 20241229) (generator "solarband_gen_footprints") (layer "F.Cu")\n'
         f'  (descr "{descr}")\n  (attr {attr})\n{extra_head}' + prop("Reference", "REF**", 0, ref_y) + prop("Value", name, 0, val_y, "F.Fab") + body + ")\n")
    d = os.path.join(LIB, lib + ".pretty"); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, name + ".kicad_mod"), "w").write(s)

def court(x1, y1, x2, y2): return rect(x1, y1, x2, y2, "F.CrtYd", 0.05)

# ---------------- main board (copper only) ----------------
fp("solarband", "Pad_Electrode_2.5x2.5mm", "ECG electrode spring landing pad, ENIG, no paste (ARCHITECTURE 6.3)",
   pad("1", 0, 0, 2.5, 2.5) + court(-1.5, -1.5, 1.5, 1.5))
fp("solarband", "Pad_Contact_2.0x2.5mm", "Cradle C+/C- spring contact landing pad, ENIG, no paste",
   pad("1", 0, 0, 2.0, 2.5) + court(-1.25, -1.5, 1.25, 1.5))
fp("solarband", "Pad_Wire_1.5x2.5mm", "Hand-soldered battery lead pad (B+/B-/NTC), place on B.Cu (L6)",
   pad("1", 0, 0, 1.5, 2.5) + court(-1.0, -1.5, 1.0, 1.5))
fp("solarband", "Pad_Wire_1.5x2.0mm", "Hand-soldered PV lead pad (32 AWG), place on B.Cu (L6)",
   pad("1", 0, 0, 1.5, 2.0) + court(-1.0, -1.25, 1.0, 1.25))
names = ["VDD", "GND", "SWDIO", "SWDCLK", "nRESET", "UART_TX", "VSTOR", "VIN_DC", "VLED", "AVDD_ECG"]
b = ""
for i in range(10):     # Integrate: 2 x 5 (adds VLED, AVDD_ECG for the G10 rail check, review_mcu-rf-dfm #4)
    col, row = i % 5, i // 5
    b += pad(str(i + 1), (col - 2.0) * 1.27, (row - 0.5) * 1.27, 0.9, 0.9, shape="circle")
b += court(-3.45, -1.5, 3.45, 1.5) + text("1", -2.54 - 1.0, -0.635, size=0.6)
fp("solarband", "TestPad_2x5_P1.27mm_D0.9mm", "Pogo test/SWD array 2x5, 1.27 mm pitch, place on B.Cu (L6); pad order: " + ",".join(names), b, ref_y=-2.2, val_y=2.2)
fp("solarband", "Fiducial_1.0mm_Mask2.0mm", "Local fiducial, 1.0 mm copper, 2.0 mm mask opening",
   pad("", 0, 0, 1.0, 1.0, shape="circle", layers=("F.Cu", "F.Mask"), mask_margin=0.5) + court(-1.25, -1.25, 1.25, 1.25),
   attr="smd exclude_from_pos_files exclude_from_bom")
fp("solarband", "NetTie_2_SMD_0.3mm", "Net tie (star point), 2 pads joined by copper",
   pad("1", -0.25, 0, 0.3, 0.3, layers=("F.Cu",)) + pad("2", 0.25, 0, 0.3, 0.3, layers=("F.Cu",)) + line(-0.25, 0, 0.25, 0, "F.Cu", 0.3),
   extra_head='  (net_tie_pad_groups "1,2")\n')
fp("solarband", "ANT_IFA_AN043_placeholder",
   "Printed meander IFA B2 (SIM-10, sim/rf/sim10_ifa/export/ifa_L6.dxf) on B.Cu; radiator copper imported from the DXF at layout. Pad 1 FEED (via 0.20/0.40 at board (12.5, 5.95)), pad 2 short-to-GND. Keep-out X 0-15.5 x Y 0-5.5 mm all layers; feed notch X 12.0-13.0 x Y 5.5-6.4 cleared on L3-L6 (L2 solid, 0.60 mm antipad)",
   pad("1", 0, 0, 0.5, 0.5, layers=("B.Cu",)) + pad("2", 1.0, 0, 0.5, 0.5, layers=("B.Cu",)) +
   # frame: origin = feed via; board X right, board Y (ARCHITECTURE 5.4, Y = 0 at the antenna edge) = -KiCad y.
   # Keep-out X 0-15.5 / Y 0-5.5 -> x -12.5..+3.0, y +0.45..+5.95; notch X 12.0-13.0 / Y 5.5-6.4 -> x +-0.5, y -0.45..+0.45.
   # Authority for the copper is sim/rf/sim10_ifa/export/ifa_L6.dxf (layers incl. FEED_NOTCH_L3_L6); this is only a marker.
   rect(-12.5, 0.45, 3.0, 5.95, "Dwgs.User", 0.1) + text("IFA KEEP-OUT 15.5x5.5 ALL LAYERS (SIM-10)", -4.75, 3.2, "Dwgs.User", 0.6) +
   rect(-0.5, -0.45, 0.5, 0.45, "Dwgs.User", 0.05) + text("FEED NOTCH L3-L6", 0, -1.0, "Dwgs.User", 0.4),
   attr="smd exclude_from_pos_files exclude_from_bom")

# ---------------- V2-B copper-only footprints (REDESIGN_V2 rev 1 sections 5.3, 5.5, 5.8; sizes as itemised in v2_calc.py) ----------------
fp("solarband", "Pad_PlateDot_D2.0mm", "Electrode-plate contact pad for one silver-epoxy dot: 2.0 mm round ENIG pad, no paste; place on B.Cu (skin face). "
   "Two per titanium plate on separate nets (dot-loop test). Carrier-film opening 1.6 mm; vias >= 1 mm from the opening (REDESIGN 5.5)",
   pad("1", 0, 0, 2.0, 2.0, shape="circle") + court(-1.25, -1.25, 1.25, 1.25))
fp("solarband", "Pad_CellTab_3.0x4.0mm", "Cell tab pad 3.0 x 4.0 mm, ENIG, hand-soldered tab (bare cell, heat clamp); sky side at the cell-bay end",
   pad("1", 0, 0, 3.0, 4.0) + court(-1.75, -2.25, 1.75, 2.25))
fp("solarband", "Pad_Wire_1.5x2.2mm", "Hand-soldered lead pad 1.5 x 2.2 mm for the NTC bead leads; sky side",
   pad("1", 0, 0, 1.5, 2.2) + court(-1.0, -1.35, 1.0, 1.35))
b = "".join(pad(str(i + 1), (i - 1) * 2.0, 0, 1.2, 3.0) for i in range(3))
b += court(-2.85, -1.75, 2.85, 1.75) + text("PV+", -2.0, -2.2, size=0.5) + text("PV-", 0, -2.2, size=0.5) + text("BS", 2.0, -2.2, size=0.5)
fp("solarband", "Pad_LidTail_3x1.2x3.0_P2.0mm", "Land for the lid module's flex tail: 3 pads 1.2 x 3.0 mm, pitch 2.0 mm: 1 PV+, 2 PV-, 3 backsheet ground; hand-soldered; sky side", b, ref_y=-3.2, val_y=3.2)
fp("solarband", "TestPad_D1.0mm", "EOL-1 test pad, 1.0 mm round, ENIG, no paste; sky side", pad("1", 0, 0, 1.0, 1.0, shape="circle") + court(-0.9, -0.9, 0.9, 0.9))
names6 = ["VDD", "GND", "SWDIO", "SWDCLK", "nRESET", "UART_TX"]
b = ""
for i in range(6):
    col, row = i % 3, i // 3
    b += pad(str(i + 1), (col - 1.0) * 1.27, (row - 0.5) * 1.27, 0.9, 0.9, shape="circle")
b += court(-2.2, -1.5, 2.2, 1.5) + text("1", -1.27 - 1.0, -0.635, size=0.6)
fp("solarband", "TestPad_2x3_P1.27mm_D0.9mm", "Sky-side SWD / reset pad group 2x3, 1.27 mm pitch; pad order: " + ",".join(names6), b, ref_y=-2.2, val_y=2.2)
fp("solarband", "ANT_PRINTED_V2_placeholder",
   "Printed 2.4 GHz radiator of V2-B (geometry, layer and keep-out come from gate 3a, SIM-10/11 in the V2-B stack; nothing is frozen here). "
   "Pad 1 FEED, pad 2 short-to-GND. Marker only: no copper outline, no keep-out drawn",
   pad("1", 0, 0, 0.5, 0.5, layers=("F.Cu",)) + pad("2", 1.0, 0, 0.5, 0.5, layers=("F.Cu",)) + text("PRINTED RADIATOR (gate 3a)", 0.5, -1.0, "Dwgs.User", 0.4),
   attr="smd exclude_from_pos_files exclude_from_bom")

# The v1 PV-board footprints (lib/pv.pretty) are not regenerated: V2-B has no PV board (the laminated lid module replaces it).
print("V2-B copper-only footprints written to", os.path.join(LIB, "solarband.pretty"))

# ---------------- V3-F copper-only footprints (v3/decide/BASELINE.md 5.1, 7, 16) ----------------
fp("solarband", "Pad_RootEntry_1.0x4.0mm", "Strap entry land: one pad per strap conductor (root A BATT_P | GND | NTC | GND, root B PV_W+ | GND), 1.0 x 4.0 mm "
   "(4.0 mm2 copper), placed at 1.5 mm pitch: gap 0.5 mm (BASELINE 4: conductors >= 0.5 mm apart); four lands span 5.5 mm and fit X 4.5-10.5 (BASELINE 1). "
   "[V3F] BASELINE 5.1 planned 6 mm2 per pad: a 1.5 mm wide pad would need 7.5 mm for four. Hand-soldered 1-layer flex; sky side at the root wall",
   pad("1", 0, 0, 1.0, 4.0) + court(-0.75, -2.25, 0.75, 2.25))
b = "".join(pad(str(i + 1), (i - 4.5) * 0.5, 0, 0.3, 1.6) for i in range(10))
b += pad("11", 3.2, -0.3, 0.6, 1.0)                         # key pad: off the row and off centre, so the FPC fits one way only
b += court(-2.65, -1.05, 3.75, 1.05) + text("1", -2.25, -1.4, size=0.5)
fp("solarband", "FPC_Solder_10P_P0.5mm_Key", "LS011B7DH03 FPC soldered land: 10 pads 0.3 x 1.6 mm at 0.5 mm in the spec's pin order (LD-29Y03 p.14: 1 SCLK ... 10 VSSA) "
   "+ asymmetric key pad 11 (no net) for the stiffener tab; hot-bar or hand solder at final assembly; not JLC-placed", b, ref_y=-1.8, val_y=1.8)
b = pad("1", -0.9, 0, 1.0, 1.4) + pad("2", 0.8, 0, 0.6, 1.4, shape="oval") + court(-1.55, -0.95, 1.25, 0.95) + text("+", -0.9, -1.3, size=0.5)
fp("solarband", "Pad_Tail2_Keyed_FL", "Front-light film tail land: pad 1 (+, LED anode) rectangular 1.0 x 1.4, pad 2 (-) round 0.6 x 1.4: asymmetric, the tail is cut to match; "
   "hand-soldered at final assembly", b, ref_y=-1.6, val_y=1.6)
b = pad("1", -0.8, 0, 1.0, 1.5) + pad("2", 0.8, 0, 1.0, 1.5) + court(-1.45, -0.9, 1.45, 0.9) + text("+", -0.8, -1.3, size=0.5)
fp("solarband", "Pad_Wire2_ERM_1.0x1.5mm", "ERM motor wire pads 2 x 1.0 x 1.5 mm, pitch 1.6 mm, at the edge of the 8.6 mm motor cut-out; polarity sets only the spin direction",
   b, ref_y=-1.6, val_y=1.6)
print("V3-F copper-only footprints written")

# ---------------- Gate-1 level 0 (2026-11-15, v3/g1/dense/DENSE.md section 3): lands trimmed to what their tails need ----------------
# No tail drawing exists yet (the strap flex, the lid flex tail and the display bridge flex are our own custom parts: RFQ items). Assumptions (E):
#   strap tail: one exposed finger per conductor, 0.8 mm wide, 2.0 mm long, lap-soldered (iron or hot bar); <= 0.4 A (F1 hold), no strap pull on the joint
#   (the root moulding carries it). Land = finger + 0.1 mm per side, + 0.25 mm toe and heel fillet -> 1.0 x 2.5 mm; pitch 1.5 mm keeps the 0.5 mm gap of BASELINE 4.
fp("solarband", "Pad_RootEntry_1.0x2.5mm", "Strap entry land (gate-1 level 0): one pad per strap conductor, 1.0 x 2.5 mm (2.5 mm2 copper) for a 0.8 x 2.0 mm exposed flex finger "
   "(assumption: no tail drawing yet), placed at 1.5 mm pitch: gap 0.5 mm (BASELINE 4). Was 1.0 x 4.0 mm. Hand-soldered 1-layer flex; sky side at the root wall",
   pad("1", 0, 0, 1.0, 2.5) + court(-0.75, -1.5, 0.75, 1.5))
#   lid tail: 3 conductors (PV+, PV-, backsheet ground), <= 66 mA; fingers 0.8 x 1.5 mm at 1.5 mm pitch -> lands 1.0 x 2.0 mm, gap 0.5 mm.
b = "".join(pad(str(i + 1), (i - 1) * 1.5, 0, 1.0, 2.0) for i in range(3))
b += court(-2.25, -1.25, 2.25, 1.25) + text("PV+", -1.5, -1.7, size=0.4) + text("PV-", 0, -1.7, size=0.4) + text("BS", 1.5, -1.7, size=0.4)
fp("solarband", "Pad_LidTail_3x1.0x2.0_P1.5mm", "Land for the lid module's flex tail (gate-1 level 0): 3 pads 1.0 x 2.0 mm, pitch 1.5 mm (gap 0.5 mm): 1 PV+, 2 PV-, 3 backsheet ground; "
   "for 0.8 x 1.5 mm exposed fingers (assumption: no tail drawing yet). Was 3 x 1.2 x 3.0 at 2.0 mm. Hand-soldered; sky side", b, ref_y=-2.6, val_y=2.6)
#   display bridge flex (our own part, CAD lane option L1-A): 10 fingers at the panel's terminal pitch 0.5 mm (LD-29Y03 p.42 Detail A: 10 terminals at 0.5 +- 0.03, 0.35 wide,
#   3.5 +- 0.3 long, tail 5.5 +- 0.05 wide). Board end: lands 0.30 x 1.20 mm (1.0 mm overlap + 0.2 mm toe fillet), span 4.8 mm, inside the 5.5 mm tail width. No key pad:
#   the stage-1 key pad at x 3.2 mm lay outside the tail. The flex is one-sided and its two ends differ, so it fits one way only.
b = "".join(pad(str(i + 1), (i - 4.5) * 0.5, 0, 0.3, 1.2) for i in range(10))
b += court(-2.65, -0.85, 2.65, 0.85) + text("1", -2.25, -1.2, size=0.5)
fp("solarband", "FPC_Bridge_10P_P0.5mm", "Display bridge-flex land (gate-1 level 0): 10 pads 0.30 x 1.20 mm at 0.5 mm in the LS011B7DH03 terminal order (LD-29Y03 p.14: 1 SCLK ... 10 VSSA); "
   "hot-bar or hand solder at final assembly; not JLC-placed. Was 10 x 0.3 x 1.6 + a key pad (13.4 mm2)", b, ref_y=-1.6, val_y=1.6)
print("gate-1 level 0 trimmed lands written")

# ---------------- Stage 2c (2026-11-15, v3/stage2c/ECO2C.md): lid antenna L1 ----------------
# AE1 = the RF lane's exported footprint, copied unchanged (feed leg + J40 land = pad 1 FEED, pad 2 GND in the pour, keep-out rule area on all 6 copper layers).
_src = "/path/to/SolarVest_work/wristband/v3/sim/rf/lid/export/AE1_lid_L1.kicad_mod"
open(os.path.join(LIB, "solarband.pretty", "AE1_lid_L1.kicad_mod"), "w").write(open(_src).read())
print("S2c: AE1_lid_L1 copied from v3/sim/rf/lid/export")
