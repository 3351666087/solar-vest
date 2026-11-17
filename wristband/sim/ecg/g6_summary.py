"""Collects results/*.json of the V3-G6 lane into ecg_results.json (verdicts as in ECG.md)."""
import json, pathlib
H = pathlib.Path(__file__).resolve().parent; L = lambda n: json.loads((H / "results" / n).read_text())
D, F, E, C, CC = L("g6_display.json"), L("g6_patient_dc.json"), L("g6_esd.json"), L("g6_calc.json"), L("com_caps.json")
iv = lambda c: max(max(v[f]["inband_uVpp"] + v[f]["alias_uVpp"] for f in v if f != "edge_step_pp_uV") for e, v in c["per_electrode"].items() if e.startswith("in-vivo"))
disp = {k: dict(C_finger_pF=c["C_finger_pF"], C_e3_pF=c["C_e3_pF"], nominal30_uVpp=c["per_electrode"]["in-vivo nominal (E3 0.75 cm2)"]["30 Hz (EXTCOMIN 60 Hz)"]["inband_uVpp"],
                worst_invivo_uVpp=iv(c), worst_arch_uVpp=c["worst_any_fcom_uVpp"]) for k, c in D["cases"].items()}
esd = {c["case"]: c for c in E["cases"]}
out = dict(gate="V3-G6 (SIM-06 / SIM-07 / SIM-08), V3-F variant v3f, 41 x 34 mm pod", date="2026-11-15",
           display=dict(cases=disp, floor_input_short_uVpp=D["floor_uVpp"], budget_uVpp=D["budget_uVpp"], sensitivity=D["sensitivity_3V_square_per_pF"],
                        sim06=D["sim06_vdd_disp"], strap=D["strap"]),
           patient_dc=dict(worst_by_class_uA=F["worst_by_class_uA"], worst_case_by_class=F["worst_case_by_class"]),
           ac_leakage=C["ac_leakage"], vbus_lockout=C["vbus_lockout"], reversed_head=C["reversed_head"], root_short=C["root_short"], esd=esd,
           verdicts=json.loads((H / "verdicts.json").read_text()))
# [S2b ECO] the pre-ECO sections stay as "before"; the ECO re-check is added as "after" (results/eco/)
LE = lambda n: json.loads((H / "results" / "eco" / n).read_text())
DE, FE, EE, CE, NE = LE("g6_display_680k.json"), LE("g6_patient_dc_eco.json"), LE("g6_esd_eco.json"), LE("g6_calc_eco.json"), LE("g6_eco_noise.json")
before = {k: out.pop(k) for k in ("display", "patient_dc", "reversed_head", "esd")}
before["note"] = "first run 2026-11-15, as built before the stage-2b ECO (330 k chains, frame floating, J18 = GND, D14 NSR0240)"
dispe = {k: dict(C_finger_pF=c["C_finger_pF"], C_e3_pF=c["C_e3_pF"], nominal30_uVpp=c["per_electrode"]["in-vivo nominal (E3 0.75 cm2)"]["30 Hz (EXTCOMIN 60 Hz)"]["inband_uVpp"],
                 worst_invivo_uVpp=iv(c), worst_arch_uVpp=c["worst_any_fcom_uVpp"]) for k, c in DE["cases"].items()}
after = dict(note="stage-2b ECO as built in v3/design (2 x 680 k, J19 frame GND, Q20 + D15 on J18, D14 PMEG10020AELR, D16 clamp, D18 + R511 on BTN)",
             display=dict(cases=dispe, floor_input_short_uVpp=DE["floor_uVpp"], budget_uVpp=DE["budget_uVpp"]),
             noise_invivo={k: NE[k] for k in ("2 x 330 k", "2 x 680 k")}, input_short_uVpp=NE["input_short_uVpp"],
             patient_dc=dict(worst_by_class_uA=FE["worst_by_class_uA"], worst_case_by_class=FE["worst_case_by_class"], r_gate_ohm=FE["r_gate_ohm"]),
             reversed_head=CE, esd={c["case"]: c for c in EE["cases"]}, pmeg_fit=EE["pmeg_fit"])
out["before"] = before; out["after"] = after
# [mini-ECO, LEAD_NOTES 2f F-1..F-3] D15 = TPD1E10B06, chains 2 x 330 k; results/mini/ (g6_*_mini.py)
LM = lambda n: json.loads((H / "results" / "mini" / n).read_text())
DM, FM, EM, CM, NM = LM("g6_display_330k.json"), LM("g6_patient_dc_mini.json"), LM("g6_esd_mini.json"), LM("g6_calc_mini.json"), LM("g6_noise_mini.json")
dispm = {k: dict(C_finger_pF=c["C_finger_pF"], C_e3_pF=c["C_e3_pF"], nominal30_uVpp=c["per_electrode"]["in-vivo nominal (E3 0.75 cm2)"]["30 Hz (EXTCOMIN 60 Hz)"]["inband_uVpp"],
                 worst_invivo_uVpp=iv(c), worst_arch_uVpp=c["worst_any_fcom_uVpp"]) for k, c in DM["cases"].items()}
out["after_mini"] = dict(note="mini-ECO as built in v3/design: D15 TPD1E10B06 (C48260) on J18, R301-R306 2 x 330 k anti-surge (E-3 withdrawn); "
                              "patient DC against F-3: <= 10 uA normal, <= 50 uA single fault",
                         display=dict(cases=dispm, floor_input_short_uVpp=DM["floor_uVpp"], budget_uVpp=DM["budget_uVpp"]),
                         noise_invivo=NM["2 x 330 k"], input_short_uVpp=NM["input_short_uVpp"],
                         patient_dc=dict(worst_by_class_uA=FM["worst_by_class_uA"], worst_case_by_class=FM["worst_case_by_class"], normal_limit_uA=10, sfc_limit_uA=50),
                         reversed_head=CM, esd_j18={c["case"]: c for c in EM["cases"]})
# [stage 2c, LEAD_NOTES 2g F-8] Q20 = CJBA7002K 60 V (IDSS <= 100 nA); results/s2c/ (g6_*_s2c.py)
LS = lambda n: json.loads((H / "results" / "s2c" / n).read_text())
FS, ES, CS = LS("g6_patient_dc_s2c.json"), LS("g6_esd_s2c.json"), LS("g6_calc_s2c.json")
out["after_s2c"] = dict(note="stage 2c as built in v3/design: Q20 CJBA7002K (C504101, 60 V, IDSS <= 100 nA), D15 TPD1E10B06 on J18; everything else as after_mini",
                        patient_dc=dict(worst_by_class_uA=FS["worst_by_class_uA"], worst_case_by_class=FS["worst_case_by_class"], normal_limit_uA=10, sfc_limit_uA=50),
                        reversed_head=CS, esd_j18={c["case"]: c for c in ES["cases"]})
(H / "ecg_results.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print("ecg_results.json written:", len(out["verdicts"]), "verdict rows")
