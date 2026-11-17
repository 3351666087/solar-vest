"""SolarBand V3-F (stage 2b, pod 41 x 34, board 38 x 31) RF scene for gate V3-G3a (SIM-10 / SIM-11).

Adapted from v2/gates/g3a/common/scene_v2b.py (copied, not edited).  Geometry is read from the CAD lane's single-source
module v3/cad/src/geom_v3f.py (stage 2b, option L41W34_fold1p9_fpcdwg_jointzif_raise0p15) at import time [CAD].

FRAMES
  X, Y = CASE frame of geom_v3f (X 0..41 along the forearm, X = 0 elbow end; Y 0..34, Y = 0 = root B / antenna wall).
  Board frame = case - 1.5 (KiCad export converts).   z = Z_case - 0.35 (so the nominal 1.0 mm board is z 0..1 as in V2-B,
  and the V2-B z mesh is reused): skin plane / floor skin face z = -0.35, floor film -0.35..-0.10, carrier -0.10..0,
  board 0..1.0 (nominal; CAD carries the 1.10 max-material board), F.Cu = z 1.0, B.Cu = z 0.
Tags: [CAD] geom_v3f value, [V2B] as scene_v2b.py, [GAB] Gabriel 1996, [E] estimate of this lane (listed in RF.md).
"""
import math, os, sys
from dataclasses import dataclass, field
import numpy as np
from shapely.geometry import Polygon, LineString, Point, box as sbox
from shapely.ops import unary_union

from geom import Mat, AIR, PEC, Box, PolyZ, PolyX, EllCylX, IfacePlane

# ------------------------------------------------------------------ CAD geometry (stage 2b, 41 x 34)
os.environ.setdefault("V3F_POD_L", "41"); os.environ.setdefault("V3F_POD_W", "34")
os.environ.setdefault("V3F_OPT", "fpc=dwg,fold=1.9,joint=zif,raise=0.15"); os.environ["V3F_NO_OUT"] = "1"
os.environ.setdefault("V3F_STAGE", "2b")
sys.path.insert(0, "/path/to/SolarVest_work/wristband/v3/cad/src")
import geom_v3f as G   # noqa: E402
assert G.TAG == "L41W34_fold1p9_fpcdwg_jointzif_raise0p15" and G.S2B, G.TAG
ZC = G.Z
DZ = -0.35                                   # z = Z_case + DZ
zc = lambda Zcase: round(Zcase + DZ, 4)

# ------------------------------------------------------------------ materials
FR4 = Mat("fr4_1p0", eps=4.44, tand=0.02)          # [V2B] JLC06101H-3313 thickness-weighted
PC = Mat("pc", eps=3.0, tand=0.01)                 # [V2B]
GLASS = Mat("glass_cs", eps=7.20, tand=0.024)      # [V2B] aluminosilicate class (window 0.70, laminate 0.50)
PANEL_GL = Mat("panel_glass", eps=6.0, tand=0.01)  # [E] memory-LCD glass pair
OCA = Mat("film_oca", eps=3.0, tand=0.01)          # [E] front-light film + OCA
ENCAP = Mat("encapsulant", eps=2.8, tand=0.03)     # [V2B]
LCP = Mat("gf_lcp", eps=4.0, tand=0.005)           # [E] glass-filled LCP rail
ROOT = Mat("tpu_root", eps=3.0, tand=0.03)         # [E] TPU strap root / hinge
CAPS = Mat("capsule", eps=3.5, tand=0.01)          # [E] PC + glass capsule shell (cell inside = PEC)
WINGL = Mat("wing_lam", eps=3.0, tand=0.02)        # [E] wing laminate polymer
SKIN = Mat("skin_dry", eps=38.02, sigma=1.459)     # [GAB] 2.44 GHz
FAT = Mat("fat", eps=5.281, sigma=0.1041)          # [GAB]
MUSCLE = Mat("muscle", eps=52.74, sigma=1.732)     # [GAB]

BOARD_T = 1.0
Z_FLOOR = -0.35
YC = G.POD_W / 2                                   # wrist centre line under the pod centre (Y 17) [E]
KO = (1.5, 1.5, 6.5, 4.5)                          # antenna keep-out, case frame (board 0..5 x 0..3) [CAD ANT_KEEPOUT]
G_EDGE_Y = KO[3]                                   # ground edge (feed side) Y 4.5 case = 3.0 board [zones antenna]
G_EDGE_X = KO[2]                                   # ground edge X 6.5 case = 5.0 board (short side)
ARC_C, ARC_R = (6.0, 6.0), 4.5                     # board corner R4.5 [CAD BOARD]
EDGE_CLR = 0.30                                    # copper to routed edge [E, JLC >= 0.2]
GRID = 0.25                                        # radiator design grid (level c radiator zone = 1 cell)


# ------------------------------------------------------------------ radiator candidates
@dataclass
class Cand:
    """kind 'fill'  : booster block = the keep-out pocket filled on F.Cu and B.Cu (via-stitched), fed by a leg from the
                      Y 4.5 ground edge; open (capacitive) element exciting the board ground mode.
       kind 'loop'  : shorted-arm IFA: 0.5 mm trace along the board corner arc, short into the X 6.5 ground edge at its
                      bottom end, open end at the top-left; feed leg from the Y 4.5 ground edge (inductive element)."""
    kind: str = "fill"
    name: str = "PA"
    fill_ytop: float = 3.5          # top of the fill (1.0 mm below the Y 4.5 ground edge)
    fill_xright: float = 5.75       # right end of the fill / arm region (0.75 from the X 6.5 ground edge)
    feed_x0: float = 4.0            # feed leg X range
    feed_w: float = 0.5
    w: float = 0.5                  # loop trace width
    short_y0: float = 1.75          # loop: short stub Y range (into the X 6.5 edge)
    open_ytop: float = 3.75         # loop: top of the open end
    two_layer: bool = True          # fill: copy on B.Cu + via stitching
    port_gap: float = 0.25


def _cells_in(region, x0, y0, x1, y1, g=GRID):
    """union of the g x g grid cells fully inside region (staircase polygon on the design grid)"""
    cells = []
    for i in range(int(round((x1 - x0) / g))):
        for j in range(int(round((y1 - y0) / g))):
            c = sbox(x0 + i * g, y0 + j * g, x0 + (i + 1) * g, y0 + (j + 1) * g)
            if region.contains(c):
                cells.append(c)
    return unary_union(cells)


def board_region_inset(d=EDGE_CLR):
    return Point(*ARC_C).buffer(ARC_R - d, quad_segs=256).union(sbox(ARC_C[0], KO[1] + d, 50, 50)).union(
        sbox(KO[0] + d, ARC_C[1], 50, 50))


def radiator(c: Cand):
    """copper (case frame) of F.Cu (and B.Cu), vias, feed and short info"""
    reg = board_region_inset()
    gap = c.port_gap
    fx0, fx1 = c.feed_x0, c.feed_x0 + c.feed_w
    if c.kind == "fill":
        top = _cells_in(reg, KO[0], KO[1], c.fill_xright, c.fill_ytop)
        leg = sbox(fx0, c.fill_ytop - GRID, fx1, G_EDGE_Y - gap)
        fcu = unary_union([top, leg])
        bcu = top if c.two_layer else None
        vias = []
        if c.two_layer:     # 0.25 x 0.25 PEC posts at the via centres (drill 0.2 / pad 0.4 in the footprint)
            for (x, y) in ((2.75, 3.0), (3.75, 2.25), (4.75, 2.0), (5.25, 3.0), (3.5, 3.25)):
                if top.contains(sbox(x - 0.125, y - 0.125, x + 0.125, y + 0.125)):
                    vias.append((x, y))
        short = None
    elif c.kind == "loop":
        full = _cells_in(reg, KO[0], KO[1], c.fill_xright, c.open_ytop)
        inner = _cells_in(reg.buffer(-c.w, quad_segs=256), KO[0], KO[1], c.fill_xright - c.w, c.open_ytop)
        band = full.difference(inner)
        # cut the band's top edge (the open end stays on the arc side) and its right edge above the short
        band = band.difference(sbox(KO[0] + 1.75, c.open_ytop - c.w - 1e-6, 10, 10))
        band = band.difference(sbox(c.fill_xright - c.w - 1e-6, c.short_y0 + c.w, 10, 10))
        short = sbox(c.fill_xright - c.w, c.short_y0, G_EDGE_X + 0.25, c.short_y0 + c.w)    # 0.25 into the ground copper
        leg = sbox(fx0, KO[1], fx1, G_EDGE_Y - gap).intersection(reg)
        leg = _cells_in(leg.buffer(1e-6), fx0, KO[1], fx1, G_EDGE_Y - gap)
        fcu = unary_union([band, short, leg])
        # keep only the connected piece that holds the feed leg
        if fcu.geom_type == "MultiPolygon":
            fcu = max(fcu.geoms, key=lambda p: p.intersection(leg).area)
        bcu = None; vias = []
    else:
        raise ValueError(c.kind)
    fcu = fcu.simplify(1e-9)
    feed = dict(x0=fx0, x1=fx1, y_gap0=G_EDGE_Y - gap, y_gap1=G_EDGE_Y)
    inside = sbox(*KO).intersection(board_region_inset(EDGE_CLR - 1e-6))
    cu_all = fcu if bcu is None else fcu.union(bcu)
    ok_in = cu_all.difference(inside.union(sbox(G_EDGE_X - 1e-6, KO[1], G_EDGE_X + 0.25 + 1e-6, KO[3]))).area < 1e-9
    b = fcu.bounds
    info = dict(fits=bool(ok_in), copper_area_F_mm2=round(fcu.area, 3), copper_area_B_mm2=(round(bcu.area, 3) if bcu else 0.0),
                bounds_case=b, n_vias=len(vias), feed_leg_len_mm=round(G_EDGE_Y - gap - min(y for _, y in fcu.exterior.coords), 3)
                if fcu.geom_type == "Polygon" else None)
    return dict(fcu=fcu, bcu=bcu, vias=vias, feed=feed, short=short, info=info)


# ------------------------------------------------------------------ scene variants
@dataclass
class Var:
    phantom: bool = True
    wrist_a: float = 28.0           # [V2B / SIM-10 v1] top curvature a^2/b = 35 mm
    wrist_b: float = 22.4
    skin_t: float = 1.5
    fat_t: float = 2.5
    wrist_x0: float = -20.0
    wrist_x1: float = 61.0
    frame_gnd: bool = True          # E-1 frame ground finger at the E3 end
    wing: bool = True               # c-Si wing on root B
    rail_ss: bool = True            # stainless rail section (M-2)


def strap_path(side, v: Var, n=400, s_max=19.0):
    """strap midline in the (Y, z) plane from the bar (s = 0) to s_max: free span tangent to the wrist ellipse offset by
    half the strap thickness, then along it.  side 'B' = root B (Y < 0, antenna wall), 'A' = root A (Y > 34).
    Model of geom_v3f.wrist_geo (strap lane) with the V2-B phantom ellipse [CAD BAR_OUT, BAR_Z, STRAP_T]."""
    a, b = v.wrist_a, v.wrist_b
    zcen = Z_FLOOR - b                         # ellipse centre (dorsal vertex on the floor plane)
    ts = G.STRAP_T
    sgn = -1.0 if side == "B" else 1.0
    P0 = (YC + sgn * (G.POD_W / 2 + G.BAR_OUT), Z_FLOOR + G.BAR_Z)
    def pt(t, off):   # t from the dorsal vertex toward the side; returns point and outward normal
        y = a * math.sin(t); z = b * math.cos(t)
        nrm = (math.sin(t) / a, math.cos(t) / b); nn = math.hypot(*nrm)
        return (YC + sgn * (y + off * nrm[0] / nn), zcen + z + off * nrm[1] / nn), (sgn * nrm[0] / nn, nrm[1] / nn)
    def f(t):
        q, nr = pt(t, ts / 2)
        return (P0[0] - q[0]) * nr[0] + (P0[1] - q[1]) * nr[1]
    lo, hi = 0.05, math.pi / 2 + 0.5
    for _ in range(80):
        m = 0.5 * (lo + hi)
        if f(lo) * f(m) <= 0: hi = m
        else: lo = m
    t0 = 0.5 * (lo + hi); q0, _ = pt(t0, ts / 2)
    free = math.hypot(P0[0] - q0[0], P0[1] - q0[1])
    pts = [P0]; s = [0.0]
    for k in range(1, 41):
        u = k / 40; pts.append((P0[0] + u * (q0[0] - P0[0]), P0[1] + u * (q0[1] - P0[1]))); s.append(u * free)
    t = t0
    while s[-1] < s_max:
        t += 0.002
        q, _ = pt(t, ts / 2)
        s.append(s[-1] + math.hypot(q[0] - pts[-1][0], q[1] - pts[-1][1])); pts.append(q)
    return np.array(pts), np.array(s), dict(P0=P0, t0=t0, free=free)


def _offset_path(P, off, sgn):
    """offset a polyline by off (outward = away from the wrist)"""
    out = []
    for i in range(len(P)):
        a = P[max(i - 1, 0)]; b = P[min(i + 1, len(P) - 1)]
        d = b - a; d = d / (np.hypot(*d) + 1e-12)
        nrm = np.array([-d[1], d[0]])
        if nrm[1] < 0: nrm = -nrm          # outward = upward / away from the wrist on both sides
        out.append(P[i] + off * nrm)
    return np.array(out)


def path_band(side, v, s0, s1, off0, off1):
    """(Y, z) polygon of the strap between arc lengths s0..s1 and offsets off0..off1 from the midline"""
    P, s, _ = strap_path(side, v)
    sel = (s >= s0) & (s <= s1)
    Q = P[sel]
    A = _offset_path(Q, off0, 0); B = _offset_path(Q, off1, 0)
    return Polygon(list(map(tuple, A)) + list(map(tuple, B[::-1]))).buffer(0)


def path_points(side, v, s0, s1, off):
    P, s, _ = strap_path(side, v)
    off_all = _offset_path(P, off, 0)
    sel = (s >= s0) & (s <= s1)
    if not sel.any():
        sel = np.zeros(len(s), bool); sel[int(np.argmin(np.abs(s - s0)))] = True
    return off_all[sel]


# ------------------------------------------------------------------ scene
def build_scene(c: Cand, v: Var, snap):
    """snap = (snap_y, snap_z): nearest mesh grid plane (physical) in y and z (PEC sheets must lie on grid planes).
    returns (prims, port, ant) ; dielectrics in precedence order, PEC on top."""
    sy, sz = snap
    P = []
    a, b = v.wrist_a, v.wrist_b
    zcen = Z_FLOOR - b
    # ---------------- wrist phantom (rigid ellipse), as V2-B
    if v.phantom:
        P.append(EllCylX(YC, zcen, a, b, v.wrist_x0, v.wrist_x1, SKIN, tag="skin"))
        P.append(EllCylX(YC, zcen, a - v.skin_t, b - v.skin_t, v.wrist_x0, v.wrist_x1, FAT, tag="fat"))
        t2 = v.skin_t + v.fat_t
        P.append(EllCylX(YC, zcen, a - t2, b - t2, v.wrist_x0, v.wrist_x1, MUSCLE, tag="muscle"))
    # ---------------- strap roots (TPU) to s 16 + quick release to s 19 [CAD ROOT_END_S, QR]; band beyond: not modelled [E]
    LX = (G.LUG["x0"], G.LUG["x1"])
    for side in ("A", "B"):
        P.append(PolyX(path_band(side, v, 0.0, G.QR["s1"], -G.STRAP_T / 2, G.STRAP_T / 2), LX[0], LX[1], ROOT, f"root_{side}"))
    # capsule on root A (shell) and wing laminate on root B [CAD CAPSULE, WING]
    cp = G.CAPSULE
    P.append(PolyX(path_band("A", v, cp["s0"], cp["s1"], G.STRAP_T / 2, G.STRAP_T / 2 + cp["t"] - G.STRAP_T), cp["x0"], cp["x0"] + cp["L"], CAPS, "capsule"))
    wg = G.WING
    if v.wing:
        P.append(PolyX(path_band("B", v, wg["s0"], wg["s1"], G.STRAP_T / 2, G.STRAP_T / 2 + wg["t"] - G.STRAP_T), wg["x0"], wg["x0"] + wg["L"], WINGL, "wing_lam"))
    # ---------------- band interior = air (overrides tissue where the rigid shapes overlap)
    P.append(Box((0.0, 0.0, Z_FLOOR), (G.POD_L, G.POD_W, zc(ZC.win1)), AIR, "pod_interior"))
    # ---------------- ring (PC), floor films, lugs, K block, E3 block, mesa
    ring = G.case_outline().difference(G.cavity())
    P.append(PolyZ(ring, Z_FLOOR, zc(ZC.win1), PC, "ring"))
    P.append(PolyZ(G.case_outline(), Z_FLOOR, 0.0, PC, "floor_films"))
    P.append(Box((LX[0], -G.BAR_OUT, Z_FLOOR), (LX[1], 0.0, zc(G.LUG["z1"])), PC, "lug_B"))
    P.append(Box((LX[0], G.POD_W, Z_FLOOR), (LX[1], G.POD_W + G.BAR_OUT, zc(G.LUG["z1"])), PC, "lug_A"))
    kb = G.K_BLOCK_IN
    P.append(Box((kb["x0"], kb["y0"], BOARD_T), (kb["x1"], kb["y1"], zc(ZC.rim_top)), PC, "K_block"))
    P.append(Box((G.E3_BLOCK["x0"], 1.0, Z_FLOOR), (G.POD_L - 1.0, G.POD_W - 1.0, zc(ZC.rim_top)), PC, "E3_block"))
    P.append(PolyZ(G.cap_poly(), zc(ZC.mesa), Z_FLOOR, PC, "ppg_mesa"))
    # ---------------- lid: window glass + film/OCA, PV laminate (glass + encapsulant), rail (GF-LCP section)
    P.append(PolyZ(G.film_outline(), zc(ZC.film0), zc(ZC.win0), OCA, "film_oca"))
    P.append(PolyZ(G.window_glass_outline(), zc(ZC.win0), zc(ZC.win1), GLASS, "window_glass"))
    P.append(PolyZ(G.lam_outline(), zc(ZC.pv0), zc(ZC.pv_glass0), ENCAP, "lam_encap"))
    P.append(PolyZ(G.lam_outline(), zc(ZC.pv_glass0), zc(ZC.pv1), GLASS, "lam_glass"))
    rl = G.RAIL
    P.append(Box((rl["x0"], rl["y0"], zc(ZC.rail0)), (G.RAIL_LCP_X1, rl["y1"], zc(ZC.win_seat)), LCP, "rail_lcp"))
    for (x0, y0, x1, y1) in [p.bounds for p in G.rail_posts()]:
        P.append(Box((x0, y0, BOARD_T), (x1, y1, zc(ZC.rail0)), LCP, "rail_post"))
    pn = G.PANEL
    P.append(Box((pn["x0"], pn["y0"], zc(ZC.panel0)), (pn["x1"], pn["y1"], zc(ZC.panel1)), PANEL_GL, "panel_glass"))
    # ---------------- board: FR-4 in the pocket, ground (PEC, all layers merged) elsewhere
    bo = G.board_outline()
    pocket = sbox(*KO).intersection(bo)
    P.append(PolyZ(pocket, 0.0, BOARD_T, FR4, "fr4_pocket"))
    P.append(IfacePlane(pocket, BOARD_T, FR4, AIR, "fr4_top_iface"))
    P.append(IfacePlane(pocket, 0.0, PC, FR4, "fr4_bot_iface"))
    gnd = bo.difference(sbox(*KO)).difference(G.motor_cut_poly())
    P.append(PolyZ(gnd, 0.0, BOARD_T, PEC, "board_gnd"))
    # ---------------- radiator
    ant = radiator(c)
    P.append(PolyZ(ant["fcu"], BOARD_T, BOARD_T, PEC, "ant_F"))
    if ant["bcu"] is not None:
        P.append(PolyZ(ant["bcu"], 0.0, 0.0, PEC, "ant_B"))
        for (x, y) in ant["vias"]:
            P.append(Box((x - 0.125, y - 0.125, 0.0), (x + 0.125, y + 0.125, BOARD_T), PEC, "ant_via"))
    f = ant["feed"]
    port = dict(x0=f["x0"], x1=f["x1"], y_gap0=f["y_gap0"], y_gap1=f["y_gap1"], z=BOARD_T)
    # ---------------- Ti plates in the floor (PEC through the floor: RF-tied to the board by film + 12 pF TVS, as V2-B)
    for k, pl in enumerate(G.plate_outlines()):
        P.append(PolyZ(pl, Z_FLOOR, 0.0, PEC, f"plate_E{k + 1}"))
    # ---------------- motor (PEC can, dia 8, in the board cut-out) [CAD MOTOR]
    mc = G.MOTOR_C
    P.append(PolyZ(Point(*mc).buffer(G.MOTOR["d"] / 2, quad_segs=8), sz(zc(ZC.motor0)), sz(zc(ZC.motor1)), PEC, "motor"))
    # ---------------- display panel (conductor sheet) + FPC: top run, fold, return run on the board, J13 tie
    zp = sz(0.5 * (zc(ZC.panel0) + zc(ZC.panel1)))
    P.append(Box((pn["x0"], pn["y0"], zp), (pn["x1"], pn["y1"], zp), PEC, "panel_sheet"))
    xf = sy(G.fpc_fold_outer_x()) if callable(getattr(G, "fpc_fold_outer_x", None)) else 36.5
    yw = G.FPC_Y_WIDE; ytl = G.FPC_Y_TAIL
    zr = sz(BOARD_T + 0.25)
    P.append(Box((pn["x1"], yw[0], zp), (xf, yw[1], zp), PEC, "fpc_top"))
    P.append(Box((xf, yw[0], zr), (xf, yw[1], zp), PEC, "fpc_fold"))
    P.append(Box((G.FPC_WIDE_X - 2.0, yw[0], zr), (xf, yw[1], zr), PEC, "fpc_return_wide"))
    P.append(Box((G.FPC_END_X, ytl[0], zr), (G.FPC_WIDE_X - 2.0, ytl[1], zr), PEC, "fpc_tail"))
    P.append(Box((G.FPC_END_X, ytl[0], BOARD_T), (G.FPC_END_X + 1.0, ytl[1], zr), PEC, "J13_tie"))
    # ---------------- stainless window frame (cut back 5 mm around the keep-out) + E-1 ground tab at the E3 end
    zf0, zf1 = sz(zc(ZC.frame0)), sz(zc(ZC.frame1))
    P.append(PolyZ(G.frame_outline(), zf0, zf1, PEC, "window_frame"))
    fg = G.frame_gnd()["courtyard"]; fg = fg.bounds if hasattr(fg, "bounds") else fg
    if v.frame_gnd:
        P.append(Box((fg[0] + 1.0, fg[1] + 0.4, BOARD_T), (fg[2] - 1.0, fg[3] - 0.4, zf0), PEC, "frame_gnd_finger"))
    # ---------------- rib insert (stainless, posts floating 0.25 above the board) and the stainless rail section
    ins = G.INSERT
    P.append(Box((ins["x0"], ins["y0"], zc(ZC.insert0)), (ins["x1"], ins["y1"], zc(ZC.insert1)), PEC, "rib_insert"))
    for x in G.POST_X:
        P.append(Box((x - 0.3, G.POST_Y[0], BOARD_T + 0.25), (x + 0.3, G.POST_Y[1], zc(ZC.insert0)), PEC, "rib_post"))
    if v.rail_ss:
        P.append(Box((G.RAIL_LCP_X1, rl["y0"], zc(ZC.rail0)), (rl["x1"], rl["y1"], zc(ZC.win_seat)), PEC, "rail_ss"))
    # ---------------- top-rim contacts (K block pins on J15 / J18) and the E3 strip (+ wrap, J11 finger)
    for p in G.PINS:
        (tx, ty), (lx, ly) = p["top"], p["land"]
        P.append(Box((tx - 0.5, ty - 0.5, BOARD_T), (tx + 0.5, ty + 0.5, zc(ZC.rim_top - G.PIN_RECESS)), PEC, p["name"]))
        P.append(Box((min(tx, lx) - 0.5, min(ty, ly) - 0.5, BOARD_T), (max(tx, lx) + 0.5, max(ty, ly) + 0.5, BOARD_T + 0.25), PEC, p["name"] + "_finger"))
    e3 = G.E3_TOP; ztop = sz(zc(ZC.rim_top))
    P.append(Box((e3["x0"], e3["y0"], ztop), (G.POD_L, e3["y1"], ztop), PEC, "E3_strip"))
    P.append(Box((G.POD_L, G.E3_WRAP["y0"], sz(zc(G.E3_WRAP["z0"]))), (G.POD_L, G.E3_WRAP["y1"], ztop), PEC, "E3_wrap"))
    jx, jy = G.J11["land"]
    P.append(Box((jx - 0.5, jy - 0.5, BOARD_T), (jx + 0.5, jy + 0.5, ztop), PEC, "J11_finger"))
    # ---------------- PV strips (conductors) + lid tail to J6
    zs = sz(zc(ZC.cell0) + 0.08)
    for k, s in enumerate(G.strips()):
        P.append(PolyZ(s, zs, zs, PEC, f"pv_strip{k + 1}"))
    lt = G.LID_TAIL
    P.append(Box((G.STRIP_X[1] - 0.5, lt["y0"], zs), (lt["x1"], lt["y1"], zs), PEC, "lid_tail_top"))
    P.append(Box((lt["x0"], sy(0.5 * (lt["y0"] + lt["y1"])), BOARD_T), (lt["x1"], sy(0.5 * (lt["y0"] + lt["y1"])), zs), PEC, "lid_tail_drop"))
    # ---------------- strap conductors (tied to the board ground at the entry lands), wing silicon, capsule cell foil
    def path_sheet(side, s0, s1, off, x0, x1, tag):
        pts = path_points(side, v, s0, s1, off)
        q = [(sy(y), sz(z)) for y, z in pts]
        qq = [q[0]]
        for p_ in q[1:]:
            if p_ != qq[-1]:
                qq.append(p_)
        for (y0, z0), (y1, z1) in zip(qq[:-1], qq[1:]):
            if y1 != y0:
                P.append(Box((x0, min(y0, y1), z0), (x1, max(y0, y1), z0), PEC, tag))
            if z1 != z0:
                P.append(Box((x0, y1, min(z0, z1)), (x1, y1, max(z0, z1)), PEC, tag))
        return qq
    zt = sz(Z_FLOOR + G.BAR_Z)
    lb = G.LAND_B; la = G.LAND_A
    # root B: PV_W+ | GND (merged 2 mm strip), board land -> bar -> root to the wing
    sB = wg["s0"] + 0.45 if v.wing else G.ROOT_END_S
    qB = path_sheet("B", 0.0, sB if v.wing else G.ROOT_END_S, 0.0, lb[0] + 0.5, lb[0] + 2.5, "tail_B")
    P.append(Box((lb[0] + 0.5, qB[0][0], zt), (lb[0] + 2.5, sy(lb[2] + 1.0), zt), PEC, "tail_B_in"))
    P.append(Box((lb[0] + 0.5, sy(lb[2] + 1.0), zt), (lb[0] + 2.5, sy(lb[2] + 1.5), BOARD_T), PEC, "tail_B_tie"))
    if v.wing:
        cs = G.wing_cells_s()
        path_sheet("B", cs[0][0], cs[-1][1], 0.9, wg["x0"] + (wg["L"] - wg["cell_x"]) / 2, wg["x0"] + (wg["L"] + wg["cell_x"]) / 2, "wing_si")
        # string link from the tail to the first sub-cell
        q0 = path_points("B", v, sB, sB, 0.0)[0]; q1 = path_points("B", v, sB, sB, 0.9)[0]
        P.append(Box((lb[0] + 0.5, sy(q0[0]), sz(q0[1])), (lb[0] + 2.5, sy(q0[0]), sz(q1[1])), PEC, "wing_link"))
    # root A: BATT_P | GND | NTC | GND (merged 5 mm strip) -> capsule cell foil (tab end at the bar side)
    sA = cp["s0"] + 0.95
    qA = path_sheet("A", 0.0, sA, 0.0, la[0] + 0.5, la[1] - 0.5, "tail_A")
    P.append(Box((la[0] + 0.5, sy(la[3] - 1.0), zt), (la[1] - 0.5, qA[0][0], zt), PEC, "tail_A_in"))
    P.append(Box((la[0] + 0.5, sy(la[3] - 1.5), zt), (la[1] - 0.5, sy(la[3] - 1.0), BOARD_T), PEC, "tail_A_tie"))
    cx0 = cp["x0"] + (cp["L"] - cp["cell"][0]) / 2
    offc = G.STRAP_T / 2 + (cp["t"] - G.STRAP_T) / 2
    path_sheet("A", sA, sA + cp["cell"][1], offc, cx0, cx0 + cp["cell"][0], "cell_foil")
    q0 = path_points("A", v, sA, sA, 0.0)[0]; q1 = path_points("A", v, sA, sA, offc)[0]
    P.append(Box((la[0] + 0.5, sy(q0[0]), sz(q0[1])), (la[1] - 0.5, sy(q0[0]), sz(q1[1])), PEC, "cell_tab"))
    return P, port, ant


def split_pec_polyz(prims, mesh):
    """split PEC PolyZ prisms at the mesh zone boundaries in x and y (geom.polyz maps PEC polygons per vertex, which
    is exact only inside one zone)"""
    out = []
    xs = [s[0] for s in mesh.ax[0].segs] + [mesh.ax[0].segs[-1][1]]
    ys = [s[0] for s in mesh.ax[1].segs] + [mesh.ax[1].segs[-1][1]]
    for p in prims:
        if isinstance(p, PolyZ) and p.mat.pec:
            for i in range(len(xs) - 1):
                for j in range(len(ys) - 1):
                    q = p.poly.intersection(sbox(xs[i], ys[j], xs[i + 1], ys[j + 1]))
                    if q.area > 1e-9:
                        out.append(PolyZ(q, p.z0, p.z1, p.mat, p.tag))
        else:
            out.append(p)
    return out
