"""V3-F masses and volumes from the CAD model against BASELINE 10 (pod) and the strap lines.
Reads out/checks_pod_L<..>.json (pod part masses from CAD volumes) and builds the strap parts of worn_v3f at 165 mm.
CAD volumes are max-material (BASELINE 8 stack); the board mass uses the 1.0 mm nominal thickness. Writes out/mass_L<..>.json"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import geom_v3f as G                                       # noqa: E402
from shapely.geometry import box as sbox                   # noqa: E402
OUT = G.OUT_DIR
TAG = G.TAG
Z = G.Z

B10_POD = {  # BASELINE 10, typical g (source note)
    "top: PV laminate + window + panel + support frame": 2.83, "PCBA (6L 1.0 mm + parts)": 3.32, "ring walls 1.0 mm + strap bars": 0.83,
    "floor: PC film, Ti plates, carrier film": 0.97, "E3 strip and tab": 0.15, "optical cap": 0.08, "contact pins, spring fingers, ferritic targets": 0.10,
    "adhesives, vent, posts, tails": 0.28, "front-light film + LED": 0.05, "ERM net of the board removed": 0.30,
    "button, membrane, ship-wake parts": 0.10, "O-2 inhibit parts": 0.01, "stainless rib insert + 6 posts": 0.12,
    "window glass 0.70 instead of 0.50 mm": 0.25}
B10_POD_TOTAL = (9.38, 9.73)
B10_STRAP = {"textile band": (5.50, 6.00), "root A: textile replaced": (-0.26, -0.26), "root A: capsule shell PC": (0.66, 0.66),
             "root A: cell GEB301030": (1.40, 1.80), "root A: PCM, F1, NTC, leads, flex": (0.11, 0.11), "root A: TPU in the bar hinge": (0.21, 0.21),
             "root A: capsule glass top (net of PC)": (0.24, 0.50), "root B: textile replaced": (-0.26, -0.26), "root B: TPU core": (0.81, 0.81),
             "root B: wing laminate": (1.41, 1.41), "quick release at both root ends": (0.10, 0.30)}
B10_STRAP_TOTAL = (9.90, 11.26)
RHO_PCB = 2.63e-3   # g/mm3 for a 1.0 mm 6-layer board incl. copper (REDESIGN 5.4: 2.63 mg/mm2)


def main():
    ck = json.load(open(os.path.join(OUT, f"checks_pod_{TAG}.json")))
    m = {k: v["g"] for k, v in ck["mass_g"].items()}
    vol = {k: v["brep_mm3"] for k, v in ck["volumes"].items()}
    board_area_full = G.board_outline().area
    parts_g = round(3.32 - board_area_full * 1.0 * RHO_PCB, 3)      # BASELINE PCBA line less a full uncut board = parts (stage-1 convention:
    #   the PCBA line is 3.32 g at every board size). [G1] board_scaled below adds the board area beyond BASELINE's 37 x 29 mm at 2.63 mg/mm2
    board_area_b10 = G.rrect(1.5, 1.5, 38.5, 30.5, 4.5).area
    board_extra_g = round((board_area_full - board_area_b10) * RHO_PCB, 3)
    cut_area = (G.motor_cut_poly().intersection(G.board_outline()).area if G.HAS_MOTOR else 0.0)
    m.setdefault("motor_ERM", 0.0); m.setdefault("motor_psa", 0.0)
    if G.HAS_MOTOR:
        m["motor_ERM"] = G.MOTOR["g"]
    lines = {
        "top: PV laminate + window + panel + support frame": sum(m[k] for k in ("window_glass", "pv_glass", "pv_encapsulant", "pv_flex", "panel_LS011B7DH03", "panel_support"))
                                                             + sum(v for k, v in m.items() if k.startswith("pv_cell_")),
        "window frame, stainless 0.25 mm (not in BASELINE)": m["window_frame_ss"],
        "PCBA (6L 1.0 mm + parts)": round(board_area_full * RHO_PCB + parts_g, 3),
        "ring walls 1.0 mm + strap bars": m["ring_pc"] + m["bar_A_ss"] + m["bar_B_ss"],
        "floor: PC film, Ti plates, carrier film": m["floor_film"] + m["plate_E1"] + m["plate_E2"] + m["carrier_film"],
        "E3 strip and tab": m["E3_strip_ti"] + m["E3_tab_ti"], "optical cap": m["optical_cap"],
        "contact pins, spring fingers, ferritic targets": m["pin_VBUS"] + m["pin_GND"] + m["target_1"] + m["J15_finger"] + m["J18_finger"] + m["J11_finger"],
        "adhesives, vent, posts, tails": m["bead_pv"] + m["bead_window"] + m["bead_antenna_corner"] + m["slot_A_potting"] + m["slot_B_potting"]
                                         + m["panel_FPC"] + m["FPC_stiffener"] + m["motor_psa"] + m["bond_window_rib"] + m["bond_window_rail"] + m["pv_flex_tail"],
        "window rail GF-LCP on 9 posts (stage 1 C-1; not in BASELINE)": m["window_rail_lcp"],
        "front-light film + LED": m["frontlight_film"] + 0.01,
        "ERM net of the board removed": round(m["motor_ERM"] - cut_area * 1.0 * RHO_PCB, 3),
        "button, membrane, ship-wake parts": m["SW1_body"] + m["membrane_tpe"] + 0.01,
        "O-2 inhibit parts": 0.01,
        "stainless rib insert + 6 posts": m["rib_insert_ss"] + m["rib_posts_ss"],
        "rib PC body (lid RFQ part; not a separate BASELINE line)": m["rib_pc"],
    }
    if G.S2B:   # [S2b] new parts
        lines["[S2b] stainless window-rail section (M-2)"] = m["window_rail_ss"]
        lines["[S2b] PC corner bumpers (M-5)"] = m["corner_bumpers_pc"]
        lines["[S2b] frame ground finger + tab (E-1)"] = m["frame_gnd_finger"] + m["frame_gnd_tab_ss"]
    lines = {k: round(v, 3) for k, v in lines.items()}
    pod_cad = round(sum(lines.values()), 2)
    # BASELINE's top line + the window delta cover the same items as the CAD 'top' line
    cmp_pod = {k: dict(cad_g=v, baseline_g=(B10_POD.get(k) if k != "top: PV laminate + window + panel + support frame" else round(B10_POD[k] + B10_POD["window glass 0.70 instead of 0.50 mm"], 2)))
               for k, v in lines.items()}
    # ---------------- strap (165 mm wrist) from the worn model
    import worn_v3f as W
    p, it = W.items_for(165.0)
    cap = W.capsule_parts(p); wng = W.wing_parts(p)
    rho = dict(pc=1.20e-3, glass=2.50e-3, tpu=1.20e-3, lam=1.90e-3, si=2.33e-3, band=0.55e-3)
    shell_g = cap["capsule_shell_pc"].volume * rho["pc"]
    glass_g = cap["capsule_glass_top"].volume * rho["glass"]
    glass_net_g = glass_g - cap["capsule_glass_top"].volume * rho["pc"]
    hinge_g = 2 * it["rootA_hinge"].area * 35.0 * rho["tpu"]
    ends_g = (it["rootA_end"].area + it["rootB_end"].area) * 35.0 * rho["tpu"]
    core_g = wng["wing_core_tpu"].volume * rho["tpu"]
    lam_g = wng["wing_laminate"].volume * rho["lam"] + sum(wng[f"wing_cell_{i}"].volume for i in range(1, 5)) * rho["si"]
    band_vol = (it["band_A"].area + it["band_B"].area) * G.BAND["w"]
    strap = {"capsule shell PC (CAD)": round(shell_g, 3), "capsule glass top gross / net of PC (CAD)": (round(glass_g, 3), round(glass_net_g, 3)),
             "cell GEB301030 (BASELINE, not modelled by mass)": (1.40, 1.80), "PCM, F1, NTC, leads, flex (BASELINE)": 0.11,
             "TPU hinges s 0-2 mm, both roots (CAD, 1.2 g/cm3)": round(hinge_g, 3), "TPU root ends s 13.7/13.9-16 mm, both roots (CAD)": round(ends_g, 3),
             "wing TPU core (CAD)": round(core_g, 3), "wing laminate (CAD, 1.9 g/cm3 + Si)": round(lam_g, 3),
             "textile band 22 x 1.5 mm worn on 165 mm (CAD volume mm3; mass at 0.55 g/cm3)": (round(band_vol, 1), round(band_vol * rho["band"], 2))}
    out = dict(pod_L=G.POD_L, pod_W=G.POD_W, tag=G.TAG, pod_lines_g=cmp_pod, pod_cad_total_g=pod_cad, pod_baseline_total_g=B10_POD_TOTAL,
               pod_delta_vs_baseline_typ_g=round(pod_cad - B10_POD_TOTAL[0], 2),
               pod_delta_vs_baseline_max_g=round(pod_cad - B10_POD_TOTAL[1], 2),   # [S1 C-13] CAD volumes are max-material: compare with the MAX
               pcba_line_note="COPIED: the PCBA line is BASELINE's 3.32 g by construction (board area x 2.63 mg/mm2 + BASELINE's parts); D10_led and "
                              "the other modelled board parts are inside it and not added again [S1 C-13]",
               parts_on_pcba_g_from_baseline=parts_g,
               strap_165mm=strap, strap_baseline_lines_g=B10_STRAP, strap_baseline_total_g=B10_STRAP_TOTAL,
               notes=["CAD masses are max-material volumes x handbook densities (E); panel 0.73 g max (DS), motor 0.45 g (BASELINE E)",
                      "the CAD adds a 0.25 mm stainless window frame and the rib PC body, which BASELINE 10 does not list",
                      "the board mass uses the 1.0 mm nominal thickness; parts on the PCBA are BASELINE's (3.32 g less a full uncut board)"])
    # ---------------- volumes
    oa = G.case_outline()
    win = oa.intersection(sbox(-1, -1, G.X_LID1, G.Y_WIN1)).area
    rest = oa.area - win
    env = win * Z.win1 + rest * Z.pv1 + 11 * 7 * 0.8 + 2 * 35 * G.BAR_OUT * Z.pv_seat
    out["board_extra_vs_37x29_g"] = board_extra_g
    out["pod_cad_total_board_scaled_g"] = round(pod_cad + board_extra_g, 2)      # [G1] use this one to compare outlines
    out["worn_mass_g_cad_pod_board_scaled_plus_baseline_strap_typ"] = round(pod_cad + board_extra_g + B10_STRAP_TOTAL[0], 2)
    out["volumes"] = dict(case_outline_mm2=round(oa.area, 1), envelope_mm3_without_mesa=round(win * Z.win1 + rest * Z.pv1, 1),
                          envelope_mm3_with_mesa_and_lugs=round(env, 1), solid_material_mm3=round(sum(vol.values()) - vol.get("parts_envelope", 0), 1),
                          parts_envelope_mm3=vol.get("parts_envelope"), capsule_outer_mm3=round(cap["capsule_shell_pc"].volume + cap["capsule_glass_top"].volume
                                                                                              + cap["capsule_cell"].volume + cap["capsule_pcm"].volume, 1),
                          capsule_box_mm3=round(G.CAPSULE["L"] * G.CAPSULE["w"] * G.CAPSULE["t"], 1))
    json.dump(out, open(os.path.join(OUT, f"mass_{TAG}.json"), "w"), indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
