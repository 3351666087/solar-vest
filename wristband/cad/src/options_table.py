"""[G1] Gate-1 CAD options: one board_zones file per option under out/options/ and the table of what each option costs the wearer
(mm, g, worn fit) and gives the board (mm2 by height class).

For every option in OPTIONS: if out/options/board_zones_<TAG>.json is missing, exports_v3f.py (zones only) and test_lgeom_v3f.py are run for
it; if a full run exists (logs/run_L.sh ... fast -> out/options/<TAG>/), its checks, masses and worn numbers are read.
Area method (geometric, from the zone file; board frame):
  inner      = board outline - 0.5 mm edge band
  fixed      = zones of kind land / part (root lands, J6, J13, J16, J17, SW1, the three fingers, D10)
  dead       = zones of kind no_parts / keepout / keepout_all_layers / cutout / keepout_except
  free       = inner - fixed - dead, split by the lowest height_limit zone at each point (else the general 1.05 mm)
  The layout's own fixed features that the CAD does not place (SWD group 13.2, TP1-TP5 16.2, two lid posts 12.3 E, fiducials) are the same
  in every option and are NOT subtracted from 'free'.
First-order gate-1 figure (E; the real placement decides), stage-1 convention of v3/stage1/checks/cross_check.py:
  placement = board - edge band - antenna 15 - fixed features 102.1 - motor cut-out - 6 post feet - CAD-only no-parts features
  utilisation = courtyard / placement, v1 measure x 399.5 / 360.7, limit 0.62 on both; courtyard as built 490.8 mm2 and 516.4 mm2 with the
  DNP lands and sky fiducials (v3/design/area_check.md), plus the option's own courtyard change.
usage: python3 -B options_table.py     -> out/options/options_table.json, options_table.md
"""
import json, math, os, subprocess, sys
from shapely.geometry import Polygon
from shapely.ops import unary_union
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "out")); OPTD = os.path.join(OUT, "options"); LOGS = os.path.normpath(os.path.join(HERE, "..", "logs"))
PY = "python3"
V1 = 399.5 / 360.7; LIMIT = 0.62
CY_BUILT, CY_PCB, FIXED = 490.8, 516.4, 102.1          # v3/design/area_check.md (stage 1)
MOTOR_PARTS_MM2 = 12.0                                 # D17 2.025 + J17 5.22 + Q12 2.025 + Q19 2.025 + R163 0.704 (v3/design/parts.json, block hmi)
ZIF_MINUS_LAND = 32.94 - 13.44                         # [S2a] FH34SRJ courtyard 7.66 x 4.30 (v3/design parts.json, Hirose p.6 body) against the bridge-flex J13 land (was 33.6 E)
MIN_PART_H = 0.31                                      # lowest part class of the netlist with solder: R0201 0.26 + 0.05 (v3/design/parts.json)
TALL_TO_PLACE = 156.7 - (26.42 + 3 * 6.295 + 7.611)    # tall parts (> 0.70 mm) less SW1, J15, J18, J11 and D10, which the CAD already places: 103.8 mm2

# (level, L, W, V3F_OPT, what, cost notes that the CAD cannot compute)
OPTIONS = [
    ("base", 41, 32, "", "41 x 32 mm base, stage-1 FPC corridor (10.4 mm wide, J13 under the stiffened end: not solderable, see L1-A)", ""),
    ("L1-A", 41, 32, "fpc=dwg", "FPC outline as drawn (9.47 mm wide part + 5.5 mm tail), return run on the board, J13 land beyond the tip + bridge flex", "bridge flex (new custom part), two hot-bar joints"),
    ("L1-A3", 41, 32, "fpc=dwg,fold=1.9", "as L1-A with the fold 1.9 mm from the glass edge", "SW1 courtyard 0.14 mm from the fold"),
    ("L1-R05", 41, 32, "fpc=dwg,raise=0.05", "as L1-A, panel raised 0.05 mm (free fold meets R 0.45 at worst case; low zone 0.80 mm)", ""),
    ("L1-R10", 41, 32, "fpc=dwg,raise=0.1", "as L1-A, panel raised 0.10 mm (low zone 0.85 mm: WSON U10, U15 may go under the panel)", "head rebate +0.10 mm"),
    ("L1-R15", 41, 32, "fpc=dwg,raise=0.15", "as L1-A, panel raised 0.15 mm (low zone 0.90 mm)", "head rebate +0.15 mm"),
    ("L1-B05", 41, 32, "fpc=over,raise=0.05", "FPC over parts: former nose R0.48, return run level, bridge joint, panel +0.05 mm", "former nose, tape over parts"),
    ("L1-B10", 41, 32, "fpc=over,raise=0.1", "FPC over parts, panel +0.10 mm", "former nose, tape over parts; head rebate +0.10"),
    ("L1-B15", 41, 32, "fpc=over,raise=0.15", "FPC over parts, panel +0.15 mm", "former nose, tape over parts; head rebate +0.15"),
    ("L1-Z15", 41, 32, "fpc=dwg,joint=zif,raise=0.15", "J13 as a top-contact ZIF (1.0 mm) under the panel, panel +0.15 mm, return run on the board", "ZIF courtyard +20.2 mm2; head rebate +0.15"),
    ("L1-A3R10", 41, 32, "fpc=dwg,fold=1.9,raise=0.1", "L1-A3 with the panel raised 0.10 mm: the most that level 1 gives inside the maker's rules", "SW1 courtyard 0.09 mm from the fold; head rebate +0.10 mm"),
    ("L1-D00", 41, 32, "fpc=rear", "CONSENT NEEDED: return run bonded under the panel rear after an S-rise (reverse curve, Note 8-1-1); zones only", "the maker's written consent; bridge flex with a 0.8 mm step; no 3-D model"),
    ("L1-D15", 41, 32, "fpc=rear,raise=0.15", "CONSENT NEEDED: as L1-D00 with the panel raised 0.15 mm; zones only", "the maker's written consent; head rebate +0.15; no 3-D model"),
    ("L2-33", 41, 33, "", "41 x 33 mm pod, board 38 x 30, four strips 2.55 mm (stage-1 FPC corridor)", "lid, ring, floor, capsule-side lug retooled"),
    ("L2-33A", 41, 33, "fpc=dwg", "41 x 33 with L1-A", ""),
    ("L2-34", 41, 34, "", "41 x 34 mm pod, board 38 x 31, four strips 2.80 mm (stage-1 FPC corridor)", "PV glass needs a check at 5 bar (see lid)"),
    ("L2-34A", 41, 34, "fpc=dwg", "41 x 34 with L1-A", ""),
    ("L2-33A3", 41, 33, "fpc=dwg,fold=1.9", "41 x 33 with L1-A3 (fold at 1.9 mm)", "SW1 courtyard 0.14 mm from the fold"),
    ("L2-34A3", 41, 34, "fpc=dwg,fold=1.9", "41 x 34 with L1-A3 (fold at 1.9 mm)", "SW1 courtyard 0.14 mm from the fold"),
    ("S2a", 41, 34, "fpc=dwg,fold=1.9,joint=zif,raise=0.15", "STAGE 2a BASELINE (lead decisions a-c): 41 x 34, FPC as drawn, fold 1.9 mm, J13 = top-contact ZIF FH34SRJ, panel +0.15 mm", "ZIF courtyard +19.5 mm2; head rebate +0.15"),
    ("L3-42", 42, 32, "", "42 x 32 mm pod, board 39 x 29 (stage-1 FPC corridor)", ""),
    ("L3-42A", 42, 32, "fpc=dwg", "42 x 32 with L1-A", ""),
    ("L3-42A3", 42, 32, "fpc=dwg,fold=1.9", "42 x 32 with L1-A and the fold at 1.9 mm (SW1 clears it by 1.14 mm)", ""),
    ("L3-42A4", 42, 32, "fpc=dwg,fold=2.9", "42 x 32 with L1-A and the fold at 2.9 mm (SW1 clears it by 0.14 mm)", "SW1 courtyard 0.14 mm from the fold"),
    ("L23-42x33A3", 42, 33, "fpc=dwg,fold=1.9", "42 x 33 mm pod (levels 2 + 3), board 39 x 30, with L1-A and the fold at 1.9 mm", ""),
    ("L4-notch", 41, 32, "motor=d8,my=26.85,notch=1", "dia 8 motor moved to Y 26.85, cut-out opened to the far edge (frees a strip along the rib)", "motor 1.45 mm nearer the root-A wall"),
    ("L4-x17", 41, 32, "motor=d8,mx=17.55", "dia 8 motor at the elbow-side end of its legal window (X 17.55)", ""),
    ("L4-x22", 41, 32, "motor=d8,mx=22.45", "dia 8 motor at the hand-side end of its legal window (X 22.45)", ""),
    ("L4-d7", 41, 32, "motor=d7", "dia 7.0 x 2.0 mm coin ERM (Vybronics VC0720B001F class), 7.6 mm cut-out", "weaker and hungrier: 0.10 Grms, 53 mA typ / 85 max against 0.25 Grms, 30 / 35 mA (maker pages, 2026-11-15); breaks the 35 mA motor budget"),
    ("L4-d6", 41, 32, "motor=d6", "dia 6.0 x 2.5 mm coin ERM (Vybronics VC0625B001L class), 6.6 mm cut-out: DOES NOT FIT in Z", "2.5 mm motor in a 2.35 mm column: 0.25 mm into the PV laminate; PV half +0.40 mm to keep the 0.15 mm margin; 42 mA typ / 100 max"),
    ("L4-none", 41, 32, "motor=none", "no motor: no cut-out, plates extended into the corridor (E1 / E2 contact +16 mm2 each)", "no haptics: wake alarm, alerts and the skin-hot pattern lose their channel (BASELINE 14)"),
    ("L4-noneA3", 41, 32, "fpc=dwg,fold=1.9,motor=none", "no motor with L1-A3: the most a 41 x 32 mm pod gives", "no haptics; SW1 courtyard 0.14 mm from the fold"),
]


def tag_of(L, W, opt):
    env = dict(os.environ, V3F_POD_L=str(L), V3F_POD_W=str(W), V3F_OPT=opt, V3F_NO_OUT="1")
    return subprocess.run([PY, "-B", "-c", "import geom_v3f as G; print(G.TAG)"], cwd=HERE, env=env, capture_output=True, text=True, check=True).stdout.strip()


def probe(L, W, opt, strips=None):
    """geometry numbers of a variant (lid strips, spans) without writing files"""
    o = opt + ("," if opt and strips else "") + (f"strips={strips}" if strips else "")
    env = dict(os.environ, V3F_POD_L=str(L), V3F_POD_W=str(W), V3F_OPT=o, V3F_NO_OUT="1")
    code = ("import json, geom_v3f as G\n"
            "s = G.strips()\n"
            "print(json.dumps(dict(strip_n=G.STRIP_N, strip_w=G.STRIP_W, strips_mm2=[round(x.area, 2) for x in s], silicon_mm2=round(sum(x.area for x in s), 1),"
            " lam_mm2=round(G.lam_outline().area, 1), board=[G.BOARD_L, G.BOARD_W], board_mm2=round(G.board_outline().area, 1),"
            " case_mm2=round(G.case_outline().area, 1), pod_win=G.Z.pod_win, pod_pv=G.Z.pod_pv, e3x=G.E3_BLOCK['x0'], y1=G.BOARD['y1'], cap=G.CAP)))")
    return json.loads(subprocess.run([PY, "-B", "-c", code], cwd=HERE, env=env, capture_output=True, text=True, check=True).stdout)


def ensure_zones(L, W, opt, tag):
    flat = os.path.join(OUT, f"board_zones_{tag}.json") if (W == 32 and not opt) else os.path.join(OPTD, f"board_zones_{tag}.json")
    ran = None
    if not os.path.exists(flat):
        env = dict(os.environ, V3F_POD_L=str(L), V3F_POD_W=str(W), V3F_OPT=opt)
        rc = []
        for scr in ("exports_v3f.py", "test_lgeom_v3f.py"):
            with open(os.path.join(LOGS, f"{scr.split('_')[0]}_{tag}.log"), "w") as fh:
                rc.append(subprocess.run([PY, "-B", scr], cwd=HERE, env=env, stdout=fh, stderr=subprocess.STDOUT).returncode)
        ran = dict(zones_only=True, exports_rc=rc[0], test_lgeom_rc=rc[1])
    if W == 32 and not opt:      # plain outlines live in out/; every option also gets its file in out/options/
        import shutil
        shutil.copyfile(flat, os.path.join(OPTD, f"board_zones_{tag}.json"))
        flat = os.path.join(OPTD, f"board_zones_{tag}.json")
    return flat, ran


def poly(z):
    ps = [Polygon(p).buffer(0) for p in z["poly_board"] if len(p) >= 3]
    return unary_union(ps) if ps else Polygon()


def areas(bz):
    Z = {z["name"]: z for z in bz["zones"]}
    board = Polygon(bz["board"]["outline_board"]); inner = board.buffer(-0.5)
    fixed = unary_union([poly(z) for z in Z.values() if z["kind"] in ("land", "part")])
    dead = unary_union([poly(z) for z in Z.values() if z["kind"] in ("no_parts", "keepout", "keepout_all_layers", "cutout", "keepout_except")])
    free = inner.difference(fixed).difference(dead)
    hz = sorted([z for z in Z.values() if z["kind"] == "height_limit"], key=lambda z: z["h_max_mm"])
    cls, taken = {}, Polygon()
    for z in hz:
        g = poly(z).difference(taken).intersection(free)
        k = f"{z['h_max_mm']:.3f}".rstrip("0").rstrip(".")
        cls[k] = round(cls.get(k, 0.0) + g.area, 1)
        taken = taken.union(poly(z))
    cls[f"{bz['meta']['general_zone_h_max']:g}"] = round(free.difference(taken).area, 1)
    # stage-1 convention (cross_check.py): CAD-only features that no part may use
    feat = [n for n, z in Z.items() if z["kind"] == "no_parts" or n.startswith(("support_leg", "rail_foot"))]
    counted = unary_union([poly(Z[n]) for n in Z if Z[n]["kind"] in ("land", "part", "cutout", "keepout_all_layers") or n.startswith("post_foot") or n == "motor_edge_keepout"])
    feats = unary_union([poly(Z[n]) for n in feat])
    kz = poly(Z["K_zone"]).difference(unary_union([poly(Z["J15_land"]), poly(Z["J18_land"])]))
    jz = poly(Z["J11_zone"]).difference(poly(Z["J11_land"]))
    cad_only = unary_union([feats, kz, jz]).difference(counted).intersection(inner)
    X, Y, R = bz["board"]["W"], bz["board"]["H"], 4.5
    cut = 0.0
    if "motor_cutout" in Z:
        d = bz["motor"]["cutout_d"]
        cut = (math.pi * d * d / 4 + 0.3 * math.pi * d) if not bz["motor"].get("notch") else unary_union([poly(Z["motor_cutout"]), poly(Z["motor_edge_keepout"])]).intersection(inner).area
    conv = (X * Y - (4 - math.pi) * R * R) - 0.5 * 2 * (X + Y) - 15.0 - FIXED - cut - 6.0
    fp = {n: round(poly(Z[n]).intersection(inner).area, 1) for n in Z if n.startswith(("fpc_", "under_fpc", "J13", "bridge"))}
    fpc_dead = unary_union([poly(Z[n]) for n in fp if Z[n]["kind"] != "height_limit"]).intersection(inner)     # union: the stage-1 J13 land lies inside its corridor
    # a height class below the lowest part of the netlist (R0201 0.26 + 0.05 solder) is free on paper only
    unusable = round(sum(v for k, v in cls.items() if float(k) < MIN_PART_H), 1)
    return dict(inner_mm2=round(inner.area, 1), fixed_zones_mm2=round(fixed.intersection(inner).area, 1), dead_zones_mm2=round(dead.difference(fixed).intersection(inner).area, 1),
                free_mm2=round(free.area, 1), free_by_h_max_mm2=cls, free_too_low_for_any_part_mm2=unusable, usable_mm2=round(free.area - unusable, 1),
                cad_only_mm2=round(cad_only.area + unusable, 1), motor_cut_mm2=round(cut, 1),
                placement_stage1_convention_mm2=round(conv - cad_only.area - unusable, 1), fpc_and_J13_zones_mm2=fp,
                fpc_no_parts_incl_J13_mm2=round(fpc_dead.area + unusable, 1))


def navier_w(a, b, t, q, E=70e3, nu=0.22, terms=79):
    D = E * t ** 3 / (12 * (1 - nu ** 2)); w = 0.0
    for m in range(1, terms + 1, 2):
        for n in range(1, terms + 1, 2):
            s = (-1) ** ((m + n) // 2 - 1); w += s / (m * n * (m * m / a ** 2 + n * n / b ** 2) ** 2)
    return w * 16 * q / (math.pi ** 6 * D)


def contact_bar(a, b, t, gap):
    return gap / navier_w(a, b, t, 0.1)


def lid(L, W, pr):
    dw = W - 32.0
    out = dict(strips_4=None, strips_5=None)
    p4 = probe(L, W, "", None); p5 = probe(L, W, "", 5) if dw else None
    base = 255.74                       # four 2.30 mm strips at 32 mm (stage 1, out/checks_V3G9_L41.json)
    out["strips_4"] = dict(width_mm=p4["strip_w"], silicon_mm2=p4["silicon_mm2"], gain_vs_2p30=round(p4["silicon_mm2"] / base - 1, 4))
    if p5:
        out["strips_5"] = dict(width_mm=p5["strip_w"], silicon_mm2=p5["silicon_mm2"], gain_vs_2p30=round(p5["silicon_mm2"] / base - 1, 4),
                               note="five cells in series raise the lid string voltage by 5/4; the wing has four: the PV node, R_LIM and the cold start change (BASELINE 4, 11)")
    b_bl = 10.6 + dw; a_bl = 28.7        # BASELINE 13.4 span (28.7 x 10.6 at 32 mm)
    t5 = None
    lo, hi = 0.3, 1.5
    for _ in range(50):
        m = (lo + hi) / 2
        if contact_bar(a_bl, b_bl, m, 0.15) < 5.0: lo = m
        else: hi = m
    out["pv_glass_5bar"] = dict(span_mm=[a_bl, round(b_bl, 2)], t_mm=0.50, gap_mm=0.15, contact_bar_ss=round(contact_bar(a_bl, b_bl, 0.50, 0.15), 2),
                                contact_bar_clamped_E=round(contact_bar(a_bl, b_bl, 0.50, 0.15) * 3.2, 1), glass_needed_for_5bar_ss_mm=round(hi, 3),
                                method="BASELINE 13.4 Navier plate, simply supported upper bound, 0.50 mm glass alone, 0.15 mm to the parts")
    Ei = 193e3; Ii = 0.5 * 0.755 ** 3 / 12; q5 = 0.5; pg = 6.0
    w_rib = q5 * (14.6 / 2 + (10.45 + dw) / 2)
    out["rib_insert_5bar"] = dict(line_load_N_per_mm=round(w_rib, 2), deflection_between_posts_mm=round(5 * w_rib * pg ** 4 / (384 * Ei * Ii), 4), criterion_mm=0.05,
                                  method="v3/stage1/calc/window_plate_s1.py: beam between posts 6.0 mm apart, 0.5 x 0.755 mm stainless")
    out["laminate_mm2"] = p4["lam_mm2"]
    return out


def load(tag, name, plain):
    p = os.path.join(OUT if plain else os.path.join(OPTD, tag), f"{name}_{tag}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def main():
    rows = []; base = None
    for lvl, L, W, opt, what, extra in OPTIONS:
        tag = tag_of(L, W, opt); plain = (W == 32 and not opt)
        flat, ran = ensure_zones(L, W, opt, tag)
        bz = json.load(open(flat)); pr = probe(L, W, opt)
        a = areas(bz)
        r = dict(id=lvl, tag=tag, pod_mm=[L, W], board_mm=bz["meta"]["board_mm"], opt=opt, what=what, zones_file=os.path.relpath(flat, os.path.join(OUT, "..")),
                 n_zones=len(bz["zones"]), areas=a, extra_cost=extra, zones_only_run=ran,
                 window_half_mm=round(pr["pod_win"], 3), pv_half_mm=round(pr["pod_pv"], 3))
        cy_d = (ZIF_MINUS_LAND if "joint=zif" in opt else 0.0) - (MOTOR_PARTS_MM2 if "motor=none" in opt else 0.0)
        pa = a["placement_stage1_convention_mm2"]
        r["gate1_first_order"] = dict(courtyard_delta_mm2=round(cy_d, 1), placement_mm2=pa,
                                      as_built=[round((CY_BUILT + cy_d) / pa, 3), round((CY_BUILT + cy_d) / pa * V1, 3)],
                                      pcb_with_dnp_and_fiducials=[round((CY_PCB + cy_d) / pa, 3), round((CY_PCB + cy_d) / pa * V1, 3)],
                                      courtyard_allowed_at_0p62_on_v1_mm2=round(pa * LIMIT / V1 - cy_d, 1), courtyard_allowed_at_0p62_project_mm2=round(pa * LIMIT - cy_d, 1),
                                      tall_parts_to_place_mm2=round(TALL_TO_PLACE - (0.0 if "motor=none" not in opt else 0.0), 1),
                                      general_zone_free_mm2=a["free_by_h_max_mm2"].get("1.05"),
                                      tall_zone_first_order=[round(TALL_TO_PLACE / (a["free_by_h_max_mm2"]["1.05"] - 41.7), 3),
                                                             round(TALL_TO_PLACE / (a["free_by_h_max_mm2"]["1.05"] - 41.7) * V1, 3)],
                                      tall_zone_note="tall parts still to place (103.8 mm2) over the 1.05 mm class less the layout's SWD group, test pads and lid posts (41.7 mm2)")
        ck = load(tag, "checks_pod", plain); wn = load(tag, "worn_checks", plain); ma = load(tag, "mass", plain); ms = load(tag, "motor_search", plain)
        g9 = load(tag, "checks_V3G9", plain); pc = load(tag, "plate_contact", plain)
        r["full_run"] = ck is not None
        if ck:
            cm = ck["clearance_mm"]
            def find(s): return next((v for k, v in cm.items() if s in k), None)
            r["checks"] = dict(interference=len(ck["interference"]), pairs=ck["pairs_tested"], voids_clear=all(v["ok"] for v in ck["void_checks"].values()),
                               sw1_to_fpc_fold_mm=find("SW1 courtyard / copper to the FPC fold"), e3_metal_to_panel_mm=find("E3-net metal to the max-material panel"),
                               e3_metal_to_fold_mm=find("E3-net metal to the display FPC fold"), fpc_to_sw1_3d_mm=find("display FPC fold -> SW1"),
                               fpc_to_frame_mm=find("display FPC -> window frame"), panel_to_film_gap_mm=find("panel at max material -> front-light film"),
                               motor_to_laminate_mm=find("PV laminate flex (motor column margin)"),
                               g9=[(c["name"].split(":")[0], c["status"]) for c in g9["criteria"]] if g9 else None)
        if ma:
            r["mass"] = dict(pod_cad_g=ma["pod_cad_total_g"], pod_cad_board_scaled_g=ma["pod_cad_total_board_scaled_g"],
                             worn_typ_g=ma["worn_mass_g_cad_pod_board_scaled_plus_baseline_strap_typ"])
        if wn:
            w = wn["wrists"]
            r["worn"] = {c: dict(free_span_mm=w[c]["free_span_mm"], tilt_deg=w[c]["tilt_deg"], capsule_above_skin_mm=w[c]["capsule"]["thickness_above_skin_far_end_box_mm"],
                                 capsule_inner_gap_mm=w[c]["capsule"]["inner_face_gap_far_end_mm"], capsule_overhang_mm=w[c]["capsule"]["overhang_past_tangent_mm"],
                                 capsule_top_below_pv_top_mm=w[c]["capsule"]["outer_top_below_pod_PV_top_mm"], wing_above_skin_mm=w[c]["wing"]["thickness_above_skin_far_end_box_mm"],
                                 wing_inner_gap_mm=w[c]["wing"]["inner_face_gap_far_end_mm"], pod_edge_from_skin_mm=w[c]["items"]["pod_body"]["max_distance_from_skin_mm"],
                                 capsule_from_skin_max_mm=w[c]["items"]["capsule"]["max_distance_from_skin_mm"],
                                 no_strap_item_above_pv_top=max(v["max_height_above_floor_plane_mm"] for k, v in w[c]["items"].items() if not k.startswith("pod")) < pr["pod_pv"] - 0.8,
                                 capsule_first_contact_roll_deg=[(x["phi0"], x["phi1"]) for x in wn["roll_contact"][c]["ranges"] if x["item"] == "capsule"],
                                 head_to_capsule_mm=wn["head"][c]["clearance to capsule"], head_to_skin_mm=wn["head"][c]["clearance to skin"]) for c in w}
            ex = [c for c in wn["wrist_extension"]["cases"] if c["axis_depth_mm"] == 16.0 and c["gap_pod_end_to_joint_line_mm"] in (0.0, 15.0)]
            r["wrist_extension_deg"] = {f"{c['end'][:5].strip()} g{c['gap_pod_end_to_joint_line_mm']:g}": c["contact_deg_this_pod_centred"] for c in ex}
            r["head_rebate_clearance_mm"] = wn["head"]["165"]["rebate_clearance_mm"]
        if pc:
            r["plates"] = dict(area_mm2=pc["plate_area_mm2"], strip_14p9_mm2=pc["convention_14p9"], wrist130_indent0p6_mm2=pc["wrists"]["130"]["indent 0.6"],
                               wrist140_indent0p6_mm2=pc["wrists"]["140"]["indent 0.6"], g7_min_mm2=pc["G7_min_mm2"])
        if ms and ms.get("variants", {}).get("hole", {}).get("feasible") is not None:
            r["motor"] = dict(part=ms.get("motor", {}).get("part"), asked_centre=ms.get("asked_centre"), asked_variant=ms.get("asked_variant"), asked_legal=ms.get("asked_centre_legal"),
                              hole_window=dict(x=ms["variants"]["hole"].get("x_range"), y=ms["variants"]["hole"].get("y_range"), mm2=ms["variants"]["hole"].get("area_mm2")),
                              notch_window=dict(x=ms["variants"]["notch"].get("x_range"), y=ms["variants"]["notch"].get("y_range"), mm2=ms["variants"]["notch"].get("area_mm2")),
                              clearances=ms.get("asked_centre_clearances"))
        if W != 32:
            r["lid"] = lid(L, W, pr)
            r["ppg_mesa_off_centre_mm"] = round((pr["cap"]["y0"] + pr["cap"]["y1"]) / 2 - W / 2, 2)
        if lvl == "base":
            base = r; r["lid"] = lid(L, W, pr); r["ppg_mesa_off_centre_mm"] = round((pr["cap"]["y0"] + pr["cap"]["y1"]) / 2 - W / 2, 2)
        # deltas against the base
        b = base["areas"]
        keys = sorted(set(a["free_by_h_max_mm2"]) | set(b["free_by_h_max_mm2"]), key=float)
        r["gain_vs_base"] = dict(free_mm2=round(a["free_mm2"] - b["free_mm2"], 1), usable_mm2=round(a["usable_mm2"] - b["usable_mm2"], 1),
                                 by_h_max_mm2={k: round(a["free_by_h_max_mm2"].get(k, 0.0) - b["free_by_h_max_mm2"].get(k, 0.0), 1) for k in keys},
                                 placement_stage1_convention_mm2=round(a["placement_stage1_convention_mm2"] - b["placement_stage1_convention_mm2"], 1))
        if "mass" in r and "mass" in base:
            r["cost_vs_base"] = dict(pod_g=round(r["mass"]["pod_cad_board_scaled_g"] - base["mass"]["pod_cad_board_scaled_g"], 2),
                                     window_half_mm=round(r["window_half_mm"] - base["window_half_mm"], 3), length_mm=L - 41, width_mm=W - 32)
        rows.append(r)
    res = dict(date="2026-11-14 / 2026-11-15", lane="v3/g1/cad (gate-1 CAD options)", base="41 x 32 mm pod, board 38 x 29 mm", method=__doc__.split("Area method")[1].split("usage")[0],
               courtyards=dict(as_built_mm2=CY_BUILT, pcb_with_dnp_and_fiducials_mm2=CY_PCB, fixed_features_mm2=FIXED, source="v3/design/area_check.md"),
               options=rows)
    json.dump(res, open(os.path.join(OPTD, "options_table.json"), "w"), indent=1)
    # ---------------- markdown
    def cl(a):
        return " / ".join(f"{k}: {v}" for k, v in sorted(a.items(), key=lambda kv: float(kv[0])))
    M = ["# V3-F gate-1 CAD options: what each one gives the board and costs the wearer", "",
         "Written by `src/options_table.py` (2026-11-14, extended 2026-11-15). Base = 41 x 32 mm pod, board 38 x 29 mm. Every row has a zone file with the same schema as "
         "`board_zones.json`. Marks: areas are tool output from the zone files; the gate-1 figures are first order (⚠): the real placement decides.", "",
         "## 1. Board: free placement area by height class (mm², inside the 0.5 mm edge band, CAD lands, parts and keep-outs removed)", "",
         "| Id | Tag (zone file `out/options/board_zones_<tag>.json`) | Pod / board mm | Usable, total | Free by h_max (mm: mm²) | Usable gain against the base | FPC + J13 area without parts | Placement, stage-1 convention | Courtyard that fits at 0.62: project / v1 | Gate 1 first order, as built: project / v1 | With DNP lands + fiducials | Tall zone first order |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        a = r["areas"]; g = r["gate1_first_order"]
        M.append(f"| {r['id']} | `{r['tag']}` | {r['pod_mm'][0]} x {r['pod_mm'][1]} / {r['board_mm'][0]:g} x {r['board_mm'][1]:g} | {a['usable_mm2']} | {cl(a['free_by_h_max_mm2'])} | "
                 f"{r['gain_vs_base']['usable_mm2']:+.1f} | {a['fpc_no_parts_incl_J13_mm2']} | {a['placement_stage1_convention_mm2']} ({r['gain_vs_base']['placement_stage1_convention_mm2']:+.1f}) | "
                 f"{g['courtyard_allowed_at_0p62_project_mm2']} / {g['courtyard_allowed_at_0p62_on_v1_mm2']} | "
                 f"{g['as_built'][0]:.3f} / {g['as_built'][1]:.3f} | {g['pcb_with_dnp_and_fiducials'][0]:.3f} / {g['pcb_with_dnp_and_fiducials'][1]:.3f} | "
                 f"{g['tall_zone_first_order'][0]:.3f} / {g['tall_zone_first_order'][1]:.3f} |")
    M += ["", "'Courtyard that fits at 0.62' = placement × 0.62 (project measure) and placement × 0.62 / 1.108 (v1's bounding-box measure), less the option's own "
          "courtyard change (ZIF +20.2 mm², no motor −12.0 mm²): the stage-1 netlist's courtyard may be at most this large. "
          f"The stage-1 netlist is {CY_BUILT} mm² ({CY_PCB} mm² with the DNP lands and sky fiducials). The first-order figures are ⚠: the real placement decides.", "",
          "Rows marked CONSENT NEEDED are not available today: they break LD-29Y03 Note 8-1-1 unless the maker agrees in writing. The base row keeps the stage-1 "
          "corridor for traceability only: its J13 land lies under the FPC's stiffener and cannot be soldered, so layout must start from L1-A or later.", "",
          "A height class below 0.31 mm (R0201 with solder) holds no part of the netlist: it is listed under 'Free by h_max' but not counted as usable, "
          "nor in the placement area.", "",
          "## 2. Wearer: size, mass, worn fit", "",
          "| Id | What | Window half / PV half mm | Pod g (board scaled) | Δ g | Worn g typ | Free span 130 / 200 mm | Tilt 130 / 200 | Capsule above skin 130 / 200 | Pod edge off the skin 130 / 200 | Extension at first contact, left g 0 / g 15 | Checks (interference, voids) | Other cost |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        m = r.get("mass"); w = r.get("worn"); c = r.get("checks"); ex = r.get("wrist_extension_deg", {})
        M.append(f"| {r['id']} | {r['what']} | {r['window_half_mm']} / {r['pv_half_mm']} | {m['pod_cad_board_scaled_g'] if m else 'zones only'} | "
                 f"{r['cost_vs_base']['pod_g']:+.2f} |" .replace("| +0.00 |", "| 0 |") if m and "cost_vs_base" in r else
                 f"| {r['id']} | {r['what']} | {r['window_half_mm']} / {r['pv_half_mm']} | zones only | – |")
        M[-1] += (f" {m['worn_typ_g']} | {w['130']['free_span_mm']} / {w['200']['free_span_mm']} | {w['130']['tilt_deg']} / {w['200']['tilt_deg']} | "
                  f"{w['130']['capsule_above_skin_mm']} / {w['200']['capsule_above_skin_mm']} | {w['130']['pod_edge_from_skin_mm']} / {w['200']['pod_edge_from_skin_mm']} | "
                  f"{ex.get('left g0')} / {ex.get('left g15')} | {c['interference']} of {c['pairs']}, {'clear' if c['voids_clear'] else 'HIT'} | {r['extra_cost']} |"
                  if m and w and c else f" – | – | – | – | – | – | not run | {r['extra_cost']} |")
    M += ["", "## 3. Lid and rib of the wider pods (level 2)", "",
          "| Id | Four strips: width, silicon mm², gain | Five strips: width, silicon mm², gain | PV glass 0.50 mm, first contact (SS / clamped ⚠) | Glass for 5 bar SS | Rib insert between posts at 5 bar (limit 0.05 mm) | PPG mesa off the pod centre line |",
          "|---|---|---|---|---|---|---|"]
    for r in rows:
        if "lid" not in r: continue
        l = r["lid"]; s4 = l["strips_4"]; s5 = l["strips_5"]
        M.append(f"| {r['id']} | {s4['width_mm']:g} mm, {s4['silicon_mm2']}, {100 * s4['gain_vs_2p30']:+.1f} % | " +
                 (f"{s5['width_mm']:.3f} mm, {s5['silicon_mm2']}, {100 * s5['gain_vs_2p30']:+.1f} %" if s5 else "–") +
                 f" | {l['pv_glass_5bar']['contact_bar_ss']} / {l['pv_glass_5bar']['contact_bar_clamped_E']} bar on {l['pv_glass_5bar']['span_mm'][0]} x {l['pv_glass_5bar']['span_mm'][1]} mm | "
                 f"{l['pv_glass_5bar']['glass_needed_for_5bar_ss_mm']} mm | {l['rib_insert_5bar']['deflection_between_posts_mm']} mm | {r['ppg_mesa_off_centre_mm']} mm |")
    M += ["", "## 4. Plates and motor (level 4 and the wider pods)", "",
          "| Id | E1 / E2 area mm² | In the 14.9 mm strip | 130 mm wrist, 0.6 mm indentation (G-7 ≥ 150) | Motor | Legal centres, closed cut-out | Centre used, legal |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        p = r.get("plates"); mo = r.get("motor")
        if not p: continue
        M.append(f"| {r['id']} | {p['area_mm2']['E1']} / {p['area_mm2']['E2']} | {p['strip_14p9_mm2']['E1']} / {p['strip_14p9_mm2']['E2']} | "
                 f"{p['wrist130_indent0p6_mm2']['E1']} / {p['wrist130_indent0p6_mm2']['E2']} | " +
                 (f"{mo['part']} | X {mo['hole_window']['x']}, Y {mo['hole_window']['y']} ({mo['hole_window']['mm2']} mm²) | {mo['asked_centre']} ({mo['asked_variant']}), {mo['asked_legal']} |"
                  if mo else "none | – | – |"))
    open(os.path.join(OPTD, "options_table.md"), "w").write("\n".join(M) + "\n")
    for r in rows:
        a = r["areas"]; g = r["gate1_first_order"]
        print(f"{r['id']:8s} {r['tag']:34s} usable {a['usable_mm2']:6.1f} ({r['gain_vs_base']['usable_mm2']:+6.1f}) {cl(a['free_by_h_max_mm2']):60s} fpc {a['fpc_no_parts_incl_J13_mm2']:6.1f} "
              f"plc {a['placement_stage1_convention_mm2']:6.1f} g1 {g['as_built'][0]:.3f}/{g['as_built'][1]:.3f} pcb {g['pcb_with_dnp_and_fiducials'][0]:.3f}/{g['pcb_with_dnp_and_fiducials'][1]:.3f} "
              f"full {r['full_run']} {r.get('zones_only_run') or ''}")


if __name__ == "__main__":
    main()
