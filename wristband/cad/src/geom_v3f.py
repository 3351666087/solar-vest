"""SolarBand V3-F product model: single-source geometry (plan, Z stack, parts, zones, straps, wrist).

Used by model_v3f.py (build123d CAD + manifold3d checks + renders), motor_search.py, worn_v3f.py and exports_v3f.py.
Spec: v3/decide/BASELINE.md (cited as [B 8] = section 8). Numbers that BASELINE does not fix are design choices of
this lane, tagged [E]; datasheet facts read today are tagged [DS key] (keys in ../ref/sources.md); project files [P].

FRAMES
  Case frame (BASELINE 7): X 0..POD_L along the forearm (X = 0 = elbow end on a LEFT wrist), Y 0..32 across the wrist
  (Y = 0 = root B = antenna long wall, radial; Y = 32 = root A, ulnar), Z = 0 at the floor's skin face, Z up to the sky.
  Seen from the sky: X right, Y up.  The PPG mesa (optical cap) protrudes to Z = -0.80.
  Board frame (V2-B lgeom convention, F.Cu = sky side = JLC top): X_b = X - 1.5, Y_b = Y - 1.5.
  Wrist frame (worn): u across the wrist, u > 0 toward the ULNAR side, v up (dorsal); the floor plane is tangent to the
  dorsal vertex of the elliptical wrist (mesa pressed in, BASELINE header).  For BOTH wrists u = Y - 16 (the band is
  turned 180 degrees on the right wrist, so root B stays radial and root A ulnar); along the forearm x = X (left) or
  x = POD_L - X (right), x increasing toward the hand.

Z LEVELS are the maximum-material values of BASELINE 8 (the stack is a max-material sum); the CAD therefore shows the
designed clearances (0.15 mm layers) as air, and every 'designed contact' in the checks is a max-material contact.

STAGE 1 (2026-11-14, v3/stage1/STAGE1.md): review fixes C-1 (window rail), C-2 (K corner re-laid, pitch 5.40), C-4/C-5 (zones from
parts.json courtyards), C-6 (D10, J6 + lid tail), C-8 (J15/J18 out of the panel zone), C-10 (window column +0.055), C-12 (head housing),
C-15 (5 mm rule tolerance), C-18 (one capsule radius); tags [S1 C-n].

POD_L: 40 (stage-1 target, DROPPED), 41 (THE BASE since the gate-1 work, lead's decision 1 of 2026-11-14) or 42 (level 3): set the
environment variable V3F_POD_L.  Every feature of the hand end (E3, SW1, the button membrane, the E3 block) moves by POD_L - 40 mm and
the board is (POD_L - 3) x 29 mm.

GATE-1 OPTIONS (2026-11-14, v3/g1/cad/CAD_OPTIONS.md; tags [G1]).  The frozen stage-1 state of this folder is v3/cad_s1.
  V3F_POD_W  pod width across the wrist: 32 (base), 33, 34 (level 2). The extra width DW goes to the PV half (far long wall, root A):
             board (POD_L - 3) x (29 + DW), laminate and strips wider, root-A lands and the K zone follow the far edge; the window half,
             the rib, the antenna side, the optical cap and every part position of the window half stay where they are.
  V3F_OPT    comma-separated key=value list (levels 1 and 4), e.g. "fpc=dwg" or "fpc=over,raise=0.15,joint=zif" or "motor=d7":
             fpc=s1|dwg|over|rear  display FPC model: s1 = stage-1 corridor (default, unchanged); dwg = FPC outline as dimensioned in LD-29Y03
                               Figure 14-1 (9.47 mm wide for 5.63 mm from the glass, then a 5.5 mm tail; stiffener on the FRONT face, terminals
                               on the REAR face), return run on the board; over = return run carried over low parts by a fold former R0.48;
                               rear = [session 2] after the fold the return run rises (a gentle S inside the 0.8-6.0 mm bend area) and is
                               bonded under the panel's rear face. The S contains a reverse curve, so this routing NEEDS THE MAKER'S WRITTEN
                               CONSENT (LD-29Y03 Note 8-1-1); zones only, no 3-D model. It is the upper bound of level 1.
             fold=<mm>         start of the 180 deg fold from the glass edge (>= 0.8)
             rin=<mm>          fold inner radius for fpc=over (>= 0.45)
             raise=<mm>        panel, film, frame and window glass raised by this much (level 1: 0.05 / 0.10 / 0.15)
             joint=bridge|zif  how the FPC end is joined (its terminals face the panel after the fold): solder land + bridge flex, or a
                               top-contact ZIF connector
             motor=d8|d7|d6|none, mx=<X>, my=<Y>, notch=1   vibration motor variant and centre (level 4)
             strips=4|5        PV strips on the pod lid (level 2: wider strips or a fifth strip)
"""
import math, os, dataclasses, json
from dataclasses import dataclass
from shapely.geometry import Polygon, Point, box as sbox, LineString
from shapely.ops import unary_union

POD_L = float(os.environ.get("V3F_POD_L", "41"))      # [G1] 41 mm is the base (40 mm outline dropped)
POD_W = float(os.environ.get("V3F_POD_W", "32"))      # [B 1, 7]; [G1 level 2] 33 / 34
DX = POD_L - 40.0
DW = POD_W - 32.0                                     # [G1] extra width, all on the PV half (far wall)


def _parse_opt(txt):
    out = {}
    for kv in (txt or "").split(","):
        kv = kv.strip()
        if not kv:
            continue
        k, _, v = kv.partition("=")
        try:
            out[k.strip()] = float(v)
        except ValueError:
            out[k.strip()] = v.strip()
    return out


OPT = _parse_opt(os.environ.get("V3F_OPT", ""))
# [S2d 2026-11-15] stage 2d (v3/LEAD_NOTES.md 2k K-1..K-6, 2j J-1; v3/stage2d/STAGE2D.md), option key s2d=1 (with V3F_POD_L=43, V3F_POD_W=34):
#   K-2 pod 43 x 34 / board 40 x 31: the extra KX = POD_L - 41 mm goes into the strip between the plates; every hand-side X coordinate of the
#       41 mm model (X > 27.5: E2, strips' end, rib insert / posts, rail end / posts, E3, SW1, J11, frame ground) moves by KX, the elbow side stays.
#   K-1 motor cut-out over plate E2 (film kept under the motor), K-3 PV-half part height 1.20, K-5 rail foot X4 -0.5 mm, K-6 U10 island note,
#   J-1 J40 = BW0020AG (C2826518), zone height 3.10.
S2D = float(OPT.get("s2d", 0)) == 1.0
KX = (float(os.environ.get("V3F_POD_L", "41")) - 41.0) if S2D else 0.0


def _fmt(v):
    return (f"{v:g}" if isinstance(v, float) else str(v)).replace(".", "p")


TAG = f"L{int(POD_L)}" + (f"W{int(POD_W)}" if DW else "") + "".join(f"_{k}{_fmt(OPT[k])}" for k in sorted(OPT))
if os.environ.get("V3F_STAGE", "2b") != "2b":          # [S2b] stage-2a geometry runs go to their own folder
    TAG += "_s" + os.environ.get("V3F_STAGE")
IS_PLAIN = (DW == 0 and not OPT)                      # plain outline runs write to out/ as before; option runs to out/options/<TAG>/
OUT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out") if IS_PLAIN else
                           os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "options", TAG))
if not os.environ.get("V3F_NO_OUT"):                  # probes (options_table.py) import the geometry without creating folders
    os.makedirs(OUT_DIR, exist_ok=True)
CASE_R, WALL = 6.0, 1.0                               # [B 1, 7; REDESIGN 5.5 product ring walls 1.0 mm]
CAV_R = CASE_R - WALL                                 # 5.0
BOARD = dict(x0=1.5, y0=1.5, x1=38.5 + DX, y1=30.5 + DW, R=4.5)  # [B 5, 7] 38 x 29 at 41 x 32 (37 x 29 at 40 mm); R4.5 concentric with the cavity [P V2-B]
BOARD_L, BOARD_W = BOARD["x1"] - BOARD["x0"], BOARD["y1"] - BOARD["y0"]
LIP, LID_GAP = 0.40, 0.10                             # [E] PC bezel lip 0.40 mm at the outer edge (BASELINE plan: lid from 0.4); sealant gap
LID_IN = LIP + LID_GAP                                # glass / laminate edges 0.50 mm inside the outer outline
SETBACK = 2.5                                         # [B 7] lid set back 2.5 mm at the E3 end
X_LID1 = POD_L - SETBACK                              # 37.5: hand-end edge of both glasses


# ----------------------------------------------------------------------------------------------- 2-D helpers
def rrect(x0, y0, x1, y1, r, n=32):
    """rounded rectangle as a shapely polygon (all four corners radius r)"""
    if r <= 1e-9:
        return sbox(x0, y0, x1, y1)
    return sbox(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, quad_segs=n)


def case_outline():
    return rrect(0, 0, POD_L, POD_W, CASE_R)


def inset_outline(d):
    """outer outline inset by d (corner radius CASE_R - d, concentric)"""
    return rrect(d, d, POD_L - d, POD_W - d, CASE_R - d)


def cavity():
    return rrect(WALL, WALL, POD_L - WALL, POD_W - WALL, CAV_R)


def board_outline():
    b = BOARD
    return rrect(b["x0"], b["y0"], b["x1"], b["y1"], b["R"])


def to_board(x, y):
    return round(x - 1.5, 4), round(y - 1.5, 4)


def poly_board(p):
    """shapely polygon -> list of board-frame (x, y) tuples"""
    return [to_board(x, y) for x, y in list(p.exterior.coords)[:-1]]


# ----------------------------------------------------------------------------------------------- Z stack [B 8]
@dataclass(frozen=True)
class ZS:
    mesa: float = -0.80          # PPG mesa face (optical cap 1.15 from the PCB skin face) [B 8]
    floor1: float = 0.25         # floor: 0.25 PC film with Ti plates flush [B 8]
    carrier1: float = 0.35       # carrier film 0.10 [B 8]
    pcb1: float = 1.45           # PCB 6-layer 1.0 + tolerance = 1.10 [B 8; JLC]
    parts_gen: float = 2.50      # parts + solder 1.05 [B 8]
    parts_low: float = 2.20      # under the panel: bodies <= 0.70 + solder 0.05 [B 8]
    # PV column
    pv_seat: float = 2.45        # ring floor top -> PV seat 2.20 [B 8 'Ring']
    pv0: float = 2.65            # laminate underside: parts 2.50 + clearance 0.15 [B 8]; elastic bead 0.20 [G-14]
    pv1: float = 3.85            # laminate top, RFQ maximum 1.20 [B 8]
    pv_glass0: float = 3.35      # laminate glass 0.50 at the top [B 8]
    # window column
    sup0: float = 2.35           # panel support 0.10 [B 8]
    panel0: float = 2.45
    panel1: float = 3.25         # LS011B7DH03 0.745 + 0.055 allowance [B 8]; drawing max 0.855 -> 3.305 [DS LD29Y03 p.42]
    film0: float = 3.405         # [S1 C-10] air gap 0.10 kept at the MAX-material panel (3.305): 0.155 at the 0.80 allowance; film + OCA <= 0.25
    win0: float = 3.655
    win1: float = 4.355          # window glass 0.70 [B 8]; window column 5.155 mm max-material (was 5.10) [S1 C-10]
    win_seat: float = 3.205      # [E] ring / rib-insert / rail seat of the stainless window frame (bond line 0.20, frame 0.25 rigidly bonded)
    frame0: float = 3.405
    frame1: float = 3.655
    ant_seat: float = 3.455      # [E] PC seat of the glass in the antenna corner where the stainless frame is cut away (bond line 0.20)
    # rib [B 1, 13.4]
    rib_shelf0: float = 2.15     # [E] PC shelf under the PV seat; parts under the rib <= 0.50 mm bodies
    insert0: float = 2.45        # stainless insert 0.5 (Y) x 0.755 (Z): [B 1] 0.7 + 0.055 with the window seat [S1 C-10] (posts unchanged)
    insert1: float = 3.205
    rail0: float = 2.35          # [S1 C-1] underside of the antenna-side window rail (GF-LCP): 0.15 above the <= 0.75 mm parts under it
    # motor column [B 8]
    psa: float = 0.05
    motor_h_max: float = 2.20    # Vybronics VCLP0820 class 2.1 typ, 2.2 max class [B 5.2]
    # rims
    rim_top: float = 3.85        # K block (contacts) and E3 block tops [E: flush with the PV laminate]
    e3_t: float = 0.25           # Ti strip 0.25 mm [P REDESIGN 5.5]
    finger_work: float = 1.00    # BW0036BG working height [E, datasheet not found]; pin inner faces at pcb1 + 1.00
    shelf_e3_0: float = 2.85     # [E] underside of the E3 block shelf over SW1 (1.35 mm part: top 2.80)
    pv_flex1: float = 2.77       # [S2b] top of the laminate's flex backing (was a literal in model_v3f.py)
    cell0: float = 2.95          # [S2b] underside of the laminate's silicon (cells 0.165 mm; was a literal in model_v3f.py)

    @property
    def pod_pv(self): return self.pv1 - self.mesa            # 4.65
    @property
    def pod_win(self): return self.win1 - self.mesa           # 5.10
    @property
    def motor0(self): return (self.carrier1 if MOTOR_ON_FILM else self.floor1) + self.psa   # motor bottom (carrier film cut away; [S2d K-1] kept)
    @property
    def motor1(self): return self.motor0 + self.motor_h_max
    @property
    def finger_top(self): return self.pcb1 + self.finger_work


RAISE = float(OPT.get("raise", 0.0))                  # [G1 level 1] panel raised: the support legs grow, everything above the panel follows
Z = ZS()
if RAISE:
    Z = dataclasses.replace(Z, **{k: round(getattr(Z, k) + RAISE, 4) for k in (
        "parts_low", "sup0", "panel0", "panel1", "film0", "win0", "win1", "win_seat", "frame0", "frame1", "ant_seat", "insert1", "rail0")})
    # parts_low and rail0 rise too: the 0.15 mm clearance under the support frame and the rail is kept, so the low zone gains RAISE in height

# [S2b 2026-11-15] stage-2b fixes (v3/LEAD_NOTES.md 2c / 2d; v3/stage2b/cad/CAD2B.md). ON by default; V3F_STAGE=2a gives the stage-2a geometry.
#   M-2: window seat +0.09 (glass, frame, film + OCA, rail top, insert top, antenna-corner seat follow; the panel and its 0.10 gap do not):
#        air over the max-material panel 0.10 -> 0.19 mm; window top 4.595 = pod top 5.395 mm with the mesa.
#   T-1 + M-1: PV laminate raised until its top is flush with the window top (0.655 + 0.09 = 0.745 mm); seats, bond line (0.20, now a
#        STRUCTURAL rigid-epoxy bond on the ring and rib seats), K-block and E3-block tops follow. Air under the laminate 0.15 -> 0.895 mm.
STAGE = os.environ.get("V3F_STAGE", "2b")
S2B = STAGE == "2b"
WIN_SEAT_RAISE = 0.09 if S2B else 0.0
PV_LIFT = 0.0
if S2B:
    Z = dataclasses.replace(Z, **{k: round(getattr(Z, k) + WIN_SEAT_RAISE, 4) for k in (
        "win_seat", "frame0", "frame1", "film0", "win0", "win1", "ant_seat", "insert1")})
    PV_LIFT = round(Z.win1 - Z.pv1, 4)
    Z = dataclasses.replace(Z, **{k: round(getattr(Z, k) + PV_LIFT, 4) for k in (
        "pv_seat", "pv0", "pv1", "pv_glass0", "pv_flex1", "cell0", "rim_top")})
LUG_TOP = 2.45                                        # [S2b] lug strips keep their stage-2a top (they followed pv_seat before)
MINI = S2B and os.environ.get("V3F_MINI", "1") == "1"   # [mini-ECO 2026-11-15, LEAD_NOTES 2f F-4/F-5/F-7] V3F_MINI=0 gives stage 2b as published
BUMPER = (0.34 if MINI else 0.33) if S2B else 0.0                         # [S2b M-5] PC corner bumpers proud of the (flush) glass tops, the four R6 corners
# [S2e 2026-11-16] stage-2e CAD corrections (LEAD_NOTES 2l N-5; v3/stage2e/CAD2E.md), ON with s2d=1 (V3F_S2E=0 gives stage 2d as published):
#   rail foot X6 -> 6.7, rail foot X35.3 -> 33.4 (clear of J16_land), J40 zone = footprint courtyard and finger body inside the AE1 pocket
#   (J40 moved by J40_SHIFT), corner bumpers 0.35.
S2E = S2D and os.environ.get("V3F_S2E", "1") == "1"
if S2E:
    BUMPER = 0.35                                     # [S2e N-5] (stage-2d drop row 6: 0.35 needed at the 11.26 g pod)
# [P4 2026-11-16] lead ruling P-4 (LEAD_NOTES 2o; v3/prechecks/PRECHECKS.md C3/C4), option key p4=1 (track 2, v3/track2): the GF-LCP rail section
#   in X 1.1-11.5 (inside the antenna buffer) is 0.20 mm deeper (underside rail0 - 0.20; zone rail_strip_p4 h_max 0.70 there, parts <= 0.55 mm),
#   corner bumpers 0.36 mm. Off by default: the 40 x 31 main track is unchanged.
P4 = float(OPT.get("p4", 0)) == 1.0
RAIL_P4_DEEPEN = 0.20 if P4 else 0.0
if P4:
    BUMPER = 0.36
RAIL_CORE = S2B                                       # [S2b M-2] stainless rail section outside the antenna buffer; GF-LCP inside it (metal rule)
MATERIAL_NOTES = dict(                                 # [S2b] material notes (no geometry)
    window_glass="0.70 mm chemically strengthened, IR-cut (hot-mirror) coating removing about 40 % of the display's absorbed heat [S2b T-2; "
                 "assumed value, vendor figure needed]; border print absorptance <= " + ("0.20 [mini-ECO F-5]" if MINI else "0.25"),
    pv_laminate="0.50 mm CHEMICALLY STRENGTHENED glass (RFQ) [S2b M-1]; laminate print absorptance <= " + ("0.20 [mini-ECO F-5]" if MINI else "0.25 [S2b T-2]") + "; structural rigid-epoxy "
                "bond on the ring and rib seats (gap-filling grade) [S2b M-1]",
    capsule_top="0.50 mm chemically strengthened glass, white print underneath; capsule 4.6 mm [S2b M-3]",
    strap_roots_band="root A, root B (beyond the wing) and the textile band light coloured, solar absorptance <= 0.30 [S2b T-3]",
    corner_bumpers=f"black PC, moulded with the ring, {BUMPER:g} mm proud of the glass tops at the four R6 corners [S2b M-5" + ("; mini-ECO F-5" if MINI else "") + ("; S2e N-5]" if S2E else "]"),
    window_rail="316L stainless section 0.40 x full height outside the 5 mm antenna buffer, GF-LCP inside it and for the posts [S2b M-2]"
                + ("; posts at 2 mm pitch under the GF-LCP section (X 2-12) [mini-ECO F-4]" if MINI else ""),
    masked_window_interim="interim build with a masked window: mask absorptance <= 0.35 [S2b T-6]")

# ----------------------------------------------------------------------------------------------- top: glasses, rib [B 1, 7, 13.4]
STRIP_GAP, STRIP4_EXTRA = 0.27, 0.04                         # [B 7] gaps 0.27; [E] last strip +0.04 mm to win back its chamfered corner
STRIP_N = int(OPT.get("strips", 4))                           # [B 1] four strips in series; [G1 level 2] 5 = a fifth strip
STRIP_W = round((4 * 2.30 + 3 * STRIP_GAP + DW - (STRIP_N - 1) * STRIP_GAP) / STRIP_N, 4)   # [B 1] 2.30 at 32 mm; the silicon band grows by DW
if "sw" in OPT:   # [TRACK2 2026-11-16] option sw=<mm>: strip width fixed (the silicon band no longer grows with DW; the rest of the laminate is
    #   light print, absorptance <= 0.20) - thermal limit of the wider pod (v3/track2/TRACK2_CAD.md)
    STRIP_W = float(OPT["sw"])
STRIP_X = (4.1, 31.8 + KX)                                         # [B 7] +0.4 mm [S1 C-2]: K corner walls; silicon stops 5.8 mm before E3 at X 37.6
STRIP_Y0 = 21.0                                               # [B 1] from Y 21.0
LAM_EDGE_MARGIN = 0.45                                        # [E] laminate edge to silicon on the rib side (laminate edge Y 20.55)
Y_WIN1 = 20.45                                                # [E] window glass edge on the rib insert (BASELINE: 'to Y 20.5')
Y_LAM0 = 20.55                                                # [E] PV laminate edge on the rib shelf; 0.10 sealant joint between the glasses
X_LAM0 = 3.65                                                 # [S1 C-2] laminate edge at the K block (strips from X 4.1: margin 0.45)
X_KTOP1 = 3.55                                                # [S1 C-2] K block top surface ends here (0.10 joint to the laminate)
RIB = dict(x0=3.8, x1=X_LID1 - 0.5, y0=20.0, y1=21.0)        # [B 1] rib Y 20.0-21.0; [E] from the K block (X 3.8, S1 C-8) to the E3 block (X 37.0)
INSERT = dict(x0=3.8, x1=34.0 + KX, y0=20.0, y1=20.5)              # [B 13.1] stainless 0.5 x 0.755 (S1 C-10), X 1-34 in BASELINE; [E] X 3.8-34 (30.2 mm)
POST_X = (4.1, 10.0, 16.0, 22.0, 28.0, 33.0)                  # [B 5.1] six posts, pitch <= 6 mm (first post under the insert end, S1)
if S2D:   # [S2d K-2] hand-side posts move by KX; one post added in the widened strip so the pitch stays <= 6 mm
    POST_X = (4.1, 10.0, 16.0, 22.0, round((22.0 + 28.0 + KX) / 2, 2), 28.0 + KX, 33.0 + KX)
POST_SIZE, POST_Y = 0.6, (20.0, 20.6)                         # [B 10: 0.6 x 0.6 mm posts]; [E] centred Y 20.3 under the insert
POST_FOOT = (19.8, 20.8)                                      # [B 5.1] post feet on the board, 1.0 x 1.0 keep-out each

# LS011B7DH03 [DS LD29Y03 p.13, p.36, p.42]
PANEL_NOM = dict(L=32.00, W=14.00, t=0.745, t_tol=0.11, tol=0.20)   # general tolerance +-0.2
AA = dict(L=25.28, W=10.744, cx_from_fpc_edge=17.73, cy_from_edge=7.0, tol=0.15)
FPC = dict(len=13.63, len_tol=0.4, w_end=9.47, w=10.2, t=0.10, t_stiff=0.30, stiff_len=4.5, bend_min=0.8, bend_max=6.0, r_in_min=0.45,
           # [G1] read again on 2026-11-14 from the vector drawing LD-29Y03 p.42 Fig. 14-1 (coordinates measured, 5.670 pt/mm):
           w_wide=9.47, wide_len=5.63, w_tail=5.5, notch_at=4.11, notch_r=0.6, stiff_tol=0.5, term_len=3.5, term_apply=4.0, lat_tol=0.3)
#   s1 model: FPC width 10.2 mm 'read off the drawing' and a 9.47 mm end (stage 1). [G1] the drawing dimensions 9.47 as the WIDE part next to
#   the glass (to 5.63 mm from the glass edge, two R0.6 notches at 4.11 mm) and 5.5 +- 0.05 as the TAIL width (Detail A); the stiffener
#   (cross-hatched) is on the FRONT face and the terminals (Detail A, rear view) on the REAR face. Flexible part 0.10 mm thick [E].
FPC_MODEL = str(OPT.get("fpc", "s1"))
JOINT = str(OPT.get("joint", "land" if FPC_MODEL == "s1" else "bridge"))
PANEL_BASELINE = dict(x0=1.0, y0=6.0)                         # [B 7] panel X 1-33, Y 6-20
PANEL_SHIFT = (0.3, -0.3)                                     # [E] CAD fix: +0.3 in X (wall clearance at max material), -0.3 in Y (rib)
PANEL = dict(x0=PANEL_BASELINE["x0"] + PANEL_SHIFT[0], y0=PANEL_BASELINE["y0"] + PANEL_SHIFT[1])
PANEL.update(x1=PANEL["x0"] + PANEL_NOM["L"], y1=PANEL["y0"] + PANEL_NOM["W"])
FPC_EDGE_X = PANEL["x1"]                                      # the FPC leaves the hand-end short edge (the elbow edge touches the wall)
AA_CX = FPC_EDGE_X - AA["cx_from_fpc_edge"]
AA_CY = PANEL["y0"] + AA["cy_from_edge"]
AA_BOX = (AA_CX - AA["L"] / 2, AA_CY - AA["W"] / 2, AA_CX + AA["L"] / 2, AA_CY + AA["W"] / 2)
FPC_Y = (AA_CY - FPC["w"] / 2, AA_CY + FPC["w"] / 2)           # FPC centred on the panel (7 +- 0.3) [DS]
FPC_Z_EXIT = Z.panel0 + 0.115 + 0.25                           # FPC bonded on the TFT-glass ledge: bottom Pol 0.115 + TFT 0.25 [DS]
FPC_FOLD_AT = float(OPT.get("fold", 1.0))                      # [S1 C-4] fold 1.0 mm from the glass edge (allowed 0.8-6.0) [DS]: clears the SW1 land
FPC_TAPE = 0.05                                                # insulating tape under the FPC (on the board, or over the parts under it)
if FPC_MODEL in ("over", "rear"):                              # [G1 level 1] fold over a former of radius rin; the return run rides above the board
    FPC_FOLD_RIN = float(OPT.get("rin", 0.48))                 # former nose R0.48 +- 0.03, so the fold never goes below the 0.45 mm rule
    FPC_Z_RETURN = FPC_Z_EXIT - 2 * FPC_FOLD_RIN - FPC["t"]    # underside of the return run (rear: right after the fold, before the S-rise)
else:
    FPC_Z_RETURN = Z.pcb1 + FPC_TAPE                           # [E] the returning FPC lies on the board (0.05 tape), no parts under it
    FPC_FOLD_RIN = (FPC_Z_EXIT - (FPC_Z_RETURN + FPC["t"])) / 2.0  # inner radius of the 180 deg fold (>= 0.45 required)
FPC_ARC = math.pi * (FPC_FOLD_RIN + FPC["t"] / 2)              # centre-line length of the fold
FPC_END_X = FPC_EDGE_X + FPC_FOLD_AT - (FPC["len"] - FPC_FOLD_AT - FPC_ARC)
FPC_WIDE_X = FPC_EDGE_X + FPC_FOLD_AT - max(0.0, FPC["wide_len"] - FPC_FOLD_AT - FPC_ARC)   # [G1] where the 9.47 mm part ends on the return run
FPC_STIFF_X = (FPC_END_X, FPC_END_X + FPC["stiff_len"])         # stiffened terminal end [B 5.1]
FPC_Y_WIDE = (AA_CY - FPC["w_wide"] / 2, AA_CY + FPC["w_wide"] / 2)
FPC_Y_TAIL = (AA_CY - FPC["w_tail"] / 2, AA_CY + FPC["w_tail"] / 2)
FPC_UNDER_TOL = dict(worst=0.20, rss=0.098)                    # [G1, E] support legs + frame 0.05, bottom Pol + TFT 0.05, former nose 2 x 0.03,
#   FPC thickness 0.03, tape 0.01: 0.20 worst case, 0.098 RSS (v3/g1/cad/CAD_OPTIONS.md 2; src/fpc_options.py)
# [G1 session 2] fpc=rear: the return run bonded under the panel's rear face by a 0.05 mm PSA after an S-rise inside the bend area
FPC_PSA = 0.05
FPC_Z_REAR = Z.panel0 - FPC_PSA - FPC["t"]                     # underside of the bonded run (1.0 - 0.05 - 0.10 = 0.85 mm above the board, + raise)
FPC_SRISE = FPC_Z_REAR - FPC_Z_RETURN                          # 0.545 mm with the R0.48 former (independent of the panel raise)
FPC_REAR_TOL = dict(worst=0.11, rss=0.062)                     # [E] support legs + frame 0.05, PSA 0.02, FPC thickness 0.03, tape 0.01
FPC_JOINT_DROP = 0.15                                          # [E] the stiffened end hangs 0.15 mm below the panel rear: bridge flex 0.10 + solder 0.03 + margin
BRIDGE_DESCENT = 2.0                                           # [E] run of the bridge flex from the terminals (0.8 mm above the board) down to the J13 land, R 1.0 bends
J13_GROW = 0.005 if MINI else 0.0                              # [mini-ECO F-7] J13 zone Y 7.65 -> 7.66 = the FH34SRJ courtyard (parts.json)
ZIF = dict(part="Hirose FH34SRJ-10S-0.5SH(50) (C324723), top and bottom contact, back flip", h=1.0, w=7.15, depth=3.8, insert=3.3)
#   [S2a 2026-11-15] body read in the Hirose FH34 catalogue (Oct. 2022) p.6: A 7.0 +-0.15 (7.15 max), depth 3.8, height 1.0 (was 7.5 x 3.7 E);
#   insert (FPC tip to the entry face) stays an estimate [E]: the catalogue gives no insertion depth.
FILM = dict(x0=AA_BOX[0] - 0.8, x1=FPC_EDGE_X + 0.3, y0=AA_BOX[1] - 0.8, y1=AA_BOX[3] + 0.8)   # [E] film = AA + 0.8, to the LED end
FILM_TAIL = dict(x0=FPC_EDGE_X + 0.3, x1=FPC_EDGE_X + 0.6, y0=PANEL["y0"] + 0.05, y1=PANEL["y0"] + 1.65)   # [E] 1.6 mm tail, 0.1 beyond the max-material glass edge
J16 = dict(x0=FPC_EDGE_X + 0.6, x1=FPC_EDGE_X + 3.4, y0=PANEL["y0"] - 0.25, y1=PANEL["y0"] + 1.65)            # [B 5.1] 2 keyed pads; courtyard 2.8 x 1.9 [S1 C-5]
SUPPORT_BAND = 1.0                                             # [E] panel support frame: 0.10 mm under the panel's rear border, 1.0 mm band
SUPPORT_LEGS_D, SUPPORT_LEG_IN = 0.8, 0.6                      # [E] four PC legs to the board at the panel corners (keep-out dia 1.2)

ANT_KEEPOUT = (1.5, 6.5, 1.5, 4.5)                             # [B 7] 5 x 3 chip-antenna keep-out (x0, x1, y0, y1)
ANT_METAL_MIN = 5.0                                            # [P V2-B lgeom ANT_METAL_MIN, v1 R-RF-1] other metal >= 5 mm
ANT_PANEL_RULE = 1.5                                           # [P V3_ARCH 4.3 fix P-6] panel >= 1.5 mm in plan from the keep-out
E3_PANEL_RULE = 4.0                                            # [P display lane] panel glass edge >= 4.0 mm from E3 (S1 C-9: applied to all E3-net metal)
RULE_TOL = 0.01                                                # [S1 C-15] rules are tested on buffers drawn 0.01 mm larger (128 segments per quadrant)

# [S1 C-1] antenna-side window rail: without it the window glass spans 36 x 19 mm on elastic beads (review C-1); with it the free span is
# X 1.0-37.0 x Y 5.4-20.0 (rail and rib insert, both with a STRUCTURAL bond line), BASELINE 13.4's basis. Glass-filled LCP (non-metal:
# it runs inside the 5 mm antenna buffer), 0.40 x 0.855 mm, on 9 posts <= 4.0 mm apart standing on the board (feet 0.8 x 0.8 mm).
RAIL = dict(x0=1.1, x1=33.7 + KX, y0=5.0, y1=5.4)                  # x0 clear of the R5 cavity corner
RAIL_POST_X = (2.0, 6.0, 10.0, 13.5, 17.5, 21.5, 25.5, 29.5, 33.3)
RAIL_LCP_X1 = 11.5                                             # [S2b M-2] end of the GF-LCP rail section (5 mm antenna buffer)
if MINI:   # [mini-ECO F-4] posts at 2 mm pitch under the GF-LCP section X 1.1-11.5 (12.0 closes the span 10-13.5 across X 11.5)
    RAIL_POST_X = (2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 13.5, 17.5, 21.5, 25.5, 29.5, 33.3)
RAIL_FOOT_X4_SHIFT = -0.5 if S2D else 0.0                     # [S2d K-5] foot X4 moves 0.5 mm toward -X: room for C215 at the feed (LAYOUT.md 6)
if S2D:   # [S2d K-2] hand-side posts move by KX, one post added in the widened strip (pitch <= 4.0 kept); [K-5] X4 -> 3.5
    RAIL_POST_X = tuple([x + RAIL_FOOT_X4_SHIFT if x == 4.0 else x for x in RAIL_POST_X if x < 27.5] + [round((25.5 + 29.5 + KX) / 2, 2)]
                        + [round(x + KX, 2) for x in RAIL_POST_X if x > 27.5])
if S2E:   # [S2e N-5] foot X6 +0.7 (L204 beside C215 at the feed); end foot X35.3 -> 33.4 so its keep-out clears J16_land (board x0 32.4) by 0.10
    RAIL_POST_X = tuple({6.0: 6.7, round(33.3 + KX, 2): 33.4}.get(x, x) for x in RAIL_POST_X)
RAIL_POST = (0.5, 0.4)                                         # post X x Y (at Y 5.0-5.4)
RAIL_FOOT = 0.8                                                # board keep-out per post foot (square)
RAIL_E_GPA = 12.0                                              # [E] GF-LCP flexural modulus class (30 % glass), datasheet of the chosen grade needed

# [S2c 2026-11-15] lid antenna L1 (v3/sim/rf/lid, lead decision; v3/stage2c/ECO2C.md). ON by default with stage 2b; V3F_S2C=0 gives the mini-ECO geometry.
#   Printed silver strip + contact pad on the window glass's inner face (export/AE1_lid_L1.json "lid", case frame); stainless frame cut back to
#   X 13.0 in the long-wall border band Y 0.5-5.65 (glass seated on PC there, at ant_seat); J40 BW0019BG spring finger on AE1's FEED land.
S2C = S2B and os.environ.get("V3F_S2C", "1") == "1"
_AE1 = json.load(open("/path/to/SolarVest_work/wristband/v3/sim/rf/lid/export/AE1_lid_L1.json"))
LID_STRIP = Polygon(_AE1["lid"]["strip_case"][0])                 # case frame: strip 0.5 x (X 5.125-12.375, Y 1.5-2.0) + jog + pad X 3.875-5.875, Y 2.375-3.625
LID_STRIP_T = 0.012                                               # [E] fired silver >= 10 um + ENIG-class finish on the pad
LID_FRAME_CUT = sbox(-1.0, -1.0, 13.0, 5.65)                      # frame removed for X < 13.0 in Y 0.5-5.65 (glass starts at Y 0.5)
J40 = dict(land_board=tuple(_AE1["board"]["spring_land"]["centre_board"]), rot=_AE1["board"]["spring_land"]["rotation_deg_ccw_from_sky"],
           courtyard=Polygon([(x + 1.5, y + 1.5) for x, y in _AE1["board"]["spring_land"]["body_courtyard_board"][0]]),
           contact_case=tuple(c + 1.5 for c in _AE1["board"]["spring_land"]["contact_point_board"]), h_free=3.90,
           h_work=3.00, h_limit=2.50)                             # BW0019BG drawing 681-0019B-2 p.6 (read 2026-11-15): free 3.80 +0.10/-0.05, working 3.00, limit 2.50
if S2D:   # [S2d J-1] BW0020AG-L3.5W1.5H3.0 (C2826518): same land, position and rotation; free 3.00 (zone 3.10), working 2.50, limit 2.00 (ECO2C.md, drawing read by eye)
    J40.update(h_free=3.10, h_work=2.50, h_limit=2.00, part="BW0020AG-L3.5W1.5H3.0 (C2826518)")
else:
    J40.update(part="BW0019BG (C2826516)")
J40_SHIFT = (0.0, 0.0)
J40["body"] = J40["courtyard"]
if S2E:   # [S2e N-5] land-pattern courtyard (C2826516 footprint F.CrtYd, local X -2.70..1.30, Y +-1.00) and finger body 3.5 x 1.5 (local X -2.45..1.05,
    #   Y +-0.75: pad end + silk arm), both at rot 340 about the land centre; moved by J40_SHIFT so the body lies inside the AE1 pocket (Y < 3.0, R4.5 edge)
    #   with the glass contact point still on the lid pad (stage2e/j40_shift.py)
    from shapely import affinity as _aff
    J40_SHIFT = (0.38, -0.12)
    def _j40_rect(x0, x1, y0, y1):
        r = _aff.rotate(sbox(x0, y0, x1, y1), J40["rot"], origin=(0, 0))
        return _aff.translate(r, J40["land_board_s2d"][0] + 1.5 + J40_SHIFT[0], J40["land_board_s2d"][1] + 1.5 + J40_SHIFT[1])
    J40["land_board_s2d"] = J40["land_board"]
    J40["land_board"] = (round(J40["land_board"][0] + J40_SHIFT[0], 4), round(J40["land_board"][1] + J40_SHIFT[1], 4))
    J40["contact_case"] = tuple(round(c + d, 4) for c, d in zip(J40["contact_case"], J40_SHIFT))
    J40["courtyard"] = _j40_rect(-2.70, 1.30, -1.00, 1.00)
    J40["body"] = _j40_rect(-2.45, 1.05, -0.75, 0.75)
AE1_POCKET = Polygon([(x + 1.5, y + 1.5) for x, y in _AE1["board"]["copper_free_all_6_layers"]["board"][0]])
GLASS_GAP_TOL = 0.10                                              # [S2c] board-to-glass height at the antenna corner: +-0.10 mm (lid lane: about -24 Ohm per 0.25 mm)


def ant_seat_region():
    """[S2c] where the window glass sits on PC at ant_seat (no stainless frame): the 5 mm antenna buffer, plus the frame cut of the lid antenna"""
    return ant_buffer().union(LID_FRAME_CUT) if S2C else ant_buffer()


def keepout_poly():
    x0, x1, y0, y1 = ANT_KEEPOUT
    return sbox(x0, y0, x1, y1)


def ant_buffer(d=None):
    """keep-out buffered by the metal rule + RULE_TOL (S1 C-15: 128 segments, so the polygon chords never fall inside the rule)"""
    return keepout_poly().buffer((ANT_METAL_MIN if d is None else d) + RULE_TOL, quad_segs=128)


def window_glass_outline():
    """window glass: X 0.5..37.5, Y 0.5..20.45, R5.5 corners on the antenna side (concentric with R6)"""
    return inset_outline(LID_IN).intersection(sbox(LID_IN, LID_IN, X_LID1, Y_WIN1))


def lam_outline():
    """PV laminate: X 3.25..37.5, Y 20.55..31.5 inside the R5.5 corners"""
    return inset_outline(LID_IN).intersection(sbox(X_LAM0, Y_LAM0, X_LID1, POD_W - LID_IN))


def strips():
    """four silicon strips; the 4th is 0.04 mm wider and its elbow-end corner follows the laminate's 0.45 mm edge margin"""
    lam_in = lam_outline().buffer(-LAM_EDGE_MARGIN, quad_segs=32)
    out = []
    for i in range(STRIP_N):
        y0 = STRIP_Y0 + i * (STRIP_W + STRIP_GAP)
        y1 = y0 + STRIP_W + (STRIP4_EXTRA if i == STRIP_N - 1 else 0.0)
        r = sbox(STRIP_X[0], y0, STRIP_X[1], y1)
        out.append(r.intersection(lam_in))
    return out


def frame_outline():
    """stainless window frame (0.25 mm, rigidly bonded to the glass underside): the glass outline minus the film opening
    (+0.1), minus everything within ANT_METAL_MIN of the antenna keep-out"""
    g = window_glass_outline()
    opening = film_outline().buffer(0.1, join_style=2)
    tail = sbox(FILM_TAIL["x0"] - 0.1, FILM_TAIL["y0"] - 0.1, FILM_TAIL["x1"] + 0.1, FILM_TAIL["y1"] + 0.1)
    ant = ant_buffer()
    led = sbox(D10_WIN["x0"], LID_IN, D10_WIN["x1"], D10_WIN["y1"])            # [S1 C-6] notch over the D10 light path
    f = g.difference(opening).difference(tail).difference(ant).difference(led)
    if S2C:
        f = f.difference(LID_FRAME_CUT)                                   # [S2c] lid antenna L1: frame cut back to X 13.0 in Y 0.5-5.65
    return f


def film_outline():
    f = sbox(FILM["x0"], FILM["y0"], FILM["x1"], FILM["y1"])
    return f.union(sbox(FILM["x1"] - 2.0, FILM_TAIL["y0"], FILM["x1"], FILM["y0"] + 0.01))   # corner tab feeding the tail


# ----------------------------------------------------------------------------------------------- contacts (K corner) [B 1, 5.1, 16]
K_TOP = dict(x0=LIP + 0.0, x1=X_KTOP1, y0=Y_WIN1, y1=POD_W)  # top region of the K block (clipped by the outer outline)
K_BLOCK_IN = dict(x0=WALL, x1=3.8, y0=20.0, y1=POD_W - WALL)   # interior part of the K block (board keep-out X 1.5-4.0); X 3.8 (S1 C-8)
PINS = [  # [E] formed pins insert-moulded in the K block; top faces recessed; unequal diameters; inner faces >= 3.4 x 2.2 on J15 / J18 [B 1]
    # [S1 C-2] re-laid: >= 0.3 mm PC wall around each counterbore at its largest size (outer face, K-top edge, window-glass edge);
    # pitch 5.40 mm (was 6.203: the GND counterbore overlapped the laminate edge). [S1 C-8] lands: J15 body 0.05 mm clear of the
    # max-material panel in plan (body from Y 20.0, 0.10 mm; its courtyard reaches 0.26 mm into the panel's 0.5 mm planning margin), the J18 body 0.20 mm
    # clear of the J15 pin face, the J18 pad 0.31 mm from the R4.5 board corner; the faces 3.4 x 2.2 stay centred on the pads (E-13).
    # Ref of the GND finger = J18 (schematic).
    dict(name="pin_VBUS", ref="J15", net="VBUS (+5 V from the head)", top=(1.9, 21.9), d=1.6, land=(2.5, 22.15),
         cb_d=2.0, cb_tol=(0.0, -0.05), cb_edge="0.05 x 45 deg chamfer max", cb_edge_w=0.05),
    dict(name="pin_GND", ref="J18", net="GND", top=(1.9, 27.3), d=2.0, land=(2.65, 26.2),
         cb_d=2.4, cb_tol=(0.05, 0.0), cb_edge="0.10 x 45 deg lead-in", cb_edge_w=0.10),
]
CB_WALL_MIN = 0.30                                             # [S1 C-2] PC wall around every counterbore at its largest size


def cb_rmax(p):
    """largest counterbore radius: nominal + plus tolerance + edge break (head_interface.json)"""
    return (p["cb_d"] + max(p["cb_tol"])) / 2 + p["cb_edge_w"]
PIN_RECESS = 0.30                                              # [E] top faces 0.30 mm below the rim top, in counterbores d + 0.4
FACE = (3.4, 2.2)                                              # [B 1; P placement_proof J11 rule] inner face Y x X, centred on the land
J15_PAD = (1.2, 2.4)                                           # [P C2826535 footprint] pad X x Y (finger long axis along Y)
J15_BODY = (1.6, 3.6, -2.15, 1.45)                             # [P footprint silk] body X width, Y length, Y extent from the pad centre
J15_CRT = (1.72, -2.21, 1.45)                                   # [P parts.json C2826535] courtyard X width, Y extent from the pad centre
J15_H = 1.5                                                    # [P parts.json, verified] free height of the BW0036BG finger (working 1.0 E)
TARGETS = [dict(name="target_1", c=(1.5, 24.46), d=2.4, t=0.5, skin=0.20)]  # [S1 C-2] ferritic 430 disc between the counterbores (0.4 mm off the
#   pin axis): attach point for the head magnet only; it is no longer counted as a reversal key (ferritic: attracts either pole)
HEAD = dict(x0=-1.3, x1=27.2, y0=20.0, y1=35.0, h=7.0, seat_y0=21.0, rebate=(1.0, 0.8),   # [S1 C-12] head lane housing 28.5 x 15 x 7 mm; rebate 0.8 high,
            pogo_hf=dict(VBUS=(3.2, 1.9), GND=(3.2, 7.3)), magnet_hf=(2.8, 4.46),           # seat face from y 21.0, 1.0 x 0.6 rebate on the
            cable="+x (USB-C mouth at the hand-side end of the head)")                      # window side; head frame = v3/head/head_interface.json

# E3 and the hand-end block
E3_TOP = dict(x0=X_LID1 + 0.1, y0=3.0, y1=29.0)                # [P REDESIGN 5.5] Ti strip 26 x 3.5 incl. a 1.0 mm wrap; top part from X 37.6
E3_WRAP = dict(y0=6.5, y1=25.5, z0=Z.rim_top - 1.0, z1=Z.rim_top)   # [E] wrap down the end face on its straight part
E3_BLOCK = dict(x0=X_LID1 - 0.5, x1=POD_L - WALL)              # [E] interior shelf of the E3 block (seats for both glasses)
J11 = dict(land=(37.7 + DX, 9.5))                              # [E] E3 spring finger (BW0036BG) under the window-half shelf of the E3 block

# side button SW1 + membrane [DS PTS840 B-35; B 1, 13.4]
SW1 = dict(cy=15.5, body_x=2.9, body_y=3.5, h=1.35, lead_y=4.7, act_w=1.7, act_out=0.65, act_h=0.8, act_z_mid=0.68,
           front_x=BOARD["x1"] - 0.1)                          # body front 0.1 behind the board edge [DS '0 / -0.1']; actuator mid-height [E]
MEMBRANE = dict(y0=13.9, y1=17.1, z0=1.0, z1=2.75, t=0.40, nub_d=1.2)   # [E] TPE membrane window in the hand-end wall (3.2 x 1.75 mm)

# ----------------------------------------------------------------------------------------------- floor, cap, plates, motor
CAP = dict(x0=14.5, x1=25.5, y0=12.0, y1=19.0, R=1.5)          # [B 7 board zone c] optical cap 11 x 7, mesa 0.80 proud
WEB_MIN = 2.0                                                  # [P REDESIGN enclosure 4.4] PC web >= 2 mm between plates and around the cap
PLATE_INSET = 0.0                                              # [E] plates up to the board outline (0.5 mm inside the ring wall; bonded to the board)
MOTORS = {  # [G1 level 4] d, d_max (max-material E), board cut-out, max height, mass g, source
    "d8": dict(d=8.0, d_max=8.1, cut_d=8.6, h_max=2.20, g=0.45, part="Vybronics VCLP0820B004L class (dia 8.0 x 2.1 mm) [B 5.2]"),
    # [G1 session 2] maker pages read on 2026-11-15 (v3/cad/ref/sources.md): VC0720B001F dia 7.0 x 2.0 mm, 53 mA typ / 85 max, 0.10 Grms, FPC pads;
    # VC0625B001L dia 6.0 x 2.5 mm, 42 mA typ / 100 max. h_max = page thickness + 0.1 mm (E, as for the dia 8 class); masses E (scaled by volume).
    "d7": dict(d=7.0, d_max=7.1, cut_d=7.6, h_max=2.10, g=0.33, part="Vybronics VC0720B001F class (dia 7.0 x 2.0 mm, FPC pads)"),
    "d6": dict(d=6.0, d_max=6.1, cut_d=6.6, h_max=2.60, g=0.30, part="Vybronics VC0625B001L class (dia 6.0 x 2.5 mm): taller than the 2.2 mm motor column"),
    "none": dict(d=0.0, d_max=0.0, cut_d=0.0, h_max=0.0, g=0.0, part="no motor"),
}
MOTOR_KEY = str(OPT.get("motor", "d8"))
MOTOR = MOTORS[MOTOR_KEY]                                       # [B 5.2] dia 8 motor, 8.6 mm cut-out; [E] 8.1 max-material dia
HAS_MOTOR = MOTOR["d"] > 0
MOTOR_NOTCH = bool(OPT.get("notch", 0))                        # [G1] cut-out opened to the far board edge
MOTOR_PLATE_CLR = 1.0                                          # [E] motor body to any plate edge, in plan (creepage on the floor film)
CUT_EDGE_CLR = 0.3                                             # [P V2-B lgeom CU_EDGE] copper / pads to a routed edge
BOARD_EDGE_BAND = 0.5                                          # [B 7] the board's 0.5 mm edge band
RIB_MOTOR_CLR = 0.10                                           # [E] motor body clear of the rib shelf (Y 21.0) in plan
MOTOR_ANT_MIN = 10.0                                           # [B 13.1; eng_b] motor can and magnet >= 10 mm from the antenna
CONTACT_STRIP = (POD_W / 2 - 14.9 / 2, POD_W / 2 + 14.9 / 2)    # [P Lens D / attack_build calc.py] 14.9 mm skin-contact strip (convention), on the pod centre line
G7_MIN_MM2 = 150.0                                             # [P REDESIGN G-7] >= 1.5 cm2 of skin contact per plate
LAND_A = (5.1, 11.1, 25.9 + DW, 30.4 + DW)                     # [S1 C-5] root-A entry lands J3/J4/J5/J10: 4 x (1.5 x 4.5) courtyards of the
#   1.0 x 4.0 mm pads at 1.5 mm pitch; +0.6 mm in X so land 1 keeps 0.3 mm copper to the R4.5 board corner (pads Y 26.15-30.15)
LAND_B = (14.0, 17.0, 1.6, 6.1)                                # [S1 C-5] root-B entry lands J7/J9: 2 x (1.5 x 4.5) courtyards (pads Y 1.85-5.85)
D10 = dict(x0=17.5, x1=21.8, y0=1.5, y1=3.27, h=0.9)           # [S1 C-6] skin-hot LED KA-2810ASURSK (right angle) at the radial board edge,
D10_WIN = dict(x0=18.65, x1=20.65, y0=1.0, y1=1.6)             # emitting toward the wall; a 45 deg PC face turns the light up through a frame
#   notch and a clear dot in the glass print inside the window bond line (no new leak joint)
J6 = dict(x0=32.1, x1=35.6, y0=22.6, y1=28.3)                  # [S1 C-6] lid PV flex-tail land J6 (3 pads, courtyard 3.5 x 5.7 mm)
LID_TAIL = dict(x0=32.1, x1=35.6, y0=21.2, y1=22.6, r_bend=0.5)   # [S1 C-6] tail of the laminate flex: drops from Z 2.65 to the board
K_ZONE = (1.5, 4.0, 19.8, 30.5 + DW)                           # [B 7] J15 / K-block zone X 1.5-3.5; [E] to X 4.0 (inner faces + 0.3), from Y 19.8


def cap_poly():
    return rrect(CAP["x0"], CAP["y0"], CAP["x1"], CAP["y1"], CAP["R"])


PLATE_CORRIDOR = (CAP["x0"] - WEB_MIN, CAP["x1"] + WEB_MIN + KX, CAP["y1"] + WEB_MIN)   # (12.5, 27.5, 21.0): PC-only band between the plates
PLATE_Y = (5.0 + DW / 2, 27.0 + DW / 2)                        # [E] plates span the 14.9 mm contact strip +- 3.5 mm (pod roll, misplacement); [G1] on the pod centre line


def plate_outlines():
    """V3-F floor plates, fixed FIRST (V3-G9), without reference to a motor position: Ti Gr2 0.25 mm inlaid flush in the
    0.25 mm PC floor film. Rules: inside the board outline (0.5 mm from the ring wall; bonded to the board by silver-epoxy dots; B.Cu and L5
    void above them); >= 2 mm PC web to the optical cap, which also fixes their inner edges at X 12.5 and 27.5 over the
    full height (a PC-only corridor between them, where the motor goes); >= 5 mm from the antenna keep-out (metal rule);
    Y 5.0-27.0 (the 14.9 mm skin-contact strip +- 3.5 mm; more plate area outside the strip only adds void copper layers
    and titanium). Returns (E1, E2): E1 elbow end, E2 hand end; corners >= 0.5 mm radius.
    [S1 C-18] B.Cu and In4.Cu are void above the plates EXCEPT the four B.Cu plate-dot pads E11, E12 (E1) and E21, E22 (E2), 2.0 mm ENIG,
    which carry the silver-epoxy dots that bond and connect the plates (positions: plate_dot_pads())."""
    inner = board_outline().buffer(-PLATE_INSET, quad_segs=32)
    ant = ant_buffer()
    cx0, cx1, _ = PLATE_CORRIDOR
    left = inner.intersection(sbox(-1, PLATE_Y[0], cx0, PLATE_Y[1])).difference(ant)
    right = inner.intersection(sbox(cx1, PLATE_Y[0], 60, PLATE_Y[1]))
    if not HAS_MOTOR:   # [G1 level 4] no motor: the plates take the motor corridor beyond the cap web (Y >= 21.0), 2 mm PC web between them
        xm = (cx0 + cx1) / 2
        ext = sbox(cx0 - 1.0, PLATE_CORRIDOR[2], xm - WEB_MIN / 2, PLATE_Y[1]), sbox(xm + WEB_MIN / 2, PLATE_CORRIDOR[2], cx1 + 1.0, PLATE_Y[1])
        left = left.union(inner.intersection(ext[0])); right = right.union(inner.intersection(ext[1]))
    def main(g):   # largest piece, corners >= 0.5 mm radius
        if g.geom_type == "MultiPolygon":
            g = max(g.geoms, key=lambda p: p.area)
        return g.buffer(-0.5, quad_segs=16).buffer(0.5, quad_segs=16)
    return main(left), main(right)


def contact_area(p, strip=CONTACT_STRIP):
    return p.intersection(sbox(-5, strip[0], 60, strip[1])).area


# ----------------------------------------------------------------------------------------------- straps and worn geometry [B 9]
BAR_OUT, STRAP_T = 2.5, 1.5                                    # [P strap lane wrist_light.py] bar 2.5 mm outside the wall, 1.5 mm strap
BAR_Z = 1.0                                                    # strap centre line leaves the bar 1.0 mm above the floor plane
LUG = dict(w=BAR_OUT, z0=0.0, z1=2.25, x0=(POD_L - 35.0) / 2, x1=(POD_L + 35.0) / 2, bar_d=0.8)   # [E] PC lug strip + 0.8 mm stainless pin anchoring the TPU hinge
CAPSULE = dict(L=38.4, w=11.9, t=4.5, s0=2.0, s1=13.9, wall=0.40, side=0.50, top=0.40, gap=0.20, cell_t=3.50,
               pcm_len=4.0, cell=(30.0, 10.0), tabs=3.4, r_far=1.0, x0=(POD_L - 38.4) / 2)   # [B 1, 5.2, 9]; [E] far-edge radius 1.0 (S1 C-18: one constant)
WING = dict(L=35.0, s0=2.0, s1=13.7, t=2.95, lam=1.75, core=1.20, cells=4, cell_s=2.7, cell_x=31.0, x0=(POD_L - 35.0) / 2)   # [B 1, 9]
if S2B:
    # [S2b M-3] capsule top 0.50 mm strengthened glass, capsule 4.5 -> 4.6 mm (cell space unchanged)
    CAPSULE.update(t=4.6, top=0.50)
    # [S2b T-3] wing: active silicon ends at s 8 mm (thermal case "mit-a wing to s 8 + strap a 0.30"); the laminate ends there too, root B
    # continues as light strap. Still 4 sub-cells in series (string voltage), same margins as before: 0.45 mm before the first cell,
    # 0.075 mm gaps -> sub-cells 1.275 mm along s (was 2.7).
    WING.update(s1=8.0)
    WING.update(cell_s=round((WING["s1"] - WING["s0"] - 0.6) / WING["cells"] - 0.075, 4))


def wing_cells_s():
    """[S2b] s-ranges (mm from the bar) of the wing's sub-cells, as built by worn_v3f.wing_parts()"""
    w = WING; pitch = (w["s1"] - w["s0"] - 0.6) / w["cells"]
    return [(round(w["s0"] + 0.45 + i * pitch, 4), round(w["s0"] + 0.45 + i * pitch + w["cell_s"], 4)) for i in range(w["cells"])]
ROOT_END_S = 16.0                                              # [B 9] root A ends at s 16 mm; root B the same
QR = dict(s0=16.0, s1=19.0, t=2.0)                             # [E] quick-release connector at each root end
BAND = dict(w=22.0, t=1.5)                                     # [E] textile band 22 mm wide (not fixed in BASELINE), 1.5 mm [B 9]
BUCKLE = dict(w=24.0, l=6.0, t=2.5)                            # [E] slide buckle / D-ring frame at the volar midline
WRIST_Q = 0.68                                                 # [P strap lane G2: wrist index 0.67-0.68]
WRISTS = (130.0, 140.0, 165.0, 200.0)                          # [B 18 V3-G9]


def ellipse_axes(Cw, q=WRIST_Q):
    """semi-axes (a = half width, b = half depth) of an ellipse of perimeter Cw, b = q a (Ramanujan II) [P strap lane]"""
    def per(a):
        b = q * a; h = ((a - b) / (a + b)) ** 2
        return math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))
    lo, hi = 1.0, Cw
    for _ in range(100):
        m = 0.5 * (lo + hi)
        if per(m) < Cw: lo = m
        else: hi = m
    a = 0.5 * (lo + hi)
    return a, q * a


def wrist_geo(Cw, q=WRIST_Q, ts=STRAP_T):
    """port of v3/decide/calc/baseline_calc.py wrist_geo (strap lane model). Frame: ellipse centre at (0, 0), dorsal
    vertex (0, b); returns the bar point P0, tangent parameter t0, free span, tilt (deg), unit vectors."""
    a, b = ellipse_axes(Cw, q)
    def pt(t, off=0.0):
        n = (math.sin(t) / a, math.cos(t) / b); nn = math.hypot(*n); n = (n[0] / nn, n[1] / nn)
        return (a * math.sin(t) + off * n[0], b * math.cos(t) + off * n[1]), n
    P0 = (POD_W / 2 + BAR_OUT, b + BAR_Z)
    def f(t):
        q_, n_ = pt(t, ts / 2)
        return (P0[0] - q_[0]) * n_[0] + (P0[1] - q_[1]) * n_[1]
    lo, hi = 0.05, math.pi / 2 + 0.5
    for _ in range(80):
        m = 0.5 * (lo + hi)
        if f(lo) * f(m) <= 0: hi = m
        else: lo = m
    t0 = 0.5 * (lo + hi); q0, _ = pt(t0, ts / 2)
    free = math.hypot(P0[0] - q0[0], P0[1] - q0[1]); d = ((q0[0] - P0[0]) / free, (q0[1] - P0[1]) / free)
    tilt = math.degrees(math.atan2(-d[1], d[0]))
    n = (-d[1], d[0])                       # outward normal of the strap line (pointing away from the skin)
    if n[1] < 0: n = (-n[0], -n[1])
    return dict(C=Cw, q=q, a=a, b=b, P0=P0, t0=t0, free=free, tilt=tilt, d=d, n=n, q0=q0)


def ellipse_dist(p, a, b, n=20000):
    """distance from point p to the ellipse x^2/a^2 + y^2/b^2 = 1 (sampled, 0.01 mm class), signed: + outside"""
    import numpy as np
    th = np.linspace(-math.pi, math.pi, n)
    ex, ey = a * np.sin(th), b * np.cos(th)
    d = float(np.min(np.hypot(p[0] - ex, p[1] - ey)))
    inside = (p[0] / a) ** 2 + (p[1] / b) ** 2 < 1.0
    return -d if inside else d


def summary():
    e1, e2 = plate_outlines()
    return dict(POD_L=POD_L, board=BOARD, panel=PANEL, aa=AA_BOX, fpc_y=FPC_Y, fpc_fold_rin=round(FPC_FOLD_RIN, 3),
                fpc_end_x=round(FPC_END_X, 2), film=FILM, rib=RIB, insert=INSERT, posts=POST_X,
                strips_mm2=[round(s.area, 3) for s in strips()], e1_mm2=round(e1.area, 1), e2_mm2=round(e2.area, 1),
                e1_contact_mm2=round(contact_area(e1), 1), e2_contact_mm2=round(contact_area(e2), 1),
                pod_pv=Z.pod_pv, pod_win=Z.pod_win)


MOTOR_C = (float(OPT.get("mx", 20.0)), float(OPT.get("my", 25.4)))   # [B 7, E-11] planning centre (20.0, 25.4), legal in motor_search.py (V3-G9)
MOTOR_ON_FILM = S2D                                            # [S2d K-1] the motor stands on the carrier film over plate E2 (double insulation, R-1)
J6_MOTOR_GAP = 0.05                                            # [S2d] J6 / lid-tail edge 0.05 beyond the motor's 0.3 mm edge keep-out
if S2D:
    # [S2d K-1] motor over plate E2: motor_search.py (K-1 mode) legal window X 33.80-35.85, Y 25.35-27.70 (hole). Centre = largest legal X - 0.10
    # (35.75: the hand side of E2, J6 as far out of the strip as possible); Y 25.55 so the J17 wire pads fit on the +Y side inside the board.
    # J6 and the lid flex tail cannot stay on E2 beside the motor (no room between the motor and the E3 shelf): they sit on the elbow side
    # of the motor cut-out, across the E2 edge of the strip (zero-height land + the flex drop). E1 has no legal spot (K zone to X 4.0 + U10 island).
    MOTOR_C = (float(OPT.get("mx", 35.75)), float(OPT.get("my", 25.55)))
    _jx1 = round(MOTOR_C[0] - MOTOR["cut_d"] / 2 - CUT_EDGE_CLR - J6_MOTOR_GAP, 2)
    _jw = J6["x1"] - J6["x0"]
    J6.update(x0=round(_jx1 - _jw, 2), x1=_jx1); LID_TAIL.update(x0=round(_jx1 - _jw, 2), x1=_jx1)


def fpc_fold_outer_x():
    return FPC_EDGE_X + FPC_FOLD_AT + FPC_FOLD_RIN + FPC["t"]


DESIGN_PARTS = "/path/to/SolarVest_work/wristband/v3/design/parts.json"   # read-only: courtyards and heights of the built netlist


def design_parts():
    import json
    try:
        return json.load(open(DESIGN_PARTS))["variants"]["v3f"]["parts"]
    except Exception:   # noqa: BLE001
        return {}


O2_REFS = ("Q14", "R174", "C174", "Q16", "C175", "R176", "Q17", "R175", "Q18", "D19", "C170", "R170", "R171", "R172", "U19", "U20")


def o2_courtyard_mm2():
    P = design_parts()
    return round(sum(P[r]["courtyard_area_mm2"] for r in O2_REFS if r in P), 2), [r for r in O2_REFS if r in P]


def sw1_land():
    """[S1 C-4] SW1 courtyard and copper from the reviewed C221907 land (v3/design/lib/easyeda_rev.pretty, pad 5 deleted): footprint frame
    courtyard x -2.81 .. 1.23, y +-3.27; pads x -1.64 .. 0.70, y +-3.0125; actuator at -x. On the board it is turned 180 deg (actuator to +X):
    case X = Xc - x_fp, with the body front (x_fp -1.92) at SW1 front_x."""
    xc = SW1["front_x"] - 1.92
    crt = (xc - 1.23, SW1["cy"] - 3.27, xc + 2.81, SW1["cy"] + 3.27)
    cu = (xc - 0.70, SW1["cy"] - 3.0125, xc + 1.64, SW1["cy"] + 3.0125)
    return dict(xc=xc, courtyard=crt, copper=cu)


def finger_courtyard(land):
    lx, ly = land
    return sbox(lx - J15_CRT[0] / 2, ly + J15_CRT[1], lx + J15_CRT[0] / 2, ly + J15_CRT[2])


def rail_posts():
    return [sbox(x - RAIL_POST[0] / 2, RAIL["y0"], x + RAIL_POST[0] / 2, RAIL["y1"]) for x in RAIL_POST_X]


def rail_feet():
    yc = (RAIL["y0"] + RAIL["y1"]) / 2
    return [sbox(x - RAIL_FOOT / 2, yc - RAIL_FOOT / 2, x + RAIL_FOOT / 2, yc + RAIL_FOOT / 2) for x in RAIL_POST_X]


def plate_dot_pads():
    """[S1 C-18] B.Cu dot pads that bond and connect the Ti plates (2.0 mm ENIG, parts.json E11/E12/E21/E22): two per plate, placed on
    the plate centre line in Y, 3 mm inside each end of the plate's straight part [E: positions for V3-G1]"""
    e1, e2 = plate_outlines()
    out = []
    for nm, e in (("E1", e1), ("E2", e2)):
        x0, y0, x1, y1 = e.bounds; yc = (y0 + y1) / 2
        for k, x in enumerate((x0 + 3.0, x1 - 3.0)):
            out.append(dict(name=f"{nm}{k + 1}", centre=(round(x, 2), round(yc, 2)), d=2.0))
    return out


def board_zones():
    """board-top (sky side, F.Cu) zones for layout, case frame. Each: name, kind, geom (shapely), h_max = maximum part
    height above the board top incl. solder (None = no limit beyond the general zone; 0 = no parts), note.
    kinds: height_limit (parts up to h_max), part / land (a named part's courtyard: only that part, up to h_max), no_parts,
    keepout, keepout_except (only the named parts inside), cutout, keepout_all_layers. [S1 C-5] part and land zones are drawn from the
    parts.json courtyards of the built netlist."""
    bo = board_outline()
    def bx(x0, y0, x1, y1): return sbox(x0, y0, x1, y1).intersection(bo)
    P = design_parts()
    def cy(ref): return tuple(P.get(ref, {}).get("courtyard_mm") or (0.0, 0.0))
    Z_ = []
    pan = sbox(PANEL["x0"], PANEL["y0"], PANEL["x1"], PANEL["y1"]).buffer(0.5, join_style=2).intersection(bo)
    Z_.append(dict(name="low_under_panel", kind="height_limit", geom=pan, h_max=round(Z.parts_low - Z.pcb1, 2),
                   note="LS011B7DH03 outline + 0.5 mm: bodies <= 0.70 mm + solder [B 7, 8]"))
    Z_.append(dict(name="rail_strip", kind="height_limit", geom=bx(RAIL["x0"], RAIL["y0"] - 0.2, RAIL["x1"], RAIL["y1"] + 0.2),
                   h_max=round(Z.rail0 - 0.15 - Z.pcb1, 2), note="under the antenna-side window rail (underside Z 2.35): bodies <= 0.70 mm + solder [S1 C-1]"))
    if P4:   # [P4] GF-LCP section 0.20 deeper in X 1.1-11.5: the lower limit wins there (lgeom takes the minimum of the height limits)
        Z_.append(dict(name="rail_strip_p4", kind="height_limit", geom=bx(RAIL["x0"], RAIL["y0"] - 0.2, RAIL_LCP_X1, RAIL["y1"] + 0.2),
                       h_max=round(Z.rail0 - RAIL_P4_DEEPEN - 0.15 - Z.pcb1, 2),
                       note=f"[P-4] under the GF-LCP rail section X {RAIL['x0']:g}-{RAIL_LCP_X1:g} (0.20 mm deeper, underside Z {Z.rail0 - RAIL_P4_DEEPEN:.2f}): "
                            "0402 parts <= 0.55 mm (C215, L204, C213 / C502 class); LQW15AN height to confirm"))
    Z_.append(dict(name="rib_strip", kind="height_limit", geom=bx(RIB["x0"] - 0.3, 19.8, RIB["x1"] + 0.3, 21.2),
                   h_max=round(Z.rib_shelf0 - 0.15 - Z.pcb1, 2), note="under the rib's PC shelf (Z 2.15): bodies <= 0.50 mm [E]"))
    Z_.append(dict(name="e3_shelf_pv", kind="height_limit", geom=bx(E3_BLOCK["x0"] - 0.3, Y_WIN1 - 0.3, POD_L, BOARD["y1"]),
                   h_max=round(Z.rib_shelf0 - 0.15 - Z.pcb1, 2), note="under the PV-half shelf of the E3 block (Z 2.15) [E]"))
    xo = fpc_fold_outer_x()
    jx, jy = cy("J13") or (6.4, 2.1)
    jl, js = max(jx, jy), min(jx, jy)
    if FPC_MODEL == "s1":
        Z_.append(dict(name="fpc_corridor", kind="no_parts", geom=bx(FPC_END_X - FPC["len_tol"], FPC_Y[0] - 0.1, xo + 0.2, FPC_Y[1] + 0.1),
                       h_max=0.0, note="display FPC folded 180 deg at 1.0 mm from the glass edge and returned under the panel, lying on the "
                                       "board; its stiffened end (J13) at the corridor's elbow end; +0.2 mm at the fold for the panel tolerance "
                                       "[DS LD29Y03 p.36, p.42; E; S1 C-4]"))
        Z_.append(dict(name="J13_land", kind="land", geom=bx(FPC_END_X, AA_CY - jl / 2, FPC_END_X + js, AA_CY + jl / 2), h_max=0.0,
                       note=f"soldered FPC land: 10 pads 0.3 x 1.6 at 0.5 + key pad, under the stiffened FPC end; courtyard {jx} x {jy} (parts.json) [B 5.1; S1 C-5]"))
    else:
        # [G1 level 1] FPC outline as dimensioned in LD-29Y03 Fig. 14-1: 9.47 mm wide to 5.63 mm from the glass edge, then a 5.5 mm tail.
        # Lateral tolerance 7 +- 0.3 (+0.1 margin); tip +- 0.4 (length 13.63 +- 0.4); fold column +0.2 for the panel outline tolerance.
        lt, lat = FPC["len_tol"], FPC["lat_tol"] + 0.1
        wy0, wy1 = FPC_Y_WIDE[0] - lat, FPC_Y_WIDE[1] + lat
        ty0, ty1 = FPC_Y_TAIL[0] - lat, FPC_Y_TAIL[1] + lat
        xf = FPC_EDGE_X + FPC_FOLD_AT
        Z_.append(dict(name="fpc_fold", kind="no_parts", geom=bx(xf - 0.2, wy0, xo + 0.2, wy1), h_max=0.0,
                       note=f"180 deg fold of the display FPC (start {FPC_FOLD_AT:g} mm from the glass edge, inner R {FPC_FOLD_RIN:.3f} mm, rule 0.8-6.0 mm / "
                            f"R >= 0.45): the fold column from Z {FPC_Z_RETURN:.3f} to {FPC_Z_EXIT + FPC['t']:.3f}; +0.2 mm for the panel tolerance [DS LD29Y03 p.36]"))
        if JOINT == "zif":      # top-contact ZIF on the board under the stiffened end (the terminals face the panel after the fold)
            zx0, zx1 = FPC_END_X + ZIF["insert"] - ZIF["depth"] - 0.25, FPC_END_X + ZIF["insert"] + 0.25
            Z_.append(dict(name="J13_land", kind="part", geom=bx(zx0, AA_CY - ZIF["w"] / 2 - 0.25 - J13_GROW, zx1, AA_CY + ZIF["w"] / 2 + 0.25 + J13_GROW), h_max=ZIF["h"],
                           note=f"J13 as a TOP-contact ZIF connector ({ZIF['part']}; body {ZIF['w']} x {ZIF['depth']} x {ZIF['h']} mm E, courtyard +0.25): "
                                f"the FPC terminals face the panel after the fold [DS LD29Y03 p.42]; needs the panel raised (gap to the panel "
                                f"{Z.panel0 - Z.pcb1 - ZIF['h']:.2f} mm at this stack) [G1]"))
            tail_x0 = zx1
        else:                   # solder land beyond the tail tip, joined to the upward-facing terminals by a 10-trace bridge flex
            lx1 = FPC_END_X - lt - 0.2
            if FPC_MODEL == "rear":     # the bridge has to come down from the raised terminals to the board before the land
                Z_.append(dict(name="bridge_descent", kind="no_parts", geom=bx(lx1 - BRIDGE_DESCENT, ty0, lx1, ty1), h_max=0.0,
                               note=f"bridge flex descending from the FPC terminals to the J13 land ({BRIDGE_DESCENT:g} mm run): no parts [G1 session 2; E]"))
                lx1 -= BRIDGE_DESCENT
            Z_.append(dict(name="J13_land", kind="land", geom=bx(lx1 - js, AA_CY - jl / 2, lx1, AA_CY + jl / 2), h_max=0.0,
                           note=f"J13 solder land (10 pads 0.3 x 1.6 at 0.5 + key, courtyard {jx} x {jy}) placed BEYOND the FPC tip; a 10-trace bridge flex "
                                f"(pads down, 0.10 mm) is soldered onto the FPC terminals, which face the panel after the fold [DS LD29Y03 p.42], and onto "
                                f"this land; stack at the joint 0.45 mm above the board [G1; E]"))
            tail_x0 = lx1
        stiff_x1 = FPC_END_X + FPC["stiff_len"] + FPC["stiff_tol"] + 0.2
        if FPC_MODEL == "rear":
            x6 = xf - (FPC["bend_max"] - FPC_FOLD_AT - FPC_ARC)       # where the 6.0 mm end of the bend area lies on the return run
            h_run = round(FPC_Z_REAR - Z.pcb1 - FPC_TAPE - FPC_REAR_TOL["worst"], 3)
            h_stf = round(h_run - FPC_JOINT_DROP - (FPC["t_stiff"] - FPC["t"]), 3)
            cons = ("NEEDS THE MAKER'S WRITTEN CONSENT (the S-rise has a reverse curve, LD-29Y03 Note 8-1-1; without it this zone file must not be used) "
                    "[G1 session 2]")
            Z_.append(dict(name="under_fpc_srise", kind="no_parts", geom=bx(x6, wy0, xf - 0.2, wy1), h_max=0.0,
                           note=f"S-rise of the return run ({FPC_SRISE:.3f} mm up to the panel rear, inside the bend area that ends 6.0 mm from the glass edge): "
                                f"no parts. " + cons))
            Z_.append(dict(name="under_fpc_tail", kind="height_limit", geom=bx(stiff_x1 + lt, ty0, x6, ty1), h_max=h_run,
                           note=f"5.5 mm tail bonded under the panel rear (0.05 PSA; underside {FPC_Z_REAR - Z.pcb1:.3f} mm above the board): parts incl. solder "
                                f"<= {h_run} mm worst case under a 0.05 mm insulating tape. " + cons))
            Z_.append(dict(name="under_fpc_stiff", kind="height_limit", geom=bx(FPC_END_X - lt, ty0, stiff_x1 + lt, ty1), h_max=h_stf,
                           note=f"stiffened FPC end (stiffener 0.20 mm on the board side) hanging {FPC_JOINT_DROP:g} mm below the panel rear for the bridge joint: "
                                f"parts incl. solder <= {h_stf} mm worst case. " + cons))
        elif FPC_MODEL == "over":
            h_wc = round(FPC_Z_RETURN - Z.pcb1 - FPC_TAPE - FPC_UNDER_TOL["worst"], 3)
            h_rss = round(FPC_Z_RETURN - Z.pcb1 - FPC_TAPE - FPC_UNDER_TOL["rss"], 3)
            kind = "height_limit" if h_wc >= 0.2 else "no_parts"
            hm = h_wc if kind == "height_limit" else 0.0
            nt = (f"under the display FPC's return run (underside Z {FPC_Z_RETURN:.3f}, fold former R {FPC_FOLD_RIN:g}, panel raised {RAISE:g} mm): parts incl. "
                  f"solder <= {h_wc} mm worst case ({h_rss} mm RSS) under a 0.05 mm insulating tape [G1 level 1]")
            Z_.append(dict(name="under_fpc_stiff", kind="no_parts", geom=bx(tail_x0, ty0, stiff_x1, ty1), h_max=0.0,
                           note="stiffened FPC end (stiffener 0.20 mm on the board side, 4.5 +- 0.5 mm long), entering the ZIF or carrying the bridge "
                                "joint: no parts [G1]"))
            Z_.append(dict(name="under_fpc_tail", kind=kind, geom=bx(stiff_x1, ty0, FPC_WIDE_X - lt, ty1), h_max=hm, note="5.5 mm tail: " + nt))
            Z_.append(dict(name="under_fpc_wide", kind=kind, geom=bx(FPC_WIDE_X - lt, wy0, xf - 0.2, wy1), h_max=hm, note="9.47 mm wide part: " + nt))
        else:
            Z_.append(dict(name="fpc_tail", kind="no_parts", geom=bx(tail_x0, ty0, FPC_WIDE_X - lt, ty1), h_max=0.0,
                           note="5.5 mm FPC tail lying on the board (0.05 tape); its last 4.5 +- 0.5 mm carry the stiffener on the board side [DS LD29Y03 p.42; G1]"))
            Z_.append(dict(name="fpc_wide", kind="no_parts", geom=bx(FPC_WIDE_X - lt, wy0, xf - 0.2, wy1), h_max=0.0,
                           note="9.47 mm wide part of the FPC return run lying on the board (0.05 tape) [DS LD29Y03 p.42; G1]"))
    Z_.append(dict(name="film_tail", kind="no_parts", geom=bx(FILM_TAIL["x0"] - 0.1, FILM_TAIL["y0"] - 0.1, FILM_TAIL["x1"] + 0.1, FILM_TAIL["y1"] + 0.1),
                   h_max=0.0, note="front-light film tail folding down beside the panel's FPC end [E]"))
    Z_.append(dict(name="J16_land", kind="land", geom=bx(J16["x0"], J16["y0"], J16["x1"], J16["y1"]), h_max=0.0,
                   note=f"front-light tail, 2 keyed pads, hand-soldered; courtyard {cy('J16')} (parts.json) [B 5.1; S1 C-5]"))
    Z_.append(dict(name="K_zone", kind="keepout_except", geom=bx(K_ZONE[0], K_ZONE[2], K_ZONE[1], K_ZONE[3]), h_max=0.0,
                   note="under the K block: only the two contact fingers J15 (VBUS) and J18 (GND) [B 7; S1 C-5]"))
    for p in PINS:
        Z_.append(dict(name=f"{p['ref']}_land", kind="part", geom=finger_courtyard(p["land"]), h_max=J15_H,
                       note=f"BW0036BG spring finger {p['ref']} for {p['name']} (C2826535): courtyard 1.72 x 3.66 (parts.json), free height 1.5 mm; "
                            f"pin inner face >= 3.4 x 2.2 mm centred on the pad; tip position unknown until the BW0036BG drawing is read [S1 C-5, C-8]"))
    jx, jy = J11["land"]
    Z_.append(dict(name="J11_zone", kind="keepout_except", geom=bx(jx - 1.1, jy - 2.15, BOARD["x1"], jy + 1.7), h_max=0.0,
                   note="E3 spring finger J11 (BW0036BG) under the E3 tab boss (face Z 2.45) [E]"))
    Z_.append(dict(name="J11_land", kind="part", geom=finger_courtyard(J11["land"]), h_max=J15_H, note="E3 finger J11 courtyard (parts.json) [S1 C-5]"))
    for x in POST_X:
        Z_.append(dict(name=f"post_foot_X{x:g}", kind="keepout", geom=sbox(x - 0.5, POST_FOOT[0], x + 0.5, POST_FOOT[1]), h_max=0.0,
                       note="stainless rib post 0.6 x 0.6 stands here (5 ATM load path) [B 5.1]"))
    for x, f in zip(RAIL_POST_X, rail_feet()):
        Z_.append(dict(name=f"rail_foot_X{x:g}", kind="keepout", geom=f, h_max=0.0,
                       note="GF-LCP window-rail post 0.5 x 0.4 stands here (5 ATM load path of the window glass) [S1 C-1]"))
    for (lx, ly) in support_legs():
        Z_.append(dict(name=f"support_leg_{lx:g}_{ly:g}", kind="keepout", geom=Point(lx, ly).buffer(0.6, quad_segs=16), h_max=0.0,
                       note="panel-support leg dia 0.8 [E, added by this lane]"))
    s = sw1_land()
    Z_.append(dict(name="SW1", kind="part", geom=bx(*s["courtyard"]), h_max=SW1["h"],
                   note="C&K PTS840 GK SMTR LFS side-actuated, 1.35 mm tall, actuator to +X at the board edge [DS PTS840 B-35]; courtyard 4.04 x 6.54 "
                        "of the reviewed C221907 land with pad 5 deleted (parts.json) [S1 C-4, D-9]"))
    mc = MOTOR_C
    if HAS_MOTOR:
        cut = motor_cut_poly()
        Z_.append(dict(name="motor_cutout", kind="cutout", geom=cut, h_max=None,
                       note=f"{MOTOR['cut_d']:g} mm board cut-out for the dia {MOTOR['d']:g} ERM ({MOTOR['part']})"
                            + (", opened to the far board edge (notch)" if MOTOR_NOTCH else "") + " [B 5.1; V3-G9 position]"))
        Z_.append(dict(name="motor_edge_keepout", kind="keepout", geom=cut.buffer(CUT_EDGE_CLR, quad_segs=32).difference(cut).intersection(bo),
                       h_max=0.0, note="0.3 mm copper / part clearance to the routed edge"))
        a17, b17 = sorted(cy("J17") or (2.9, 1.8))
        x17 = mc[0] + MOTOR["cut_d"] / 2 + 0.6
        g17 = bx(x17, mc[1] - b17 / 2, x17 + a17, mc[1] + b17 / 2)
        if S2D:   # [S2d K-1] no room on the hand side (board edge): the wire pads sit on the far (+Y) side of the cut-out
            y17 = mc[1] + MOTOR["cut_d"] / 2 + CUT_EDGE_CLR + 0.05
            g17 = bx(mc[0] - b17 / 2, y17, mc[0] + b17 / 2, y17 + a17)          # long side along X (the courtyard turned 90 deg)
        Z_.append(dict(name="J17_zone", kind="land", geom=g17, h_max=0.0,
                       note=f"motor wire pads (hand-fitted motor); courtyard {cy('J17')} (parts.json) beside the cut-out [E; S1 C-5]"))
    Z_.append(dict(name="antenna_keepout", kind="keepout_all_layers", geom=bx(ANT_KEEPOUT[0], ANT_KEEPOUT[2], ANT_KEEPOUT[1], ANT_KEEPOUT[3]),
                   h_max=0.0, note=("5 x 3 mm keep-out, all layers [B 7]; [S2c] = AE1 lid antenna L1 pocket (footprint AE1_lid_L1, board (0,0) rot 0): only AE1's FEED "
                                    "copper and J40 inside; clear volume up to the glass" if S2C else "5 x 3 mm chip-antenna keep-out, all layers [B 7]; antenna type still open (S1 C-16)")))
    if S2C:
        Z_.append(dict(name="J40_land", kind="part", geom=(J40["courtyard"] if S2E else J40["courtyard"].intersection(bo)), h_max=J40["h_free"],
                       note=(f"[S2d J-1] J40 {J40['part']} lid-antenna feed finger on AE1's FEED land (the C2826516 land), board {J40['land_board']} rot {J40['rot']:g}; "
                             + (f"[S2e N-5] zone = the land pattern's courtyard 4.0 x 2.0 (not clipped to the board); finger moved {J40_SHIFT} mm from {J40['land_board_s2d']} so the "
                                f"3.5 x 1.5 body lies inside the AE1 pocket; glass contact point case {J40['contact_case']}; " if S2E else "") +
                             f"free height {J40['h_free']:.2f} max (zone), working {J40['h_work']:.2f}, limit {J40['h_limit']:.2f}; compressed to the glass {Z.win0 - Z.pcb1:.3f} mm (max board) "
                             f"in the closed unit") if S2D else
                            f"[S2c] J40 BW0019BG lid-antenna feed finger (C2826516) on AE1's FEED land, board {J40['land_board']} rot {J40['rot']:g}; body courtyard "
                            f"(EasyEDA); free height 3.90 max, compressed to the glass {Z.win0 - Z.pcb1:.3f} mm (max board) in the closed unit"))
    Z_.append(dict(name="land_A", kind="land", geom=bx(LAND_A[0], LAND_A[2], LAND_A[1], LAND_A[3]), h_max=0.0,
                   note="root-A entry lands J3 / J4 / J5 / J10 = BATT_P | GND | NTC | GND, 1.0 x 4.0 pads at 1.5 mm, courtyards 4 x 1.5 x 4.5 [B 4, 5.1; S1 C-5]"))
    Z_.append(dict(name="land_B", kind="land", geom=bx(LAND_B[0], LAND_B[2], LAND_B[1], LAND_B[3]), h_max=0.0,
                   note="root-B entry lands J7 / J9 = PV_W+ | GND, courtyards 2 x 1.5 x 4.5 [B 5.1; S1 C-5]"))
    Z_.append(dict(name="D10", kind="part", geom=bx(D10["x0"], D10["y0"], D10["x1"], D10["y1"]), h_max=D10["h"],
                   note="skin-hot LED KA-2810ASURSK (right angle, 4.3 x 1.77 courtyard, 0.9 mm) at the radial board edge, lens toward -Y; "
                        "light turned up by a 45 deg PC face through a frame notch and a clear dot in the glass print (BASELINE 13.2 keeps "
                        "D10 until decision 5 (d) is accepted) [S1 C-6]"))
    Z_.append(dict(name="J6_land", kind="land", geom=bx(J6["x0"], J6["y0"], J6["x1"], J6["y1"]), h_max=0.0,
                   note="lid PV flex-tail land J6 (PV_NODE, GND, GND), hot-bar soldered at final assembly [S1 C-6]"))
    Z_.append(dict(name="lid_tail", kind="no_parts", geom=bx(LID_TAIL["x0"], LID_TAIL["y0"], LID_TAIL["x1"], LID_TAIL["y1"]), h_max=0.0,
                   note="the laminate flex tail drops from Z 2.65 to the board here (bend radius >= 0.5 mm) [S1 C-6]"))
    if S2D:   # [S2d K-3] PV half under the flat lid: general part height 1.20 mm (laminate underside Z %.3f; D14 1.15 legal)
        Z_.append(dict(name="pv_half_general", kind="height_limit", geom=bx(BOARD["x0"], RIB["y1"] + 0.2, BOARD["x1"], BOARD["y1"]), h_max=1.20,
                       note=f"[S2d K-3] PV half (Y >= 21.2 case): general part height 1.20 mm incl. solder (laminate underside Z {Z.pv0:.3f}, "
                            f"{Z.pv0 - Z.pcb1 - 0.15:.3f} mm free above the board with 0.15 clearance); lower zones (rib, E3 shelf) and part / land / keep-out zones take priority"))
    if S2B:
        Z_.extend(s2b_zones(Z_))
    return Z_


# ----------------------------------------------------------------------------------------------- [S2b] E-1 frame ground, T-5 U10 island
U10_ISLAND = (4.05, 23.55, 8.05, 27.55)        # [S2b T-5] 4 x 4 mm, over plate E1; X from 4.05 (K zone ends at X 4.0), so U10's centre moves
#   from the s13 placement's (5.53, 25.55) to (6.05, 25.55); Y unchanged (land A from Y 27.9, rib strip to Y 21.2)
FG_FACE_MARGIN = 0.10                          # [S2b E-1] frame tab face = finger courtyard + 0.10 (tip position unknown until the BW0036BG drawing is read)
FG_TAB_T = 0.25                                # frame sheet thickness: the tab is formed from the 0.25 mm stainless frame


def _fg_courtyard(lx, ly, rot):
    """BW0036BG courtyard (parts.json C2826535: 1.72 wide, -2.21 .. +1.45 along the finger) for rot 0 (finger along +Y, as J15), 90, 270"""
    a, b0, b1 = J15_CRT
    if rot == 0:
        return sbox(lx - a / 2, ly + b0, lx + a / 2, ly + b1)
    if rot == 90:
        return sbox(lx - b1, ly - a / 2, lx - b0, ly + a / 2)
    return sbox(lx + b0, ly - a / 2, lx + b1, ly + a / 2)


_FG = {}


def frame_gnd(zones=None):
    """[S2b E-1] GND contact of the stainless window frame at the E3 end: a BW0036BG spring finger (C2826535, the part of J11 / J15 / J18)
    on a GND pad, pressing up on a tab formed down from the frame (face at the finger's working height, Z = pcb1 + 1.00).
    Position: the legal land nearest to the E3 end (largest X of the tab face) on a 0.1 mm grid. Legal = courtyard inside the board
    (0.1 mm in); courtyard and face + 0.15 clear of every existing zone, of the rail, its posts and the max-material panel (+0.1); face inside
    the frame (0.1 in) and the cavity (0.15 in), and not under the E3 block shelf (X <= 37.9)."""
    if "r" in _FG:
        return _FG["r"]
    from shapely.prepared import prep
    if zones is None:
        zones = [z for z in board_zones() if not z["name"].startswith(("frame_gnd", "U10_"))]
    tol = PANEL_NOM["tol"]
    obst = unary_union([z["geom"] for z in zones] + [sbox(RAIL["x0"], RAIL["y0"], RAIL["x1"], RAIL["y1"]).buffer(0.1, join_style=2)] + rail_feet() +
                       [sbox(PANEL["x0"] - tol, PANEL["y0"] - tol, PANEL["x1"] + tol, PANEL["y1"] + tol).buffer(0.1, join_style=2)])
    po = prep(obst); pb = prep(board_outline().buffer(-0.1)); pf = prep(frame_outline().buffer(-0.1)); pc = prep(cavity().buffer(-0.15))
    best = None
    for ix in range(int(round(10 * (29.0 + DX))), int(round(10 * (38.1 + DX)))):   # [S2d] X 30.0-39.0 at 41 mm, follows the hand end
        lx = ix / 10.0
        for iy in range(15, 205):
            ly = iy / 10.0
            for rot in (0, 90, 270):
                c = _fg_courtyard(lx, ly, rot)
                if not pb.contains(c):
                    continue
                f = c.buffer(FG_FACE_MARGIN, join_style=2)
                if f.bounds[2] > E3_BLOCK["x0"] - 0.1 or not pf.contains(f) or not pc.contains(f):
                    continue
                if po.intersects(f.buffer(0.15, join_style=2).union(c)):
                    continue
                key = (round(f.bounds[2], 3), -abs(ly - 3.0), -rot)
                if best is None or key > best[0]:
                    best = (key, lx, ly, rot, c, f)
    if best is None:
        _FG["r"] = None
        return None
    _, lx, ly, rot, c, f = best
    _FG["r"] = dict(land=(lx, ly), rot=rot, courtyard=c, face=f, zone=f.buffer(0.15, join_style=2).union(c))
    return _FG["r"]


def s2b_zones(Z_):
    out = []
    fg = frame_gnd([z for z in Z_])
    if fg is not None:
        out.append(dict(name="frame_gnd_land", kind="part", geom=fg["courtyard"], h_max=J15_H,
                        note=f"[S2b E-1] GND spring finger for the stainless window frame (BW0036BG, C2826535, as J11 / J15 / J18; ref to be given by "
                             f"the schematic lane), land on a GND pad at case ({fg['land'][0]:g}, {fg['land'][1]:g}), finger turned {fg['rot']} deg "
                             f"(0 = along +Y as J15); courtyard 1.72 x 3.66 (parts.json); it presses on a tab formed down from the frame "
                             f"(face at Z {Z.finger_top:.2f}, working height 1.0 mm E)"))
        out.append(dict(name="frame_gnd_zone", kind="keepout_except", geom=fg["zone"].intersection(board_outline()), h_max=0.0,
                        note="[S2b E-1] under the frame's ground tab (tab face + 0.15): only the frame-ground finger"))
    out.append(dict(name="U10_island", kind="keepout_except", geom=sbox(*U10_ISLAND), h_max=0.0,
                    note=("[S2d K-6, R-5] 4 x 4 mm thermal-via island under U10 (TMP117): only U10 on it (centre (6.05, 25.55) case). The island is an ISOLATED "
                          "board-only copper net (not GND, not a plate net) on every layer with filled thermal vias; its B.Cu face stays under solder mask. "
                          "Thermal path to E1: the carrier film (no opening here) and a thermally conductive, electrically insulating bond. No copper touches a "
                          "plate; no other parts, no other nets' vias") if S2D else
                         ("[S2b T-5] 4 x 4 mm thermal-via island under U10 (TMP117): only U10 on it (centre (6.05, 25.55) case); filled thermal vias "
                          "through all layers to a B.Cu contact on plate E1 (skin zone U10_E1_contact); no other parts, no other nets' vias")))
    return out


def motor_cut_poly():
    """board cut-out for the motor: a hole of cut_d, or (notch) the same hole opened to the far board edge by a slot of the same width"""
    c = Point(*MOTOR_C).buffer(MOTOR["cut_d"] / 2, quad_segs=32)
    if MOTOR_NOTCH:
        c = c.union(sbox(MOTOR_C[0] - MOTOR["cut_d"] / 2, MOTOR_C[1], MOTOR_C[0] + MOTOR["cut_d"] / 2, BOARD["y1"] + 0.5))
    return c


def support_legs():
    i = SUPPORT_LEG_IN
    return [(PANEL["x0"] + i, PANEL["y0"] + i), (PANEL["x0"] + i, PANEL["y1"] - i), (PANEL["x1"] - i, PANEL["y0"] + i), (PANEL["x1"] - i, PANEL["y1"] - i)]


def skin_zones():
    """skin face (B.Cu) and floor items, case frame"""
    e1, e2 = plate_outlines()
    out = [dict(name="plate_E1", kind="void_BCu_In4Cu", geom=e1, note="Ti Gr2 0.25 plate E1 (elbow end); B.Cu and L5 void above it [B 18 V3-G1; P REDESIGN 5.5]"),
           dict(name="plate_E2", kind="void_BCu_In4Cu", geom=e2, note="Ti Gr2 0.25 plate E2 (hand end); B.Cu and L5 void above it"),
           dict(name="cap", kind="optics_BCu", geom=cap_poly(), note="optical cap 11 x 7 (PPG mesa, 0.80 proud): LEDs and PD on B.Cu [B 7]")]
    if HAS_MOTOR and MOTOR_ON_FILM:
        out.append(dict(name="motor_on_film_E2", kind="floor", geom=motor_cut_poly().intersection(board_outline()),
                        note="[S2d K-1] the carrier film (2 x 0.05 PI, R-1) stays under the motor over plate E2; the motor bonds to the film with a 0.05 mm PSA"))
    elif HAS_MOTOR:
        out.append(dict(name="carrier_cutaway_motor", kind="floor", geom=motor_cut_poly().intersection(board_outline()),
                        note="carrier film cut away under the motor; the motor bonds to the PC floor film with a 0.05 mm PSA [B 1]"))
    if S2D:
        out.append(dict(name="U10_E1_contact", kind="BCu_isolated_island_E1", geom=sbox(*U10_ISLAND).intersection(e1),
                        note="[S2d K-6, R-5] B.Cu face of the isolated U10 island, under solder mask (an allowed exception to the B.Cu void above E1: board-only "
                             "net); no film opening, no silver epoxy: the film plus a thermally conductive, electrically insulating bond couple it to E1"))
    elif S2B:
        out.append(dict(name="U10_E1_contact", kind="BCu_contact_E1", geom=sbox(*U10_ISLAND).intersection(e1),
                        note="[S2b T-5] B.Cu pad (ENIG) under the U10 via island, joined to plate E1 by a filled silver-epoxy contact (as the plate dots); "
                             "an exception to the B.Cu void above E1"))
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(summary(), indent=1, default=str))
