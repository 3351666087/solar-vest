"""Complete wiring of the worn system: every cable with its connectors, conductors (pin-to-pin), route and length,
plus the devices that are not part of the solar chain (A, C, ECG sensor, electrodes, PulseSensor, thermocouples, phone).

used by assembly.py:  build_harness(add, F)  ->  adds meshes, returns the wire list
writes (when run):    out/harness.json  (wire list with lengths)
"""
import json, os, sys, numpy as np, trimesh
HERE = os.path.dirname(os.path.abspath(__file__)); VEST = os.path.join(HERE, "..", "vest")
sys.path.insert(0, VEST)
import enclosures as E
SL = json.load(open(os.path.join(VEST, "system_layout.json"))); PL = json.load(open(os.path.join(VEST, "placement.json")))
WS = os.path.abspath(os.path.join(HERE, "..", ".."))                     # repository root

def rgba(h, a=255): h = h.lstrip("#"); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)] + [a], np.uint8)
def colored(m, c): m = m.copy(); m.visual = trimesh.visual.ColorVisuals(m, face_colors=np.tile(c, (len(m.faces), 1))); return m
C = dict(red=rgba("c62828"), black=rgba("1a1a1a"), blue=rgba("1e5bb8"), white=rgba("eeeeea"), yellow=rgba("e0b400"), green=rgba("2e8b3a"),
         grey=rgba("6b7078"), jacket=rgba("202224"), ph=rgba("f4f1e6"), uce6=rgba("f2f2f2"), metal=rgba("b9bdc3"), kplug=rgba("f2c200"),
         purple=rgba("7b3fa0"), brown=rgba("6b4423"), pcb=rgba("f3f0e4"), board=rgba("e9e4d2"), elec=rgba("d8e2ea"), ecg=rgba("b3261e"),
         phone=rgba("15171a"), case=rgba("d5d9de"))

def smooth(P, n_out=None):
    P = np.asarray(P, float); keep = np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-5]; P = P[keep]
    if len(P) < 3: return P
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    from scipy.interpolate import PchipInterpolator
    s = np.linspace(0, d[-1], n_out or max(20, int(d[-1] / 0.004)))
    return np.c_[[PchipInterpolator(d, P[:, k])(s) for k in range(3)]].T
def plen(P): P = np.asarray(P); return float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))
def tube(P, r, sections=10):
    from vest3d import tube as vt
    return vt(np.asarray(P), r, sections)
def oriented_box(size, center, z_dir, up_hint=(0, 1, 0)):
    z = np.asarray(z_dir, float); z /= np.linalg.norm(z); x = np.cross(up_hint, z)
    if np.linalg.norm(x) < 1e-6: x = np.cross((1, 0, 0), z)
    x /= np.linalg.norm(x); y = np.cross(z, x)
    b = trimesh.creation.box(size); M = np.eye(4); M[:3, :3] = np.c_[x, y, z]; M[:3, 3] = center; b.apply_transform(M); return b
def oriented_cyl(r, h, center, z_dir):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=20); z = np.asarray(z_dir, float); z /= np.linalg.norm(z)
    a = np.cross([0, 0, 1], z); M = np.eye(4)
    if np.linalg.norm(a) > 1e-9: M = trimesh.transformations.rotation_matrix(np.arccos(np.clip(z[2], -1, 1)), a)
    M[:3, 3] = center; c.apply_transform(M); return c

# connector bodies (m): (size, colour) ; local +z = pointing INTO the mating socket
CONN = {"PHR-2": ((0.0060, 0.0045, 0.0060), "ph"), "PHR-5": ((0.0120, 0.0045, 0.0060), "ph"),
        "UC-E6": ((0.0110, 0.0065, 0.0180), "uce6"), "K-mini": ((0.0160, 0.0080, 0.0300), "kplug"),
        "WP-2P": ((0.0140, 0.0140, 0.0440), "jacket"), "ferrule": ((0.0018, 0.0018, 0.0080), "metal"),
        "snap": ((0.0110, 0.0110, 0.0060), None), "Y": ((0.0080, 0.0080, 0.0200), "uce6")}

def frame_from_pose(pose, scale=0.001, origin_offset=(0, 0, 0)):
    o, n, u, r = (np.array(pose[k], float) for k in ("origin", "normal", "up", "right"))
    M = np.eye(4); M[:3, 0], M[:3, 1], M[:3, 2] = r * scale, u * scale, n * scale; M[:3, 3] = o
    T = np.eye(4); T[:3, 3] = origin_offset; return M @ T
def at(M, p): return (M @ np.r_[p, 1.0])[:3]
def dir_(M, v): return (M[:3, :3] @ np.asarray(v, float)) / np.linalg.norm(M[:3, :3] @ np.asarray(v, float))

def build_harness(add, F):
    """F: dict of frames from assembly.py (M_S, M_BACKPOD, M_CHESTPOD, M_REF2). Returns wire list."""
    M_S, M_BP, M_CP = F["M_S"], F["M_BACKPOD"], F["M_CHESTPOD"]
    M_C = frame_from_pose(SL["C_board"], origin_offset=(-54.0, -33.6, 2.0))          # C case CAD -> body (case X -> wearer's left)
    gA = trimesh.load(os.path.join(WS, "modeling", "heartbit-kit-models", "heartbit_main_unit.glb"), force="scene")
    wires = []
    def connector(kind, end_pt, into_dir, name, group="cables", colour=None):
        size, col = CONN[kind]; centre = np.asarray(end_pt) - np.asarray(into_dir) / np.linalg.norm(into_dir) * size[2] / 2
        add(colored(oriented_box(size, centre, into_dir), C[colour or col]), name, group)
        if kind == "UC-E6":                                                             # metal tongue
            add(colored(oriented_box((0.0075, 0.0035, 0.005), np.asarray(end_pt) + np.asarray(into_dir) / np.linalg.norm(into_dir) * 0.0025, into_dir), C["metal"]), name + "_tongue", group)
    def wire(wid, name, P, r, colour, ends, conductors, source, route_note, group="cables", smooth_it=True):
        P = smooth(P) if smooth_it else np.asarray(P)
        add(colored(tube(P, r), C[colour]), f"{wid}_{name}", group)
        L = plen(P)
        for k, (kind, pt, d) in enumerate(ends):
            if kind: connector(kind, pt, d, f"{wid}_conn{k}", group, colour if kind == "snap" else None)
        wires.append(dict(id=wid, name=name, length_mm=round(L * 1000), cut_mm=int(np.ceil((L * 1000 + 80) / 50) * 50),
                          od_mm=round(2 * r * 1000, 1), ends=[e[0] for e in ends], conductors=conductors, source=source, route=route_note))
        return P

    # ===================================================== back unit ===============================================
    # W01 panel lead: junction box (panel back) -> waterproof 2P plug -> back pod PANEL notch -> J1 screw terminal
    jb = at(M_S, (-78.5, 0.0, 2.0)); notch = at(M_BP, (E.IX0 - 6.0, -7.5, 9.5)); j1 = at(M_BP, (0.8, -7.5, 9.0))
    P = [jb] + PL["cables"]["panel"][1:] + [notch, at(M_BP, (-4.0, -7.5, 9.5)), j1]
    P = wire("W01", "panel_lead", P, 0.0025, "jacket", [(None, None, None), ("ferrule", j1, dir_(M_BP, (1, 0, 0)))],
             [("+ red", "Panel junction box +", "PMB-H J1-1 PV_IN+"), ("− blue", "Panel junction box −", "PMB-H J1-2 PV_IN−")],
             "Original panel lead (measured from photo: junction box → waterproof connector ≈ 4.2 m, of which the coil ≈ 3.8 m; connector → stripped end 0.41 m + 7–8 cm of bare cores; OD 4.1 mm). Cut the panel side at 200 mm and solder it to the 100 mm tail left on the connector side (2 joints + heat-shrink); cut the other side of the connector to 200 mm, strip and clamp into the terminal", "Panel back → channel T1 → back pod PANEL port (secured with a cable-tie bridge)")
    k = len(P) // 3; add(colored(oriented_box(CONN["WP-2P"][0], P[k], P[k + 1] - P[k - 1]), C["jacket"]), "W01_waterproof_2P", "cables")
    # W02 battery leads (LiPo PCM end -> J2), W03 NTC (battery surface -> J3)
    z = E.Z_BRD + 1.6 + 2.3
    wire("W02", "battery", [at(M_BP, (10.0, -98.6, 5.0)), at(M_BP, (8.0, -74.0, 8.5)), at(M_BP, (20.0, -68.0, 8.0)), at(M_BP, (30.0, -66.0, z)), at(M_BP, (30.0, -64.9, z))],
         0.0012, "red", [(None, None, None), ("PHR-2", at(M_BP, (30.0, -58.9, z)), dir_(M_BP, (0, 1, 0)))],
         [("red", "Battery + (after PCM)", "J2-1 BAT+"), ("black", "Battery −", "J2-2 GND")], "Battery's own PH2.0 plug (⚠ red wire to J2 silkscreen +)", "Inside pod: battery left end → over the divider → J2")
    wire("W03", "ntc", [at(M_BP, (55.0, -96.0, 11.0)), at(M_BP, (50.0, -74.0, 9.0)), at(M_BP, (42.0, -66.0, z)), at(M_BP, (42.0, -64.9, z))],
         0.0009, "black", [(None, None, None), ("PHR-2", at(M_BP, (42.0, -58.9, z)), dir_(M_BP, (0, 1, 0)))],
         [("—", "NTC 10 kΩ (non-polarised)", "J3-1 NTC_ADC"), ("—", "NTC", "J3-2 GND")], "Ready-made NTC 10k B3950 with PH2.0 lead (purchased)", "NTC taped to the middle of the battery with high-temperature tape")
    # W04/W05 reference cells -> J7/J8
    ref1 = at(M_S, (-E.L_P / 2 - 26.0, 0.0, 9.0))
    wire("W04", "ref1", [ref1] + PL["cables"]["ref1"] + [at(M_BP, (E.IX0 - 6.0, -40.2, 8.1)), at(M_BP, (-5.0, -40.2, z))],
         0.0012, "yellow", [(None, None, None), ("PHR-2", at(M_BP, (1.0, -40.2, z)), dir_(M_BP, (1, 0, 0)))],
         [("red", "REF1 cell +", "J7-1 REF1+"), ("black", "REF1 cell −", "J7-2 GND")], "Panel-lead offcut (2-core Ø4.1) 0.45 m + 1 × BOM \"PH2mm straight-pin pre-wired\" plug, 2 solder joints + heat-shrink", "REF1 clip → panel left edge → channel T2 → REF1 port")
    wire("W05", "ref2", [np.array(PL["ref2"]["origin"])] + PL["cables"]["ref2"] + [at(M_BP, (E.IX0 - 6.0, -49.6, 8.1)), at(M_BP, (-5.0, -49.6, z))],
         0.0012, "yellow", [(None, None, None), ("PHR-2", at(M_BP, (1.0, -49.6, z)), dir_(M_BP, (1, 0, 0)))],
         [("red", "REF2 cell +", "J8-1 REF2+"), ("black", "REF2 cell −", "J8-2 GND")], "Panel-lead offcut 0.6 m + 1 × PH2 plug, 2 solder joints + heat-shrink", "Left-shoulder REF2 → back yoke → channel T3 → REF2 port")
    # ===================================================== back -> chest ===========================================
    j6 = at(M_BP, (58.0, -58.9, z)); lib_j1 = at(M_CP, (2.8, -28.0, E.ZLIB + 1.6 + 2.3))
    P = [at(M_BP, (58.0, -64.9, z)), at(M_BP, (72.0, -66.0, 8.0)), at(M_BP, (E.IX1 + 6.0, -65.0, 8.0))] + PL["cables"]["J6_back_to_chest"] + \
        [at(M_CP, (-17.0, -28.0, 7.0)), at(M_CP, (-3.2, -28.0, E.ZLIB + 1.6 + 2.3))]
    wire("W06", "J6_back_to_chest", P, 0.0023, "jacket",
         [("PHR-5", j6, dir_(M_BP, (0, 1, 0))), ("PHR-5", lib_j1, dir_(M_CP, (1, 0, 0)))],
         [("red", "PMB-H J6-1 VLOAD", "LIB J1-1 VLOAD"), ("black", "J6-2 GND", "J1-2 GND"), ("yellow", "J6-3 SYNC", "J1-3 SYNC_IN"),
          ("green", "J6-4 unused (NC)", "J1-4 spare (to TP5 only)"), ("black/blue", "J6-5 GND", "J1-5 GND")],
         "PH2.0 5P double-ended straight-through (pin 1 to pin 1) cable 0.7 m (purchased; route 531 mm, 0.6 m leaves no slack for bending); a 5P magnetic connector can be inserted in-line", "Back pod CHEST port → channel T4 (right waistline) → chest pod BACK UNIT port")
    # ===================================================== chest pod (B) ===========================================
    zl = E.ZLIB + 1.6 + 2.3; zc_top = E.ZCORE + 1.6
    wire("W07", "lib_to_core_bat", [at(M_CP, (13.5, 2.2, zl)), at(M_CP, (13.5, 12.0, 11.0)), at(M_CP, (19.6, 50.0, 11.0)), at(M_CP, (19.6, 58.9, zc_top + 2.4))],
         0.0010, "red", [("PHR-2", at(M_CP, (13.5, -3.8, zl)), dir_(M_CP, (0, -1, 0))), ("PHR-2", at(M_CP, (19.6, 52.9, zc_top + 2.4)), dir_(M_CP, (0, -1, 0)))],
         [("red", "LIB J2-1 VBIT", "Core B battery socket +"), ("black", "LIB J2-2 GND", "Core B battery socket −")],
         "BOM \"PH2.0 jumper cable\", double-ended 10 cm (⚠ red wire in the same position as on the original Core battery plug)", "Inside pod, passing over the Core")
    i1 = at(M_CP, (56.0, 5.2, zc_top + 1.75))
    wire("W08", "sync_to_I1", [at(M_CP, (28.0, 2.2, zl)), at(M_CP, (40.0, 3.0, 11.0)), at(M_CP, (57.5, 3.0, 11.0)), at(M_CP, (66.0, 1.0, 9.0)), at(M_CP, (78.0, 5.2, zc_top + 1.75))],
         0.0012, "grey", [("PHR-2", at(M_CP, (28.0, -3.8, zl)), dir_(M_CP, (0, -1, 0))), ("UC-E6", i1, dir_(M_CP, (-1, 0, 0)))],
         [("—", "LIB J3-1 SYNC_OUT", "UC-E6 SIGNAL → Core B port I1"), ("—", "LIB J3-2 GND", "UC-E6 GND"), ("—", "(not connected)", "UC-E6 VCC / REF cut short and insulated")],
         "PLUX \"UC-E6 to open-end\" sensor cable with one end cut off (purchased) + PH2 pre-wired lead, crimped/soldered", "Inside pod → out through the right window → into I1")
    # B's ECG sensor (HeartBIT) in the inner pocket: UC-E6 cable to A2 + 3 electrode leads
    eb = SL["ecg_box_B"]; Meb = frame_from_pose(eb)
    for part, dz, col in (("ecg_sensor_bot.stl", -2.0, "ecg"), ("ecg_top.stl", 2.0, "ecg")):
        m = trimesh.load(os.path.join(WS, "modeling", "heartbit-kit-models", "official-stl", part)); m.apply_translation(-m.bounds.mean(0) + (0, 0, dz))
        add(colored(m, C[col]), f"ecg_sensor_B_{part[:-4]}", "skin", Meb)
    a2 = at(M_CP, (56.0, 45.6, zc_top + 1.75)); port_B = np.array(SL["port_B"]["origin"])
    wire("W09", "ecg_B_uce6", [at(Meb, (0, -8.0, 3.0))] + SL["routes"]["B_ecg_uce6_to_A2"][1:-1] + [port_B, port_B + np.array(SL["port_B"]["normal"]) * 0.010,
                                                                 at(M_CP, (80.0, 40.0, 9.0)), at(M_CP, (74.0, 45.6, zc_top + 1.75))],
         0.0015, "white", [(None, None, None), ("UC-E6", a2, dir_(M_CP, (-1, 0, 0)))],
         [("—", "HeartBIT ECG sensor UC-E6", "Core B port A2 (original PLUX cable, pin-to-pin)")], "30 cm UC-E6 sensor cable supplied with the HeartBIT kit ECG sensor (there is also a 10 cm one — too short)",
         "Inner pocket → cable hole B (brass eyelet) → pocket → into A2")
    for col, key, lab in (("red", "B_IN+", "IN+"), ("black", "B_IN-", "IN−"), ("white", "B_REF", "REF")):
        P = SL["routes"][{"B_IN+": "B_lead_red_IN+", "B_IN-": "B_lead_black_IN-", "B_REF": "B_lead_white_REF"}[key]]
        e = SL["electrodes"][key]; n = np.array(e["normal"]); tip = np.array(e["origin"]) + n * 0.004
        wire(f"W10{'abc'[['B_IN+', 'B_IN-', 'B_REF'].index(key)]}", f"lead_B_{lab}", P[:-1] + [tip.tolist()], 0.0010, col,
             [(None, None, None), ("snap", tip, -n)], [(col, f"HeartBIT ECG sensor {lab}", f"Electrode {key}")], "Leads supplied with the HeartBIT kit ECG sensor", "Between skin and lining, held by elastic loops", group="skin")
    # ===================================================== C (Board BLE) ============================================
    for part in ("c_case_base", "c_case_lid"):
        m = trimesh.load(os.path.join(HERE, "parts", part + ".stl")); add(colored(m, C["case"] if part.endswith("base") else rgba("e3e6ea")), part, "C_board" if part.endswith("base") else "C_lid", M_C)
    zb = E.CB["Z"]
    brd = trimesh.creation.box((108.0, 65.0, 1.6)); brd.apply_translation((54.0, 32.5, zb + 0.8)); add(colored(brd, C["board"]), "C_board_pcb", "C_board", M_C)
    for nm, (x0, x1, y0, y1, h) in (("core", (36.0, 72.0, 14.0, 52.0, 2.6)), ("ble", (39.0, 51.0, 0.0, 17.0, 2.3)), ("pwr_conn", (60.0, 66.0, 16.0, 23.0, 4.8)),
                                    ("usb", (55.9, 63.5, -0.6, 5.0, 2.6)), ("switch", (66.0, 73.0, 0.0, 3.5, 3.0)), ("btn", (95.0, 101.0, 38.1, 44.1, 4.0)),
                                    ("led", (39.5, 42.5, 60.0, 63.0, 1.2)), ("lux", (66.5, 70.5, 60.0, 64.0, 1.4)), ("acc", (93.0, 99.0, 10.0, 16.0, 1.0))):
        b = trimesh.creation.box((x1 - x0, y1 - y0, h)); b.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, zb + 1.6 + h / 2))
        add(colored(b, C["metal"] if nm in ("usb",) else C["black"] if nm in ("core", "acc", "btn") else C["ph"]), f"C_{nm}", "C_board", M_C)
    for nm, y in E.C_SOCK_Y.items():
        b = trimesh.creation.box((6.0, 7.0, 3.5)); b.apply_translation((3.0, y, zb + 1.6 + 1.75)); add(colored(b, rgba("d9c389")), f"C_sock_{nm}", "C_board", M_C)
    bat = trimesh.creation.box((50.0, 34.0, 5.2)); bat.apply_translation((46.0, 33.0, 3.1)); add(colored(bat, rgba("c8ccd2")), "C_battery_523450", "C_board", M_C)
    wire("W12", "C_battery", [at(M_C, (21.0, 33.0, 3.5)), at(M_C, (16.0, 60.0, 4.0)), at(M_C, (40.0, 66.8, 6.0)), at(M_C, (63.0, 66.8, 10.0)), at(M_C, (63.0, 26.0, zb + 1.6 + 2.4))],
         0.0010, "red", [(None, None, None), ("PHR-2", at(M_C, (63.0, 23.0, zb + 1.6 + 2.4)), dir_(M_C, (0, -1, 0)))],
         [("red", "523450 +", "Board power block PWR +"), ("black", "523450 −", "PWR −")], "Lead supplied with BOM \"523450 1000 mAh\"; if the plug differs, re-terminate with a \"PH2mm straight-pin pre-wired\" lead", "Inside case, routed around the top edge of the board")
    ecg_c = at(M_C, (0.0, E.C_SOCK_Y["ECG"], zb + 1.6 + 1.75)); port_C = np.array(SL["port_C"]["origin"])
    # the PLUX 3-lead cable splits right at its UC-E6 plug, so the three leads part at the eyelet (skin side), not above it
    ysplit = np.array(SL["routes"]["C_lead_white_REF"][0]) + np.array([0.0, 0.004, -0.002])
    wire("W11", "C_electrode_cable", [at(M_C, (-23.0, E.C_SOCK_Y["ECG"], zb + 1.6 + 1.75)), at(M_C, (-30.0, 50.0, 10.0)), port_C + np.array(SL["port_C"]["normal"]) * 0.01, port_C, ysplit],
         0.0015, "white", [("UC-E6", ecg_c, dir_(M_C, (1, 0, 0))), ("Y", ysplit, np.array([0, -1.0, 0]))],
         [("red", "UC-E6 → C's ECG module", "Electrode C_IN+ (below left clavicle)"), ("black", "—", "Electrode C_IN− (below right clavicle)"), ("white", "—", "Electrode C_REF (left lower ribs)")],
         "PLUX 3-lead electrode cable (supplied with the Board kit, or taken from the HeartBIT kit)", "C case left window → cable hole C → splits inside the vest → skin")
    for col, key, rk in (("red", "C_IN+", "C_lead_red_IN+"), ("black", "C_IN-", "C_lead_black_IN-"), ("white", "C_REF", "C_lead_white_REF")):
        P = SL["routes"][rk]; e = SL["electrodes"][key]; n = np.array(e["normal"]); tip = np.array(e["origin"]) + n * 0.004
        wire(f"W11{'abc'[['C_IN+', 'C_IN-', 'C_REF'].index(key)]}", f"lead_C_{key[2:]}", [ysplit] + P[1:-1] + [tip.tolist()], 0.0010, col,
             [(None, None, None), ("snap", tip, -n)], [(col, "3-lead split", f"Electrode {key}")], "Same as W11", "Between skin and lining", group="skin")
    # ===================================================== A (HeartBIT) + PulseSensor ==============================
    A = SL["A_heartbit"]; MA = frame_from_pose(A)
    for node in gA.graph.nodes_geometry:
        Tn, g = gA.graph[node]; m = gA.geometry[g].copy(); m.apply_transform(Tn)
        G2C = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]]) @ np.diag([1000, 1000, 1000, 1]); m.apply_transform(G2C)
        add(m, f"A_heartbit_{node}", "A_heartbit", None) if False else None
    mA = trimesh.util.concatenate([gA.geometry[g].copy().apply_transform(gA.graph[n][0]) for n, g in ((n, gA.graph[n][1]) for n in gA.graph.nodes_geometry)])
    mA.apply_transform(np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]]) @ np.diag([1000, 1000, 1000, 1]))
    bA = mA.bounds; mA.apply_translation((-(bA[0][0] + bA[1][0]) / 2, -(bA[0][1] + bA[1][1]) / 2, -bA[0][2]))
    add(colored(mA, rgba("c0392b")), "A_heartbit_unit", "A_heartbit", MA)
    clipM = frame_from_pose(SL["earlobe_L"], origin_offset=(-14.0, 0.0, -2.0))
    add(colored(trimesh.load(os.path.join(HERE, "parts", "ear_clip_pulsesensor.stl")), rgba("2b2b2b")), "ear_clip", "skin", clipM)
    ps = trimesh.creation.cylinder(radius=0.0080, height=0.0032, sections=24); ps.apply_translation((0, 0, 0)); add(colored(ps, rgba("101010")), "pulsesensor", "skin", clipM @ np.diag([1000, 1000, 1000, 1]) @ np.array([[1, 0, 0, 0.014], [0, 1, 0, 0], [0, 0, 1, 0.0045], [0, 0, 0, 1]]) @ np.diag([0.001, 0.001, 0.001, 1]))
    a_sock = at(MA, (-34.7 - 9.0, 8.0, 7.0))
    wire("W13", "pulsesensor", [a_sock] + SL["routes"]["A_ppg_cable"][3:] + [at(clipM, (26.0, 0.0, 4.0))], 0.0013, "purple",
         [("UC-E6", at(MA, (-34.7, 8.0, 7.0)), dir_(MA, (1, 0, 0))), (None, None, None)],
         [("red", "PulseSensor +", "A port A3 VCC"), ("black", "PulseSensor −", "A3 GND"), ("purple", "PulseSensor signal", "A3 SIGNAL")],
         "Original HeartBIT kit PulseSensor cable (≈ 60 cm)", "Top edge of A pocket → left-front yoke elastic loop → side of neck → left earlobe clip")
    # ===================================================== thermocouples ==========================================
    pouch = SL["tc_pouch"]; Mp = frame_from_pose(pouch)
    tc1 = at(M_S, (-100.0, 0.0, 9.4)); tc2 = np.array(SL["routes"]["TC2_airgap"][0])
    for wid, tip, rk, plug_x in (("W14", tc1, "TC1_panel", -8.0), ("W15", tc2, "TC2_airgap", 8.0)):
        add(colored(trimesh.creation.cylinder(radius=0.004, height=0.0008), C["metal"]), f"{wid}_tip", "sensors", np.eye(4) @ trimesh.transformations.translation_matrix(tip))
        plug = at(Mp, (plug_x, -6.0, 9.0))
        wire(wid, rk, [tip] + SL["routes"][rk] + [plug + np.array(pouch["up"]) * 0.03, plug], 0.0009, "brown",
             [(None, None, None), ("K-mini", plug, -np.array(pouch["up"]))],
             [("yellow/red", "Type-K thermocouple +", "Thermometer K plug +"), ("red/blue", "Type-K thermocouple −", "Thermometer K plug −")],
             "BOM \"Type-K surface thermocouple\", supplied with plug", {"W14": "Centre of panel backsheet (high-temperature aluminium-foil tape) → channel → left-front plug pouch", "W15": "Vest surface under the panel (heat reaching the body) → channel → plug pouch"}[wid])
    # ===================================================== electrodes, phone ======================================
    for key, e in SL["electrodes"].items():
        o, n = np.array(e["origin"]), np.array(e["normal"])
        add(colored(oriented_cyl(0.012, 0.0010, o + n * 0.0005, n), C["elec"]), f"electrode_{key}", "skin")
        add(colored(oriented_cyl(0.0020, 0.0022, o + n * 0.0021, n), C["metal"]), f"electrode_{key}_stud", "skin")
    ph = SL["phone"]; Mph = frame_from_pose(ph); b = trimesh.creation.box((78.0, 165.0, 9.0)); b.apply_translation((0, 0, 6.0))
    add(colored(b, C["phone"]), "phone", "phone", Mph)
    return wires

if __name__ == "__main__":
    import assembly
    sc, idx = assembly.build(False)
