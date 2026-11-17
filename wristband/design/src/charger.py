"""CHARGER block of SolarBand V3-F (BASELINE.md sections 1, 4, 5.1, 13.2, 13.3; CALC_V3F.md section 1): the BQ25170 linear charger fed
from the two flush contacts in the top rim (elbow-end corner), which mate only with the isolated USB-C magnetic head (accessory, V3-G10).
  contact + (J15 spring finger) == VBUS_K -> D13 ESD761 to GND (at the entry) -> D14 NSR0240 40 V Schottky (a reversed head puts -5 V on
  the contacts: blocks it; BQ25170 IN abs. max -0.3 V, SLUSDJ8A p.4) -> VBUS -> U15 BQ25170 IN (C130 1 uF)
  contact - (J18 spring finger) == GND_K -> D15 TPD1E10B06 to GND [F-1] -> Q20 PMZ290UNE2 (drain GND_K, source GND; gate from VBUS_K via R509 100 k, R510 1 M) [S2b E-2]
  D14 is a 100 V Schottky PMEG10020AELR (SOD123W) [S2b E-4]; D16 NSR0240 clamps VBUS >= -0.3 V (anode GND) [S2b E-5]
  U15: VSET 36 k = 4.10 V (Table 7-1), RISET 10.2 k = 26.2-32.7 mA (KISET 270-330 A*Ohm; S1 D-8), ISET RC 2 k + 4.7 nF (TI SLUAAG9 p.7, below 50 mA),
       TS on the pack NTC (B 3950 K), /PG -> P0.20 (220 k to VDD_1V8), STAT not used (open drain, no pull-up), OUT -> VBAT_IC (C131 1 uF)
  VB_DET = VBUS / 2 (R144 / R145 1 M hold VBUS and VB_DET at 0 V without a head; [S1 D-16] the contact node VBUS_K itself floats behind D14,
       with only the D13 / D14 leakage: the head's pin check and the EOL dummy model it so) -> Q8 (PV short), Q9 (AVDD_EN low: ECG off),
       D12 half A (EN_HOLD: ship-mode wake); D12 half B = button wake (BTN from hmi.py)
  CHG_DIS (P0.09) -> Q10 pulls TS below VTS_ENZ (charge off, firmware: 41 C skin), R146 gate pull-down; [S1 D-1] the same pin carries the
       O-2 heartbeat (short pulses while /PG is high, o2.py C175), which Q10 sees as harmless 10 us TS dips while the BQ25170 is unpowered
"""
from common import mk, two, wire, NC, O2

def build(n):
    B = "charger"; gnd = n.GND
    # ---------------- contacts, ESD, reverse block ----------------
    wire(mk("SPRING", "J15", B, "contact + (VBUS): BW0036BG spring finger under the insert-moulded pin of the top rim (inner face >= 3.4 x 2.2 mm centred on the land, BASELINE E-13)"),
         {1: n.VBUS_K})
    wire(mk("SPRING", "J18", B, "contact - (GND_K): BW0036BG spring finger under the second rim pin (BASELINE calls the pair 'J15'); behind Q20 [S2b E-2]"), {1: n.GND_K})
    # [S2b E-2] the GND contact is no longer board GND: N-FET Q20 in series (drain = contact, source = GND). With a head, VBUS_K drives the gate through
    # R509 / R510 and Q20 is on; the body diode carries the charge return until then. Without a head, a finger on J18 meets an off FET (IDSS), not GND.
    q20 = mk("CJBA7002K", "Q20", B, "GND-contact switch, 60 V N-FET: on only while VBUS_K is driven (head attached); off = a finger on J18 does not reach board GND "
             "[S2b E-2, ECG.md 2c/2d; F-8: was PMZ290UNE2 20 V]")
    wire(q20, {"G": n.GK_G, "S": gnd, "D": n.GND_K})
    two(mk("R100k_0201", "R509", B, "Q20 gate feed 100 k from VBUS_K (gate 4.5 V at a 5.0 V head) [S2b E-2]"), n.VBUS_K, n.GK_G)
    two(mk("R1M_0201", "R510", B, "Q20 gate pull-down 1 M: Q20 off without a head [S2b E-2]"), n.GK_G, gnd)
    d15 = mk("TPD1E10B06", "D15", B, "ESD clamp on the - contact J18 (GND_K) at the pod entry: TPD1E10B06 (same part as D18), bidirectional, IEC 61000-4-2; "
             "protects Q20 (an ESD761 lets Q20 avalanche) [mini-ECO F-1; was ESD761]")
    wire(d15, {1: n.GND_K, 2: gnd})
    d13 = mk("ESD761", "D13", B, "ESD on the + contact at the pod entry: bidirectional, 24 V working, IEC 61000-4-2 +-15 kV (SLVSH10C p.1, p.5) [G-10]")
    wire(d13, {"IO": n.VBUS_K, "GND": gnd})
    d14 = mk("PMEG10020AELR", "D14", B, "reverse-attach block, 100 V Schottky (Nexperia PMEG10020AELR, SOD123W): -5 V head and -15 kV contact ESD blocked; "
             "VF typ about 0.43 V at 33 mA, 25 C (Fig. 4) [S2b E-4: was NSR0240 40 V]")
    wire(d14, {"K": n.VBUS, "A": n.VBUS_K})
    d16 = mk("NSR0240", "D16", B, "VBUS negative clamp, anode GND -> cathode VBUS: holds VBUS above -0.3 V (U15 IN abs. max) against the D14 leakage at -5 V [S2b E-5]")
    wire(d16, {"CATHODE": n.VBUS, "ANODE": gnd})
    # ---------------- U15 BQ25170 ----------------
    u15 = mk("BQ25170", "U15", B, "linear charger 4.10 V / 27-33 mA from the contacts; TS = pack NTC (0-45 C window with B 3950 K); OUT on VBAT_IC (INA_BAT sees the charge)")
    wire(u15, {"IN": n.VBUS, "ISET": n.ISET, "TS": n.NTC, "GND": gnd, "STAT": NC, "/PG": n.CHG_PG_N, "VSET": n.VSET, "OUT": n.VBAT_IC, "EP": gnd})
    two(mk("C1u", "C130", B, "U15 IN 1 uF 25 V (SLUSDJ8A p.3: >= 1 uF close to the IC); absorbs the ESD charge behind D14"), n.VBUS, gnd)
    two(mk("C1u", "C131", B, "U15 OUT 1 uF 25 V (p.3)"), n.VBAT_IC, gnd)
    two(mk("R10k2_0201", "R140", B, "RISET 10.2 k 0.5 % 0201 [G1 L0]: ICHG = 300 A*Ohm / 10.2 k = 29.4 mA (26.2-32.7 mA): <= 0.50 C at a 66 mAh pack with KISET max and R -1 %; "
           "locked to the >= 66 mAh pack with R130 [BASELINE 11.5, FS-1; S1 D-8: was 10.0 k, 0.505 C]"), n.ISET, gnd)
    two(mk("R2k_0201", "R141", B, "ISET RC: 2 k in series with C132, the pair across RISET (TI SLUAAG9 p.7: below 50 mA, R = 2 k, C = 4.7 nF)"), n.ISET, n.ISET_RC)
    two(mk("C4n7_0201", "C132", B, "ISET RC: 4.7 nF X7R 25 V 0201 (TI SLUAAG9 p.7) [G1 L0]"), n.ISET_RC, gnd)
    two(mk("R36k", "R142", B, "VSET 36 k 1 % 100 ppm: 4.10 V (SLUSDJ8A Table 7-1, p.14; <= 200 ppm/C required p.4)"), n.VSET, gnd)
    two(mk("R220k_0201", "R143", B, "/PG pull-up 220 k to VDD_1V8 (open drain; 8.5 uA only while the head charges)"), n.CHG_PG_N, n.VDD_1V8)
    # ---------------- VBUS detector and the hardware interlocks ----------------
    two(mk("R1M_0201", "R144", B, "VBUS divider top 1 M -> VB_DET (2.3 V at 4.6 V)"), n.VBUS, n.VB_DET)
    two(mk("R1M_0201", "R145", B, "VBUS divider bottom 1 M: holds VBUS and VB_DET at 0 V without a head; the contact node VBUS_K floats behind D14 (no drive at rest) [S1 D-16]"), n.VB_DET, gnd)
    q8 = mk("PMZ290UNE2", "Q8", B, "PV short while VBUS is present: PV and USB never charge together (0.43 + 0.40 C would exceed the cell's rating) [BASELINE 11.5, 13.3]")
    wire(q8, {"G": n.VB_DET, "S": gnd, "D": n.PV_SW})
    q9 = mk("PMZ290UNE2", "Q9", B, "AVDD_EN low while VBUS is present: ECG supply off in hardware [BASELINE 13.2, 13.3]")
    wire(q9, {"G": n.VB_DET, "S": gnd, "D": n.AVDD_EN})
    q10 = mk("PMZ290UNE2", "Q10", B, "CHG_DIS: pulls TS below VTS_ENZ (40-60 mV): charger off (firmware: 41 C skin) [BASELINE 12, 14 item 10]")
    wire(q10, {"G": n.CHG_DIS, "S": gnd, "D": n.NTC})
    if O2 == "merged":     # [G1 L0 option] the approval edge of U20 couples through C175 into this node: 10 k keeps the Q10 gate below 0.25 V (calc/o2_dense.py 3.3)
        two(mk("R10k_0201", "R146", B, "CHG_DIS gate pull-down 10 k: charging allowed while the MCU is in reset; holds the Q10 gate below 0.25 V when the O-2 approval edge couples in through C175"), n.CHG_DIS, gnd)
    else:
        two(mk("R1M_0201", "R146", B, "CHG_DIS gate pull-down 1 M: charging allowed while the MCU is in reset; no O-2 heartbeat then (o2.py)"), n.CHG_DIS, gnd)
    # ---------------- ship-mode wake pair ----------------
    d12 = mk("BAV70M", "D12", B, "ship-mode wake into EN_HOLD: half A from VB_DET (head attached), half B from BTN (button pressed); Si pair, IR <= 30 nA at 25 V "
             "(hold node of FIX R-02) [BASELINE 5.1, 16]")
    wire(d12, {"A1": n.VB_DET, "A2": n.BTN, "CC": n.EN_HOLD})
