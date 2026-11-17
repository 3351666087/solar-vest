"""Datasheet pin tables of the parts that are new in SolarBand V2-B (REDESIGN_V2 rev 1), added to the v1 tables of
pinmap_data.py. Same conventions (name = datasheet pin name, ASCII-normalised; type = KiCad electrical type).
Datasheets: cache/v2/ds/<ds>.pdf (downloaded 2026-11-12 from the LCSC link the JLC parts API returns for the C-number,
index in cache/v2/ds/index.json) unless `ds_dir` says otherwise. Page = PDF page (1-based).
"""
from pinmap_data import PARTS as V1
V2DS = "/path/to/SolarVest_work/wristband/cache/v2/ds"
V1DS = "/path/to/SolarVest_work/wristband/cache/datasheets"

# nRF52832-CIAA WLCSP ball table (PS v1.4 Table 4, p.15-17): ball -> name. Type and function are taken from the QFN-48
# entry with the same pin name (same silicon), so the two radio variants share one description per signal.
_BALLS = """A1 XC2|A2 DEC2|A3 P0.28/AIN4|A4 P0.29/AIN5|A5 P0.30/AIN6|A6 DEC4|A7 VDD|B2 XC1|B3 P0.25|B4 P0.27|B5 P0.31/AIN7|B6 DCC|B7 DEC1|
C2 DEC3|C3 NC|C4 VSS|C5 VSS|C6 P0.02/AIN0|C7 P0.01/XL2|D1 ANT|D2 VSS_PA|D3 P0.26|D6 P0.03/AIN1|D7 P0.00/XL1|E1 P0.24|E2 P0.23|E3 VSS|
E6 P0.04/AIN2|E7 P0.05/AIN3|F1 SWDCLK|F2 P0.22|F3 P0.19|F4 P0.11|F5 VSS|F6 P0.07|F7 P0.06|G1 SWDIO|G2 P0.20/TRACECLK|G3 P0.17|G4 P0.13|
G5 NFC2/P0.10|G6 NFC1/P0.09|G7 P0.08|H1 P0.21/nRESET|H2 P0.18/TRACEDATA[0]|H3 P0.16/TRACEDATA[1]|H4 P0.15/TRACEDATA[2]|
H5 P0.14/TRACEDATA[3]|H6 P0.12|H7 VDD""".replace("\n", "").split("|")
_q = {name: (typ, fn) for name, typ, fn in V1["C77540"]["pins"].values()}
_q["P0.18/TRACEDATA[0]"] = _q["P0.18/TRACEDATA[0]/SWO"]; _q["VSS_PA"] = ("power_in", "Ground (radio supply), ball D2 next to ANT")
_wl = {}
for b in _BALLS:
    ball, name = b.split(" ")
    _wl[ball] = (name,) + _q[name]
assert len(_wl) == 50

def _same(c, names):          # copy (type, function) by pin name from a v1 part of the same die
    d = {name: (typ, fn) for name, typ, fn in V1[c]["pins"].values()}
    return {num: (name,) + d[name] for num, name in names.items()}

PARTS_V2 = {
"C509405": dict(mpn="nRF52832-CIAA-R", mfr="Nordic Semiconductor", refs="U6 (RADIO=wlcsp)", ds="nrf52832_lcsc", ds_dir=V1DS,
    url="https://www.lcsc.com/datasheet/lcsc_datasheet_1810010217_Nordic-Semicon-NRF52832-QFAA-R_C77540.pdf",
    doc="nRF52832 Product Specification v1.4 (2017-10-10)",
    pin_table="Section 4.2 WLCSP ball assignments, Figure 3 (top view) and Table 4, p.15-17; Table 6 GPIO near the radio, p.17",
    package="WLCSP-50, 3.0 x 3.2 mm (D 2.956, E 3.226 nom.), 0.4 mm pitch, 8 rows A-H x 7 columns, 6 positions unpopulated "
            "(B1, C1, D4, D5, E4, E5), ball 0.20 mm (Table 132, Figure 164, p.541)",
    package_page=541, land_page=None,
    pin1="Ball A1 at the top-left corner of the top view, marked by the top-side dot; columns 1-7 left to right, rows A-H downward "
         "(Figure 3, rendered in cache/v2/ds/png/nrf52832_ps_fig3_wlcsp_balls.png)",
    polarity=None, pins=_wl,
    ids="FICR INFO.PART 0x52832, INFO.VARIANT 'AAxx', INFO.PACKAGE 0x2002 (CIxx, WLCSP) (PS p.2739-2741 of the text = section 14)",
    notes="Same silicon as the QFAA (C77540): same GPIO numbers, same firmware. WLCSP is light-sensitive (PS section 6.1, p.20): "
          "it must sit under the opaque lid backsheet (REDESIGN S-9). Reference circuit: Figure 173 / Table 149, p.549.",
    human_review="WLCSP A1 corner in the JLC preview (ball pattern is not 180-degree symmetric: positions B1/C1 and D4/D5/E4/E5 are empty)"),
"C4371025": dict(mpn="INA236AIYBJR", mfr="Texas Instruments", refs="U4, U5", ds="ina236", ds_dir=V1DS,
    url="https://www.ti.com/lit/ds/symlink/ina236.pdf", doc="SBOSA81D (Aug 2023)",
    pin_table="Figure 5-1 (YBJ top view) and Table 5-1 Pin Functions, p.3",
    package="DSBGA-8 (YBJ0008), 0.745 x 1.508 mm, 2 x 4 bumps, 0.4 mm pitch", package_page=41, land_page=42,
    pin1="Bump A1 (ALERT) at the marked corner; Figure 5-1 top view: column 1 = ALERT, A0, SDA, SCL (rows A-D), column 2 = IN+, IN-, GND, VS",
    polarity=None,
    pins=_same("C5443912", {"A1": "ALERT", "A2": "IN+", "B1": "A0", "B2": "IN-", "C1": "SDA", "C2": "GND", "D1": "SCL", "D2": "VS"}),
    ids="Manufacturer ID register 0x3E = 0x5449 ('TI'), device ID register 0x3F = 0xA080 (SBOSA81D register map)",
    notes="Same die and registers as the INA236AIDDFR of v1. SDA/SCL/A0/ALERT abs. max GND-0.3..6 V independent of VS (p.4), so "
          "the I2C bus may stay at 1.8 V while the gated VS rail is off. IQ 300 uA typ / 380 uA max (500 uA over temperature), "
          "shutdown 2.2 / 3 uA (p.6)."),
"C2760012": dict(mpn="XB5358D0", mfr="XySemi", refs="U14", ds="xb5358d0",
    url="https://www.lcsc.com/datasheet/lcsc_datasheet_2106062204_XySemi-XB5358D0_C2760012.pdf", doc="XB5358D0 REV0.4",
    pin_table="Figure 2 PIN Configuration and PIN DESCRIPTION, p.2", package="SOT23-5 (D 2.82-3.02, E 1.50-1.70, E1 2.65-2.95, e 0.95; p.11)",
    package_page=11, land_page=None,
    pin1="SOT23-5: pins 1-2-3 on one side (pin 1 = VT), 4-5 on the other; top mark '5358D' + date code",
    polarity=None,
    pins={1: ("VT", "passive", "Test pin, only for the vendor: not used by the application (left open)"),
          2: ("GND", "power_in", "Ground: negative terminal of the cell"),
          3: ("VDD", "power_in", "Power supply: positive terminal of the cell"),
          4: ("VM", "passive", "Negative terminal of the pack; the internal FET switch connects it to GND"),
          5: ("VM", "passive", "Negative terminal of the pack (second pin)")},
    notes="VCU 4.20/4.25/4.30 V, VCL 4.05/4.10/4.15 V, VDL 2.80/2.9/3.00 V, VDR 2.90/3.0/3.10 V, IOV1 2.5/3.3/4.1 A, operation "
          "2.8 uA typ / 6 uA max, power-down 1.5 / 3 uA, RSS(on) 40/45/54 mOhm (p.3); 0 V battery charging function (p.7)."),
"C727398": dict(mpn="SiP32431DNP3-T1GE4", mfr="Vishay Siliconix", refs="U12, U13", ds="sip32431", ds_dir=V1DS,
    url="https://www.vishay.com/docs/66597/sip32431.pdf", doc="Document 66597 Rev. G (06-Jul-2020)",
    pin_table="Fig. 3 TDFN4 1.2 mm x 1.6 mm package (bottom view) and Pin Description table, p.3",
    package="TDFN4 1.2 x 1.6 mm, 0.5 mm pitch, exposed pad", package_page=13, land_page=14,
    pin1="TDFN4 (Fig. 3 is a BOTTOM view, rendered in cache/v2/ds/png/sip32431_fig3_tdfn4.png): pin 1 = OUT at the dot corner, 2 = GND on the same side; 3 = IN opposite pin 2, 4 = ON/OFF opposite pin 1; centre pad GND",
    polarity=None,
    pins={1: ("OUT", "power_out", "P-channel MOSFET drain (switched output)"), 2: ("GND", "power_in", "Ground"),
          3: ("IN", "power_in", "P-channel MOSFET source; 1 uF to GND"), 4: ("ON/OFF", "input", "Enable, active high (SiP32431)"),
          5: ("GND", "power_in", "Exposed centre pad, ground")},
    notes="Same die as the SC-70 part of v1: IQ 0.01 nA typ / 100 nA max, IQ(off) 0.01/100 nA, ISD(off) 0.2/100 nA; RDS(on) TDFN4 "
          "135 mOhm typ at 3 V, 230 mOhm typ at 1.8 V; VIH 1.3 V (VIN 1.5-2.7 V), 1.5 V (2.7-4.2 V), 1.8 V (>= 4.2 V); VIL 0.3/0.4/0.6 V; "
          "ON/OFF leakage 0.014 nA typ, no internal pull-down; turn-on rise 140 us typ (p.3).",
    human_review="TDFN4 2 x 2 lands + centre pad: a 180-degree turn fits the copper (pin 1 OUT <-> pin 3 IN); identity by the pin map (EasyEDA symbol of C727398 agrees: 1 OUT, 2 GND, 3 IN, 4 ON/OFF, 5 GND) and by G10 (rail does not switch if turned)"),
"C478155": dict(mpn="PMZ290UNE2YL", mfr="Nexperia", refs="Q1, Q4, Q5, Q6", ds="pmz290une2",
    url="https://www.lcsc.com/datasheet/lcsc_datasheet_2001040909_Nexperia-PMZ290UNE2YL_C478155.pdf", doc="PMZ290UNE2 product data sheet (24 March 2015)",
    pin_table="Table 2 Pinning information, p.2", package="DFN1006-3 (SOT883), 1.0 x 0.6 x 0.48 mm", package_page=12, land_page=13,
    pin1="Pins 1 (G) and 2 (S) are the two small lands on one side, pin 3 (D) is the large land on the other (transparent top view, p.2)",
    polarity=None,
    pins={1: ("G", "input", "Gate (ESD-protected, 2 kV HBM)"), 2: ("S", "passive", "Source"), 3: ("D", "passive", "Drain")},
    notes="VGSth 0.45/0.7/0.95 V; RDSon 470 typ / 680 max mOhm at VGS 1.8 V, 600/1190 mOhm at 1.5 V; IDSS <= 1 uA at 20 V; "
          "IGSS <= 100 nA at +-2.5 V, <= 1 uA at +-4.5 V, <= 5 uA at +-8 V; VDS 20 V, VGS +-8 V (Tables 5 and 7, p.3 and p.6)."),
"C253326": dict(mpn="EMX1T2R", mfr="ROHM", refs="Q2 (CHARGE=contacts)", ds="rohm_emx1",
    url="https://www.lcsc.com/datasheet/lcsc_datasheet_1808280341_ROHM-Semicon-EMX1T2R_C253326.pdf", doc="EMX1 / UMX1N / IMX1 datasheet Rev.003 (2015-08-25)",
    pin_table="Inner circuit EMX1 / UMX1N, p.1", package="SOT-563 (EMT6), 1.6 x 1.6 mm, 0.5 mm pitch", package_page=8, land_page=8,
    pin1="(1) Tr1 emitter at the marked corner; pins 1-3 on one side, 4-6 on the other, counter-clockwise (p.1)",
    polarity=None,
    pins={1: ("E1", "passive", "Tr1 emitter"), 2: ("B1", "input", "Tr1 base"), 3: ("C2", "passive", "Tr2 collector"),
          4: ("E2", "passive", "Tr2 emitter"), 5: ("B2", "input", "Tr2 base"), 6: ("C1", "passive", "Tr1 collector")},
    notes="Two independent 2SC2412K NPN, VCEO 50 V, IC 150 mA, hFE 120-560 at 1 mA (p.1-2). The pin map is its own 180-degree "
          "image (1<->4, 2<->5, 3<->6) and both halves are wired symmetrically (base divider 1 k / 10 k, emitter to GND), so a "
          "180-degree turn only swaps two identical transistors: rotation-neutral (REDESIGN 4.8)."),
"C130414": dict(mpn="BAS521,115", mfr="Nexperia", refs="D9; D1 (CHARGE=contacts)", ds="bas521",
    url="https://www.lcsc.com/datasheet/lcsc_datasheet_2407241026_Nexperia-BAS521-115_C130414.pdf", doc="BAS521 product data sheet",
    pin_table="Table 2 Pinning information, p.1", package="SOD523 (SC-79), 1.2 x 0.8 x 0.6 mm", package_page=6, land_page=7,
    pin1="Pin 1 = cathode, marked by the cathode band", polarity=dict(kind="diode", reference="K", reference_pin="1", body_mark="cathode band at pin 1"),
    pins={1: ("K", "passive", "Cathode"), 2: ("A", "passive", "Anode")},
    notes="VR 300 V, IF 250 mA, IR 30 nA max at 250 V (JLC listing and datasheet table); used as the EN-hold diode D9 and, with "
          "contacts, as the cradle isolation diode D1 (SIM-08 result <= 83 V carries over: higher VRRM than BAS21)."),
"C5603826": dict(mpn="CT DBLP31.12", mfr="ams-OSRAM", refs="D3, D4", ds="osram_ct_dblp31_12",
    url="https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2404151600_OSRAM-Opto-Semicon-CT-DBLP31-12_C5603826.pdf", doc="CT DBLP31.12 datasheet Version 1.3 (2021-03-29)",
    pin_table="Dimensional drawing (anode / cathode leaders), p.11; electrical internal circuit and recommended solder pad, p.12",
    package="2.2 x 1.8 x 0.6 mm (+-0.1); lands: one 1.45 x 1.25 mm and two 0.55 x 0.35 mm, 0.34 mm apart, 0.25 mm from the large land (p.11, p.12)",
    package_page=11, land_page=12,
    pin1="Anode = one of the two small lands; cathode = the other small land and the large land (p.11 pad view). In the top "
         "view of the board the anode is the small land on the LEFT when the small lands are at the top",
    polarity=dict(kind="led", reference="A", reference_pin="1", body_mark="pad set is asymmetric: large cathode land opposite the two small lands"),
    pins={1: ("A", "passive", "Anode ('+', small land)"), 2: ("C", "passive", "Cathode ('-', small land)"),
          3: ("C", "passive", "Cathode (large land, heat path)")},
    notes="VF 2.00 / 2.30 / 2.80 V at 20 mA, 3150-5000 mcd, IF 2.5-140 mA (p.3-5); ESD protection device in parallel (p.12); not "
          "suitable for ultrasonic cleaning (p.12). The pad set is not its own 180-degree image, so a turned part cannot match "
          "(REDESIGN 5.8 item 3); which small land is the anode rests on the p.11 pad view and on the EasyEDA symbol of "
          "C5603826 (pin 1 '+', pin 2 '-'): two sources, human review + G10 LED/PD loop-back."),
"C125114": dict(mpn="LTST-S270KRKT", mfr="Lite-On", refs="D10", ds="liteon_ltst_s270krkt",
    url="https://www.lcsc.com/datasheet/lcsc_datasheet_1810231514_Lite-On-LTST-S270KRKT_C125114.pdf", doc="LTST-S270KRKT data sheet (BNS-OD-C131/A4)",
    pin_table="Package dimensions with cathode mark and polarity, p.2", package="Side-looking chip LED 1.65 x 1.15 x 0.60 mm (height 0.60)",
    package_page=2, land_page=8,
    pin1="Cathode mark on the mounting face at the cathode terminal (p.2)",
    polarity=dict(kind="led", reference="K", reference_pin="1", body_mark="cathode mark on the terminal face"),
    pins={1: ("K", "passive", "Cathode"), 2: ("A", "passive", "Anode")},
    notes="AlInGaP red 631 nm, VF 2.0 typ / 2.4 max V at 20 mA, IV 18 min / 54 typ mcd, 130 deg, IR 10 uA at 5 V (p.3-4)."),
"C598214": dict(mpn="KA-2810ASURSK", mfr="Kingbright", refs="D10", ds="C598214_kingbright_ka2810asursk", ds_dir="/path/to/SolarVest_work/wristband/cache/v2/ds_fix/C598214_kingbright_ka2810asursk",
    url="https://datasheet.lcsc.com/datasheet/pdf/67b1a40883785436a496c98954203521.pdf?productCode=C598214", doc="KA-2810ASURSK data sheet, Spec No DSAK2457, Rev V.7A (2019-05-07)",
    pin_table="Package dimensions with the polarity symbol (1 = cathode side of the diode symbol, 2 = anode), p.1", package="Right-angle chip LED 2.8 x 1.2 x 0.8 mm (thickness 0.8)",
    package_page=1, land_page=1,
    pin1="Terminal 1 = cathode: the diode symbol on p.1 has its bar at terminal 1; front view (looking into the lens) has terminal 1 on the left",
    polarity=dict(kind="led", reference="K", reference_pin="1", body_mark="terminals 1 / 2 as numbered in the front view of p.1"),
    pins={1: ("K", "passive", "Cathode"), 2: ("A", "passive", "Anode")},
    notes="AlGaInP hyper red 630 nm dominant, IV 150 min / 300 typ mcd at 20 mA (40 / 100 mcd on the CIE127-2007 scale), VF 1.95 typ / 2.5 max V at 20 mA, "
          "DC forward current 30 mA, peak 185 mA, 75 mW, 110 deg, MSL 3 (p.1-2). Two equal lands: a 180 deg turn fits the copper, swaps the polarity and turns the "
          "light away from the window -> identity by the G10 item 'ALERT_LED on: supply current rises by 6-26 mA and red light leaves the board edge' and by the JLC preview."),
"C398713": dict(mpn="SC-16S 32.768kHz 20ppm 12.5pF", mfr="Seiko Instruments", refs="X2", ds="seiko_sc16s",
    url="https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/1912111437_Seiko-SC-16S-32-768kHz-20PPM-12-5pF_C398713.pdf", doc="SC-16S data sheet (SII)",
    pin_table="Internal lead connections and dimensions, p.1", package="1.6 x 1.0 x 0.5 max mm, 2 terminals", package_page=1, land_page=1,
    pin1="Non-polar: #1 and #2 are interchangeable", polarity=None,
    pins={1: ("#1", "passive", "Crystal terminal"), 2: ("#2", "passive", "Crystal terminal")},
    notes="CL 12.5 pF, ESR 90 kOhm max, C0 1.2 pF typ, drive level 0.1 uW typ / 0.5 uW absolute max (p.1). 'No pattern under "
          "the SC-16S' (p.1 remark)."),
"C2826535": dict(mpn="BW0036BG-L3.0W1.0H1.4", mfr="BAT WIRELESS", refs="J11 (E3); J1, J2 (CHARGE=contacts); J13 (SB_ANT=lid)", ds="C2826535_bw0036bg",
    ds_dir="/path/to/SolarVest_work/wristband/cache/v2/ds_fix/C2826535_bw0036bg",
    url="https://datasheet.lcsc.com/datasheet/pdf/0d9351c75350d96481cb46f6d203076e.pdf?productCode=C2826535", doc="BW0036BG-L3.0W1.0H1.4 data sheet (April-14-2025-A01), drawing 681-0036B-2",
    pin_table="Dimension drawing with the solder pad, p.6 (render v2/design/fix/evidence/bw0036bg_p6.png)",
    package="Spring finger 2.90 +-0.10 x 1.00 +-0.08 mm, free height 1.40 +0.10 / -0.05 mm, working height 1.00 mm, limit 0.70 mm, 60-80 gf, one solder pad 2.30 x 1.00 mm",
    package_page=6, land_page=6,
    pin1="One pad: no pin 1. The spring arm points to one end, so the part is mechanically polar and electrically neutral",
    polarity=None, pins={1: ("1", "passive", "Contact (the only terminal)")},
    notes="JLC part page 2026-11-12 23:00 UTC: 'SMT Assembly' (assemblyMode smtWeld); the BW0025BG C2826523 used before is 'Wave Soldering' (manualWeld). "
          "Contact tip about 0.35 +-0.15 mm inside the non-folded end, i.e. 0.6-0.8 mm from the pad centre (drawing, estimate): a tab of 3.4 x 2.2 mm centred "
          "on the pad centre covers the tip at 0 and at 180 deg with +-0.3 mm of tolerance. 180 deg cannot be proven by pad geometry; 90 deg is caught by the pad shape.",
    human_review="arm direction in the JLC preview against the mating tab drawing (cplgate class: mechanically polar, electrically neutral)"),
"C2826523": dict(mpn="BW0025BG-L2.8W1.55H1.35", mfr="BAT WIRELESS", refs="not used after the review fix (R-04: wave / manual soldering at JLC)", ds="bw0025bg",
    url="https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2105242107_BAT-WIRELESS-BW0025BG-L2-8W1-55H1-35_C2826523.pdf", doc="BW0025BG-L2.8W1.55H1.35 data sheet",
    pin_table="Dimension drawing with the solder pad, p.6 (read and rendered by the redesign build review: cache/redesign/attack_build/ds/bw0025bg_C2826523_p6.png)",
    package="Spring finger 2.8 x 1.55 x 1.35 mm (free height), working height 0.90 mm, 60-80 gf, one solder pad 1.95 x 1.55 mm", package_page=6, land_page=6,
    pin1="One pad: no pin 1. The spring arm points to one end, so the part is mechanically polar and electrically neutral",
    polarity=None, pins={1: ("1", "passive", "Contact (the only terminal)")},
    notes="180 deg cannot be proven by pad geometry and nothing measures it before the ring is on: the mating tab must be >= 3.4 x 2.2 mm and "
          "centred on the pad centre so that contact is made at 0 and 180 deg (REDESIGN 5.8 item 6). 90 deg is caught by the pad shape.",
    human_review="arm direction in the JLC preview against the mating tab drawing (new cplgate class: mechanically polar, electrically neutral)"),
}
PARTS = dict(V1); PARTS.update(PARTS_V2)
for _c, _d in PARTS.items():
    _d.setdefault("ds_dir", V1DS if _c in V1 else V2DS)
