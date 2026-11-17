#!/usr/bin/env python3
"""Export the chosen radiator (from a run's meta, case frame) to the board frame:
  export/AE1_<tag>.json       polygons (F.Cu / B.Cu), vias, feed and short points, copper-free region per layer, placement
  export/AE1_<tag>.kicad_mod  KiCad footprint for AE1 (pins FEED, GND as in v3/design/src/mcu_rf.py)
Board frame = case - 1.5 (X right, Y up, viewed from the sky = F.Cu).  Footprint origin = board (0, 0); place AE1 at
board (0, 0), rotation 0, front side: KiCad page (100.0, 130.0) with the layout lane's KICAD_ORIGIN (KiCad Y down).
The feed leg is extended to the keep-out edge (board Y 3.0), where the CPWG from L204 / C215 joins it.
usage: python export_ae1.py runs/<tag>_body_f_meta.json <name>
"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "common")); sys.dont_write_bytecode = True
from shapely import wkt
from shapely.geometry import box as sbox, Polygon
from shapely.ops import unary_union
from shapely.affinity import translate
import scene_v3f as S

meta = json.load(open(sys.argv[1])); name = sys.argv[2]
B = lambda g: translate(g, -1.5, -1.5)
cand = meta["cand"]; port = meta["port"]
fcu = wkt.loads(meta["copper_F_wkt"])
feed_ext = sbox(port["x0"], port["y_gap0"] - 0.25, port["x1"], port["y_gap1"])      # leg to the keep-out edge
fcu = B(unary_union([fcu, feed_ext]))
bcu = B(wkt.loads(meta["copper_B_wkt"])) if meta.get("copper_B_wkt") else None
vias = [(round(x - 1.5, 4), round(y - 1.5, 4)) for x, y in meta.get("vias", [])]
ko = S.board_region_inset(0.0).intersection(sbox(*S.KO))
ko_b = B(ko)
feed_pt = (round((port["x0"] + port["x1"]) / 2 - 1.5, 4), round(port["y_gap1"] - 1.5, 4))
short = None
if cand["kind"] == "loop":
    sh = S.radiator(S.Cand(**{k: v for k, v in cand.items()}))["short"]
    short = B(sh)
gnd_pad = short if short is not None else sbox(feed_pt[0] + 0.75, 3.0, feed_pt[0] + 1.25, 3.25)   # pin GND (in the pour)

def rings(g):
    return [[(round(x, 4), round(y, 4)) for x, y in list(p.exterior.coords)[:-1]] for p in (g.geoms if hasattr(g, "geoms") else [g])]

J = dict(name=name, frame="board frame (mm): origin = board bottom-left corner, X along the forearm (X 0 = elbow end), Y 0 = "
         "antenna / root-B edge, viewed from the sky (F.Cu). KiCad: page = (100 + X, 130 - Y)",
         source_run=os.path.basename(sys.argv[1]), candidate=cand,
         copper={"F.Cu": rings(fcu), "B.Cu": rings(bcu) if bcu is not None else []},
         vias=[dict(at=v, drill=0.2, pad=0.4, net="FEED", note="filled / tented, B.Cu to F.Cu") for v in vias],
         feed_point=dict(at=feed_pt, layer="F.Cu", note="CPWG (W 0.170 / gap 0.150 on L1 over L2) from L204 / C215 joins the "
                         "feed leg here, at the keep-out edge, running in -Y"),
         short_point=(dict(at=[round(v, 4) for v in short.centroid.coords[0]], poly=rings(short),
                           note="stub into the GND copper at the X 5.0 keep-out edge; >= 2 GND vias 0.2/0.4 within 0.6 mm of it "
                                "outside the keep-out, all layers") if short is not None else None),
         copper_free={"all 6 layers (F.Cu, In1..In4, B.Cu)": rings(ko_b), "except": "the radiator copper above (F.Cu, and B.Cu "
                      "if listed) and its vias; no tracks, vias, pours, parts or fiducials inside; L2 ground edge = keep-out edge "
                      "(no ground under the radiator on any layer)"},
         layout_rules=["AE1 at board (0, 0), rot 0, front; the footprint carries the keep-out as a rule area on all copper layers",
                       "ground edges of the pocket (Y 3.0 for X 0.26-5.0 and X 5.0 for Y 0-3.0) solid on ALL layers and stitched "
                       "with GND vias 0.2/0.4 at <= 1.0 mm pitch along both edges, 0.3-0.5 mm back from the edge",
                       "pi-net: L204 / C215 / C213 within 2 mm of the feed point; their CPWG to the feed point as short as possible "
                       "(the match values assume l_b given in rf_results.json)",
                       "copper to the routed board edge >= 0.30 mm (as modelled)"],
         area_mm2=dict(F=round(fcu.area, 3), B=round(bcu.area, 3) if bcu is not None else 0.0, keepout=round(ko_b.area, 3)))
os.makedirs(os.path.join(HERE, "export"), exist_ok=True)
json.dump(J, open(os.path.join(HERE, "export", f"AE1_{name}.json"), "w"), indent=1)

# ------------------------------------------------------------------ KiCad footprint (local = (x, -y))
L = lambda p: f"(xy {p[0]:.4f} {-p[1]:.4f})"
def gr_poly(r, layer=None):
    return "(gr_poly (pts " + " ".join(L(p) for p in r) + ") (width 0) (fill yes))"
out = [f'(footprint "AE1_{name}" (version 20240108) (generator "v3_sim_rf_export") (layer "F.Cu")',
       f'  (descr "V3-F gate 3a printed radiator {name} in the 5 x 3 mm AE1 keep-out; origin = board (0,0); see v3/sim/rf/RF.md")',
       '  (attr smd board_only exclude_from_pos_files exclude_from_bom)',
       '  (property "Reference" "AE1" (at 2.5 -4.0 0) (layer "F.SilkS") (hide yes) (effects (font (size 0.5 0.5) (thickness 0.08))))',
       f'  (property "Value" "{name}" (at 2.5 1.0 0) (layer "F.Fab") (effects (font (size 0.5 0.5) (thickness 0.08))))']
def custom_pad(num, g, layer, anchor):
    s = []
    for r in rings(g):
        s.append(f'  (pad "{num}" smd custom (at {anchor[0]:.4f} {-anchor[1]:.4f}) (size 0.2 0.2) (layers "{layer}") '
                 f'(options (clearance outline) (anchor rect)) (primitives '
                 + "(gr_poly (pts " + " ".join(f"(xy {x - anchor[0]:.4f} {-(y - anchor[1]):.4f})" for x, y in r) + ") (width 0) (fill yes))))")
    return s
fa = (feed_pt[0], feed_pt[1] - 0.1)
out += custom_pad("FEED", fcu, "F.Cu", fa)
if bcu is not None:
    ba = bcu.representative_point().coords[0]
    out += custom_pad("FEED", bcu, "B.Cu", ba)
for (x, y) in vias:
    out.append(f'  (pad "FEED" thru_hole circle (at {x:.4f} {-y:.4f}) (size 0.4 0.4) (drill 0.2) (layers "*.Cu"))')
ga = gnd_pad.representative_point().coords[0]
out += custom_pad("GND", gnd_pad, "F.Cu", ga)
kr = rings(ko_b)[0]
out.append('  (zone (net 0) (net_name "") (layers "F&B.Cu" "In1.Cu" "In2.Cu" "In3.Cu" "In4.Cu") (name "AE1_keepout") (hatch edge 0.5) '
           '(connect_pads (clearance 0)) (min_thickness 0.25) (filled_areas_thickness no) '
           '(keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints not_allowed)) '
           '(fill (thermal_gap 0.5) (thermal_bridge_width 0.5)) (polygon (pts ' + " ".join(L(p) for p in kr) + ")))")
out.append('  (fp_poly (pts ' + " ".join(L(p) for p in kr) + ') (stroke (width 0.05) (type solid)) (fill no) (layer "F.Fab"))')
out.append('  (fp_poly (pts ' + " ".join(L(p) for p in kr) + ') (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))')
out.append(")")
open(os.path.join(HERE, "export", f"AE1_{name}.kicad_mod"), "w").write("\n".join(out) + "\n")
print(json.dumps(J["area_mm2"]), feed_pt, "vias", vias)
