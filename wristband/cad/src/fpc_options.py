"""[G1 level 1] Display FPC routing study for the LS011B7DH03 in the V3-F pod (41 x 32 mm base).

What is fixed by the drawing (read 2026-11-14, LD-29Y03 p.36 text and p.42 Figure 14-1 vector coordinates, 5.670 pt/mm):
  length 13.63 +- 0.4 from the glass edge; 9.47 mm wide from the glass edge to 5.63 mm (two R0.6 notches centred 4.11 mm), then a 5.5 +- 0.05 mm
  tail; stiffener 4.5 +- 0.5 mm on the FRONT face (0.3 +- 0.03 total); terminals 3.5 mm long on the REAR face; bend area 0.8-6.0 mm from the
  glass edge; inner R >= 0.45; never toward the front polarizer; <= 3 bends; the FPC must not touch the glass edge.
Consequences used here:
  - only one routing is legal in this pod: one 180 deg fold toward the rear, the tail returning under the panel;
  - after that fold the terminals face the panel (up) and the stiffener faces the board (down);
  - the height of the return run is set at the fold: underside = ledge top - 2 R_in - t.
Model (all E): circular fold over a former nose, or a free fold (elastica between two parallel faces: apex centre-line radius 0.417 x the
centre-line gap, the two-plate bend-test relation sigma = 1.198 E t / (D - t)).
Writes out/options/fpc_options.json and prints the tables.  usage: python3 -B fpc_options.py
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ["V3F_POD_L"] = os.environ.get("V3F_POD_L", "41"); os.environ["V3F_POD_W"] = "32"; os.environ["V3F_OPT"] = ""
import geom_v3f as G   # noqa: E402  (base geometry only; the variants are computed here)
Z = G.Z
OUT = os.path.join(HERE, "..", "out", "options"); os.makedirs(OUT, exist_ok=True)

T = G.FPC["t"]                      # 0.10 E (the drawing shows about 0.064 mm, not dimensioned)
LEDGE = Z.panel0 + 0.115 + 0.25 - Z.pcb1          # FPC underside on the TFT ledge above the board top: 1.365 mm (legs + frame 1.00, bottom Pol + TFT 0.365)
TAPE = 0.05
ELASTICA = 1.0 / (2 * 1.198)       # apex centre-line radius / centre-line gap of a free fold between parallel faces = 0.4174
TOL = dict(legs_frame=0.05, pol_tft=0.05, nose=0.06, fpc_t=0.03, tape=0.01)
TOL_WC = sum(TOL.values()); TOL_RSS = math.sqrt(sum(v * v for v in TOL.values()))
TOL_WC_NO_NOSE = TOL_WC - TOL["nose"]; TOL_RSS_NO_NOSE = math.sqrt(sum(v * v for k, v in TOL.items() if k != "nose"))
CLASSES = [  # body max height from v3/design/parts.json + 0.05 mm solder (BASELINE 8 convention), courtyard on the board today
    ("R0201", 0.26), ("C0201", 0.33), ("R0402", 0.40), ("X1SON / X2DFN", 0.45), ("DFN1006, WLCSP", 0.50), ("C0402, L0402", 0.55),
    ("USON, TDFN, C0402 thick", 0.60), ("SOD-523, LGA-12", 0.70), ("WSON (U10, U15)", 0.80)]
SOLDER = 0.05
SW1_X0 = G.sw1_land()["courtyard"][0]
J11_X0 = G.J11["land"][0] - 1.1


def parts_classes():
    P = G.design_parts(); H = {}
    for r, p in P.items():
        if p["side"] == "F" and p["jlc_placed"]:
            h = p.get("height_max_mm") or 0.0
            H.setdefault(h, [0, 0.0]); H[h][0] += 1; H[h][1] += p["courtyard_area_mm2"]
    return {f"{h:.2f}": dict(n=n, courtyard_mm2=round(a, 2)) for h, (n, a) in sorted(H.items())}


def highest_class(h_allowed):
    ok = [nm for nm, body in CLASSES if body + SOLDER <= h_allowed + 1e-9]
    return ok[-1] if ok else "none"


def routing(fold_at, raise_, former_r=None, t=T, s_rise=0.0):
    """one routing: fold start, panel raise, former nose radius (None = free fold with the return run on the board), FPC thickness,
    optional S-rise of the return run inside the bend area (needs the maker's written consent)"""
    ledge = LEDGE + raise_
    r = dict(fold_start_mm=fold_at, panel_raise_mm=raise_, fpc_t_mm=t, window_half_mm=round(Z.pod_win + raise_, 3))
    if former_r is None:
        dc = ledge - TAPE                              # centre-line gap (exit run on the ledge, return run on the taped board)
        rin_circ = (ledge - TAPE - t) / 2
        rin_free = ELASTICA * dc - t / 2
        rin_free_wc = ELASTICA * (dc - TOL["legs_frame"] - TOL["pol_tft"] - TOL["tape"]) - (t + TOL["fpc_t"]) / 2
        rin_free_rss = ELASTICA * (dc - math.sqrt(TOL["legs_frame"] ** 2 + TOL["pol_tft"] ** 2 + TOL["tape"] ** 2)) - t / 2
        r.update(fold="free fold, return run on the board (0.05 tape)", r_in_circular_mm=round(rin_circ, 3), r_in_free_fold_apex_mm=round(rin_free, 3),
                 r_in_free_fold_worst_mm=round(rin_free_wc, 3), r_in_free_fold_rss_mm=round(rin_free_rss, 3),
                 r_rule_ok_nominal=rin_free >= 0.45, r_rule_ok_worst=rin_free_wc >= 0.45, r_rule_ok_rss=rin_free_rss >= 0.45,
                 return_underside_above_board_mm=TAPE, part_height_allowed_wc_mm=0.0, part_height_allowed_rss_mm=0.0, highest_class_wc="none",
                 highest_class_rss="none")
        rin = rin_circ
    else:
        rin = former_r
        g = ledge - 2 * rin - t + s_rise                # underside of the return run above the board top
        h_wc = g - TAPE - TOL_WC; h_rss = g - TAPE - TOL_RSS
        r.update(fold=f"over a former nose R{former_r:g} +- 0.03", r_in_circular_mm=rin, r_rule_ok_nominal=rin - 0.03 >= 0.45 - 1e-9, r_rule_ok_worst=rin - 0.03 >= 0.45 - 1e-9,
                 s_rise_mm=s_rise, return_underside_above_board_mm=round(g, 3), part_height_allowed_wc_mm=round(h_wc, 3),
                 part_height_allowed_rss_mm=round(h_rss, 3), highest_class_wc=highest_class(h_wc), highest_class_rss=highest_class(h_rss),
                 under_stiffened_end_wc_mm=round(h_wc - 0.20, 3),
                 return_top_below_panel_rear_mm=round((Z.panel0 + raise_ - Z.pcb1) - (g + t), 3))
    arc = math.pi * (rin + t / 2)
    xf = G.FPC_EDGE_X + fold_at
    xo = xf + rin + t
    ret = G.FPC["len"] - fold_at - arc
    wide = max(0.0, G.FPC["wide_len"] - fold_at - arc)
    r.update(arc_mm=round(arc, 3), fold_end_from_glass_mm=round(fold_at + arc, 3), bend_area_ok=(fold_at >= 0.8 - 1e-9 and fold_at + arc <= 6.0 + 1e-9),
             fold_outer_x_case=round(xo, 3), tail_tip_x_case=round(xf - ret, 3), wide_part_end_x_case=round(xf - wide, 3),
             stiffened_end_x_case=[round(xf - ret, 3), round(xf - ret + G.FPC["stiff_len"], 3)],
             footprint_length_mm=round(xo - (xf - ret), 3),
             sw1_courtyard_clearance_mm=round(SW1_X0 - (xo + 0.2), 3), j11_zone_clearance_mm=round(J11_X0 - (xo + 0.2), 3),
             e3_metal_to_fold_note="E3-net metal (tab, J11 finger) to the fold: out/checks_pod_<tag>.json")
    return r


def routing_rear(fold_at, raise_, t=T):
    """[session 2] D: after the fold over the R0.48 former the return run rises in a gentle S inside the bend area and is bonded under the
    panel's rear face (0.05 PSA). The S has a reverse curve, so the routing needs the maker's written consent (Note 8-1-1)."""
    rin = 0.48; psa = 0.05; drop = 0.15; tol = dict(legs_frame=0.05, psa=0.02, fpc_t=0.03, tape=0.01)
    wc = sum(tol.values()); rss = math.sqrt(sum(v * v for v in tol.values()))
    arc = math.pi * (rin + t / 2)
    under_fold = LEDGE + raise_ - 2 * rin - t                    # underside right after the fold
    under_rear = (Z.panel0 - Z.pcb1) + raise_ - psa - t          # underside of the bonded run
    rise = under_rear - under_fold
    run = 6.0 - fold_at - arc                                    # length left inside the bend area for the S
    th = math.atan2(rise, run) * 2                               # two equal arcs: rise = 2 R (1 - cos th), run = 2 R sin th  ->  tan(th / 2) = rise / run
    r_s = run / (2 * math.sin(th))
    h_run_wc = under_rear - TAPE - wc; h_run_rss = under_rear - TAPE - rss
    h_st_wc = h_run_wc - drop - 0.20; h_st_rss = h_run_rss - drop - 0.20
    full_h_len = G.FPC["len"] - 6.0 - G.FPC["stiff_len"] - G.FPC["stiff_tol"] - 0.2 - G.FPC["len_tol"]
    xf = G.FPC_EDGE_X + fold_at
    return dict(fold_start_mm=fold_at, panel_raise_mm=raise_, fpc_t_mm=t, window_half_mm=round(Z.pod_win + raise_, 3),
                fold="over a former nose R0.48 +- 0.03, then an S-rise to the panel rear (0.05 PSA): NEEDS THE MAKER'S WRITTEN CONSENT",
                r_in_circular_mm=rin, s_rise_mm=round(rise, 3), s_run_available_mm=round(run, 3), s_arc_radius_mm=round(r_s, 2), s_arc_angle_deg=round(math.degrees(th), 1),
                return_underside_above_board_mm=round(under_rear, 3), tolerances_mm=tol, tol_worst_mm=round(wc, 3), tol_rss_mm=round(rss, 3),
                part_height_allowed_wc_mm=round(h_run_wc, 3), part_height_allowed_rss_mm=round(h_run_rss, 3),
                highest_class_wc=highest_class(h_run_wc), highest_class_rss=highest_class(h_run_rss),
                under_stiffened_end_wc_mm=round(h_st_wc, 3), under_stiffened_end_rss_mm=round(h_st_rss, 3),
                under_stiffened_end_class_wc=highest_class(h_st_wc), under_stiffened_end_class_rss=highest_class(h_st_rss),
                tail_length_at_full_height_mm=round(full_h_len, 2), arc_mm=round(arc, 3), fold_end_from_glass_mm=round(fold_at + arc, 3),
                bend_area_ok=(fold_at >= 0.8 - 1e-9), fold_outer_x_case=round(xf + rin + t, 3),
                tail_tip_x_case=round(xf - (G.FPC["len"] - fold_at - arc), 3),
                sw1_courtyard_clearance_mm=round(SW1_X0 - (xf + rin + t + 0.2), 3))


def main():
    R = dict(
        date="2026-11-14 (first session); D rows and the re-read of LD-29Y03 on 2026-11-15", pod="41 x 32 mm base (board 38 x 29)",
        sources={
            "LD-29Y03 p.36 (PDF p.38), 8-2 FPC Bend Specification": "bend area 0.8-6.0 mm from the glass edge; minimum inner bend R 0.45; 'Do not bend to the front polarizer "
                                                                   "film side'; bend frequency 3 times or less (180 to 0 deg); FPC not to contact the glass edge, no stress on the "
                                                                   "joint; Table 8-1 recommended connectors: Panasonic AYF531035 (bottom and upper contact), SMK CFP-4510-0150F (upper), "
                                                                   "CFP-4610-0150F (bottom), HRS FH34SRJ-10S-0.5SH (bottom and upper)",
            "LD-29Y03 p.42 (PDF p.44), Figure 14-1, vector coordinates": "glass 32.00 x 14.00; FPC 9.47 wide from the glass edge to 5.63 mm, 2-R0.6 notches centred 4.11 mm, tail 5.49 "
                                                                        "(Detail A 5.5 +- 0.05) to 13.63 +- 0.4; stiffener hatch 4.50 long in the FRONT view; terminals (Detail A, 10 at "
                                                                        "0.5 +- 0.03, 0.35 wide, 3.5 +- 0.3 long) in the REAR view; side view: bottom Pol 0.115 / TFT 0.25 / CF 0.15 / top Pol "
                                                                        "0.23, the FPC on the TFT ledge, its stiffened end 0.33 mm thick toward the FRONT, flexible part drawn 0.064 mm",
            "url": "https://d7rh5s3nxmpy4.cloudfront.net/CMP7377/files/LS011B7DH03_24Nov17_Spec_LD-29Y03.pdf",
            "ZIF height": "search summaries only (2026-11-14 and 2026-11-15): Hirose FH34SRJ series 0.5 mm pitch, 1.0 mm above the board, top and top/bottom "
                          "contact, back flip (RS listing: height 1.00 mm, width 3.8 mm); JLC C324723 exists; Panasonic AYF531035 body height 1.00 mm; Molex 503480 "
                          "and TE 1-2328702-0 1.00 mm; Hirose FH19D 0.93 mm (front actuator, being discontinued); no 0.5 mm pitch part of 0.6-0.8 mm found. The "
                          "Farnell-hosted datasheet timed out twice and the LCSC datasheet page gave only its title: body and land pattern NOT read",
            "motors": "maker pages read through WebFetch on 2026-11-15 (v3/cad/ref/sources.md): VCLP0820B004L 8.0 x 2.1 mm, 30 / 35 mA, 0.25 Grms; VC0720B001F "
                      "7.0 x 2.0 mm, 53 / 85 mA, 0.10 Grms; VC0625B001L 6.0 x 2.5 mm, 42 / 100 mA",
        },
        stack=dict(ledge_top_above_board_mm=round(LEDGE, 3), panel_rear_above_board_mm=round(Z.panel0 - Z.pcb1, 3), tape_mm=TAPE, fpc_t_assumed_mm=T,
                   fpc_t_as_drawn_mm=0.064, tolerances_mm=TOL, tol_worst_mm=round(TOL_WC, 3), tol_rss_mm=round(TOL_RSS, 3),
                   note="E: the panel rests on the support frame, whose legs stand on the board, so the board thickness is not in the chain"),
        terminal_side=dict(
            finding="after the only legal fold (toward the rear) the terminals face the panel and the stiffener faces the board",
            consequence="a board land under the stiffened end (BASELINE 5.1 J13 as drawn in stage 1) cannot be soldered to the terminals",
            joints={
                "bridge": "a 10-trace bridge flex (ours, 0.10 mm, pads on its underside): one end hot-bar soldered on the FPC terminals, the other on the J13 "
                          "land placed beyond the FPC tip; stack at the joint 0.30 + 0.03 + 0.10 = 0.43 mm above the board (limit under the panel 0.75); no panel raise; "
                          "two hot-bar joints; solderability of the terminal finish is not stated by the maker (unknown)",
                "zif": "top-contact ZIF (maker's Table 8-1): 1.0 mm tall under the panel, where the max-material gap is 1.00 mm: clearance = panel raise "
                       "(0.15 mm raise gives BASELINE's 0.15 mm); courtyard about 33.6 mm2 against the land's 13.4; no solder joint on the FPC"},
            pin_order="Detail A numbers the terminals 1 and 10 in the REAR view: the J13 pin order on the board must be proven from the drawing before layout "
                      "(placement-safety item; not resolved in this lane)"),
        parts_on_board_by_body_height=parts_classes(), classes_with_solder={nm: round(b + SOLDER, 2) for nm, b in CLASSES})
    rows = {}
    for raise_ in (0.0, 0.05, 0.10, 0.15):
        rows[f"A  free fold, on the board, fold 1.0, raise {raise_:.2f}"] = routing(1.0, raise_)
    rows["A2 free fold, on the board, fold 0.8, raise 0.00"] = routing(0.8, 0.0)
    rows["A3 free fold, on the board, fold 1.9, raise 0.00"] = routing(1.9, 0.0)
    for raise_ in (0.0, 0.05, 0.10, 0.15):
        rows[f"B  former R0.48, fold 1.0, raise {raise_:.2f}"] = routing(1.0, raise_, 0.48)
    for raise_ in (0.0, 0.05, 0.10, 0.15):
        rows[f"B' former R0.48, fold 1.0, raise {raise_:.2f}, FPC 0.064 mm as drawn"] = routing(1.0, raise_, 0.48, t=0.064)
    for raise_ in (0.0, 0.05, 0.10, 0.15):
        rows[f"C  former R0.48 + S-rise 0.30 inside the bend area (needs the maker's consent), raise {raise_:.2f}"] = routing(1.0, raise_, 0.48, s_rise=0.30)
    for raise_ in (0.0, 0.05, 0.10, 0.15):
        rows[f"D  former R0.48 + S-rise to the panel rear, bonded (needs the maker's consent), raise {raise_:.2f}"] = routing_rear(1.0, raise_)
    R["routings"] = rows
    R["reverified_2026-11-15"] = ("LD-29Y03 p.36 text and Figure 8-2 (the folded FPC is drawn with its stiffened end on the side away from the panel) and p.42 "
                                  "Figure 14-1 vector coordinates were read again from the PDF fetched on 2026-11-13 20:24 UTC from the URL above: wide part "
                                  "53.70 pt = 9.47 mm to 31.92 pt = 5.63 mm from the glass edge; tail 31.14 pt = 5.49 mm; tip 77.28 pt = 13.63 mm; stiffener 25.50 pt = "
                                  "4.50 mm; side view: bottom Pol 0.116 / TFT 0.254 / CF 0.148 / top Pol 0.233 mm, FPC 0.064 mm on the TFT's front face, stiffened end "
                                  "0.328 mm thick toward the FRONT, terminal step 3.50 mm long on the REAR face")
    # panel raise needed for each part class under the flat return run (former R0.48, no S-rise)
    need = {}
    for nm, body in CLASSES[:6]:
        h = body + SOLDER
        base = LEDGE - 2 * 0.48 - T - TAPE
        need[nm] = dict(height_with_solder_mm=round(h, 2), raise_needed_worst_mm=round(max(0.0, h - (base - TOL_WC)), 3),
                        raise_needed_rss_mm=round(max(0.0, h - (base - TOL_RSS)), 3),
                        raise_needed_worst_fpc_0p064_mm=round(max(0.0, h - (base + T - 0.064 - TOL_WC)), 3))
    R["panel_raise_needed_per_class"] = need
    R["zif_under_panel"] = {f"raise {d:.2f}": dict(clearance_over_1p0_connector_mm=round(Z.panel0 + d - Z.pcb1 - 1.0, 3)) for d in (0.0, 0.05, 0.10, 0.15)}
    R["low_zone_under_panel"] = {f"raise {d:.2f}": dict(h_max_mm=round(Z.parts_low - Z.pcb1 + d, 2), body_max_mm=round(Z.parts_low - Z.pcb1 + d - SOLDER, 2),
                                                         newly_allowed=[nm for nm, b in CLASSES if (Z.parts_low - Z.pcb1) - SOLDER < b <= Z.parts_low - Z.pcb1 + d - SOLDER + 1e-9])
                                 for d in (0.0, 0.05, 0.10, 0.15)}
    R["head_rebate_over_window_glass"] = {f"raise {d:.2f}": round(Z.rim_top + G.HEAD["rebate"][1] - (Z.win1 + d), 3) for d in (0.0, 0.05, 0.10, 0.15)}
    R["assembly"] = dict(
        common=["1 reflow the board (JLC); the panel-support frame with its legs (and the fold former nose, if used) is placed on the board",
                "2 the board lies outside the ring; the panel lies FACE DOWN beside the board's hand end, its FPC flat, terminals up"],
        bridge=["3 hot-bar the bridge flex onto the FPC terminals (the only solder operation on the maker's FPC: soldered once)",
                "4 lay the FPC tail on the taped board, hot-bar the bridge's free end onto J13 (beyond the tail tip), insulate with tape",
                "5 swing the panel over the fold (one 180 deg bend, bend count 1 of 3) onto the support frame; the fold forms 1.0 mm from the glass edge",
                "6 floor assembly (floor film, plates, board, panel) enters the ring from below; ring-to-floor bond; front-light tail to J16; lid tail to J6",
                "7 lid closing: window glass with frame and film onto the rail, the rib insert and the ring seat; PV laminate onto the rib and ring"],
        zif=["3 open the ZIF flap, insert the stiffened FPC end (terminals up, top contact), close the flap; no solder on the FPC",
             "4 swing the panel over the fold onto the support frame (bend count 1 of 3; the FPC can be released and re-seated: rework possible)",
             "5-6 as steps 6-7 of the bridge sequence"],
        note="E: sequence proposed by this lane; the stage-1 sequence (FPC end soldered to a land under it) does not exist physically")
    json.dump(R, open(os.path.join(OUT, "fpc_options.json"), "w"), indent=1)
    print(f"ledge top above the board {LEDGE:.3f} mm; tolerance worst {TOL_WC:.2f} / RSS {TOL_RSS:.3f} mm")
    print(f"{'routing':86s} R_in  free-apex(nom/wc)  under  h_wc   h_rss  class_wc      class_rss     SW1clr  tip_x  win-half")
    for k, r in rows.items():
        print(f"{k:86s} {r['r_in_circular_mm']:.3f} "
              f"{str(r.get('r_in_free_fold_apex_mm', '-')):>6s}/{str(r.get('r_in_free_fold_worst_mm', '-')):<6s}      "
              f"{r['return_underside_above_board_mm']:.3f}  {r['part_height_allowed_wc_mm']:6.3f} {r['part_height_allowed_rss_mm']:6.3f}  "
              f"{r['highest_class_wc']:13s} {r['highest_class_rss']:13s} {r['sw1_courtyard_clearance_mm']:6.2f} {r['tail_tip_x_case']:6.2f} {r['window_half_mm']:.3f}"
              + (f"  | stiffened end {r['under_stiffened_end_wc_mm']:.3f} ({r['under_stiffened_end_class_wc']}), S R{r['s_arc_radius_mm']} x {r['s_arc_angle_deg']} deg, "
                 f"full height on {r['tail_length_at_full_height_mm']} mm of tail" if "s_arc_radius_mm" in r else ""))
    print(json.dumps(R["panel_raise_needed_per_class"], indent=1))
    print(json.dumps(R["zif_under_panel"]), json.dumps(R["low_zone_under_panel"]), json.dumps(R["head_rebate_over_window_glass"]))


if __name__ == "__main__":
    main()
