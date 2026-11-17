"""IO block of SolarBand V3-F (BASELINE.md 1, 5.1, 9, 13.1, 16): pads, contacts, test points. Copper only (not JLC-placed, not in the BOM/CPL)
except the spring finger of E3 and the 0 Ohm strap links, which JLC places.
Skin face (B.Cu): plate-dot pads E11/E12, E21/E22, the 2 x 5 pogo array J8 for the G10 test before the floor is bonded, fiducials FID3/FID4.
Sky side (F.Cu): E3 spring finger J11, lid flex-tail land J6 (PV+, PV-, backsheet ground), SWD/reset group J12, EOL-1 test pads TP1-TP5,
fiducials FID1/FID2.
[V3F] the cell-tab pads J3/J4 and the NTC pads J5/J10 of V2-B become the strap entry lands (one pad per conductor, 1.5 x 4.0 mm = 6 mm2):
  root A (elbow end, X 4.5-10.5 mm): J3 BATT_P | J4 GND | J5 NTC | J10 GND  (protected pack: cell + PCM + F1 + NTC, welded by the pack maker)
  root B: J7 PV_W+ | J9 GND  (c-Si wing, joins PV+)
  each strap conductor, GND included, through its own 0402 link FB1-FB6 (0 Ohm by default; ferrite bead / CM choke if SIM-10/11 asks, BASELINE 13.1)
Assembly: pack leads colour-coded on asymmetric pads, polarity measured before soldering (BASELINE 16 'Pack leads'). The XB5358D0 first-connection step
of V2-B (bridge CELL_N to GND) moves to the pack maker.
"""
from common import mk, wire, two

def build(n):
    B = "io"; gnd = n.GND
    for ref, net, f in (("E11", n.E1_PAD, "E1 plate (IN+), silver-epoxy dot A"), ("E12", n.E1_LINK, "E1 plate, dot B (through R318)"),
                        ("E21", n.E2_PAD, "E2 plate (RLD), silver-epoxy dot A"), ("E22", n.E2_LINK, "E2 plate, dot B (through R319)")):
        wire(mk("PAD_DOT", ref, B, f + "; split ENIG pad on the skin face, opening in the carrier film", side="B"), {1: net})
    wire(mk("SPRING", "J11", B, "E3 top-rim strip contact (IN-, finger): SMT spring finger BW0036BG under the strip's tab, working height 1.00 mm (0.70-1.30); mating tab >= 3.4 x 2.2 mm centred on the pad centre (rotation-neutral) [FIX R-04]"), {1: n.E3_PAD})
    wire(mk("SPRING", "J19", B, "window-frame GND contact: BW0036BG spring finger under the stainless window frame at the E3 end (frame -> board GND) "
            "[S2b E-1, ECG.md 1b/1c/5f; position: v3/stage2b/frame_gnd.json]"), {1: gnd})
    # ---------------- strap root A (protected pack) and root B (wing) entry lands + one link per conductor ----------------
    for ref, net, f in (("J3", n.BATT_P_A, "root A: BATT_P (pack +)"), ("J4", n.GND_A1, "root A: GND (pack -), guard between BATT_P and NTC"),
                        ("J5", n.NTC_A, "root A: NTC (10 k B 3950 K on the cell, to pack -)"), ("J10", n.GND_A2, "root A: GND (guard)"),
                        ("J7", n.PV_W, "root B: PV_W+ (c-Si wing, 4 sub-cells in series)"), ("J9", n.GND_B, "root B: GND (wing -)")):
        wire(mk("PAD_ROOT_T", ref, B, f + "; 1-layer strap flex soldered to the entry land 1.0 x 2.5 mm [BASELINE 5.1, 9; G1 L0: was 1.0 x 4.0]"), {1: net})
    for ref, a, b, f in (("FB1", n.BATT_P, n.BATT_P_A, "BATT_P"), ("FB2", gnd, n.GND_A1, "GND (root A, 1)"), ("FB3", n.NTC, n.NTC_A, "NTC"),
                         ("FB4", gnd, n.GND_A2, "GND (root A, 2)"), ("FB5", n.PV_NODE, n.PV_W, "PV_W+ (joins PV+)"), ("FB6", gnd, n.GND_B, "GND (root B)")):
        two(mk("R0_0201", ref, B, f"strap-line link {f}: 0 Ohm 0201 by default (rated 0.5 A); 0201 ferrite bead if SIM-10/11 asks (strap tails are quarter-wave monopoles) [BASELINE 13.1; G1 L0: was 0402]"), a, b)
    wire(mk("PAD_LIDTAIL_T", "J6", B, "lid flex-tail land 3 x 1.0 x 2.0 mm at 1.5 mm: PV+, PV-, backsheet ground (copper under the finger rest tied to PV-) [G1 L0: was 3 x 1.2 x 3.0 at 2.0]"),
         {"PV+": n.PV_NODE, "PV-": gnd, "BS_GND": gnd})
    t = mk("TEST_ARRAY", "J8", B, "skin-face pogo array 2 x 5 for the G10 jig (before the floor is bonded); pad 6 is DISP_CTRL now (was UART_TX)", side="B")
    wire(t, {"VDD": n.VDD_1V8, "GND": gnd, "SWDIO": n.SWDIO, "SWDCLK": n.SWDCLK, "nRESET": n.NRESET,
             "DISP_CTRL": n.DISP_CTRL, "VSTOR": n.VSTOR, "VIN_DC": n.VIN_DC, "VLED": n.VLED, "AVDD_ECG": n.AVDD_ECG})
    s = mk("SWD_GROUP", "J12", B, "sky-side SWD / reset group 2 x 3 (reachable on screwed-lid units, S-10); pad 6 DISP_CTRL (was UART_TX: logs over RTT)")
    wire(s, {"VDD": n.VDD_1V8, "GND": gnd, "SWDIO": n.SWDIO, "SWDCLK": n.SWDCLK, "nRESET": n.NRESET, "DISP_CTRL": n.DISP_CTRL})
    tps = [("TP1", n.E1_PAD, "E1 electrode net (dot A side)"), ("TP2", n.E1_LINK, "E1 dot B side: loop TP1-TP2"),
           ("TP3", n.E2_PAD, "E2 electrode net (dot A side)"), ("TP4", n.E2_LINK, "E2 dot B side: loop TP3-TP4"),
           ("TP5", n.E3_PAD, "E3 electrode net (spring contact check, leakage test)")]
    for ref, net, f in tps:
        wire(mk("TP_EOL", ref, B, "EOL-1 test pad: " + f), {1: net})
    mk("FIDUCIAL", "FID1", B, "local fiducial 1 (sky side)"); mk("FIDUCIAL", "FID2", B, "local fiducial 2 (sky side)")
    mk("FIDUCIAL", "FID3", B, "local fiducial 3 (skin face: two-sided assembly)", side="B")
    mk("FIDUCIAL", "FID4", B, "local fiducial 4 (skin face)", side="B")
