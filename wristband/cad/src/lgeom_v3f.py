"""V3-F main-board layout geometry in the style of layout/tools/lgeom.py, read from the CAD lane's board_zones JSON.

Board frame: mm, origin bottom-left, X 0..BOARD_W along the forearm (X = 0 elbow end = antenna end), Y 0..BOARD_H
(Y = 0 antenna / root-B edge), view from the SKY = F.Cu (parts side; JLC top). Case frame = board frame + (1.5, 1.5).
[G1] The 41 x 32 mm pod (board 38 x 29) is the base and the default. V3F_POD_L selects another plain outline file
(out/board_zones_L<L>.json); V3F_ZONES=<path> loads any zone file, e.g. out/options/board_zones_L41W33.json.
Pure python (no KiCad import).
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
_L = int(float(os.environ.get("V3F_POD_L", "41")))
SRC = os.environ.get("V3F_ZONES") or os.path.join(HERE, "..", "out", f"board_zones_L{_L}.json")
_D = json.load(open(SRC))

BOARD_W, BOARD_H = _D["board"]["W"], _D["board"]["H"]
CORNER_R = _D["board"]["corner_r"]
THICKNESS_MAX = _D["board"]["thickness_max"]
OUTLINE = [tuple(p) for p in _D["board"]["outline_board"]]
H_GENERAL = _D["meta"]["general_zone_h_max"]                       # 1.05 mm parts + solder
ZONES = {z["name"]: z for z in _D["zones"]}
SKIN = {z["name"]: z for z in _D["skin_face"]}
ANT_KEEPOUT = tuple(_D["antenna"]["keepout_board"])                 # (x0, y0, x1, y1), all layers
ANT_METAL_MIN = _D["antenna"]["metal_rule_mm"]
MOTOR_CENTER = tuple(_D["motor"]["centre_board"]); MOTOR_CUT_D = _D["motor"]["cutout_d"]     # cutout_d = 0: no motor (zone file of that option)
POST_FEET = [(x - 0.5, _D["rib_posts"]["foot_y_board"][0], x + 0.5, _D["rib_posts"]["foot_y_board"][1]) for x in _D["rib_posts"]["x_board"]]
J15_LANDS = [tuple(s["land_board"]) for s in _D["springs"]["J15"]]          # J15 (VBUS) and J18 (GND) fingers
J11_LAND = tuple(_D["springs"]["J11"]["land_board"])
LAND_A = tuple(_D["entry_lands"]["root_A"]["rect_board"]); LAND_B = tuple(_D["entry_lands"]["root_B"]["rect_board"])
CAP = tuple(SKIN["cap"]["rect_board"])
PLATE_E1 = [tuple(p) for p in SKIN["plate_E1"]["poly_board"][0]]; PLATE_E2 = [tuple(p) for p in SKIN["plate_E2"]["poly_board"][0]]
PLATE_VOID_LAYERS = ("B.Cu", "In4.Cu")


def outline():
    return list(OUTLINE)


def zone_polys(name):
    return [[tuple(p) for p in poly] for poly in ZONES[name]["poly_board"]]


def _inside(pt, poly):
    x, y = pt; c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


ZERO_KINDS = ("keepout", "keepout_all_layers", "cutout", "no_parts")


def height_limit_at(x, y, part=None):
    """part-height limit (mm above the board top, incl. solder) at board point (x, y); 0 = no parts.
    [S1 C-7] priority (the first version took the minimum over every zone starting from the general 1.05 mm, so no part zone could raise
    the limit and zones without h_max, e.g. the antenna keep-out, were skipped):
      1. motor cut-out, keep-out, all-layer antenna keep-out, cut-out and no_parts zones -> 0;
      2. a 'part' or 'land' zone gives its own h_max (that zone is reserved for its named part; if `part` is given, only a zone of that
         name counts; several part zones at one point -> the largest);
      3. inside a keepout_except zone and no part zone -> 0;
      4. the lowest height_limit zone;
      5. otherwise the general zone."""
    if MOTOR_CUT_D > 0 and math.hypot(x - MOTOR_CENTER[0], y - MOTOR_CENTER[1]) < MOTOR_CUT_D / 2:
        return 0.0
    hit = [z for z in ZONES.values() if any(_inside((x, y), [tuple(p) for p in poly]) for poly in z["poly_board"])]
    if any(z["kind"] in ZERO_KINDS for z in hit):
        return 0.0
    own = [z for z in hit if z["kind"] in ("part", "land") and (part is None or z["name"].split("_")[0] == part or z["name"] == part)]
    if own:
        return max(float(z["h_max_mm"] or 0.0) for z in own)
    if any(z["kind"] == "keepout_except" for z in hit) or any(z["kind"] in ("part", "land") for z in hit):
        return 0.0
    lim = [float(z["h_max_mm"]) for z in hit if z["kind"] == "height_limit" and z["h_max_mm"] is not None]
    return min(lim) if lim else H_GENERAL


def summary():
    return dict(board=(BOARD_W, BOARD_H), corner_r=CORNER_R, ant_keepout=ANT_KEEPOUT, motor=(MOTOR_CENTER, MOTOR_CUT_D),
                post_feet=POST_FEET, j15=J15_LANDS, j11=J11_LAND, land_a=LAND_A, land_b=LAND_B, cap=CAP,
                zones={k: (v["kind"], v["h_max_mm"], v["rect_board"]) for k, v in ZONES.items()})


if __name__ == "__main__":
    print(json.dumps(summary(), indent=1))
    for pt in ((10.0, 10.0), (25.0, 12.0), (18.0, 19.0), (5.0, 2.0)):
        print(pt, height_limit_at(*pt))
