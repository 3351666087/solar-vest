"""MCU_RF block of SolarBand V3-F (unchanged from V2-B dock_wlcsp except the GPIO map of BASELINE section 6 and P0.18 DISP_CTRL).
RADIO=wlcsp (baseline): nRF52832-CIAA WLCSP-50 with Nordic's "CIAA WLCSP with DC/DC regulator setup" reference circuit
(PS v1.4 Figure 173 / Table 149, p.549) component for component: 0201 parts at the chip, L1 3.3 nH + C3 1.0 pF match.
RADIO=qfn (fallback of REDESIGN 8.3): nRF52832-QFAA QFN-48 with the QFAA reference of v1 (Figure 170 / Table 146, p.546).
Both variants use the same GPIO numbers (same silicon, same firmware), the 2016 32 MHz crystal of v1 (the 1612 part named
in REDESIGN 5.8 fails the nRF52832 ESR limit, CALC.md section 9), the SC-16S 1610 32.768 kHz crystal, a 3-pad pi tuning
network in 0402 (Murata parts with S-parameter files, SIM-09) and the feed of a PRINTED radiator (working decision 7):
SB_ANT=board -> radiator on the main board (AE1, copper only); SB_ANT=lid -> radiator on the lid backsheet, spring-fed (J13).
Nordic designator -> board reference map and deviations: CHANGES.md / design_notes.md section 2. Pin budget: pin_budget.md.
"""
from common import mk, two, wire, NC, CONTACTS, WLCSP, ANT_LID, ABSENT_NETS

# nRF52832 GPIO assignment by port number (the same for the WLCSP and the QFN, pin_budget.md has the reasoning per pin).
# PS v1.4 Tables 5 and 6: P0.22-P0.31 are "low drive, low frequency I/O only" (near the radio) -> only static / slow signals there.
GPIO = {
    "P0.03": "ECG_PWDN", "P0.04": "MOTOR_PWM", "P0.05": "ECG_DRDY",
    "P0.06": "SPI_SCK", "P0.07": "SPI_MOSI", "P0.08": "SPI_MISO",
    "P0.11": "CS_ECG", "P0.12": "CS_PPG", "P0.13": "CS_FLASH", "P0.14": "PPG_INT",
    "P0.15": "I2C_SDA", "P0.16": "I2C_SCL",
    "P0.25": "IMU_INT1",
    "P0.28": "NTC_ADC", "P0.30": "NTC_EN", "P0.31": "PV_INH", "P0.22": "ECG_PWR_EN",
    "P0.27": "PWR_HOLD",     # keeps BQ25570 EN low (run); released = ship mode in the dark [G-4]
    "P0.02": "PWR_CYC",      # hard power-cycle one-shot [G-4, E-09]
    "P0.23": "INA_EN",       # gated INA236 rail [G-11]
    "P0.24": "ALERT_LED",    # skin-hot warning LED D10 (kept until decision 5 (d) is accepted in writing, BASELINE 5.1)
    # [V3F] BASELINE 6 (GPIO budget) + this lane: P0.18 DISP_CTRL replaces the debug UART_TX (the display needs a fifth translated signal)
    "P0.09": "CHG_DIS",      # Q10: TS low -> BQ25170 off (41 C skin); NFC pad, UICR NFCPINS
    "P0.10": "FL_EN",        # Q11 front-light PWM; NFC pad, UICR NFCPINS
    "P0.17": "EXTCOMIN",     # 60 Hz COM inversion by RTC -> PPI -> GPIOTE (inner ball)
    "P0.18": "DISP_CTRL",    # [V3F] display DISP through U21 (was UART_TX; logging goes over SWD / RTT)
    "P0.19": "DISP_EN",      # U16 EN, U17 / U21 VCCA and OE (inner ball)
    "P0.20": "CHG_PG_N",     # BQ25170 /PG: head attached; SENSE wakes System OFF (inner ball)
    "P0.26": "BTN_N",        # side button through Q13, active low, SENSE wake (was IMU_INT2: FIFO threshold moved to INT1)
    "P0.29": "DISP_SCS",     # display chip select (high active) through U17
}
SPARE = []                    # BASELINE 6: no pin is left

def gp(part, port):
    """The pin of `part` whose datasheet name contains the token `port` (e.g. 'P0.18' in 'P0.18/TRACEDATA[0]/SWO')."""
    hits = [p for p in part.pins if port in p.name.split("/")]
    if len(hits) != 1: raise KeyError(f"{part.ref}: port {port} matched {len(hits)} pins")
    return hits[0]

def build(n):
    B = "mcu_rf"; gnd = n.GND; v = n.VDD_1V8
    if WLCSP:
        u6 = mk("NRF52832_CIAA", "U6", B, "BLE SoC nRF52832-CIAA WLCSP-50, DC/DC enabled (Nordic CIAA DC/DC reference, Fig. 173)")
        wire(u6, {"A7": v, "H7": v, "C4": gnd, "C5": gnd, "E3": gnd, "F5": gnd, "D2": gnd, "C3": NC})
    else:
        u6 = mk("NRF52832", "U6", B, "BLE SoC nRF52832-QFAA QFN-48, DC/DC enabled (Nordic QFAA DC/DC reference, Fig. 170)")
        wire(u6, {13: v, 36: v, 48: v, 31: gnd, 45: gnd, 49: gnd, "NC": NC})
    for port, net in GPIO.items(): gp(u6, port).__iadd__(NC if net in ABSENT_NETS else getattr(n, net))   # [G1 L4] a removed block leaves its port unconnected
    for port in SPARE: gp(u6, port).__iadd__(NC)
    gp(u6, "P0.21").__iadd__(n.NRESET); gp(u6, "P0.00").__iadd__(n.XL1); gp(u6, "P0.01").__iadd__(n.XL2)
    wire(u6, {"SWDIO": n.SWDIO, "SWDCLK": n.SWDCLK, "DEC1": n.DEC1, "DEC2": n.DEC2, "DEC3": n.DEC3, "DEC4": n.DEC4, "DCC": n.DCC,
              "XC1": n.XC1, "XC2": n.XC2, "ANT": n.RF_ANT})
    # --- supply decoupling ---
    c100n = "C100n_0201" if WLCSP else "C100n"; c100p = "C100p_0201" if WLCSP else "C100p"; c12p = "C12p_0201" if WLCSP else "C12p_2"
    two(mk(c100n, "C204", B, "Nordic C4 100 nF: DEC1"), n.DEC1, gnd)
    two(mk(c100n, "C205", B, "Nordic C5 100 nF: VDD (ball H7 / pin 13)"), v, gnd)
    two(mk("C4u7_0402", "C209", B, "Nordic C8 (WLCSP) / C9 (QFN) 4.7 uF: VDD (ball A7 / pin 48); 0402 10 V instead of Nordic's 0603 [Lens C 3.1]"), v, gnd)
    two(mk(c100p, "C207", B, "Nordic C7 100 pF NP0: DEC3"), n.DEC3, gnd)
    if WLCSP:
        two(mk(c100p, "C206", B, "Nordic C6 100 pF NP0: DEC2 (fitted in the CIAA reference)"), n.DEC2, gnd)
    else:
        two(mk("C100n", "C208", B, "Nordic C8 100 nF: VDD pin 36"), v, gnd)
        two(mk("C100p", "C206", B, "Nordic C6: DEC2, N.C. in Nordic's QFAA BOM (pad kept, not fitted)", value="DNP", dnp=True), n.DEC2, gnd)
    two(mk("C1u", "C210", B, "Nordic C9 (WLCSP) / C10 (QFN) 1.0 uF 0402: DEC4"), n.DEC4, gnd)
    # --- DC/DC: DCC -> L2 10 uH -> L3 15 nH -> DEC4 (same parts in both reference circuits) ---
    two(mk("L10u_0603", "L202", B, "Nordic L2 10 uH 0603 (IDC >= 50 mA): DC/DC"), n.DCC, n.DCDC_MID)
    two(mk("L15n", "L203", B, "Nordic L3 15 nH 0402: DC/DC HF filter"), n.DCDC_MID, n.DEC4)
    # --- 32 MHz HFXO: 2016 crystal of v1 (ESR <= 80 Ohm, C0 <= 3 pF inside RS_HFXO_3PF <= 100 Ohm); Nordic X1, C1, C2 12 pF ---
    x1 = mk("XTAL32M", "X1", B, "Nordic X1 32 MHz 2016, CL 8 pF (kept: the 1612 C2982342 is 150 Ohm max, over the nRF limit)")
    wire(x1, {"#1": n.XC1, "#3": n.XC2, 2: gnd, 4: gnd})
    two(mk(c12p, "C201", B, "Nordic C1 12 pF NP0: XC1"), n.XC1, gnd)
    two(mk(c12p, "C202", B, "Nordic C2 12 pF NP0: XC2"), n.XC2, gnd)
    # --- 32.768 kHz LFXO: SC-16S 1610, CL 12.5 pF -> 2 x 12.5 - 4 pF pin - 0.5 pF stray = 20.5 -> 20 pF ---
    x2 = mk("XTAL32K_1610", "X2", B, "X2 32.768 kHz SC-16S 1610, CL 12.5 pF, ESR <= 90 k (nRF limits: 12.5 pF, 100 k)")
    wire(x2, {"#1": n.XL1, "#2": n.XL2})
    two(mk("C20p_0201", "C211", B, "LFXO load 20 pF C0G: (20 + 4 + 0.5)/2 = 12.25 pF"), n.XL1, gnd)
    two(mk("C20p_0201", "C212", B, "LFXO load 20 pF C0G"), n.XL2, gnd)
    # --- RF match at the chip: Nordic C3 shunt at ANT, L1 series ---
    if WLCSP:
        two(mk("C1p0_0201", "C203", B, "Nordic C3 1.0 pF 0201 shunt at ANT (ball D1, next to VSS_PA D2) [SIM-09 re-run]"), n.RF_ANT, gnd)
        two(mk("L3n3_0201", "L201", B, "Nordic L1 3.3 nH 0201 series -> 50 Ohm [SIM-09 re-run]"), n.RF_ANT, n.RF_50R)
    else:
        two(mk("C0p8", "C203", B, "Nordic C3 0.8 pF shunt at ANT (pin 30, next to VSS pin 31)"), n.RF_ANT, gnd)
        two(mk("L3n9", "L201", B, "Nordic L1 3.9 nH series -> 50 Ohm"), n.RF_ANT, n.RF_50R)
    # --- pi tuning network for the printed radiator: 3 lands in 0402. The values are the v1 SIM-10 optimum and are only
    #     starting values: gate 3a (SIM-10/11 in the V2-B stack) sets them; the resonance moved down 3.6 % in the review run ---
    two(mk("C100p", "C213", B, "pi-net chip-side shunt land, DNP (tuning) [gate 3a]", value="DNP", dnp=True), n.RF_50R, gnd)
    # [S2c] lid antenna L1 (v3/sim/rf/lid/LID_ANTENNA.md, lead decision 2026-11-15): C215 = 9.0 nH series, L204 = 6.2 nH antenna-side shunt (fitted), C213 DNP
    # [F] final re-tune on the closed board (v3/sim/rf/final/RF_FINAL.md, 2026-11-16): C215 7.6 nH, L204 4.3 nH, C213 stays DNP (bench-tune land)
    two(mk("LQW15AN7N6", "C215", B, "pi-net series 7.6 nH wire-wound on the C215 land (lid antenna L1) [F; S2c 9.0 nH; was 2.1 pF]"), n.RF_50R, n.ANT_FEED)
    two(mk("LQW15AN4N3", "L204", B, "pi-net antenna-side shunt 4.3 nH wire-wound, fitted (lid antenna L1) [F; S2c 6.2 nH; was 1.8 nH]"), n.ANT_FEED, gnd)
    if ANT_LID:
        wire(mk("SPRING", "J13", B, "feed spring finger to the printed radiator on the lid backsheet (gate 3a option 2)"), {1: n.ANT_FEED})
    else:
        # [S2c] AE1 = feed copper + keep-out pocket of the lid strip L1 (board (0,0), rot 0); J40 sits on AE1's FEED copper and touches the strip's pad on the glass
        ae = mk("ANT_LID_L1", "AE1", B, "lid antenna L1: feed leg + J40 spring land in the copper-free pocket (all 6 layers); radiator = printed strip on the glass")
        wire(ae, {"FEED": n.ANT_FEED, "GND": gnd})
        wire(mk("SPRING_BW0019", "J40", B, "feed spring finger to the lid strip L1 contact pad: BW0020AG (C2826518) on AE1's FEED land (the C2826516 land), board (3.30, 1.55), rot 340 [S2c; S2d J-1]"), {1: n.ANT_FEED})
