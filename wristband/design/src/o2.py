"""O-2 hardware PV-charge inhibit and the pack-NTC interface of SolarBand V3-F (BASELINE.md 4, 13.2, 15 G-22, 18 V3-G4).
Design and every number: calc/o2_inhibit.py -> calc/o2_inhibit.json (stage 1) and calc/o2_dense.py -> calc/o2_dense.json (gate-1 level 0),
CALC_V3F.md section 3 and its "Gate 1 level 0" section.

Principle (all variants with an O-2 on the board): the PV reaches R_LIM / the BQ25570 only through Q14 (P-MOSFET, source PV_SW). Q14 is OFF by
default (R174 / C174 gate-source).
  * [S1 D-1] Firmware override only while the firmware RUNS: the gate FET is driven by O2_HB, an AC-coupled heartbeat from CHG_DIS (P0.09).
    The firmware pulses CHG_DIS high for about 10 us at 10 Hz, in software only (never PPI, a timer or PWM), and only while /PG is high and its
    last NTC reading is inside 0-45 C. Each pulse refreshes the C174 hold; when the pulses stop (reset, boot loop, halt, System OFF, power cycle,
    out-of-window reading) Q14 opens after the hold (<= 1.67 s). A static level on CHG_DIS (high = BQ25170 charge stop, BASELINE 14 item 10)
    gives at most one hold period.
  * VBAT_OK high (healthy cell, buck on): Q18 keeps the O-2 unpowered. Without a heartbeat Q14 therefore stays off: a healthy band whose
    firmware is not running does not harvest (fail-safe). The firmware governor (heartbeat + Q1 PV_INH + the MCU's own NTC reading) keeps
    0-45 C while it runs (BASELINE 14 item 11).
  * VBAT_OK low (flat, deep-discharged, PCM tripped, or before boot; the buck and the MCU are off then, R129): Q18 feeds V_O2 from PV_SW
    through D19 half A. The window comparators decide with Q14 still off, i.e. on the open-circuit PV voltage, which does not depend on
    the cell. Only "not cold AND not hot" (U19 powers U20) pulls the gate low. Out of range, or without enough light to run the comparators,
    Q14 stays off: no PV current reaches the cell. The O-2 never shorts the PV, so tripping raises its own supply (no oscillation with Q1 / Q8).
  * Ladder: V_O2 -> R116 100 k -> NTC (pack, 10 k B 3950 K, to GND) and the chain R170 / R171 / R172 -> taps O2_TC, O2_TH: ratiometric.
  * VBUS present: Q8 shorts PV_SW, D19A blocks, the ladder hangs on the NTC node only through R116 + chain (TS window shift: CALC_V3F 3).
  * MCU reading: NTC_EN (P0.30) -> D19 half B -> V_O2 powers the same ladder; P0.28 reads the NTC node through R149 1 M (C113 at the pin).
    [S1 D-4] NTC_EN is never driven while CHG_PG_N is low (it would raise the BQ25170 hot stop to 46-54 C): BASELINE 14 item 10.

SB_O2 = std (baseline): the stage-1 circuit (Q16 heartbeat, Q17 approval, R175 1 M pull-down, C175 220 pF). [G1 level 0] R174 is a 0201 part
    (leakage across it only shortens the hold: fail-safe): 16 parts, 21.3 mm2 (stage 1: 22.1 mm2).
SB_O2 = merged (gate-1 level 0 OPTION, v3/g1/dense/DENSE.md section 4; NOT the baseline): ONE gate FET. Q16 is driven by the heartbeat (C175 1 nF)
    and, through R175 100 k, by the approval output O2_OK of U20; R176 1 M holds the gate low; R146 becomes 10 k (charger.py). Q17 is gone:
    15 parts, 19.3 mm2. Two effects need SIM-03 and a maker's answer before use (calc/o2_dense.py 3.3, 3.4): the approval edge couples into
    CHG_DIS / Q10, and the heartbeat forward-biases the output clamp of the unpowered U20.
SB_O2 = pack: no O-2 on the board (charge-temperature cut-off in the pack PCM, BASELINE 5.3 reserve 3; only with a pack RFQ answer). R130 sits on
    PV_SW (power.py); the MCU biases the NTC through R116 from NTC_EN, as V3-R.
"""
from common import mk, two, wire, NC, O2

def build(n):
    B = "o2"; gnd = n.GND
    # ---------------- MCU AIN on the shared NTC node (every variant) ----------------
    two(mk("R1M_0201", "R149", B, "AIN protection 1 M on the NTC node: TS clamp 2.6 V / unpowered-MCU ESD path <= 0.2 uA [V3F: 100 k -> 1 M, CALC_V3F 3]"), n.NTC, n.NTC_ADC)
    two(mk("C10n", "C113", B, "NTC_ADC SAADC sample reservoir 10 nF (tau 10 ms with R149)"), n.NTC_ADC, gnd)
    if O2 == "pack":
        two(mk("R100k", "R116", B, "NTC bias 100 k 1 % from NTC_EN for the MCU's reading (no O-2 on the board: SB_O2=pack) [BASELINE 5.3 reserve 3]"), n.NTC_EN, n.NTC)
        return
    # ---------------- actuator and its gate ----------------
    q14 = mk("PMZ350UPE", "Q14", B, "O-2 series PV switch PV_SW -> PV_Q (-> R130): OFF unless O2_G is pulled low; adds 0.4-0.9 Ohm to R_LIM [V3F O-2]")
    wire(q14, {"G": n.O2_G, "S": n.PV_SW, "D": n.PV_Q})
    two(mk("R10M_0201", "R174", B, "Q14 gate-source 10 M 0201: default OFF (fail-safe); leakage across it only shortens the hold [G1 L0: was 0402]"), n.O2_G, n.PV_SW)
    two(mk("C100n_0201", "C174", B, "Q14 gate-source hold 100 nF: keeps an approval for 0.64-1.67 s when the O-2 browns out (re-check cycle, CALC_V3F 3)"), n.O2_G, n.PV_SW)
    if O2 == "merged":
        q16 = mk("PMZ290UNE2", "Q16", B, "O-2 gate FET: pulls O2_G low on a heartbeat pulse (C175) or while U20 approves (R175); no heartbeat and no approval = Q14 off [S1 D-1; G1 L0 option: Q17 merged]")
        wire(q16, {"G": n.O2_HB, "S": gnd, "D": n.O2_G})
        two(mk("C1n_0201", "C175", B, "heartbeat coupling 1 nF C0G from CHG_DIS: a 10 us pulse holds O2_HB >= 1.5 V (tau 95 us with R175 || R176); a static level decays [S1 D-1; G1 L0: was 220 pF]"),
            n.CHG_DIS, n.O2_HB)
        two(mk("R1M_0201", "R176", B, "O2_HB pull-down 1 M: Q16 off without a heartbeat and without an approval [S1 D-1]"), n.O2_HB, gnd)
        two(mk("R100k_0201", "R175", B, "approval series 100 k from U20 OUT: O2_HB = 0.91 x V_O2 while U20 approves (>= 1.45 V at the 1.6 V POR edge); isolates the heartbeat from U20's output [G1 L0]"),
            n.O2_OK, n.O2_HB)
    else:
        q16 = mk("PMZ290UNE2", "Q16", B, "firmware override: each heartbeat edge on O2_HB pulls O2_G low and refreshes the C174 hold; no heartbeat = no override [S1 D-1]")
        wire(q16, {"G": n.O2_HB, "S": gnd, "D": n.O2_G})
        two(mk("C220p_0201", "C175", B, "heartbeat coupling 220 pF C0G from CHG_DIS: a rising edge lifts O2_HB to >= 1.2 V for about 0.1 ms; a static level decays (tau 0.27 ms) [S1 D-1]"),
            n.CHG_DIS, n.O2_HB)
        two(mk("R1M_0201", "R176", B, "O2_HB pull-down 1 M: Q16 off without a heartbeat (MCU in reset, halted, off, or a static CHG_DIS level) [S1 D-1]"), n.O2_HB, gnd)
        q17 = mk("PMZ290UNE2", "Q17", B, "O-2 approval: O2_OK high (not cold AND not hot) pulls the Q14 gate low")
        wire(q17, {"G": n.O2_OK, "S": gnd, "D": n.O2_G})
        two(mk("R1M_0201", "R175", B, "Q17 gate pull-down 1 M: no approval while U20 is unpowered"), n.O2_OK, gnd)
    # ---------------- supply of the comparators and the ladder ----------------
    q18 = mk("PMZ350UPE", "Q18", B, "O-2 supply gate: on only while VBAT_OK is low (buck and MCU off); off = no O-2 load on the PV while the cell is healthy")
    wire(q18, {"G": n.VBAT_OK, "S": n.PV_SW, "D": n.O2_PV})
    d19 = mk("BAT54CM", "D19", B, "V_O2 OR: half A from the PV (also the disconnect while Q8 shorts the PV), half B from NTC_EN (MCU bias for its own reading)")
    wire(d19, {"A1": n.O2_PV, "A2": n.NTC_EN, "CC": n.V_O2})
    two(mk("C100n_0201", "C170", B, "V_O2 reservoir 100 nF"), n.V_O2, gnd)
    # ---------------- ladder (ratiometric) ----------------
    two(mk("R100k", "R116", B, "NTC bias 100 k 1 % from V_O2 (O-2 ladder and the MCU's reading) [V3F: was 10 k from NTC_EN]"), n.V_O2, n.NTC)
    two(mk("R732k_0201", "R170", B, "O-2 chain top 732 k 1 %"), n.V_O2, n.O2_TC)
    two(mk("R162k_0201", "R171", B, "O-2 chain 162 k 1 %: O2_TC = 0.2265 V_O2 (cold threshold 2.6 C nominal)"), n.O2_TC, n.O2_TH)
    two(mk("R53k6_0201", "R172", B, "O-2 chain bottom 53.6 k 1 %: hot stop <= 45.0 C down to a 1.30 V supply [S2b, LEAD_NOTES 2b; was 52.3 k]"), n.O2_TH, gnd)
    # ---------------- window comparators (chained AND) ----------------
    u19 = mk("TLV7031", "U19", B, "O-2 'not cold': OUT high while NTC < O2_TC; OUT is the supply of U20 (POR holds OUT low below 1.6 V)")
    wire(u19, {"OUT": n.O2_NC, "VCC": n.V_O2, "VEE": gnd, "IN-": n.NTC, "IN+": n.O2_TC})
    u20 = mk("TLV7031", "U20", B, "O-2 'not hot': OUT high while NTC > O2_TH and U19 says not cold" + ("; drives the gate FET Q16 through R175" if O2 == "merged" else ""))
    wire(u20, {"OUT": n.O2_OK, "VCC": n.O2_NC, "VEE": gnd, "IN-": n.O2_TH, "IN+": n.NTC})
