"""POWER block of SolarBand V3-F (v3/decide/BASELINE.md sections 3, 4, 5.1; numbers in CALC_V3F.md / calc/*.py).
Kept from V2-B dock_wlcsp: BQ25570 MPPT harvester + 1.859 V buck, MOhm dividers on GND_PMIC (net tie at U1 pin 15), PV input chain
PV+ -> D8 TVS -> RSH1 1 Ohm (INA_PV) -> PV_SW (Q1 PV_INH probe), INA236 x2 on a gated rail (U13), EN self-hold / ship mode (Q4),
VOUT_EN power-cycle one-shot (Q5) with the VDD_1V8 discharge path (Q7), U12 VSTOR load switch, VLED = VSTOR_SW through R117 3.3 Ohm,
TPS7A2030 AVDD_ECG LDO.
[V3F] changes (CHANGES_V3F.md): the cell, its protector U14 / R132 / C123 and the cell-tab pads leave the board (protected pack on strap root A,
entry lands in io_block.py); R130 R_LIM = 12 Ohm 1 % 1206 (C17913), now after the O-2 series switch Q14 (o2.py): PV_SW -> Q14 -> PV_Q -> R130 -> VIN_DC;
R108 / R131 10 MOhm (C144806); U3 EN through R123 so that Q9 (charger.py) can force the ECG supply off while VBUS is present; the NTC bias moved to o2.py.
"""
from common import mk, two, wire, NC, INA_KEY, RLIM_KEY, VARIANT, O2

def build(n):
    B = "power"; gnd, gpm = n.GND, n.GND_PMIC
    # ---------------- U1 BQ25570 (SLUSBH2G Fig. 24; VOC_SAMP = VSTOR -> 80 % FOCV) ----------------
    u1 = mk("BQ25570", "U1", B, "MPPT harvester + 1.859 V buck; EN = self-hold node (ship mode), VOUT_EN behind R129; VBAT_OK also gates the O-2 (o2.py)")
    wire(u1, {1: gnd, "VIN_DC": n.VIN_DC, "VOC_SAMP": n.VSTOR, "VREF_SAMP": n.VREF_SAMP, "EN": n.BQ_EN,
              "VOUT_EN": n.VOUT_EN, "VBAT_OV": n.VBAT_OV, "VRDIV": n.VRDIV, 9: gnd, "OK_HYST": n.OK_HYST,
              "OK_PROG": n.OK_PROG, "VOUT_SET": n.VOUT_SET, "VBAT_OK": n.VBAT_OK, "VOUT": n.VDD_1V8, 15: gnd,
              "LBUCK": n.LBUCK, 17: gnd, "VBAT": n.VBAT_IC, "VSTOR": n.VSTOR, "LBOOST": n.LBOOST, "PowerPAD": gnd})
    two(mk("L22u", "L1", B, "Boost inductor 22 uH (datasheet L1)"), n.VIN_DC, n.LBOOST)
    two(mk("L10u", "L2", B, "Buck inductor 10 uH (datasheet L2)"), n.LBUCK, n.VDD_1V8)
    two(mk("C4u7_0603", "C101", B, "CIN 4.7 uF on VIN_DC, after R_LIM - do not enlarge (R-PMIC-2)"), n.VIN_DC, gnd)
    two(mk("C10u_0603", "C102", B, "CSTOR 10 uF on VSTOR (to pin 1)"), n.VSTOR, gnd)
    two(mk("C100n", "C103", B, "CBYP 0.1 uF on VSTOR (first priority at pin 19-pin 1)"), n.VSTOR, gnd)
    two(mk("C10n_C0G_0402", "C104", B, "CREF 10 nF C0G 0402 low leakage (MPPT hold 16 s) -> GND_PMIC [G1 L0: was 0603; same C0G insulation class]"), n.VREF_SAMP, gpm)
    for i, r_ in enumerate(("C105", "C114", "C115", "C116", "C117")):
        two(mk("C22u_0402", r_, B, f"COUT {i + 1}/5: 22 uF 0402 on VDD_1V8 [SIM-06 re-run with the 0402 DC-bias curve]"), n.VDD_1V8, gnd)
    two(mk("C22u_0603", "C106", B, "CBAT 22 uF local bypass at U1 VBAT"), n.VBAT_IC, gnd)
    # threshold dividers (SLUSBH2G eq. 2-5, VBIAS 1.21 V); bottoms to GND_PMIC (R-PMIC-1)
    two(mk("R5M76", "R101", B, "ROV1 (VBAT_OV divider, bottom)"), n.VBAT_OV, gpm)
    two(mk("R7M32", "R102", B, "ROV2 (VBAT_OV divider, top) -> VBAT_OV 4.122 V"), n.VRDIV, n.VBAT_OV)
    two(mk("R3M92", "R103", B, "ROK1 3.92 M (VBAT_OK divider, bottom)"), n.OK_PROG, gpm)
    two(mk("R6M81", "R104", B, "ROK2 6.81 M -> VBAT_OK 3.312 V falling"), n.OK_HYST, n.OK_PROG)
    two(mk("R383k", "R105", B, "ROK3 383 k: VBAT_OK hysteresis 118 mV, no chatter [S2b, LEAD_NOTES 2b; was 294 k]"), n.VRDIV, n.OK_HYST)
    two(mk("R7M50", "R106", B, "ROUT1 7.50 M (VOUT divider, bottom)"), n.VOUT_SET, gpm)
    two(mk("R4M02", "R107", B, "ROUT2 4.02 M (VOUT divider, top) -> VOUT 1.859 V [G-5 / E-06]"), n.VRDIV, n.VOUT_SET)
    two(mk("NETTIE", "NT1", B, "GND_PMIC star: joins GND only at U1 VSS pin 15 (R-PMIC-1)"), gpm, gnd)

    # ---------------- PV input: TVS, shunt, PV_INH probe; the series limiter follows the O-2 switch Q14 (o2.py) ----------------
    d8 = mk("TPD1E10B06", "D8", B, "TVS on PV+ (lid tail and wing root B), on the PV side of RSH1 [G-10 / E-20; SIM-08 with the PV node]")
    wire(d8, {1: n.PV_NODE, 2: gnd})
    two(mk("R1R_01", "R111", B, "RSH1 PV shunt 1.00 Ohm 0.1 % (INA_PV): lid + wing current"), n.PV_NODE, n.PV_SW)
    q1 = mk("PMZ290UNE2", "Q1", B, "PV_INH: shorts the PV after RSH1 (harvest inhibit of the W-C band, Isc probe, firmware 0-45 C governor) [N-3]")
    wire(q1, {"G": n.PV_INH, "S": gnd, "D": n.PV_SW})
    two(mk("R10M_0201", "R108", B, "RQ1 gate pull-down 10 M 0201: harvesting by default with the MCU off [V3F: 1 M -> 10 M; G1 L0: 0201, leakage across it only strengthens the pull-down]"), n.PV_INH, gnd)
    # [V3F] 12 Ohm 1 %, locked to a >= 66 mAh-nominal / >= 60 mAh-minimum pack (BASELINE 11.5, CALC_V3F 2); Q14 adds 0.4-0.9 Ohm in series.
    # [G1 L0] 0805 125 mW (C17445): the PV is current-limited, so R130 never sees more than 52 mW (1.2 sun, -10 C) = 42 % of the rating (was 1206 250 mW).
    # SB_O2=pack: no Q14 on the board, R130 sits directly on PV_SW.
    two(mk(RLIM_KEY, "R130", B, "R_LIM 12 Ohm 0805 125 mW between the O-2 switch Q14 (PV_Q) and VIN_DC: hardware charge-current limit, <= 52 mW; locked to the pack (BOM kit, EOL check) [G-15, BASELINE 11.5]"),
        n.PV_SW if O2 == "pack" else n.PV_Q, n.VIN_DC)

    # ---------------- INA236 x2 on the gated rail INA_VS (Table 7-1: A0 = GND 0x40, A0 = VS 0x41) ----------------
    def ina(ref, a0, inp, inn, func, cref):
        u = mk(INA_KEY, ref, B, func)
        wire(u, {"IN+": inp, "IN-": inn, "GND": gnd, "VS": n.INA_VS, "SCL": n.I2C_SCL, "SDA": n.I2C_SDA, "A0": a0, "ALERT": NC})
        two(mk("C100n", cref, B, f"{ref} VS bypass 0.1 uF (SBOSA81D section 9.4)"), n.INA_VS, gnd)
    ina("U4", gnd, n.PV_NODE, n.PV_SW, "INA_PV 0x40: PV current in RSH1 (lid + wing), bus = PV_SW", "C107")
    ina("U5", n.INA_VS, n.VBAT_IC, n.BATT_P, "INA_BAT 0x41: pack net current (+ = charging, PV and USB), bus = BATT_P: the motor's VBAT >= 3.60 V rule reads it", "C108")
    two(mk("R1R_01", "R112", B, "RSH2 battery shunt 1.00 Ohm 0.1 % (INA_BAT)"), n.VBAT_IC, n.BATT_P)
    u13 = mk("SIP32431DNP3", "U13", B, "INA rail switch VDD_1V8 -> INA_VS, ON = INA_EN: both INA236 unpowered in SHELF [G-11, Lens B E4]")
    wire(u13, {"IN": n.VDD_1V8, "OUT": n.INA_VS, "ON/OFF": n.INA_EN, 2: gnd, 5: gnd})
    two(mk("R10M_0201", "R131", B, "INA_EN pull-down 10 M 0201: rail off while the MCU is in reset [V3F: 1 M -> 10 M; G1 L0: 0201]"), n.INA_EN, gnd)

    # ---------------- U12 VSTOR load switch (SIM-03a) and the VOUT_EN node ----------------
    u12 = mk("SIP32431DNP3", "U12", B, "VSTOR -> VSTOR_SW load switch (TDFN4), ON = VOUT_EN delayed (off during cold start) [SIM-03a]")
    wire(u12, {"IN": n.VSTOR, "OUT": n.VSTOR_SW, "ON/OFF": n.SW_ON, 2: gnd, 5: gnd})
    two(mk("C1u_0201", "C119", B, "U12 IN bypass 1 uF 0201 10 V (SiP32431 p.3); the bulk on this net is C102 10 uF [G1 L0]"), n.VSTOR, gnd)
    two(mk("R47k_0201", "R129", B, "VBAT_OK -> VOUT_EN series 47 k: lets Q5 pull the enable node low [G-4; FIX R-17a]"), n.VBAT_OK, n.VOUT_EN)
    two(mk("R1M", "R124", B, "U12 ON delay 1 M from VOUT_EN"), n.VOUT_EN, n.SW_ON)
    two(mk("C10n", "C120", B, "U12 ON delay 10 nF (t ~ 6 ms to VIH)"), n.SW_ON, gnd)
    # ---------------- LED supply straight from the cell: VSTOR_SW -> R117 3.3 Ohm -> VLED ----------------
    two(mk("R3R3", "R117", B, "LED supply series R 3.3 Ohm VSTOR_SW -> VLED [P-6; SIM-06 re-run]"), n.VSTOR_SW, n.VLED)
    two(mk("C22u_0402", "C118", B, "LED reservoir 22 uF at the LED anodes: NOT FITTED (0402 land kept; 22 uF 0402 = C105226) [P-6; FIX R-08; G1 L0: land 0603 -> 0402]", dnp=True), n.VLED, gnd)

    # ---------------- U3 TPS7A2030 AVDD_ECG 3.0 V; EN through R123 so that Q9 (VBUS) overrides it [V3F] ----------------
    u3 = mk("TPS7A2030", "U3", B, "AVDD_ECG LDO 3.0 V, on only during ECG sessions; forced off by Q9 while VBUS is present [SIM-06, BASELINE 13.3]")
    wire(u3, {"IN": n.VSTOR_SW, "GND": gnd, "EN": n.AVDD_EN, "OUT": n.AVDD_ECG, "ThermalPad": gnd})
    two(mk("C1u", "C111", B, "U3 CIN 1 uF; also U12 output bypass"), n.VSTOR_SW, gnd)
    two(mk("C1u", "C112", B, "U3 COUT 1 uF"), n.AVDD_ECG, gnd)
    two(mk("R220k_0201", "R123", B, "ECG_PWR_EN -> AVDD_EN series 220 k: EN 1.29 V against the 500 k internal pull-down before start, Q9 overrides it [V3F]"), n.ECG_PWR_EN, n.AVDD_EN)

    # ---------------- G-4 ship mode: EN self-hold. EN = VBAT (ship, < 5 nA) unless Q4 pulls it low. ----------------
    # Q4 is on while the MCU holds PWR_HOLD (D9), while the PV node is up (R126), while VBUS is present (D12 half A) or while the button is
    # pressed (D12 half B) - D12 lives in charger.py. C121 x R126 keeps Q4 on through an MCU reset.
    two(mk("R10M_0201", "R125", B, "EN pull-up 10 M 0201 to the VBAT pin: EN(H) >= VBAT - 0.2 V needs <= 20 nA of leakage on BQ_EN [G-4; G1 L0: 0201, leakage across it only strengthens the pull-up]"), n.VBAT_IC, n.BQ_EN)
    q4 = mk("PMZ290UNE2", "Q4", B, "EN hold: on = BQ25570 enabled; off = ship mode [G-4, E-03 c/d, E-31]")
    wire(q4, {"G": n.EN_HOLD, "S": gnd, "D": n.BQ_EN})
    d9 = mk("BAS521", "D9", B, "PWR_HOLD -> EN_HOLD (MCU keeps the harvester enabled in the dark)")
    wire(d9, {"A": n.PWR_HOLD, "K": n.EN_HOLD})
    two(mk("R3M3_0201", "R126", B, "EN_HOLD <- PV node 3.3 M: wake by light (>= 200 lx); in the dark it is the gate pull-down [G-4; FIX R-02, R-13]"), n.EN_HOLD, n.PV_NODE)
    two(mk("C4u7_0402", "C121", B, "EN_HOLD hold capacitor 4.7 uF (tau 15.5 s with R126) [FIX R-02]"), n.EN_HOLD, gnd)
    # ---------------- G-4 hard power-cycle: Q5 pulls VOUT_EN (and, through R124, SW_ON) low for a self-timed interval ----------------
    q5 = mk("PMZ290UNE2", "Q5", B, "power-cycle one-shot: buck and VSTOR_SW off while CYC_G is charged [G-4, E-09]")
    wire(q5, {"G": n.CYC_G, "S": gnd, "D": n.VOUT_EN})
    d11 = mk("BAS521", "D11", B, "PWR_CYC -> CYC_A: no back-current into the unpowered MCU pin [FIX R-17a]")
    wire(d11, {"A": n.PWR_CYC, "K": n.CYC_A})
    two(mk("R4k7", "R127", B, "CYC_A -> CYC_G 4.7 k: gate charge current <= 0.33 mA, tau 4.7 ms [FIX R-02]"), n.CYC_A, n.CYC_G)
    two(mk("R1M", "R128", B, "CYC_G discharge 1 M: off interval tau 1 s with C122 [FIX R-02]"), n.CYC_G, gnd)
    two(mk("C1u_0201", "C122", B, "power-cycle timer 1 uF 0201 10 V (off interval 0.5-1 s with R128) [FIX R-02; G1 L0]"), n.CYC_G, gnd)
    q7 = mk("PMZ290UNE2", "Q7", B, "VDD_1V8 discharge while the one-shot is active: the rail falls to 0 V, a real power-cycle [FIX R-02]")
    wire(q7, {"G": n.CYC_G, "S": gnd, "D": n.VDD_DIS})
    two(mk("R100R_0201", "R133", B, "VDD_1V8 discharge 100 Ohm 0201 50 mW (<= 35 mW peak, <= 0.5 mJ per event) [FIX R-02; G1 L0]"), n.VDD_1V8, n.VDD_DIS)
