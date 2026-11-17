"""ECG block of SolarBand V2-B: ADS1291 single-lead (Lead I) with RLD, unchanged from v1 at the AFE (REDESIGN 8.1: front end,
2 x 330 kOhm per electrode and the 3.0 V LDO are untouched). Each electrode: TVS at the contact -> 330 k -> 330 k -> AFE pin.
V2-B changes: E1 / E2 are titanium plates in the floor, each joined to the board by TWO silver-epoxy dots on two separate
ENIG pads (io_block.py E11/E12, E21/E22); the second pad reaches the electrode net through a 100 Ohm link (R318, R319), so
the dot loop pad A -> plate -> pad B can be measured between two test pads at EOL-1 (100 Ohm = a dot is open) while both
dots stay in circuit. E3 is a strip on the top rim, contacted by a spring finger (io_block.py). The hardware cradle
interlock (dual NPN Q2) exists only with CHARGE=contacts and lives in power.py. C_CM / C_DIFF, CEXT and Rz keep the v1
SIM-07 values; SIM-07 must be re-run with the plate capacitance and the PV-to-finger path (REDESIGN 5.7) before M2 is claimed.
"""
from common import mk, two, wire, NC

def build(n):
    B = "ecg"; gnd = n.GND
    u7 = mk("ADS1291", "U7", B, "ECG AFE, internal oscillator + reference")
    wire(u7, {"PGA1N": n.PGA1N, "PGA1P": n.PGA1P, "IN1N": n.ECG_INN, "IN1P": n.ECG_INP,
              "IN2N": n.AVDD_ECG, "IN2P": n.AVDD_ECG,                       # unused analog inputs -> AVDD (note 1)
              "PGA2N": n.PGA2N, "PGA2P": n.PGA2P, "VREFP": n.ECG_VREFP, "VREFN": gnd,
              "VCAP1": n.ECG_VCAP1, "AVDD": n.AVDD_ECG, "AVSS": gnd, "CLKSEL": n.VDD_1V8,   # CLKSEL = 1: internal osc (Table 9)
              "PWDN/RESET": n.ECG_PWDN, "START": n.ECG_START, "CLK": n.ECG_CLK, "CS": n.CS_ECG, "DIN": n.SPI_MOSI,
              "SCLK": n.SPI_SCK, "DOUT": n.SPI_MISO, "DRDY": n.ECG_DRDY, "DVDD": n.VDD_1V8, "DGND": gnd,
              "GPIO2/RCLK2": n.ECG_GPIO2, "GPIO1/RCLK1": n.ECG_GPIO1, "VCAP2": n.ECG_VCAP2,
              "RLDINV": n.RLD_INV, "RLDIN/RLDREF": n.AVDD_ECG,              # RLDREF internal (AVDD+AVSS)/2; pin unused -> AVDD
              "RLDOUT": n.RLD_OUT, "RESP_MODP/IN3P": n.AVDD_ECG, "RESP_MODN/IN3N": n.AVDD_ECG, "PowerPad": gnd})
    # --- electrode networks (section 7.3: TVS -> 330 k -> 330 k -> filter -> AFE) ---
    def electrode(tvs, ra, rb, pad, mid, node, name):
        d = mk("TPD1E10B06", tvs, B, f"ESD clamp at the {name} landing pad"); wire(d, {1: pad, 2: gnd})
        two(mk("R330k_PA", ra, B, f"{name} patient-current limit, 1st 330 k (pad side) [mini-ECO F-2: E-3 withdrawn]"), pad, mid)
        two(mk("R330k_PA", rb, B, f"{name} patient-current limit, 2nd 330 k [mini-ECO F-2]"), mid, node)
    electrode("D5", "R301", "R302", n.E1_PAD, n.E1_MID, n.ECG_INP, "E1 (IN+, back, wearing wrist)")
    electrode("D6", "R303", "R304", n.E3_PAD, n.E3_MID, n.ECG_INN, "E3 (IN-, top-rim strip, finger)")
    electrode("D7", "R305", "R306", n.E2_PAD, n.E2_MID, n.RLD_OUT, "E2 (RLD, back)")
    # dot-loop links (REDESIGN 5.5 "two separate ENIG pads joined through a sky-side test link", build review B-14)
    two(mk("R100R", "R318", B, "E1 dot-loop link 100 Ohm: pad E12 -> electrode net; loop measured TP1-TP2 at EOL-1"), n.E1_PAD, n.E1_LINK)
    two(mk("R100R", "R319", B, "E2 dot-loop link 100 Ohm: pad E22 -> electrode net; loop measured TP3-TP4 at EOL-1"), n.E2_PAD, n.E2_LINK)
    # SIM-07: every pF of C_CM/C_DIFF worsens attenuation and 50 Hz CM->DM; RF is already -130 dB at 2.4 GHz -> DNP, pads kept
    two(mk("C22p_0201", "C301", B, "C_CM+ DNP (pad kept) [SIM-07]", value="DNP", dnp=True), n.ECG_INP, gnd)
    two(mk("C22p_0201", "C302", B, "C_CM- DNP (pad kept) [SIM-07]", value="DNP", dnp=True), n.ECG_INN, gnd)
    two(mk("C100p_0201", "C303", B, "C_DIFF DNP (pad kept) [SIM-07]", value="DNP", dnp=True), n.ECG_INP, n.ECG_INN)
    # --- RLD amplifier feedback (SIM-07 stage 2 choice): RLDOUT -> Rz 470 k -> CEXT 150 pF -> RLDINV; REXT DNP (10 M fallback) ---
    two(mk("R10M_0201", "R307", B, "RLD REXT DNP (pad kept; 10 M fallback) [SIM-07]", value="DNP", dnp=True), n.RLD_INV, n.RLD_OUT)
    two(mk("C150p_0201", "C304", B, "RLD CEXT 150 pF C0G (RLDINV side) [SIM-07: PM >= 55.4 deg]"), n.RLD_INV, n.RLD_Z)
    two(mk("R470k_0201", "R317", B, "RLD Rz 470 k in series with CEXT (RLDOUT side) [SIM-07]"), n.RLD_Z, n.RLD_OUT)
    # --- 2-electrode fallback (section 7.2): R_BIAS 10 M RLDOUT -> IN+/IN-, DNP ---
    two(mk("R10M_0201", "R308", B, "R_BIAS+ 10 M, 2-electrode variant only", value="DNP", dnp=True), n.RLD_OUT, n.ECG_INP)
    two(mk("R10M_0201", "R309", B, "R_BIAS- 10 M, 2-electrode variant only", value="DNP", dnp=True), n.RLD_OUT, n.ECG_INN)
    # --- PGA anti-alias, reference and bypass capacitors (Fig. 73 single-supply) ---
    two(mk("C4n7_C0G_0402", "C305", B, "CFILTER PGA1 4.7 nF C0G 50 V 0402 [G1 L0: was 0603]"), n.PGA1P, n.PGA1N)
    two(mk("C4n7_C0G_0402", "C306", B, "CFILTER PGA2 4.7 nF C0G 50 V 0402 [G1 L0: was 0603]"), n.PGA2P, n.PGA2N)
    two(mk("C10u", "C307", B, "VREFP-VREFN 10 uF"), n.ECG_VREFP, gnd)
    two(mk("C100n", "C308", B, "VREFP-VREFN 0.1 uF"), n.ECG_VREFP, gnd)
    two(mk("C1u", "C309", B, "VCAP1 1 uF"), n.ECG_VCAP1, gnd)
    two(mk("C1u", "C310", B, "VCAP2 1 uF"), n.ECG_VCAP2, gnd)
    two(mk("C1u", "C311", B, "AVDD 1 uF"), n.AVDD_ECG, gnd)
    two(mk("C100n", "C312", B, "AVDD 0.1 uF"), n.AVDD_ECG, gnd)
    two(mk("C1u_0201", "C313", B, "DVDD 1 uF 0201 10 V (the rail carries 5 x 22 uF) [G1 L0]"), n.VDD_1V8, gnd)
    two(mk("C100n", "C314", B, "DVDD 0.1 uF"), n.VDD_1V8, gnd)
    # --- unused digital pins: series R to DGND (section 8.5.1.7); CLK is 3-state with CLKSEL = 1, CLK_EN = 0 ---
    two(mk("R10k", "R312", B, "GPIO1 unused -> 10 k -> DGND"), n.ECG_GPIO1, gnd)
    two(mk("R10k", "R313", B, "GPIO2 unused -> 10 k -> DGND"), n.ECG_GPIO2, gnd)
    two(mk("R10k", "R314", B, "CLK unused (internal osc) -> 10 k -> DGND"), n.ECG_CLK, gnd)
    # --- PWDN/RESET and START defaults (review power #6: IIN up to +-10 uA, VIL 0.2 V at DVDD 1.8 V, SBAS502C p.9) ---
    two(mk("R10k", "R311", B, "PWDN/RESET pull-down 10 k: AFE held in power-down while the MCU is in reset (10 uA x 10 k = 0.1 V < VIL)"), n.ECG_PWDN, gnd)
    two(mk("R100k", "R316", B, "START pull-down 100 k: START permanently low, conversions by the START opcode (ADS1291 p.44, p.48) [V3F: P0.04 is the motor PWM]"), n.ECG_START, gnd)
    two(mk("R100k", "R315", B, "CS_ECG pull-up 100 k (deselected while the MCU is in reset)"), n.CS_ECG, n.VDD_1V8)
