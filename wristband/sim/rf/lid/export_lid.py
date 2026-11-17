#!/usr/bin/env python3
"""Export of the lid antenna L1x as built (scene_lid feed 'bw0019'):
  export/AE1_lid_L1.json        board side (board frame = case - 1.5): keep-out, FEED copper (feed leg + spring land), feed point,
                                spring J40 placement; lid side (case frame): strip, jog, contact pad, frame cut-back
  export/AE1_lid_L1.kicad_mod   AE1 footprint: FEED custom pad on F.Cu (leg + land), rule area on all 6 copper layers,
                                F.Fab outline of the spring body and its contact point (the spring J40 is a separate part)
usage: python export_lid.py"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common")); sys.path.insert(0, HERE); sys.dont_write_bytecode = True
from shapely.geometry import box as sbox, Point
from shapely.ops import unary_union
from shapely.affinity import translate, rotate
import scene_v3f as S, scene_lid as SL

B = lambda g: translate(g, -1.5, -1.5)
bp = lambda p: (round(p[0] - 1.5, 4), round(p[1] - 1.5, 4))
o = dict(SL.NOM, feed="bw0019")
land = SL.bw_land()
leg = unary_union([land, sbox(SL.FX0, 3.5, SL.FX1, S.G_EDGE_Y), sbox(SL.FX0, 3.5, 4.75, 3.875)]).simplify(1e-9)
body = translate(rotate(unary_union([sbox(-2.43, -0.5, 1.05, 0.5), sbox(-1.05, -0.75, 1.05, 0.75)]), SL.BW["rot"], origin=(0, 0)), *SL.BW["c"])
ko = S.board_region_inset(0.0).intersection(sbox(*S.KO))
assert S.board_region_inset(0.3).contains(leg.difference(sbox(0, S.G_EDGE_Y - 0.3, 50, 50))) and ko.buffer(1e-6).contains(body)
lid = SL.lid_poly(o)
feed_pt = bp(((SL.FX0 + SL.FX1) / 2, S.G_EDGE_Y))
ct = SL.BW["ct"]; ct180 = (round(2 * SL.BW["c"][0] - ct[0], 3), round(2 * SL.BW["c"][1] - ct[1], 3))


def rings(g):
    return [[(round(x, 4), round(y, 4)) for x, y in list(p.exterior.coords)[:-1]] for p in (g.geoms if hasattr(g, "geoms") else [g])]


J = dict(name="AE1_lid_L1", date="2026-11-15",
         frames="board frame = case frame - 1.5 mm (X, Y), viewed from the sky; KiCad page = (100 + X, 130 - Y)",
         board=dict(
             feed_point=dict(at_board=feed_pt, layer="F.Cu", note="CPWG from the pi-net (C215 antenna-side pad within 0.5 mm, LEAD_NOTES A-2) "
                             "joins the FEED copper here, at the Y 3.0 keep-out edge"),
             FEED_copper_F={"board": rings(B(leg)), "area_mm2": round(leg.area, 3),
                            "note": "F.Cu only: feed leg X 2.5-3.0 from Y 3.0 down to Y 2.0, joined to the spring land; no via, nothing on B.Cu"},
             spring_land=dict(part="J40 (new ref) BAT WIRELESS BW0019BG-L3.5W1.5H3.8, LCSC C2826516", size_mm=[2.10, 1.50],
                              centre_board=bp(SL.BW["c"]), rotation_deg_ccw_from_sky=SL.BW["rot"],
                              land_board=rings(B(land)), body_courtyard_board=rings(B(body)),
                              contact_point_board=bp(ct), contact_point_if_turned_180_board=bp(ct180),
                              source="land and body outline: JLC/EasyEDA footprint ANT-SMD_L3.5-W1.5-H3.8 of C2826516 (read 2026-11-15); "
                                     "contact point from its side-profile layer (arm apex 0.57 mm from the land centre) - drawing not read"),
             copper_free_all_6_layers={"board": rings(B(ko)), "except": "FEED copper on F.Cu only; no tracks, vias, pours, other parts, "
                                       "fiducials or silk-free-copper in the pocket on any layer"},
             rules=["AE1 at board (0, 0), rot 0, front; its rule area is the keep-out on all 6 copper layers",
                    "J40 land is part of AE1's FEED pad; J40 is placed by JLC on that land (rot 340 deg about board (3.30, 1.55))",
                    "ground edges Y 3.0 (X 0.26-5.0) and X 5.0 (Y 0-3.0) solid on all layers, GND vias <= 1.0 mm pitch, 0.3-0.5 mm back (A-2)",
                    "no part body or copper other than J40 above the pocket; J40 body stays inside the pocket (checked)",
                    "copper >= 0.30 mm from the routed board edge (checked for the FEED copper)"]),
         lid=dict(
             frame="case frame (X along the forearm from the elbow end, Y from the antenna wall), glass inner face Z_case 3.895",
             strip_case=rings(lid), strip_area_mm2=round(lid.area, 3),
             parts="strip 0.5 mm wide Y 1.5-2.0, X 5.125-12.375; jog X 5.125-5.625, Y 2.0-2.375; contact pad X 3.875-5.875, Y 2.375-3.625",
             contact_point_case=ct, contact_if_spring_turned_180_case=ct180,
             open_end_to_frame_mm=round(o["frame_x"] - o["x_end"], 3),
             material="printed silver on the glass inner face (fired silver paste, >= 10 um, sheet resistance <= 5 mOhm/sq) with a "
                      "gold or ENIG-equivalent contact finish on the pad (or LDS on a PC carrier bonded to the glass: same outline); "
                      "the IR-cut coating (T-2) must not cover the pad; the strip sits outside the display window (Y < 5.65)",
             frame_cut_back="stainless window frame removed for X < 13.0 in the long-wall border band (Y 0.5-5.65); the antenna-corner PC "
                            "seat (ant_seat) is extended to X 13.0 (was the 5 mm buffer edge, X 11.38 at Y 0.5); display, film opening "
                            "and rail unchanged"))
os.makedirs(os.path.join(HERE, "export"), exist_ok=True)
json.dump(J, open(os.path.join(HERE, "export", "AE1_lid_L1.json"), "w"), indent=1)

L = lambda p: f"(xy {p[0]:.4f} {-p[1]:.4f})"
out = ['(footprint "AE1_lid_L1" (version 20240108) (generator "v3_sim_rf_lid_export") (layer "F.Cu")',
       '  (descr "V3-F lid antenna L1: feed leg + BW0019BG spring land (J40) in the AE1 keep-out; origin = board (0,0); v3/sim/rf/lid/LID_ANTENNA.md")',
       '  (attr smd board_only exclude_from_pos_files exclude_from_bom)',
       '  (property "Reference" "AE1" (at 2.5 -4.0 0) (layer "F.SilkS") (hide yes) (effects (font (size 0.5 0.5) (thickness 0.08))))',
       '  (property "Value" "lid_L1" (at 2.5 1.0 0) (layer "F.Fab") (effects (font (size 0.5 0.5) (thickness 0.08))))']
lb = B(leg); fa = feed_pt[0], feed_pt[1] - 0.1
for r in rings(lb):
    out.append(f'  (pad "1" smd custom (at {fa[0]:.4f} {-fa[1]:.4f}) (size 0.2 0.2) (layers "F.Cu" "F.Mask") '
               '(options (clearance outline) (anchor rect)) (primitives (gr_poly (pts '
               + " ".join(f"(xy {x - fa[0]:.4f} {-(y - fa[1]):.4f})" for x, y in r) + ") (width 0) (fill yes))))")
gp = sbox(feed_pt[0] + 0.75, 3.0, feed_pt[0] + 1.25, 3.25); ga = gp.centroid.coords[0]   # pin 2 GND: pad in the pour (as RF.md)
out.append(f'  (pad "2" smd rect (at {ga[0]:.4f} {-ga[1]:.4f}) (size 0.5 0.25) (layers "F.Cu"))')
kr = rings(B(ko))[0]
out.append('  (zone (net 0) (net_name "") (layers "F&B.Cu" "In1.Cu" "In2.Cu" "In3.Cu" "In4.Cu") (name "AE1_keepout") (hatch edge 0.5) '
           '(connect_pads (clearance 0)) (min_thickness 0.25) (filled_areas_thickness no) '
           '(keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed)) '
           '(fill (thermal_gap 0.5) (thermal_bridge_width 0.5)) (polygon (pts ' + " ".join(L(p) for p in kr) + ")))")
for lay in ("F.Fab", "F.CrtYd"):
    out.append('  (fp_poly (pts ' + " ".join(L(p) for p in kr) + f') (stroke (width 0.05) (type solid)) (fill no) (layer "{lay}"))')
out.append('  (fp_poly (pts ' + " ".join(L(p) for p in rings(B(body))[0]) + ') (stroke (width 0.05) (type solid)) (fill no) (layer "F.Fab"))')
c = bp(ct)
out.append(f'  (fp_circle (center {c[0]:.4f} {-c[1]:.4f}) (end {c[0] + 0.15:.4f} {-c[1]:.4f}) (stroke (width 0.05) (type solid)) (fill no) (layer "F.Fab"))')
out.append(")")
open(os.path.join(HERE, "export", "AE1_lid_L1.kicad_mod"), "w").write("\n".join(out) + "\n")
print(json.dumps(dict(feed_pt=feed_pt, leg_area=round(leg.area, 3), land_c=bp(SL.BW["c"]), contact=bp(ct), contact180=bp(ct180),
                      lid_area=round(lid.area, 3))))
