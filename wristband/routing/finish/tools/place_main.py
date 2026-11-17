"""SolarBand V3-F main board: variant loader, anchors and placement rules for autoplace.py / legalize.py / check_placement.py.
Adapted from v2/layout/tools/place_main.py. Board frame (lgeom.py): mm, origin bottom-left, Y up, view from the sky (F.Cu).
Rotation = KiCad orientation in degrees (counter-clockwise seen from the top). Side from v3/design/parts.json (F = sky, B = skin).

Anchors are the parts whose position the pod fixes; they come from the CAD zone file [CAD]:
  J15 / J18 / J11 spring fingers (land_board), SW1 (zone SW1, actuator to +X), D10 (zone D10 at the radial edge),
  root lands J3 J4 J5 J10 (zone land_A) and J7 J9 (zone land_B), lid-tail land J6, display bridge land J13, front-light land J16,
  motor wire pads J17, plate dots E11 E12 E21 E22, the optics D3 PD1 D4 in the cap.
Level-0 lands (v3/g1/dense) are smaller than the stage-1 CAD zones: the level-0 courtyard is put at the tail-entry end of its CAD
zone and the rest of that zone is free for parts (option 'cadlands' keeps the whole zone reserved). [G1]
Anchors chosen by this lane [G1]: J8 (G10 pogo array, skin face) and the skin-face fiducials, AE1 (placeholder in the antenna keep-out).
Everything else on the sky side is placed by the annealer.
"""
import json, math, os
import lgeom as G

W = G.W


def load_variant():
    allv = json.load(open(G.DESIGN + "/parts.json"))["variants"]
    parts = json.loads(json.dumps(allv[G.VARIANT]["parts"]))
    fg = json.load(open(G.WORK + f"/fpgeom_{G.VARIANT}.json"))
    return parts, fg


PARTS, FPG = load_variant()
BB = 0.045                      # pcbnew courtyard bounding box - F.CrtYd centre line, per side (v2/gates/g1/PROGRESS.md; checked on 230 footprints)


def clbox(ref):
    """F.CrtYd centre-line box in the footprint's own KiCad frame (y down); parts without a courtyard keep the dumped pad box"""
    c = FPG[ref]["crt"]
    if PARTS[ref].get("courtyard_mm"):
        c = [c[0] + BB, c[1] + BB, c[2] - BB, c[3] - BB]
    c = list(c)
    if ref in ISLAND:                                   # [layout, LEAD_NOTES T-5] part-free thermal-via island centred on the part
        h = ISLAND[ref] / 2
        c = [min(c[0], -h), min(c[1], -h), max(c[2], h), max(c[3], h)]
    return c


ISLAND = {} if os.environ.get("G1_NO_ISLAND") else {"U10": 4.0}   # set G1_NO_ISLAND=1 once the zone file carries the island                                   # mm, square; U10 = TMP117: 4 x 4 mm thermal-via island to B.Cu (contact toward plate E1)


def need_h(ref):
    """height the zone must allow: body + solder; 0 for copper-only features; DNP lands take the part they are drawn for"""
    p = PARTS[ref]
    h = p.get("height_max_mm") or 0.0
    if p.get("dnp") and h == 0.0:
        fp = p["footprint"]
        h = 0.26 if fp.endswith("R0201") else 0.33 if fp.endswith("C0201") else 0.70 if "0402" in fp else 0.70
    if ref in H_OVR:                                    # [layout] placement-only override (G1_HOVR="REF:h,..."); check_placement runs without it
        h = H_OVR[ref]
    return (h + G.SOLDER) if h > 0 else 0.0


H_OVR = {k: float(v) for k, v in (e.split(":") for e in os.environ.get("G1_HOVR", "").split(",") if e)}


def pad_of(ref, net):
    for num, n in PARTS[ref]["pins"].items():
        if n == net:
            return num
    raise KeyError((ref, net))


# ------------------------------------------------------------------ anchors (ref: (x, y, rot))
def _rot(x, y, r):
    c, s = round(math.cos(math.radians(r))), round(math.sin(math.radians(r)))
    return x * c - y * s, x * s + y * c


def _box_at(ref, r):
    """centre-line courtyard box in the board frame (y up) for the footprint at the origin with rotation r"""
    k = clbox(ref)
    pts = [_rot(x, -y, r) for x in (k[0], k[2]) for y in (k[1], k[3])]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def fit(ref, rect, r, ax="c", ay="c"):
    """origin (x, y, r) that puts the centre-line courtyard of ref at rotation r inside rect; ax / ay: 'c' centre, 'lo' / 'hi' edge-aligned"""
    b = _box_at(ref, r)
    x = {"c": (rect[0] + rect[2]) / 2 - (b[0] + b[2]) / 2, "lo": rect[0] - b[0], "hi": rect[2] - b[2]}[ax]
    y = {"c": (rect[1] + rect[3]) / 2 - (b[1] + b[3]) / 2, "lo": rect[1] - b[1], "hi": rect[3] - b[3]}[ay]
    return (round(x, 4), round(y, 4), r)


Z = G.ZONES
cx, cy = G.PPG_CENTER
ANCHORS = {}
NOTES = {}
# ---- spring fingers: the land centre is the footprint origin; the finger body (local -x) points to -Y [CAD courtyard_board]
for s in G.D["springs"]["J15"]:
    ANCHORS[s["ref"]] = (s["land_board"][0], s["land_board"][1], 90)
ANCHORS["J11"] = (G.D["springs"]["J11"]["land_board"][0], G.D["springs"]["J11"]["land_board"][1], 90)
# ---- side button: actuator (local -x) toward +X; the CAD zone starts at the inboard courtyard edge [CAD button]
if "SW1" in PARTS and "SW1" in Z:
    ANCHORS["SW1"] = fit("SW1", Z["SW1"]["rect_board"], 180, ax="lo")
# ---- skin-hot LED at the radial edge (0 / 180 not decided here: same courtyard; the lens side is set from the Kingbright drawing at layout)
if "D10" in PARTS and "D10" in Z:
    ANCHORS["D10"] = fit("D10", Z["D10"]["rect_board"], 180, ay="lo")
# ---- root lands: 1.5 mm pitch along X, at the board-edge end of the CAD zone (the tail enters over the edge)
ra = Z["land_A"]["rect_board"]
for i, r in enumerate(("J3", "J4", "J5", "J10")):          # BATT_P | GND | NTC | GND [CAD entry_lands.root_A.order]
    if r in PARTS:
        ANCHORS[r] = fit(r, (ra[0] + 1.5 * i, ra[1], ra[0] + 1.5 * (i + 1), ra[3]), 0, ay="hi")
rb = Z["land_B"]["rect_board"]
for i, r in enumerate(("J7", "J9")):                        # PV_W+ | GND
    if r in PARTS:
        ANCHORS[r] = fit(r, (rb[0] + 1.5 * i, rb[1], rb[0] + 1.5 * (i + 1), rb[3]), 0, ay="lo")
# ---- lid tail land: pads stacked along Y as in the CAD zone (3.5 wide), at the tail-entry end (rib side)
if "J6" in PARTS and "J6_land" in Z:
    ANCHORS["J6"] = fit("J6", Z["J6_land"]["rect_board"], 90, ay="lo")
# ---- display land J13 (bridge flex of CAD option L1-A): at the FPC-tip side of its zone; for the stage-1 corridor file: centred
if "J13" in PARTS and "J13_land" in Z:
    jr = Z["J13_land"]["rect_board"]
    tall = (jr[3] - jr[1]) > (jr[2] - jr[0])
    ANCHORS["J13"] = fit("J13", jr, 90 if tall else 0, ax="hi" if tall else "c")
if "J16" in PARTS and "J16_land" in Z:
    ANCHORS["J16"] = fit("J16", Z["J16_land"]["rect_board"], 0)
if "J17" in PARTS and "J17_zone" in Z:
    _b = _box_at("J17", 0); _jr = Z["J17_zone"]["rect_board"]          # [S2d] orientation that matches the zone's aspect (zone 2.9 x 1.8 now)
    ANCHORS["J17"] = fit("J17", _jr, 0 if (_b[2] - _b[0] >= _b[3] - _b[1]) == (_jr[2] - _jr[0] >= _jr[3] - _jr[1]) else 90)
# ---- [S2b] frame-ground finger J19 on its land; U10 (TMP117) centred on its part-free thermal island (zone file)
if "J19" in PARTS and "frame_gnd_land" in Z:
    _b = _box_at("J19", 0); _jr = Z["frame_gnd_land"]["rect_board"]
    ANCHORS["J19"] = fit("J19", _jr, 0 if (_b[2] - _b[0] >= _b[3] - _b[1]) == (_jr[2] - _jr[0] >= _jr[3] - _jr[1]) else 90)
if "U10" in PARTS and "U10_island" in Z:
    ANCHORS["U10"] = fit("U10", Z["U10_island"]["rect_board"], 90)
# ---- skin face (B.Cu): optics under the cap, plate dots, G10 array, fiducials
ANCHORS.update({"D3": (cx - G.PPG_PITCH, cy, 0), "PD1": (cx, cy, 90), "D4": (cx + G.PPG_PITCH, cy, 0)})
ANCHORS.update({k: (x, y, 0) for k, (x, y) in G.DOTS.items()})
_e2x = G.PLATE_RECT["E2"][0]; _e1x = G.PLATE_RECT["E1"][2]
J8_POS = (round(_e2x - G.BARE_BCU_TO_PLATE - 3.5, 3), round(G.CAP[1] - 0.2 - 1.5, 3), 0)     # bare ENIG >= 2 mm from the plates, just outside the cap, under J13 / the FPC tail [G1]
ANCHORS["J8"] = J8_POS
ANCHORS["FID3"] = (_e1x + 1.6, G.BOARD_H - 2.2, 0); ANCHORS["FID4"] = (_e2x - 1.6, 1.9, 0)
# ---- antenna placeholder inside the keep-out, feed end toward the board [G1; antenna type open, S1 C-16]
ANCHORS["AE1"] = (0.0, 0.0, 0)                  # [LEAD_NOTES 2i L-1/L-2] lid antenna L1 feed footprint: board (0,0), rot 0, front
ANCHORS["J40"] = (3.68, 1.43, 340)              # [2i L-1, 2j J-1, S2e N-5] BW0020AG feed finger on AE1's spring land, moved (+0.38, -0.12)
# [2h A-2 / S2d] C215 (series, 9.0 nH) vertical between rail feet X3.5 [1.6-2.4] and X6 [4.1-4.9]: its antenna-side pad 2 at the bottom,
# 0.345 mm straight above the feed point (2.75, 3.00); 0.16 mm pad gap to AE1's GND pad. L204 (antenna-side shunt) beside it, above foot X6;
# C213 (chip-side shunt land, not fitted) is placed by the annealer next to C215 pad 1.
ANCHORS["C215"] = (3.04, 4.06, 270)
ANCHORS["L204"] = (4.20, 4.12, 90)              # [S2e N-5] foot X6.7 [4.8-5.6] frees the gap: L204 beside C215, ANT_FEED pad 1 at the bottom
# [S2e N-4, 2j J-2 / J-3] D15 (TPD1E10B06 on GND_K) right below the J18 land, outside K_zone and the U10 island, courtyard <= 1 mm from J18's;
# Q20 (CJBA7002K) right of it at rot 180: its large drain land (pad 2, GND_K) faces -X toward D15 / J18 (JLC zero = old part + 180)
ANCHORS["D15"] = (3.56, 21.45, 0)
ANCHORS["Q20"] = (5.65, 21.40, 180)
ANCHORS = {r: v for r, v in ANCHORS.items() if r in PARTS}
EXEMPT = set(ANCHORS)              # anchors sit in their own CAD zones by construction (checked against the zone file in check_placement.py)

# ------------------------------------------------------------------ per-part hard exclusions
WLCSP_PARTS = [r for r in ("U6", "U8", "U4", "U5") if r in PARTS]
# parts that need vias in their own land pattern (via-in-pad, centre pads of many-net packages) or carry many nets: never over a
# plate, where only GND vias and vias of nets behind >= 100 kOhm are allowed [D PLATE_VOID]
NO_PLATE = {r for r in ("U6", "U8", "U9", "U11", "X1") if r in PARTS}
NO_BSHADOW = {r for r in ("U6", "U8", "U9", "U11", "U12", "U13", "U17") if r in PARTS}     # not above skin-face pads (their vias would land in them)
ON_PLATE = {r for r in ("U10",) if r in PARTS}             # skin thermometer: thermal-via island down to B.Cu under a plate [D TMP117_ISLAND]
UFPC_REFS = {r for r in ("FID1", "FID2", "J12") if r in PARTS} if G.UFPC else set()        # copper-only, no part, no electrode net
# soft preferences
PLATE_OK = {r for r in PARTS if PARTS[r]["kind"] in ("pad1", "fid", "swd6")} | {"D5", "D6", "D7", "R301", "R303", "R305", "R306", "R318", "R319",
            "U10", "C504", "D13", "D14", "FB1", "FB2", "FB3", "FB4", "R116", "R149", "R170", "R171", "R172", "R174", "C174", "U19", "U20", "C170"}
PLATE_AVOID_W = float(os.environ.get("G1_PLATE_W", "12.0"))               # cost per mm2 of a part outside PLATE_OK lying over a plate (soft: the plates cover 43 % of the board)
HINT_W = 40.0
# floor plan of the tall blocks [G1]: the PV half (general zone, 1.05 mm) is the only place that takes U1 and U7 (4.8 / 5.3 mm courtyards).
# R-ECG-1 keeps L1 / L2 8 mm from the electrode dots (Y = 16) and from the ECG inputs, so: ECG front end on the elbow side of the motor
# cut-out, harvester on the hand side with its inductors along the far edge.
_mk = Z.get("motor_edge_keepout", {}).get("rect_board") or [G.BOARD_W / 2 - 4.6, 0, G.BOARD_W / 2 + 4.6, 0]
_ytop = max(z["rect_board"][3] for z in Z.values() if z["kind"] == "height_limit" and z["name"] == "rib_strip")
_kx = Z["K_zone"]["rect_board"][2] if "K_zone" in Z else 2.5
_ex = Z["e3_shelf_pv"]["rect_board"][0] if "e3_shelf_pv" in Z else G.BOARD_W - 1.8
# [S2d K-1] the motor now sits over plate E2 in the PV half (hand side): the PV half left of it, X K-zone .. motor keep-out, takes the tall blocks
_pvx = (_kx, _mk[0]) if _mk[0] - _kx > _ex - _mk[2] else (_mk[2], _ex)
_pvm = round(_pvx[0] + 0.45 * (_pvx[1] - _pvx[0]), 2)
PV_LEFT = (_pvx[0], _ytop, _pvm, G.BOARD_H - G.EDGE)
PV_RIGHT = (_pvm, _ytop, _pvx[1], G.BOARD_H - G.EDGE)
HINTS = {"U7": [PV_LEFT], "U15": [PV_LEFT], "U1": [(PV_RIGHT[0], PV_RIGHT[1], PV_RIGHT[2], G.BOARD_H - 3.4)],
         "L1": [(PV_RIGHT[0] + 1.5, G.BOARD_H - 4.2, PV_RIGHT[2], PV_RIGHT[3])], "L2": [(PV_RIGHT[0] + 1.5, G.BOARD_H - 4.2, PV_RIGHT[2], PV_RIGHT[3])]}
HINTS = {r: v for r, v in HINTS.items() if r in PARTS}
REGION = {}

# ------------------------------------------------------------------ proximity pairs: (part, ic, ic pad, weight)
def _pairs():
    Pp = []
    seen = set()
    def add(part, ic, net=None, w=6, pad=None):
        if part in PARTS and ic in PARTS:
            try:
                pd = pad if pad else pad_of(ic, net)
            except KeyError:
                return
            if pd not in {q["num"] for q in FPG[ic]["pads"]}:
                return
            Pp.append((part, ic, pd, w)); seen.add((part, ic))
    # radio
    for c, n, w in (("C204", "DEC1", 10), ("C206", "DEC2", 6), ("C207", "DEC3", 6), ("C210", "DEC4", 10), ("L203", "DEC4", 6),
                    ("L202", "DCC", 6), ("C201", "XC1", 6), ("C202", "XC2", 6), ("X1", "XC1", 5), ("X2", "XL1", 4),
                    ("C203", "RF_ANT", 14), ("L201", "RF_ANT", 14)):
        add(c, "U6", n, w)
    vdd = [k for k, v in PARTS["U6"]["pins"].items() if v == "VDD_1V8"]
    add("C205", "U6", pad=vdd[-1], w=6); add("C209", "U6", pad=vdd[0], w=8)
    add("C211", "X2", "XL1", 6); add("C212", "X2", "XL2", 6)
    add("C215", "L201", "RF_50R", 10); add("C213", "L201", "RF_50R", 6)
    add("L204", "AE1", "ANT_FEED", 10); add("C215", "AE1", "ANT_FEED", 4)
    # PPG
    add("C401", "U8", pad="D2", w=6); add("C402", "U8", pad="D2", w=4); add("C405", "U8", pad="C2", w=6)
    add("C404", "U8", "VLED", 6); add("C403", "U8", "PPG_VREF", 8); add("NT2", "U8", pad="C5", w=8)
    # ECG
    for c, pin, w in (("C313", "23", 6), ("C314", "23", 6), ("C311", "12", 6), ("C312", "12", 6), ("C305", "1", 8), ("C306", "7", 8),
                      ("C307", "9", 6), ("C308", "9", 6), ("C309", "11", 6), ("C310", "27", 6), ("C304", "28", 6), ("R317", "30", 6),
                      ("U3", "12", 3), ("R302", "4", 4), ("R304", "3", 4), ("C301", "4", 5), ("C302", "3", 5), ("C303", "4", 5),
                      ("R308", "4", 3), ("R309", "3", 3), ("R307", "28", 4)):
        add(c, "U7", pad=pin, w=w)
    add("C111", "U3", "VSTOR_SW", 6); add("C112", "U3", "AVDD_ECG", 6)
    # harvester
    for c, pin, w in (("C101", "2", 12), ("C102", "19", 12), ("C103", "19", 8), ("C106", "18", 10), ("C105", "14", 6),
                      ("C114", "14", 3), ("C115", "14", 3), ("C116", "14", 3), ("C117", "14", 3), ("NT1", "15", 8), ("C104", "4", 10),
                      ("L1", "20", 10), ("L2", "16", 10)):
        add(c, "U1", pad=pin, w=w)
    add("C107", "U4", "INA_VS", 6); add("C108", "U5", "INA_VS", 6)
    # electrodes: protection and first resistor at the dot / spring
    add("D5", "E11", "E1_PAD", 8); add("R301", "E11", "E1_PAD", 5); add("TP1", "E11", "E1_PAD", 3)
    add("R318", "E12", "E1_LINK", 5); add("TP2", "E12", "E1_LINK", 3)
    add("D7", "E21", "E2_PAD", 8); add("R305", "E21", "E2_PAD", 5); add("TP3", "E21", "E2_PAD", 3)
    add("R319", "E22", "E2_LINK", 5); add("TP4", "E22", "E2_LINK", 3)
    add("D6", "J11", "E3_PAD", 8); add("R303", "J11", "E3_PAD", 5); add("TP5", "J11", "E3_PAD", 3)
    # entries
    add("FB1", "J3", "BATT_P_A", 8); add("FB2", "J4", pad="1", w=8); add("FB3", "J5", pad="1", w=8); add("FB4", "J10", pad="1", w=8)
    add("FB5", "J7", pad="1", w=8); add("FB6", "J9", pad="1", w=8)
    add("D13", "J15", pad="1", w=10); add("D14", "J15", pad="1", w=6); add("D8", "J6", "PV_NODE", 6)
    add("D17", "J17", pad="1", w=6); add("Q12", "J17", pad="2", w=5); add("Q19", "Q12", pad="2", w=4)
    add("Q11", "J16", pad="2", w=5); add("R160", "J16", pad="1", w=4)
    add("R507", "D10", "ALERT_A", 4); add("Q6", "D10", "ALERT_K", 4)
    add("U17", "J13", pad="1", w=3); add("U21", "J13", pad="5", w=3); add("U16", "J13", pad="6", w=3)
    # automatic decoupling pairs: a capacitor with one pin on GND and the other on a net of exactly one IC -> next to that IC pin
    ics = {r for r, p in PARTS.items() if p["kind"] == "pinmap" and len(p["pins"]) >= 4}
    netpins = {}
    for r in ics:
        for num, n in PARTS[r]["pins"].items():
            if n and n not in ("GND",):
                netpins.setdefault(n, []).append((r, num))
    for r, p in PARTS.items():
        if p["kind"] != "C" or p.get("dnp"):
            continue
        ns = [n for n in p["pins"].values() if n]
        if len(ns) != 2 or "GND" not in ns:
            continue
        n = ns[0] if ns[1] == "GND" else ns[1]
        cand = netpins.get(n, [])
        if n in ("VDD_1V8",) or not cand:
            continue
        for ic in sorted({c[0] for c in cand}):
            if (r, ic) in seen or len({c[0] for c in cand}) > 2:
                continue
            add(r, ic, pad=[c[1] for c in cand if c[0] == ic][0], w=5)
    return Pp


PAIRS = _pairs()


def _crit():
    """critical proximity limits of this lane [G1]: (part, ic, ic pad, largest pad-to-pad distance in mm). The placer pulls hard on them and
    check_placement.py reports every pair beyond its limit (hard rule of the placement handed to routing)."""
    C = []
    def add(part, ic, pad=None, net=None, d=3.0):
        if part in PARTS and ic in PARTS:
            try:
                pd = pad if pad else pad_of(ic, net)
            except KeyError:
                return
            if pd in {q["num"] for q in FPG[ic]["pads"]}:
                C.append((part, ic, pd, d))
    # limits are pad-to-pad; they allow for the 1.0 mm JLC body spacing around QFN / BGA packages (0.6 mm between courtyards)
    for p, pad, d in (("L1", "20", 5.0), ("L2", "16", 5.0), ("C102", "19", 5.5), ("C106", "18", 5.5), ("C101", "2", 6.0), ("C104", "4", 4.5),
                      ("C105", "14", 5.5), ("NT1", "15", 5.0)):
        add(p, "U1", pad=pad, d=d)
    for p, net, d in (("C204", "DEC1", 4.0), ("C210", "DEC4", 4.0), ("C206", "DEC2", 4.5), ("C207", "DEC3", 4.5), ("C203", "RF_ANT", 3.5),
                      ("L201", "RF_ANT", 4.5), ("X1", "XC1", 5.0), ("X2", "XL1", 7.0), ("L202", "DCC", 7.0), ("L203", "DEC4", 5.0)):
        add(p, "U6", net=net, d=d)
    add("C401", "U8", pad="D2", d=4.0); add("C405", "U8", pad="C2", d=4.0); add("C403", "U8", net="PPG_VREF", d=4.0)
    for p, pad, d in (("C305", "1", 4.5), ("C306", "7", 4.5), ("C307", "9", 4.5), ("C309", "11", 4.5), ("C310", "27", 4.5), ("C311", "12", 4.5),
                      ("C313", "23", 4.5)):
        add(p, "U7", pad=pad, d=d)
    add("D13", "J15", pad="1", d=4.0); add("D5", "E11", pad="1", d=5.5); add("D7", "E21", pad="1", d=5.5); add("D6", "J11", pad="1", d=5.5)
    add("R301", "E11", pad="1", d=6.5); add("R305", "E21", pad="1", d=6.5); add("R303", "J11", pad="1", d=6.5)
    add("R318", "E12", pad="1", d=6.5); add("R319", "E22", pad="1", d=6.5)
    add("D17", "J17", pad="1", d=6.0); add("Q12", "J17", pad="2", d=6.0)
    for i, (fb, j) in enumerate((("FB1", "J3"), ("FB2", "J4"), ("FB3", "J5"), ("FB4", "J10"), ("FB5", "J7"), ("FB6", "J9"))):
        add(fb, j, pad="1", d=5.0)
    add("C130", "U15", net="VBUS", d=4.5); add("C131", "U15", pad="8", d=4.5); add("C504", "U10", net="VDD_1V8", d=4.5)
    add("C1501", "U16", pad="4", d=4.5); add("C1502", "U16", pad="1", d=5.0); add("C111", "U3", pad="4", d=4.5); add("C112", "U3", pad="1", d=4.5)   # [K-4] C1502 5.0 mm
    return C


CRIT = _crit()
CRIT_W = float(os.environ.get("G1_CRIT_W", "40.0"))
NET_W = {"ECG_INP": 2.0, "ECG_INN": 2.0, "E1_PAD": 3, "E2_PAD": 3, "E3_PAD": 3, "E1_LINK": 2, "E2_LINK": 2, "E1_MID": 2, "E2_MID": 2, "E3_MID": 2,
         "VREF_SAMP": 8, "LBOOST": 6, "LBUCK": 6, "XC1": 4, "XC2": 4, "XL1": 4, "XL2": 4, "DCC": 5, "DCDC_MID": 5, "DEC4": 5,
         "RF_ANT": 10, "RF_50R": 8, "ANT_FEED": 8,
         "PGA1P": 3, "PGA1N": 3, "PGA2P": 3, "PGA2N": 3, "ECG_VCAP1": 4, "ECG_VCAP2": 4, "ECG_VREFP": 4,
         "PV_NODE": 2, "PV_SW": 3, "PV_Q": 3, "PV_W": 2, "VIN_DC": 2, "VBAT_IC": 1.0, "BATT_P": 3, "BATT_P_A": 4, "GND_PMIC": 4, "VBAT_OV": 3,
         "OK_PROG": 3, "OK_HYST": 3, "VOUT_SET": 3, "VRDIV": 3, "BQ_EN": 3, "EN_HOLD": 3, "CYC_G": 3, "CYC_A": 3,
         "O2_G": 3, "O2_TC": 3, "O2_TH": 3, "VB_DET": 2, "BTN": 2, "BTN_SUP": 2, "BTN_N": 1.5, "NTC": 1.5, "NTC_A": 3, "ISET": 4, "ISET_RC": 4, "VSET": 3,
         "VBUS_K": 5, "VBUS": 4, "MOTOR_N": 3, "MOTOR_S": 3, "MOTOR_G": 2, "FL_A": 2, "FL_K": 3, "ALERT_A": 3, "ALERT_K": 3,
         "GND_A1": 4, "GND_A2": 4, "GND_B": 4,
         "D_SCLK": 2, "D_SI": 2, "D_SCS": 2, "D_EXTCOMIN": 2, "D_DISP": 2, "VDD_DISP": 1.0,
         "VLED": 0.5, "VSTOR": 0.7, "VSTOR_SW": 0.5, "SPI_SCK": 0.3, "SPI_MOSI": 0.3, "SPI_MISO": 0.3, "I2C_SDA": 0.3,
         "I2C_SCL": 0.3, "NTC_ADC": 0.5, "AVDD_ECG": 1.5, "INA_VS": 1.0, "PD1_IN": 4, "PD_GND": 2, "PPG_VREF": 3,
         "SWDIO": 0.1, "SWDCLK": 0.1, "NRESET": 0.1, "DISP_CTRL": 0.2, "LED1_DRV": 0.5, "LED2_DRV": 0.5}
SKIP_NETS = {"GND", "VDD_1V8"}

# ------------------------------------------------------------------ JLC recommended minimum spacing between SMD components [J]
# jlcpcb.com/help/article/minimum-spacing-for-smd-components ("Last updated on Sep 09, 2026"; cached 2026-11-12 in cache/v2/jlc_cap, re-read
# 2026-11-15): mm between adjacent components. The measurement drawing of the page is an image that could not be read, so the distance is
# taken between the part envelopes (pads + body) = F.CrtYd centre line shrunk by the courtyard margin of the footprint generator
# (0.15 mm chip passives, 0.25 mm other parts; v3/g1/dense/scripts/margin_whatif.py).
JLC_T = {("chip", "chip"): 0.18, ("chip", "sot"): 0.20, ("chip", "qfn"): 1.0, ("chip", "bga"): 1.0, ("sot", "sot"): 0.40, ("sot", "qfn"): 1.0,
         ("sot", "bga"): 1.0, ("qfn", "qfn"): 1.0, ("qfn", "bga"): 1.5, ("bga", "bga"): 2.0}
JLC_MODE = "full" if "jlc=full" in G.OPTS else "chip"       # chip: courtyard rule only (it already covers the chip / SOT rows); full: every row


def jclass(ref):
    """package class of the JLC spacing table; None = copper-only feature (no part)"""
    p = PARTS[ref]; fp = p["footprint"]; k = p["kind"]
    if k in ("pad1", "fid", "swd6", "tail2", "lidtail", "fpc10b", "nettie", "antenna", "testarray"):
        return None
    if k in ("R", "C", "L"):
        return "chip"
    if any(t in fp for t in ("WLCSP", "BGA")):
        return "bga"
    npad = len({q["num"] for q in FPG[ref]["pads"] if q["num"]})
    if npad >= 4 and k == "pinmap" and not any(t in fp for t in ("CRYSTAL", "SW-SMD", "SENSOR", "LED")):
        return "qfn"                                        # QFN / VQFN / WSON / USON / TDFN / UDFN / XQFN / SON / X2SON / LGA
    return "sot"                                            # DFN1006-3, SOD-523, X1SON-2, X2DFN-2, crystals, LEDs, switch, spring fingers


def margin(ref):
    return 0.15 if PARTS[ref]["kind"] in ("R", "C", "L") else 0.25


BASE_GAP = (2 * BB + 0.05) if G.GAPMODE == "v1" else 0.0     # centre-line gap of the courtyard rule (v1: bounding boxes 0.05 mm apart)


def pair_gap(a, b, mode=None):
    """required gap between the F.CrtYd centre-line boxes of a and b (mm)"""
    g = BASE_GAP
    if (mode or JLC_MODE) == "full":
        ca, cb = jclass(a), jclass(b)
        if ca and cb:
            t = JLC_T.get((ca, cb), JLC_T.get((cb, ca)))
            g = max(g, t - margin(a) - margin(b))
        elif "bga" in (ca, cb):                             # copper-only features (net ties, test pads, fiducials) stay out of the fan-out ring
            g = max(g, 0.35)
    if mode is None and (T2_SPREAD or T2_HALO):           # [track2 Q-5] placer-only spreading + escape halo (check_placement passes mode / no env)
        g += T2_SPREAD
        for ic, o in ((a, b), (b, a)):
            if ic in T2_HALO_ICS and o not in T2_OWN.get(ic, ()):
                g = max(g, T2_HALO)
    return g


# [track2 Q-5] G1_SPREAD (mm, extra centre-line gap for every pair), G1_HALO (mm, gap around the halo ICs except their own decoupling:
# capacitors sharing a non-GND net with the IC). Set them only for autoplace / refine; check_placement runs without them.
T2_SPREAD = float(os.environ.get("G1_SPREAD", "0") or 0)
T2_HALO = float(os.environ.get("G1_HALO", "0") or 0)
T2_HALO_ICS = [r for r in ("U7", "U1", "U6", "U15", "U17") if r in PARTS]


def _t2_own():
    def nets(r):
        return {n for n in (PARTS[r].get("pins") or {}).values() if n and n != "GND" and not str(n).startswith("NC")}
    own = {}
    for ic in T2_HALO_ICS:
        icn = nets(ic)
        own[ic] = {r for r in PARTS if r.startswith("C") and nets(r) & icn} | {pp for (pp, i2, _p, _d) in CRIT if i2 == ic}   # + critical-pair parts
    return own


T2_OWN = _t2_own()


# ------------------------------------------------------------------ R-ECG-1: aggressors >= 8 mm from the ECG inputs and electrode networks [D ECG_NOISE_DISTANCE]
SWITCHERS = [r for r in ("L1", "L2", "Q12", "Q19", "D17", "Q11", "U17", "U21") if r in PARTS]
FIXED_AGGR = [r for r in ("J17", "J16", "J13") if r in PARTS]          # fixed by the pod: movable ECG items keep 8 mm from them
E3_TIED = {"J11", "D6", "R303", "TP5"}                                   # sit at the E3 spring J11, which the pod puts 4.5 mm from J16: reported
ECG_ITEMS = [r for r in ("D5", "D6", "D7", "R301", "R302", "R303", "R304", "R305", "R306", "E11", "E12", "E21", "E22", "J11", "TP1", "TP2", "TP3",
                         "TP4", "TP5") if r in PARTS] + ([("U7", "3"), ("U7", "4")] if "U7" in PARTS else [])
ECG_MIN = G.ECG_MIN
