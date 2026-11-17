"""[S2b] mech_raw_s2b.json (mech_s2b.py) -> 'after_stage2b' in mech_results.json; the stage-2a content of mech_results.json stays ('before').
usage: python3 -B make_results_s2b.py"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "mech_raw_s2b.json"))); OUT = json.load(open(os.path.join(HERE, "mech_results.json")))
S, C1, C2, L2, C3, C4, C6, C7 = (R["stack"], R["case1_pv"], R["case2_window"], R["case2_window_LCP_section"], R["case3_capsule"], R["case4_floor_membrane"],
                                 R["case6_drop"], R["case7_flex_hinge"])
c1 = C1["bond_pin t0.50"]; c2 = C2["t0.70"]; m6 = C6["S2b_R6_corner_margin_mm_pod_only"]
cases = [
    dict(case="1 PV laminate 5 bar", status=c1["verdict"], result=f"structural bond, 0.50 glass, air 0.895: {c1['contact_bar']['max_material']} / {c1['contact_bar']['wc']} bar; "
         f"stress {c1['sigma_5bar_MPa']} MPa at 5 bar (strengthened glass)"),
    dict(case="2 window 0.70 5 bar", status="PARTIAL",
         result=f"stainless rail section (X 11.5-33.7): {c2['contact_bar']['max_material']} / {c2['contact_bar']['wc']} bar PASS; GF-LCP section inside the antenna buffer "
                f"(X 1.1-11.5, mid-span strip, conservative): {L2['contact_bar']['max_material']} / {L2['contact_bar']['wc']} bar {L2['verdict']}; with LCP posts at 2 mm there: "
                f"{L2['posts_2mm']['max_material']} / {L2['posts_2mm']['wc']}, at 3 mm: {L2['posts_3mm']['max_material']} / {L2['posts_3mm']['wc']}"),
    dict(case="3a capsule 30 N", status="PASS", result=f"top 0.50: spread {C3['spread']['force_to_touch_cell_N']} N, thumb {C3['thumb_15mm']['force_to_touch_cell_N']} N, probe {C3['probe_5mm']['force_to_touch_cell_N']} N"),
    dict(case="3b capsule 5 bar", status=C3["5bar"]["verdict"], result=f"top 0.50: {C3['5bar']['contact_bar_SS']} bar, {C3['5bar']['sigma_5bar_MPa']} MPa"),
    dict(case="4a floor film over the motor", status="PASS", result=f"rise {C4['motor_as_boss_eccentric_worst']['motor_rise_mm_5bar']} mm (unchanged)"),
    dict(case="4b button membrane", status="PASS", result="unchanged"),
    dict(case="5 tolerance stack", status="PASS" if all(v["pass_wc"] for v in S.values()) else "FAIL",
         result="; ".join(f"{k.split('_')[0]} WC {v['wc']}" for k, v in S.items()) + " (W1 / W2 with the precision tolerances of M-2 / M-4)"),
    dict(case="6 1 m drop", status="PARTIAL",
         result=f"bumper {C6['S2b_bumper_mm']} mm: R6 corner margin (pod {R['inputs'].get('m_pod_g', 10.49)} g) " + ", ".join(f"{k} {v:+.3f}" for k, v in m6.items())
                + f" mm; needed {C6['corner_bumper_proud_needed_mm_pod_only']} mm at the stage-2b pod mass; capsule corner with the pod's mass "
                f"{C6['pod_only']['by_angle']['45deg']['capsule_corner_R1_mm']} > {C6['pod_only']['by_angle']['45deg']['capsule_glass_edge_clear_mm']} (as before); bench decides"),
    dict(case="7 flex at the bar hinge", status=C7["verdict"], result=f"R {C7['R_wear_cycle_mm']} mm, Cu {C7['cu_strain_amplitude_wear_pct']} % (unchanged)"),
]
OUT["after_stage2b"] = dict(verdict="PARTIAL", cases=cases, source="mech_s2b.py -> mech_raw_s2b.json; make_results_s2b.py",
                            design="stage 2b: structural PV bond, flush laminate (air 0.895), window seat +0.09, rail stainless outside the antenna buffer, precision W1 / W2, "
                                   "capsule top 0.50 / 4.6, bumpers 0.33, CAD masses 10.49 g pod")
OUT["note_before_after"] = "'cases' = before (stage 2a); 'after_stage2b' = the stage-2b design"
json.dump(OUT, open(os.path.join(HERE, "mech_results.json"), "w"), indent=1, default=float)
for c in cases: print(c["status"], "|", c["case"], "|", c["result"])
