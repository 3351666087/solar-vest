"""V3-F CAD exports for other lanes:
  out/board_zones_L<40|41>.json  layout input (board outline, keep-outs, zones with height limits, motor cut-out, rib-post feet,
                                 spring-finger and entry-land positions, button and contact positions, antenna keep-out, plates)
  out/band_contacts_L<..>.json   the band side of the charging interface as built in CAD (for the head lane)
and, if v3/head/head_interface.json exists, a comparison with it.  Frames: see geom_v3f.py.  The loader src/lgeom_v3f.py
reads board_zones*.json in the style of layout/tools/lgeom.py.
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import geom_v3f as G                                       # noqa: E402
from shapely.geometry import Point, box as sbox, mapping   # noqa: E402

OUT = G.OUT_DIR                                             # [G1] out/ for plain outlines, out/options/<TAG>/ for option runs
TAG = G.TAG
HEAD_IF = "/path/to/SolarVest_work/wristband/v3/head/head_interface.json"
Z = G.Z


def r4(v): return round(float(v), 4)


def poly_xy(g, frame="board", simplify=0.005):
    g = g.buffer(0).simplify(simplify, preserve_topology=True)
    polys = [g] if g.geom_type == "Polygon" else list(getattr(g, "geoms", []))
    out = []
    for p in polys:
        pts = list(p.exterior.coords)[:-1]
        if frame == "board":
            pts = [G.to_board(x, y) for x, y in pts]
        out.append([[r4(x), r4(y)] for x, y in pts])
    return out


def bbox(g, frame="board"):
    x0, y0, x1, y1 = g.bounds
    if frame == "board":
        (x0, y0), (x1, y1) = G.to_board(x0, y0), G.to_board(x1, y1)
    return [r4(x0), r4(y0), r4(x1), r4(y1)]


def board_zones():
    zones = []
    for z in G.board_zones():
        zones.append(dict(name=z["name"], kind=z["kind"], h_max_mm=z["h_max"], rect_board=bbox(z["geom"]), poly_board=poly_xy(z["geom"]),
                          rect_case=bbox(z["geom"], "case"), area_mm2=round(z["geom"].area, 2), note=z["note"]))
    skin = []
    for z in G.skin_zones():
        skin.append(dict(name=z["name"], kind=z["kind"], rect_board=bbox(z["geom"]), poly_board=poly_xy(z["geom"]),
                         rect_case=bbox(z["geom"], "case"), area_mm2=round(z["geom"].area, 2), note=z["note"]))
    bo = G.board_outline()
    mc = G.MOTOR_C
    out = dict(
        meta=dict(date="2026-11-14 (stage 1 fixes, v3/stage1/STAGE1.md; gate-1 options lane v3/g1/cad)", lane="v3/cad (V3-G9)", pod_L=G.POD_L, pod_W=G.POD_W,
                  tag=G.TAG, options=G.OPT, board_mm=[G.BOARD_L, G.BOARD_W],
                  frames=dict(board="board frame, mm: origin at the board's bottom-left corner, X along the forearm (X = 0 elbow end on a left "
                                    "wrist), Y = 0 antenna / root-B edge, viewed from the SKY = F.Cu = JLC top (V2-B lgeom convention)",
                              case="case frame of BASELINE 7: X_case = X_board + 1.5, Y_case = Y_board + 1.5"),
                  h_max="maximum part height above the board top surface including solder (max-material stack of BASELINE 8: board top at "
                        "Z 1.45 above the floor face); 0 = no parts (lands and keep-outs); null = no limit beyond the general zone",
                  general_zone_h_max=round(Z.parts_gen - Z.pcb1, 2),
                  rule="part courtyards must lie inside a zone whose h_max covers the part; zone edges already include 0.3 mm to the "
                       "structure above them (rib, rail, K block, E3 shelf). Priority (lgeom_v3f.height_limit_at): keep-out / cut-out / "
                       "antenna keep-out / no_parts = 0; a 'part' or 'land' zone gives its own h_max for that part; otherwise the lowest "
                       "height_limit zone; otherwise the general zone",
                  source="v3/cad/src/geom_v3f.py board_zones(), skin_zones(); BASELINE.md 5.1, 7, 8; datasheets in v3/cad/ref/sources.md"),
        board=dict(W=G.BOARD_L, H=G.BOARD_W, corner_r=dict(BL=G.BOARD["R"], BR=G.BOARD["R"], TR=G.BOARD["R"], TL=G.BOARD["R"]),
                   thickness_nominal=1.0, thickness_max=1.10, outline_board=poly_xy(bo)[0], case_origin=[1.5, 1.5]),
        motor=dict(centre_board=list(G.to_board(*mc)), centre_case=list(mc), cutout_d=G.MOTOR["cut_d"], motor_d=G.MOTOR["d"],
                   motor_d_max=G.MOTOR["d_max"], motor_h_max=G.MOTOR["h_max"], edge_clearance=G.CUT_EDGE_CLR, fitted=G.HAS_MOTOR,
                   variant=G.MOTOR_KEY, part=G.MOTOR["part"], notch=G.MOTOR_NOTCH,
                   board_strip_to_far_edge_mm=round(G.BOARD["y1"] - (mc[1] + G.MOTOR["cut_d"] / 2), 2),
                   note=("closed 8.6 mm cut-out (BASELINE); legal centres X 17.55-22.45, Y 25.15-25.70 (motor_search); the 0.8 mm strip to the "
                         "far edge cannot carry routing: V3-G1 may open the cut-out to the edge (notch variant, legal Y up to 26.85)")
                   if G.MOTOR_KEY == "d8" and not G.OPT and not G.DW else "see out/options/<tag>/motor_search_<tag>.json for this variant's legal window"),
        rib_posts=dict(x_board=[r4(x - 1.5) for x in G.POST_X], foot_y_board=[r4(G.POST_FOOT[0] - 1.5), r4(G.POST_FOOT[1] - 1.5)],
                       post_mm=[G.POST_SIZE, G.POST_SIZE], foot_keepout_mm=[1.0, 1.0]),
        springs=dict(J15=[dict(ref=p["ref"], pin=p["name"], net=p["net"], land_board=list(G.to_board(*p["land"])), pad_mm=list(G.J15_PAD),
                               part="BAT WIRELESS BW0036BG-L3.0W1.0H1.4 (C2826535)", mating_face_mm=list(G.FACE),
                               courtyard_board=bbox(G.finger_courtyard(p["land"])), free_height_mm=G.J15_H,
                               mating_face_z_above_board_top=round(Z.finger_work, 2),
                               open_item="BW0036BG drawing (tip position, free and working height) not found: the inner face must cover the tip "
                                         "in both 180 deg orientations; JLC preview + EOL-1 until then (S1 C-8)") for p in G.PINS],
                     J11=dict(land_board=list(G.to_board(*G.J11["land"])), pad_mm=list(G.J15_PAD), part="BW0036BG (E3 finger)",
                              mating_face_mm=list(G.FACE))),
        button=dict(SW1="C&K PTS840 GK SMTR LFS (C221907), side actuated, actuator toward +X at the board's hand-end edge",
                    body_front_board_x=r4(G.SW1["front_x"] - 1.5), centre_board_y=r4(G.SW1["cy"] - 1.5), body_mm=[G.SW1["body_x"], G.SW1["body_y"], G.SW1["h"]],
                    leads_span_y=G.SW1["lead_y"], actuator=dict(w=G.SW1["act_w"], protrusion=G.SW1["act_out"]),
                    membrane_case=dict(Y=[G.MEMBRANE["y0"], G.MEMBRANE["y1"]], Z=[G.MEMBRANE["z0"], G.MEMBRANE["z1"]], t=G.MEMBRANE["t"])),
        display=dict(panel_case=G.PANEL, panel_board=[*G.to_board(G.PANEL["x0"], G.PANEL["y0"]), *G.to_board(G.PANEL["x1"], G.PANEL["y1"])],
                     fpc_end_x_board=r4(G.FPC_END_X - 1.5), fpc_y_board=[r4(G.FPC_Y[0] - 1.5), r4(G.FPC_Y[1] - 1.5)],
                     fpc_model=G.FPC_MODEL, fpc_joint=G.JOINT, fpc_fold_at_mm=G.FPC_FOLD_AT, fpc_fold_r_in_mm=round(G.FPC_FOLD_RIN, 4),
                     fpc_return_underside_above_board_mm=round(G.FPC_Z_RETURN - Z.pcb1, 3), panel_raise_mm=G.RAISE,
                     needs_maker_consent=(G.FPC_MODEL == "rear"),   # [G1 session 2] the rear-bonded routing has a reverse curve (LD-29Y03 Note 8-1-1)
                     fpc_wide_end_x_board=r4(G.FPC_WIDE_X - 1.5), fpc_y_wide_board=[r4(G.FPC_Y_WIDE[0] - 1.5), r4(G.FPC_Y_WIDE[1] - 1.5)],
                     fpc_y_tail_board=[r4(G.FPC_Y_TAIL[0] - 1.5), r4(G.FPC_Y_TAIL[1] - 1.5)],
                     fpc_open_item="[G1] LD-29Y03 Fig. 14-1 shows the terminals on the REAR face and the stiffener on the FRONT face: after the only "
                                   "allowed fold the terminals face the panel, not the board. A land under the stiffened end (fpc=s1, stage 1) cannot "
                                   "be soldered; see v3/g1/cad/CAD_OPTIONS.md 2 (bridge flex or top-contact ZIF)",
                     J13_note="soldered FPC land under the stiffened FPC end (10 pads 0.3 x 1.6 mm at 0.5 mm + key pad)" if G.FPC_MODEL == "s1" else
                              "see zone J13_land of this option (joint = " + G.JOINT + ")",
                     film_tail_J16_board=bbox(sbox(G.J16["x0"], G.J16["y0"], G.J16["x1"], G.J16["y1"]))),
        entry_lands=dict(root_A=dict(rect_board=bbox(sbox(G.LAND_A[0], G.LAND_A[2], G.LAND_A[1], G.LAND_A[3])), order="BATT_P | GND | NTC | GND"),
                         root_B=dict(rect_board=bbox(sbox(G.LAND_B[0], G.LAND_B[2], G.LAND_B[1], G.LAND_B[3])), order="PV_W+ | GND")),
        antenna=dict(keepout_board=bbox(sbox(G.ANT_KEEPOUT[0], G.ANT_KEEPOUT[2], G.ANT_KEEPOUT[1], G.ANT_KEEPOUT[3])), all_layers=True,
                     metal_rule_mm=G.ANT_METAL_MIN, motor_rule_mm=G.MOTOR_ANT_MIN,
                     **(dict(lid_antenna_L1=dict(
                         footprint="AE1_lid_L1 (v3/sim/rf/lid/export), board (0, 0), rot 0, front; J40 BW0019BG (C2826516) on its FEED land, board "
                                   + str(list(G.J40["land_board"])) + f" rot {G.J40['rot']:g}",
                         strip_case=[list(map(float, c)) for c in G.LID_STRIP.exterior.coords], strip_t_mm=G.LID_STRIP_T, strip_z_case=[round(Z.win0 - G.LID_STRIP_T, 4), Z.win0],
                         frame_cut_case="stainless window frame removed for X < 13.0 in Y 0.5-5.65; glass on the PC seat (ant_seat) there",
                         board_to_glass_mm=dict(max_board=round(Z.win0 - Z.pcb1, 3), nominal_board=round(Z.win0 - Z.pcb1 + 0.10, 3)),
                         tolerance_note=f"TOLERANCE: board top to glass inner face at the antenna corner +-{G.GLASS_GAP_TOL:.2f} mm (lid lane: about -24 Ohm "
                                        "reactance per 0.25 mm; first boards get a bench S11 tune). J40 BW0019BG: working 3.00, limit 2.50 (drawing 681-0019B-2)")) if G.S2C else {})),
        O2_reserve=dict(area_mm2=G.o2_courtyard_mm2()[0], refs=G.o2_courtyard_mm2()[1], position=None,
                        note="[S1 C-5] courtyard of the built O-2 (v3/design/parts.json, incl. the stage-1 heartbeat C175 / R176) against "
                             "BASELINE's 12 mm2 reserve; 0 if reserve 3 (cut-off in the pack PCM) is taken; layout chooses the position"),
        window_rail=dict(rect_case=[G.RAIL["x0"], G.RAIL["y0"], G.RAIL["x1"], G.RAIL["y1"]], underside_z_case=Z.rail0,
                         posts_x_case=list(G.RAIL_POST_X), post_mm=list(G.RAIL_POST), foot_keepout_mm=G.RAIL_FOOT,
                         note="[S1 C-1] GF-LCP rail under the window frame / glass (structural bond); parts <= 0.70 mm under it (zone rail_strip)"),
        skin_hot_led=dict(rect_case=[G.D10["x0"], G.D10["y0"], G.D10["x1"], G.D10["y1"]], h=G.D10["h"], light_path_case=G.D10_WIN),
        lid_tail=dict(J6_case=G.J6, tail_case=G.LID_TAIL),
        plate_dot_pads=G.plate_dot_pads(),
        zones=zones, skin_face=skin)
    return out


def band_contacts(board):
    pins = []
    for p in G.PINS:
        tx, ty = p["top"]; lx, ly = p["land"]
        pins.append(dict(name=p["name"], ref=p["ref"], net=p["net"], top_face_centre_case=[tx, ty], top_face_d_mm=p["d"],
                         top_face_z_case=round(Z.rim_top - G.PIN_RECESS, 3), recess_mm=G.PIN_RECESS, recess_tol_mm=0.05,
                         counterbore_d_mm=p["cb_d"], counterbore_tol_mm=list(p["cb_tol"]), counterbore_edge=p["cb_edge"],
                         counterbore_r_max_mm=round(G.cb_rmax(p), 3),
                         rim_top_z_case=Z.rim_top, inner_face_centre_case=[lx, ly], inner_face_mm=dict(along_Y=G.FACE[0], along_X=G.FACE[1]),
                         inner_face_z_case=Z.finger_top, J15_land_board=list(G.to_board(lx, ly)),
                         material="gold over a nickel-free layer, or 316L / Ti (EN 1811) [B 5.2]"))
    (ax, ay), (bx_, by_) = G.PINS[0]["top"], G.PINS[1]["top"]
    pitch = math.hypot(bx_ - ax, by_ - ay)
    mid = ((ax + bx_) / 2, (ay + by_) / 2)
    tg = G.TARGETS[0]
    tr = (2 * mid[0] - tg["c"][0], 2 * mid[1] - tg["c"][1])
    head = G.HEAD
    hrot = (2 * mid[0] - head["x1"], 2 * mid[0] - head["x0"], 2 * mid[1] - head["y1"], 2 * mid[1] - head["y0"])
    ktop = G.case_outline().intersection(sbox(0, G.Y_WIN1, G.X_KTOP1, G.POD_W))
    return dict(
        meta=dict(date="2026-11-14 (stage 1: K corner re-laid, review C-2; head housing of head_interface.json, C-12)", lane="v3/cad (V3-G9)", pod_L=G.POD_L, frame="case frame of BASELINE 7 (X along the forearm, X = 0 elbow end on a "
                  "left wrist; Y = 0 root B / antenna wall; Z = 0 floor skin face, Z up)", source="v3/cad/src/geom_v3f.py"),
        pins=pins, pitch_mm=round(pitch, 3), pitch_note="[S1 C-2] 5.40 mm (was 6.203): the only pitch that keeps >= 0.30 mm PC walls in the "
                                                        "re-laid K corner; non-standard, but a catalogue survey (D-14) is still open, and 5.4 is "
                                                        "close to common 5.0 / 5.5 mm pitches",
        unequal_pins="VBUS dia 1.6, GND dia 2.0 (the head's pins can be sized so a reversed head cannot seat)",
        magnet_code=dict(targets=[dict(name=t["name"], centre_case=list(t["c"]), d_mm=t["d"], t_mm=t["t"], top_z_case=round(Z.rim_top - t["skin"], 3),
                                       material="ferritic stainless (430 class), under a 0.20 mm PC skin") for t in G.TARGETS],
                         magnets="in the head only; no magnet on the wrist [B 1]",
                         offset_under_reversal_mm=round(math.hypot(tr[0] - tg["c"][0], tr[1] - tg["c"][1]), 2),
                         note="[S1 C-2, C-21] the target sits between the counterbores, 0.4 mm off the pin axis: it is the magnet's attach point "
                              "only and no longer a reversal key (ferritic: attracts either pole; a reversed head lands within 0.8 mm of it). "
                              "Reversal is excluded by K1 unequal pins, K2 the window-glass step, K4 the head's electrical pin check"),
        keying=dict(window_glass_step=dict(y_case=G.Y_WIN1, height_mm=round(Z.win1 - Z.rim_top, 3), note=f"the window glass stands {Z.win1 - Z.rim_top:.3f} mm "
                                                                                                          "above the K block and the PV laminate along Y 20.45 (S1 C-10)"),
                    head_footprint_used_case=dict(x=[head["x0"], head["x1"]], y=[head["y0"], head["y1"]], h=head["h"], seat_z=Z.rim_top,
                                                  seat_face_y0=head["seat_y0"], rebate_w_h_mm=list(head["rebate"]),
                                                  rebate_clearance_over_window_glass_mm=round(Z.rim_top + head["rebate"][1] - Z.win1, 3),
                                                  pogo_head_frame=head["pogo_hf"], magnet_head_frame=head["magnet_hf"],
                                                  source="v3/head/head_interface.json housing 28.5 x 15 x 7 mm, re-anchored on the S1 pins"),
                    reversed_head_footprint_case=dict(x=[round(hrot[0], 2), round(hrot[1], 2)], y=[round(hrot[2], 2), round(hrot[3], 2)]),
                    reversed_result="a head turned 180 deg about the pin midpoint would reach Y < 20.45 and sit on the window-glass step: it "
                                    "cannot seat flat, and its pins would land on the wrong pin sizes"),
        K_top_region_case=poly_xy(ktop, "case")[0],
        worn=dict(left="elbow end, ulnar corner; the head body extends from the corner toward +x (the hand) over the pod top and its cable leaves "
                       "the USB-C mouth toward +x, i.e. toward the hand (S1 C-12: the earlier 'over the forearm' was wrong)",
                  right="hand end, ulnar corner (band turned 180 deg); the head body and cable then point toward the elbow",
                  head_while_worn="see out/worn_checks_L<..>.json head: 28.5 x 15 x 7 mm housing (S1 C-12) on 130-200 mm wrists"),
        board_side=dict(J15=board["springs"]["J15"]))


def compare_head(bc):
    if not os.path.exists(HEAD_IF):
        return dict(head_interface_found=False, path=HEAD_IF)
    try:
        h = json.load(open(HEAD_IF))
    except Exception as e:   # noqa: BLE001
        return dict(head_interface_found=True, error=str(e))
    diff = dict(head_interface_found=True, keys_in_head_file=sorted(h.keys()) if isinstance(h, dict) else None)
    def find(d, keys):
        if isinstance(d, dict):
            for k, v in d.items():
                if any(kk in k.lower() for kk in keys):
                    yield k, v
                yield from find(v, keys)
        elif isinstance(d, list):
            for v in d:
                yield from find(v, keys)
    diff["pitch_in_head_file"] = [v for k, v in find(h, ("pitch",))][:5]
    diff["pin_d_in_head_file"] = [(k, v) for k, v in find(h, ("diam", "_d", "dia"))][:10]
    diff["band_pitch_mm"] = bc["pitch_mm"]
    return diff


def main():
    bz = board_zones()
    json.dump(bz, open(os.path.join(OUT, f"board_zones_{TAG}.json"), "w"), indent=1)
    bc = band_contacts(bz)
    bc["head_interface_comparison"] = compare_head(bc)
    json.dump(bc, open(os.path.join(OUT, f"band_contacts_{TAG}.json"), "w"), indent=1)
    if G.IS_PLAIN and int(G.POD_L) == 41:   # [G1] canonical names at the lane root = the 41 x 32 mm base (lead's decision 1); 40 mm is dropped
        root = os.path.join(HERE, "..")
        bz["meta"]["variants"] = ("this file = 41 x 32 mm base (board 38 x 29) = out/board_zones_L41.json; gate-1 options: out/options/board_zones_<tag>.json; "
                                  "the dropped 40 mm outline: v3/cad_s1/board_zones.json")
        bc["meta"]["variants"] = "this file = 41 x 32 mm base = out/band_contacts_L41.json; the dropped 40 mm outline: v3/cad_s1/band_contacts.json (contact geometry identical)"
        json.dump(bz, open(os.path.join(root, "board_zones.json"), "w"), indent=1)
        json.dump(bc, open(os.path.join(root, "band_contacts.json"), "w"), indent=1)
    if not G.IS_PLAIN:                       # [G1] every option's zone file also lands flat in out/options/
        json.dump(bz, open(os.path.join(HERE, "..", "out", "options", f"board_zones_{TAG}.json"), "w"), indent=1)
    print(json.dumps(dict(zones=len(bz["zones"]), pitch=bc["pitch_mm"], head=bc["head_interface_comparison"]), indent=1, default=str))


if __name__ == "__main__":
    main()
