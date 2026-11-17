"""mech_raw.json (mech_v3f.py) -> mech_results.json (verdicts against BASELINE 18 V3-G7 as written; SF 1.5 on pressure / force).
usage: python3 -B make_results.py"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "mech_raw.json")))
S, C1, F1, C2, F2, C3, C4, C6, C7 = (R["stack"], R["case1_pv"], R["case1_fix_bonded_seat_raise"], R["case2_window"], R["case2_fix"], R["case3_capsule"],
                                       R["case4_floor_membrane"], R["case6_drop"], R["case7_flex_hinge"])
crit5 = "contact pressure >= 7.5 bar (SF 1.5) at the max-material gap AND >= 5.0 bar at the case-5 worst-case gap"
cases = [
    dict(case="1 PV laminate 5 bar", criterion=crit5, status="FAIL",
         result=f"as built (0.50, elastic beads): {C1['bead t0.50']['contact_bar']['max_material']} / {C1['bead t0.50']['contact_bar']['wc']} bar; "
                f"bonded 0.50: {C1['bond_pin t0.50']['contact_bar']['max_material']} / 0; bonded 0.60: {C1['bond_pin t0.60']['contact_bar']['max_material']} / 0 (WC gap P1 = {S['P1_PV_lam_to_parts']['wc']})",
         fix=f"structural bond on ring and rib + PV seat +{F1['t0.50']['seat_raise_mm']} mm, glass stays 0.50 (PV half {F1['t0.50']['pv_half_mm']}): "
             f"{F1['t0.50']['contact_bar_max_material']} / {F1['t0.50']['contact_bar_wc']} bar"),
    dict(case="2 window 0.70 5 bar", criterion=crit5, status="FAIL",
         result=f"{C2['t0.70']['contact_bar']['max_material']} / 0 bar (W1 WC gap {S['W1_window_film_to_panel_gap']['wc']}); rail sag {C2['t0.70']['rail_sag_mm_5bar']} mm governs; 0.80 glass: {C2['t0.80']['contact_bar']['max_material']}",
         fix="stainless core in the rail (same 0.4 x 0.855 section) + precision tolerances on W1 + window seat +"
             f"{F2['variants']['rail stainless core 0.4 x 0.855 | t0.70 | precision tolerances']['seat_raise_mm']} mm (window half "
             f"{F2['variants']['rail stainless core 0.4 x 0.855 | t0.70 | precision tolerances']['window_half_mm']})"),
    dict(case="3a capsule 30 N", criterion="cell not loaded: force to touch the cell >= 45 N (SF 1.5)", status="PASS",
         result=f"spread {C3['spread']['force_to_touch_cell_N']} N, thumb {C3['thumb_15mm']['force_to_touch_cell_N']} N, probe {C3['probe_5mm']['force_to_touch_cell_N']} N"),
    dict(case="3b capsule 5 bar", criterion=crit5.split(" AND")[0], status="FAIL", result=f"{C3['5bar']['contact_bar_SS']} bar SS (needs t {C3['5bar']['t_needed_for_SF_mm']})",
         fix=f"capsule top 0.50 mm strengthened glass: {C3['5bar_fix_t0.50']['contact_bar_SS']} bar, capsule 4.6 mm"),
    dict(case="4a floor film over the motor", criterion="motor not pushed into the lid (else the Ti disc)", status="PASS",
         result=f"motor acts as a boss: rise {C4['motor_as_boss_centred']['motor_rise_mm_5bar']}-{C4['motor_as_boss_eccentric_worst']['motor_rise_mm_5bar']} mm, film {C4['motor_as_boss_eccentric_worst']['film_stress_MPa']} MPa; Ti disc not needed"),
    dict(case="4b button membrane", criterion="BASELINE 13.4: switch held pressed is handled by the firmware stuck rule", status="PASS",
         result=f"{C4['membrane']['force_5bar_N']} N at 5 bar > 2.2 N: pressed above {C4['membrane']['bar_at_actuation']} bar"),
    dict(case="5 tolerance stack", criterion="no interference at worst case", status="FAIL",
         result="; ".join(f"{k} WC {v['wc']} / RSS {v['rss']}" for k, v in S.items()),
         fix=f"W1: as case 2; W2: support legs +-0.02 and FH34SRJ 1.0 confirmed as maximum (WC {R['case5_fix_W2']['precision']['wc']}), or raise 0.15 -> 0.21"),
    dict(case="6 1 m drop", criterion="estimate (bench decides): PC lip crush before the glass edge", status="PARTIAL",
         result=f"window straight edge crush {C6['pod_only']['by_angle']['45deg']['window_edge_line_mm']} < {C6['pod_only']['by_angle']['45deg']['window_glass_edge_clear_mm']} mm; "
                f"R6 corner {C6['pod_only']['by_angle']['45deg']['window_corner_R6_mm']} > clear: glass edge reached; capsule corner {C6['capsule_only_2p75g']['by_angle']['45deg']['capsule_corner_R1_mm']} < {C6['capsule_only_2p75g']['by_angle']['45deg']['capsule_glass_edge_clear_mm']}",
         fix=f"PC corner bumpers {C6['corner_bumper_proud_needed_mm_pod_only']} mm proud of the glass at the four window-half R6 corners"),
    dict(case="7 flex at the bar hinge", criterion="no flex crack (10^5 cycles): R >= IPC-2223 100 t, Cu strain <= 0.30 %", status="PASS",
         result=f"wear +-10 deg: R {C7['R_wear_cycle_mm']} mm >= {C7['IPC2223_dynamic_1layer_min_R_mm']}, Cu {C7['cu_strain_amplitude_wear_pct']} %; fit offset +-{C7['fit_offset_deg']} deg: R {C7['R_fit_offset_mm']} mm"),
]
out = dict(gate="V3-G7 (SIM-14, calculation part)", verdict="FAIL", SF=R["inputs"]["SF"], tag=R["inputs"]["tag"], cases=cases,
           decision_case1="bonded support (structural epoxy on the ring and rib seats) is required in every variant; 0.55 / 0.60 glass alone cannot pass "
                          "because the PV worst-case gap is 0.00 mm; keep 0.50 glass and raise the PV seat 0.14 mm (PV half 4.79 <= 5.305)",
           numbers=dict(case1=C1, case1_fix=F1, case2=C2, case2_fix=F2["variants"], case3=C3, case4=C4, case5=S, case5_fix_W2=R["case5_fix_W2"],
                        case6=C6, case7=C7, supports=R["supports"], checks=dict(navier_28p7x12p6_bar=R["check_navier_28p7x12p6"], stage1_window_bar=R["case2_check_stage1_SS_36x14p6"])),
           inputs=R["inputs"], source="v3/sim/mech/mech_v3f.py -> mech_raw.json; make_results.py")
json.dump(out, open(os.path.join(HERE, "mech_results.json"), "w"), indent=1, default=float)
for c in cases: print(c["status"], "|", c["case"], "|", c["result"][:200], "|", c.get("fix", ""))
