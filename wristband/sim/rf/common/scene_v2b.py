"""SolarBand V2-B (REDESIGN_V2 revision 1) RF scene for gate 3a (SIM-10 / SIM-11).

Board frame (as SIM-10 v1): X 0..37 along the forearm (X = 0 elbow side, X = 37 hand side),
Y 0..29 across the wrist (Y = 0 = antenna edge, Y = 29 = cell-bay edge), units mm.
z = 0 is the board's SKIN face, z = 1.0 its SKY face (parts, RF line, printed radiator on F.Cu).

Source tags:  [R5.x] = redesign/REDESIGN_V2.md section 5.x,  [LD] = redesign/enclosure.md (Lens D),
[PR] = redesign/attack_physics/calc/rf/run_v2b.py (review surrogate model),  [JLC] = JLC stack API
(cache/v2/g3a/jlc/stack_6L_1p0_1oz_0p5oz.json),  [GAB] = Gabriel 1996 (as sim/rf/common/scene.py),
[E] = estimate of this lane.  Every [E] is listed in REPORT.md.

Z stack used (nominal column of [R5.2], snapped to the mesh planes named in mesh_v2b.py):
  skin plane            z = -0.35   (skin touches the floor film; cap 0.80 proud is pressed into the skin)
  floor PC film 0.25    z = -0.35 .. -0.10  } modelled as ONE 0.35 mm layer, PC values [E]
  carrier film 0.10     z = -0.10 ..  0.00  }
  Ti plates 0.25        z = -0.35 .. -0.175 (PEC; real -0.35 .. -0.10: the mesh has 2 cells in the floor)
  board 1.0 (JLC06101H) z =  0.00 ..  1.00
  free height 1.95      z =  1.00 ..  2.95  (lid underside; [R5.2] 1.85 with the 1.10 mm max board)
  lid backsheet copper  z =  3.00           (real 2.95 .. 3.07 flex)
  PV cell back metal    z =  3.25           (real 3.22 .. 3.385 cells)
  encapsulant           z =  3.00 ..  3.50  (real 3.07 .. 3.585 incl. cells)
  cover glass 0.50      z =  3.50 ..  4.00  (real 3.585 .. 4.085)
"""
import math
from dataclasses import dataclass, asdict, field
import numpy as np
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union

from geom import Mat, AIR, PEC, Box, PolyZ, PolyX, EllCylX, IfacePlane

# ------------------------------------------------------------------ materials
# Board laminate without copper: JLC06101H-3313 (6 layers, 1.0 mm): 2 x 3313 0.0994 (4.1), 2 x core 0.25 (4.6),
# 7628 0.2104 (4.4) -> thickness-weighted er 4.44 [JLC]; tan d 0.02 [E] (JLC publishes none)
FR4 = Mat("fr4_1p0", eps=4.44, tand=0.02)
PC = Mat("pc", eps=3.0, tand=0.01)                 # ring, floor film, strap bars, cap [E] (v1 SIM-10 value)
GLASS = Mat("glass_gg3", eps=7.20, tand=0.024)     # Corning Gorilla Glass 3 PI sheet p.1, 2.47 GHz [LD F-10] verified
ENCAP = Mat("encapsulant", eps=2.8, tand=0.03)     # EVA / POE film + polyimide backsheet [E]
STRAP = Mat("textile", eps=2.0, tand=0.02)         # woven nylon hook-and-loop band, dry [E]
STRAP_WET = Mat("textile_wet", eps=10.0, sigma=0.5)  # sweat-soaked band: mixture estimate [E]
SLEEVE = Mat("sleeve", eps=2.0, tand=0.04)         # dry cotton / polyester cuff [E]
SKIN = Mat("skin_dry", eps=38.02, sigma=1.459)     # [GAB] 2.44 GHz
FAT = Mat("fat", eps=5.281, sigma=0.1041)          # [GAB]
MUSCLE = Mat("muscle", eps=52.74, sigma=1.732)     # [GAB]

BOARD_T = 1.0
Z_FLOOR = -0.35
Z_PLATE_TOP = 0.0                                   # plates PEC through the whole floor (RF-shorted to the board anyway:
                                                    # >= 80 mm2 at 0.1-0.4 mm = tens of pF, plus the 12 pF TVS [LD 231])
Z_LID_CU = 3.0
Z_PV = 3.0                                          # cell back metal modelled in the backsheet-copper plane (real +0.22 mm)
Z_GLASS0, Z_GLASS1 = 3.5, 4.0
CASE_OUT = (-1.5, -1.5, 38.5, 30.5)                # 40 x 32 case around the 37 x 29 board [R5.3]
WALL = 1.0                                          # [R5.5]
LID = (-1.5, -1.5, 36.0, 30.5)                      # lid 39.6 x 31.6 (drawn 0.2 larger: 0.5 mm grid), set back 2.5 mm at the E3 end [R5.3/5.9]
PV_SHEET = (2.5, 4.5, 30.0, 26.5)                   # four strips 27.7 x 5.2: board X 2.2..29.9, Y 4.5..26.5 [R5.3]
FINGER_CU = (30.0, 4.5, 35.5, 26.5)                 # backsheet copper under the finger rest, tied to PV- [R5.3]
CUT = (1.5, 18.0, 35.5, 29.0)                       # cell cut-out 11.0 x 34 [R5.3] = BAY of v2/layout/tools/lgeom.py
CELL = (3.5, 18.5, 33.5, 28.5)                      # bare cell 10 x 30 [R5.2]
Z_CELL = (0.5, 2.5)                                 # real 0.25 .. 2.35 (shim 0.15 + PSA 0.10 above z = 0; cell 2.1)
E1 = (-1.0, 11.0, 11.5, 29.5)                       # Ti plate, antenna side, 12.5 x 18.5 [lgeom.py PLATE_E1, from LD]
E2 = (25.0, 7.0, 38.0, 29.5)                        # Ti plate, hand side, 13 x 22.5 [lgeom.py PLATE_E2, from LD]
CAP = (13.0, 10.0, 24.0, 17.0)                      # optical cap 11 x 7 [lgeom.py CAP]; modelled 1.0 mm proud (real 0.80)
BAR_X = (7.5, 29.5)                                 # strap bars 22 mm long, centred on the case [R5.4]
G_SNAP = 0.5


@dataclass
class Cand:
    """One radiator candidate.  kind:
       'board_ifa' : meander IFA (TI AN043 topology) on F.Cu (z = 1.0) in an all-layer board keep-out
       'lid_rim'   : IFA on the lid backsheet (z = 3.0) along the Y = 0 rim, fed and shorted by two spring posts;
                     the board keeps its ground under it except a small feed-pad opening
       'lid_ifa'   : the board_ifa copper lifted to the lid backsheet (z = 3.0), feed and short by spring posts,
                     board keep-out kept under it
    u = distance leftward from x_right, v = height above the ground edge toward the board edge (as v1)."""
    kind: str = "board_ifa"
    name: str = "A"
    # ---- board_ifa / lid_ifa (meander IFA)
    gnd_edge: float = 5.5
    x_right: float = 15.5
    d1: float = 0.5
    w1: float = 1.0
    w: float = 0.5
    d5: float = 1.5
    l3: float = 5.0
    v_bar: float = 4.0
    l4: float = 2.0
    l5: float = 1.5
    l2s: tuple = (2.5, 2.5)
    l1: float = 3.0
    corner_r: float = 4.5           # board corner at the antenna: case R6, wall 1.0, clearance 0.5 [E]
    edge_clear: float = 0.3
    short_into_gnd: float = 0.5
    # ---- lid_rim
    rim_y0: float = -1.0            # arm strip Y range on the backsheet (over the wall top)
    rim_y1: float = -0.5
    rim_x_open: float = 3.5
    rim_x_short: float = 22.5       # left edge of the short post (post = x .. x + 0.5)
    rim_feed_dx: float = 2.0        # feed post left edge = rim_x_short - rim_feed_dx
    rim_pad_w: float = 1.0          # feed pad (spring land) width on the board (post edge - 0.5 .. + 0.5)
    rim_ko_y: float = 3.5           # depth of the feed-pad opening in the board ground
    rim_ko_halfw: float = 1.5       # opening = pad centre +- this
    rim_board_ko: tuple = ()        # optional extra board keep-out (x0, y0, x1, y1) under the arm
    post_y0: float = 0.5            # spring posts (0.5 x 0.5 PEC) [E for the real 3.0 x 1.0 spring finger]
    post_y1: float = 1.0
    port_gap: float = 0.5


def board_outline(r=4.5, W=37.0, H=29.0):
    """outline with the antenna corner (0, 0) rounded to r; other corners left square (far from the antenna)"""
    arc = [(r + r * math.cos(t), r + r * math.sin(t)) for t in np.linspace(1.5 * math.pi, math.pi, 65)]
    arc[0] = (r, 0.0); arc[-1] = (0.0, r)
    return Polygon(arc + [(0.0, H), (W, H), (W, 0.0)])


def ifa_polygons(c: Cand):
    """Meander IFA copper (board frame) + feed / short info + fit report.  Copper is NOT clipped."""
    G, XR = c.gnd_edge, c.x_right

    def R(u0, u1, v0, v1):
        return sbox(XR - max(u0, u1), G - max(v0, v1), XR - min(u0, u1), G - min(v0, v1))
    rects = {}
    vb0, vb1 = c.v_bar, c.v_bar + c.w
    us0 = c.d1; us1 = us0 + c.w1
    uf0 = us1 + c.d5; uf1 = uf0 + c.w
    rects["short_leg"] = R(us0, us1, -c.short_into_gnd, vb0)
    rects["feed_leg"] = R(uf0, uf1, c.port_gap, vb0)
    ub_end = us0 + c.l3
    rects["bar1"] = R(us0, ub_end, vb0, vb1)
    vc0 = vb0 - c.l4; vc1 = vc0 + c.w
    u = ub_end
    length = (vb0 + c.w / 2 - c.port_gap) + ((ub_end - c.w / 2) - (uf0 + c.w / 2))
    for m, l2 in enumerate(c.l2s):
        dl0, dl1 = u - c.w, u
        ul0, ul1 = u + c.l5, u + c.l5 + c.w
        rects[f"down{m}"] = R(dl0, dl1, vc0, vb0)
        rects[f"conn{m}"] = R(dl0, ul1, vc0, vc1)
        rects[f"up{m}"] = R(ul0, ul1, vc0, vb0)
        rects[f"bar{m + 2}"] = R(ul0, ul0 + l2, vb0, vb1)
        u = ul0 + l2
        length += 2 * c.l4 + (c.l5 + c.w) + (l2 - c.w)
    length += c.w / 2
    rects["open_leg"] = R(u - c.w, u, vb0 - c.l1, vb0)
    length += c.l1
    cu = unary_union(list(rects.values()))
    keep = board_outline(c.corner_r).buffer(-c.edge_clear, join_style=1)
    outside = cu.difference(keep).area
    b = cu.bounds
    info = dict(copper_outside_board_mm2=outside, bounds=b, copper_area_mm2=cu.area,
                min_gap_open_leg_to_gnd=vb0 - c.l1, meander_bottom_above_gnd=vc0,
                centre_line_length_mm=length,
                fits=bool(outside < 1e-9 and b[2] <= XR + 1e-9 and b[1] >= 0 and vb0 - c.l1 >= 0.5 - 1e-9
                          and vc0 >= 0.5 - 1e-9 and (ub_end - c.w) - uf1 >= 0.5 - 1e-9))
    feed = dict(x0=XR - uf1, x1=XR - uf0, y_gap0=G - c.port_gap, y_gap1=G)
    short = dict(x0=XR - us1, x1=XR - us0)
    return dict(copper=cu, rects=rects, feed=feed, short=short, info=info)


def check_grid(c: Cand):
    bad = {}
    for k, v in asdict(c).items():
        if k in ("corner_r", "edge_clear", "port_gap", "kind", "name", "rim_board_ko"):
            continue
        for x in (v if isinstance(v, (tuple, list)) else [v]):
            if isinstance(x, float) and abs(x / G_SNAP - round(x / G_SNAP)) > 1e-9:
                bad[k] = v
    return bad


@dataclass
class Var:
    """scene variant (wearer / environment)"""
    phantom: bool = True
    wrist_a: float = 28.0           # as SIM-10 v1: top curvature radius a^2/b = 35 mm [ARCH 6.3]
    wrist_b: float = 22.4
    skin_t: float = 1.5             # [E]
    fat_t: float = 2.5              # [E]
    wrist_x0: float = -20.0
    wrist_x1: float = 57.0
    skin_dz: float = 0.0            # + = skin further from the floor (loose strap), - = band pressed into the tissue
    strap: str = "dry"              # "dry" | "wet" | "none"
    hand: str = "none"              # "none" | "cover" (palm / fingers lying on the lid) | "finger" (finger on E3)
    sleeve: bool = False            # 2 mm fabric draped over the lid and the long walls
    dock: bool = False              # light dock: LED board (metal) 8 mm above the lid + PC cradle walls [E]
    with_lid: bool = True
    with_pv: bool = True
    pv_tail_x: float = 34.0         # PV flex tail to the board (hand end) [E, as PR]


def _ellipse(yc, zc, a, b, n=128):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return Polygon(list(zip(yc + a * np.cos(t), zc + b * np.sin(t))))


def build_scene(c: Cand, v: Var):
    """returns (prims, port, ant) ; prims in precedence order (later dielectrics override earlier; PEC on top)."""
    P = []
    yc = 14.5
    z_skin = Z_FLOOR - v.skin_dz
    zc = z_skin - v.wrist_b
    a, b = v.wrist_a, v.wrist_b
    ox0, oy0, ox1, oy1 = CASE_OUT
    # ---------------- strap: 1.25 mm textile band, through the bar slots and around the wrist [E geometry]
    if v.strap != "none":
        sm = STRAP if v.strap == "dry" else STRAP_WET
        shell = _ellipse(yc, zc, a + 1.25, b + 1.25).difference(_ellipse(yc, zc, a, b))
        for half in (sbox(-60, -80, yc - 17.0, 20), sbox(yc + 17.0, -80, 90, 20)):
            for q in (shell.intersection(half).geoms if hasattr(shell.intersection(half), "geoms") else [shell.intersection(half)]):
                if q.area > 1e-6:
                    P.append(PolyX(q, BAR_X[0], BAR_X[1], sm, "strap_ring"))
        # vertical run from the wrist up through the slot between the wall and the bar (1.0 mm slot)
        z_at = zc + b * math.sqrt(max(0.0, 1 - (17.0 / a) ** 2))
        P.append(Box((BAR_X[0], oy0 - 1.0, z_at - 0.5), (BAR_X[1], oy0, 2.5), sm, "strap_slot_y0"))
        P.append(Box((BAR_X[0], oy1, z_at - 0.5), (BAR_X[1], oy1 + 1.0, 2.5), sm, "strap_slot_y1"))
    # ---------------- wrist phantom (rigid ellipse; the band displaces it where they overlap)
    if v.phantom:
        P.append(EllCylX(yc, zc, a, b, v.wrist_x0, v.wrist_x1, SKIN, tag="skin"))
        P.append(EllCylX(yc, zc, a - v.skin_t, b - v.skin_t, v.wrist_x0, v.wrist_x1, FAT, tag="fat"))
        t2 = v.skin_t + v.fat_t
        P.append(EllCylX(yc, zc, a - t2, b - t2, v.wrist_x0, v.wrist_x1, MUSCLE, tag="muscle"))
    # ---------------- hand / sleeve / dock (before the band so that the band overrides them)
    if v.sleeve:
        P.append(Box((-6.0, -6.0, Z_GLASS1), (43.0, 35.0, Z_GLASS1 + 2.0), SLEEVE, "sleeve_top"))
        P.append(Box((-6.0, -6.0, -3.0), (43.0, -4.0, Z_GLASS1), SLEEVE, "sleeve_y0"))
        P.append(Box((-6.0, 33.0, -3.0), (43.0, 35.0, Z_GLASS1), SLEEVE, "sleeve_y1"))
    if v.hand == "cover":
        # the other hand lying flat on the band: skin 1.5 + muscle, 70 x 50 x 14 mm, touching the glass [E]
        P.append(Box((-16.0, -10.0, Z_GLASS1), (54.0, 40.0, Z_GLASS1 + 14.0), MUSCLE, "hand_core"))
        P.append(Box((-16.0, -10.0, Z_GLASS1), (54.0, 40.0, Z_GLASS1 + 1.5), SKIN, "hand_skin"))
    if v.hand == "finger":
        # finger pad on the E3 strip and the finger rest (ECG posture): 16 x 40 x 12 mm bar along Y at the hand end [E]
        P.append(Box((27.0, -6.0, Z_GLASS1), (43.0, 34.0, Z_GLASS1 + 12.0), MUSCLE, "finger_core"))
        P.append(Box((27.0, -6.0, Z_GLASS1), (43.0, 34.0, Z_GLASS1 + 1.5), SKIN, "finger_skin"))
    if v.dock:
        # cradle: PC tray 2 mm under and around the band, open top closed by the LED board [E]
        P.append(Box((-5.5, -7.5, -3.0), (42.5, 36.5, Z_FLOOR - 0.5), PC, "dock_base"))
        P.append(Box((-5.5, -7.5, -3.0), (-3.5, 36.5, 12.0), PC, "dock_wx0")); P.append(Box((40.5, -7.5, -3.0), (42.5, 36.5, 12.0), PC, "dock_wx1"))
        P.append(Box((-5.5, -7.5, -3.0), (42.5, -5.5, 12.0), PC, "dock_wy0")); P.append(Box((-5.5, 34.5, -3.0), (42.5, 36.5, 12.0), PC, "dock_wy1"))
    # ---------------- band interior = air (overrides tissue / strap / sleeve where the rigid shapes overlap)
    P.append(Box((ox0, oy0, Z_FLOOR), (ox1, oy1, Z_GLASS1), AIR, "band_interior"))
    # ---------------- ring walls (PC), floor (PC film + carrier film), rim block at the E3 end, strap bars
    zt = Z_LID_CU
    P += [Box((ox0, oy0, Z_FLOOR), (ox1, oy0 + WALL, zt), PC, "wall_y0"),
          Box((ox0, oy1 - WALL, Z_FLOOR), (ox1, oy1, zt), PC, "wall_y1"),
          Box((ox0, oy0, Z_FLOOR), (ox0 + WALL, oy1, zt), PC, "wall_x0"),
          Box((ox1 - WALL, oy0, Z_FLOOR), (ox1, oy1, zt), PC, "wall_x1"),
          Box((ox0, oy0, Z_FLOOR), (ox1, oy1, 0.0), PC, "floor"),
          Box((LID[2], oy0, zt), (ox1, oy1, Z_GLASS1), PC, "rim_E3_end"),
          Box(CAP[:2] + (Z_FLOOR - 1.0,), CAP[2:] + (Z_FLOOR,), PC, "ppg_cap")]
    zb = Z_FLOOR + 3.0                               # bars 2.0 x 3.0 x 22, 1.0 mm strap slot to the wall [R3 G-1, E]
    P += [Box((BAR_X[0], oy0 - 3.0, Z_FLOOR), (BAR_X[1], oy0 - 1.0, zb), PC, "bar_y0"),
          Box((BAR_X[0] - 2.0, oy0 - 3.0, Z_FLOOR), (BAR_X[0], oy0, zb), PC, "bar_y0_end0"),
          Box((BAR_X[1], oy0 - 3.0, Z_FLOOR), (BAR_X[1] + 2.0, oy0, zb), PC, "bar_y0_end1"),
          Box((BAR_X[0], oy1 + 1.0, Z_FLOOR), (BAR_X[1], oy1 + 3.0, zb), PC, "bar_y1"),
          Box((BAR_X[0] - 2.0, oy1, Z_FLOOR), (BAR_X[0], oy1 + 3.0, zb), PC, "bar_y1_end0"),
          Box((BAR_X[1], oy1, Z_FLOOR), (BAR_X[1] + 2.0, oy1 + 3.0, zb), PC, "bar_y1_end1")]
    # ---------------- lid dielectrics: encapsulant + backsheet, cover glass
    if v.with_lid:
        P.append(Box((LID[0], LID[1], Z_LID_CU), (LID[2], LID[3], Z_GLASS0), ENCAP, "lid_encap"))
        P.append(Box((LID[0], LID[1], Z_GLASS0), (LID[2], LID[3], Z_GLASS1), GLASS, "lid_glass"))
    # ---------------- board: ground (PEC, all layers merged) and FR-4 openings
    gnd = sbox(0, 0, 37.0, CUT[1]).union(sbox(0, CUT[1], CUT[0], 29.0)).union(sbox(CUT[2], CUT[1], 37.0, 29.0))
    ant = None
    openings = []
    if c.kind in ("board_ifa", "lid_ifa"):
        openings.append(sbox(0, 0, c.x_right, c.gnd_edge))
    if c.kind == "lid_rim":
        xfc = c.rim_x_short - c.rim_feed_dx + 0.25
        openings.append(sbox(xfc - c.rim_ko_halfw, 0, xfc + c.rim_ko_halfw, c.rim_ko_y))
        if c.rim_board_ko:
            openings.append(sbox(*c.rim_board_ko))
    op = unary_union(openings) if openings else None
    if op is not None:
        gnd = gnd.difference(op)
        keep_poly = op.intersection(board_outline(c.corner_r))
        for q in (keep_poly.geoms if hasattr(keep_poly, "geoms") else [keep_poly]):
            P.append(PolyZ(q, 0.0, BOARD_T, FR4, "fr4_opening"))
            P.append(IfacePlane(q, BOARD_T, FR4, AIR, "fr4_top_iface"))
            P.append(IfacePlane(q, 0.0, PC, FR4, "fr4_bot_iface"))
    # ground as non-overlapping rectangles (PEC boxes)
    for k, r in enumerate(_rect_decompose(gnd)):
        P.append(Box((r[0], r[1], 0.0), (r[2], r[3], BOARD_T), PEC, f"gnd_{k}"))
    # ---------------- radiator
    if c.kind == "board_ifa":
        ant = ifa_polygons(c)
        P.append(PolyZ(ant["copper"], BOARD_T, BOARD_T, PEC, "ifa"))
        f = ant["feed"]
        port = dict(x0=f["x0"], x1=f["x1"], y_gap0=f["y_gap0"], y_gap1=f["y_gap1"], z=BOARD_T)
    elif c.kind == "lid_ifa":
        ant = ifa_polygons(c)
        f = ant["feed"]; s = ant["short"]
        # lid copper = the IFA without the lower 1.5 mm of its feed / short legs (they become the spring posts)
        G = c.gnd_edge
        lidcu = ant["copper"].difference(sbox(-5, G - 2.5, 40, G + 5))
        P.append(PolyZ(lidcu, Z_LID_CU, Z_LID_CU, PEC, "ifa_lid"))
        # feed pad on the board (in the keep-out) + post; short post from a ground tongue.  The posts stand
        # 2.5-3.0 mm from the ground edge so that the Ampere loop of the port cuts the pad, not the post.
        P.append(PolyZ(sbox(f["x0"], G - 3.0, f["x1"], G - c.port_gap), BOARD_T, BOARD_T, PEC, "feed_pad"))
        P.append(Box((f["x0"], G - 3.0, BOARD_T), (f["x1"], G - 2.5, Z_LID_CU), PEC, "feed_post"))
        P.append(Box((s["x0"], G - 3.0, BOARD_T), (s["x1"], G - 2.5, Z_LID_CU), PEC, "short_post"))
        P.append(PolyZ(sbox(s["x0"], G - 3.0, s["x1"], G + 0.5), BOARD_T, BOARD_T, PEC, "short_pad"))
        port = dict(x0=f["x0"], x1=f["x1"], y_gap0=f["y_gap0"], y_gap1=f["y_gap1"], z=BOARD_T)
        ant["lid_copper"] = lidcu
    elif c.kind == "lid_rim":
        xs = c.rim_x_short; xf = xs - c.rim_feed_dx
        arm = sbox(c.rim_x_open, c.rim_y0, xs + 0.5, c.rim_y1)
        stub_s = sbox(xs, c.rim_y0, xs + 0.5, c.post_y1)
        stub_f = sbox(xf, c.rim_y0, xf + 0.5, c.post_y1)
        lidcu = unary_union([arm, stub_s, stub_f])
        P.append(PolyZ(lidcu, Z_LID_CU, Z_LID_CU, PEC, "rim_ifa"))
        P.append(Box((xs, c.post_y0, BOARD_T), (xs + 0.5, c.post_y1, Z_LID_CU), PEC, "short_post"))
        P.append(Box((xf, c.post_y0, BOARD_T), (xf + 0.5, c.post_y1, Z_LID_CU), PEC, "feed_post"))
        px0 = xf + 0.25 - c.rim_pad_w / 2; px1 = xf + 0.25 + c.rim_pad_w / 2
        pad = sbox(px0, c.post_y0, px1, c.rim_ko_y - c.port_gap)
        P.append(PolyZ(pad, BOARD_T, BOARD_T, PEC, "feed_pad"))
        port = dict(x0=px0, x1=px1, y_gap0=c.rim_ko_y - c.port_gap, y_gap1=c.rim_ko_y, z=BOARD_T)
        length = (c.rim_ko_y - c.port_gap - c.post_y0) + (Z_LID_CU - BOARD_T) + (c.post_y0 - c.rim_y0) + (xf - c.rim_x_open)
        ant = dict(copper=lidcu, lid_copper=lidcu, pad=pad, feed=port,
                   short=dict(x0=xs, x1=xs + 0.5),
                   info=dict(fits=True, bounds=lidcu.bounds, copper_area_mm2=lidcu.area,
                             feed_path_length_mm=length, arm_length_mm=xs + 0.5 - c.rim_x_open))
    else:
        raise ValueError(c.kind)
    # ---------------- bare cell (pouch = metal), RF-tied to the plates below by 0.35 mm of film; tab to the board
    P.append(Box(CELL[:2] + (Z_CELL[0],), CELL[2:] + (Z_CELL[1],), PEC, "cell"))
    P.append(Box((CELL[2], 20.0, 0.5), (CUT[2], 22.0, BOARD_T), PEC, "cell_tab"))        # tabs at the hand end [E]
    # ---------------- Ti electrode plates in the floor + contact dots to the board (TVS 12 pF = -j5.4 ohm at RF [LD 231])
    P.append(Box(E1[:2] + (Z_FLOOR,), E1[2:] + (Z_PLATE_TOP,), PEC, "E1_plate"))
    P.append(Box(E2[:2] + (Z_FLOOR,), E2[2:] + (Z_PLATE_TOP,), PEC, "E2_plate"))
    # ---------------- E3: Ti strip 26 x 3.5 on the top rim at the hand end, 1 mm wrap, tab + spring finger to the board
    P.append(Box((35.0, 1.5, Z_GLASS1), (ox1, 27.5, Z_GLASS1), PEC, "E3_strip"))
    P.append(Box((ox1, 1.5, Z_GLASS1 - 1.0), (ox1, 27.5, Z_GLASS1), PEC, "E3_wrap"))
    P.append(Box((36.0, 14.0, BOARD_T), (36.5, 15.0, Z_GLASS1), PEC, "E3_tab_spring"))
    # ---------------- PV lid conductors: four IBC strips (full back metal) merged into one sheet + finger-rest copper
    if v.with_lid and v.with_pv:
        P.append(Box(PV_SHEET[:2] + (Z_PV,), PV_SHEET[2:] + (Z_PV,), PEC, "pv_sheet"))
        P.append(Box(FINGER_CU[:2] + (Z_PV,), FINGER_CU[2:] + (Z_PV,), PEC, "finger_rest_cu"))
        P.append(Box((v.pv_tail_x, 8.0, BOARD_T), (v.pv_tail_x + 0.5, 8.5, Z_PV), PEC, "pv_minus_tail"))
        P.append(Box((v.pv_tail_x, 11.0, BOARD_T), (v.pv_tail_x + 0.5, 11.5, Z_PV), PEC, "pv_plus_tail"))
    if v.dock:
        P.append(Box((-3.5, -5.5, 12.0), (40.5, 34.5, 12.0), PEC, "dock_led_board"))
    return P, port, ant


def _rect_decompose(poly):
    """split a rectilinear polygon (possibly multi) into non-overlapping rectangles (x0, y0, x1, y1)"""
    polys = list(poly.geoms) if hasattr(poly, "geoms") else [poly]
    out = []
    for p in polys:
        xs = sorted({round(x, 6) for x, _ in p.exterior.coords})
        ys = sorted({round(y, 6) for _, y in p.exterior.coords})
        for i in range(len(xs) - 1):
            run = None
            for j in range(len(ys) - 1):
                cell = sbox(xs[i], ys[j], xs[i + 1], ys[j + 1])
                inside = p.contains(cell.representative_point())
                if inside:
                    if run is None:
                        run = [xs[i], ys[j], xs[i + 1], ys[j + 1]]
                    else:
                        run[3] = ys[j + 1]
                else:
                    if run is not None:
                        out.append(tuple(run)); run = None
            if run is not None:
                out.append(tuple(run))
    return out


def skin_distance(c: Cand, v: Var, pts):
    """minimum distance (mm) from points (x, y, z) of the radiator to the skin surface (rigid ellipse)"""
    yc = 14.5; zc = Z_FLOOR - v.skin_dz - v.wrist_b
    t = np.linspace(0, 2 * np.pi, 7200)
    ey = yc + v.wrist_a * np.cos(t); ez = zc + v.wrist_b * np.sin(t)
    return float(min(np.min(np.hypot(ey - y, ez - z)) for (_, y, z) in pts))
