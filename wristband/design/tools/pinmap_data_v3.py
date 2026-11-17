"""Datasheet pin tables of the parts that are new in SolarBand V3-F (v3/decide/BASELINE.md 5.1 + this lane), added to the v2 tables of
pinmap_data_v2.py. Same conventions (name = datasheet pin name, ASCII-normalised; type = KiCad electrical type).
Datasheets were read on 2026-11-13 from the URL given (TI: ti.com/lit; others: the LCSC copy the JLC parts API links for the C-number).
The PDFs are NOT kept in the project (lane rule: downloads stay outside); `sha256` is the hash of the file that was read, `pages` are PDF pages.
KEY RULE (cplgate G3, research/cpl-placement-gate.md): the pin NUMBER is the pad number of the JLC/EasyEDA footprint of the C-number; where the
maker's numbering differs, the pin is mapped BY POSITION and both numbers are written in the function text (TLV7031 X2SON-5 below).
"""
from pinmap_data_v2 import PARTS as V2
SCR = "session scratchpad (not kept; see sha256)"

PARTS_V3 = {
"C5208201": dict(mpn="BQ25170DSGR", mfr="Texas Instruments", refs="U15", ds="bq25170", sha256="90ddfdb38e001e2b528a3b7605acad04ba7bfd36bc5594d27cff002076c7b545",
    url="https://www.ti.com/lit/ds/symlink/bq25170.pdf", doc="SLUSDJ8A (April 2020, revised April 2021)",
    pin_table="Figure 5-1 WSON-8 top view and Table 5-1 Pin Functions, p.3", package="WSON-8 (DSG0008A) 2.0 x 2.0 x 0.8 mm max, 0.5 mm pitch, exposed pad 0.9 x 1.6 mm",
    package_page=32, land_page=33,
    pin1="WSON-8: pins 1-4 down the left side (pin 1 at the pin-1 index corner), 5-8 up the right side, exposed pad 9 = GND; marking B170 (p.28); tape pin-1 quadrant Q2 (p.29)",
    polarity=None,
    pins={1: ("IN", "power_in", "Input power, >= 1 uF to GND close to the IC; 30 V abs. max, -0.3 V min (p.4); OVP 6.60-6.90 V"),
          2: ("ISET", "passive", "Fast-charge current: ICHG = KISET / RISET, KISET 270/300/330 A*Ohm (p.6); RC recommended below 50 mA (p.14)"),
          3: ("TS", "passive", "NTC from TS to GND; 38 uA bias duty-cycled 100 ms / 2 s; < VTS_ENZ 40-60 mV disables the charger (p.3, p.7-8)"),
          4: ("GND", "power_in", "Ground"),
          5: ("STAT", "open_collector", "Open-drain charge status (low = charging, blinks 1 Hz on a fault); not used here (no pull-up)"),
          6: ("/PG", "open_collector", "Open-drain power good: low when VIN_LOWV < VIN < VIN_OV and VIN > VOUT + VSLEEPZ (p.3, p.17)"),
          7: ("VSET", "passive", "Charge-voltage select by pull-down resistor: 36 k = 4.10 V (Table 7-1, p.14); 1 %, <= 200 ppm/C"),
          8: ("OUT", "power_out", "Battery / system connection, >= 1 uF to GND; IQ_OUT 0.35 typ / 0.6 max uA with IN floating (p.6)"),
          9: ("EP", "power_in", "Exposed thermal pad: solder to GND with vias (p.3)")},
    notes="KISET 270/300/330 A*Ohm; precharge 20 %, termination 10 %; IBAT_SHORT 12/16/20 mA below 2.1-2.3 V; VREG +-0.5 % at 25 C, +-0.8 % over temperature; "
          "TS: ITS_BIAS 36.5/38/39.5 uA, VCOLD 0.99/1.04/1.09 V, VHOT 176/188/200 mV, clamp 2.3-2.9 V (p.6-7). EasyEDA symbol of C5208201 has the same names and numbers.",
    human_review="WSON-8 + EP: the copper fits turned 180 deg (4 + 4 + EP): JLC preview of pin 1 before payment and G10 (e)"),
"C2867950": dict(mpn="TPS7A0230PDQNR", mfr="Texas Instruments", refs="U16", ds="tps7a02", sha256="ed213c153f1db84762558fcac2ff9752e322151a1d44672cf554988b860cebc8",
    url="https://www.ti.com/lit/ds/symlink/tps7a02.pdf", doc="SBVS277C (July 2019, revised September 2022)",
    pin_table="Figure 5-1 DQN 1 x 1 mm X2SON-4 top view and Table 5-1, p.3", package="X2SON-4 (DQN0004A) 1.0 x 1.0 x 0.4 mm max, thermal pad", package_page=39, land_page=40,
    pin1="X2SON-4: pin 1 OUT and pin 2 GND on one side, pin 3 EN and pin 4 IN on the other, thermal pad in the middle; pin-1 index on top",
    polarity=None,
    pins={1: ("OUT", "power_out", "Regulated output, >= 0.5 uF effective to GND (p.3, p.5)"), 2: ("GND", "power_in", "Ground"),
          3: ("EN", "input", "Enable, internal pull-down; VEN(HI) 1.1 V, VEN(LOW) 0.3 V (p.7)"), 4: ("IN", "power_in", "Input 1.5-6.0 V, >= 1 uF (p.5)"),
          5: ("PAD", "power_in", "Thermal pad (internally GND), to the ground plane")},
    notes="IGND 25 typ / 46 nA max (25 C), ISHDN 3 / 10 nA, accuracy +-1.5 % over temperature, dropout <= 310 mV at 200 mA (2.5-3.3 V outputs), start-up 750-1200 us, "
          "output pull-down 60 Ohm when disabled (p.6-7). Same package and pin-out class as U3 (TPS7A2030PDQNR, v2).",
    human_review="X2SON-4 + pad fits turned 180 deg (as U3): JLC preview of the pin-1 index and G10 (g)"),
"C5187176": dict(mpn="TXU0104RUTR", mfr="Texas Instruments", refs="U17", ds="txu0104", sha256="f331ba62c302c5921ffdc98082083438ef1c9b6821fdedb5f9be41f23af81545",
    url="https://www.ti.com/lit/ds/symlink/txu0104.pdf", doc="SCES937B (May 2021, revised February 2025)",
    pin_table="Figure 4-3 RUT 12-pin UQFN transparent top view and Table 4-1, p.4", package="UQFN-12 (RUT0012A) 2.0 x 1.7 x 0.55 mm max, 0.4 mm pitch",
    package_page=36, land_page=37,
    pin1="UQFN-12: optional pin-1 ID (p.36); land symmetric on both axes (V3_ARCH 10, SCES937B p.37): a 180 deg turn fits the copper",
    polarity=None,
    pins={1: ("VCCA", "power_in", "A-port supply 1.1-5.5 V"), 2: ("A1", "input", "Input A1 (VCCA level), 5 M pull-down"), 3: ("A2", "input", "Input A2"),
          4: ("A3", "input", "Input A3"), 5: ("A4", "input", "Input A4"), 6: ("GND", "power_in", "Ground"),
          7: ("B4Y", "output", "Output B4 (VCCB level)"), 8: ("B3Y", "output", "Output B3"), 9: ("B2Y", "output", "Output B2"), 10: ("B1Y", "output", "Output B1"),
          11: ("VCCB", "power_in", "B-port supply 1.1-5.5 V"), 12: ("OE", "input", "Output enable, active high (VCC(MIN) logic: either supply)")},
    notes="VT+ 0.76-1.13 V at 1.65 V VCCA; VOH >= VCCO - 0.1 V at 0.1 mA; ICCA + ICCB 2.5 / 3 / 6 uA max (25 / 85 / 125 C); Ioff +-1.5 uA; outputs high-Z if "
          "either VCC < 100 mV (p.8-9, p.22). EasyEDA symbol of C5187176 has the same names and numbers.",
    human_review="UQFN-12 land fits turned 180 deg: JLC preview of pin 1 against our CPL rotation + G10 (g) test pattern at a 20 mA limit"),
"C5217869": dict(mpn="TXU0101DRYR", mfr="Texas Instruments", refs="U21", ds="txu0101", sha256="e8cbdac70666f37b26a7217f740cdd42c0d3163253df9cea4bdb7fcbd0f1c276",
    url="https://www.ti.com/lit/ds/symlink/txu0101.pdf", doc="SCES940A (February 2022, revised May 2024)",
    pin_table="Figure 4-4 DRY 6-pin SON transparent top view and Table 4-1, p.3", package="USON-6 (DRY0006A) 1.45 x 1.0 x 0.6 mm max, 0.5 mm pitch",
    package_page=35, land_page=36,
    pin1="USON-6: pins 1-3 on one side (1 at the pin-1 corner), 4-6 on the other; the land is symmetric except the slightly longer pin-1 pad of the EasyEDA footprint",
    polarity=None,
    pins={1: ("VCCA", "power_in", "A-port supply"), 2: ("GND", "power_in", "Ground"), 3: ("A", "input", "Input A (VCCA level)"),
          4: ("BY", "output", "Output B (VCCB level)"), 5: ("OE", "input", "Output enable, active high"), 6: ("VCCB", "power_in", "B-port supply")},
    notes="Same TXU family as U17 (Schmitt inputs, 5 M pull-downs, VCC isolation). Used for the panel's DISP input.",
    human_review="USON-6 fits turned 180 deg (VCCA <-> BY, GND <-> OE, A <-> VCCB): JLC preview of pin 1 + G10 (g) (blank screen if wrong)"),
"C549313": dict(mpn="BAV70M,315", mfr="Nexperia", refs="D12", ds="bav70m", sha256="489ea64bb38044e3fa62bff32c49ea138280583d49e9e19ff834ab5e9a000416",
    url="https://datasheet.lcsc.com/datasheet/pdf/57d454f2d24a7e90ce02c5218e178436.pdf?productCode=C549313", doc="BAV70M product data sheet (1 July 2022)",
    pin_table="Table 2 Pinning information, p.2", package="DFN1006-3 (SOT883) 1.0 x 0.6 x 0.48 mm", package_page=7, land_page=8,
    pin1="SOT883: pins 1 (A1) and 2 (A2) are the two small lands on one side, pin 3 (common cathode) the large land on the other (transparent top view, p.2)",
    polarity=dict(kind="diode-pair", note="common cathode on the large land: the land geometry proves the orientation (1F class, placement_proof)"),
    pins={1: ("A1", "passive", "Anode, diode 1"), 2: ("A2", "passive", "Anode, diode 2"), 3: ("CC", "passive", "Common cathode")},
    notes="VF <= 715 mV at 1 mA, <= 855 mV at 10 mA; IR <= 30 nA at 25 V, <= 0.5 uA at 80 V (25 C); VR 100 V; Ptot 250 mW (p.3-4). "
          "EasyEDA has NO footprint for C549313 (API 404 'Component not found', 2026-11-13 20:41 UTC): the board uses the SOT883 land of C549275 (BAT54CM, same Nexperia "
          "package and pin positions), compared with Nexperia's sot883_fr footprint (p.8) in footprint_audit.md.",
    human_review="JLC's 0 deg of C549313 cannot be read from EasyEDA: JLC preview of the cathode (large) land side before payment; G10 (f)"),
"C549275": dict(mpn="BAT54CM,315", mfr="Nexperia", refs="D17, D19", ds="bat54cm", sha256="ae312086c5836a5549da09396e5f030f6c23e19263cbaa34762d8220bd416fee",
    url="https://datasheet.lcsc.com/datasheet/pdf/857e6e97bc7a4b56c05ca8c91376cec5.pdf?productCode=C549275", doc="BAT54CM product data sheet (2003 Nov 11, NXP/Nexperia)",
    pin_table="Pinning table and Fig. 1, p.3 (document page 2)", package="SOT883 1.0 x 0.6 x 0.5 mm", package_page=6, land_page=None,
    pin1="SOT883: pins 1 (a1) and 2 (a2) on the small lands, pin 3 (common cathode) on the large land; cathode mark on top (Fig. 1)",
    polarity=dict(kind="diode-pair", note="common cathode on the large land: 1F by geometry"),
    pins={1: ("A1", "passive", "Anode a1"), 2: ("A2", "passive", "Anode a2"), 3: ("CC", "passive", "Common cathode")},
    notes="VF max 240 / 320 / 400 / 500 / 800 mV at 0.1 / 1 / 10 / 30 / 100 mA; VR 30 V; IF 200 mA; IFRM 300 mA (p.4). EasyEDA symbol: 1 A, 2 A, 3 K (consistent)."),
"C20345399": dict(mpn="ESD761DPYR", mfr="Texas Instruments", refs="D13, D15", ds="esd761", sha256="fe0372302560019f29e903350d465f948845fd6ee84b6b6109c5950f0f2d0b79",
    url="https://www.ti.com/lit/ds/symlink/esd761.pdf", doc="SLVSH10C (November 2022, revised December 2022)",
    pin_table="Figure 5-1 DPY X1SON-2 top view and Table 5-1, p.3", package="X1SON-2 (DPY0002A) 1.0 x 0.6 x 0.45 mm max", package_page=18, land_page=19,
    pin1="bidirectional: orientation irrelevant (class N)", polarity=None,
    pins={1: ("IO", "passive", "ESD-protected line"), 2: ("GND", "passive", "Ground")},
    notes="VRWM +-24 V, VBR 25.5-35.5 V, leakage <= 50 nA at +-24 V, clamp 36.3 V at 1.8 A 8/20 us, IEC 61000-4-2 +-15 kV, CL 1.1 / 1.8 pF (p.4-5)."),
"C896422": dict(mpn="NSR0240MX2T5G", mfr="onsemi", refs="D16", ds="nsr0240", sha256="053f0d99260675e0db4c662478cbd3198932be8c99df2829078bc653b7a3dd62",
    url="https://datasheet.lcsc.com/datasheet/pdf/4b95626787cd7ec325d86dd9eff135e9.pdf?productCode=C896422", doc="NSR0240MX2/D Rev. 3 (March 2022)",
    pin_table="Pin assignment p.1 (1 CATHODE, 2 ANODE) and case 714AB, p.4", package="X2DFN2 1.0 x 0.6 x 0.37 mm (case 714AB)", package_page=4, land_page=4,
    pin1="pin 1 = cathode at the pin-1 indicator (case 714AB, p.4)",
    polarity=dict(kind="diode", note="[S2b] D16 VBUS clamp: a reversed D16 conducts from VBUS to GND (no charge, head current limit; G10 (e) fails); 2-pad land fits at 180 deg"),
    pins={1: ("CATHODE", "passive", "Cathode (VBUS)"), 2: ("ANODE", "passive", "Anode (GND) [S2b; was D14 before stage 2b]")},
    notes="VR 40 V, IF 200 mA, VF typ/max 0.21/0.24 V at 0.1 mA, 0.27/0.30 V at 1 mA, 0.34/0.365 V at 10 mA, 0.46/0.50 V at 100 mA; IR 0.2/0.55 uA at 25 V (p.1-2)."),
"C221907": dict(mpn="PTS840GKSMTRLFS", mfr="C&K", refs="SW1", ds="pts840", sha256="fbe3ca6f1fd6bafc98f409060cd7495bb6e216da1d610df7d97b505c70ea9af4",
    url="https://datasheet.lcsc.com/datasheet/pdf/82b5c1248b369a64727907ed223b233b.pdf?productCode=C221907", doc="C&K catalogue pages B-40 to B-42 'PTS 840 Series Microminiature SMT Side Actuated'",
    pin_table="Schematic and recommended PCB layout, p.2 (B-41): pins 1-2 joined, 3-4 joined; pin 5 = ESD ground pin of the ESD versions only",
    package="body 3.5 x 2.9 x 1.35 mm, actuator 1.7 mm wide protruding 0.65 mm on one long side; 4 gull-wing leads (G); GK = 220 gf, no pegs, no ground pin (p.1)",
    package_page=2, land_page=2,
    pin1="mechanically polar: the actuator must face the wall; the 4-pad land fits turned 180 deg (pins 1-2 / 3-4 swap, electrically the same)",
    polarity=dict(kind="mechanical", note="class M: actuator side visible only in the JLC preview (EasyEDA 3D / silk), G10 (j) press test"),
    pins={1: ("1", "passive", "Contact A (joined to pin 2 inside)"), 2: ("2", "passive", "Contact A"), 3: ("3", "passive", "Contact B (joined to pin 4 inside)"),
          4: ("4", "passive", "Contact B")},   # [S1 D-9] pin / pad 5 (ESD ground pin of the ESD versions only) removed: GK has none, its land is deleted
    notes="SPST N.O., travel 0.2 +0.2/-0.1 mm, 100,000 cycles, 12 V DC / 50 mA max, contact <= 500 mOhm, bounce <= 10 ms, -40..85 C (p.1). Height 1.35 mm above the board (p.2 front view): above the 1.05 mm part budget of BASELINE 8.",
    human_review="actuator toward the hand-end wall in the JLC preview before payment; height 1.35 mm needs a local relief in the ring (V3-G9)"),
"C2876045": dict(mpn="TLV7031DPWR", mfr="Texas Instruments", refs="U19, U20", ds="tlv7031", sha256="6dc3780f7b59b4ba9e26c9f8f088e409ddef650e43cb07c5ed0c1dc4d8c95e60",
    url="https://www.ti.com/lit/ds/symlink/tlv7031.pdf", doc="SLVSE13J (September 2017, revised November 2024)",
    pin_table="Figure 4-4 TLV70x1 5-pin X2SON top view and Table 4-1, p.3: TI pin 1 OUT (corner), 2 VCC (corner), 3 VEE (CENTRE), 4 IN- (corner), 5 IN+ (corner)",
    package="X2SON-5 (DPW0005A) 0.8 x 0.8 x 0.4 mm max", package_page=53, land_page=54,
    pin1="TI numbering: 1 top-left (OUT), 2 bottom-left (VCC), 4 bottom-right (IN-), 5 top-right (IN+), 3 centre (VEE). The EasyEDA footprint of C2876045 numbers the "
         "same positions 1 top-left, 2 bottom-left, 3 bottom-right, 4 top-right, 5 centre, and its symbol names them OUT, VCC, IN-, IN+, VEE: same functions on the "
         "same pads, DIFFERENT NUMBERS. This pin map uses the footprint (pad) numbers, mapped by position.",
    polarity=None,
    pins={1: ("OUT", "passive", "Output, push-pull (TI pin 1, corner); POR holds it low below the minimum supply (p.17). Typed passive for the ERC: "
                       "U19's output is the supply of U20 (chained AND, PWR_FLAG on O2_NC)"),
          2: ("VCC", "power_in", "Positive supply 1.6-6.5 V (TI pin 2, corner)"),
          3: ("IN-", "input", "Inverting input (TI pin 4, corner opposite OUT's side) - footprint pad 3"),
          4: ("IN+", "input", "Non-inverting input (TI pin 5, corner) - footprint pad 4"),
          5: ("VEE", "power_in", "Negative supply / ground (TI pin 3, CENTRE pad) - footprint pad 5")},
    notes="VIO +-0.1 typ / +-8 mV max, VHYS 2/7/17 mV, ICC 335/900 nA, tON 200 us, inputs VEE-0.3..7 V independent of VCC (p.6, p.8).",
    human_review="pad numbering differs from TI's pin numbering (mapped by position, see pin1); X2SON-5 with a centre pad: check the JLC preview of the pin-1 corner"),
"C2863637": dict(mpn="TLV7031DCKR", mfr="Texas Instruments", refs="U19, U20", ds="tlv7031", sha256="6dc3780f7b59b4ba9e26c9f8f088e409ddef650e43cb07c5ed0c1dc4d8c95e60",
    url="https://www.ti.com/lit/ds/symlink/tlv7031.pdf", doc="SLVSE13J (September 2017, revised November 2024)",
    pin_table="Figure 4-1 TLV70x1 'North West' pinout DBV/DCK top view and Table 4-1, p.3: 1 OUT, 2 V-, 3 IN+, 4 IN-, 5 V+",
    package="SC70-5 (DCK0005A) 2.0 x 1.25 body, 1.1 mm max height", package_page=59, land_page=60,
    pin1="SC70-5: pins 1-3 on one side (pin 1 at the pin-1 index end), 4-5 on the other (4 opposite 3, 5 opposite 1). EasyEDA C2863637 uses TI's numbers "
         "(pads 1-3 at x +1.10, 4-5 at x -1.10). [ECO3 2026-11-16] replaces the X2SON C2876045.",
    polarity=None,
    pins={1: ("OUT", "passive", "Output, push-pull; POR holds it low below the minimum supply (p.17). Typed passive for the ERC: U19's output is the supply of U20 (chained AND, PWR_FLAG on O2_NC)"),
          2: ("VEE", "power_in", "Negative supply / ground (TI name V-, pin 2)"),
          3: ("IN+", "input", "Non-inverting input"),
          4: ("IN-", "input", "Inverting input"),
          5: ("VCC", "power_in", "Positive supply 1.6-6.5 V (TI name V+, pin 5)")},
    notes="Same die and the same single-channel tables as the X2SON part: VIO +-0.1 typ / +-8 mV max, VHYS 2/7/17 mV, ICC 335/900 nA, tON 200 us (p.8; one table for DPW/DBV/DCK). RthJA 278.8 C/W (p.6).",
    human_review="5 leads 3 + 2: the copper does not fit turned 180 deg onto the same nets (3-lead side vs 2-lead side); a mirrored placement swaps OUT/IN+ with V+/IN-: JLC preview of the pin-1 mark"),
"C478207": dict(mpn="PMZ350UPEYL", mfr="Nexperia", refs="Q14, Q18", ds="pmz350", sha256="9f5edb6565c9a9ac9333b1ee193f480f024fbdee4eaa12844e6d22a13b07a79e",
    url="https://datasheet.lcsc.com/datasheet/pdf/61ec9f5ef7c9e0bb0863e45d64cfc884.pdf?productCode=C478207", doc="PMZ350UPE product data sheet (14 May 2014)",
    pin_table="Table 2 Pinning information, p.2", package="DFN1006-3 (SOT883) 1.0 x 0.6 x 0.48 mm", package_page=10, land_page=11,
    pin1="Pins 1 (G) and 2 (S) are the two small lands on one side, pin 3 (D) the large land on the other (as PMZ290UNE2)",
    polarity=None,
    pins={1: ("G", "input", "Gate (ESD-protected > 1.8 kV HBM)"), 2: ("S", "passive", "Source"), 3: ("D", "passive", "Drain")},
    notes="VDS -20 V, VGS +-8 V, VGSth -0.45/-0.7/-0.95 V at 250 uA; RDSon 330/450 mOhm at -4.5 V, 420/645 at -2.5 V, 520/940 at -1.8 V; IDSS <= 1 uA at -20 V; "
          "IGSS <= 10 uA at +-8 V; Ciss 127 pF (p.6)."),
# [S2c F-8, 2026-11-15] Q20 60 V N-FET. JSCJ CJBA7002K datasheet Rev 1.0 (LCSC copy of C504101, read today, not kept). Pin numbers = EasyEDA footprint of C504101
# (pad 1 S and pad 3 G = small lands at -x, pad 2 D = large land at +x); datasheet top view p.1: D large, S and G small. The copper is the C478155 SOT883 land turned 180 deg.
"C504101": dict(mpn="CJBA7002K", mfr="Jiangsu Changjing Electronics (JSCJ)", refs="Q20", ds="cjba7002k", sha256="ecba20a77f027ec81c98ab5923c72c95abca67459d20e4d9b8545db01712df7b",
    url="https://www.lcsc.com/datasheet/lcsc_datasheet_2004231932_Jiangsu-Changjing-Electronics-Technology-Co---Ltd--CJBA7002K_C504101.pdf",
    doc="CJBA7002K DFN1006-3L Plastic-Encapsulate MOSFETs, Rev. 1.0", pin_table="p.1 top view internal schematic (D large land; S, G small lands)",
    package="DFN1006-3L (X1-DFN1006-3) 1.0 x 0.6 x 0.53 mm max", package_page=4, land_page=4,
    pin1="EasyEDA C504101: pad 1 S (-0.35, +0.23), pad 3 G (-0.35, -0.23), pad 2 D (+0.35, 0); turned 180 deg this is the C478155 land with G and S on the same pads (G at +y)",
    polarity=None,
    pins={1: ("S", "passive", "Source"), 2: ("D", "passive", "Drain"), 3: ("G", "input", "Gate (ESD-protected)")},
    notes="VDS 60 V, VGS +-20 V; RDS(on) max 1.8 Ohm at VGS 4.5 V / ID 35 mA, 1.5 Ohm at 10 V / 40 mA (typ 1.3 / 1.2); VGS(th) 1.3-2.3 V; IDSS <= 100 nA at 60 V; "
          "IGSS <= 1 uA at +-5 V; Ciss 41 pF, Coss 3.6 pF; PD 0.1 W, RthJA 1250 K/W (p.1-2)."),
# [S2a 2026-11-15] J13 = top-contact ZIF (lead decision c). Hirose FH34 catalogue Oct. 2022 (Farnell copy https://www.farnell.com/datasheets/3932894.pdf, read today):
# p.6 dimensions (10 pos: A 7.0 +-0.15, B 4.5, C 5.53, D 6.38; depth 3.8, height 1.0), p.8-9 recommended PCB pattern (pads 0.3 x 0.8 at 0.5; retention-tab pads
# 0.4 x 0.8 between E 6.1 and F 6.9; 3.3 overall), p.8 FPC: contact No.1 (top contact) on the right with the lead row away from the viewer, FPC width G 5.5 +-0.05.
# Contact n mates panel terminal n (LS011B7DH03 Table 4-1 p.14; derivation v3/stage2a/STAGE2A.md section 2).
"C324723": dict(mpn="FH34SRJ-10S-0.5SH(50)", mfr="Hirose (HRS)", refs="J13", ds="fh34", sha256="b5666f9deffa708f32d4e1ec298c6f8b21bf5fa7729e38f35242aa89802cff65",
    url="https://www.farnell.com/datasheets/3932894.pdf", doc="Hirose FH34 Series catalogue, Oct. 2022 (0.5 mm pitch, 1.0 mm height, top and bottom contact, back flip)",
    pin_table="p.6 'Contact No.1' at the +x end of the lead row; p.8 recommended FPC: contact No.1 (top contact) on the right; panel terminals LS011B7DH03 p.14 Table 4-1",
    package="FH34SRJ-10S: body 7.0 +-0.15 x 3.8 x 1.0 mm (p.6, A / depth / height); 10 contacts at 0.5 mm in one row at the actuator side; 2 retention tabs at the FPC-entry corners",
    package_page=6, land_page=8,
    pin1="contact 1 at the +x end of the lead row (EasyEDA pad 1 at x +2.25, y -1.25); the land (10 pads in one row + 2 tab pads on the other side) cannot be placed turned 180 deg",
    polarity=dict(kind="mechanical", note="land shape decides (1F); the FPC entry must face the fold (+X); FPC inserted terminals UP (top contact); G10 (g)"),
    pins={1: ("C1_SCLK", "passive", "contact 1 -> panel terminal 1 SCLK"), 2: ("C2_SI", "passive", "contact 2 -> panel terminal 2 SI"),
          3: ("C3_SCS", "passive", "contact 3 -> panel terminal 3 SCS"), 4: ("C4_EXTCOMIN", "passive", "contact 4 -> panel terminal 4 EXTCOMIN"),
          5: ("C5_DISP", "passive", "contact 5 -> panel terminal 5 DISP"), 6: ("C6_VDDA", "passive", "contact 6 -> panel terminal 6 VDDA"),
          7: ("C7_VDD", "passive", "contact 7 -> panel terminal 7 VDD"), 8: ("C8_EXTMODE", "passive", "contact 8 -> panel terminal 8 EXTMODE"),
          9: ("C9_VSS", "passive", "contact 9 -> panel terminal 9 VSS"), 10: ("C10_VSSA", "passive", "contact 10 -> panel terminal 10 VSSA"),
          11: ("MP1", "passive", "retention tab (pure-tin plated copper alloy, p.5), soldered, tied to GND"), 12: ("MP2", "passive", "retention tab, tied to GND")},
    notes="0.5 A per contact, 50 V, -55..105 C, contact resistance <= 100 mOhm, 20 mating cycles; recommended FPC t 0.3 +-0.03 gold plated (p.4) = LS011B7DH03 stiffened end "
          "0.3 +-0.03 (LD-29Y03 p.42). FPC width G 5.5 +-0.05 (p.9) = LS011B7DH03 tail 5.5 +-0.05. Delivered with the actuator open (p.16). Sharp LD-29Y03 Table 8-1 lists it.",
    human_review="the FPC goes in terminals UP (top contact); a flipped FPC mates in reverse order (1<->10): assembly instruction + G10 (g) at a 20 mA limit"),
# [S2b E-4, 2026-11-15] D14 100 V Schottky. Datasheet read today from the LCSC copy of C552793 (same die, non-Q; the -Q page of C6736531 returned HTML).
"C6736531": dict(mpn="PMEG10020AELR-QX", mfr="Nexperia", refs="D14", ds="pmeg10020aelr", sha256="a9d827c3f1d22ddf57ddc8063f8ace11df48bae2041a38a664878c69809e103e",
    url="https://datasheet.lcsc.com/datasheet/pdf/d8079dbb0971066558fedc170d99edb4.pdf?productCode=C552793", doc="PMEG10020AELR product data sheet (1 January 2023)",
    pin_table="Table 2 pinning information, p.2 (1 K cathode, 2 A anode; the marking bar indicates the cathode)", package="CFP3 (SOD123W) 3.3-3.7 x 1.5-1.9 x 0.9-1.1 mm", package_page=9, land_page=10,
    pin1="pin 1 = cathode at the marking bar (Table 2, Fig. 16)",
    polarity=dict(kind="diode", note="2-pad land: a 180 deg turn fits; a reversed D14 blocks the head completely (G10 (e) fails: no /PG, no charge current)"),
    pins={1: ("K", "passive", "Cathode (to the BQ25170 IN, VBUS)"), 2: ("A", "passive", "Anode (contact side, VBUS_K)")},
    notes="VR 100 V; VF typ/max 470/520 mV at 0.1 A, 580/630 at 0.5 A (25 C, p.5); about 0.43 V typ at 33 mA from Fig. 4 (25 C); IR typ 10 / 25 / 70 nA at 10 / 60 / 100 V, "
          "max 300 nA at 100 V (25 C); Cd typ 135 / 80 / 50 pF at 1 / 4 / 10 V (p.5)."),

}

PARTS = dict(V2)
PARTS.update(PARTS_V3)
