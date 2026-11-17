#!/usr/bin/env python3
"""V3-F main-board calculations other than O-2 (o2_inhibit.py) and the board area (tools/area_check.py): CALC_V3F.md sections 1, 2, 4-9.
Every datasheet value is quoted with its document and page in SRC and in CALC_V3F.md; 'E' marks an estimate or an assumption.
Reads (read-only): ../parts.json (values as built), o2_inhibit.json, ../area_check.json, v3/integrate/energy/v3_energy.py (PV model, imported),
v3/decide/calc/baseline_calc.json (BASELINE 11.1 loads). Writes: v3f_calc.json (next to this file).
run: python3 -B v3f_calc.py   (about 30 s: the PV model import)
"""
import json, math, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); DESIGN = os.path.dirname(HERE); V3 = os.path.dirname(DESIGN)
OUT = {}
SRC = {
 "BQ25170": "TI SLUSDJ8A (Apr 2020, rev. Apr 2021) https://www.ti.com/lit/ds/symlink/bq25170.pdf",
 "SLUAAG9": "TI SLUAAG9 BQ25171-Q1 Quick Start Guide (Sep 2021) https://www.ti.com/lit/an/sluaag9/sluaag9.pdf",
 "TPS7A02": "TI SBVS277C (Jul 2019, rev. Sep 2022) https://www.ti.com/lit/ds/symlink/tps7a02.pdf",
 "TXU0104": "TI SCES937B (May 2021, rev. Feb 2025) https://www.ti.com/lit/ds/symlink/txu0104.pdf",
 "TXU0101": "TI SCES940A (Feb 2022, rev. May 2024) https://www.ti.com/lit/ds/symlink/txu0101.pdf",
 "LS011": "Sharp LD-29Y03 LS011B7DH03 spec (24 Nov 2017) https://d7rh5s3nxmpy4.cloudfront.net/CMP7377/files/LS011B7DH03_24Nov17_Spec_LD-29Y03.pdf",
 "BAV70M": "Nexperia BAV70M (1 Jul 2022) https://datasheet.lcsc.com/datasheet/pdf/57d454f2d24a7e90ce02c5218e178436.pdf?productCode=C549313",
 "BAT54CM": "Nexperia BAT54CM (2003) https://datasheet.lcsc.com/datasheet/pdf/857e6e97bc7a4b56c05ca8c91376cec5.pdf?productCode=C549275",
 "ESD761": "TI SLVSH10C (Nov 2022, rev. Dec 2022) https://www.ti.com/lit/ds/symlink/esd761.pdf",
 "NSR0240": "onsemi NSR0240MX2/D rev. 3 (Mar 2022) https://datasheet.lcsc.com/datasheet/pdf/4b95626787cd7ec325d86dd9eff135e9.pdf?productCode=C896422",
 "PMZ290": "Nexperia PMZ290UNE2 (24 Mar 2015) https://datasheet.lcsc.com/datasheet/pdf/bc9c5c1607503fe9b387ba45e37b3765.pdf?productCode=C478155",
 "PMZ350": "Nexperia PMZ350UPE (14 May 2014) https://datasheet.lcsc.com/datasheet/pdf/61ec9f5ef7c9e0bb0863e45d64cfc884.pdf?productCode=C478207",
 "PTS840": "C&K PTS 840 catalogue B-40..B-42 https://datasheet.lcsc.com/datasheet/pdf/82b5c1248b369a64727907ed223b233b.pdf?productCode=C221907",
 "BQ25570": "TI SLUSBH2G https://www.ti.com/lit/ds/symlink/bq25570.pdf",
 "VCLP0820": "Vybronics VCLP0820B004L product page (v3/decide/research/eng_b/notes_sources.md row VCLP0820)",
 "CLP1020": "Jinlong CLP1020B002L spec 2019-04-29 p.4/13 (eng_b notes_sources.md row CLP1020): class analogy only",
 "AZ11049": "Azumo 11049-xx front light data sheet 12367-01_T5 p.2 (eng_b notes_sources.md row AZ_11049): the 1.28 in part, not the custom 1.08 in film",
 "V2CALC": "v3/design/v2_ref/CALC.md sections 1, 4, 5 and v2_ref/calc/led_supply.py (V2-B values as frozen)",
 "BASELINE": "v3/decide/BASELINE.md and v3/decide/calc/baseline_calc.json",
}
P = json.load(open(os.path.join(DESIGN, "parts.json")))["variants"]["v3f"]["parts"]
def val(ref): return P[ref]["value"]

# ======================================================================================= 1. BQ25170 block
KISET = (270.0, 300.0, 330.0)                    # A*Ohm, SLUSDJ8A p.6 (10 mA < ICHG < 800 mA)
RISET = 10.2e3; RTOL = 0.01                      # R140 10.2 k 1 % (parts.json) [S1 D-8: was 10.0 k, 0.505 C at 66 mAh]
assert val("R140").startswith("10.2k")
ich = (KISET[0] / (RISET * (1 + RTOL)), KISET[1] / RISET, KISET[2] / (RISET * (1 - RTOL)))
CAPS = (70.0, 66.0, 60.0)                        # mAh: BASELINE 5.2 (>= 66 nominal, >= 60 minimum, 70 planning)
VREG = 4.10                                      # R142 36 k: Table 7-1 p.14
VREG_ACC = (0.005, 0.008)                        # +-0.5 % at 25 C, +-0.8 % -40..125 C (p.6)
RVSET_TOL = (36e3 * 0.99, 36e3 * 1.01)           # next table entries 27 k (4.20 V) and 47 k (4.05 V), p.14
VSLEEPZ = (0.095, 0.135, 0.175); VIN_LOWV_R = (3.05, 3.09, 3.15); VIN_OV = (6.60, 6.75, 6.90)    # p.6
RON = (0.845, 1.0, 1.45)                         # charge FET, p.7 (1.45 max over -40..125 C)
NSR_VF = {1e-4: (0.21, 0.24), 1e-3: (0.27, 0.30), 1e-2: (0.34, 0.365), 1e-1: (0.46, 0.50)}          # NSR0240 p.1-2 (typ, max)
def nsr_vf(i, k=1):
    xs = sorted(NSR_VF); lx = math.log10(i)
    for a, b in zip(xs, xs[1:]):
        if a <= i <= b:
            t = (lx - math.log10(a)) / (math.log10(b) - math.log10(a)); return NSR_VF[a][k] + t * (NSR_VF[b][k] - NSR_VF[a][k])
    return NSR_VF[xs[-1]][k]
vf33 = nsr_vf(ich[2], 1)
head_min_for_sleepz = VREG * (1 + VREG_ACC[1]) + VSLEEPZ[2] + vf33 + ich[2] * 0.2       # + 0.2 Ohm contacts + traces (E)
OUT["bq25170"] = dict(
    ichg_mA=[round(x * 1e3, 2) for x in ich], c_rate={f"{c:g} mAh": [round(x * 1e3 / c, 3) for x in ich] for c in CAPS},
    rule_half_C=f"<= 0.5 C at >= 66 mAh nominal with KISET max and R140 at -1 %: {ich[2] * 1e3:.2f} mA / 66 mAh = {ich[2] * 1e3 / 66:.3f} C (S1 D-8: 10.0 k gave 0.505 C)",
    precharge_mA=[round(0.20 * x * 1e3, 2) for x in ich], precharge_note="20 % of ICHG between VBAT_SHORT and VBAT_LOWV 2.7-3.0 V (p.7)",
    trickle_mA=(12, 16, 20), trickle_note="IBAT_SHORT below VBAT_SHORT 2.1-2.3 V, independent of RISET (p.7): 0.17-0.29 C for 70 mAh",
    term_mA_nominal=round(0.10 * ich[1] * 1e3, 2), term_note="ITERM 10 % (p.7); accuracy given only at 600 Ohm / 3 k / 30 k: at 30 k it is 0.4-1.6 mA for 1 mA nominal (+-60 %), so 3 mA +-60 % (E)",
    vreg_V=dict(nominal=VREG, at_25C=(round(VREG * (1 - VREG_ACC[0]), 3), round(VREG * (1 + VREG_ACC[0]), 3)),
                over_temp=(round(VREG * (1 - VREG_ACC[1]), 3), round(VREG * (1 + VREG_ACC[1]), 3)), recharge_below_mV=(75, 100, 125),
                rvset_window_ohm=[round(x) for x in RVSET_TOL], rvset_ok="36 k +-1 % stays far from the 27 k and 47 k table entries; latched at power-up (p.15)"),
    dropout=dict(charge_fet_mV_at_33mA=round(RON[2] * ich[2] * 1e3, 1), d14_vf_max_at_33mA_V=round(vf33, 3),
                 head_min_V_for_sleep_exit_at_full_cell=round(head_min_for_sleepz, 3),
                 note="/PG and charging need VIN > VOUT + VSLEEPZ (95-175 mV, p.6, p.17): at the end of charge (VOUT up to 4.133 V) the head must deliver "
                      f">= {head_min_for_sleepz:.2f} V at the contacts (D14 {vf33:.2f} V max at 33 mA, NSR0240 p.2 interpolated; 0.2 Ohm contacts E). "
                      "A 5.0 V -5 % head (4.75 V) sits exactly at this limit: V3-G10 head requirement >= 4.85 V at the contacts at 40 mA (below it the charger sleeps "
                      "near the end of charge and /PG goes high: a few % of capacity lost, no hazard)"),
    dissipation_mW=round((5.25 - 0.40 - 3.0) * ich[2] * 1e3, 1), dissipation_note="head 5.25 V, D14 0.40 V, cell 3.0 V at the CC start, 33 mA (E head); RthJA 75.2 C/W JEDEC (p.5): +4.6 K",
    iset_rc=dict(R141=val("R141"), C132=val("C132"), tau_us=round(2e3 * 4.7e-9 * 1e6, 1),
                 source="SLUSDJ8A p.14 7.3.1.1: an extra RC on ISET is recommended below 50 mA; values from SLUAAG9 Figure 5-1 p.4 (2.0 kOhm + 4.7 nF across R-ISET, "
                        "45 mA design of the sibling BQ25171-Q1, read as an image in this lane): applicability to the BQ25170 assumed (same ISET detection, E)"),
    ts=dict(bias_uA=(36.5, 38.0, 39.5), vcold_V=(0.99, 1.04, 1.09), vhot_V=(0.176, 0.188, 0.200), enz_V=(0.040, 0.050, 0.060), clamp_V=(2.3, 2.6, 2.9),
            duty="ITS_BIAS duty-cycled 100 ms on / 2 s off (p.8, p.17)", window_from_o2=json.load(open(os.path.join(HERE, "o2_inhibit.json")))["ts_window"],
            chg_dis=f"Q10 on: VTS = 39.5 uA x 0.68 Ohm = {39.5e-6 * 0.68 * 1e6:.0f} uV << VTS_ENZ 40 mV (charge disabled, p.7, PMZ290 p.6)"),
    pg=dict(pullup=val("R143"), low_uA=round(1.859 / 220e3 * 1e6, 2), leak_max_uA=1.0, high_level_V_min=round(1.859 - 1e-6 * 220e3, 3),
            note="open drain, VOL <= 0.4 V at 5 mA, high-level leakage <= 1 uA with a 3.3 V pull-up (p.7); no typical value: 1 uA is a bound. "
                 "High level >= 1.64 V against VIH 0.7 x VDD = 1.30 V (nRF52832, E). Low only while the head is attached (8.45 uA from VDD_1V8)"),
    iq_out_uA=(0.35, 0.6, 0.8), iq_out_note="IQ_OUT with IN floating or 0-5 V, charge disabled: 0.35 typ / 0.6 max at 25 C, 0.8 below 105 C (p.6); in BASELINE 11.1 base loads",
    abs_max_in_V=(-0.3, 30.0), ovp_V=VIN_OV)

# ======================================================================================= 2. R_LIM bound and cold start with Q14 in series
t0 = time.time()
sys.path.insert(0, os.path.join(V3, "integrate", "energy"))
import v3_energy as VE                                          # read-only import of the V3 PV model (as o2_inhibit.py)
M = VE.M; SET = "LID2+WR31"
Q14_RON = dict(vgs_4p5=(0.33, 0.45), vgs_2p5=(0.42, 0.645), vgs_1p8=(0.52, 0.94))   # PMZ350UPE p.6 (typ, max)
R130 = 12.0; R130_TOL = 0.01
def bound(strip_mm, r_series):
    VE.A_LID2 = 27.7 * strip_mm / 100
    out = {}
    for lab, G, tc in (("1.2 sun, strings -10 C", 1.2, -10.0), ("1.2 sun, strings -20 C", 1.2, -20.0), ("1 sun, strings 25 C", 1.0, 25.0)):
        r = VE.charge_point(VE.sources(SET, "walking|sun30", G, dvoc=VE.dvoc_T(tc), wing_ratio=1.0), r_series, 3.0, 0.72)
        out[lab] = dict(c_rate_70=round(r["i_bat_inst_mA"] / 70.0, 3), i_pv_mA=round(r["i_pv_mA"], 1))
    return out
def cold(strip_mm, r130, ron):
    VE.A_LID2 = 27.7 * strip_mm / 100
    out = {}
    for lab, G, tc in (("1 sun, 25 C", 1.0, 25.0), ("1.2 sun, -10 C", 1.2, -10.0)):
        i = VE.series_i(VE.sources(SET, "walking|sun30", G, dvoc=VE.dvoc_T(tc), wing_ratio=1.0), 0.6, 1.0 + r130 + ron)
        out[lab] = dict(i_mA=round(i * 1e3, 1), p_R130_mW=round(i * i * r130 * 1e3, 1), p_Q14_mW=round(i * i * ron * 1e3, 2))
    return out
OUT["r_lim"] = dict(
    note="charge_point / series_i of v3_energy (RSH1 1 Ohm + series R), k 0.72, cell 3.0 V, every string lit (BASELINE 11.5 convention). Q14 conducts with "
         "VGS = -PV_SW (MCU on, Q16) or with the gate held by C174 at -Voc of the approval (MCU off): -1.8 to -2.5 V at the bound points (E)",
    bound_2p50mm_baseline_R12=bound(2.50, R130),
    bound_2p50mm_lowest_R=bound(2.50, R130 * (1 - R130_TOL) + Q14_RON["vgs_4p5"][0]),
    bound_2p50mm_highest_R=bound(2.50, R130 * (1 + R130_TOL) + Q14_RON["vgs_1p8"][1]),
    bound_2p30mm_lowest_R=bound(2.30, R130 * (1 - R130_TOL) + Q14_RON["vgs_4p5"][0]),
    cold_start_2p50mm_baseline=cold(2.50, R130, 0.0),
    cold_start_2p50mm_q14_min=cold(2.50, R130 * (1 + R130_TOL), Q14_RON["vgs_4p5"][0]),
    cold_start_2p50mm_q14_max=cold(2.50, R130 * (1 + R130_TOL), Q14_RON["vgs_1p8"][1]),
    r130_rating_mW=250, q14_ptot_note="PMZ350UPE / SOT883: a few mW against a Ptot of several 100 mW (same package class as PMZ290 350 mW, p.3): no limit (E)",
    import_s=round(time.time() - t0, 1))

# ======================================================================================= 3. O-2 (summary of o2_inhibit.json)
O2 = json.load(open(os.path.join(HERE, "o2_inhibit.json")))
OUT["o2_summary"] = dict(corners=O2["threshold_design"]["corners"], typical=O2["threshold_design"]["typical_C"], dark_load_uW=O2["dark_load_uW"]["value"],
                         approval_lux_mcu_off=O2["approval_light_mcu_off"]["lux"], hold_s=O2["timing"]["hold"], hysteresis_K=O2["no_oscillation"]["hysteresis_K"],
                         ts_window=O2["ts_window"], mcu_reading_error_K=O2["mcu_reading"]["error_K_for_30mV_VF_error"])

# ======================================================================================= 4. ERM drive and VBAT_OK margin
VBOK_F = (3.192, 3.312, 3.441)                   # VBAT_OK falling: min / nominal / max with IC accuracy (V2CALC section 1)
VBOK_R = (3.279, 3.403, 3.536)
PATH = dict(cell_pcm=(0.15, 1.00, 2.50), r112=1.00, pfet=(0.95, 1.50), f1_strap_links=0.25)
#   cell + PCM: 0.15 Ohm GEB statement (BASELINE 11.2 T7 row via ENG_A) / 1.0 Ohm sister-cell limit (V2CALC) / 2.5 Ohm at 0 C (V2CALC, E);
#   R112 1 Ohm INA_BAT shunt; BQ25570 PFET 0.95 / 1.50 Ohm (V2 led_supply.py); F1 + strap conductors + FB1/FB2 links 0.25 Ohm (E: F1 not selected)
def path(case, on_vstor):
    c = dict(typ=0, max=1, cold=2)[case]
    r = PATH["cell_pcm"][c] + PATH["r112"] + PATH["f1_strap_links"]
    if on_vstor: r += PATH["pfet"][0 if case == "typ" else 1]
    return r
I_RUN = (0.030, 0.035)                           # A at 3.0 V average (VCLP0820 page: 30 typ / 35 max mA)
R_COIL = 3.0 / 0.080                             # Ohm: start current 80 mA max at 3.0 V (CLP1020 class, E)
V_START = 2.3                                    # V starting voltage (CLP1020 class p.4/13, E for the VCLP0820)
def erm(vbat, case, on_vstor, duty_start=None):
    r = path(case, on_vstor); d_run = min(1.0, 3.0 / vbat)
    i_run = d_run * I_RUN[1]                                     # battery current while running (continuous motor current, E)
    d0 = d_run if duty_start is None else duty_start
    i_start = d0 * d0 * vbat / R_COIL                            # rotor still: I_motor = D x V / R_coil; battery current = D x I_motor
    return dict(path_ohm=round(r, 2), i_run_mA=round(i_run * 1e3, 1), vstor_run_V=round(vbat - i_run * r, 3),
                i_start_mA=round(i_start * 1e3, 1), vstor_start_V=round(vbat - i_start * r, 3), duty_start=round(d0, 3), v_avg_start=round(d0 * vbat, 2))
def duty_limit(vbat, case, on_vstor, vmin):
    r = path(case, on_vstor); i_max = (vbat - vmin) / r
    return min(1.0, math.sqrt(max(0.0, i_max) * R_COIL / vbat)), i_max
ERM = {}
for sup in ("VBAT_IC", "VSTOR"):
    on_vs = sup == "VSTOR"
    for case in ("typ", "max", "cold"):
        e = erm(3.60, case, on_vs); d, imax = duty_limit(3.60, case, on_vs, VBOK_F[2])
        e.update(margin_start_to_vbok_max_mV=round((e["vstor_start_V"] - VBOK_F[2]) * 1e3), margin_start_to_vbok_nom_mV=round((e["vstor_start_V"] - VBOK_F[1]) * 1e3),
                 margin_run_to_vbok_max_mV=round((e["vstor_run_V"] - VBOK_F[2]) * 1e3),
                 soft_start_limit=dict(i_bat_max_mA=round(imax * 1e3, 1), duty_max=round(d, 3), v_avg_max=round(d * 3.60, 2), starts=d * 3.60 >= V_START))
        ERM[f"{sup} | {case}"] = e
vds_peak = 4.28 + 0.50                           # VSTOR / VBAT_IC max (VBAT_OV) + BAT54CM VF max at 30 mA (p.4)
QG_18 = 46e-12 * 1.86 + 0.1e-9                   # E: Ciss 46 pF x 1.86 V + gate-drain charge at a few V (QGD 0.2 nC at 10 V, p.6)
t_gate = 2.2 * 1e3 * QG_18 / 1.86                # 10-90 % with R162 1 k
p_sw = 0.5 * 4.28 * I_RUN[1] * 2 * t_gate * 40e3
OUT["erm"] = dict(supply_choice="VBAT_IC (as built): the start current does not cross the BQ25570 PFET; VSTOR (BASELINE 4) compared below",
                  cases_at_vbat_3p60=ERM, vbok_falling_V=VBOK_F, vbok_rising_V=VBOK_R, path_ohm_parts=PATH,
                  motor=dict(i_run_mA=(30, 35), r_coil_ohm_E=round(R_COIL, 1), start_current_mA_E=80, starting_voltage_V_E=V_START, rise_ms_max=90),
                  flyback=dict(diode="D17 BAT54CM, both halves in parallel to VBAT_IC", vf_max_V_at_30mA=0.50, vds_peak_V=round(vds_peak, 2), q12_vds_max_V=20,
                               diode_avg_mW=round((1 - 3.0 / 3.6) * I_RUN[1] * 0.5 * 1e3, 1), ifrm_mA=300),
                  gate=dict(r162=val("R162"), r163=val("R163"), peak_gpio_mA=round(1.86 / 1e3 * 1e3, 2), edge_10_90_ns=round(t_gate * 1e9), qg_E_nC=round(QG_18 * 1e9, 2),
                            switching_loss_mW_at_40kHz=round(p_sw * 1e3, 2), rdson_mOhm_at_1p8V=(470, 680), drop_mV_at_80mA=round(0.68 * 80, 1)),
                  pwm_ripple_mV=round(I_RUN[1] * 0.83 * 0.17 * 25e-6 / (22e-6 * 0.40) * 1e3, 1),
                  ship_mode=("VBAT_IC stays on the cell in ship mode (the BQ25570 opens only the VSTOR-VBAT PFET, SLUSBH2G 7.4.1 p.18): Q12 off-state leakage "
                             "becomes a ship-mode load: IDSS <= 1 uA at VDS 20 V, 25 C (PMZ290 p.6) is the only published bound; no figure at 4 V (bound 3.7 uW)"),
                  hook=("BASELINE 14 item 6: INA_BAT (U5 INA236, R112, bus = BATT_P) reads VBAT before the start and the battery current during the 30 ms ramp; "
                        "the firmware ramps the duty while I_bat <= 40 mA and VBAT_IC - I x 1.0 Ohm >= 3.50 V (keeps VSTOR above VBAT_OK falling max 3.441 V "
                        "at every corner of the table); never during ECG"))

# ======================================================================================= 5. front light
VS = (3.31, 4.28)                                 # VSTOR_SW operating range: VBAT_OK falling nominal .. VBAT_OV (V2CALC; BASELINE R160 note)
VF = (2.6, 2.9)                                   # E: white LED of the custom film at 1-5 mA (film not specified; AZ11049 gives no VF in the notes)
R160 = 100.0; assert val("R160").startswith("100R")
FL = {}
for r in (100.0, 120.0, 150.0, 220.0):
    lo = (VS[0] - VF[1] - 0.68 * 0.004) / r; hi = (VS[1] - VF[0]) / r
    FL[f"{r:g} Ohm"] = dict(i_peak_low_mA=round(lo * 1e3, 2), i_peak_high_mA=round(hi * 1e3, 2), p_peak_high_mW=round(hi * hi * r * 1e3, 1),
                            dim_room_3mA_possible=lo >= 3e-3)
E_NIGHT = 10 * 3 * 1.5e-3 * 3.7; E_DIM = 20 * 3 * 3e-3 * 3.7; E_DARK = 100 * 3 * 1.5e-3 * 3.7     # J/day (BASELINE 11.1 eng_b counts)
# [S1 D-6] G10 (h) window: 330 Ohm +-1 % jig load on J16, pack pads at 3.80 V -> VSTOR_SW 3.70-3.80 V (E: PFET + switch drop at 9 mA),
# Q11 0.47-0.68 Ohm, R160 100 Ohm +-1 %; and with a jig LED of stated VF 2.7 +-0.1 V instead of the resistor
jig_lo = 3.70 / (101.0 + 333.3 + 0.68); jig_hi = 3.80 / (99.0 + 326.7 + 0.47)
led_lo = (3.70 - 2.8) / (101.0 + 0.68); led_hi = (3.80 - 2.6) / (99.0 + 0.47)
OUT["front_light_G10h"] = dict(load_330R_mA=[round(jig_lo * 1e3, 2), round(jig_hi * 1e3, 2)], window_mA=[8.3, 9.1],
                               jig_led_2p7V_mA=[round(led_lo * 1e3, 2), round(led_hi * 1e3, 2)],
                               note="stage 0 wrote 1.5-7.6 mA (derived for R160 = 220 Ohm): a good board would have failed EOL (review D-6)")
OUT["front_light"] = dict(r160=val("R160"), table=FL, choice=("100 Ohm (C270366): >= 3 mA possible at VSTOR_SW 3.31 V with VF 2.9 V; peak <= 16.8 mA at 4.28 V with VF 2.6 V "
                          "(the LED's VF rises with current, so the real peak is lower) against 25 mA absolute maximum of the 1.28 in part (AZ11049 p.2); 220 Ohm "
                          "(the first value) cannot give the 3 mA dim-room level below VSTOR_SW 3.56 V"),
                          energy_uW=dict(night_typ=round(E_NIGHT / 86400 * 1e6, 2), dim_room_typ=round(E_DIM / 86400 * 1e6, 2),
                                         typical_total=round((E_NIGHT + E_DIM) / 86400 * 1e6, 2), dark_test=round(E_DARK / 86400 * 1e6, 2),
                                         baseline=(9.64, 19.27), note="battery-referred: I_avg x 3.7 V (R160, LED and Q11 are all in this product)"),
                          pwm=("PWM duty = target average / peak, the firmware reads VSTOR on INA_BAT and corrects for it; the VF spread stays (open loop, "
                               "brightness +-30 % E)"), q11=f"PMZ290UNE2 0.68 Ohm max at 1.8 V: {0.68 * 16.8:.0f} mV at the peak", r160_rating_mW=50)

# ======================================================================================= 6. display interface: TXU0104 / TXU0101 levels, TPS7A0230
VDD18 = (1.80, 1.859, 1.90)                        # VDD_1V8 (BASELINE 4: 1.859 V; range E)
def interp(v, a, b, va, vb): return va + (vb - va) * (v - a) / (b - a)
vt_plus_max = interp(VDD18[2], 1.65, 2.3, 1.13, 1.56); vt_minus_min = interp(VDD18[0], 1.65, 2.3, 0.35, 0.56)
VDISP = (3.0 * 0.985, 3.0, 3.0 * 1.015)           # TPS7A02 +-1.5 % over temperature (p.6)
OUT["display_if"] = dict(
    a_port=dict(vccA="DISP_EN = GPIO P0.19 high (VDD_1V8)", vt_plus_max_V=round(vt_plus_max, 3), vt_minus_min_V=round(vt_minus_min, 3),
                margin_high_V=round(VDD18[0] - 0.05 - vt_plus_max, 3), margin_low_V=round(vt_minus_min - 0.05, 3),
                note="SCES937B p.8: VT+ 0.76-1.13 V at 1.65 V and 1.08-1.56 V at 2.3 V, VT- 0.35-0.69 / 0.56-0.97 V (interpolated to VCCA); nRF outputs at "
                     "light load within 50 mV of the rails (E)"),
    b_port=dict(vdd_disp_V=[round(x, 3) for x in VDISP], panel_vdd_range_V=(2.7, 3.3), panel_vih_min="VDD - 0.1 V", panel_vil_max="VSS + 0.1 V",
                txu_voh_min="VCCB - 0.1 V at 0.1 mA", txu_vol_max="0.1 V at 0.1 mA",
                ok="VCCB = panel VDD (same rail VDD_DISP), so VOH >= VDD - 0.1 V meets VIH >= VDD - 0.1 V at the panel's uA input current; "
                   "LD-29Y03 Table 6-1 spec p.18; SCES937B p.9"),
    edges=("SCES937B p.10: 100 Mbps for 1.65-1.95 V -> 3.0-3.6 V with 20 % of the pulse above 0.7 VCCO, i.e. edges of a few ns; the panel asks <= 50 ns "
           "(LD-29Y03 spec p.22): met with margin (inference from the data-rate row, E)"),
    supply_currents_uA=dict(per_translator_icca_iccb_max=(2.5, 3.0, 6.0), note="SCES937B p.9 / SCES940A p.7: ICCA + ICCB max 2.5 (25 C) / 3 (85 C) / 6 uA (125 C); "
                            "no typical value published (V3_ARCH lists the TXU0104 typical as not found)",
                            u21_bound_uW_face_on=round(2.5e-6 * 3.7 * 1e6, 2)),
    sequence=("on: DISP_EN high (U16 EN, VCCA, OE) -> wait >= 1.2 ms (tSTR 0.75-1.2 ms, SBVS277C p.7) -> panel init with DISP_CTRL low -> DISP_CTRL high. "
              "off: DISP_CTRL low -> wait >= 30 us (LD-29Y03 spec p.21) -> DISP_EN low (U16 discharges VDD_DISP through 60 Ohm, p.7; both translators "
              "go high-Z once a supply is < 100 mV, SCES937B p.1). Below 100 mV of VCCB the DISP input is undriven for the first part of the VDD ramp (E: "
              "check on the bench, V3-G10 (g))"),
    tps7a0230=dict(vout_V=[round(x, 3) for x in VDISP], headroom_at_vbok_min_V=round(VBOK_F[0] - VDISP[2], 3), dropout_max_mV_at_200mA=310,
                   dropout_at_100uA_mV_E=round(0.310 / 0.2 * 100e-6 * 1e3, 3), ignd_nA=(25, 46, 60), ishdn_nA=(3, 10),
                   ignd_uW=(round(25e-9 * 3.7 * 1e6, 3), round(46e-9 * 3.7 * 1e6, 3)), ishdn_uW=(round(3e-9 * 3.7 * 1e6, 4), round(10e-9 * 3.7 * 1e6, 4)),
                   en=("VEN(HI) >= 1.1 V, VEN(LOW) <= 0.3 V, IEN <= 10 nA (p.7): driven by DISP_EN at 1.86 V"),
                   panel_power_uW=dict(hold_typ_max=(15, 50), update_1Hz_typ_max=(25, 100), source="LD-29Y03 Table 6-4 spec p.24 at 3.0 V, 60 Hz EXTCOMIN")))

# ======================================================================================= 7. BAV70M wake paths, button, ship-mode leakage
R144 = R145 = 1e6; R126 = 3.3e6; C121 = 4.7e-6; VTH_STRICT = 1.0       # V2CALC 4: strict release level of Q4 1.0 V
VF_UA = 0.45                                       # E: BAV70M at a few uA (715 mV max at 1 mA, p.3)
def wake(v_src, r_src):
    rth = r_src * R126 / (r_src + R126); vfin = (v_src - VF_UA) * R126 / (r_src + R126)
    t = -rth * C121 * math.log(1 - VTH_STRICT / vfin) if vfin > VTH_STRICT else None
    return dict(final_V=round(vfin, 3), tau_s=round(rth * C121, 3), t_to_1V_s=None if t is None else round(t, 3))
R165, R167 = 100e3, 1e6
OUT["wake"] = dict(
    vbus=dict(vb_det_V=round(5.0 * R145 / (R144 + R145), 2), **wake(5.0 * R145 / (R144 + R145), R144 * R145 / (R144 + R145)),
              note="VBUS 5.0 V -> R144 / R145 1 M / 1 M -> VB_DET 2.5 V -> D12 half A -> EN_HOLD (C121 4.7 uF, R126 3.3 M to the dark PV node): Q4 on, EN low; "
                   "VB_DET also turns on Q8 (PV short) and Q9 (AVDD_EN low) at VGS 2.5 V"),
    button=dict(btn_V_at_vbat={f"{v:.1f}": round(v * R167 / (R165 + R167), 3) for v in (3.0, 3.7, 4.1)},
                **{f"vbat_{v:.1f}": wake(v * R167 / (R165 + R167), R165 * R167 / (R165 + R167)) for v in (3.0, 3.7)},
                press_current_uA=round(4.1 / (R165 + R167) * 1e6, 2), btn_n_pullup_uA=round(1.859 / 1e6 * 1e6, 2),
                note="SW1 closes BTN_SUP (VBAT_IC through R165 100 k) to BTN (R167 1 M): BTN 0.91 x VBAT -> D12 half B -> EN_HOLD; BTN -> Q13 gate -> BTN_N low. "
                     "Running: EN_HOLD already 1.27-1.46 V (D9), so BTN starts at EN_HOLD + VF and Q13 switches at once; ship mode: a press of >= 0.3 s wakes "
                     "(strict 1.0 V), then MCUboot holds PWR_HOLD. C&K contact <= 500 mOhm, bounce <= 10 ms, 50 mA / 12 V max (PTS840 p.1): 4 uA is a dry "
                     "circuit (E: gold-plated contacts would be the safer finish; the GK finish is not stated in the notes)"),
    stuck_button=("water pressure or a stuck key: 3.7 uA in R165 + R167 and 1.9 uA in R164 (when awake) = about 21 uW while held; firmware ignores > 5 s "
                  "(BASELINE 14 item 5); in ship mode a held key keeps EN_HOLD up, so the band leaves ship mode (E: SHELF then applies)"),
    leakage=dict(d12="ship mode: anodes at 0 V (R145, R167 to GND) and cathode at EN_HOLD = 0 V: no bias, no current. Running: reverse bias about 1.3 V, "
                     "IR <= 30 nA at 25 V (BAV70M p.4) per half: < 0.06 uA from the hold node (fed by PWR_HOLD)",
                 r144_r145="0 with the head off (VBUS_K floating, D14 blocks)", sw1="open contact: no path (insulation, E)"))

# ======================================================================================= 8. contact ESD and reverse attach
C130 = 1e-6 * 0.6                                 # 1 uF 25 V X5R 0402 at 5 V: derated to 0.6 (E)
q8kv = 150e-12 * 8e3
OUT["contact_esd"] = dict(
    parts="J15 (VBUS_K) -> D13 ESD761 to GND at the land -> D14 NSR0240 -> VBUS -> C130 1 uF at U15 IN; J18 = GND",
    positive=dict(iec_8kV_contact_charge_uC=round(q8kv * 1e6, 2), dv_on_C130_V=round(q8kv / C130, 2),
                  note="the residual after D13 is charge-limited by C130 through D14: about 2 V on the input capacitor against the 30 V absolute maximum of "
                       "IN (SLUSDJ8A p.4); ESD761 clamps 36.3 V at 1.8 A 8/20 us, IEC 61000-4-2 +-15 kV (SLVSH10C p.4-5)"),
    negative=dict(d14_reverse_V="up to the ESD761 clamp, 36.3 V at 1.8 A plus the dynamic part at the IEC peak (not stated) against NSR0240 VR 40 V (p.1)",
                  status="margin small and not specified for ns pulses: V3-G6 ESD test on the contacts with the head off; fallback a 60 V Schottky in the same land"),
    reverse_attach=dict(d14_ir_uA_max_at_25V=0.55, at_minus5V="D14 blocks: BQ25170 IN stays >= -0.3 V (p.4); ESD761 VRWM +-24 V: no conduction (p.4); "
                        "current <= 0.55 uA (NSR0240 p.2)"),
    standby="head off: VBUS_K floats, D13 leakage <= 50 nA only with a voltage on the pin (SLVSH10C p.4): 0 in use")

# ======================================================================================= 9. standby against BASELINE 11.1
BC = json.load(open(os.path.join(V3, "decide", "calc", "baseline_calc.json")))
VB = 3.7; ETA = 0.85; VDD = 1.859
add = {
 "U21 TXU0101 ICCA + ICCB (bound 2.5 uA, all taken at VSTOR; face on only)": dict(MON_face_on=2.5e-6 * VB),
 "BQ25170 /PG high-level leakage from VDD_1V8 (bound 1 uA; VDD_1V8 on)": dict(MON_face_on=1e-6 * VDD / ETA, MON_dark=1e-6 * VDD / ETA, SHELF=1e-6 * VDD / ETA, ECO=1e-6 * VDD / ETA),
 "Q12 off-state leakage on VBAT_IC in ship mode (bound 1 uA at 20 V; new path of the VBAT_IC supply: on VSTOR the PFET opens in ship mode)": dict(ship=1e-6 * VB),
 "O-2 not a battery load as built (BASELINE planned 2.5 uW while lit)": dict(MON_face_on=-2.5e-6),
 "U16 shutdown current while the display is off (10 nA max)": dict(MON_dark=10e-9 * VB, SHELF=10e-9 * VB, ECO=10e-9 * VB),
 "NTC readings by NTC_EN (15 uA for 50 ms a minute)": dict(MON_face_on=15e-6 * VDD * 0.05 / 60, MON_dark=15e-6 * VDD * 0.05 / 60),
}
BASE = {"MON_face_on": 257.6, "MON_dark": 238.8, "ECO": 93.9, "SHELF": 35.7, "ship": 22.3}
tot = {k: round(BASE[k] + sum(v.get(k, 0.0) for v in add.values()) * 1e6, 1) for k in BASE}
tot_typ = {k: round(BASE[k] + sum(v.get(k, 0.0) for n, v in add.items() if "bound" not in n) * 1e6, 1) for k in BASE}
OUT["standby"] = dict(baseline_uW=BASE, additions_uW={k: {s: round(x * 1e6, 3) for s, x in v.items()} for k, v in add.items()},
                      total_with_bounds_uW=tot, total_without_bound_items_uW=tot_typ,
                      t6_shelf_days_with_bounds=round(257 * BASE["SHELF"] / tot["SHELF"]), t6_ship_days_with_bounds=round(411 * BASE["ship"] / tot["ship"]),
                      note="BASELINE 11.1 values (battery-referred, 3.7 V) with the as-built differences; 'bound' items have only a datasheet maximum (no typical): "
                           "the real values are expected far lower but are not published (unverified - needs samples). T6 >= 182.6 d (BASELINE 11.2)")

# ======================================================================================= 10. board area (from tools/area_check.py)
A = json.load(open(os.path.join(DESIGN, "area_check.json")))
OUT["area"] = {k: {kk: v[kk] for kk in ("courtyard_mm2", "fixed_mm2", "placement_mm2", "utilisation", "utilisation_v1", "pass_project", "pass_v1",
                                         "tall_courtyard_mm2", "tall_zone_util", "tall_zone_util_v1")} for k, v in A["cases"].items()}
OUT["area_delta_vs_plan"] = A["delta_vs_plan"]["by_group"]
OUT["sources"] = SRC
OUT["generated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(OUT, open(os.path.join(HERE, "v3f_calc.json"), "w"), indent=1, default=str)
print("v3f_calc.json written; ICHG", OUT["bq25170"]["ichg_mA"], "| ERM VBAT_IC max start", ERM["VBAT_IC | max"]["vstor_start_V"], "VSTOR max start", ERM["VSTOR | max"]["vstor_start_V"],
      "| standby bounds", tot)
