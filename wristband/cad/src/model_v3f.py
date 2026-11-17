"""SolarBand V3-F pod: build123d model from geom_v3f.py, STEP + GLB export, manifold3d interference and clearance
checks, masses and volumes, renders (zrender.py, copied from mech/) and exact planar sections.

usage: python3 -B model_v3f.py      (V3F_POD_L=41 for the RFQ reserve)
Writes out/V3F_L<40|41>_pod.step, .glb, checks_pod_L<..>.json, render_*.png, section_*.png
"""
import json, math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import geom_v3f as G                                       # noqa: E402
from shapely.geometry import box as sbox, Point, Polygon  # noqa: E402
from shapely.ops import unary_union                       # noqa: E402
import build123d as bd                                    # noqa: E402
from build123d import (Wire, Face, Vector, extrude, Pos, Rot, Box, Cylinder, Compound, Color, export_step,  # noqa: E402
                       export_gltf, Plane)
import manifold3d as mf                                   # noqa: E402
import trimesh                                            # noqa: E402

OUT = G.OUT_DIR                                             # [G1] out/ for plain outlines, out/options/<TAG>/ for option runs
TAG = G.TAG
if G.FPC_MODEL == "rear":                                   # [G1 session 2] consent-dependent routing: zone file only
    sys.exit("fpc=rear is a zones-only option (exports_v3f.py, test_lgeom_v3f.py): no 3-D model is built for it")
Z = G.Z
L = G.POD_L
BIG = 200.0


def H(x0, y0, x1, y1):
    return sbox(x0, y0, x1, y1)


# ----------------------------------------------------------------------------------------------- 2-D -> 3-D helpers
def _faces(g):
    g = g.buffer(0)
    polys = [g] if g.geom_type == "Polygon" else [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]
    out = []
    for p in polys:
        if p.area < 1e-4:
            continue
        p = p.simplify(0.002, preserve_topology=True)
        ext = [Vector(x, y, 0) for x, y in list(p.exterior.coords)[:-1]]
        w = Wire.make_polygon(ext, close=True)
        holes = [Wire.make_polygon([Vector(x, y, 0) for x, y in list(r.coords)[:-1]], close=True) for r in p.interiors
                 if Polygon(r).area > 1e-4]
        out.append(Face(w, holes) if holes else Face(w))
    return out


def prism(g, z0, z1):
    """extrude a shapely (Multi)Polygon from z0 to z1; returns a build123d Part or None"""
    fs = _faces(g)
    if not fs or z1 <= z0:
        return None
    parts = [Pos(0, 0, z0) * extrude(f, z1 - z0, dir=(0, 0, 1)) for f in fs]
    s = parts[0]
    for p in parts[1:]:
        s = s + p
    return s


def union(*items):
    items = [i for i in items if i is not None]
    s = items[0]
    for i in items[1:]:
        s = s + i
    return s


def cyl_z(x, y, d, z0, z1):
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(d / 2, z1 - z0)


def cyl_x(x0, x1, y, z, d):
    return Pos((x0 + x1) / 2, y, z) * (Rot(0, 90, 0) * Cylinder(d / 2, x1 - x0))


def bx3(x0, y0, z0, x1, y1, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def annulus_sector_xz(xc, zc, r_in, r_out, y0, y1, a0=-90, a1=90, n=40):
    """half-ring in the X-Z plane (angles from +X axis), extruded along Y"""
    a = np.radians(np.linspace(a0, a1, n))
    outer = [(xc + r_out * math.cos(t), zc + r_out * math.sin(t)) for t in a]
    inner = [(xc + r_in * math.cos(t), zc + r_in * math.sin(t)) for t in a[::-1]]
    pts = [Vector(u, 0, v) for u, v in outer + inner]
    w = Wire.make_polygon(pts, close=True)
    f = Face(w)
    return Pos(0, y0, 0) * extrude(f, y1 - y0, dir=(0, 1, 0))


# ----------------------------------------------------------------------------------------------- regions
OUTL = G.case_outline(); CAV = G.cavity(); WALLR = OUTL.difference(CAV)
LIPR = OUTL.difference(G.inset_outline(G.LIP))
WIN_HALF = H(-BIG, -BIG, BIG, G.Y_WIN1)
PV_HALF = H(-BIG, G.Y_WIN1, BIG, BIG)
K_REG = H(-BIG, G.Y_WIN1, G.X_KTOP1, BIG)
E3_REG = H(G.E3_BLOCK["x0"], -BIG, BIG, BIG)
ANT_BUF = G.ant_buffer()
ANT_SEAT = G.ant_seat_region()          # [S2c] buffer + lid-antenna frame cut: glass on PC at ant_seat
GLASS = G.window_glass_outline()
LAM = G.lam_outline()
FRAME = G.frame_outline()
E1, E2 = G.plate_outlines()
CAPP = G.cap_poly()
BOARD = G.board_outline()
MC = G.MOTOR_C
X_E3W = L - G.WALL                      # inner face of the hand-end wall
J11X, J11Y = G.J11["land"]
J11_FACE = H(J11X - G.FACE[1] / 2, J11Y - G.FACE[0] / 2, J11X + G.FACE[1] / 2, J11Y + G.FACE[0] / 2)
_cr = G.CASE_R
BUMPERS = LIPR.intersection(unary_union([H(-1, -1, _cr, _cr), H(L - _cr, -1, L + 1, _cr), H(-1, G.POD_W - _cr, _cr, G.POD_W + 1),
                                         H(L - _cr, G.POD_W - _cr, L + 1, G.POD_W + 1)])).difference(
    H(G.E3_TOP["x0"] - 0.1, G.E3_TOP["y0"] - 0.1, BIG, G.E3_TOP["y1"] + 0.1))           # [S2b M-5] the four R6 corner arcs of the lip, off the E3 strip


def build():
    P = {}
    # ---------------- floor, plates, carrier film, board, cap
    cap_open = CAPP.buffer(0.10, quad_segs=16)
    P["floor_film"] = prism(OUTL.difference(E1).difference(E2).difference(cap_open), 0.0, Z.floor1)
    P["plate_E1"] = prism(E1, 0.0, Z.floor1)
    P["plate_E2"] = prism(E2, 0.0, Z.floor1)
    mcut = G.motor_cut_poly() if G.HAS_MOTOR else Point(*MC).buffer(1e-6)       # [G1] hole, notch or none
    P["carrier_film"] = prism(BOARD.difference(cap_open).difference(Point(*MC).buffer(1e-6) if G.MOTOR_ON_FILM else mcut), Z.floor1, Z.carrier1)   # [S2d K-1] film kept under the motor
    P["board"] = prism(BOARD.difference(mcut), Z.carrier1, Z.pcb1)
    P["optical_cap"] = prism(CAPP, Z.mesa, Z.carrier1)
    # ---------------- parts envelope on the board top (zones of board_zones, max-material heights)
    zones = G.board_zones()
    zg = {z["name"]: z for z in zones}
    excl = unary_union([z["geom"] for z in zones if z["kind"] in ("no_parts", "land", "keepout", "keepout_except", "part", "cutout")
                        + (("keepout_all_layers",) if G.S2C else ())]   # [S2c] the AE1 pocket holds no parts but J40 (its own zone)
                       + ([mcut.buffer(G.CUT_EDGE_CLR)] if G.HAS_MOTOR else []))
    hz = sorted([z for z in zones if z["kind"] == "height_limit"], key=lambda z: z["h_max"])     # [S1] lowest limit wins where zones overlap
    env, taken = [], None
    for z in hz:
        g = z["geom"] if taken is None else z["geom"].difference(taken)
        env.append(prism(g.difference(excl).buffer(-0.05), Z.pcb1, Z.pcb1 + z["h_max"]))
        taken = z["geom"] if taken is None else taken.union(z["geom"])
    env.append(prism(BOARD.difference(taken).difference(excl).buffer(-0.05), Z.pcb1, Z.parts_gen))
    P["parts_envelope"] = union(*env)
    # ---------------- modelled board parts
    sw = G.SW1; fx = sw["front_x"]
    P["SW1_body"] = bx3(fx - sw["body_x"], sw["cy"] - sw["body_y"] / 2, Z.pcb1, fx, sw["cy"] + sw["body_y"] / 2, Z.pcb1 + sw["h"])
    zm = Z.pcb1 + sw["act_z_mid"]
    P["SW1_actuator"] = bx3(fx, sw["cy"] - sw["act_w"] / 2, zm - sw["act_h"] / 2, fx + sw["act_out"], sw["cy"] + sw["act_w"] / 2, zm + sw["act_h"] / 2)
    for p in G.PINS:
        lx, ly = p["land"]
        P[f"{p['ref']}_finger"] = bx3(lx - G.J15_BODY[0] / 2, ly + G.J15_BODY[2], Z.pcb1, lx + G.J15_BODY[0] / 2, ly + G.J15_BODY[3], Z.finger_top)
    d10 = G.D10
    P["D10_led"] = bx3(d10["x0"] + 0.25, d10["y0"], Z.pcb1, d10["x1"] - 0.25, d10["y1"] - 0.15, Z.pcb1 + d10["h"])      # [S1 C-6] body inside its courtyard
    P["J11_finger"] = bx3(J11X - G.J15_BODY[0] / 2, J11Y + G.J15_BODY[2], Z.pcb1, J11X + G.J15_BODY[0] / 2, J11Y + G.J15_BODY[3], Z.finger_top)
    if G.HAS_MOTOR:
        P["motor_psa"] = cyl_z(MC[0], MC[1], G.MOTOR["d"], Z.carrier1 if G.MOTOR_ON_FILM else Z.floor1, Z.motor0)
        P["motor_ERM"] = cyl_z(MC[0], MC[1], G.MOTOR["d_max"], Z.motor0, Z.motor0 + G.MOTOR["h_max"])
    # ---------------- display: panel, FPC, support, film, frame, glass
    pn = G.PANEL
    P["panel_LS011B7DH03"] = bx3(pn["x0"], pn["y0"], Z.panel0, pn["x1"], pn["y1"], Z.panel1)
    fy0, fy1 = G.FPC_Y; xf = G.FPC_EDGE_X + G.FPC_FOLD_AT; t = G.FPC["t"]
    zc = (G.FPC_Z_EXIT + G.FPC_Z_RETURN + t) / 2
    sx0, sx1 = G.FPC_STIFF_X
    if G.FPC_MODEL == "s1":
        fpc = union(bx3(G.FPC_EDGE_X, fy0, G.FPC_Z_EXIT, xf, fy1, G.FPC_Z_EXIT + t),
                    annulus_sector_xz(xf, zc, G.FPC_FOLD_RIN, G.FPC_FOLD_RIN + t, fy0, fy1),
                    bx3(G.FPC_END_X, fy0, G.FPC_Z_RETURN, xf, fy1, G.FPC_Z_RETURN + t))
        P["panel_FPC"] = fpc
        P["FPC_stiffener"] = bx3(sx0, G.AA_CY - G.FPC["w_end"] / 2, G.FPC_Z_RETURN + t, sx1, G.AA_CY + G.FPC["w_end"] / 2,
                                 G.FPC_Z_RETURN + G.FPC["t_stiff"])
    else:   # [G1] outline as dimensioned (9.47 mm wide part, 5.5 mm tail); the stiffener is on the FRONT face = the board side after the fold
        wy0, wy1 = G.FPC_Y_WIDE; ty0, ty1 = G.FPC_Y_TAIL; zr = G.FPC_Z_RETURN; ts = G.FPC["t_stiff"] - t
        lift = ts if G.FPC_MODEL == "dwg" else 0.0      # dwg: the stiffened end lies on the board, so the tail rides up by the stiffener there
        P["panel_FPC"] = union(bx3(G.FPC_EDGE_X, wy0, G.FPC_Z_EXIT, xf, wy1, G.FPC_Z_EXIT + t),
                               annulus_sector_xz(xf, zc, G.FPC_FOLD_RIN, G.FPC_FOLD_RIN + t, wy0, wy1),
                               bx3(G.FPC_WIDE_X, wy0, zr, xf, wy1, zr + t),
                               bx3(sx1, ty0, zr, G.FPC_WIDE_X, ty1, zr + t),
                               bx3(sx0, ty0, zr + lift, sx1, ty1, zr + lift + t))
        P["FPC_stiffener"] = bx3(sx0, ty0, zr + lift - ts, sx1, ty1, zr + lift)
    sup = H(pn["x0"], pn["y0"], pn["x1"], pn["y1"]).difference(
        H(pn["x0"] + G.SUPPORT_BAND, pn["y0"] + G.SUPPORT_BAND, pn["x1"] - G.SUPPORT_BAND, pn["y1"] - G.SUPPORT_BAND))
    P["panel_support"] = union(prism(sup, Z.sup0, Z.panel0), *[cyl_z(x, y, G.SUPPORT_LEGS_D, Z.pcb1, Z.sup0) for x, y in G.support_legs()])
    ft = G.FILM_TAIL
    P["frontlight_film"] = union(prism(G.film_outline(), Z.film0, Z.win0),
                                 bx3(ft["x0"], ft["y0"], Z.pcb1 + 0.05, ft["x1"], ft["y1"], Z.film0),
                                 bx3(ft["x1"], ft["y0"], Z.pcb1 + 0.05, G.J16["x1"], ft["y1"], Z.pcb1 + 0.15))
    P["window_frame_ss"] = prism(FRAME, Z.frame0, Z.frame1)
    # [S1 C-1] antenna-side window rail (GF-LCP) on 9 posts: glass-only seat inside the antenna buffer, frame seat outside it
    rl = G.RAIL; rail2d = H(rl["x0"], rl["y0"], rl["x1"], rl["y1"])
    if G.RAIL_CORE:   # [S2b M-2] stainless section outside the antenna buffer (metal rule), GF-LCP inside it and for the posts
        P["window_rail_lcp"] = union(prism(rail2d.intersection(ANT_BUF), Z.rail0 - G.RAIL_P4_DEEPEN, Z.ant_seat),   # [P4] 0.20 deeper (p4=1)
                                     *[prism(pp, Z.pcb1, Z.rail0) for pp in G.rail_posts()])
        ss2d = rail2d.difference(ANT_BUF)   # [S2c] stainless section inside the frame cut (X 11.5-13.0) rises to ant_seat (glass bonded, no frame)
        P["window_rail_ss"] = union(prism(ss2d.difference(ANT_SEAT), Z.rail0, Z.win_seat),
                                    *([prism(ss2d.intersection(ANT_SEAT), Z.rail0, Z.ant_seat)] if not ss2d.intersection(ANT_SEAT).is_empty else []))
    else:
        P["window_rail_lcp"] = union(prism(rail2d.intersection(ANT_BUF), Z.rail0, Z.ant_seat), prism(rail2d.difference(ANT_BUF), Z.rail0, Z.win_seat),
                                     *[prism(pp, Z.pcb1, Z.rail0) for pp in G.rail_posts()])
    P["window_glass"] = prism(GLASS, Z.win0, Z.win1)
    # ---------------- PV laminate
    strips = G.strips()
    P["pv_glass"] = prism(LAM, Z.pv_glass0, Z.pv1)
    z_cell0, z_cell1 = Z.cell0, Z.cell0 + 0.165                                       # [S2b] follow the laminate lift
    P["pv_encapsulant"] = prism(LAM, Z.pv_flex1, Z.pv_glass0) - union(*[prism(s_, z_cell0, z_cell1) for s_ in strips])
    for i, s_ in enumerate(strips):
        P[f"pv_cell_{i + 1}"] = prism(s_, z_cell0, z_cell1)
    P["pv_flex"] = prism(LAM, Z.pv0, Z.pv_flex1)
    lt = G.LID_TAIL; j6 = G.J6
    P["pv_flex_tail"] = union(bx3(lt["x0"], lt["y0"], Z.pcb1 + 0.05, lt["x1"], lt["y0"] + 0.12, Z.pv0),          # [S1 C-6] drop beside the rib
                              bx3(lt["x0"], lt["y0"], Z.pcb1 + 0.05, lt["x1"], j6["y1"], Z.pcb1 + 0.17))        # flat on the J6 land
    # ---------------- rib (lid RFQ part) [B 1, 5.2]
    rb, ins = G.RIB, G.INSERT
    post_holes = unary_union([H(x - G.POST_SIZE / 2, G.POST_Y[0], x + G.POST_SIZE / 2, G.POST_Y[1]) for x in G.POST_X])
    if Z.pv_seat > Z.insert0 + 1e-9:   # [S2b] the PV seat is now above the insert's underside: the PC beside the insert only
        P["rib_pc"] = union(prism(H(rb["x0"], rb["y0"], rb["x1"], rb["y1"]).difference(post_holes), Z.rib_shelf0, Z.insert0),
                            prism(H(rb["x0"], ins["y1"], rb["x1"], rb["y1"]), Z.insert0, Z.pv_seat),
                            prism(H(ins["x1"], rb["y0"], rb["x1"], ins["y1"]), Z.insert0, Z.insert1))
    else:
        P["rib_pc"] = union(prism(H(rb["x0"], rb["y0"], rb["x1"], rb["y1"]).difference(post_holes), Z.rib_shelf0, Z.pv_seat),
                            prism(H(ins["x1"], rb["y0"], rb["x1"], G.Y_WIN1), Z.insert0, Z.insert1))
    P["rib_insert_ss"] = prism(H(ins["x0"], ins["y0"], ins["x1"], ins["y1"]), Z.insert0, Z.insert1)
    P["rib_posts_ss"] = union(*[prism(H(x - G.POST_SIZE / 2, G.POST_Y[0], x + G.POST_SIZE / 2, G.POST_Y[1]), Z.pcb1, Z.insert0) for x in G.POST_X])
    # ---------------- ring (black PC) with K block, E3 block, lip, lugs
    ring = [prism(WALLR, Z.floor1, Z.pv_seat)]
    wwin = WALLR.intersection(WIN_HALF).difference(E3_REG).difference(K_REG)
    ring.append(prism(wwin.difference(ANT_SEAT), Z.pv_seat, Z.win_seat))
    ring.append(prism(wwin.intersection(ANT_SEAT), Z.pv_seat, Z.ant_seat))      # [S2c] PC seat extended to X 13.0 (lid antenna frame cut)
    ring.append(prism(LIPR.intersection(WIN_HALF).intersection(H(-BIG, -BIG, G.X_LID1, BIG)).difference(K_REG), Z.pv_seat, Z.win1))
    ring.append(prism(LIPR.intersection(PV_HALF).intersection(H(G.X_KTOP1, -BIG, G.X_LID1, BIG)), Z.pv_seat, Z.pv1))
    # K block
    ring.append(prism(WALLR.intersection(K_REG), Z.floor1, Z.rim_top))
    ring.append(prism(CAV.intersection(K_REG), Z.finger_top + 0.10, Z.rim_top))
    ring.append(prism(CAV.intersection(H(G.WALL, G.RIB["y0"], G.K_BLOCK_IN["x1"], G.Y_WIN1)), Z.finger_top + 0.10, Z.win_seat))
    # E3 block (hand end)
    ring.append(prism(WALLR.intersection(H(G.X_LID1, -BIG, BIG, BIG)), Z.floor1, Z.rim_top))
    ring.append(prism(WALLR.intersection(H(G.E3_BLOCK["x0"], -BIG, G.X_LID1, BIG)).intersection(WIN_HALF), Z.pv_seat, Z.win_seat))
    e3in_w = CAV.intersection(E3_REG).intersection(WIN_HALF)
    e3in_p = CAV.intersection(E3_REG).intersection(PV_HALF)
    ring.append(prism(e3in_w.intersection(H(-BIG, -BIG, G.X_LID1, BIG)), Z.shelf_e3_0, Z.win_seat))
    ring.append(prism(e3in_w.intersection(H(G.X_LID1, -BIG, BIG, BIG)), Z.shelf_e3_0, Z.rim_top))
    ring.append(prism(e3in_p.intersection(H(-BIG, -BIG, G.X_LID1, BIG)), Z.rib_shelf0, Z.pv_seat))
    ring.append(prism(e3in_p.intersection(H(G.X_LID1, -BIG, BIG, BIG)), Z.rib_shelf0, Z.rim_top))
    j11_boss = J11_FACE.buffer(0.15, join_style=2).intersection(CAV)
    ring.append(prism(j11_boss.intersection(WIN_HALF), Z.finger_top + 0.25, Z.win_seat))
    # lugs (strap bars) on both long walls
    lg = G.LUG
    for (y0, y1) in ((-lg["w"], 4.0), (G.POD_W - 4.0, G.POD_W + lg["w"])):
        ring.append(prism(H(lg["x0"], y0, lg["x1"], y1).difference(OUTL), lg["z0"], G.LUG_TOP))      # [S2b] lugs keep their stage-2a top
    ring_s = union(*ring)
    # cuts: root slots, membrane window, pin counterbores, target pocket, E3 recess, J11 tab
    cuts = [bx3(G.LAND_A[0], G.POD_W - G.WALL - 0.01, 1.60, G.LAND_A[1], G.POD_W + lg["w"] + 0.01, 2.00),
            bx3(G.LAND_B[0], -lg["w"] - 0.01, 1.60, G.LAND_B[1], G.WALL + 0.01, 2.00)]
    mb = G.MEMBRANE
    cuts.append(bx3(X_E3W - 0.01, mb["y0"], mb["z0"], L + 0.01, mb["y1"], mb["z1"]))
    for p in G.PINS:
        cuts.append(cyl_z(p["top"][0], p["top"][1], p["cb_d"], Z.rim_top - G.PIN_RECESS, Z.rim_top + 0.01))
    e3top = OUTL.intersection(H(G.E3_TOP["x0"], G.E3_TOP["y0"], BIG, G.E3_TOP["y1"]))
    cuts.append(prism(e3top, Z.rim_top - Z.e3_t, Z.rim_top + 0.01))
    w3 = G.E3_WRAP
    cuts.append(bx3(L - Z.e3_t, w3["y0"], w3["z0"], L + 0.01, w3["y1"], w3["z1"] + 0.01))
    cuts.append(prism(J11_FACE, Z.finger_top, Z.finger_top + 0.25))
    for c in cuts:
        ring_s = ring_s - c
    P["ring_pc"] = ring_s
    # ---------------- inserts and fitted parts of the ring
    P["slot_A_potting"] = bx3(G.LAND_A[0], G.POD_W - G.WALL, 1.60, G.LAND_A[1], G.POD_W + lg["w"], 2.00)
    P["slot_B_potting"] = bx3(G.LAND_B[0], -lg["w"], 1.60, G.LAND_B[1], G.WALL, 2.00)
    P["bar_B_ss"] = cyl_x(lg["x0"], lg["x1"], -lg["w"] + 1.0, 0.85, lg["bar_d"])
    P["bar_A_ss"] = cyl_x(lg["x0"], lg["x1"], G.POD_W + lg["w"] - 1.0, 0.85, lg["bar_d"])
    P["membrane_tpe"] = union(bx3(L - mb["t"], mb["y0"], mb["z0"], L, mb["y1"], mb["z1"]),
                              cyl_x(fx + sw["act_out"] + 0.05, L - mb["t"], sw["cy"], zm, mb["nub_d"]))
    P["E3_strip_ti"] = union(prism(e3top, Z.rim_top - Z.e3_t, Z.rim_top), bx3(L - Z.e3_t, w3["y0"], w3["z0"], L, w3["y1"], w3["z1"]))
    P["E3_tab_ti"] = prism(J11_FACE, Z.finger_top, Z.finger_top + 0.25)
    pins = []
    for i, p in enumerate(G.PINS):
        tx, ty = p["top"]; lx, ly = p["land"]
        face = prism(H(lx - G.FACE[1] / 2, ly - G.FACE[0] / 2, lx + G.FACE[1] / 2, ly + G.FACE[0] / 2), Z.finger_top, Z.finger_top + 0.15)
        post = cyl_z(tx, ty, p["d"], Z.finger_top + 0.15 - 0.01, Z.rim_top - G.PIN_RECESS)
        leg = None
        if math.hypot(tx - lx, ty - ly) > 0.5:
            ls = Polygon([(tx, ty), (lx, ly), (lx + 0.01, ly + 0.01)]).buffer(0)
            from shapely.geometry import LineString
            leg = prism(LineString([(tx, ty), (lx, ly)]).buffer(0.6, cap_style=2), Z.finger_top + 0.14, Z.finger_top + 0.45)
        P[p["name"]] = union(face, post, leg)
    for p in G.PINS:
        P["ring_pc"] = P["ring_pc"] - P[p["name"]]
    P["ring_pc"] = P["ring_pc"] - P["bar_A_ss"] - P["bar_B_ss"]
    for tg in G.TARGETS:
        cx, cy = tg["c"]
        ring_cut = cyl_z(cx, cy, tg["d"], Z.rim_top - tg["skin"] - tg["t"], Z.rim_top - tg["skin"])
        P["ring_pc"] = P["ring_pc"] - ring_cut
        P[tg["name"]] = cyl_z(cx, cy, tg["d"], Z.rim_top - tg["skin"] - tg["t"], Z.rim_top - tg["skin"])
    # ---------------- adhesive beads (elastic) [G-14]
    pv_sup = unary_union([WALLR.intersection(PV_HALF).difference(K_REG).difference(E3_REG),
                          H(G.RIB["x0"], G.Y_LAM0, G.RIB["x1"], G.RIB["y1"]),
                          e3in_p.intersection(H(-BIG, -BIG, G.X_LID1, BIG))]).intersection(LAM)
    P["bead_pv"] = prism(pv_sup, Z.pv_seat, Z.pv0)
    win_sup = unary_union([wwin.difference(ANT_SEAT), CAV.intersection(H(G.WALL, G.RIB["y0"], G.K_BLOCK_IN["x1"], G.Y_WIN1)),
                           e3in_w.intersection(H(-BIG, -BIG, G.X_LID1, BIG)), j11_boss.intersection(WIN_HALF)]).intersection(FRAME)
    P["bead_window"] = prism(win_sup, Z.win_seat, Z.frame0)                                   # elastic seal bead on the ring seats [G-14]
    P["bead_antenna_corner"] = prism(wwin.intersection(ANT_SEAT).intersection(GLASS), Z.ant_seat, Z.win0)
    # [S1 C-1, C-19] STRUCTURAL bond lines (rigid epoxy class): frame on the rib insert and on the rail, glass on the rail inside the
    # antenna buffer; the PV laminate's rib-side seat bead sits on the PC shelf, which is bonded structurally to the insert (rib RFQ)
    P["bond_window_rib"] = prism(H(G.INSERT["x0"], G.INSERT["y0"], G.RIB["x1"], G.Y_WIN1).intersection(FRAME), Z.win_seat, Z.frame0)
    P["bond_window_rail"] = union(prism(rail2d.difference(ANT_SEAT).intersection(FRAME), Z.win_seat, Z.frame0),
                                  prism(rail2d.intersection(ANT_SEAT).intersection(GLASS), Z.ant_seat, Z.win0))
    if G.S2B:
        # [S2b M-5] PC corner bumpers (moulded with the ring) on the lip of the four R6 corner arcs, G.BUMPER (0.34, mini-ECO F-5) proud of the flush glass tops
        P["corner_bumpers_pc"] = prism(BUMPERS, Z.win1, Z.win1 + G.BUMPER)
        # [S2b E-1] frame ground: BW0036BG finger on a GND pad; tab formed down from the stainless frame (face plate + riser on the +X edge)
        fg = G.frame_gnd()
        fx0, fy0, fx1, fy1 = fg["face"].bounds; lx, ly = fg["land"]; c = fg["courtyard"].bounds
        bw, bl = G.J15_BODY[0], G.J15_BODY[3] - G.J15_BODY[2]
        cx, cy = (c[0] + c[2]) / 2, (c[1] + c[3]) / 2
        if fg["rot"] == 0:
            P["frame_gnd_finger"] = bx3(lx - bw / 2, ly + G.J15_BODY[2], Z.pcb1, lx + bw / 2, ly + G.J15_BODY[3], Z.finger_top)
        else:
            P["frame_gnd_finger"] = bx3(cx - bl / 2, cy - bw / 2, Z.pcb1, cx + bl / 2, cy + bw / 2, Z.finger_top)
        P["frame_gnd_tab_ss"] = union(bx3(fx0, fy0, Z.finger_top, fx1, fy1, Z.finger_top + G.FG_TAB_T),
                                      bx3(fx1 - G.FG_TAB_T, fy0, Z.finger_top + G.FG_TAB_T, fx1, fy1, Z.frame0))
    if G.S2C:
        # [S2c] lid antenna L1: printed strip + contact pad on the glass inner face; J40 compressed between AE1's FEED land and the pad
        P["lid_strip_ag"] = prism(G.LID_STRIP, Z.win0 - G.LID_STRIP_T, Z.win0)
        P["J40_finger"] = prism(G.J40["body"], Z.pcb1, Z.win0 - G.LID_STRIP_T)
    return P


COLORS = {
    "floor_film": (0.15, 0.15, 0.17, 1), "plate_E1": (0.62, 0.64, 0.68, 1), "plate_E2": (0.62, 0.64, 0.68, 1),
    "carrier_film": (0.85, 0.55, 0.15, 1), "board": (0.10, 0.42, 0.20, 1), "optical_cap": (0.55, 0.80, 0.95, 0.75),
    "parts_envelope": (0.90, 0.35, 0.30, 0.55), "SW1_body": (0.25, 0.25, 0.28, 1), "SW1_actuator": (0.95, 0.95, 0.95, 1),
    "J15_finger": (0.85, 0.70, 0.20, 1), "J18_finger": (0.85, 0.70, 0.20, 1), "J11_finger": (0.85, 0.70, 0.20, 1),
    "D10_led": (0.90, 0.15, 0.15, 1), "window_rail_lcp": (0.20, 0.20, 0.24, 1), "pv_flex_tail": (0.70, 0.50, 0.15, 1),
    "bond_window_rib": (0.95, 0.60, 0.20, 1), "bond_window_rail": (0.95, 0.60, 0.20, 1),
    "motor_psa": (0.9, 0.9, 0.9, 1), "motor_ERM": (0.70, 0.70, 0.72, 1), "panel_LS011B7DH03": (0.35, 0.40, 0.45, 1),
    "panel_FPC": (0.85, 0.55, 0.10, 1), "FPC_stiffener": (0.75, 0.45, 0.10, 1), "panel_support": (0.30, 0.30, 0.32, 1),
    "frontlight_film": (0.80, 0.95, 1.00, 0.45), "window_frame_ss": (0.72, 0.72, 0.75, 1), "window_glass": (0.60, 0.80, 0.95, 0.30),
    "pv_glass": (0.60, 0.80, 0.95, 0.30), "pv_encapsulant": (0.90, 0.92, 0.95, 0.35), "pv_flex": (0.70, 0.50, 0.15, 1),
    "pv_cell_1": (0.08, 0.10, 0.32, 1), "pv_cell_2": (0.08, 0.10, 0.32, 1), "pv_cell_3": (0.08, 0.10, 0.32, 1), "pv_cell_4": (0.08, 0.10, 0.32, 1),
    "pv_cell_5": (0.08, 0.10, 0.32, 1), "rib_pc": (0.12, 0.12, 0.14, 1), "rib_insert_ss": (0.78, 0.78, 0.80, 1), "rib_posts_ss": (0.78, 0.78, 0.80, 1),
    "ring_pc": (0.10, 0.10, 0.11, 1), "slot_A_potting": (0.5, 0.35, 0.2, 1), "slot_B_potting": (0.5, 0.35, 0.2, 1),
    "bar_A_ss": (0.78, 0.78, 0.80, 1), "bar_B_ss": (0.78, 0.78, 0.80, 1), "membrane_tpe": (0.30, 0.55, 0.85, 1),
    "E3_strip_ti": (0.66, 0.68, 0.72, 1), "E3_tab_ti": (0.66, 0.68, 0.72, 1), "pin_VBUS": (0.95, 0.78, 0.25, 1),
    "pin_GND": (0.95, 0.78, 0.25, 1), "target_1": (0.45, 0.45, 0.50, 1), "bead_pv": (0.95, 0.95, 0.85, 1),
    "bead_window": (0.95, 0.95, 0.85, 1), "bead_antenna_corner": (0.95, 0.95, 0.85, 1),
    "window_rail_ss": (0.78, 0.78, 0.80, 1), "corner_bumpers_pc": (0.10, 0.10, 0.11, 1), "frame_gnd_finger": (0.85, 0.70, 0.20, 1),
    "frame_gnd_tab_ss": (0.72, 0.72, 0.75, 1), "lid_strip_ag": (0.85, 0.85, 0.88, 1), "J40_finger": (0.85, 0.70, 0.20, 1),
}
# densities g/cm3 (E handbook values unless noted)
RHO = {"floor_film": 1.20, "plate_E1": 4.51, "plate_E2": 4.51, "carrier_film": 1.42, "board": 2.63, "optical_cap": 1.20,
       "SW1_body": None, "SW1_actuator": None, "J15_finger": None, "J18_finger": None, "J11_finger": None, "motor_psa": 1.0,
       "D10_led": None, "window_rail_lcp": 1.60, "pv_flex_tail": 1.70, "bond_window_rib": 1.15, "bond_window_rail": 1.15,
       "motor_ERM": None, "panel_LS011B7DH03": None, "panel_FPC": 1.6, "FPC_stiffener": 1.4, "panel_support": 1.20,
       "frontlight_film": 1.15, "window_frame_ss": 7.95, "window_glass": 2.50, "pv_glass": 2.50, "pv_encapsulant": 0.95,
       "pv_flex": 1.70, "pv_cell_1": 2.33, "pv_cell_2": 2.33, "pv_cell_3": 2.33, "pv_cell_4": 2.33, "pv_cell_5": 2.33, "rib_pc": 1.20,
       "rib_insert_ss": 7.95, "rib_posts_ss": 7.95, "ring_pc": 1.20, "slot_A_potting": 1.20, "slot_B_potting": 1.20,
       "bar_A_ss": 7.95, "bar_B_ss": 7.95, "membrane_tpe": 1.10, "E3_strip_ti": 4.51, "E3_tab_ti": 4.51, "pin_VBUS": 7.95,
       "pin_GND": 7.95, "target_1": 7.70, "bead_pv": 1.10, "bead_window": 1.10, "bead_antenna_corner": 1.10, "parts_envelope": None,
       "window_rail_ss": 7.95, "corner_bumpers_pc": 1.20, "frame_gnd_finger": None, "frame_gnd_tab_ss": 7.95,
       "lid_strip_ag": 10.5, "J40_finger": None}
FIXED_MASS_G = {"panel_LS011B7DH03": (0.73, "LS011B7DH03 mass max 0.73 g [DS LD29Y03 p.13]"),
                "motor_ERM": (0.45, "8 x 2.1 mm coin ERM 0.45 g [B 10, eng_b estimate]"),
                "SW1_body": (0.03, "PTS840 class tact switch [E]"), "SW1_actuator": (0.0, "in SW1_body"),
                "J15_finger": (0.005, "[E]"), "J18_finger": (0.005, "[E]"), "J11_finger": (0.005, "[E]"),
                "D10_led": (0.006, "KA-2810 class right-angle LED [E]"), "frame_gnd_finger": (0.005, "[E] BW0036BG as J11"),
                "J40_finger": (0.09, "BW0019BG 0.09 g (datasheet p.4) [S2c]")}


# ----------------------------------------------------------------------------------------------- meshing and checks
def to_tm(shape, tol=0.005):
    v, t = shape.tessellate(tol, 0.15)
    V = np.array([[p.X, p.Y, p.Z] for p in v], dtype=np.float64)
    T = np.array(t, dtype=np.int64)
    m = trimesh.Trimesh(V, T, process=True)
    m.merge_vertices(digits_vertex=6)
    return m


def to_mf(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, dtype=np.float32), tri_verts=np.asarray(m.faces, dtype=np.uint32)))


DESIGNED = {  # pairs meant to touch (shared faces: seats, bonds, contacts at the max-material stack); volume must still be ~0
    ("floor_film", "plate_E1"), ("floor_film", "plate_E2"), ("floor_film", "carrier_film"), ("plate_E1", "carrier_film"),
    ("plate_E2", "carrier_film"), ("carrier_film", "board"), ("board", "optical_cap"), ("floor_film", "optical_cap"),
    ("carrier_film", "optical_cap"), ("floor_film", "ring_pc"), ("floor_film", "motor_psa"), ("motor_psa", "motor_ERM"), ("carrier_film", "motor_psa"),
    ("board", "parts_envelope"), ("board", "SW1_body"), ("SW1_body", "SW1_actuator"), ("board", "J15_finger"),
    ("board", "J18_finger"), ("board", "J11_finger"), ("J15_finger", "pin_VBUS"), ("J18_finger", "pin_GND"),
    ("board", "D10_led"), ("board", "window_rail_lcp"), ("window_rail_lcp", "bond_window_rail"), ("bond_window_rail", "window_frame_ss"),
    ("bond_window_rail", "window_glass"), ("bond_window_rib", "rib_insert_ss"), ("bond_window_rib", "window_frame_ss"), ("bond_window_rib", "rib_pc"),
    ("bond_window_rib", "window_glass"), ("window_rail_lcp", "parts_envelope"), ("window_rail_lcp", "window_glass"), ("window_rail_lcp", "window_frame_ss"),
    ("pv_flex_tail", "pv_flex"), ("pv_flex_tail", "board"), ("pv_flex_tail", "parts_envelope"), ("pv_flex_tail", "rib_pc"),
    ("pv_flex_tail", "bead_pv"), ("D10_led", "parts_envelope"), ("bond_window_rail", "bead_antenna_corner"),
    ("J11_finger", "E3_tab_ti"), ("board", "rib_posts_ss"), ("rib_posts_ss", "rib_insert_ss"), ("rib_pc", "rib_insert_ss"),
    ("rib_pc", "rib_posts_ss"), ("panel_support", "board"), ("panel_support", "panel_LS011B7DH03"), ("panel_LS011B7DH03", "panel_FPC"),
    ("panel_FPC", "FPC_stiffener"), ("frontlight_film", "window_glass"), ("frontlight_film", "board"), ("window_frame_ss", "window_glass"),
    ("window_frame_ss", "bead_window"), ("bead_window", "ring_pc"), ("bead_window", "rib_insert_ss"), ("bead_window", "rib_pc"),
    ("bead_antenna_corner", "ring_pc"), ("bead_antenna_corner", "window_glass"), ("pv_glass", "pv_encapsulant"),
    ("pv_encapsulant", "pv_flex"), ("pv_flex", "bead_pv"), ("bead_pv", "ring_pc"), ("bead_pv", "rib_pc"), ("bead_pv", "rib_posts_ss"),
    ("ring_pc", "slot_A_potting"), ("ring_pc", "slot_B_potting"), ("ring_pc", "bar_A_ss"), ("ring_pc", "bar_B_ss"),
    ("ring_pc", "membrane_tpe"), ("ring_pc", "E3_strip_ti"), ("ring_pc", "E3_tab_ti"), ("E3_strip_ti", "E3_tab_ti"),
    ("ring_pc", "pin_VBUS"), ("ring_pc", "pin_GND"), ("ring_pc", "target_1"), ("rib_pc", "ring_pc"), ("rib_insert_ss", "ring_pc"),
    ("pv_glass", "ring_pc"), ("pv_encapsulant", "ring_pc"), ("pv_flex", "ring_pc"), ("window_glass", "ring_pc"),
    ("window_frame_ss", "ring_pc"), ("board", "FPC_stiffener"), ("board", "panel_FPC"), ("SW1_actuator", "membrane_tpe"),
    ("carrier_film", "ring_pc"), ("board", "ring_pc"), ("parts_envelope", "ring_pc"), ("panel_FPC", "parts_envelope"),
    ("frontlight_film", "parts_envelope"), ("pv_cell_1", "pv_encapsulant"), ("pv_cell_2", "pv_encapsulant"),
    ("pv_cell_3", "pv_encapsulant"), ("pv_cell_4", "pv_encapsulant"), ("pv_cell_5", "pv_encapsulant"), ("window_glass", "pv_glass"), ("bead_window", "window_glass"),
    ("rib_pc", "window_frame_ss"), ("rib_insert_ss", "window_frame_ss"), ("pv_flex", "rib_pc"), ("pv_glass", "window_glass"),
    # [S2b]
    ("window_rail_ss", "window_rail_lcp"), ("window_rail_ss", "bond_window_rail"), ("window_rail_ss", "parts_envelope"), ("window_rail_ss", "window_frame_ss"),
    ("window_rail_ss", "window_glass"), ("corner_bumpers_pc", "ring_pc"), ("corner_bumpers_pc", "E3_strip_ti"), ("corner_bumpers_pc", "window_glass"),
    ("corner_bumpers_pc", "pv_glass"), ("board", "frame_gnd_finger"), ("frame_gnd_finger", "frame_gnd_tab_ss"), ("frame_gnd_tab_ss", "window_frame_ss"),
    ("frame_gnd_finger", "parts_envelope"), ("frame_gnd_tab_ss", "bead_window"),
    # [S2c] lid antenna L1
    ("lid_strip_ag", "window_glass"), ("J40_finger", "lid_strip_ag"), ("board", "J40_finger"),
}


def interference(names, M):
    res = dict(interference=[], designed_contacts_zero_volume=[], pairs_tested=0)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            ba, bb = M[a].bounding_box(), M[b].bounding_box()
            if any(ba[k] > bb[k + 3] + 1e-6 or bb[k] > ba[k + 3] + 1e-6 for k in range(3)):
                continue
            res["pairs_tested"] += 1
            v = (M[a] ^ M[b]).volume()
            designed = (a, b) in DESIGNED or (b, a) in DESIGNED
            if v > 1e-3:
                bb = (M[a] ^ M[b]).bounding_box()
                res["interference"].append(dict(a=a, b=b, volume_mm3=round(v, 4), designed_contact=designed,
                                                bbox=[round(float(x), 2) for x in bb]))
            elif designed:
                res["designed_contacts_zero_volume"].append(f"{a}|{b}")
    return res


def gap(ma, mb, search=6.0):
    try:
        return round(float(ma.min_gap(mb, search)), 3)
    except Exception as e:   # noqa: BLE001
        return f"err {e}"


def clearance_checks(P, M):
    C = {}
    pn = G.PANEL; tol = G.PANEL_NOM["tol"]
    pmax = bx3(pn["x0"] - tol, pn["y0"] - tol, Z.panel0, pn["x1"] + tol, pn["y1"] + tol, Z.panel0 + G.PANEL_NOM["t"] + G.PANEL_NOM["t_tol"])
    Mp = to_mf(to_tm(pmax))
    C["panel at max material (32.4 x 14.4 x 0.855) -> rib insert"] = gap(Mp, M["rib_insert_ss"])
    C["panel at max material -> rib posts"] = gap(Mp, M["rib_posts_ss"])
    C["panel at max material -> ring (elbow wall)"] = gap(Mp, M["ring_pc"])
    C["panel at max material -> window frame (above, air gap)"] = gap(Mp, M["window_frame_ss"])
    C["panel at max material -> front-light film (air gap)"] = gap(Mp, M["frontlight_film"])
    C["panel nominal (0.80 allowance) -> front-light film (air gap)"] = gap(M["panel_LS011B7DH03"], M["frontlight_film"])
    C["panel nominal -> rib insert"] = gap(M["panel_LS011B7DH03"], M["rib_insert_ss"])
    C["panel nominal -> ring"] = gap(M["panel_LS011B7DH03"], M["ring_pc"])
    if G.HAS_MOTOR:
        C["motor (8.1 x 2.2 max) -> PV laminate flex (motor column margin)"] = gap(M["motor_ERM"], M["pv_flex"])
        C["motor -> board (cut-out edge)"] = gap(M["motor_ERM"], M["board"])
        C["motor -> rib shelf"] = gap(M["motor_ERM"], M["rib_pc"])
        C["motor -> plate E1 (3-D)"] = gap(M["motor_ERM"], M["plate_E1"]); C["motor -> plate E2 (3-D)"] = gap(M["motor_ERM"], M["plate_E2"])
    C["parts envelope -> PV laminate flex (0.15 clearance layer)"] = gap(M["parts_envelope"], M["pv_flex"])
    C["parts envelope -> panel support"] = gap(M["parts_envelope"], M["panel_support"])
    C["parts envelope -> rib shelf"] = gap(M["parts_envelope"], M["rib_pc"])
    C["parts envelope -> ring (K block, E3 shelf)"] = gap(M["parts_envelope"], M["ring_pc"])
    C["SW1 body -> ring (E3 shelf over it)"] = gap(M["SW1_body"], M["ring_pc"])
    C["SW1 actuator tip -> membrane nub (pre-travel gap)"] = gap(M["SW1_actuator"], M["membrane_tpe"])
    C["display FPC fold -> SW1"] = gap(M["panel_FPC"], M["SW1_body"])
    C["display FPC -> window frame"] = gap(M["panel_FPC"], M["window_frame_ss"])
    C["display FPC -> front-light tail"] = gap(M["panel_FPC"], M["frontlight_film"])
    C["window glass underside -> front-light film (laminated)"] = gap(M["window_glass"], M["frontlight_film"])
    C["window glass edge -> PV laminate glass edge (sealant joint)"] = gap(M["window_glass"], M["pv_glass"])
    C["J15 finger -> pin_GND (insulation)"] = gap(M["J15_finger"], M["pin_GND"])
    C["J18 finger -> pin_VBUS (insulation)"] = gap(M["J18_finger"], M["pin_VBUS"])
    lx15, ly15 = G.PINS[0]["land"]
    C["J15 finger body (free height 1.5, before the ring is fitted) -> panel at max material [S1 C-8]"] = gap(to_mf(to_tm(bx3(
        lx15 - G.J15_BODY[0] / 2, ly15 + G.J15_BODY[2], Z.pcb1, lx15 + G.J15_BODY[0] / 2, ly15 + G.J15_BODY[3], Z.pcb1 + G.J15_H))), Mp)
    C["J15 finger body (working height) -> panel at max material [S1 C-8]"] = gap(M["J15_finger"], Mp)
    C["J15 finger -> panel support"] = gap(M["J15_finger"], M["panel_support"])
    C["J15 / J18 / J11 courtyards inside the panel's 0.5 mm planning margin (info, mm2) [S1 C-8]"] = round(sum(
        G.finger_courtyard(l).intersection(H(pn["x0"], pn["y0"], pn["x1"], pn["y1"]).buffer(0.5, join_style=2)).area
        for l in [p["land"] for p in G.PINS] + [G.J11["land"]]), 3)
    C["window rail -> panel at max material [S1 C-1]"] = gap(M["window_rail_lcp"], Mp)
    C["window rail -> parts envelope (designed contact at the rail strip)"] = gap(M["window_rail_lcp"], M["parts_envelope"])
    C["window rail -> panel support legs"] = gap(M["window_rail_lcp"], M["panel_support"])
    C["window rail -> front-light film"] = gap(M["window_rail_lcp"], M["frontlight_film"])
    C["D10 LED -> ring wall (light path gap)"] = gap(M["D10_led"], M["ring_pc"])
    C["lid flex tail -> rib posts"] = gap(M["pv_flex_tail"], M["rib_posts_ss"])
    if G.HAS_MOTOR:
        C["lid flex tail -> motor"] = gap(M["pv_flex_tail"], M["motor_ERM"])
    C["pin_VBUS -> pin_GND (insulation)"] = gap(M["pin_VBUS"], M["pin_GND"])
    C["pin_GND -> target_1"] = gap(M["pin_GND"], M["target_1"]); C["pin_VBUS -> target_1"] = gap(M["pin_VBUS"], M["target_1"])
    C["rib posts -> panel support"] = gap(M["rib_posts_ss"], M["panel_support"])
    C["E3 strip -> membrane (finger electrode vs button)"] = gap(M["E3_strip_ti"], M["membrane_tpe"])
    C["E3 strip -> window glass edge"] = gap(M["E3_strip_ti"], M["window_glass"])
    # plan-view rule checks (2-D)
    pmax2 = H(pn["x0"] - tol, pn["y0"] - tol, pn["x1"] + tol, pn["y1"] + tol)
    C["plan: panel (max material) to the antenna keep-out, rule >= 1.5"] = round(pmax2.distance(G.keepout_poly()), 3)
    C["plan: panel (nominal) to the antenna keep-out, rule >= 1.5"] = round(H(pn["x0"], pn["y0"], pn["x1"], pn["y1"]).distance(G.keepout_poly()), 3)
    C["plan: panel glass edge (max material) to E3, rule >= 4.0"] = round(G.E3_TOP["x0"] - (pn["x1"] + tol), 3)
    # [S1 C-9] the 4.0 mm rule applied to every E3-net metal part, and to the display FPC fold
    pmx = H(pn["x0"] - tol, pn["y0"] - tol, pn["x1"] + tol, pn["y1"] + tol)
    jx_, jy_ = G.J11["land"]
    e3m = dict(strip=OUTL.intersection(H(G.E3_TOP["x0"], G.E3_TOP["y0"], BIG, G.E3_TOP["y1"])), tab=J11_FACE,
               J11_finger=H(jx_ - G.J15_BODY[0] / 2, jy_ + G.J15_BODY[2], jx_ + G.J15_BODY[0] / 2, jy_ + G.J15_BODY[3]))
    fold = (H(G.FPC_EDGE_X, G.FPC_Y[0], G.fpc_fold_outer_x() + 0.2, G.FPC_Y[1]) if G.FPC_MODEL == "s1" else
            H(G.FPC_EDGE_X, G.FPC_Y_WIDE[0] - G.FPC["lat_tol"], G.fpc_fold_outer_x() + 0.2, G.FPC_Y_WIDE[1] + G.FPC["lat_tol"]))   # [G1] as drawn, +- 0.3 lateral
    C["plan: E3-net metal to the max-material panel edge, rule >= 4.0 (strip / tab / J11 finger) [S1 C-9]"] = {k: round(v.distance(pmx), 3) for k, v in e3m.items()}
    C["plan: E3-net metal to the display FPC fold (+0.2 tolerance) (strip / tab / J11 finger) [S1 C-9]"] = {k: round(v.distance(fold), 3) for k, v in e3m.items()}
    sl = G.sw1_land()
    C["plan: SW1 courtyard / copper to the FPC fold (+0.2), rule > 0 [S1 C-4]"] = (round(H(*sl["courtyard"]).distance(fold), 3), round(H(*sl["copper"]).distance(fold), 3))
    C["plan: stainless frame to the antenna keep-out, rule >= 5.0 [S1 C-15: buffer 5.01, 128 segments]"] = round(FRAME.distance(G.keepout_poly()), 4)
    C["plan: rib insert to the antenna keep-out"] = round(H(G.INSERT["x0"], G.INSERT["y0"], G.INSERT["x1"], G.INSERT["y1"]).distance(G.keepout_poly()), 2)
    C["plan: contact pins to the antenna keep-out, REDESIGN >= 11"] = round(min(Point(*p["top"]).buffer(p["d"] / 2).distance(G.keepout_poly()) for p in G.PINS), 2)
    if G.HAS_MOTOR:
        C["plan: motor can to the antenna keep-out, rule >= 10"] = round(Point(*MC).buffer(G.MOTOR["d_max"] / 2).distance(G.keepout_poly()), 2)
    C["plan: front-light tail to the antenna keep-out"] = round(H(G.FILM_TAIL["x0"], G.FILM_TAIL["y0"], G.FILM_TAIL["x1"], G.FILM_TAIL["y1"]).distance(G.keepout_poly()), 2)
    C["plan: SW1 to the antenna keep-out"] = round(H(G.SW1["front_x"] - G.SW1["body_x"], G.SW1["cy"] - 2.35, G.SW1["front_x"] + 0.65, G.SW1["cy"] + 2.35).distance(G.keepout_poly()), 2)
    C["plan: plate E1 to the antenna keep-out, rule >= 5.0 [S1 C-15]"] = round(E1.distance(G.keepout_poly()), 4)
    # [S1 C-2] K corner: PC wall around each counterbore at its LARGEST size (head tolerance + edge), rule >= 0.30
    lam = G.lam_outline(); kcorner = {}
    for p in G.PINS:
        r = G.cb_rmax(p)
        cb = Point(*p["top"]).buffer(r, quad_segs=64)
        kcorner[p["name"]] = dict(r_max=round(r, 3), wall_to_outer_face=round(OUTL.exterior.distance(cb), 3),
                                  wall_to_K_top_edge=round(G.X_KTOP1 - (p["top"][0] + r), 3), wall_to_window_glass_edge=round((p["top"][1] - r) - G.Y_WIN1, 3),
                                  overlap_with_laminate_mm2=round(cb.intersection(lam).area, 4))
    (ax_, ay_), (bx__, by__) = G.PINS[0]["top"], G.PINS[1]["top"]
    kcorner["pitch_mm"] = round(math.hypot(bx__ - ax_, by__ - ay_), 3)
    tg = G.TARGETS[0]; tgp = Point(*tg["c"]).buffer(tg["d"] / 2)
    kcorner["target_wall_to_counterbores"] = round(min(tgp.distance(Point(*p["top"]).buffer(G.cb_rmax(p))) for p in G.PINS), 3)
    kcorner["target_wall_to_outer_face"] = round(OUTL.exterior.distance(tgp), 3)
    kcorner["rule"] = ">= 0.30 mm PC wall to the outer face, the K-top edge and the window-glass edge; no overlap with the laminate"
    C["K corner [S1 C-2]"] = kcorner
    if G.S2B:   # [S2b]
        C["[S2b] frame ground tab -> panel at max material"] = gap(M["frame_gnd_tab_ss"], Mp)
        C["[S2b] frame ground tab -> display FPC"] = gap(M["frame_gnd_tab_ss"], M["panel_FPC"])
        C["[S2b] frame ground tab -> front-light film"] = gap(M["frame_gnd_tab_ss"], M["frontlight_film"])
        C["[S2b] frame ground tab -> ring"] = gap(M["frame_gnd_tab_ss"], M["ring_pc"])
        C["[S2b] frame ground tab -> parts envelope"] = gap(M["frame_gnd_tab_ss"], M["parts_envelope"])
        C["[S2b] frame ground finger -> J11 finger (E3 net)"] = gap(M["frame_gnd_finger"], M["J11_finger"])
        C["[S2b] stainless rail section -> panel at max material"] = gap(M["window_rail_ss"], Mp)
        C["[S2b] plan: stainless rail section to the antenna keep-out, rule >= 5.0"] = round(H(G.RAIL["x0"], G.RAIL["y0"], G.RAIL["x1"], G.RAIL["y1"]).difference(ANT_BUF).distance(G.keepout_poly()), 4)
        C["[S2b] parts envelope -> PV laminate flex (air under the laminate)"] = gap(M["parts_envelope"], M["pv_flex"])
        C["[S2b] panel at max material -> front-light film (air gap after the window seat raise)"] = gap(Mp, M["frontlight_film"])
        C["[S2b] top heights: window / laminate / rim / bumper (Z, mm)"] = [Z.win1, Z.pv1, Z.rim_top, round(Z.win1 + G.BUMPER, 4)]
    C["plan: E1 to E2 web, rule >= 2.0"] = round(E1.distance(E2), 2)
    C["plan: plates to the optical cap web, rule >= 2.0"] = round(min(E1.distance(CAPP), E2.distance(CAPP)), 2)
    C["plan: J15 inner faces, each >= 3.4 x 2.2 centred on its land"] = [list(G.FACE)] * 2
    C["plan: laminate edge to silicon, min (rib side / far side / K side / corner)"] = round(min(LAM.exterior.distance(s_) for s_ in G.strips()), 3)
    return C


def void_checks(P, M):
    """[S1 C-20] cuts and functional voids against every solid: a cut is a negative volume, so interference() cannot see a solid that
    reaches into it (that is how the GND counterbore over the laminate edge got through). Each void is meshed as a solid and intersected
    with every part except the ones that are meant to be inside it. Pass: no intersection > 0.001 mm3."""
    pn = G.PANEL; tol = G.PANEL_NOM["tol"]
    voids = {}
    for p in G.PINS:   # counterbore at its largest size, from the pin's top face to the rim top
        voids[f"counterbore_{p['name']}"] = (cyl_z(p["top"][0], p["top"][1], 2 * G.cb_rmax(p), Z.rim_top - G.PIN_RECESS + 0.005, Z.rim_top + 0.3), {"ring_pc"})
    mb = G.MEMBRANE
    voids["membrane_window"] = (bx3(X_E3W - 0.01, mb["y0"], mb["z0"], L, mb["y1"], mb["z1"]), {"ring_pc", "membrane_tpe", "SW1_actuator"})
    lg = G.LUG
    voids["root_A_slot"] = (bx3(G.LAND_A[0], G.POD_W - G.WALL, 1.60, G.LAND_A[1], G.POD_W + lg["w"], 2.00), {"ring_pc", "slot_A_potting"})
    voids["root_B_slot"] = (bx3(G.LAND_B[0], -lg["w"], 1.60, G.LAND_B[1], G.WALL, 2.00), {"ring_pc", "slot_B_potting"})
    w = G.D10_WIN
    voids["D10_light_path"] = (bx3(w["x0"], w["y0"], Z.pcb1 + 0.1, w["x1"], w["y1"], Z.win0 - 0.001), {"ring_pc", "D10_led", "parts_envelope"})
    voids["panel_max_material_box"] = (bx3(pn["x0"] - tol, pn["y0"] - tol, Z.panel0, pn["x1"] + tol, pn["y1"] + tol, Z.panel0 + G.PANEL_NOM["t"] + G.PANEL_NOM["t_tol"]),
                                       {"panel_LS011B7DH03", "panel_support", "panel_FPC"})
    if G.S2C:   # [S2c] clear volume of the AE1 pocket from the board top to the glass: only J40 and the strip print may be in it
        voids["AE1_pocket_to_glass"] = (prism(G.AE1_POCKET, Z.pcb1 + 0.001, Z.win0 - 0.001), {"J40_finger", "lid_strip_ag"})
    res = {}
    for vn, (solid, allowed) in voids.items():
        mv = to_mf(to_tm(solid)); hits = []
        for nm, m in M.items():
            if nm in allowed:
                continue
            bb1, bb2 = mv.bounding_box(), m.bounding_box()
            if any(bb1[k] > bb2[k + 3] + 1e-6 or bb2[k] > bb1[k + 3] + 1e-6 for k in range(3)):
                continue
            v = (mv ^ m).volume()
            if v > 1e-3:
                hits.append(dict(part=nm, volume_mm3=round(v, 4)))
        res[vn] = dict(hits=hits, ok=not hits)
    return res


def section_2d(meshes, fn, axis, value, title, lims, aspect=3.0):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MP
    fig, ax = plt.subplots(figsize=(17, 6.2))
    normal = np.zeros(3); normal[axis] = 1.0; origin = np.zeros(3); origin[axis] = value
    other = 0 if axis == 1 else 1
    seen = []
    for nm, m in meshes.items():
        sec = m.section(plane_origin=origin, plane_normal=normal)
        if sec is None:
            continue
        c = COLORS.get(nm, (0.7, 0.7, 0.7, 1))
        for ent in sec.entities:
            pts = sec.vertices[ent.points]
            if len(pts) < 3:
                continue
            ax.add_patch(MP(np.c_[pts[:, other], pts[:, 2]], closed=True, fc=c[:3], alpha=max(c[3], 0.45), ec="k", lw=0.3))
        seen.append(nm)
    ax.set_xlim(*lims[0]); ax.set_ylim(*lims[1]); ax.set_aspect(aspect)
    ax.set_xlabel(f"{'XY'[other]} mm"); ax.set_ylabel(f"Z mm (x{aspect:g} vertical exaggeration)")
    ax.grid(alpha=0.3); ax.set_title(title, fontsize=10)
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[k][:3]) for k in seen]
    ax.legend(handles, seen, fontsize=6.5, ncol=8, loc="upper center", bbox_to_anchor=(0.5, -0.13))
    fig.tight_layout(); fig.savefig(fn, dpi=125); plt.close(fig)


def main():
    t0 = time.time()
    P = build()
    print(f"built {len(P)} parts {time.time() - t0:.1f}s", flush=True)
    for nm, s in P.items():
        s.label = nm; s.color = Color(*COLORS.get(nm, (0.7, 0.7, 0.7, 1)))
    asm = Compound(label=f"SolarBand_V3F_pod_{TAG}", children=list(P.values()))
    export_step(asm, os.path.join(OUT, f"V3F_{TAG}_pod.step"))
    export_gltf(asm, os.path.join(OUT, f"V3F_{TAG}_pod.glb"), binary=True, linear_deflection=0.01, angular_deflection=0.2)
    print(f"exported STEP + GLB {time.time() - t0:.1f}s", flush=True)
    meshes, M, vol, wt = {}, {}, {}, {}
    for nm, s in P.items():
        m = to_tm(s); meshes[nm] = m; wt[nm] = bool(m.is_watertight); M[nm] = to_mf(m)
        vol[nm] = dict(brep_mm3=round(s.volume, 3), mesh_mm3=round(M[nm].volume(), 3), status=str(M[nm].status()))
    print(f"meshed {time.time() - t0:.1f}s", flush=True)
    names = list(P)
    res = interference(names, M)
    res["clearance_mm"] = clearance_checks(P, M)
    res["void_checks"] = void_checks(P, M)
    res["volumes"] = vol; res["watertight"] = wt
    mass = {}
    for nm in names:
        if nm in FIXED_MASS_G:
            mass[nm] = dict(g=FIXED_MASS_G[nm][0], basis=FIXED_MASS_G[nm][1])
        elif RHO.get(nm):
            vv = P[nm].volume
            if nm == "board":
                vv *= 1.0 / 1.10      # nominal 1.0 mm board for mass (CAD carries the 1.10 max-material thickness)
            mass[nm] = dict(g=round(vv * RHO[nm] / 1000.0, 4), basis=f"CAD volume x {RHO[nm]} g/cm3")
    res["mass_g"] = mass
    res["z_stack"] = {k: getattr(Z, k) for k in Z.__dataclass_fields__} | dict(pod_pv=Z.pod_pv, pod_win=Z.pod_win)
    res["pod_L"] = G.POD_L; res["pod_W"] = G.POD_W; res["opt"] = G.OPT; res["tag"] = G.TAG
    json.dump(res, open(os.path.join(OUT, f"checks_pod_{TAG}.json"), "w"), indent=1, default=str)
    print("interference:", res["interference"])
    for k, v in res["clearance_mm"].items():
        print(f"  {k}: {v}")
    print(f"checked {time.time() - t0:.1f}s", flush=True)
    # ---------------- renders
    import zrender
    def plist(names_=None, clip=None, alpha=None, explode=None, skip=()):
        Lst = []
        for nm, m in meshes.items():
            if (names_ is not None and nm not in names_) or nm in skip:
                continue
            mm = m
            if clip is not None:
                mm = m.slice_plane(clip[0], clip[1], cap=True)
                if mm is None or len(mm.faces) == 0:
                    continue
            V = np.asarray(mm.vertices).copy()
            if explode:
                V[:, 2] += explode.get(nm, 0.0)
            c = list(COLORS.get(nm, (0.7, 0.7, 0.7, 1)))
            if alpha and nm in alpha:
                c[3] = alpha[nm]
            Lst.append((nm, V, np.asarray(mm.faces), c))
        return Lst
    noenv = ("parts_envelope",)
    zrender.render(plist(skip=noenv), os.path.join(OUT, f"render_top_{TAG}.png"), 90, -90, size=(1500, 1250),
                   title=f"V3-F pod {TAG}: top (sky) view: window glass over the panel, rib, PV strips, K corner (2 pins), E3 rim")
    zrender.render(plist(skip=noenv), os.path.join(OUT, f"render_iso_{TAG}.png"), 32, -58, size=(1500, 1100),
                   title=f"V3-F pod {TAG}: assembled, sky side")
    zrender.render(plist(skip=noenv), os.path.join(OUT, f"render_bottom_{TAG}.png"), -90, -90, size=(1500, 1250),
                   title=f"V3-F pod {TAG}: skin view: floor film, Ti plates E1/E2, optical cap (PPG mesa), lugs")
    exp = {"window_glass": 9.0, "pv_glass": 9.0, "pv_encapsulant": 8.0, "pv_cell_1": 8.0, "pv_cell_2": 8.0, "pv_cell_3": 8.0, "pv_cell_4": 8.0,
           "pv_flex": 7.0, "frontlight_film": 7.6, "window_frame_ss": 7.6, "bead_window": 6.6, "bead_pv": 6.0, "bead_antenna_corner": 6.6,
           "panel_LS011B7DH03": 5.0, "panel_FPC": 5.0, "FPC_stiffener": 5.0, "panel_support": 4.0, "rib_pc": 4.5, "rib_insert_ss": 4.5,
           "rib_posts_ss": 4.5, "ring_pc": 2.5, "E3_strip_ti": 2.5, "E3_tab_ti": 2.5, "pin_VBUS": 2.5, "pin_GND": 2.5, "target_1": 2.5,
           "membrane_tpe": 2.5, "slot_A_potting": 2.5, "slot_B_potting": 2.5, "bar_A_ss": 2.5, "bar_B_ss": 2.5,
           "board": 0.0, "parts_envelope": 0.0, "SW1_body": 0.0, "SW1_actuator": 0.0, "J15_1_finger": 0.0, "J15_2_finger": 0.0,
           "J11_finger": 0.0, "motor_ERM": -2.0, "motor_psa": -2.0, "carrier_film": -2.5, "optical_cap": -4.0,
           "floor_film": -5.0, "plate_E1": -5.0, "plate_E2": -5.0}
    zrender.render(plist(explode=exp, alpha={"parts_envelope": 0.35}), os.path.join(OUT, f"render_exploded_{TAG}.png"), 26, -60,
                   size=(1500, 1700), title=f"V3-F pod {TAG}: exploded along Z (red = parts envelope by zone, max-material heights)")
    for nm_, (o, n_), ttl in ((f"cut_rib_X20_{TAG}", ((20.0, 0, 0), (1, 0, 0)), "cut at X 20 (through the motor, the rib and the window)"),
                              (f"cut_window_Y12p7_{TAG}", ((0, G.AA_CY, 0), (0, 1, 0)), f"cut at Y {G.AA_CY:.1f} (through the panel, FPC fold, SW1 side)")):
        zrender.render(plist(clip=(np.array(o, float), np.array(n_, float)), skip=noenv, alpha={"window_glass": 0.4, "pv_glass": 0.4}),
                       os.path.join(OUT, f"render_{nm_}.png"), 18, -75 if n_[0] else -20, size=(1500, 1000), title=f"V3-F pod {TAG}: {ttl}")
    section_2d(meshes, os.path.join(OUT, f"section_X20_rib_motor_{TAG}.png"), 0, 20.0,
               f"V3-F {TAG}: section X = 20.0 (motor centre): antenna wall | window column (glass 0.70, film, panel, support, low parts) | rib with insert and post | PV column | motor | far wall",
               ((-3.5, 35.5), (-1.2, 4.8)))
    section_2d(meshes, os.path.join(OUT, f"section_X16_post_{TAG}.png"), 0, 16.0,
               f"V3-F {TAG}: section X = 16.0 (through a rib post)", ((15.0, 26.0), (-1.0, 4.6)), aspect=2.0)
    section_2d(meshes, os.path.join(OUT, f"section_Y{G.AA_CY:.1f}_window_{TAG}.png"), 1, G.AA_CY,
               f"V3-F {TAG}: section Y = {G.AA_CY:.1f}: elbow wall | panel (window column) | FPC exit, 180 deg fold, return to J13 | SW1 + membrane | E3 rim",
               ((-0.5, L + 0.5), (-1.2, 4.8)), aspect=3.0)
    section_2d(meshes, os.path.join(OUT, f"section_Y{G.PINS[0]['top'][1]:.1f}_contacts_{TAG}.png"), 1, G.PINS[0]["top"][1],
               f"V3-F {TAG}: section Y = {G.PINS[0]['top'][1]:.1f}: contact pin VBUS (recessed top, inner face on J15) | PV laminate | E3 rim",
               ((-0.5, 12.0), (-0.5, 4.5)), aspect=2.0)
    section_2d(meshes, os.path.join(OUT, f"section_Y{G.SW1['cy']:.1f}_button_{TAG}.png"), 1, G.SW1["cy"],
               f"V3-F {TAG}: section Y = {G.SW1['cy']:.1f}: SW1 (PTS840, 1.35 mm), actuator, TPE membrane in the hand-end wall, E3 wrap above",
               ((L - 9.0, L + 0.6), (-0.6, 4.6)), aspect=1.5)
    print(f"done {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
