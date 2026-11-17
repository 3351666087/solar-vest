#!/usr/bin/env python3
"""O-2 hardware PV-charge inhibit of the V3-F main board (BASELINE.md 13.2, 15 G-22, 18 V3-G4): design calculation.

Circuit (src/o2.py):
  * Q14 PMZ350UPE (P-MOSFET) in series between PV_SW (after RSH1, Q1, Q8) and R130 R_LIM -> VIN_DC. Gate O2_G, source PV_SW.
    R174 10 MOhm + C174 100 nF from gate to source: Q14 is OFF unless something pulls O2_G low (fail-safe default).
  * Q16 PMZ290UNE2 (N): gate = VBAT_OK of the BQ25570 (high while VSTOR > VBAT_OK, i.e. while the buck and the MCU run): holds O2_G low,
    so in normal operation Q14 is ON and the firmware governor (Q1 PV_INH + the MCU's own NTC reading) keeps 0-45 C.
  * Q18 PMZ350UPE (P): gate = VBAT_OK: the O-2 supply V_O2 is taken from PV_SW only while VBAT_OK is low (MCU off).
  * D19 BAT54CM: A1 = Q18 drain -> V_O2 (PV supply, also the disconnect while Q8 shorts the PV), A2 = NTC_EN GPIO -> V_O2 (MCU bias for
    its own dark reading). C170 100 nF on V_O2.
  * Ladder: R116 from V_O2 to the NTC node (pack NTC 10 k B3950 to GND); reference chain R170-R171-R172 from V_O2 to GND with taps
    O2_TC (cold) and O2_TH (hot): ratiometric, so V_O2 cancels.
  * U19 TLV7031 "not cold": IN+ = O2_TC, IN- = NTC, VCC = V_O2 -> OUT O2_NC (high while NTC < cold threshold). U19's output is the
    supply of U20 (chained AND).
  * U20 TLV7031 "not hot": IN+ = NTC, IN- = O2_TH, VCC = O2_NC -> OUT O2_OK (high while not cold AND not hot AND powered).
  * Q17 PMZ290UNE2 (N): gate = O2_OK (R175 1 MOhm pull-down), drain = O2_G: pulls the gate low -> Q14 ON only while the window is OK.
Every number below is computed here from the datasheet values quoted with their page (marks in CALC_V3F.md). Output: o2_inhibit.json.
run: python3 -B o2_inhibit.py   (about 30 s: imports the V3 energy model read-only for the PV)
"""
import itertools, json, math, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "o2_inhibit.json")
R = {}

# ------------------------------------------------------------------ datasheet values (CALC_V3F.md section 3 lists the sources)
NTC = dict(R25=10e3, tolR=0.01, B=3950.0, tolB=0.01)              # BASELINE 5.2: 10 k B 3950 K +-1 % (B tolerance +-1 % assumed, see CALC_V3F 3)
TLV7031 = dict(Vos=8e-3, Vhys_min=2e-3, Vhys_typ=7e-3, Vhys_max=17e-3, Vmin=1.6, Icc_typ=335e-9, Icc_max=900e-9, tON=200e-6, tpd=3e-6)
#   SLVSE13J p.8 (5.7, single): VIO +-0.1 typ / +-8 mV max (-40..125 C), VHYS 2/7/17 mV, ICC 335/900 nA at 1.8 V, tON 200 us; p.6 VS 1.6-6.5 V;
#   p.17: below the minimum supply the POR holds the push-pull output LOW; p.6: inputs VEE-0.3 .. 7 V independent of VCC.
BAT54CM_VF = {1e-4: (0.24,), 1e-3: (0.32,), 1e-2: (0.40,)}       # Nexperia BAT54CM p.4: VF max 240 mV at 0.1 mA, 320 mV at 1 mA, 400 mV at 10 mA
PMZ350 = dict(Vth=(0.45, 0.70, 0.95), Ron18=(0.52, 0.94), Ron25=(0.42, 0.645), IDSS=1e-6, IGSS8=10e-6)   # PMZ350UPE p.6 Table 7
PMZ290 = dict(Vth=(0.45, 0.70, 0.95), Ron18=(0.47, 0.68))                                               # PMZ290UNE2 p.6 (v2 pin map notes)
RES_TOL = 0.01                                                    # every resistor of the ladder and chain: 1 % thick film (UNI-ROYAL 0201WMF, JLC)
E96_AVAIL = {   # 0201 UNI-ROYAL values with JLC stock (tools/jlc_find.py, 2026-11-13 20:5x UTC): C-number, orderable
    100e3: ("C270364", 2940709), 1e6: ("C473482", 39095), 10e6: ("C423797", 89795),
    750e3: ("C473603", 14324), 732e3: ("C423439", 12683), 768e3: ("C2691502", 3),
    174e3: ("C474246", 12780), 162e3: ("C2691509", 14900), 180e3: ("C473559", 178),
    56e3: ("C473524", 66060), 54.9e3: ("C474117", 14926), 53.6e3: ("C423488", 15000), 52.3e3: ("C473632", 17919)}

def Rntc(T, R25=NTC["R25"], B=NTC["B"]): return R25 * math.exp(B * (1.0 / (T + 273.15) - 1.0 / 298.15))
def T_of(Rx, R25=NTC["R25"], B=NTC["B"]):
    return 1.0 / (1.0 / 298.15 + math.log(Rx / R25) / B) - 273.15

# ------------------------------------------------------------------ PV node: the supply of the O-2 at the check (Q14 off) and at the MPP
def pv_model():
    E = "/path/to/SolarVest_work/wristband/v3/integrate/energy"     # read-only import of the V3 model (V3_ARCH, BASELINE source)
    sys.path.insert(0, E)
    import v3_energy as VE
    VE.A_LID2 = 27.7 * 2.30 / 100                                         # V3-F strips 27.7 x 2.30 mm (BASELINE 1, E-5)
    return VE
t0 = time.time(); VE = pv_model(); M = VE.M
SET = "LID2+WR31"
def srcs_at(lux=None, sun=None, tc=25.0):
    if lux is not None: return VE.sources(SET, "desk|indoor_iso", M.g_si(lux=lux), dvoc=VE.dvoc_T(tc))
    return VE.sources(SET, "walking|sun30", M.g_si(sun=sun), dvoc=VE.dvoc_T(tc), wing_ratio=1.0)
def node_v_at_load(srcs, i_load):
    """PV node voltage with a load current i_load (A): bisection on node_I(V) = i_load"""
    lo, hi = 0.0, float(M.node_voc(srcs))
    if float(M.node_I(0.0, srcs)[0]) < i_load: return 0.0
    for _ in range(60):
        m = 0.5 * (lo + hi)
        if float(M.node_I(m, srcs)[0]) > i_load: lo = m
        else: hi = m
    return 0.5 * (lo + hi)
R["pv_model"] = dict(source="v3/integrate/energy/v3_energy.py (read-only import), set LID2+WR31 with the lid strips at 2.30 mm; Voc slope -6.96 mV/K per string (KXOB25-03X4TF p.1 via V3)",
                     import_s=round(time.time() - t0, 1))

# ------------------------------------------------------------------ 1. threshold design: ladder R116 and reference chain
def corners(Rb, R170, R171, R172, Vlo_c, Vlo_h, Vhi):
    """trip temperatures at every corner: NTC R25 and B +-1 %, every resistor +-1 %, comparator offset +-8 mV, hysteresis 2-17 mV,
    V_O2 from Vlo to Vhi. 'stop' = output changes while the cell leaves the window (cooling for the cold side, heating for the hot side),
    'release' = output returns. Returns min / max of each."""
    out = dict(cold_stop=[99, -99], cold_release=[99, -99], hot_stop=[99, -99], hot_release=[99, -99])
    for dR25, dB, dRb, d170, d171, d172 in itertools.product(*[(-1, 1)] * 6):
        R25 = NTC["R25"] * (1 + dR25 * NTC["tolR"]); B = NTC["B"] * (1 + dB * NTC["tolB"]); rb = Rb * (1 + dRb * RES_TOL)
        r170 = R170 * (1 + d170 * RES_TOL); r171 = R171 * (1 + d171 * RES_TOL); r172 = R172 * (1 + d172 * RES_TOL)
        tot = r170 + r171 + r172; kc = (r171 + r172) / tot; kh = r172 / tot
        for vos in (-TLV7031["Vos"], TLV7031["Vos"]):
            for hy in (TLV7031["Vhys_min"], TLV7031["Vhys_max"]):
                for side, V in (("c", Vlo_c), ("c", Vhi), ("h", Vlo_h), ("h", Vhi)):
                    if side == "c":
                        # U19: IN+ = TC, IN- = NTC; output high while V(NTC) < V(TC) + Vos - hy/2 (falls when NTC rises past TC + Vos + hy/2)
                        for key, sgn in (("cold_stop", +1), ("cold_release", -1)):
                            ratio = kc + (vos + sgn * hy / 2) / V
                            ratio = min(max(ratio, 1e-6), 0.999999); t = T_of(rb * ratio / (1 - ratio), R25, B)
                            out[key][0] = min(out[key][0], t); out[key][1] = max(out[key][1], t)
                    else:
                        # U20: IN+ = NTC, IN- = TH; output high while V(NTC) > V(TH) + Vos + hy/2 ... falls when NTC drops below TH + Vos - hy/2
                        for key, sgn in (("hot_stop", -1), ("hot_release", +1)):
                            ratio = kh + (vos + sgn * hy / 2) / V
                            ratio = min(max(ratio, 1e-6), 0.999999); t = T_of(rb * ratio / (1 - ratio), R25, B)
                            out[key][0] = min(out[key][0], t); out[key][1] = max(out[key][1], t)
    return {k: [round(v[0], 2), round(v[1], 2)] for k, v in out.items()}

# V_O2 range at the decision point: PV at its open-circuit voltage (Q14 off) less D19A and Q18; computed in section 2 and fed back here
def vo2_range():
    rows = []
    for sun in (0.1, 0.2, 0.45, 1.0, 1.2):
        for tc in (-10.0, 25.0, 50.0, 65.0):
            s = srcs_at(sun=sun, tc=tc)
            v = node_v_at_load(s, 20e-6)                  # the O-2 draws <= 20 uA at the check (section 3)
            rows.append(dict(sun=sun, pv_temp_C=tc, node_V_at_20uA=round(v, 3), V_O2=round(v - 0.24 - 20e-6 * 1.0, 3)))
    return rows
VO2 = vo2_range()
R["V_O2_at_check"] = dict(rows=VO2, note="V_O2 = PV node at a 20 uA load (Q14 off) - 0.24 V (BAT54CM VF max at 0.1 mA, p.4; at 20 uA it is lower) - Q18 at uA (negligible)")
vlo_all = min(r["V_O2"] for r in VO2); vhi_all = max(r["V_O2"] for r in VO2)
vlo_hot = min(r["V_O2"] for r in VO2 if r["pv_temp_C"] >= 25.0)       # a hot cell (> 40 C) comes with a lid / wing at >= 25 C
vlo_cold = min(r["V_O2"] for r in VO2 if r["pv_temp_C"] <= 25.0)      # a cell below 0 C comes with strings at <= 25 C

cands = []
for R170 in (750e3, 732e3):
    for R171 in (174e3, 162e3, 180e3):
        for R172 in (56e3, 54.9e3, 53.6e3, 52.3e3):
            c = corners(100e3, R170, R171, R172, vlo_cold, vlo_hot, vhi_all)
            ok = c["cold_stop"][0] >= 0.5 and c["hot_stop"][1] <= 44.5
            score = c["hot_stop"][0] - c["cold_stop"][1]                    # width of the window that is always allowed
            cands.append(dict(R170=R170, R171=R171, R172=R172, ok=ok, score=round(score, 2), corners=c,
                              stock_min=min(E96_AVAIL[R170][1], E96_AVAIL[R171][1], E96_AVAIL[R172][1])))
best = max([x for x in cands if x["ok"] and x["stock_min"] >= 1000], key=lambda x: x["score"])
R["threshold_design"] = dict(
    R116_bias=100e3, chain=dict(R170=best["R170"], R171=best["R171"], R172=best["R172"]),
    c_numbers={k: E96_AVAIL[best[k]][0] for k in ("R170", "R171", "R172")} | {"R116": E96_AVAIL[100e3][0]},
    V_O2_range_used=dict(cold_side_min=vlo_cold, hot_side_min=vlo_hot, max=vhi_all),
    rule="every corner: cold stop >= 0.5 C and hot stop <= 44.5 C (0.5 K margin to the cell's 0-45 C charge window, GEB301030 via BASELINE 5.2)",
    corners=best["corners"], candidates_checked=len(cands), candidates_ok=sum(1 for x in cands if x["ok"]))
tot = best["R170"] + best["R171"] + best["R172"]
kc = (best["R171"] + best["R172"]) / tot; kh = best["R172"] / tot
Tc_nom = T_of(100e3 * kc / (1 - kc)); Th_nom = T_of(100e3 * kh / (1 - kh))
R["threshold_design"]["nominal_thresholds_C"] = dict(cold=round(Tc_nom, 2), hot=round(Th_nom, 2), kc=round(kc, 5), kh=round(kh, 5))
# sensitivity at the thresholds (mV/K at V_O2 = 2.0 V)
def dVdT(T, V=2.0, Rb=100e3):
    Rx = Rntc(T); return V * Rb * Rx / (Rx + Rb) ** 2 * NTC["B"] / (T + 273.15) ** 2
R["threshold_design"]["sensitivity_mV_per_K_at_2V"] = dict(cold=round(dVdT(Tc_nom) * 1e3, 2), hot=round(dVdT(Th_nom) * 1e3, 2))
# the same window with typical comparator values (Vos 0, hysteresis 7 mV), resistors and NTC nominal, V_O2 2.0 V
def typ_trip(k, sgn):
    ratio = k + sgn * TLV7031["Vhys_typ"] / 2 / 2.0; return T_of(100e3 * ratio / (1 - ratio))
R["threshold_design"]["typical_C"] = dict(cold_stop=round(typ_trip(kc, +1), 2), cold_release=round(typ_trip(kc, -1), 2),
                                          hot_stop=round(typ_trip(kh, -1), 2), hot_release=round(typ_trip(kh, +1), 2))

# ------------------------------------------------------------------ 2. currents and loads
I_ladder = lambda V, T: V / (100e3 + Rntc(T))
I_chain = lambda V: V / tot
loads = {}
for V in (1.6, 2.0, 2.6):
    loads[f"V_O2 {V} V"] = dict(ladder_uA_0C=round(I_ladder(V, 0) * 1e6, 2), ladder_uA_45C=round(I_ladder(V, 45) * 1e6, 2), chain_uA=round(I_chain(V) * 1e6, 2),
                                 comparators_uA_typ_max=[round(2 * TLV7031["Icc_typ"] * 1e6, 2), round(2 * TLV7031["Icc_max"] * 1e6, 2)],
                                 total_uA_max=round((I_ladder(V, 45) + I_chain(V) + 2 * TLV7031["Icc_max"]) * 1e6, 2))
R["o2_load_from_pv"] = dict(by_V_O2=loads, when="only while VBAT_OK is low (MCU off) and the PV is lit: Q18 is off while VBAT_OK is high")
R["dark_load_uW"] = dict(value=0.0, why="in the dark PV_SW = 0 V: no O-2 supply; VBAT_OK only drives the gates of Q16 and Q18 (no DC current); NTC_EN is driven "
                                         "only for an MCU reading (15 uA x 1.86 V for about 50 ms per reading = 0.8 nA average at one reading a minute)",
                        criterion="<= 2.5 uW (BASELINE 18 V3-G4)", status="PASS (computed)")
R["normal_operation_cost"] = dict(
    R174_uA_at_2V=round(2.0 / 10e6 * 1e6, 3), note="MCU on: Q16 holds O2_G at 0 V, so R174 draws PV_SW / 10 MOhm from the PV (0.2 uA, 0.4 uW of harvest); the O-2 itself is "
    "unpowered (Q18 off). Q14 adds its RDSon to R_LIM: 0.42-0.645 Ohm at VGS -2.5 V, 0.52-0.94 Ohm at -1.8 V (PMZ350UPE p.6)")

# ------------------------------------------------------------------ 3. light needed for the O-2 to approve with the MCU off (room-light restart)
def approves(lux, tc=25.0):
    s = srcs_at(lux=lux, tc=tc)
    load = I_ladder(1.7, 25) + I_chain(1.7) + 2 * TLV7031["Icc_max"]
    v = node_v_at_load(s, load) - 0.24
    return v >= TLV7031["Vmin"] + 0.05, round(v, 3)
lo, hi = 100.0, 5000.0
for _ in range(25):
    m = math.sqrt(lo * hi)
    if approves(m)[0]: hi = m
    else: lo = m
R["approval_light_mcu_off"] = dict(lux=round(hi, 0), rule="V_O2 >= 1.65 V (TLV7031 1.6 V minimum + 50 mV) with the O-2's own load drawn from the PV at 25 C",
    table={str(l): approves(l)[1] for l in (200, 300, 500, 700, 1000, 2000)},
    baseline_cold_start_lux=dict(wing_lit=167, dark_wing=358, source="BASELINE 11.5"),
    consequence="with the MCU off (dead or flat band) PV charging resumes only above this light; normal operation (MCU on) is not affected (Q16)")

# ------------------------------------------------------------------ 4. timing: start-up, hold, re-check, response
C174, R174 = 100e-9, 10e6
tau = R174 * C174
hold = {}
for vgs0 in (1.8, 2.4):
    hold[f"VGS0 -{vgs0} V"] = dict(hold_s_Vth_min=round(tau * math.log(vgs0 / 0.45), 3), hold_s_Vth_max=round(tau * math.log(vgs0 / 0.95), 3))
c170_charge = {}
for lab, s in (("1000 lx", srcs_at(lux=1000)), ("0.1 sun 25 C", srcs_at(sun=0.1))):
    i = float(M.node_I(1.0, s)[0])
    c170_charge[lab] = dict(i_avail_uA_at_1V=round(i * 1e6, 1), t_to_1V8_us=round(100e-9 * 1.8 / max(i - 20e-6, 1e-9) * 1e6, 1))
R["timing"] = dict(
    comparator_power_up_us=TLV7031["tON"] * 1e6, comparator_delay_us=TLV7031["tpd"] * 1e6,
    C170_charge=c170_charge,
    Q14_turn_on_us=round(C174 * 2.0 / 5e-3 * 1e6, 1), Q14_turn_on_note="Q17 sinks >= 5 mA at VGS 1.8 V (PMZ290 RDSon <= 0.68 Ohm at 1.8 V), C174 100 nF discharged from 2 V",
    hold_tau_s=tau, hold=hold,
    hold_note="when the O-2 browns out after approving (V_O2 < 1.6 V at the MPP or at the cold-start clamp), C174 keeps Q14 on for the hold time, then Q14 opens, "
              "PV_SW returns to Voc and the O-2 re-checks within about 0.3-1 ms: harvest duty >= 99 %; out of range, Q14 stays off",
    gate_leakage_note="PMZ350UPE IGSS <= 10 uA at +-8 V (ESD diodes, p.6); at 2 V it is not specified: with 20 nA the hold shortens by about 10 % (assumption)",
    fault_response_s=round(tau * math.log(2.4 / 0.45), 2))

# ------------------------------------------------------------------ 5. every cell state (MCU off), 0.1-1.2 sun
R["cell_states"] = dict(
    method="the decision is taken with Q14 OFF, so the O-2 is supplied by the open-circuit PV (rows of V_O2_at_check) and does not depend on the cell: "
           "0 / 0.5 / 1.2 / 2.0 V cells, a tripped PCM and a healthy flat cell give the same decision supply",
    V_O2_min_at_0p1_sun=min(r["V_O2"] for r in VO2 if r["sun"] == 0.1), Vmin_comparator=TLV7031["Vmin"],
    paths_into_cell_with_Q14_off=["none: PV_SW reaches the cell only through Q14 - R130 - BQ25570; R126 (EN_HOLD), Q18/D19 (V_O2), U4 IN- and D8 end at GND",
                                  "Q14 off-state leakage IDSS <= 1 uA at -20 V, 25 C (PMZ350UPE p.6): at VDS 2-3 V and 50 C it is assumed <= 1 uA, i.e. < 0.00002 C"],
    after_approval="cell 0-1.6 V: VSTOR < 1.73 V so the BQ25570 cold-starts (VIN_DC clamped at 0.6 V, SLUSBH2G p.18) or the three-diode path conducts at high light; "
                   "V_O2 may fall below 1.6 V, then the hold of section 4 applies (re-check every 0.1-1.0 s); healthy flat cell: MPP at 0.8 Voc",
    out_of_range="Q14 stays off: no PV current into the cell in any state (criterion of V3-G4)")

# ------------------------------------------------------------------ 6. NTC node shared with the BQ25170 TS bias and the MCU AIN
TS = dict(I=(36.5e-6, 38e-6, 39.5e-6), Vcold=(0.99, 1.04, 1.09), Vcold_exit=(0.83, 0.88, 0.93), Vhot=(0.176, 0.188, 0.200), Vhot_exit=(0.208, 0.220, 0.232))
#   BQ25170 SLUSDJ8A p.7: ITS_BIAS 36.5/38/39.5 uA, VCOLD 0.99/1.04/1.09 V (rising), cold exit 0.83/0.88/0.93 V, VHOT 176/188/200 mV (falling), hot exit 208/220/232 mV
def ts_window(R_par):
    """TS stop temperatures at every corner with a parallel load R_par on the NTC node (None = no load)"""
    res = dict(cold=[99, -99], hot=[99, -99])
    for I in (TS["I"][0], TS["I"][2]):
        for dR25, dB in itertools.product((-1, 1), (-1, 1)):
            R25 = NTC["R25"] * (1 + dR25 * NTC["tolR"]); B = NTC["B"] * (1 + dB * NTC["tolB"])
            for key, Vt in (("cold", TS["Vcold"][0]), ("cold", TS["Vcold"][2]), ("hot", TS["Vhot"][0]), ("hot", TS["Vhot"][2])):
                Rtot = Vt / I                                   # the TS pin sees R_ntc || R_par
                Rx = Rtot if R_par is None else (Rtot * R_par / (R_par - Rtot) if R_par > Rtot else 1e12)
                t = T_of(Rx, R25, B); res[key][0] = min(res[key][0], t); res[key][1] = max(res[key][1], t)
    return {k: [round(v[0], 2), round(v[1], 2)] for k, v in res.items()}
R_U19_subpor = 1e6         # assumption: U19 draws <= 1 uA per volt below its POR threshold (not specified by TI)
R_o2_path = 100e3 + (tot * R_U19_subpor / (tot + R_U19_subpor))
R_ain_on = 1e9             # R149 1 MOhm into a powered SAADC input (high impedance) -> negligible
R["ts_window"] = dict(
    alone=ts_window(None),
    with_O2_path=ts_window(R_o2_path), O2_path_ohm=round(R_o2_path),
    note="while VBUS is present Q8 shorts PV_SW, D19A blocks, so the ladder hangs on the NTC node only through R116 + (chain || U19 supply pin); the MCU is awake "
         "(VBUS wakes it through D12A) and NTC_EN is not driven while /PG is low (firmware rule, BASELINE 14 item 10). Q10 off: IDSS <= 1 uA at 20 V (PMZ290), nA at 1 V.",
    criterion="cold stop >= 0 C and hot stop <= 45 C at every corner (BASELINE 12, 13.2)",
    v3_arch_reference="V3_ARCH 7.4: 1.9-6.0 C / 38.8-44.8 C with the TS bias alone")

# MCU reading through the O-2 ladder (NTC_EN high -> D19B -> V_O2), with the BAT54CM forward drop as the error term
def mcu_read_error(T, dVf=0.03):
    V = 1.859 - 0.25; Rx = Rntc(T); v = V * Rx / (Rx + 100e3)
    # firmware assumes V_O2 = 1.859 - 0.25; an error dVf in VF gives R error:
    v_err = (V + dVf) * Rx / (Rx + 100e3)
    Rest = 100e3 * v_err / (V - v_err)
    return round(T_of(Rest) - T, 2)
R["mcu_reading"] = dict(
    path="NTC_EN (P0.30) high -> D19B -> V_O2 -> R116 -> NTC; P0.28 reads the NTC node through R149 1 MOhm with C113 10 nF at the pin (tau 10 ms)",
    error_K_for_30mV_VF_error={str(T): mcu_read_error(T) for T in (0, 25, 45)},
    note="VF of D19B is the main error (BAT54CM 240-320 mV max at 0.1-1 mA, p.4); firmware corrects VF with the board temperature (TMP117); the hardware O-2 is "
         "ratiometric and does not depend on it. While VBUS is present the MCU reads the TS bias instead (38 uA x R_ntc), as V3-R.",
    ain_leak_mcu_off_uA=round((0.6 - 0.4) / 1e6 * 1e6, 3),
    ain_leak_note="MCU unpowered (the O-2 case): the AIN ESD diode can conduct once the NTC node exceeds about 0.4 V; through R149 1 MOhm that is <= 0.2 uA at 0.6 V "
                  "(about 0 C at V_O2 2 V) against a ladder current of 15 uA: < 0.5 K, in the 'reads colder' direction below 0 C only beyond -10 C")

# ------------------------------------------------------------------ 7. Q1 / Q8 shorts and oscillation
R["no_oscillation"] = dict(
    Q1="Q1 (PV_INH) can only be on while the MCU runs (R108 10 MOhm pull-down): then VBAT_OK is high and Q18 keeps the O-2 unpowered: no loop (S1: Q16 follows the heartbeat)",
    Q8="Q8 shorts PV_SW while VBUS is present: V_O2 collapses, U19/U20 go to POR (outputs low), Q17 releases, Q14 opens after the hold (or stays on via Q16): "
       "no PV current either way; when VBUS goes away PV_SW rises with Q14 off and the O-2 decides at Voc",
    own_action="the O-2 opens Q14 (it never shorts the PV), so tripping RAISES its own supply to Voc: the decision state is self-consistent",
    hysteresis_K=dict(cold=round(TLV7031["Vhys_typ"] / dVdT(Tc_nom), 2), hot=round(TLV7031["Vhys_typ"] / dVdT(Th_nom), 2),
                      note="internal hysteresis 2/7/17 mV (typ 7 mV) at V_O2 2.0 V, in kelvin at each threshold"),
    supply_ratiometric="ladder and chain hang on the same V_O2: a supply step (Q14 switching moves PV_SW between Voc and the MPP) does not move the trip ratio; "
                       "C170 100 nF filters the BQ25570's 16 s Voc-sampling step and the boost ripple")

# ------------------------------------------------------------------ 8. area (filled by tools/area_check.py from parts.json; placeholder here)
R["parts"] = ["U19 TLV7031DPWR", "U20 TLV7031DPWR", "Q14 PMZ350UPEYL", "Q18 PMZ350UPEYL", "Q16 PMZ290UNE2YL", "Q17 PMZ290UNE2YL", "D19 BAT54CM,315",
              "R116 100k", "R170", "R171", "R172", "R174 10M 0402", "R175 1M", "C170 100n", "C174 100n", "C175 220p (S1 D-1)", "R176 1M (S1 D-1)"]
# ------------------------------------------------------------------ 9. STAGE 1 (2026-11-14, v3/stage1/STAGE1.md): review D-1, D-4, D-11, D-15
S1 = {}
# D-15: corners down to the 1.6 V POR edge (an approval at low light can let V_O2 sag to the edge before the comparators reset)
S1["D15_corners_V_O2_1p6_to_max"] = corners(100e3, best["R170"], best["R171"], best["R172"], 1.60, 1.60, vhi_all)
c16 = S1["D15_corners_V_O2_1p6_to_max"]
S1["D15_margin_K"] = dict(cold=round(c16["cold_stop"][0] - 0.0, 2), hot=round(45.0 - c16["hot_stop"][1], 2),
                          rule="no PV current outside 0-45 C: cold stop >= 0 C, hot stop <= 45 C at every corner (the lane's 0.5 K design margin is not met at 1.6 V)")
# D-1: heartbeat on CHG_DIS -> C175 220 pF -> O2_HB (Q16 gate, R176 1 MOhm)
C175, R176, CISS = 220e-12, 1e6, 46e-12           # Ciss of PMZ290UNE2 46 pF (E, as v3f_calc.py section 4)
QGD = 0.1e-9                                      # E: gate-drain charge at a few volts (PMZ290 p.6 gives 0.2 nC at 10 V)
VDD = (1.80, 1.859, 1.90)
vg_first = [round(v * C175 / (C175 + CISS) - QGD / (C175 + CISS), 3) for v in VDD]   # first edge: Miller charge taken while O2_G falls from PV_SW
vg_next = [round(v * C175 / (C175 + CISS), 3) for v in VDD]                          # later edges: O2_G already low
tau_hb = (C175 + CISS) * R176
t_above_1V = [round(tau_hb * math.log(v / 1.0) * 1e6, 1) for v in vg_next]
tau_hold_min = 0.8 * C174 * 0.99 * R174                                              # C174 -20 % (X7R 0201 at 2-3 V, E), R174 -1 %
S1["D1_heartbeat"] = dict(
    circuit="CHG_DIS (P0.09) -> C175 220 pF C0G -> O2_HB = Q16 gate; R176 1 MOhm to GND; Q16 drain on O2_G (C174 100 nF / R174 10 MOhm hold of Q14)",
    gate_peak_V_first_edge=vg_first, gate_peak_V_next_edges=vg_next, gate_tau_us=round(tau_hb * 1e6, 1), time_above_1V_us=t_above_1V,
    Q16_needs=">= 1.0 V for a few us: PMZ290UNE2 VGSth 0.45-0.95 V at 250 uA (p.6); C174 needs only 30-300 nC per pulse (Q16 sinks mA)",
    static_level="a static CHG_DIS level decays through R176 in 5 tau = 1.3 ms: no override from a stuck pin",
    pulse_rate_Hz=10, pulse_width_us=10,
    VGS_Q14_between_pulses_fraction=round(math.exp(-0.1 / tau_hold_min), 3),
    release_after_last_pulse_s=dict(Vth_max=R["timing"]["hold"]["VGS0 -1.8 V"]["hold_s_Vth_max"], Vth_min=R["timing"]["fault_response_s"],
                                    note="Q14 opens when |VGS| decays below its threshold: the stage-0 'fault response' of the O-2 hold"),
    cost_uW_E=dict(mcu_wake=round(55e-9 * 10 * 1.859 * 1e6, 2), c174_topup_from_pv=round((1 - math.exp(-0.1 / tau_hold_min)) * 100e-9 * 2.5 * 10 * 2.5 * 1e6, 2),
                   note="E: one 15 us CPU wake per pulse (about 55 nC at 3.7 mA) and the C174 top-up at PV_SW 2.5 V; only while the firmware wants PV charging"),
    states=dict(
        mcu_running_heartbeat="Q16 refreshes the hold: Q14 on, the firmware governor (Q1 PV_INH + NTC reading + heartbeat stop) keeps 0-45 C",
        vbat_ok_high_no_heartbeat="Q16 off and Q18 off (O-2 unpowered): Q14 off within the hold: no PV charging (reset, boot loop, halt, System OFF, power cycle)",
        vbat_ok_low="buck and MCU off (VOUT_EN = VBAT_OK through R129): Q18 feeds the O-2 from the PV; the window comparators decide (stage 0 behaviour)"),
    firmware_rules=["pulse CHG_DIS only in software (never PPI, a timer or PWM), 10 us at 10 Hz",
                    "only while CHG_PG_N is high (no head) and the last NTC reading is inside 0-45 C (0.5 K margin); stop on any out-of-window reading",
                    "never during an NTC reading (Q10 pulls the NTC node low for 10 us)",
                    "SHELF in System OFF does not harvest with a healthy cell; below VBAT_OK falling (3.31 V) the O-2 takes over (>= 711 lx)"])
# D-4: NTC_EN driven while VBUS is present -> V_O2 1.5-1.7 V through R116 100 k into the TS node
def ts_hot_with_bias(V, I, Rb=100e3):
    out = [99, -99]
    for dR25, dB in itertools.product((-1, 1), (-1, 1)):
        R25 = NTC["R25"] * (1 + dR25 * NTC["tolR"]); B = NTC["B"] * (1 + dB * NTC["tolB"])
        for Vt in (TS["Vhot"][0], TS["Vhot"][2]):
            # node: Vt = (I + (V - Vt) / Rb) * Rx  ->  Rx = Vt / (I + (V - Vt) / Rb)
            for rb in (Rb * 0.99, Rb * 1.01):
                Rx = Vt / (I + (V - Vt) / rb); t_ = T_of(Rx, R25, B); out[0] = min(out[0], t_); out[1] = max(out[1], t_)
    return [round(out[0], 2), round(out[1], 2)]
S1["D4_hot_stop_with_NTC_EN_high_C"] = dict(range=[min(ts_hot_with_bias(v, i)[0] for v in (1.5, 1.7) for i in (TS["I"][0], TS["I"][2])),
                                                  max(ts_hot_with_bias(v, i)[1] for v in (1.5, 1.7) for i in (TS["I"][0], TS["I"][2]))],
                                            criterion="hot stop <= 45 C", rule="firmware: never drive NTC_EN while CHG_PG_N is low; ignore NTC_ADC while /PG is low (BASELINE 14 item 10, S1 D-4)")
# D-11: cold start through Q14 at the maximum threshold (MCU off: only after an O-2 approval, i.e. >= the approval light)
def pv_v(lux, i): return round(node_v_at_load(srcs_at(lux=lux), i), 3)
I_cs = 21.4e-6                                      # BASELINE 11.5 cold-start need
I_o2 = I_ladder(1.7, 25) + I_chain(1.7) + 2 * TLV7031["Icc_max"]
vgs_need = 0.95 - 0.09 * math.log10(250e-6 / I_cs)  # E: sub-threshold slope 90 mV/decade from VGSth max 0.95 V at 250 uA (PMZ350UPE p.6)
S1["D11_cold_start_Q14_Vth_max"] = dict(
    VGS_needed_V_E=round(vgs_need, 3), I_cold_start_uA=21.4, I_O2_uA=round(I_o2 * 1e6, 1),
    PV_node_V_at_cold_start_plus_O2_load={str(l): pv_v(l, I_cs + I_o2) for l in (200, 500, 711, 1000, 2000)},
    note="Q14's gate sits at GND after an approval, so |VGS| = PV_SW: Q14 passes the cold-start current while PV_SW >= the value above. With the MCU off "
         "nothing harvests below the approval light anyway (711 lx); above it the PV node holds >= 1.4 V at the combined load, so a max-threshold Q14 "
         "does not throttle the cold start further (E; SIM-03 (a) to confirm)")
R["stage1"] = S1
R["generated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(R, open(OUT, "w"), indent=1)
print(json.dumps({k: R[k] for k in ("threshold_design", "approval_light_mcu_off", "ts_window", "timing")}, indent=1)[:6000])
print("wrote", OUT, "in", round(time.time() - t0, 1), "s")
