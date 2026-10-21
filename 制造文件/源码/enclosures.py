"""3D-printable parts for the solar vest (build123d). Every dimension traces back to the KiCad boards
(out/*/fab/*.step), the BITalino Core LOD1, the photo-measured panel and the body-fitted placement.json.

Frames (mm):
  back pod : X = PMB-H board x, Y = -board y (board top-left corner at 0,0), Z up out of the lid; inner floor Z = 0
  chest pod: X = to the wearer's LEFT (viewer's right when facing the lid), Y up, Z out of the lid; inner floor Z = 0
  shoes / ref1 : panel frame S, origin = centre of the panel's rear plane, X_S = wearer's right, Y_S = up, Z_S = away from body
outputs: parts/<name>.step / .stl / .3mf and parts/parts_meta.json (volumes + transforms for the assembly)
"""
import json, os, sys, numpy as np
from build123d import *
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "parts"); os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, HERE)
PL = json.load(open(os.environ.get("SV_PLACEMENT", os.path.join(HERE, "..", "vest", "placement.json"))))
META = {}

def rbox(x0, x1, y0, y1, z0, z1, r=0.0):
    w, h = x1 - x0, y1 - y0
    sk = RectangleRounded(w, h, min(r, w / 2 - 0.01, h / 2 - 0.01)) if r > 0 else Rectangle(w, h)
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, z0) * extrude(sk, amount=z1 - z0)
def cyl(x, y, z0, z1, r): return Pos(x, y, z0) * Cylinder(r, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
def xcyl(x0, x1, y, z, r): return Pos(x0, y, z) * (Rot(0, 90, 0) * Cylinder(r, x1 - x0, align=(Align.CENTER, Align.CENTER, Align.MIN)))
def ycyl(y0, y1, x, z, r): return Pos(x, y0, z) * (Rot(-90, 0, 0) * Cylinder(r, y1 - y0, align=(Align.CENTER, Align.CENTER, Align.MIN)))
def engrave(part, text, x, y, z_top, size=4.0, depth=0.5, rot=0):
    t = Pos(x, y, z_top) * (Rot(0, 0, rot) * extrude(Text(text, font_size=size, align=(Align.CENTER, Align.CENTER)), amount=-depth))
    return part - t
def save(name, part, material, note, transform=None):
    import trimesh
    assert part.is_valid and len(part.solids()) == 1, f"{name}: invalid or {len(part.solids())} solids"
    export_step(part, os.path.join(OUT, name + ".step"))
    export_stl(part, os.path.join(OUT, name + ".stl"), tolerance=0.02, angular_tolerance=0.15)
    tm = trimesh.load(os.path.join(OUT, name + ".stl"))
    if not tm.is_watertight: print(f"  !! {name}: STL not watertight")
    trimesh.repair.fix_normals(tm); tm.export(os.path.join(OUT, name + ".3mf"))
    bb = part.bounding_box()
    META[name] = dict(watertight=bool(tm.is_watertight), material=material, note=note, volume_cm3=round(part.volume / 1000, 2),
                      mass_g_100pct=round(part.volume / 1000 * 1.27, 1), bbox_mm=[round(bb.size.X, 1), round(bb.size.Y, 1), round(bb.size.Z, 1)],
                      transform=transform)
    print(f"{name:22s} {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:6.1f} mm  {part.volume/1000:6.1f} cm³")

# =====================================================================================================
# BACK POD  (PMB-H 86 x 60 + 1S LiPo up to 50 x 64 x 10.5 mm)
# =====================================================================================================
W, FL, LIDT = 2.0, 2.0, 2.0
IX0, IX1, IY0, IY1, ZC = -10.0, 87.0, -126.6, 1.0, 24.5
OX0, OX1, OY0, OY1 = IX0 - W, IX1 + W, IY0 - W, IY1 + W
RO = 6.0
Z_BRD = 4.0                                   # PMB-H underside (THT pins stick out 2.9 mm -> 1.1 mm air)
HOLES = [(2.6, -2.6), (2.6, -57.4), (83.4, -57.4), (83.4, -30.0)]
COLS = [(-7.0, -25.0), (-7.0, -122.1), (84.0, -122.1), (84.0, -76.0)]      # sunk 0.5 mm into the walls (no tangent contact)
HOOK_X = (19.0, 58.0); HOOK_TOP_Y = OY1 - 15.0
BAT_X = (22.7, 63.3)                          # 104050 pocket: 40.6 mm wide, centred where the old 50 x 64 bay was
# cable openings: (wall, along-wall position, centre Z, radius)
# cable openings sized from the photo of the panel cable (2-core, Ø4.1 mm measured; its leftover also becomes W04/W05):
# (wall, along-wall position, centre Z, radius, label); the lid tongues grip 0.3 mm below the cable radius
OPEN = [("L", -7.5, 9.5, 2.4, "PANEL"), ("L", -40.2, 8.1, 2.25, "REF1"), ("L", -49.6, 8.1, 2.25, "REF2"), ("R", -65.0, 8.0, 2.6, "CHEST")]
USB = dict(y=-13.0, z=Z_BRD + 15.4, w=13.0, h=8.0)

def back_pod_tub():
    tub = rbox(OX0, OX1, OY0, OY1, -FL, ZC, RO) - rbox(IX0, IX1, IY0, IY1, 0, ZC + 1, RO - W)
    tub = fillet(tub.edges().group_by(Axis.Z)[0], 1.5)
    for x, y in HOLES: tub += cyl(x, y, 0, Z_BRD, 2.6)
    for x, y in COLS: tub += cyl(x, y, 0, ZC, 3.5)
    # TEUCER HP600 thermal pad seat under the charger (CN3791 / M1 / D5 / L1): 20 x 20 plateau, 2 mm below the PCB
    # (v3 §5.4: the pad only conducts charger heat into the enclosure, never toward the body)
    tub += rbox(35.0, 55.0, -22.0, -2.0, 0, Z_BRD - 2.0)
    # battery bay for the 104050 cell bought on JD (10 x 40 x 50 + protection board, leads toward the divider):
    # pocket 40.6 wide with 0.3 mm crush bumps (grips 40.0), 1 mm end rib, divider at the lead end
    bx0, bx1 = BAT_X
    tub += rbox(bx0 - 1.4, bx0, -126.6, -73.0, 0, 7) + rbox(bx1, bx1 + 1.4, -126.6, -73.0, 0, 7) + rbox(20.0, 77.6, -71.6, -70.0, 0, 7)
    for y in (-118.0, -100.0, -82.0):
        tub += Pos(bx0, y, 0) * Cylinder(0.6, 6.0, align=(Align.CENTER, Align.CENTER, Align.MIN)) - rbox(bx0 - 1.0, bx0 - 0.3, y - 1, y + 1, -0.1, 6.1)
        tub += Pos(bx1, y, 0) * Cylinder(0.6, 6.0, align=(Align.CENTER, Align.CENTER, Align.MIN)) - rbox(bx1 + 0.3, bx1 + 1.0, y - 1, y + 1, -0.1, 6.1)
    tub += rbox(bx0 + 4.0, bx1 - 4.0, -126.6, -125.6, 0, 5)
    # zip-tie bars beside the panel and chest cable openings (tunnel runs across the cable)
    for (x0, x1, y0, y1) in ((-9.5, -3.5, -11.5, -3.5), (78.0, 84.0, -68.5, -61.5)):
        bar = rbox(x0, x1, y0, y1, 0, 5) - rbox(x0 + 1.1, x1 - 1.1, y0 - 1, y1 + 1, 1.2, 3.0)
        tub += bar
    for x, y in HOLES: tub -= cyl(x, y, -1.0, Z_BRD + 0.1, 0.85)                       # M2 self-tapping pilots
    for x, y in COLS: tub -= cyl(x, y, 4.0, ZC + 0.1, 0.85)
    for hx in HOOK_X:                                                                 # hook screws from inside
        for dy in (-12.0, -26.0): tub -= cyl(hx, HOOK_TOP_Y + dy, -FL - 0.1, 0.1, 1.2)
    for wall, s, zc, r, _ in OPEN:                                                     # U-notches from the top
        x0, x1 = (OX0 - 0.1, IX0 + 0.1) if wall == "L" else (IX1 - 0.1, OX1 + 0.1)
        tub -= xcyl(x0, x1, s, zc, r) + rbox(x0, x1, s - r, s + r, zc, ZC + 1)
    u = USB; tub -= Pos(IX1 - 0.1, u["y"], u["z"]) * (Rot(0, 90, 0) * extrude(RectangleRounded(u["h"], u["w"], 2.5), amount=W + 0.2))
    # outside: debossed arrow + label on the back face (faces the vest)
    tub -= Pos(38.5, -62.8, -FL) * (Rot(180, 0, 0) * extrude(Text("UP ^  PMB-H BACK POD", font_size=6, align=(Align.CENTER, Align.CENTER)), amount=-0.5))
    return tub

def back_pod_lid():
    lid = rbox(OX0, OX1, OY0, OY1, ZC, ZC + LIDT, RO)
    lid = fillet(lid.edges().group_by(Axis.Z)[-1], 1.5)
    g = 0.25
    lip = rbox(IX0 + g, IX1 - g, IY0 + g, IY1 - g, ZC - 2.5, ZC, RO - W - g) - rbox(IX0 + g + 1.2, IX1 - g - 1.2, IY0 + g + 1.2, IY1 - g - 1.2, ZC - 3, ZC + 1, max(RO - W - g - 1.2, 0.5))
    for x, y in COLS: lip -= cyl(x, y, ZC - 3, ZC + 1, 3.5 + 0.4)
    lid += lip
    for wall, s, zc, r, _ in OPEN:                                                     # tongues close each notch above the cable
        x0, x1 = (OX0 + 0.15, IX0 + 1.2) if wall == "L" else (IX1 - 1.2, OX1 - 0.15)
        t = rbox(x0, x1, s - r + 0.15, s + r - 0.15, zc, ZC) - xcyl(x0 - 1, x1 + 1, s, zc, r - 0.3)   # 0.3 mm grip on the cable
        lid += t
    for y in (-88.0, -110.0): lid += rbox(BAT_X[0] + 2.0, BAT_X[1] - 2.0, y - 0.8, y + 0.8, 11.0, ZC)   # clamp the 10 mm cell through 2 mm foam (→ ~1 mm)
    for x, y in COLS: lid -= cyl(x, y, ZC - 3, ZC + LIDT + 0.1, 1.2) + cyl(x, y, ZC + LIDT - 1.2, ZC + LIDT + 0.1, 2.3)
    top = ZC + LIDT
    lid = engrave(lid, "PMB-H  SOLAR BACK UNIT", 38.5, -95.0, top, 5.5)
    lid = engrave(lid, "SOLAR VEST  v3.1", 38.5, -104.0, top, 3.5)
    for wall, s, zc, r, lab in OPEN:
        lid = engrave(lid, lab, (IX0 + 9.0) if wall == "L" else (IX1 - 9.0), s, top, 3.2)
    lid = engrave(lid, "USB-C", IX1 - 9.0, USB["y"], top, 3.2)
    lid = engrave(lid, "^ UP", 38.5, -8.0, top, 4.0)
    return lid

def webbing_hook():
    """U-hook for 25 mm webbing: the plate slides behind the webbing, the bridge rests on its top edge.
    local frame: Y up (worn), Z = 0 at the face it is screwed to, -Z toward the body."""
    w, L = 24.0, 34.0
    pad = rbox(-w / 2, w / 2, -L, 0, -3.5, 0); slot_top = -3.5; plate = rbox(-w / 2, w / 2, -L, 0, -7.7, -5.7)
    bridge = rbox(-w / 2, w / 2, -4.0, 0, -7.7, 0)
    bump = rbox(-w / 2, w / 2, -L, -L + 4.0, -5.7, -5.0)
    h = pad + plate + bridge + bump
    h = fillet(h.edges().filter_by(Axis.X).group_by(Axis.Y)[0], 0.8)
    for dy in (-12.0, -26.0): h -= cyl(0, dy, -3.0, 0.1, 0.85)
    return h

# =====================================================================================================
# CHEST POD  (BITalino Core B 56 x 65 above, LIB 56 x 37 below, both rotated 180° from their drawings)
# =====================================================================================================
CZC, ZCORE, ZLIB = 15.6, 2.5, 3.0
CORE = (0.0, 56.0, 0.0, 65.0); LIBR = (0.0, 56.0, -40.0, -3.0)
CI = [(-0.75, 56.75, -3.0, 65.75), (-9.0, 56.75, -40.75, -3.0)]                       # interior rectangles
CO = [(-2.75, 58.75, -42.75, 67.75), (-11.0, 58.75, -42.75, -1.0)]                    # outer rectangles
LUGS = [(-5.25, 70.25), (61.25, 70.25), (-13.5, -45.25), (61.25, -45.25)]
LUG_CORNERS = [(-2.75, 67.75), (58.75, 67.75), (-11.0, -42.75), (58.75, -42.75)]
SOCK_Y = [5.2, 18.6, 32.1, 45.6, 59.1]
LAB_R = ["I1", "A4", "A3", "A2", "A1"]; LAB_L = ["O1", "O2", "PWM", "A6", "A5"]

def chest_outline(z0, z1, grow=0.0, r=3.0):
    a, b = CO
    s = rbox(a[0] - grow, a[1] + grow, a[2] - grow, a[3] + grow, z0, z1, r) + rbox(b[0] - grow, b[1] + grow, b[2] - grow, b[3] + grow, z0, z1, r)
    for (x, y), (cx, cy) in zip(LUGS, LUG_CORNERS):
        sx, sy = np.sign(x - cx), np.sign(y - cy)
        s += cyl(x, y, z0, z1, 4.0 + grow)
        s += rbox(*sorted([x, cx - sx * 1.0]), *sorted([y, cy - sy * 1.0]), z0, z1)   # web back into the wall
    return s
def chest_pod_tub():
    tub = chest_outline(-2.0, CZC)
    tub -= rbox(*CI[0], 0, CZC + 1, 1.0) + rbox(*CI[1], 0, CZC + 1, 1.0)
    for (x, y) in ((53.4, -5.6), (2.6, -5.6)): tub += cyl(x, y, 0, ZLIB, 2.5)        # LIB mounting holes (rotated)
    tub += rbox(3.0, 53.0, -40.75, -38.5, 0, ZLIB)                                    # ledge under the LIB's far edge
    for (x0, y0) in ((0.5, 0.5), (51.5, 0.5), (0.5, 60.5), (51.5, 60.5)): tub += rbox(x0, x0 + 4, y0, y0 + 4, 0, ZCORE)   # Core corner pads
    for (x0, x1) in ((30.0, 36.0), (44.0, 50.0)): tub += rbox(x0, x1, -1.25, -0.3, 0, ZCORE + 1.6 + 1.0)   # end stops: Core cannot slide toward the LIB
    for (x, y) in ((53.4, -5.6), (2.6, -5.6)): tub -= cyl(x, y, -1.0, ZLIB + 0.1, 0.85)
    for x, y in LUGS: tub -= cyl(x, y, 3.0, CZC + 0.1, 0.85)
    zw0, zw1 = ZCORE + 1.6 - 0.3, ZCORE + 1.6 + 6.2                                   # UC-E6 windows, both sides, full length
    tub -= rbox(-3.0, -0.5, 0.5, 64.5, zw0, zw1, 1.0) + rbox(56.5, 59.0, 0.5, 64.5, zw0, zw1, 1.0)
    # (no micro-USB opening: B is powered by the back unit; plugging USB in while electrodes are on couples the body to mains)
    tub -= rbox(9.5, 17.5, 65.5, 68.0, ZCORE + 1.1, ZCORE + 1.6 + 3.5, 0.8)          # power switch slot
    tub -= xcyl(-11.2, -8.8, -28.0, 7.0, 2.5) + rbox(-11.2, -8.8, -30.5, -25.5, 7.0, CZC + 1)   # J6 cable from the back unit
    tub -= Pos(28.0, 12.5, -2.0) * (Rot(180, 0, 0) * extrude(Text("LIB + BITalino B", font_size=5, align=(Align.CENTER, Align.CENTER)), amount=-0.5))
    return tub
def chest_pod_lid():
    lid = chest_outline(CZC, CZC + LIDT)
    g = 0.25
    inner = rbox(CI[0][0] + g, CI[0][1] - g, CI[0][2] + g, CI[0][3] - g, CZC - 2.0, CZC, 0.8) + rbox(CI[1][0] + g, CI[1][1] - g, CI[1][2] + g, CI[1][3] - g, CZC - 2.0, CZC, 0.8)
    hole = rbox(CI[0][0] + g + 1.2, CI[0][1] - g - 1.2, CI[0][2] + g + 1.2, CI[0][3] - g - 1.2, CZC - 3, CZC + 1, 0.5) + \
           rbox(CI[1][0] + g + 1.2, CI[1][1] - g - 1.2, CI[1][2] + g + 1.2, CI[1][3] - g - 1.2, CZC - 3, CZC + 1, 0.5)
    lid += inner - hole
    lid -= rbox(-0.5, 56.5, 0.5, 64.5, CZC - 2.1, CZC - 0.01)                         # lip open over the socket windows
    for x0 in (1.0, 51.0): lid += rbox(x0, x0 + 4.0, 4.0, 61.0, ZCORE + 1.6 + 3.5 + 0.5, CZC)   # press on the socket rows
    lid += rbox(-11.2 + 0.15, -9.0 + 1.0, -30.5 + 0.15, -25.5 - 0.15, 9.5, CZC) - xcyl(-12, -7, -28.0, 7.0, 2.2)
    for x, y in LUGS: lid -= cyl(x, y, CZC - 0.1, CZC + LIDT + 0.1, 1.2) + cyl(x, y, CZC + LIDT - 1.2, CZC + LIDT + 0.1, 2.3)
    top = CZC + LIDT
    lid = engrave(lid, "BITalino B", 28.0, 40.0, top, 6.0)
    lid = engrave(lid, "+ LIB  solar", 28.0, 31.0, top, 4.0)
    lid = engrave(lid, "ON/OFF", 13.5, 61.0, top, 3.0); lid = engrave(lid, "NO USB", 26.0, 61.0, top, 3.0)
    for y, a, b in zip(SOCK_Y, LAB_R, LAB_L):
        lid = engrave(lid, a, 52.0, y, top, 3.0); lid = engrave(lid, b, 4.5, y, top, 2.6)
    lid = engrave(lid, "<- BACK UNIT", 12.0, -28.0, top, 3.0)
    return lid

# =====================================================================================================
# PANEL SHOES (6) in the panel frame S
# =====================================================================================================
try:                                              # the panel shoes need the private body model; the rest does not
    from torso import Torso
    from vest_geom import off_layer, DEG
    T = Torso()
except Exception as e:
    T = None; print("  (torso model not available - panel shoes are not regenerated)", e)
L_P, W_P, D_P = 261.8, 171.0, 15.0
C_BACK = np.array(PL["panel"]["back_plane_centre"]); n_out = np.array(PL["panel"]["n_out"]); upv = np.array(PL["panel"]["up"])
ex = np.array([1.0, 0, 0]); MS = np.c_[-ex, upv, n_out]                              # columns: S axes in body coords
def to_S(p): return (MS.T @ (np.asarray(p) - C_BACK)) * 1000.0
def vec_S(v): return MS.T @ np.asarray(v)
CARRIER = 0.0025
def carrier_frame(x_body, y):
    ph = np.linspace(-170, -10, 3201)
    P = T.point(np.full_like(ph, y), ph * DEG, off_layer(y, "outer") + CARRIER)
    phi = ph[np.argmin(np.abs(P[:, 0] - x_body))]
    off = float(off_layer(y, "outer") + CARRIER); h = 1e-4
    p = T.point(y, phi * DEG, off); py = T.point(y + h, phi * DEG, off) - p; pt = T.point(y, phi * DEG + h, off) - p
    n = np.cross(pt, py); n /= np.linalg.norm(n)
    if n @ (-n_out) > 0: n = -n                                                       # outward = toward the panel
    yv = py - (py @ n) * n; yv /= np.linalg.norm(yv); xv = np.cross(yv, n)
    return p, xv, yv, n
CL, WALL_T, LIP_W, LIP_T = 0.6, 3.0, 4.0, 2.2

def cradle(kind, sx, sy):
    """frame-gripping part at a corner (sx, sy = ±1 in S) or edge centre (sx = 0)."""
    cy = sy * W_P / 2; z_top = D_P + 0.3 + LIP_T
    if sx != 0:
        cx = sx * L_P / 2; span = 28.0
        xs = sorted([cx - sx * span, cx + sx * (CL + WALL_T)]); ys = sorted([cy - sy * span, cy + sy * (CL + WALL_T)])
        pad = rbox(*xs, *ys, -3.0, 0.0)
        wall_x = rbox(*sorted([cx + sx * CL, cx + sx * (CL + WALL_T)]), *ys, -3.0, z_top)
        wall_y = rbox(*xs, *sorted([cy + sy * CL, cy + sy * (CL + WALL_T)]), -3.0, z_top)
        lip = rbox(*sorted([cx - sx * LIP_W, cx + sx * (CL + WALL_T)]), *ys, D_P + 0.3, z_top) + rbox(*xs, *sorted([cy - sy * LIP_W, cy + sy * (CL + WALL_T)]), D_P + 0.3, z_top)
        c = pad + wall_x + wall_y + lip
        c = fillet(c.edges().filter_by(Axis.Z).group_by(Axis.X)[0 if sx > 0 else -1], 1.0) if False else c
        centre = ((xs[0] + xs[1]) / 2 - sx * 4, (ys[0] + ys[1]) / 2 - sy * 4)
    else:
        xs = (-18.0, 18.0); ys = sorted([cy - sy * 12.0, cy + sy * (CL + WALL_T)])
        pad = rbox(*xs, *ys, -3.0, 0.0)
        wall_y = rbox(*xs, *sorted([cy + sy * CL, cy + sy * (CL + WALL_T)]), -3.0, z_top)
        lip = rbox(*xs, *sorted([cy - sy * LIP_W, cy + sy * (CL + WALL_T)]), D_P + 0.3, z_top)
        c = pad + wall_y + lip; centre = (0.0, (ys[0] + ys[1]) / 2)
    return c, centre

def foot_hook(p, xv, yv, n):
    """U-hook foot on the carrier surface; origin = webbing centre on the carrier, built in that local frame."""
    o = to_S(p); X, Y, Z = vec_S(xv), vec_S(yv), vec_S(n)
    pl = Plane(origin=tuple(o), x_dir=tuple(X), z_dir=tuple(Z))
    w = 24.0; top, bot = 17.0, -21.0
    plate = rbox(-w / 2, w / 2, bot, top, 0.0, 2.0); bridge = rbox(-w / 2, w / 2, top - 4.0, top, 0.0, 7.7)
    pad = rbox(-w / 2, w / 2, bot, top, 4.2, 7.7); bump = rbox(-w / 2, w / 2, bot, bot + 4.0, 2.0, 2.7)
    f = plate + bridge + pad + bump
    return pl * f, pl * (Pos(0, -2.0, 7.7) * Rectangle(20.0, 26.0))

def shoe(spec):
    """returns (solid, gap_mm, wearer-side name). placement 'u' is body x (+ = wearer's left); S +X = wearer's right."""
    u = spec["u"]; sy = 1 if spec["v"] > 0 else -1
    sx = 0 if abs(u) < 1e-6 else (1 if u < 0 else -1)
    name = ("T" if sy > 0 else "B") + ("M" if sx == 0 else ("L" if u > 0 else "R"))
    c, centre = cradle(spec["kind"], sx, sy)
    p, xv, yv, n = carrier_frame(u, PL["webbing_rows_y"][spec["webbing_row"]])
    foot, top_face = foot_hook(p, xv, yv, n)
    pad_face = Plane(origin=(centre[0], centre[1], -3.0), x_dir=(1, 0, 0), z_dir=(0, 0, 1)) * Rectangle(20.0, 20.0)
    col = loft([top_face, pad_face])
    return c + foot + col, float(-(to_S(p)[2])), name

# =====================================================================================================
# REFERENCE-CELL HOLDERS
# =====================================================================================================
CELL = (40.6, 28.6, 3.0)                       # pocket for the AK 40 x 28 mm epoxy cell (3.5 V / 30 mA) bought on JD; foam tape under it
def ref1_holder():
    """clips over the panel's short edge on the wearer's LEFT (S -X side), cell flush with the glass plane."""
    x_edge = -L_P / 2; g = 0.4; hw = 20.0
    back_jaw = rbox(x_edge - g - 3.0, x_edge + 6.0, -hw, hw, -2.5, 0.0)
    wall = rbox(x_edge - g - 3.0, x_edge - g, -hw, hw, -2.5, D_P + 0.3 + 2.2)
    front_jaw = rbox(x_edge, x_edge + 4.0, -hw, hw, D_P + 0.3, D_P + 0.3 + 2.2) + rbox(x_edge - g - 3.0, x_edge, -hw, hw, D_P + 0.3, D_P + 0.3 + 2.2)
    glass_z = D_P - 1.2                          # glass front surface
    plat = rbox(x_edge - g - 3.0 - CELL[0] - 6.0, x_edge - g - 3.0, -hw, hw, glass_z - CELL[2] - 2.5, glass_z)
    plat -= rbox(x_edge - g - 3.0 - CELL[0] - 3.0, x_edge - g - 3.0 - 3.0, -CELL[1] / 2, CELL[1] / 2, glass_z - CELL[2], glass_z + 1)
    plat -= rbox(x_edge - g - 3.0 - 8.0, x_edge - g - 3.0 + 0.1, -2.3, 2.3, glass_z - CELL[2] - 2.6, glass_z - CELL[2] + 0.1)   # lead slot (Ø4.1 cable)
    h = back_jaw + wall + front_jaw + plat
    return h
def ref2_holder():
    """horizontal cell on the left shoulder (hook-and-loop patch on the back yoke). Built in the shoulder's tangent
    frame (x = right, y = surface up, z = outward normal); the top is cut by a horizontal (body +y) plane."""
    r2 = PL["ref2"]; R = np.c_[r2["right"], r2["up"], r2["normal"]]
    g = R.T @ np.array([0.0, 1.0, 0.0])                                             # body 'up' in local coords
    corners = [(x, y) for x in (-25, 25) for y in (-20, 20)]
    h0 = 3.0 + max((g[0] * x + g[1] * y) / g[2] for x, y in corners) + 3.5
    blk = rbox(-25, 25, -20, 20, 0, h0 + 40)
    top = Plane(origin=(0, 0, h0), z_dir=tuple(g))
    w = split(blk, bisect_by=top, keep=Keep.BOTTOM)
    w -= top * Box(CELL[0], CELL[1], 2 * CELL[2], align=(Align.CENTER, Align.CENTER, Align.CENTER))
    w -= top * (Pos(0, -CELL[1] / 2 - 3, 0) * Box(4.6, 8, 2 * CELL[2] + 2, align=(Align.CENTER, Align.CENTER, Align.CENTER)))   # lead slot (Ø4.1 cable)
    w -= rbox(-23, 23, -18, 18, -0.1, 0.8)                                            # recess for adhesive hook tape
    tilt = float(np.degrees(np.arccos(np.clip(g[2], -1, 1))))
    return w, tilt


# =====================================================================================================
# C: BITalino (r)evolution Board BLE (108 x 65, user manual Fig. 9) + 523450 1000 mAh under it
#    frame: X along the board (UC-E6 column at X = 0), Y across (USB / switch edge at Y = 0), Z up; inner floor Z = 0
# =====================================================================================================
CB = dict(L=108.0, W=65.0, Z=7.0, T=1.6, H_COMP=4.4)
C_SOCK_Y = {"EEG": 55.2, "EDA": 41.1, "ECG": 27.4, "EMG": 13.0}      # traced from datasheet Fig. 5 (4.6 px/mm), ±1 mm
C_USB_X, C_SW_X, C_BTN, C_LED, C_LUX = 59.7, (65.5, 74.0), (98.0, 41.1), (41.0, 62.5), (68.5, 62.5)
C_BAT = (20.0, 72.0, 15.0, 51.0)               # 523450: 50 x 34 x 5.2 (+ protection board) lying under the board
CI_ = (-0.75, 108.75, -0.75, 68.0); CZ = 14.0
C_LUGS = [(-5.25, 72.5), (113.25, 72.5), (-5.25, -5.25), (113.25, -5.25)]
C_LUG_CORNERS = [(-2.75, 70.0), (110.75, 70.0), (-2.75, -2.75), (110.75, -2.75)]
def c_outline(z0, z1):
    s = rbox(CI_[0] - 2, CI_[1] + 2, CI_[2] - 2, CI_[3] + 2, z0, z1, 3.0)
    for (x, y), (cx, cy) in zip(C_LUGS, C_LUG_CORNERS):
        sx, sy = np.sign(x - cx), np.sign(y - cy)
        s += cyl(x, y, z0, z1, 4.0) + rbox(*sorted([x, cx - sx * 1.0]), *sorted([y, cy - sy * 1.0]), z0, z1)
    return s
def c_case_base():
    t = c_outline(-2.0, CZ) - rbox(*CI_, 0, CZ + 1, 1.0)
    for (x0, y0) in ((0.5, 0.5), (102.5, 0.5), (0.5, 59.5), (102.5, 59.5), (51.5, 0.5), (51.5, 59.5)):
        t += rbox(x0, x0 + 5, y0, y0 + 5, 0, CB["Z"])                                 # board support pads
    t += rbox(18.5, 19.7, 15.0, 51.0, 0, 3.5) + rbox(72.3, 73.5, 15.0, 51.0, 0, 3.5)   # battery side ribs
    t += rbox(30.0, 62.0, 14.6, 15.6, 0, 3.5) + rbox(30.0, 62.0, 50.4, 51.4, 0, 3.5)     # battery end stops (523450 is 34 wide)
    for (x0, x1) in ((2.0, 10.0), (88.0, 104.0)): t += rbox(x0, x1, 65.3, 68.0, 0, CB["Z"] + CB["T"] + 1.0)   # board far-edge stops (W12 runs at x 16-63)
    for x, y in C_LUGS: t -= cyl(x, y, 3.0, CZ + 0.1, 0.85)
    zt = CB["Z"] + CB["T"]
    t -= rbox(-3.0, -0.5, 6.0, 62.0, zt - 0.3, zt + 5.8, 1.0)                         # UC-E6 window (EEG/EDA/ECG/EMG)
    t -= Pos(C_USB_X, -0.5, zt + 1.3) * (Rot(90, 0, 0) * extrude(RectangleRounded(11.0, 7.0, 2.0), amount=2.6))   # micro-USB (charging, not while worn)
    t -= rbox(C_SW_X[0], C_SW_X[1], -3.0, -0.5, zt - 0.5, zt + 3.4, 0.8)               # ON/OFF switch
    t -= Pos(54.0, 33.0, -2.0) * (Rot(180, 0, 0) * extrude(Text("C  BITalino Board BLE", font_size=5, align=(Align.CENTER, Align.CENTER)), amount=-0.5))
    return t
def c_case_lid():
    lid = c_outline(CZ, CZ + 2.0)
    g = 0.25
    lip = rbox(CI_[0] + g, CI_[1] - g, CI_[2] + g, CI_[3] - g, CZ - 2.0, CZ, 0.8) - rbox(CI_[0] + g + 1.2, CI_[1] - g - 1.2, CI_[2] + g + 1.2, CI_[3] - g - 1.2, CZ - 3, CZ + 1, 0.5)
    lip -= rbox(-1.0, 1.0, 6.0, 62.0, CZ - 2.2, CZ)                                    # keep the UC-E6 window clear
    lid += lip
    for x, y in C_LUGS: lid -= cyl(x, y, CZ - 0.1, CZ + 2.1, 1.2) + cyl(x, y, CZ + 0.8, CZ + 2.1, 2.3)
    lid -= cyl(*C_LED, CZ - 0.1, CZ + 2.1, 1.6) + cyl(*C_LUX, CZ - 0.1, CZ + 2.1, 2.5)   # LED + light-sensor windows
    bx, by = C_BTN                                                                      # flexure button over the BTN block
    lid -= rbox(bx - 6.0, bx + 6.0, by - 8.0, by + 7.0, CZ - 0.1, CZ + 2.1) - rbox(bx - 5.0, bx + 5.0, by - 9.0, by + 6.0, CZ - 0.2, CZ + 2.2)
    lid += cyl(bx, by - 1.0, CB["Z"] + CB["T"] + CB["H_COMP"] + 0.3, CZ, 2.0)            # plunger
    for x in (33.0, 78.0):                                                              # clamp posts on the two bare rails (2 mm foam under each)
        for y in (5.0, 60.0): lid += cyl(x, y, CB["Z"] + CB["T"] + 1.2, CZ, 2.5)
    top = CZ + 2.0
    lid = engrave(lid, "C  control (battery)", 54.0, 40.0, top, 5.0)
    lid = engrave(lid, "ECG <-", 9.0, C_SOCK_Y["ECG"], top, 3.0); lid = engrave(lid, "BTN", bx, by + 10.5, top, 3.0)
    lid = engrave(lid, "LED", C_LED[0], C_LED[1] - 5.0, top, 2.6); lid = engrave(lid, "LUX", C_LUX[0], C_LUX[1] - 5.0, top, 2.6)
    return lid

# =====================================================================================================
# PulseSensor ear clip (holds the official Ø18.1 x 5 cup housing; flexure opens to ~6 mm)
# =====================================================================================================
def ear_clip():
    w = 22.0
    jaw_a = rbox(0, 26, -w / 2, w / 2, 0, 6.5); jaw_b = rbox(0, 26, -w / 2, w / 2, 9.0, 11.0)
    ring = Pos(0, -w / 2, 5.5) * (Rot(-90, 0, 0) * (Cylinder(5.5, w, align=(Align.CENTER, Align.CENTER, Align.MIN)) - Cylinder(4.3, w, align=(Align.CENTER, Align.CENTER, Align.MIN))))
    ring = ring - rbox(0, 12, -w, w, -1, 12)                                            # keep the half on the -X side
    clip = jaw_a + jaw_b + ring
    clip -= cyl(14.0, 0, 1.3, 6.6, 9.2)                                                 # cup pocket
    clip -= rbox(14.0, 26.5, -1.5, 1.5, 3.0, 6.6)                                       # cable slot
    clip -= rbox(5.0, 23.0, -8.0, 8.0, 8.9, 9.5)                                        # recess for a 0.5 mm foam pad
    return clip

# =====================================================================================================
# Panel test stand (bench): base + cradle per side, M4 pivot + M4 lock bolt, tilt 0..90° in 15° steps
# =====================================================================================================
PIVOT_Z, LOCK_R = 100.0, 35.0              # pivot high enough for a vertical panel: 85.5 + 3 frame + 10 clearance
def stand_base():
    foot = rbox(-70, 70, -25, 25, 0, 6, 4.0)
    up = rbox(-30, 30, -3, 3, 0, PIVOT_Z + 12, 3.0)
    gus = Pos(0, 0, 6) * extrude(Polygon((-30, 0), (30, 0), (0, 40)), amount=6).rotate(Axis.X, 90).moved(Location((0, 3, 0)))
    b = foot + up + Pos(0, 3, 6) * (Rot(90, 0, 0) * extrude(Polygon((-30, 0), (30, 0), (0, 30)), amount=6))
    b = b + Pos(0, 9, 6) * (Rot(90, 0, 0) * extrude(Polygon((-12, 0), (12, 0), (0, 22)), amount=3))
    b -= Pos(0, -4, PIVOT_Z) * (Rot(-90, 0, 0) * Cylinder(2.2, 20, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    for k in range(7):
        a = np.radians(15 * k); x, z = -LOCK_R * np.cos(a), PIVOT_Z - LOCK_R * np.sin(a)
        b -= Pos(x, -4, z) * (Rot(-90, 0, 0) * Cylinder(2.2, 20, align=(Align.CENTER, Align.CENTER, Align.MIN)))
        b = engrave(b, f"{15 * k}", x - 6.5 * np.cos(a), z - 6.5 * np.sin(a), 0, 3.0) if False else b
    for k in range(7):
        a = np.radians(15 * k); x, z = -(LOCK_R + 9) * np.cos(a), PIVOT_Z - (LOCK_R + 9) * np.sin(a)
        b -= Pos(x, 3.0, z) * (Rot(90, 0, 0) * extrude(Text(f"{15 * k}", font_size=4, align=(Align.CENTER, Align.CENTER)), amount=0.5))
    return b
def stand_cradle():
    """U-channel gripping the panel's short side (frame depth 15 mm). On the stand the REF1 clip goes on the top long edge."""
    inner = 15.6; wall = 3.0; L = 120.0; dep = 20.0
    u = rbox(-L / 2, L / 2, 0, dep, -wall, inner + wall) - rbox(-L / 2 - 1, L / 2 + 1, 3.0, dep + 1, 0, inner)
    arm = rbox(-12, 12, -6, 0, -wall, inner + wall) + rbox(-12, 12, -6, 0, -LOCK_R - 8, inner + wall)
    c = u + arm
    c -= Pos(0, -7, inner / 2) * (Rot(-90, 0, 0) * Cylinder(2.2, 10, align=(Align.CENTER, Align.CENTER, Align.MIN)))      # pivot (centre of mass line)
    c -= Pos(0, -7, inner / 2 - LOCK_R) * (Rot(-90, 0, 0) * Cylinder(2.2, 10, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return c

if __name__ == "__main__":
    META.update(json.load(open(os.environ["SV_META_IN"])))
    tub = back_pod_tub(); save("back_pod_base", tub, "PETG 白/浅灰（反光降温）", "PMB-H（M2×6 ×4）+ 104050 电池（40.6 宽电池槽 + 压紧凸点，底面贴双面泡棉胶）")
    save("back_pod_lid", back_pod_lid(), "PETG 白/浅灰", "M2×8 自攻 ×4；两根压条下各贴一条 2 mm 泡棉，把电池压住")
    save("chest_pod_base", chest_pod_tub(), "PETG", "LIB（下，M2×6 ×2）+ BITalino Core B（上，四角垫块 + 两个端部挡块）")
    save("chest_pod_lid", chest_pod_lid(), "PETG", "M2×8 自攻 ×4；两根压条下贴 2 mm 泡棉，压住 Core B 的插座排")
    save("ref1_holder", ref1_holder(), "ASA/PETG", "夹在面板左侧短边中部；槽 40.6 × 28.6，放 AK 40×28 参考片，片下垫泡棉胶使其与玻璃面齐平")
    r2, tilt = ref2_holder(); save("ref2_holder", r2, "ASA/PETG", f"左肩，楔角 {tilt:.1f}° 使参考片水平；槽 40.6 × 28.6；底面贴魔术贴（钩面）")
    save("c_case_base", c_case_base(), "PETG", "C：BITalino Board（官方 108 × 65）+ 523450；板边挡块 + 电池端部挡块；左侧窗口插心电线")
    save("c_case_lid", c_case_lid(), "PETG", "M2×8 ×4；4 个压柱（各贴 2 mm 泡棉）压住板子两条侧轨；柔性按键压 BTN")
    json.dump(META, open(os.path.join(OUT, "parts_meta.json"), "w"), ensure_ascii=False, indent=1)
