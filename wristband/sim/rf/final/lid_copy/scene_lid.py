"""V3-G3a lid antenna L1 (full design). Copied from ../scout_lid/scene_lid.py and extended.
Scene = ../common/scene_v3f.build_scene (unchanged) minus the board radiator, plus:
  * stainless window frame cut back to X FRAME_X (case) in the long-wall border (Y < 5.65); the film opening, display panel,
    rail (GF-LCP to X 11.5, stainless from X 11.5) are untouched.
  * lid strip L1x on the glass inner face (z 3.5 grid, = Z_case win0 3.895): 0.5 mm strip Y 1.5-2.0, X 4.0-X_END, jog X 4.0-4.5
    Y 2.0-2.25, contact pad 1.0 x 1.0 (X 3.75-4.75, Y 2.25-3.25) over the spring.
  * feed spring 0.5 x 0.5 (X 4.0-4.5, Y 2.5-3.0) from the board top (z 1.0) to the strip plane; F.Cu feed leg X 4.0-4.5, Y 2.5 to the gap.
Variants (dict o): x_end, frame_x, dz_lid (strip + pad plane shift, grid 0.25), hand (bool), pins (bool)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "common"))
from shapely.geometry import box as sbox
from shapely.ops import unary_union
import scene_v3f as S
from geom import PEC, PolyZ, Box, Mat

Z_LID = 3.545          # glass inner face (ZC.win0 + DZ)
FX0, FX1 = 4.0, 4.5
SPR_Y = (2.5, 3.0)
BAND_Y = (1.5, 2.0)
PAD = (3.75, 2.25, 4.75, 3.25)
FRAME_Y1 = 5.65        # film opening (Y 5.75) - 0.1: the long-wall border band of the frame ends here
NOM = dict(x_end=12.375, frame_x=13.0, dz_lid=0.0, hand=False, pins=False, feed="ideal")
# as-built feed "bw0019": BAT WIRELESS BW0019BG-L3.5W1.5H3.8 (C2826516) land 2.10 x 1.50 (EasyEDA footprint of C2826516), rotated 340 deg,
# land centre case (4.80, 3.05); contact (arm apex, +0.57 mm along the axis) case (5.34, 2.86) -> column X 5.125-5.625, Y 2.625-3.125.
BW = dict(rot=340.0, c=(4.80, 3.05), ct=(5.34, 2.86), col=(5.125, 2.625, 5.625, 3.125), pad=(3.875, 2.375, 5.875, 3.625), strip_x0=5.125)   # pad covers the contact also after a 180 deg turn (4.26, 3.25)


# [rf final 2026-11-17] as-built feed "asbuilt": J40 moved (+0.38, -0.12) mm (LAYOUT N-5): land centre case (5.18, 2.93), contact case (5.72, 2.74)
# (cad/board_zones.json J40_land) -> column X 5.47-5.97, Y 2.49-2.99; board feed copper = AE1 pad 1 of the closed board (case frame); lid print unchanged.
ASB_LEG = [(4.5, 3.976), (6.4232, 3.2756), (5.9102, 1.8661), (3.9368, 2.5844), (4.0, 2.757), (4.0, 4.5), (4.5, 4.5)]
ASB_COL = (5.47, 2.49, 5.97, 2.99)


def bw_land():
    from shapely import affinity
    return affinity.translate(affinity.rotate(sbox(-1.05, -0.75, 1.05, 0.75), BW["rot"], origin=(0, 0)), *BW["c"])
SKIN = S.SKIN; MUSCLE = S.MUSCLE


def lid_poly(o):
    if o.get("feed") in ("bw0019", "asbuilt"):
        x0, y0, x1, y1 = BW["col"]
        return unary_union([sbox(BW["strip_x0"], BAND_Y[0], o["x_end"], BAND_Y[1]), sbox(x0, BAND_Y[1], x1, BW["pad"][1]), sbox(*BW["pad"])]).simplify(1e-9)
    return unary_union([sbox(FX0, BAND_Y[0], o["x_end"], BAND_Y[1]), sbox(FX0, BAND_Y[1], FX1, PAD[1]), sbox(*PAD)]).simplify(1e-9)


def build(o, v, snap, gap):
    sy, sz = snap
    prims, port, ant = S.build_scene(S.Cand(), v, snap)
    prims = [p for p in prims if p.tag not in ("ant_F", "ant_B", "ant_via")]
    cut = sbox(-1.0, -1.0, o["frame_x"], FRAME_Y1)
    out = []
    for p in prims:
        if p.tag == "window_frame":
            q = p.poly.difference(cut)
            if q.area > 1e-9:
                out.append(PolyZ(q, p.z0, p.z1, p.mat, p.tag))
        else:
            out.append(p)
    prims = out
    zl = sz(Z_LID + o["dz_lid"])
    if o["hand"]:      # hand resting on the lid: skin 1.5 + muscle 10.5, X -6..47, Y -10..44, from the lid top (z 4.245 -> grid)
        z0 = sz(4.245)
        diel = [Box((-6.0, -10.0, z0), (47.0, 44.0, z0 + 12.0), MUSCLE, "hand_muscle"),
                Box((-6.0, -10.0, z0), (47.0, 44.0, z0 + 1.5), SKIN, "hand_skin")]
        prims = diel[:1] + diel[1:] + prims      # lowest precedence: no pod / strap / capsule part is overwritten
    lidp = lid_poly(o)
    if o.get("feed") == "asbuilt":
        from shapely.geometry import Polygon
        legp = Polygon(ASB_LEG).intersection(sbox(0, 0, 20, S.G_EDGE_Y - gap)).simplify(1e-9)
        prims.append(PolyZ(legp, S.BOARD_T, S.BOARD_T, PEC, "feed_leg_F"))
        prims.append(Box((ASB_COL[0], ASB_COL[1], S.BOARD_T), (ASB_COL[2], ASB_COL[3], zl), PEC, "spring_feed"))
    elif o.get("feed") == "bw0019":
        land = bw_land()
        legp = unary_union([land, sbox(FX0, 3.5, FX1, S.G_EDGE_Y - gap), sbox(FX0, 3.5, 4.75, 3.875)]).simplify(1e-9)
        x0, y0, x1, y1 = BW["col"]
        prims.append(PolyZ(legp, S.BOARD_T, S.BOARD_T, PEC, "feed_leg_F"))
        prims.append(Box((x0, y0, S.BOARD_T), (x1, y1, zl), PEC, "spring_feed"))
    else:
        legp = sbox(FX0, SPR_Y[0], FX1, S.G_EDGE_Y - gap)
        prims.append(PolyZ(legp, S.BOARD_T, S.BOARD_T, PEC, "feed_leg_F"))
        prims.append(Box((FX0, SPR_Y[0], S.BOARD_T), (FX1, SPR_Y[1], zl), PEC, "spring_feed"))
    prims.append(PolyZ(lidp, zl, zl, PEC, "lid_strip"))
    if o["pins"]:      # stainless strap-bar pins d 0.8 (model_v3f bar_B_ss / bar_A_ss): X 3..38, Y -1.5 / 35.5, Z_case 0.85 -> z 0.5
        L = S.G.LUG
        for yc, tag in ((-L["w"] + 1.0, "bar_B_ss"), (S.G.POD_W + L["w"] - 1.0, "bar_A_ss")):
            prims.append(Box((L["x0"], yc - 0.5, 0.125), (L["x1"], yc + 0.5, 0.875), PEC, tag))
    port = dict(x0=FX0, x1=FX1, y_gap0=S.G_EDGE_Y - gap, y_gap1=S.G_EDGE_Y, z=S.BOARD_T)
    info = dict(opts=o, z_lid=zl, lid_area_mm2=round(lidp.area, 3), lid_bounds=lidp.bounds, lid_wkt=lidp.wkt, leg_wkt=legp.wkt,
                frame_cut=cut.bounds, gap_end_to_frame_mm=round(o["frame_x"] - o["x_end"], 3))
    return prims, port, info
