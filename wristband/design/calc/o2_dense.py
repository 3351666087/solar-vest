#!/usr/bin/env python3
"""Gate-1 level 0: the O-2 hardware PV-charge inhibit on less board area (BASELINE.md 13.2, 15 G-22, 18 V3-G4; v3/g1/dense/DENSE.md section 4).

What is compared (areas from design/parts.json and design_s1/parts.json, F.CrtYd boxes):
  s1      stage-1 circuit as built (16 parts, R174 0402)                                  frozen in v3/design_s1
  std     SB_O2=std (baseline): the same circuit, R174 in 0201                          src/o2.py
  merged  SB_O2=merged (option): one gate FET; Q16 driven by the heartbeat (C175 1 nF) and, through R175 100 k, by U20; Q17 removed;
          R146 (CHG_DIS pull-down, charger.py) 1 M -> 10 k                               src/o2.py
  pack    SB_O2=pack: no O-2 on the board, cut-off in the pack PCM (ABLIC S-82D1A class) BASELINE 5.3 reserve 3
Unchanged in std and merged, so NOT recomputed here but re-run today from calc/o2_inhibit.py (-> o2_inhibit.json): the ladder R116, the chain
R170-R172, U19 / U20, Q18, D19, C170, i.e. the window corners, the approval light, the TS window, the MCU reading, the D-4 / D-11 / D-15 items.
This script computes what the two changes touch: the hold with R174 in 0201, the gate drive of the merged FET, the heartbeat through the larger
C175, the two side effects of the merge (edge injected into CHG_DIS / Q10, current into the output of the unpowered U20) and the PCM coverage.
Marks: every number here is a calculation (model output) from the datasheet values quoted with their page; nothing was simulated or measured.
run: python3 -B o2_dense.py     (reads o2_inhibit.json, ../parts.json, ../../design_s1/parts.json)
"""
import itertools, json, math, os, time
HERE = os.path.dirname(os.path.abspath(__file__)); DESIGN = os.path.dirname(HERE); V3 = os.path.dirname(DESIGN)
S0 = json.load(open(os.path.join(HERE, "o2_inhibit.json")))
PJ = json.load(open(os.path.join(DESIGN, "parts.json")))["variants"]
PS1 = json.load(open(os.path.join(V3, "design_s1", "parts.json")))["variants"]["v3f"]["parts"]
R = {}
O2_REFS = ("Q14", "R174", "C174", "Q16", "C175", "R176", "Q17", "R175", "Q18", "D19", "C170", "R170", "R171", "R172", "U19", "U20")

# ------------------------------------------------------------------ datasheet values
PMZ290 = dict(Vth=(0.45, 0.70, 0.95), Ciss=46e-12, Qgd=0.1e-9)     # PMZ290UNE2 p.6: VGSth 0.45 / 0.70 / 0.95 V at 250 uA; Ciss, Qgd as calc/o2_inhibit.py (E)
PMZ350 = dict(Vth=(0.45, 0.70, 0.95))                              # PMZ350UPE p.6 Table 7
TLV7031 = dict(Vmin=1.6, VOH_drop_3mA=0.35, VOUT_abs_max_over_VCC=0.3)   # SLVSE13 p.8: VOH 4.65 V min at 5 V / 3 mA; p.6: OUT (TLV703x) VEE - 0.3 .. VCC + 0.3 V; p.17: POR holds OUT low
VDD = (1.80, 1.859, 1.90)                                          # MCU rail (BQ25570 buck 1.859 V nominal)
TOL = 0.01                                                         # 1 % resistors (UNI-ROYAL 0201WMF)
NTC = dict(R25=10e3, B=3950.0)
def Rntc(T): return NTC["R25"] * math.exp(NTC["B"] * (1.0 / (T + 273.15) - 1.0 / 298.15))
SUBTH = 0.09                                                       # V per decade below threshold (E, as calc/o2_inhibit.py D-11)
def id_sub(vgs, vth): return 250e-6 * 10 ** ((vgs - vth) / SUBTH) if vgs < vth else 250e-6

# ------------------------------------------------------------------ 1. parts and area
def o2_area(parts):
    it = {r: parts[r] for r in O2_REFS if r in parts and parts[r]["jlc_placed"]}
    return dict(parts=len(it), courtyard_mm2=round(sum(p["courtyard_area_mm2"] for p in it.values()), 2),
                items={r: [p["value"][:40], p["courtyard_area_mm2"]] for r, p in it.items()})
area = dict(s1=o2_area(PS1), std=o2_area(PJ["v3f"]["parts"]))
if "v3f_o2m" in PJ: area["merged"] = o2_area(PJ["v3f_o2m"]["parts"])
if "v3f_o2pack" in PJ: area["pack"] = o2_area(PJ["v3f_o2pack"]["parts"])
R["area"] = dict(reserve_mm2=12.0, options=area,
                 verdict="no board design that keeps every O-2 requirement reaches 12 mm2: " + ", ".join(f"{k} {v['courtyard_mm2']} mm2 ({v['parts']} parts)" for k, v in area.items()),
                 floor_mm2=dict(note="smallest parts the function needs, all 0201 / SOT883 / X2SON: series switch Q14 1.95 + hold R174 0.70 + C174 0.78; heartbeat FET 2.02 + C175 0.78 + R176 0.70; "
                                     "window U19 + U20 4.78 + chain 2.11 + C170 0.78; supply gate Q18 1.95 + OR D19 2.02; approval path 0.70 (merged) or 2.73 (Q17 + R175)",
                                merged=round(1.95 + 0.70 + 0.78 + 2.02 + 0.78 + 0.70 + 4.78 + 2.11 + 0.78 + 1.95 + 2.02 + 0.70, 2)))

# ------------------------------------------------------------------ 2. std: R174 in 0201 (C423797, 10 M 1 %, 1/20 W, 25 V)
C174, R174 = 100e-9, 10e6
tau = R174 * C174
R["std_R174_0201"] = dict(
    hold_tau_s=tau, hold_s=dict(Vth_min_VGS0_2p4=round(tau * math.log(2.4 / 0.45), 2), Vth_max_VGS0_1p8=round(tau * math.log(1.8 / 0.95), 2)),
    same_as_stage1=S0["timing"]["hold"],
    leakage_direction="a leak across R174 (gate to source) lowers the gate-source resistance: the hold gets shorter and Q14 opens earlier (fail-safe). A leak from O2_G to GND would hold "
                      "Q14 on; it does not depend on the resistor's case size (netclass MOHM_KEEPOUT keeps 0.30 mm to other nets). With 1 GOhm across the 0201 body the hold shortens by 1 %.",
    rating="voltage across R174 <= PV open-circuit voltage (3.0 V) against 25 V working; power 3.0^2 / 10 M = 0.9 uW against 50 mW (UNI-ROYAL datasheet V.9 p.4-5)")

# ------------------------------------------------------------------ 3. merged: one gate FET
C175, R175, R176 = 1e-9, 100e3, 1e6
CISS = PMZ290["Ciss"]
# 3.1 approval: O2_HB = V_O2 x R176 / (R175 + R176), U20 sourcing V_O2 / (R175 + R176)
appr = {}
for V in (1.6, 2.0, 2.6, 3.0):
    lo = V * (R176 * (1 - TOL)) / (R175 * (1 + TOL) + R176 * (1 - TOL)); hi = V * (R176 * (1 + TOL)) / (R175 * (1 - TOL) + R176 * (1 + TOL))
    appr[f"V_O2 {V} V"] = dict(O2_HB_V=[round(lo, 3), round(hi, 3)], margin_to_Vth_max_V=round(lo - PMZ290["Vth"][2], 3), U20_load_uA=round(V / (R175 + R176) * 1e6, 2))
R["merged_approval"] = dict(divider=round(R176 / (R175 + R176), 4), by_V_O2=appr,
    stage1_load_uA_at_2V=round(2.0 / 1e6 * 1e6, 2),
    note="U20 is push-pull (TLV7031): at 1.5-2.7 uA its output sits at V_O2 within millivolts (VOH is specified at 3 mA: 0.35 V drop, SLVSE13 p.8). Q16 needs only to hold O2_G "
         "against R174 (PV_SW / 10 M <= 0.3 uA) after recharging C174 once; VGSth max 0.95 V is defined at 250 uA (PMZ290UNE2 p.6). The load on U20 is 9 % lower than "
         "the stage-1 pull-down R175 1 M, so the approval light and the 1.6 V corners of calc/o2_inhibit.json do not get worse.")
# 3.2 heartbeat: CHG_DIS step VDD through C175 into O2_HB (Q16 gate, R176 to GND, R175 into the output of the unpowered U20)
hb = {}
for lab, rpd in (("U20 output as a short to GND (worst case: its clamp diodes into the discharged O2_NC / V_O2 nodes)", R175 * R176 / (R175 + R176)),
                 ("U20 output open (best case)", R176)):
    t_ = (C175 + CISS) * rpd
    hb[lab] = dict(tau_us=round(t_ * 1e6, 1),
                   gate_V_first_edge=[round(v * C175 / (C175 + CISS) - PMZ290["Qgd"] / (C175 + CISS), 3) for v in VDD],
                   gate_V_next_edges=[round(v * C175 / (C175 + CISS), 3) for v in VDD],
                   gate_V_at_end_of_10us_pulse=[round(v * C175 / (C175 + CISS) * math.exp(-10e-6 / t_), 3) for v in VDD],
                   undershoot_after_falling_edge_V=[round(v * C175 / (C175 + CISS) * (math.exp(-10e-6 / t_) - 1), 3) for v in VDD],
                   static_level_on_time_ms=round(t_ * math.log(VDD[2] * C175 / (C175 + CISS) / PMZ290["Vth"][0]) * 1e3, 2))
tau_hold_min = 0.8 * C174 * 0.99 * R174
R["merged_heartbeat"] = dict(C175_nF=1.0, R175_k=100, R176_M=1.0, cases=hb,
    stage1_for_comparison=dict(C175_pF=220, gate_V_next_edges=S0["stage1"]["D1_heartbeat"]["gate_peak_V_next_edges"], tau_us=S0["stage1"]["D1_heartbeat"]["gate_tau_us"]),
    charge_needed_per_pulse_nC=round((1 - math.exp(-0.1 / tau_hold_min)) * C174 * 2.5 * 1e9, 1),
    Q16_at_gate_1p5V="RDSon <= 0.68 Ohm at VGS 1.8 V (PMZ290UNE2 p.6); at 1.5 V the FET is far above VGSth max 0.95 V: C174 (100 nF) recharges in well under 1 us",
    pin_load="CHG_DIS drives C175 + the Q10 and Q16 gates: 1.1 nF x 1.86 V = 2.0 nC per edge; with the nRF52832 standard drive (>= 0.5 mA) the edge takes <= 4 us (inside the 10 us pulse); "
             f"energy C V^2 f = {round(1.1e-9 * 1.859 ** 2 * 10 * 1e9, 1)} nW at 10 Hz",
    release_after_last_pulse_s=S0["stage1"]["D1_heartbeat"]["release_after_last_pulse_s"],
    rules_unchanged=S0["stage1"]["D1_heartbeat"]["firmware_rules"])
# 3.3 side effect A: the approval edge couples through C175 into CHG_DIS = the gate of Q10 (TS / NTC pull-down), MCU unpowered
def inj(R146, V_OH):
    rb = R176 * R146 / (R176 + R146)
    v0 = V_OH * rb / (R175 + rb)                       # both ends of the uncharged C175 move together at t = 0+
    return v0, R146 * C175
sideA = {}
for R146 in (1e6, 10e3):
    row = {}
    for V in (1.6, 2.6, 3.0):
        v0, t_ = inj(R146, V)
        vclamp = min(v0, 0.55)                          # E: the unpowered nRF52832 pin clamps to its VDD rail (0 V) through the ESD diode at about 0.5-0.6 V
        i_q10 = [id_sub(vclamp, vt) for vt in (PMZ290["Vth"][0], PMZ290["Vth"][1])]
        par0 = 100e3 * Rntc(0) / (100e3 + Rntc(0)); par45 = 100e3 * Rntc(45) / (100e3 + Rntc(45))
        row[f"V_O2 {V} V"] = dict(CHG_DIS_V_unclamped=round(v0, 3), CHG_DIS_V_with_pin_clamp=round(vclamp, 3), duration_tau_us=round(t_ * 1e6, 1),
                                  Q10_current_uA_Vth_min_typ=[round(i * 1e6, 3) for i in i_q10],
                                  NTC_node_pull_mV_at_0C=[round(min(i * par0, V * Rntc(0) / (Rntc(0) + 100e3)) * 1e3, 2) for i in i_q10],
                                  NTC_node_pull_mV_at_45C=[round(min(i * par45, V * Rntc(45) / (Rntc(45) + 100e3)) * 1e3, 2) for i in i_q10])   # limited to the node voltage (pulled to 0 V)
    sideA[f"R146 {R146 / 1e3:g} k"] = row
R["merged_side_effect_A_CHG_DIS"] = dict(
    cases=sideA, sensitivity_mV_per_K_at_2V=S0["threshold_design"]["sensitivity_mV_per_K_at_2V"],
    reading="with R146 1 M the approval edge lifts the Q10 gate to the pin clamp (about 0.55 V) for about 1 ms: a Q10 with a low threshold pulls the NTC node down, U20 reads 'hot' and "
            "withdraws the approval: chatter. With R146 10 k the gate stays below 0.25 V for about 10 us: at most one extra comparator cycle at the moment of approval. "
            "The glitch can only follow a genuine approval (U19 and U20 both true), so it cannot create one outside the window; it must be shown in SIM-03.",
    change="R146 1 M -> 10 k 0201 (C473048, already in the BOM) with SB_O2=merged: 186 uA from the MCU only while CHG_DIS is held high (charge stop at 41 C skin, head attached)")
# 3.4 side effect B: heartbeat current into the output pin of the unpowered U20 (R175 -> OUT -> clamp diode -> O2_NC -> U19 OUT clamp -> V_O2 -> ladder / chain)
vd = 0.40
r_path = 100e3 * 946.3e3 / (100e3 + 946.3e3)             # (R116 + NTC about 110 k) || chain 946.3 k, rounded down to R116 || chain
i_pk = (VDD[2] * C175 / (C175 + CISS) - 2 * vd) / (R175 + r_path)
R["merged_side_effect_B_U20_output"] = dict(
    peak_current_uA=round(i_pk * 1e6, 2), charge_per_pulse_pC=round(i_pk * 10e-6 * 1e12, 1), average_nA_at_10Hz=round(i_pk * 10e-6 * 10 * 1e9, 3),
    V_O2_rise_per_pulse_mV=round(i_pk * 10e-6 / 100e-9 * 1e3, 3),
    abs_max="TLV703x OUT: VEE - 0.3 V .. VCC + 0.3 V (SLVSE13 p.6). While the O-2 is unpowered the heartbeat forward-biases the output clamp of U20 by one diode drop "
            "(about 0.4 V above its VCC pin) at the microampere level, 10 us at 10 Hz. TI limits the INPUT pins to 10 mA in this condition and gives no current limit for OUT: "
            "the letter of the table is exceeded by about 0.1 V. Open question for TI (or a bench check) before SB_O2=merged is used.")
R["merged_verdict"] = dict(saves_mm2=round(area["std"]["courtyard_mm2"] - area.get("merged", {"courtyard_mm2": float("nan")})["courtyard_mm2"], 2) if "merged" in area else None,
    status="calculated; NOT in the baseline: two effects that the stage-1 circuit does not have (sections 3.3, 3.4) need SIM-03 and a maker's answer",
    requirements_check={
        "MCU off, cell flat (VBAT_OK low), in window": "U19 / U20 approve -> O2_HB 0.91 x V_O2 -> Q16 on -> Q14 on (as stage 1 through Q17)",
        "MCU off, cell flat, out of window or too little light": "U20 low or unpowered -> R176 holds O2_HB at 0 V -> Q14 off",
        "MCU in reset / halted / off at a healthy cell (VBAT_OK high)": "no heartbeat, O-2 unpowered -> Q14 off within the hold (0.64-1.67 s)",
        "firmware running": "heartbeat pulses -> Q16 -> Q14 on; stop on any out-of-window reading",
        "dark load": "0 (PV_SW = 0 V); heartbeat about 1 uW only while the firmware wants PV charging",
        "no oscillation with Q1 / Q8": "unchanged: the O-2 only opens Q14"})

# ------------------------------------------------------------------ 4. pack PCM with a charge-temperature cut-off: ABLIC S-82D1A (datasheet Rev.1.2_00)
R["pack_pcm_S82D1A"] = dict(
    source="https://www.ablic.com/en/doc/datasheet/battery_protection/S82D1A_E.pdf (fetched 2026-11-14 22:15 UTC, read 2026-11-15)",
    facts={"p.1": "temperature protection with an external NTC on a dedicated pin; low temperature charge inhibition -40..+10 C and high temperature charge inhibition +40..+85 C in 1 C steps, "
                  "accuracy +-3 C with the NTC of Table 6; 0 V battery charge enabled or inhibited (option); HSNT-8(1616); 2.5 uA typ / 5.0 uA max operating, 0.5 uA max in overdischarge",
           "p.6 Table 6": "catalogue products S-82D1AAI / AAJ / AAK / AAL-A8T2U7: THCD 60 C, THC 45 C, TLC 0 C, TLCD -20 C, hysteresis 5 C, sampling wait 512 ms, count 2, NTC 10 k +-1 % B 3380 K +-1 %",
           "p.9": "operation voltage VDD-VSS 1.5-6.0 V; 0 V battery charge inhibition battery voltage V0INH 0.9 / 1.2 / 1.5 V (min / typ / max)",
           "p.21": "overdischarge status below VDL (2.0-3.0 V); with a charger connected it is released at VDL or VDU",
           "p.22-23": "charge overcurrent detection and the CTL input do not function in the overdischarge status",
           "p.24": "'carries out intermittent operation in the normal status': the NTC is sampled for 4 ms after each sampling wait time; the charge FET is turned off in the charge-inhibit "
                   "statuses only while the VM pin is at or below 3 mV typ. (charger connected)",
           "p.25": "0 V battery charge inhibited: below V0INH the charge FET gate is fixed to EB-: no charging"},
    coverage_by_cell_voltage=[
        dict(cell_V="0 to V0INH (0.9-1.5 V)", pv_current="none at any temperature with the '0 V battery charge inhibited' option", status="meets O-2, but the cell can never be recovered by light or by the head"),
        dict(cell_V="V0INH to 1.5 V", pv_current="not specified (below the 1.5 V operation voltage)", status="unknown: maker's answer needed"),
        dict(cell_V="1.5 V to VDL (2.0-3.0 V), overdischarge status", pv_current="charging is allowed to recover the cell; the datasheet describes the temperature sampling for the normal status only",
             status="unknown: maker's answer needed (this is the deeply discharged case of BASELINE 13.2)"),
        dict(cell_V=">= VDL, normal status", pv_current="charge FET off outside TLC..THC after 2 samples (about 1 s)", status="meets O-2 within +-3 C: a guaranteed 0-45 C window needs TLC 3 C and THC 42 C (1 C steps exist; not catalogue values)")],
    other_points=["the catalogue parts are trimmed for a 10 k B 3380 K NTC; the pack NTC of BASELINE 5.2 is B 3950 K (BQ25170 TS, board ladder): the PCM needs its own NTC on its own pin (a second NTC in the capsule) or a custom trim",
                  "in a charge-inhibit status the charge FET is off while VM <= 3 mV: the band's small discharge current then flows through the FET's body diode (about 0.5 V below the cell): "
                  "the rail can fall below VBAT_OK falling (3.31 V) whenever the cell is below 0 C or above 45 C (my reading of p.24, 7.2 / 7.3; to be confirmed with the maker)",
                  "Iq 2.5 / 5.0 uA is inside the pack's 6 uA limit (BASELINE 5.2)",
                  "Nisshinbo NB7130 / R5449 also list a temperature protection; their datasheets could not be downloaded (HTML answer on 2026-11-14) and are not read: unknown"],
    verdict="a real PCM IC with a 0 / 45 C charge-temperature cut-off exists (ABLIC S-82D1A). Its datasheet does not state that the cut-off works for a deeply discharged cell "
            "(1.5 V to VDL), so the board O-2 cannot be dropped on the datasheet alone: reserve 3 stays open until the pack maker or ABLIC answers in writing")
R["generated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(R, open(os.path.join(HERE, "o2_dense.json"), "w"), indent=1)
print(json.dumps({k: R[k] for k in ("area", "merged_approval", "merged_heartbeat", "merged_side_effect_A_CHG_DIS", "merged_side_effect_B_U20_output")}, indent=1)[:7000])
print("wrote o2_dense.json")
