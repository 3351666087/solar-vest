"""SolarBand V3-F main-board layout geometry for the gate V3-G1 placement / fan-out / routing scripts (v3/layout/tools).
Adapted from v2/layout/tools/lgeom.py (V2-B). The geometry is NOT typed in here: it is read from the CAD lane's zone file
v3/cad/out/options/board_zones_<G1_ZONES>.json (outline, height-limit zones, keep-outs, no-part zones, motor cut-out, rib / rail post
feet, fixed lands, antenna keep-out, plates = B.Cu and L5 voids, optical cap, plate-dot pads). Pure python + numpy + shapely (no KiCad).

Board frame: mm, origin bottom-left, X along the forearm (X = 0 elbow end = antenna end), Y = 0 antenna / root-B edge, view from the
SKY = F.Cu (parts side; JLC "top"). Case frame = board frame + (1.5, 1.5).

Environment:
  G1_ZONES   tag of the CAD zone file (default L41_fpcdwg = CAD option L1-A, the first file with a solderable J13 joint)
  G1_VARIANT key of v3/design/parts.json "variants" (default v3f = level-0 dense schematic)
  G1_OPTS    comma list of placement options of THIS lane:
             gap=v1   courtyards = pcbnew bounding boxes (+0.045 mm per side) kept 0.05 mm apart (v1 / V2-B rule; default)
             gap=dru  courtyards = F.CrtYd centre-line boxes of parts.json, touching allowed (KiCad DRC 'courtyards_overlap' rule)
             ufpc     copper-only features without a part (FID1, FID2, SWD group J12) may lie under the display FPC return run
             cadlands the CAD 'part' / 'land' zones stay reserved at their stage-1 size (default: the level-0 courtyards are placed
                      inside them and the rest is free)
  G1_TAG     file-name tag of a run
Status tags: [CAD] zone file, [D] v3/design, [B] BASELINE.md, [J] JLC capability page (cache/v2/jlc_cap), [G1] choice of this lane.
"""
import json, math, os
import numpy as np
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely import contains_xy

W = "/path/to/SolarVest_work/wristband"
V3 = W + "/v3"
LANE = V3 + "/layout"
WORK = os.environ.get("G1_WORK", V3 + "/finish/work")   # [eco3] own footprint-geometry cache (SC70 U19 / U20); v3/layout/work untouched
DESIGN = os.environ.get("G1_DESIGN", V3 + "/design")                # [layout] override: G1_DESIGN
CADOPT = V3 + "/cad/out/options"

ZTAG = os.environ.get("G1_ZONES", "L41_fpcdwg")
VARIANT = os.environ.get("G1_VARIANT", "v3f")
OPTS = [o for o in os.environ.get("G1_OPTS", "").split(",") if o]
GAPMODE = "dru" if "gap=dru" in OPTS else "v1"
UFPC = "ufpc" in OPTS
CADLANDS = "cadlands" in OPTS
TAG = os.environ.get("G1_TAG", f"{VARIANT}_{ZTAG}")
ZFILE = os.environ.get("G1_ZFILE") or os.path.join(CADOPT, f"board_zones_{ZTAG}.json")   # [layout] override: G1_ZFILE
D = json.load(open(ZFILE))

# ---------------------------------------------------------------------------------------- outline
BOARD_W, BOARD_H = D["board"]["W"], D["board"]["H"]
CORNER_R = D["board"]["corner_r"]
THICKNESS = 1.04                                              # JLC06101H-3313 compression thickness [J stack json]
OUTLINE = [tuple(p) for p in D["board"]["outline_board"]]
BOARD = Polygon(OUTLINE).buffer(0)
KICAD_ORIGIN = (100.0, 130.0)                                 # board (0,0) in KiCad page coordinates; KiCad Y is down
EDGE = 0.5                                                    # courtyard to the board edge = the 0.5 mm edge band of the gate-1 metric [B 5.3; CAD 'inner']
CU_EDGE = 0.3                                                 # copper to any routed edge: JLC minimum 0.2 [J] + 0.1 [v1]
INNER = BOARD.buffer(-EDGE)
H_GENERAL = float(D["meta"]["general_zone_h_max"])            # 1.05 mm (part + solder) [CAD]
SOLDER = 0.05                                                 # solder under a part: zone h_max = body + 0.05 [CAD zone notes]

# JLC06101H-3313 (default 6-layer 1.0 mm, 1 oz outer / 0.5 oz inner) [J: cache/v2/jlc_cap/stack_6L_1p0_1oz_0p5oz.json]
STACK = [("F.Cu", "copper", 0.035, None), ("PP1", "prepreg 3313", 0.0994, 4.1),
         ("In1.Cu", "copper", 0.0152, None), ("Core1", "core", 0.25, 4.6),
         ("In2.Cu", "copper", 0.0152, None), ("PP2", "prepreg 7628", 0.2104, 4.4),
         ("In3.Cu", "copper", 0.0152, None), ("Core2", "core", 0.25, 4.6),
         ("In4.Cu", "copper", 0.0152, None), ("PP3", "prepreg 3313", 0.0994, 4.1),
         ("B.Cu", "copper", 0.035, None)]
LAYER_USE = {"F.Cu": "L1 parts + signals (sky)", "In1.Cu": "L2 GND plane", "In2.Cu": "L3 signals",
             "In3.Cu": "L4 GND plane", "In4.Cu": "L5 signals / supply, void under the plates",
             "B.Cu": "L6 skin face: D3, D4, PD1, dot pads, G10 array; void under the plates"}
JLC = dict(track=0.09, space=0.09, via_hole=0.15, via_pad=0.25, via_hole_pref=0.20, via_pad_pref=0.40,
           hole_to_hole=0.20, hole_to_track=0.20, inner_hole_to_copper=0.20, bga_pad_min=0.20, bga_pad_to_trace=0.09,
           mask_bridge=0.10, mask_bridge_black=0.13, smd_pad_gap=0.15, cu_to_edge=0.20, outline_tol=0.20,
           pofv_via=(0.15, 0.55))

# ---------------------------------------------------------------------------------------- zones [CAD]
ZONES = {z["name"]: z for z in D["zones"]}
SKIN = {z["name"]: z for z in D["skin_face"]}


def zpoly(z):
    ps = [Polygon(p).buffer(0) for p in z["poly_board"] if len(p) >= 3]
    return unary_union(ps) if ps else Polygon()


ZP = {n: zpoly(z) for n, z in ZONES.items()}
ZERO_KINDS = ("keepout", "keepout_all_layers", "cutout", "no_parts", "keepout_except")
FPC_RUN = [n for n, z in ZONES.items() if z["kind"] == "no_parts" and n in ("fpc_tail", "fpc_wide", "fpc_corridor")]   # the return run lying on the board
MOTOR_CENTER = tuple(D["motor"]["centre_board"]); MOTOR_CUT_D = float(D["motor"]["cutout_d"])
MOTOR_CUT = ZP.get("motor_cutout", Polygon())
ANT_KEEPOUT = tuple(D["antenna"]["keepout_board"])            # (x0, y0, x1, y1), all layers [CAD; B 7: 5 x 3 mm chip-antenna keep-out]
ANT_METAL_MIN = D["antenna"]["metal_rule_mm"]
CAP = tuple(SKIN["cap"]["rect_board"])                        # optical cap on the skin face
CAP_POLY = zpoly(SKIN["cap"])
PPG_CENTER = ((CAP[0] + CAP[2]) / 2, (CAP[1] + CAP[3]) / 2)
PPG_PITCH = 3.25                                              # LED - PD - LED along X [v2 G1]
PLATES = {"E1": zpoly(SKIN["plate_E1"]), "E2": zpoly(SKIN["plate_E2"])}
PLATE_RECT = {"E1": tuple(SKIN["plate_E1"]["rect_board"]), "E2": tuple(SKIN["plate_E2"]["rect_board"])}
PLATE_U = unary_union(list(PLATES.values()))
PLATE_VOID_LAYERS = ("B.Cu", "In4.Cu")
_CO = D["board"].get("case_origin", [0.0, 0.0])                # [S2d] plate_dot_pads are in CASE coordinates: board = case - case_origin
DOTS = {d["name"]: (round(d["centre"][0] - _CO[0], 4), round(d["centre"][1] - _CO[1], 4)) for d in D["plate_dot_pads"]}
DOT_VIA_MIN = 1.0                                             # vias >= 1 mm from a dot opening [D PLATE_VOID]
BARE_BCU_TO_PLATE = 2.0                                       # J8 / mask-free B.Cu >= 2 mm from plate edges and dots [D PLATE_VOID]
POST_FEET = [tuple(ZONES[n]["rect_board"]) for n in ZONES if n.startswith("post_foot")]
RAIL_FEET = [tuple(ZONES[n]["rect_board"]) for n in ZONES if n.startswith("rail_foot")]
ECG_MIN = 8.0                                                 # [D ECG_NOISE_DISTANCE]
H_LEVELS_NOTE = "zone h_max = part body height + 0.05 mm solder [CAD]"

# ---------------------------------------------------------------------------------------- rasters for the placer
RES = 0.05
NX = int(round((BOARD_W + 2.0) / RES)); NY = int(round((BOARD_H + 2.0) / RES)); X0 = -1.0; Y0 = -1.0     # grid covers -1 .. W+1


def _allowed_all_corners(poly):
    """boolean [NY, NX]: cell fully inside poly (all four corner nodes inside or on the boundary)"""
    xs = X0 + RES * np.arange(NX + 1); ys = Y0 + RES * np.arange(NY + 1)
    XX, YY = np.meshgrid(xs, ys)
    inn = contains_xy(poly.buffer(1e-7), XX, YY)
    return inn[:-1, :-1] & inn[1:, :-1] & inn[:-1, 1:] & inn[1:, 1:]


def _touched(poly):
    """boolean [NY, NX]: cell touched by poly (conservative: poly grown by one cell diagonal, tested at the cell centre)"""
    xs = X0 + RES * (np.arange(NX) + 0.5); ys = Y0 + RES * (np.arange(NY) + 0.5)
    XX, YY = np.meshgrid(xs, ys)
    return contains_xy(poly.buffer(RES * 0.7072 - 1e-7), XX, YY)


def limit_raster(ufpc=False):
    """height limit of every cell for a MOVABLE part: -1 = no courtyard at all; 0 = copper-only features without a part (ufpc);
    else the lowest height_limit zone, else the general zone [CAD priority rule; conservative on every boundary]"""
    lim = np.full((NY, NX), H_GENERAL)
    for n, z in ZONES.items():                          # [S2d K-3] a height_limit zone above the general limit raises it inside the zone (PV half 1.20)
        if z["kind"] == "height_limit" and float(z["h_max_mm"] or 0) > H_GENERAL:
            m = _touched(ZP[n].buffer(-RES * 1.4143))
            lim[m] = np.maximum(lim[m], float(z["h_max_mm"]))
    for n, z in sorted(ZONES.items(), key=lambda kv: -(kv[1]["h_max_mm"] or 0)):
        if z["kind"] == "height_limit":
            m = _touched(ZP[n])
            lim[m] = np.minimum(lim[m], float(z["h_max_mm"]))
    lim[~_allowed_all_corners(INNER)] = -1.0
    for n, z in ZONES.items():
        if z["kind"] in ZERO_KINDS:
            if ufpc and n in FPC_RUN:
                continue
            lim[_touched(ZP[n])] = -1.0
        elif z["kind"] in ("part", "land") and CADLANDS:
            lim[_touched(ZP[n])] = -1.0
    if ufpc:
        run = unary_union([ZP[n] for n in FPC_RUN])
        other = unary_union([ZP[n] for n, z in ZONES.items() if z["kind"] in ZERO_KINDS and n not in FPC_RUN] + [BOARD.difference(INNER)])
        m = _touched(run) & ~_touched(other) & (lim > -1.0)
        lim[m] = 0.0
    return lim


def integral(mask):
    s = np.zeros((NY + 1, NX + 1))
    s[1:, 1:] = np.cumsum(np.cumsum(mask.astype(np.float64), axis=0), axis=1)
    return s


def rect_count(S, r):
    """number of raster cells TOUCHED by rect r = (x0, y0, x1, y1) that are set in the mask of integral image S"""
    i0 = max(0, min(NX, int(math.floor((r[0] - X0) / RES + 1e-6)))); i1 = max(0, min(NX, int(math.ceil((r[2] - X0) / RES - 1e-6))))
    j0 = max(0, min(NY, int(math.floor((r[1] - Y0) / RES + 1e-6)))); j1 = max(0, min(NY, int(math.ceil((r[3] - Y0) / RES - 1e-6))))
    if i1 <= i0 or j1 <= j0:
        return 0.0
    return S[j1, i1] - S[j0, i1] - S[j1, i0] + S[j0, i0]


def outline():
    return list(OUTLINE)


def poly_area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


# ---------------------------------------------------------------------------------------- free area by height class (as v3/cad/src/options_table.py areas())
def cad_areas(fixed_mm2):
    """the CAD lane's area method on this zone file; fixed_mm2 = the schematic's fixed features (area_check.py convention) for the
    stage-1 placement convention.  -> dict"""
    Z = ZONES
    fixed = unary_union([ZP[n] for n, z in Z.items() if z["kind"] in ("land", "part")])
    dead = unary_union([ZP[n] for n, z in Z.items() if z["kind"] in ZERO_KINDS])
    free = INNER.difference(fixed).difference(dead)
    hz = sorted([n for n, z in Z.items() if z["kind"] == "height_limit"], key=lambda n: Z[n]["h_max_mm"])
    cls, taken = {}, Polygon()
    for n in hz:
        g = ZP[n].difference(taken).intersection(free)
        k = f"{Z[n]['h_max_mm']:.3f}".rstrip("0").rstrip(".")
        cls[k] = round(cls.get(k, 0.0) + g.area, 1)
        taken = taken.union(ZP[n])
    cls[f"{H_GENERAL:g}"] = round(free.difference(taken).area, 1)
    feat = [n for n, z in Z.items() if z["kind"] == "no_parts" or n.startswith(("support_leg", "rail_foot"))]
    counted = unary_union([ZP[n] for n in Z if Z[n]["kind"] in ("land", "part", "cutout", "keepout_all_layers") or n.startswith("post_foot") or n == "motor_edge_keepout"])
    feats = unary_union([ZP[n] for n in feat])
    kz = ZP["K_zone"].difference(unary_union([ZP["J15_land"], ZP["J18_land"]])) if "K_zone" in ZP else Polygon()
    jz = ZP["J11_zone"].difference(ZP["J11_land"]) if "J11_zone" in ZP else Polygon()
    cad_only = unary_union([feats, kz, jz]).difference(counted).intersection(INNER)
    X, Y, R = BOARD_W, BOARD_H, 4.5
    cut = 0.0
    if "motor_cutout" in Z and MOTOR_CUT_D > 0:
        d = MOTOR_CUT_D
        cut = (math.pi * d * d / 4 + 0.3 * math.pi * d) if not D["motor"].get("notch") else unary_union([ZP["motor_cutout"], ZP["motor_edge_keepout"]]).intersection(INNER).area
    conv = (X * Y - (4 - math.pi) * R * R) - 0.5 * 2 * (X + Y) - 15.0 - fixed_mm2 - cut - 6.0
    unusable = round(sum(v for k, v in cls.items() if float(k) < 0.31), 1)
    return dict(inner_mm2=round(INNER.area, 1), cad_fixed_zones_mm2=round(fixed.intersection(INNER).area, 1),
                dead_zones_mm2=round(dead.difference(fixed).intersection(INNER).area, 1), free_mm2=round(free.area, 1), free_by_h_max_mm2=cls,
                cad_only_mm2=round(cad_only.area + unusable, 1), motor_cut_mm2=round(cut, 1), fixed_features_mm2=round(fixed_mm2, 1),
                placement_stage1_convention_mm2=round(conv - cad_only.area - unusable, 1))


def summary():
    return dict(zones=ZTAG, variant=VARIANT, opts=OPTS, board=(BOARD_W, BOARD_H), board_mm2=round(BOARD.area, 1), inner_mm2=round(INNER.area, 1),
                ant_keepout=ANT_KEEPOUT, motor=(MOTOR_CENTER, MOTOR_CUT_D), cap=CAP, plates=PLATE_RECT, dots=DOTS,
                zones_n=len(ZONES), fpc_run=FPC_RUN)


if __name__ == "__main__":
    print(json.dumps(summary(), indent=1))
    lim = limit_raster()
    vals, cnt = np.unique(lim, return_counts=True)
    print("limit raster (movable parts):", {float(v): round(float(c) * RES * RES, 1) for v, c in zip(vals, cnt)})
    print(json.dumps(cad_areas(80.0), indent=1))
