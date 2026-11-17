"""HMI block of SolarBand V3-F (BASELINE.md 1, 4, 5.1, 6, 14; CALC_V3F.md sections 4-8): display interface, front-light driver, ERM motor
driver and the sealed side button.
Display (Sharp LS011B7DH03, spec LD-29Y03): every input needs a push-pull 3 V level with <= 50 ns edges (p.22) and DISP must be low >= 30 us
before VDD goes off (p.21) -> five translated signals: TXU0104 (SCLK, SI, SCS, EXTCOMIN) + TXU0101 (DISP). [V3F] DISP moves to its own GPIO
(P0.18, the former debug UART_TX): the RC from the rail of the display lane would violate the edge time, the power-off order and the input
limit VHI <= VDD (p.17). U16 TPS7A0230 3.0 V from VSTOR_SW, EN = DISP_EN (P0.19), which is also VCCA and OE of both translators.
Front light: VSTOR_SW -> R160 100 Ohm -> film LED (tail J16) -> Q11 (FL_EN P0.10, PWM). SB_FL=dnp: Q11, R160, R161 not fitted. SB_FL=none: no driver, no J16.
ERM: [V3F supply choice, CALC_V3F 5] VBAT_IC (cell side of the BQ25570 PFET, C106 22 uF reservoir; INA_BAT still measures the motor current)
-> motor (J17) -> Q12 + Q19 low side in series, same gate (MOTOR_PWM P0.04 through R162; S1 D-12), flyback D17 (both halves of a BAT54CM in parallel) back to VBAT_IC. On VSTOR
(BASELINE 4) the start current would also cross the PFET (0.95-1.50 Ohm) and pull VSTOR 0.07-0.10 V further toward VBAT_OK falling.
Hook for the rule of BASELINE 14 item 6 (VBAT >= 3.60 V): INA_BAT (U5, R112, bus = BATT_P) reads VBAT and the battery current during the
30 ms soft start; the firmware limits the ramp to <= 40 mA battery current until the rotor runs (CALC_V3F 5)
Button: SW1 C&K PTS840 (side actuated, C&K catalogue B-40/B-41) between BTN_SUP (VBAT_IC through R165) and BTN: BTN -> D12 half B (ship-mode
wake, charger.py) and BTN -> Q13 gate: BTN_N (P0.26, pull-up R164 to VDD_1V8) goes low on a press. No pin of the MCU sees the VBAT level and
nothing back-feeds VDD_1V8 in ship mode (the pull-up rail is off then).
"""
from common import mk, two, wire, NC, FL_DNP, FL_NONE, MOTOR_NONE, MOTOR

def build(n):
    B = "hmi"; gnd = n.GND
    # ---------------- display supply and translators ----------------
    u16 = mk("TPS7A0230_DQN", "U16", B, "VDD_DISP 3.0 V LDO for the panel (25 nA IQ, 3 nA off, output discharge 60 Ohm) EN = DISP_EN")
    wire(u16, {"IN": n.VSTOR_SW, "GND": gnd, "EN": n.DISP_EN, "OUT": n.VDD_DISP, "PAD": gnd})
    two(mk("C1u", "C1501", B, "U16 IN 1 uF (SBVS277C p.5: >= 1 uF)"), n.VSTOR_SW, gnd)
    two(mk("C1u", "C1502", B, "U16 OUT 1 uF (>= 0.5 uF effective for stability, p.5); panel VDD >= 1 uF"), n.VDD_DISP, gnd)
    u17 = mk("TXU0104", "U17", B, "A->B translator 1.86 -> 3.0 V: SCLK, SI, SCS, EXTCOMIN; VCCA = OE = DISP_EN (both sides unpowered while the display is off)")
    wire(u17, {"VCCA": n.DISP_EN, "A1": n.SPI_SCK, "A2": n.SPI_MOSI, "A3": n.DISP_SCS, "A4": n.EXTCOMIN, "GND": gnd,
               "B4Y": n.D_EXTCOMIN, "B3Y": n.D_SCS, "B2Y": n.D_SI, "B1Y": n.D_SCLK, "VCCB": n.VDD_DISP, "OE": n.DISP_EN})
    u21 = mk("TXU0101", "U21", B, "A->B translator for DISP (P0.18 DISP_CTRL): edge <= 50 ns, DISP low before VDD off (LD-29Y03 p.21-22) [V3F]")
    wire(u21, {"VCCA": n.DISP_EN, "GND": gnd, "A": n.DISP_CTRL, "BY": n.D_DISP, "OE": n.DISP_EN, "VCCB": n.VDD_DISP})
    two(mk("C100n_0201", "C1601", B, "U17 / U21 VCCA 100 nF (SCES937B 8.4)"), n.DISP_EN, gnd)
    two(mk("C100n_0201", "C1602", B, "U17 VCCB 100 nF"), n.VDD_DISP, gnd)
    two(mk("C100n_0201", "C1603", B, "U21 VCCB 100 nF"), n.VDD_DISP, gnd)
    two(mk("C100n_0201", "C1503", B, "panel VDD / VDDA 100 nF at the FPC land (LD-29Y03 p.24: capacitor for VDD and VDDA)"), n.VDD_DISP, gnd)
    # [G1 L0] J13 is the land of the display BRIDGE FLEX (our own 10-trace flex between the panel FPC terminals and the board): the CAD lane found
    # (LD-29Y03 p.42) that after the only legal fold the FPC terminals face the panel, so the panel FPC itself cannot be soldered to a board land.
    # 10 pads 0.30 x 1.20 mm at 0.5 mm; no key pad (the FPC tail is 5.5 mm wide: the stage-1 key pad lay outside it); keyed by the flex outline.
    # [S2a 2026-11-15, lead decision c] J13 is now a TOP-contact ZIF from Sharp's Table 8-1 (LD-29Y03 p.36): Hirose FH34SRJ-10S-0.5SH(50), C324723, 1.0 mm high,
    # JLC-placed. The panel FPC (folded 180 deg toward its rear, terminals up) plugs in directly; no bridge flex, no solder on the panel FPC.
    # Pin order (v3/stage2a/STAGE2A.md section 2): Sharp's rear view (LD-29Y03 Fig. 8-1) puts terminal 1 at pod +Y; the fold about a Y-parallel line keeps Y;
    # Hirose p.6 / p.8: seen from above with the FPC entering toward the lead row, contact 1 is on the right = pod +Y when the entry faces +X. So contact n = terminal n.
    j13 = mk("ZIF_FH34_10", "J13", B, "display ZIF, top contact (Hirose FH34SRJ-10S-0.5SH, C324723): contact n = LS011B7DH03 terminal n (1 SCLK ... 10 VSSA); "
             "FPC entry toward the fold (+X), contact 1 at +Y; FPC inserted terminals UP [S2a; LD-29Y03 p.14, p.35; FH34 p.6, p.8]")
    wire(j13, {1: n.D_SCLK, 2: n.D_SI, 3: n.D_SCS, 4: n.D_EXTCOMIN, 5: n.D_DISP, 6: n.VDD_DISP,
               7: n.VDD_DISP, 8: n.VDD_DISP, 9: gnd, 10: gnd, 11: gnd, 12: gnd})
    # ---------------- front light (SB_FL=none, G1 level 4: driver and tail land removed; P0.10 is left unconnected in mcu_rf.py) ----------------
    if not FL_NONE: front_light(n, B, gnd)
    if not MOTOR_NONE: motor(n, B, gnd)
    button(n, B, gnd)

def front_light(n, B, gnd):
    two(mk("R100R_0201", "R160", B, "front-light LED resistor 100 Ohm from VSTOR_SW: 4.1-16.8 mA peak over VSTOR_SW 3.31-4.28 V and VF 2.6-2.9 V (E); PWM sets the 1.5 / 3-5 mA average [CALC_V3F 6]",
           dnp=FL_DNP), n.VSTOR_SW, n.FL_A)
    wire(mk("TAIL_FL", "J16", B, "front-light film tail: 2 keyed asymmetric pads (hand-soldered at final assembly): + = LED anode, - = cathode"), {"+": n.FL_A, "-": n.FL_K})
    q11 = mk("PMZ290UNE2", "Q11", B, "front-light low-side switch, FL_EN (P0.10) PWM: 1.5 mA night, 3-5 mA dim room", dnp=FL_DNP)
    wire(q11, {"G": n.FL_EN, "S": gnd, "D": n.FL_K})
    two(mk("R1M_0201", "R161", B, "FL_EN gate pull-down 1 M (light off while the MCU is in reset)", dnp=FL_DNP), n.FL_EN, gnd)

def motor(n, B, gnd):
    # ---------------- ERM motor (SB_MOTOR=none, G1 level 4: block removed; erm7 / erm6: same driver, smaller motor and cut-out) ----------------
    wire(mk("PADS_ERM", "J17", B, f"ERM wire pads ({MOTOR['part']}, dia {MOTOR['dia_mm']:g} x {MOTOR['thick_mm']:g} mm, <= {MOTOR['i_max_mA']} mA, hand-fitted in the {MOTOR['cutout_mm']:g} mm cut-out): + = VBAT_IC, - = MOTOR_N; polarity only sets the spin"),
         {"+": n.VBAT_IC, "-": n.MOTOR_N})
    q12 = mk("PMZ290UNE2", "Q12", B, "ERM low-side switch, upper of two in series: MOTOR_PWM (P0.04) 20-40 kHz PWM to about 3.0 V average, 30 ms soft start [BASELINE 14 item 6]")
    wire(q12, {"G": n.MOTOR_G, "S": n.MOTOR_S, "D": n.MOTOR_N})
    q19 = mk("PMZ290UNE2", "Q19", B, "ERM low-side switch, lower of two in series, same gate: one shorted FET no longer runs the motor from the unswitched VBAT_IC "
             "(single fault, review D-12); EOL probes MOTOR_S (test via) with the gate low [S1 D-12]")
    wire(q19, {"G": n.MOTOR_G, "S": gnd, "D": n.MOTOR_S})
    two(mk("R1k_0201", "R162", B, "Q12 gate series 1 k: GPIO peak current <= 1.9 mA into QG; gate edge about 0.2 us (CALC_V3F 5)"), n.MOTOR_PWM, n.MOTOR_G)
    two(mk("R1M_0201", "R163", B, "Q12 gate pull-down 1 M: motor off while the MCU is in reset"), n.MOTOR_G, gnd)
    d17 = mk("BAT54CM", "D17", B, "ERM flyback: both Schottky halves in parallel from MOTOR_N to VBAT_IC (200 mA each, 30 V)")
    wire(d17, {"A1": n.MOTOR_N, "A2": n.MOTOR_N, "CC": n.VBAT_IC})

def button(n, B, gnd):
    # ---------------- sealed side button ----------------
    sw1 = mk("PTS840", "SW1", B, "side-actuated tact switch C&K PTS840 GK (2.2 N, 0.2 mm travel) at the hand-end board edge behind a moulded membrane; pins 1-2 and 3-4 joined inside")
    wire(sw1, {1: n.BTN_SUP, 2: n.BTN_SUP, 3: n.BTN, 4: n.BTN})   # [S1 D-9] EasyEDA pad 5 (ESD-pin land) deleted in the reviewed land: GK has no pin 5
    two(mk("R100k_0201", "R165", B, "button supply 100 k from VBAT_IC: BTN = 0.91 x VBAT while pressed, <= 3.8 uA; charges C121 through D12B in about 0.3 s"), n.VBAT_IC, n.BTN_SUP)
    two(mk("R1M_0201", "R167", B, "BTN pull-down 1 M (also the Q13 gate pull-down)"), n.BTN, gnd)
    q13 = mk("PMZ290UNE2", "Q13", B, "button level shifter: BTN (VBAT level) -> BTN_N (1.8 V level, active low) on P0.26 SENSE [V3F: replaces the planned series R164]")
    wire(q13, {"G": n.BTN_G, "S": gnd, "D": n.BTN_N})
    two(mk("R10k_0201", "R511", B, "Q13 gate series 10 k: limits the ESD current into the gate behind D18 [S2b E-6]"), n.BTN, n.BTN_G)
    d18 = mk("TPD1E10B06", "D18", B, "ESD clamp on BTN at SW1 (bidirectional, IEC 61000-4-2): a discharge through the button membrane [S2b E-6, ECG.md 5d]")
    wire(d18, {1: n.BTN, 2: gnd})
    two(mk("R1M_0201", "R164", B, "BTN_N pull-up 1 M to VDD_1V8 (1.9 uA while pressed; no current in ship mode: VDD_1V8 off)"), n.BTN_N, n.VDD_1V8)
