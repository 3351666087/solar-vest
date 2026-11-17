# SolarBand V3-F main board - EasyEDA footprint audit (both build variants)

Generated 2026-11-16 by `v3/design/tools/audit_footprints.py` from `lib/easyeda.pretty` (easyeda2kicad output of the
EasyEDA records; V3-F raw records are kept outside the project) and `pinmap/<C>.yaml`. The board uses the reviewed copy
`lib/easyeda_rev.pretty` whose numbered copper pads are verified identical to these (last section), so KiCad's pad geometry
and 0 deg are JLC's own (ARCHITECTURE 10.1). Nothing below was edited to make it pass.

Verdicts: **PASS** = matches the datasheet land within ~0.1 mm; **PASS-NOTE** = pin 1, numbering, pitch and rows correct,
land size differs from the vendor drawing but is solderable (noted, not changed); **FLAG** = a human decision is needed
before layout / order.

Totals: 70 PASS, 22 PASS-NOTE, 1 FLAG (over 93 distinct LCSC parts incl. DNP pads). [V3F] The FLAG is the raw EasyEDA land of C549275; the board uses the corrected copy (C478155 SOT883 pad set), see its entry and the reviewed-copy table.

V2-B: the parts that are new against v1 are C509405, C4371025, C2760012, C727398, C478155, C253326, C130414, C5603826, C598214,
C398713, C2826535 and the 0201 / 0402 / 0603 passives with new C-numbers; their datasheet land drawings were read on 2026-11-12 (renders in
`cache/v2/ds/png/` and `v2/design/fix/evidence/`). A footprint whose land could not be compared with a vendor drawing says so in its note;
FLAG = not usable as it is. After the independent review (R-04, R-06, R-12): spring finger C2826523 -> C2826535, warning LED C125114 -> C598214,
and the lands of the two 0.4 mm BGA-class parts are 0.20 mm in the reviewed copy (see the last section).

V3-F (2026-11-13): new parts C5208201, C2867950, C5187176, C5217869, C549313, C549275, C20345399, C896422, C221907, C2876045, C478207, C17913 and 0201 / 0402
passives. Their land drawings were read on 2026-11-13 from the maker datasheets (URL, page and sha256 in pinmap/<C>.yaml; renders viewed in the session, not kept).
Two findings: the EasyEDA numbering of TLV7031DPWR (C2876045) differs from TI's (mapped by position in the pin map), and the BAT54CM (C549275) small lands are too
narrow (copper replaced by the reviewed SOT883 pad set, the second permitted copper change); BAV70M (C549313) has no EasyEDA record (derived land, preview mandatory).

| LCSC | Part | Refs | EasyEDA package | Verdict |
|---|---|---|---|---|
| C130414 | BAS521,115 | D9, D11 | SOD-523_L1.2-W0.8-LS1.6-RD | PASS-NOTE |
| C139059 | ADS1291IRSMR | U7 | QFN-32_L4.0-W4.0-P0.40-BL-EP2.9 | PASS-NOTE |
| C17445 | 0805W8F120JT5E | R130 | R0805 | PASS |
| C189624 | LIS2DW12TR | U9 | LGA-12_L2.0-W2.0-P0.50-BL | PASS-NOTE |
| C20345399 | ESD761DPYR | D13 | X1SON-2_L1.0-W0.6-P0.65-BI | PASS-NOTE |
| C2048575 | LQW15AN7N6G80D | C215 | IND-SMD_L1.0-W0.6 | PASS |
| C2050114 | VLS201610CX-220M-1 | L1 | IND-SMD_L2.0-W1.6 | PASS-NOTE |
| C221907 | PTS840GKSMTRLFS | SW1 | SW-SMD_4P-L3.5-W3.5_PTS840GKSMTRLFS | PASS |
| C2803242 | TMP117MAIDRVR | U10 | WSON-6_L2.0-W2.0-P0.65-BL-EP | PASS-NOTE |
| C2826518 | BW0020AG-L3.5W1.5H3.0 | J40 | ANT-SMD_L3.5-W1.5 | PASS-NOTE |
| C2826535 | BW0036BG-L3.0W1.0H1.4 | J11, J15, J18, J19 | SMD_L2.9-W1.0-2108613-5 | PASS-NOTE |
| C2863637 | TLV7031DCKR | U19, U20 | SC-70-5_L2.1-W1.3-P0.65-LS2.2-BR | PASS |
| C2867950 | TPS7A0230PDQNR | U16 | UDFN-4_L1.0-W1.0-P0.65-TL | PASS |
| C324723 | FH34SRJ-10S-0.5SH(50) | J13 | FFC-SMD_10P-P0.50_FH34SRJ-10S-0.5SH | PASS |
| C398713 | SC-16S-32.768KHZ-20PPM-12.5PF | X2 | CRYSTAL-SMD_L1.6-W1.0 | PASS-NOTE |
| C434843 | VLS201610CX-100M-1 | L2 | IND-SMD_L2.0-W1.6 | PASS-NOTE |
| C4371025 | INA236AIYBJR | U4, U5 | DSBGA-8_L1.5-W0.7-R2-C4-P0.40-BL | PASS-NOTE |
| C471381 | LQW15AN4N3B80D | L204 | IND-SMD_L1.0-W0.6 | PASS |
| C478155 | PMZ290UNE2YL | Q1, Q4, Q5, Q6, Q7, Q8, Q9, Q10, Q11, Q12, Q13, Q16, Q17, Q19 | DFN1006-3L_L1.0-W0.6-LS1.0-BR | PASS-NOTE |
| C478207 | PMZ350UPEYL | Q14, Q18 | X1-DFN1006-3_L1.0-W0.6-P0.35-BR | PASS-NOTE |
| C48260 | TPD1E10B06DPYR | D5, D6, D7, D8, D15, D18 | X1SON-2_L1.0-W0.6-P0.65-BI-1 | PASS-NOTE |
| C504101 | CJBA7002K | Q20 | DFN1006-3L_L1.0-W0.6-BL | PASS-NOTE |
| C506250 | BQ25570RGRR | U1 | VQFN-20_L3.5-W3.5-P0.50-BL-EP2.0 | PASS-NOTE |
| C509405 | NRF52832-CIAA-R | U6 | WLCSP-50_L3.2-W3.0-TL_NRF52832 | PASS-NOTE |
| C511402 | VEMD8080 | PD1 | SENSOR-SMD_8P-L4.8-W2.5-P1.31 | PASS |
| C5187176 | TXU0104RUTR | U17 | XQFN-12_L2.0-W1.7-P0.40-BL | PASS-NOTE |
| C5208201 | BQ25170DSGR | U15 | WSON-8_L2.0-W2.0-P0.50-TL-EP | PASS |
| C5217869 | TXU0101DRYR | U21 | SON-6_L1.5-W1.0-P0.50-TL | PASS |
| C5220164 | TPS7A2030PDQNR | U3 | X2SON-4_L1.0-W1.0-P0.65-TL-EP | PASS-NOTE |
| C5328762 | MAX86141ENP+T | U8 | BGA-20_L2.0-W1.8-R4-C5-P0.40-TL | PASS-NOTE |
| C549275 | BAT54CM,315 | D17, D19 | DFN1006-3_L1.0-W0.6-P0.35-BR_BAT54CM | FLAG |
| C549313 | None | D12 | PROXY of C549275 (no EasyEDA record) | PASS-NOTE |
| C5603826 | CT DBLP31.12 | D3, D4 | LED-SMD_3P-L2.2-W1.8_C5D-56-J6U6-20-R18 | PASS |
| C5687033 | MX25R1635FZUIH0 | U11 | USON-8_L3.0-W2.0-P0.50-BL-EP1.6_MX25R1635FZUIH0 | PASS |
| C598214 | KA-2810ASURSK | D10 | LED-SMD_L2.5-W1.2_KA-2810AVBS-D | PASS |
| C6736531 | PMEG10020AELR-QX | D14 | SOD-123F_L2.8-W1.8-LS3.7-RD | PASS |
| C718072 | X201632MKB4SI | X1 | CRYSTAL-SMD_4P-L2.0-W1.6-BL | PASS |
| C727398 | SIP32431DNP3-T1GE4 | U12, U13 | TDFN-4_L1.2-W1.6-P0.50-BL-EP | PASS |
| C896422 | NSR0240MX2T5G | D16 | X2DFN-2_L1.0-W0.6-RD | PASS-NOTE |
| C105226 | CL05A226MQ5QUNC | C105, C114, C115, C116, C117, C118(DNP) | C0402 | PASS |
| C1518204 | GRM1555C1H472JE01D | C305, C306 | C0402 | PASS |
| C1546 | 0402CG101J500NT | C213(DNP) | C0402 | PASS |
| C15525 | CL05A106MQ5NUNC | C307, C402, C502 | C0402 | PASS |
| C161408 | GRM0335C1H151JA01D | C304 | C0201 | PASS |
| C161418 | GRM0335C1H221JA01D | C175 | C0201 | PASS |
| C166160 | RTT015362FTH | R172 | R0201 | PASS |
| C19666 | CL10A475KO8NNNC | C101 | C0603 | PASS |
| C19702 | CL10A106KP8NNNC | C102, C404 | C0603 | PASS |
| C23733 | CL05A475MP5NRNC | C121, C209 | C0402 | PASS |
| C237514 | GJM0335C1H1R0BB01D | C203 | C0201 | PASS |
| C25076 | 0402WGF1000TCE | R318, R319 | R0402 | PASS |
| C2691509 | 0201WMF1623TEE | R171 | R0201 | PASS |
| C270345 | 0201WMF4702TEE | R129 | R0201 | PASS |
| C270346 | 0201WMF4701TEE | R127, R505, R506 | R0201 | PASS |
| C270358 | 0201WMF2001TEE | R141 | R0201 | PASS |
| C270364 | 0201WMF1003TEE | R116, R165, R315, R316, R401, R402, R501, R503, R504, R509 | R0201 | PASS |
| C270365 | 0201WMF1001TEE | R162 | R0201 | PASS |
| C270366 | 0201WMF1000TEE | R133, R160 | R0201 | PASS |
| C270612 | 0402WGF330KTCE | R117 | R0402 | PASS |
| C2766851 | 0402WGF5764TCE_C2766851 | R101 | R0402 | PASS |
| C285010 | 0201B103K250NT | C113, C120 | C0201 | PASS |
| C295786 | RC0201FR-071ML | R124, R128, R144, R145, R146, R149, R161, R163, R164, R167, R175, R176, R508, R510 | R0201 | PASS |
| C309454 | CC0201KRX7R8BB472 | C132 | C0201 | PASS |
| C384960 | GRM0335C1H120FA01D | C201, C202 | C0201 | PASS |
| C3855387 | GRM1555C1E103JE01D | C104 | C0402 | PASS |
| C413063 | ERJ2RKF1000X | R507 | R0402 | PASS |
| C423135 | 0402WGF7504TCE | R106 | R0402 | PASS |
| C423137 | 0402WGF7324TCE | R102 | R0402 | PASS |
| C423177 | 0402WGF4024TCE | R107 | R0402 | PASS |
| C423179 | 0402WGF3924TCE | R103 | R0402 | PASS |
| C423439 | 0201WMF7323TEE | R170 | R0201 | PASS |
| C423582 | 0201WMF3304TEE | R126 | R0201 | PASS |
| C423797 | 0201WMF1005TEE | R108, R125, R131, R174, R307(DNP), R308(DNP), R309(DNP) | R0201 | PASS |
| C43676 | 0402WGF3602TCE | R142 | R0402 | PASS |
| C441935 | ERJPA3F3303V | R301, R302, R303, R304, R305, R306 | R0603 | PASS |
| C45993 | 0402WGF3833TCE | R105 | R0402 | PASS |
| C473048 | 0201WMF1002TEE | R311, R312, R313, R314, R511 | R0201 | PASS |
| C473458 | 0201WMF2203TEE | R123, R143 | R0201 | PASS |
| C473473 | 0201WMF0000TEE | FB1, FB2, FB3, FB4, FB5, FB6 | R0201 | PASS |
| C473560 | 0201WMF4703TEE | R317 | R0201 | PASS |
| C477775 | RC0402FR-076M81L | R104 | R0402 | PASS |
| C52923 | CL05A105KA5NQNC | C111, C112, C130, C131, C210, C309, C310, C311, C403, C1501, C1502 | C0402 | PASS |
| C59461 | CL10A226MQ8NRNC | C106 | C0603 | PASS |
| C6807729 | MPH160809S100MT | L202 | L0603 | PASS |
| C7393837 | TCC0201X7R104K100ZT | C103, C107, C108, C170, C174, C204, C205, C308, C312, C314, C401, C405, C501, C504, C505, C1503, C1601, C1602, C1603 | C0201 | PASS |
| C76922 | GRM0335C1H101JA01D | C206, C207, C303(DNP) | C0201 | PASS |
| C76923 | GRM0335C1H200JA01D | C211, C212 | C0201 | PASS |
| C76924 | GRM0335C1H220JA01D | C301(DNP), C302(DNP) | C0201 | PASS |
| C76935 | GRM033R61A105ME44D | C119, C122, C313 | C0201 | PASS |
| C851635 | RC0201DR-0710K2L | R140 | R0201 | PASS |
| C86059 | LQG15HS15NJ02D | L203 | L0402 | PASS |
| C861215 | RT0603BRD071RL | R111, R112 | R0603 | PASS |
| C98045 | LQP03TN3N3B02D | L201 | L0201-RD | PASS |

## Per-part detail

### C130414 BAS521,115 - D9, D11 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C130414_SOD-523_L1.2-W0.8-LS1.6-RD` (package `SOD-523_L1.2-W0.8-LS1.6-RD`, corner token `-`), 2 pads; 3D `SOD-523_L1.2-W0.8-H0.7-LS1.6`
- Datasheet: BAS521 product data sheet, pin table Table 2 Pinning information, p.1; pin 1: Pin 1 = cathode, marked by the cathode band
- Datasheet land/package: Nexperia BAS521 Fig. 10 reflow footprint SOD523 (p.6): lands 0.50 x 0.60 at centres 1.40, occupied 2.15 x 1.2; pinning Table 2 p.1: 1 = cathode
- EasyEDA measured: pads 0.36 x 0.60; centre span 1.30
- Automatic checks: pads = pin map; symbol names agree 2/2
- Verdict: **PASS-NOTE** - Pad 1 = cathode ('C' in the EasyEDA symbol) = datasheet. Lands 0.60 x 0.36 at centres 1.30: 0.24 mm narrower across the body and 0.05 mm closer than Nexperia's; solderable (terminal 0.3 x 0.3). Polarized 2-terminal part: human review + electrical proof (EN hold works only one way round).

### C139059 ADS1291IRSMR - U7 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C139059_QFN-32_L4.0-W4.0-P0.40-BL-EP2.9` (package `QFN-32_L4.0-W4.0-P0.40-BL-EP2.9`, corner token `BL`), 33 pads; 3D `QFN-32_L4.0-W4.0-P0.40-BL-EP2.9`
- Datasheet: SBAS502C (Apr 2020), pin table Pin Functions, p.4-5; pin 1: Pin 1 index at the pin 1 / pin 32 corner (RSM0032B); counter-clockwise, top view
- Datasheet land/package: TI RSM0032B land example p.81: pad 0.20 x 0.55, pitch 0.40, rows 3.85, EP 2.80 x 2.80
- EasyEDA measured: pads 0.20 x 0.70; centre span 4.10, EP 2.90 x 2.90 (#33)
- Automatic checks: pads = pin map; symbol names agree 33/33; pin 1 at bottom-left; numbering CCW (not mirrored)
- Verdict: **PASS-NOTE** - Pin 1 corner and CCW numbering correct (rotated 90 deg). Oval pads 0.20 x 0.70 at rows 4.10 (inner edge 1.70 vs 1.65), EP 2.90 vs 2.80: EP-to-pad gap 0.25 as TI. EasyEDA SYMBOL pin names for pins 9-14 and 16 are corrupted ('32VREFP', '31VREFN', '30VCAP1', '29AVDD', '28AVSS', '27CLKSEL', '25START'): our schematic uses the datasheet names, but cplgate G3 must alias-strip the leading digits or it will report a name mismatch.

### C17445 0805W8F120JT5E - R130 - **PASS**

- EasyEDA footprint `easyeda:C17445_R0805` (package `R0805`, corner token `-`), 2 pads; 3D `None`
- Datasheet land/package: 0805 chip resistor (UNI-ROYAL 0805W8F120JT5E, 125 mW; datasheet V.9 p.4: 2.00 x 1.25 x 0.55 mm, terminations 0.40 +-0.20)
- EasyEDA measured: pads 1.13 x 1.38; centre span 2.00
- Verdict: **PASS** - [G1 level 0] EasyEDA R0805 land (measured values in the table below): standard chip land for a 2.0 x 1.25 mm body; non-polar.

### C189624 LIS2DW12TR - U9 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C189624_LGA-12_L2.0-W2.0-P0.50-BL` (package `LGA-12_L2.0-W2.0-P0.50-BL`, corner token `BL`), 12 pads; 3D `LGA-12_L2.0-W2.0-H1.0-P0.50`
- Datasheet: DocID029682 Rev 4 (Sep 2017), pin table Table 2 Pin description, p.9 (Figure 2 pin connections, bottom view); pin 1: Pin 1 indicator dot on top; pin 1 is a corner pad; 1-4 down one side (top view counter-clockwise)
- Datasheet land/package: ST LGA-12 2.0x2.0x0.7 p.61: 12 terminals on a 4 x 4 perimeter, pitch 0.50, span 1.50, terminal ~0.25 x 0.275; land pattern only 'at www.st.com' (TN0018, not cached)
- EasyEDA measured: pads 0.28 x 0.50; centre span 1.76
- Automatic checks: pads = pin map; symbol names agree 11/12; pin 1 at bottom-left; numbering CCW (not mirrored)
- Symbol name differences (informational, schematic uses datasheet names): 10: EasyEDA 'VDDIO' vs DS 'VDD_IO'
- Verdict: **PASS-NOTE** - Pin 1 corner and CCW order match Figure 2 (bottom view mirrored to top view, then rotated 90 deg). Rectangular lands 0.28 x 0.50 cover each terminal and extend 0.25 mm outward.

### C20345399 ESD761DPYR - D13 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C20345399_X1SON-2_L1.0-W0.6-P0.65-BI` (package `X1SON-2_L1.0-W0.6-P0.65-BI`, corner token `-`), 2 pads; 3D `None`
- Datasheet: SLVSH10C (November 2022, revised December 2022), pin table Figure 5-1 DPY X1SON-2 top view and Table 5-1, p.3; pin 1: bidirectional: orientation irrelevant (class N)
- Datasheet land/package: TI SLVSH10C p.19 DPY0002A land example: 2 pads 0.3 x 0.5 mm, centres (0.7)
- EasyEDA measured: pads 0.60 x 0.60; centre span 1.00
- Automatic checks: pads = pin map; symbol names agree 0/2
- Symbol name differences (informational, schematic uses datasheet names): 1: EasyEDA '1' vs DS 'IO'; 2: EasyEDA '2' vs DS 'GND'
- Verdict: **PASS-NOTE** - EasyEDA pads 0.60 x 0.60 at x +-0.50: same inner edge (0.20) as TI, outer edge 0.30 mm further out; symmetric, bidirectional part (class N). Solderable; larger fillet area.

### C2048575 LQW15AN7N6G80D - C215 - **PASS**

- EasyEDA footprint `easyeda:C2048575_IND-SMD_L1.0-W0.6` (package `IND-SMD_L1.0-W0.6`, corner token `-`), 2 pads; 3D `None`
- Datasheet land/package: Murata LQW15AN_80 reference spec JELF243A_0100H-01 section 12.1 (same series as C6652901): a 0.6, b 1.42, c 0.66
- EasyEDA measured: pads 0.50 x 0.65; centre span 0.86
- Verdict: **PASS** - [F] C215 7.6 nH LQW15AN7N6G80D (RF_FINAL re-tune). Same Murata land as C6652901 (0.41 x 0.66 at +-0.505), checked pad by pad below (MAKER LAND). Non-polar.

### C2050114 VLS201610CX-220M-1 - L1 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C2050114_IND-SMD_L2.0-W1.6` (package `IND-SMD_L2.0-W1.6`, corner token `-`), 2 pads; 3D `IND-SMD_L2.0-W1.6-H1.1`
- Datasheet land/package: TDK VLS201610CX-1 p.3 recommended land: 0.65 x 1.6, gap 0.70 (centres 1.35)
- EasyEDA measured: 
- Verdict: **PASS-NOTE** - Lands 1.00 x 1.72 at centres 1.66 (gap 0.66): 0.33 mm longer per end. Non-polar. Height 1.0 mm max (fits the 1.0 mm skin-side budget).

### C221907 PTS840GKSMTRLFS - SW1 - **PASS**

- EasyEDA footprint `easyeda:C221907_SW-SMD_4P-L3.5-W3.5_PTS840GKSMTRLFS` (package `SW-SMD_4P-L3.5-W3.5_PTS840GKSMTRLFS`, corner token `-`), 5 pads; 3D `None`
- Datasheet: C&K catalogue pages B-40 to B-42 'PTS 840 Series Microminiature SMT Side Actuated', pin table Schematic and recommended PCB layout, p.2 (B-41): pins 1-2 joined, 3-4 joined; pin 5 = ESD ground pin of the ESD versions only; pin 1: mechanically polar: the actuator must face the wall; the 4-pad land fits turned 180 deg (pins 1-2 / 3-4 swap, electrically the same)
- Datasheet land/package: C&K PTS840 datasheet p.2 (B-41) 'RECOMMENDED PCB LAYOUT', G leads (LCSC copy of C221907, re-read 2026-11-15): 5 +-0.1 over the pads across the leads, gap 2.2 +-0.1 -> pads 1.40 long at +-1.80; 2.5 +-0.1 along the actuation axis, gap 0.4 +-0.1 -> pads 1.05 wide at +-0.725 about the lead line; lead tips 4.7 apart, lead rows 1.5 +-0.1; body 3.5 x 2.9, actuator 1.7 x 0.65; ESD pad 5 (1.1 x 0.5) only on ESD versions
- EasyEDA measured: 
- Automatic checks: PAD MISMATCH missing [] extra ['5']; symbol names agree 4/4; pin 1 at bottom-left; numbering CW = MIRRORED
- Verdict: **PASS** - [G1 level 0] The reviewed copy now carries C&K's own land, checked pad by pad below (tools/review_footprints.py SET_PAD): pads 1.05 x 1.40 mm at x -1.195 / +0.255 (lead line x -0.47 +- 0.725), y +-1.80 in the EasyEDA frame (actuation axis = x, actuator at -x). Origin, 0 deg and pad numbers are EasyEDA's (JLC's centroid). Lead foot (1.75-2.35 mm from the centre line) lies fully on the pad (1.10-2.50): toe 0.15 mm, heel under the body 0.65 mm. The raw EasyEDA land was 0.84 x 1.785 at y +-2.12 (span 6.03 mm). EasyEDA numbers the C&K positions 4, 3, 2, 1: the joined pairs {1,2} and {3,4} coincide, so the switch connects the same two nets. Pad 5 stays deleted (GK has no pin 5, S1 D-9). Courtyard 4.04 x 5.50 mm = 22.2 mm2 (stage 1: 4.04 x 6.54 = 26.4). Mechanically polar (class M): the actuator must face the wall in the JLC preview.

### C2803242 TMP117MAIDRVR - U10 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C2803242_WSON-6_L2.0-W2.0-P0.65-BL-EP` (package `WSON-6_L2.0-W2.0-P0.65-BL-EP`, corner token `BL`), 7 pads; 3D `WSON-6_L2.0-W2.0-H0.8-P0.65`
- Datasheet: SNOSD82D (Sep 2022), pin table Table 5-1 Pin Functions, p.4; pin 1: Pin 1 index top-left (DRV0006B top view)
- Datasheet land/package: TI DRV0006B example board layout p.41: pad 0.30 x 0.45, pitch 0.65, rows 1.95, NO thermal-pad land (p.35: thermal pad best left unsoldered)
- EasyEDA measured: pads 0.40 x 0.45; centre span 1.96, EP 1.00 x 1.60 (#7)
- Automatic checks: pads = pin map; symbol names agree 7/7; pin 1 at bottom-left; numbering CCW (not mirrored)
- Verdict: **PASS-NOTE** - Pads 0.40 x 0.45 at rows 1.96, pin 1 / CCW correct. The EasyEDA footprint ADDS a 1.0 x 1.6 mm land (pad 7) with paste under the thermal pad, which TI's layout omits for best accuracy; soldered is allowed if floating or GND (datasheet). Schematic leaves pin 7 unconnected (floating island coupled to E1, R-THERM-1). RESOLVED (Integrate 2026-11-12): the board uses the reviewed copy lib/easyeda_rev.pretty with NO paste on pad 7 (copper unchanged), i.e. the thermal pad stays unsoldered as TI recommends.

### C2826518 BW0020AG-L3.5W1.5H3.0 - J40 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C2826518_ANT-SMD_L3.5-W1.5` (package `ANT-SMD_L3.5-W1.5`, corner token `-`), 1 pads; 3D `None`
- Datasheet: BW0020AG-L3.5W1.5H3.0 drawing (read by eye by the stage-2c lane, v3/stage2c/ECO2C.md; the URL returned an empty body online on 2026-11-16), pin table one solder pad 2.10 x 1.50 mm, contact apex 0.90 +-0.15 mm (ECO2C.md, as BW0019BG); pin 1: One pad: no pin 1. The arm points to one end: mechanically polar, electrically neutral
- Datasheet land/package: BAT WIRELESS BW0020AG-L3.5W1.5H3.0 drawing (read by eye in stage 2c, v3/stage2c/ECO2C.md 2): same solder pad and body as BW0019BG; free height 3.00, working 2.50, limit 2.00
- EasyEDA measured: 
- Automatic checks: pads = pin map; symbol names agree 1/1
- Verdict: **PASS-NOTE** - [S2d J-1] J40. No EasyEDA record fetched in stage 2d: the board keeps the reviewed C2826516 land (2.10 x 1.50 = the BW0019BG / BW0020AG solder pad), as LEAD_NOTES 2j J-1 rules (same land, position and rotation). Open: EasyEDA / JLC footprint check of C2826518 and the JLC preview (rot 340).

### C2826535 BW0036BG-L3.0W1.0H1.4 - J11, J15, J18, J19 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C2826535_SMD_L2.9-W1.0-2108613-5` (package `SMD_L2.9-W1.0-2108613-5`, corner token `-`), 1 pads; 3D `None`
- Datasheet: BW0036BG-L3.0W1.0H1.4 data sheet (April-14-2025-A01), drawing 681-0036B-2, pin table Dimension drawing with the solder pad, p.6 (render v2/design/fix/evidence/bw0036bg_p6.png); pin 1: One pad: no pin 1. The spring arm points to one end, so the part is mechanically polar and electrically neutral
- Datasheet land/package: BAT WIRELESS BW0036BG-L3.0W1.0H1.4 drawing 681-0036B-2 (p.6, render v2/design/fix/evidence/bw0036bg_p6.png): solder pad 2.30 x 1.00 mm (+-0.05), body 2.90 +-0.10 x 1.00 +-0.08, free height 1.40 +0.10/-0.05, working height 1.00, limit 0.70
- EasyEDA measured: 
- Automatic checks: pads = pin map; symbol names agree 1/1
- Verdict: **PASS-NOTE** - One rectangular land 2.40 x 1.20 mm against the maker's 2.30 x 1.00 mm solder area: 0.05 / 0.10 mm larger per side, solderable. EasyEDA body outline -1.95 ... +0.95 mm from the land centre (the folded end overhangs the land by 0.75 mm). 180 deg cannot be proven by pad geometry: the mating tab is specified >= 3.4 x 2.2 mm centred on the land centre so that the tip (0.6-0.8 mm from the centre) is under the tab at 0 and at 180 deg (REDESIGN 5.8 item 6); 90 deg is caught by the land shape. JLC part page 2026-11-12 23:00 UTC: SMT Assembly.

### C2863637 TLV7031DCKR - U19, U20 - **PASS**

- EasyEDA footprint `easyeda:C2863637_SC-70-5_L2.1-W1.3-P0.65-LS2.2-BR` (package `SC-70-5_L2.1-W1.3-P0.65-LS2.2-BR`, corner token `BR`), 5 pads; 3D `None`
- Datasheet: SLVSE13J (September 2017, revised November 2024), pin table Figure 4-1 TLV70x1 'North West' pinout DBV/DCK top view and Table 4-1, p.3: 1 OUT, 2 V-, 3 IN+, 4 IN-, 5 V+; pin 1: SC70-5: pins 1-3 on one side (pin 1 at the pin-1 index end), 4-5 on the other (4 opposite 3, 5 opposite 1). EasyEDA C2863637 uses TI's numbers (pads 1-3 at x +1.10, 4-5 at x -1.10). [ECO3 2026-11-16] replaces the X2SON C2876045.
- Datasheet land/package: TI SLVSE13J p.3 Fig. 4-1 / Table 4-1 (TLV70x1 North-West pinout, DBV/DCK): 1 OUT, 2 V-, 3 IN+, 4 IN-, 5 V+; p.60 DCK0005A land example: 5X 0.95 x 0.40, pitch 0.65, row centres 2.2 (pads at x +-1.10)
- EasyEDA measured: pads 0.40 x 0.90; centre span 2.20
- Automatic checks: pads = pin map; symbol names agree 4/5; pin 1 at bottom-right; numbering CCW (not mirrored)
- Symbol name differences (informational, schematic uses datasheet names): 2: EasyEDA 'GND' vs DS 'VEE'
- Verdict: **PASS** - [ECO3] EasyEDA C2863637: 5 pads 0.90 x 0.40 at x +-1.10, y 0 / +-0.65 (TI 0.95 x 0.40: 0.05 mm shorter, same centres). Numbering = TI: 1 (1.10, 0.65) OUT, 2 (1.10, 0) V-, 3 (1.10, -0.65) IN+, 4 (-1.10, -0.65) IN-, 5 (-1.10, 0.65) V+; EasyEDA symbol names 1 OUT, 2 GND, 3 IN+, 4 IN-, 5 VCC (same functions, same numbers). Every pad has a free outer end (escape outward); side gaps 0.25 mm.

### C2867950 TPS7A0230PDQNR - U16 - **PASS**

- EasyEDA footprint `easyeda:C2867950_UDFN-4_L1.0-W1.0-P0.65-TL` (package `UDFN-4_L1.0-W1.0-P0.65-TL`, corner token `TL`), 5 pads; 3D `None`
- Datasheet: SBVS277C (July 2019, revised September 2022), pin table Figure 5-1 DQN 1 x 1 mm X2SON-4 top view and Table 5-1, p.3; pin 1: X2SON-4: pin 1 OUT and pin 2 GND on one side, pin 3 EN and pin 4 IN on the other, thermal pad in the middle; pin-1 index on top
- Datasheet land/package: TI SBVS277C p.40 DQN0004A land example: 4 corner pads 0.36 x 0.21 (chamfered), centres (0.86) x (0.65), centre pad 0.48 square at 45 deg
- EasyEDA measured: pads 0.01 x 0.01 / 0.48 x 0.48; centre span 0.84
- Automatic checks: pads = pin map; symbol names agree 4/5; pin 1 at top-left; numbering CCW (not mirrored)
- Symbol name differences (informational, schematic uses datasheet names): 5: EasyEDA 'EP' vs DS 'PAD'
- Verdict: **PASS** - EasyEDA custom pads 1-4 at (+-0.42, +-0.33): 0.84 x 0.65 centre spacing (TI 0.86 x 0.65); centre pad 0.48 x 0.48 rotated 45 deg = TI. Pin 1 top-left, 2 bottom-left, 3 bottom-right, 4 top-right (TI Fig. 5-1). Same land as U3 (C5220164, v2). Fits turned 180 deg (2F): preview + G10 (g).

### C324723 FH34SRJ-10S-0.5SH(50) - J13 - **PASS**

- EasyEDA footprint `easyeda:C324723_FFC-SMD_10P-P0.50_FH34SRJ-10S-0.5SH` (package `FFC-SMD_10P-P0.50_FH34SRJ-10S-0.5SH`, corner token `-`), 12 pads; 3D `None`
- Datasheet: Hirose FH34 Series catalogue, Oct. 2022 (0.5 mm pitch, 1.0 mm height, top and bottom contact, back flip), pin table p.6 'Contact No.1' at the +x end of the lead row; p.8 recommended FPC: contact No.1 (top contact) on the right; panel terminals LS011B7DH03 p.14 Table 4-1; pin 1: contact 1 at the +x end of the lead row (EasyEDA pad 1 at x +2.25, y -1.25); the land (10 pads in one row + 2 tab pads on the other side) cannot be placed turned 180 deg
- Datasheet land/package: Hirose FH34 catalogue Oct. 2022 (Farnell 3932894.pdf, read 2026-11-15) p.8-9 recommended PCB mounting pattern, 10 pos: contact pads 0.3 +-0.05 x 0.8 +-0.05 at 0.5, B 4.5 (pad 1 .. 10 centres); retention-tab pads between E 6.1 and F 6.9 (0.4 wide, centres +-3.25), 0.8 long; 3.3 +-0.05 from the outer edge of the contact row to the outer edge of the tab pads (centres 2.5 apart); contact No.1 at the right end of the row seen from above with the row at the top (p.6, p.8); body A 7.0 +-0.15 x depth 3.8 x 1.0 (p.6)
- EasyEDA measured: pads 0.30 x 0.80 / 0.40 x 0.80; centre span 6.50
- Automatic checks: pads = pin map; symbol names agree 0/12; pin 1 at top-right; numbering CCW (not mirrored)
- Symbol name differences (informational, schematic uses datasheet names): 1: EasyEDA '1' vs DS 'C1_SCLK'; 2: EasyEDA '2' vs DS 'C2_SI'; 3: EasyEDA '3' vs DS 'C3_SCS'; 4: EasyEDA '4' vs DS 'C4_EXTCOMIN'; 5: EasyEDA '5' vs DS 'C5_DISP'; 6: EasyEDA '6' vs DS 'C6_VDDA'; 7: EasyEDA '7' vs DS 'C7_VDD'; 8: EasyEDA '8' vs DS 'C8_EXTMODE'; 9: EasyEDA '9' vs DS 'C9_VSS'; 10: EasyEDA '10' vs DS 'C10_VSSA'; 11: EasyEDA '11' vs DS 'MP1'; 12: EasyEDA '12' vs DS 'MP2'
- Verdict: **PASS** - [S2a] EasyEDA C324723 checked pad by pad against Hirose p.8-9: pads 1-10 0.30 x 0.80 at x +2.25 .. -2.25 step 0.5, y -1.25 (row outer edge -1.65); pads 11 / 12 0.40 x 0.80 at x -/+3.25, y +1.25 (outer edge +1.65): overall 3.30, E 6.10, F 6.90, B 4.50 as drawn; pad 1 at +x = contact No.1. Courtyard rebuilt from the body box (the EasyEDA courtyard missed the lead row). A 180 deg turn puts the 10-pad row on the 2 tab pads (class 1F).

### C398713 SC-16S-32.768KHZ-20PPM-12.5PF - X2 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C398713_CRYSTAL-SMD_L1.6-W1.0` (package `CRYSTAL-SMD_L1.6-W1.0`, corner token `-`), 2 pads; 3D `CRYSTAL-SMD_L1.6-W1.0`
- Datasheet: SC-16S data sheet (SII), pin table Internal lead connections and dimensions, p.1; pin 1: Non-polar: #1 and #2 are interchangeable
- Datasheet land/package: Seiko SC-16S p.1 recommended soldering pattern: 0.5 x 1.0 (2x), gap 0.6, centres 1.1; 'no pattern under SC-16S'
- EasyEDA measured: pads 0.60 x 1.00; centre span 1.10
- Automatic checks: pads = pin map; symbol names agree 0/2
- Symbol name differences (informational, schematic uses datasheet names): 1: EasyEDA 'OSC1' vs DS '#1'; 2: EasyEDA 'OSC2' vs DS '#2'
- Verdict: **PASS-NOTE** - Lands 0.60 x 1.00 at centres 1.10 (gap 0.50): 0.05 mm wider per side than Seiko's. Non-polar.

### C434843 VLS201610CX-100M-1 - L2 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C434843_IND-SMD_L2.0-W1.6` (package `IND-SMD_L2.0-W1.6`, corner token `-`), 2 pads; 3D `IND-SMD_L2.0-W1.6-H1.1`
- Datasheet land/package: TDK VLS201610CX-1 p.3 (same family)
- EasyEDA measured: 
- Verdict: **PASS-NOTE** - Same EasyEDA drawing as C2050114.

### C4371025 INA236AIYBJR - U4, U5 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C4371025_DSBGA-8_L1.5-W0.7-R2-C4-P0.40-BL` (package `DSBGA-8_L1.5-W0.7-R2-C4-P0.40-BL`, corner token `BL`), 8 pads; 3D `DSBGA-8_L1.5-W0.7-R2-C4-P0.40-BL`
- Datasheet: SBOSA81D (Aug 2023), pin table Figure 5-1 (YBJ top view) and Table 5-1 Pin Functions, p.3; pin 1: Bump A1 (ALERT) at the marked corner; Figure 5-1 top view: column 1 = ALERT, A0, SDA, SCL (rows A-D), column 2 = IN+, IN-, GND, VS
- Datasheet land/package: TI SBOSA81D Figure 5-1 (YBJ top view) and Table 5-1, p.3; body 0.745 x 1.508 mm (p.1). The YBJ0008 land-pattern drawing is NOT in the cached datasheet PDF (only the DDF package pages are); TI YBJ0006 drawing 4226653/A of the same family (cache/v2/ds_review/ti_mxbg457.pdf, read by the review): land 0.20 mm NSMD, ball 0.16-0.20 mm
- EasyEDA measured: pads 0.15 x 0.15; centre span 1.20
- Automatic checks: pads = pin map; symbol names agree 8/8; pin A1 at bottom-left; ball map = TI Figure 5-1 top view rotated 90 deg CCW (not mirrored)
- Verdict: **PASS-NOTE** - Ball map verified: EasyEDA = TI top view rotated 90 deg counter-clockwise, not mirrored (A1 ALERT / A2 IN+ on one short end, D1 SCL / D2 VS on the other); EasyEDA symbol names = Table 5-1 for all 8 balls; pitch 0.40. EasyEDA draws the lands 0.149 mm round, below JLC's 0.20 mm minimum BGA pad. REVIEW R-12, FIXED in the reviewed copy lib/easyeda_rev.pretty: every land 0.20 mm (TI's value for the YBJ family), centres and numbers unchanged. Not verified against the YBJ0008 drawing itself (not found): confirm before layout.

### C471381 LQW15AN4N3B80D - L204 - **PASS**

- EasyEDA footprint `easyeda:C471381_IND-SMD_L1.0-W0.6` (package `IND-SMD_L1.0-W0.6`, corner token `-`), 2 pads; 3D `None`
- Datasheet land/package: Murata LQW15AN_80 reference spec JELF243A_0100H-01 section 12.1 (same series as C6652901): a 0.6, b 1.42, c 0.66
- EasyEDA measured: pads 0.50 x 0.65; centre span 0.86
- Verdict: **PASS** - [F] L204 4.3 nH LQW15AN4N3B80D (RF_FINAL re-tune). Same Murata land as C668465 (0.41 x 0.66 at +-0.505), checked pad by pad below (MAKER LAND). Non-polar.

### C478155 PMZ290UNE2YL - Q1, Q4, Q5, Q6, Q7, Q8, Q9, Q10, Q11, Q12, Q13, Q16, Q17, Q19 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C478155_DFN1006-3L_L1.0-W0.6-LS1.0-BR` (package `DFN1006-3L_L1.0-W0.6-LS1.0-BR`, corner token `BR`), 3 pads; 3D `DFN1006-3L_L1.0-W0.6-H0.4-LS1.0-BR`
- Datasheet: PMZ290UNE2 product data sheet (24 March 2015), pin table Table 2 Pinning information, p.2; pin 1: Pins 1 (G) and 2 (S) are the two small lands on one side, pin 3 (D) is the large land on the other (transparent top view, p.2)
- Datasheet land/package: Nexperia PMZ290UNE2 Fig. 19 reflow footprint SOT883 (p.12): lands 0.30 x 0.25 (2x) and 0.30 x 0.60, land pitch 0.70, occupied 1.3 x 0.9; pinning Table 2 p.2 (transparent top view: 1, 2 left, 3 right)
- EasyEDA measured: pads 0.25 x 0.45 / 0.45 x 0.70; centre span 0.70
- Automatic checks: pads = pin map; symbol names agree 3/3; pin 1 at bottom-right
- Verdict: **PASS-NOTE** - EasyEDA = Nexperia top view rotated 180 deg, not mirrored (pin 1 G and pin 2 S keep their order). Pitch 0.70 exact; lands 0.45 x 0.25 (2x) and 0.45 x 0.70: 0.075 mm longer per end and 0.05 mm wider on the drain land than Nexperia's. Three asymmetric lands: geometry decides the rotation.

### C478207 PMZ350UPEYL - Q14, Q18 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C478207_X1-DFN1006-3_L1.0-W0.6-P0.35-BR` (package `X1-DFN1006-3_L1.0-W0.6-P0.35-BR`, corner token `BR`), 3 pads; 3D `None`
- Datasheet: PMZ350UPE product data sheet (14 May 2014), pin table Table 2 Pinning information, p.2; pin 1: Pins 1 (G) and 2 (S) are the two small lands on one side, pin 3 (D) the large land on the other (as PMZ290UNE2)
- Datasheet land/package: Nexperia PMZ350UPE p.2 pinning, SOT883 (as PMZ290UNE2)
- EasyEDA measured: pads 0.25 x 0.40 / 0.40 x 0.70; centre span 0.70
- Automatic checks: pads = pin map; symbol names agree 3/3; pin 1 at bottom-right
- Verdict: **PASS-NOTE** - Same land and numbering as C478155 (PMZ290UNE2YL, v2): pads 0.40 x 0.25 at (+0.35, +-0.23), 0.40 x 0.70 at (-0.35, 0); 1 G, 2 S, 3 D. Three unequal lands (1F).

### C48260 TPD1E10B06DPYR - D5, D6, D7, D8, D15, D18 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C48260_X1SON-2_L1.0-W0.6-P0.65-BI-1` (package `X1SON-2_L1.0-W0.6-P0.65-BI-1`, corner token `-`), 2 pads; 3D `X1SON-2_L1.0-W0.6-P0.65-BI-1`
- Datasheet: SLLSEB1G (Aug 2024), pin table Table 4-1 Pin Functions, p.3; pin 1: Bidirectional and electrically symmetric; package 'ID area' marks pin 1
- Datasheet land/package: TI DPY0002A land example p.20: pad 0.30 x 0.50, centres 0.70
- EasyEDA measured: pads 0.60 x 0.60; centre span 1.00
- Automatic checks: pads = pin map; symbol names agree 2/2
- Verdict: **PASS-NOTE** - Bidirectional, electrically symmetric. EasyEDA lands 0.60 x 0.60 at centres 1.00 are about twice the TI area (gap 0.40 as TI); higher skew/tombstone risk on a 1.0 x 0.6 mm part - watch at the first article inspection.

### C504101 CJBA7002K - Q20 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C504101_DFN1006-3L_L1.0-W0.6-BL` (package `DFN1006-3L_L1.0-W0.6-BL`, corner token `BL`), 3 pads; 3D `None`
- Datasheet: CJBA7002K DFN1006-3L Plastic-Encapsulate MOSFETs, Rev. 1.0, pin table p.1 top view internal schematic (D large land; S, G small lands); pin 1: EasyEDA C504101: pad 1 S (-0.35, +0.23), pad 3 G (-0.35, -0.23), pad 2 D (+0.35, 0); turned 180 deg this is the C478155 land with G and S on the same pads (G at +y)
- Datasheet land/package: JSCJ CJBA7002K Rev 1.0 p.1 top view (D large; S, G small), p.4 X1-DFN1006-3 outline: D 1.00, E 0.60, b1 0.10-0.20, b2 0.45-0.55, L1 = L2 0.20-0.30, L3 0.40, e 0.35
- EasyEDA measured: pads 0.25 x 0.45 / 0.45 x 0.70; centre span 0.70
- Automatic checks: pads = pin map; symbol names agree 3/3; pin 1 at bottom-left
- Verdict: **PASS-NOTE** - [S2c F-8] Q20. EasyEDA lands 0.45 x 0.25 (2x) at (-0.35, +-0.23) and 0.45 x 0.70 at (+0.35, 0) = the C478155 (PMZ290UNE2) land turned 180 deg, pad for pad (same G / S positions after the turn). Terminals (|x| 0.25-0.50, small |y| 0.10-0.25) lie inside the lands. JLC 0 deg of C504101 = C478155 + 180 deg.

### C506250 BQ25570RGRR - U1 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C506250_VQFN-20_L3.5-W3.5-P0.50-BL-EP2.0` (package `VQFN-20_L3.5-W3.5-P0.50-BL-EP2.0`, corner token `BL`), 21 pads; 3D `VQFN-20_L3.5-W3.5-P0.50-BL-EP2.0`
- Datasheet: SLUSBH2G (Mar 2019), pin table Pin Functions, p.4; pin 1: Pin 1 at the corner shared with pin 20; top-side pin-1 dot per RGR0020A; numbering counter-clockwise (top view)
- Datasheet land/package: TI RGR0020A land example p.44: pad 0.24 x 0.60, pitch 0.50, pad-row centres 3.30, EP 2.05 x 2.05
- EasyEDA measured: pads 0.28 x 0.80; centre span 3.50, EP 2.05 x 2.05 (#21)
- Automatic checks: pads = pin map; symbol names agree 21/21; pin 1 at bottom-left; numbering CCW (not mirrored)
- Verdict: **PASS-NOTE** - Pitch, EP 2.05 and pad inner edge (1.35) identical; EasyEDA pads 0.28 x 0.80 reach 0.2 mm further out (row centres 3.50). Pin 1 at the pin-1/pin-20 corner, CCW (drawn rotated 90 deg vs the TI view - JLC's own 0 deg).

### C509405 NRF52832-CIAA-R - U6 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C509405_WLCSP-50_L3.2-W3.0-TL_NRF52832` (package `WLCSP-50_L3.2-W3.0-TL_NRF52832`, corner token `-`), 50 pads; 3D `WLCSP-50_L3.2-W3.0-H0.4-TL_NRF52832`
- Datasheet: nRF52832 Product Specification v1.4 (2017-10-10), pin table Section 4.2 WLCSP ball assignments, Figure 3 (top view) and Table 4, p.15-17; Table 6 GPIO near the radio, p.17; pin 1: Ball A1 at the top-left corner of the top view, marked by the top-side dot; columns 1-7 left to right, rows A-H downward (Figure 3, rendered in cache/v2/ds/png/nrf52832_ps_fig3_wlcsp_balls.png)
- Datasheet land/package: Nordic PS v1.4 Figure 3 (top view, p.15), Table 4, Table 132 / Figure 164 (p.541): 50 balls on an 8 x 7 grid, pitch 0.40, ball b = 0.20 nominal, positions B1, C1, D4, D5, E4, E5 empty; no land pattern in the PS (Nordic reference layout not cached)
- EasyEDA measured: pads 0.17 x 0.17; centre span 2.80
- Automatic checks: pads = pin map; symbol names agree 50/50; pin A1 at top-left; A1 top-left, cols 1-7 left->right, rows A-H downward, B1/C1/D4/D5/E4/E5 empty (PS Figure 3 top view, not mirrored)
- Verdict: **PASS-NOTE** - Ball names, positions and the six empty positions are identical to Figure 3: A1 top-left, columns 1-7 left to right, rows A-H downward (top view, not mirrored; render cache/v2/ds/png/nrf52832_ps_fig3_wlcsp_balls.png); pitch 0.40 x 0.40 exact; EasyEDA symbol names = Table 4 for all 50 balls. EasyEDA draws the lands 0.17 mm round, below JLC's minimum BGA pad of 0.20 mm (capability page re-read by the review 2026-11-12: 'BGA 0.2 mm; 0.2-0.25 mm BGA pad diameter requires ENIG'). REVIEW R-12, FIXED in the reviewed copy lib/easyeda_rev.pretty: every land 0.20 mm (= the nominal ball), centres and numbers unchanged, gap 0.20 mm; the board needs ENIG. Not compared with Nordic's CIAA reference layout (not cached): confirm before layout.

### C511402 VEMD8080 - PD1 - **PASS**

- EasyEDA footprint `easyeda:C511402_SENSOR-SMD_8P-L4.8-W2.5-P1.31` (package `SENSOR-SMD_8P-L4.8-W2.5-P1.31`, corner token `-`), 8 pads; 3D `SENSOR-SMD_8P-L4.8-W2.5-P1.31`
- Datasheet: VEMD8080 Rev 1.1 (05-Sep-2023), doc 84565, pin table Package dimensions / pinning (top and bottom view), p.4; pin 1: Pin 1 marking dot at the pin-1 corner of the top view; pin 5 (anode) is the diagonally opposite corner
- Datasheet land/package: Vishay VEMD8080 p.4: 8 pads 0.54 x 0.55, x pitch 1.31/1.38/1.31, rows 2.38; pin 1 dot, pin 5 = anode
- EasyEDA measured: pads 0.55 x 0.55; centre span 4.00
- Automatic checks: pads = pin map; symbol names agree 1/8; pin 1 at top-right; pin 1 and pin 5 at opposite corners, rows 1-4 / 5-8 antiparallel (datasheet order, 180 deg)
- Symbol name differences (informational, schematic uses datasheet names): 1: EasyEDA 'C' vs DS 'cathode'; 2: EasyEDA 'C' vs DS 'cathode'; 3: EasyEDA 'C' vs DS 'cathode'; 4: EasyEDA 'C' vs DS 'cathode'; 6: EasyEDA 'C' vs DS 'cathode'; 7: EasyEDA 'C' vs DS 'cathode'; 8: EasyEDA 'C' vs DS 'cathode'
- Verdict: **PASS** - Pads 0.55 x 0.55 on exactly the datasheet grid. EasyEDA numbering = datasheet top view rotated 180 deg (pin 1 top-right, pin 5 bottom-left), not mirrored; symbol pin 5 = 'A', others 'C'. Polarized: human review required.

### C5187176 TXU0104RUTR - U17 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C5187176_XQFN-12_L2.0-W1.7-P0.40-BL` (package `XQFN-12_L2.0-W1.7-P0.40-BL`, corner token `BL`), 12 pads; 3D `None`
- Datasheet: SCES937B (May 2021, revised February 2025), pin table Figure 4-3 RUT 12-pin UQFN transparent top view and Table 4-1, p.4; pin 1: UQFN-12: optional pin-1 ID (p.36); land symmetric on both axes (V3_ARCH 10, SCES937B p.37): a 180 deg turn fits the copper
- Datasheet land/package: TI SCES937B p.37 RUT0012A land example: 12 x 0.7 x 0.2 mm, pitch 0.4, column centres (1.4), pins 6 / 12 vertical with centres (1.7) apart; top view pins 1-5 down the left column
- EasyEDA measured: pads 0.20 x 0.69; centre span 1.60
- Automatic checks: pads = pin map; symbol names agree 12/12; pin 1 at bottom-left; numbering CCW (not mirrored)
- Verdict: **PASS-NOTE** - EasyEDA = TI's land rotated 90 deg CCW (pins 1-5 along the bottom, 7-11 along the top, 6 right, 12 left; not mirrored): pads 0.69 x 0.20, pitch 0.40, row centres 1.40 = TI; pins 6 / 12 at x +-0.80 (TI +-0.85): 0.05 mm further in, inside the terminal length. Land symmetric on both axes: a 180 deg turn fits (2F, preview + G10 (g)).

### C5208201 BQ25170DSGR - U15 - **PASS**

- EasyEDA footprint `easyeda:C5208201_WSON-8_L2.0-W2.0-P0.50-TL-EP` (package `WSON-8_L2.0-W2.0-P0.50-TL-EP`, corner token `TL`), 9 pads; 3D `None`
- Datasheet: SLUSDJ8A (April 2020, revised April 2021), pin table Figure 5-1 WSON-8 top view and Table 5-1 Pin Functions, p.3; pin 1: WSON-8: pins 1-4 down the left side (pin 1 at the pin-1 index corner), 5-8 up the right side, exposed pad 9 = GND; marking B170 (p.28); tape pin-1 quadrant Q2 (p.29)
- Datasheet land/package: TI SLUSDJ8A p.33 DSG0008A land example: 8 x 0.25 x 0.50 mm, pitch 0.50, pad-row centres (1.9), EP 0.9 x 1.6 (vias 0.2 optional)
- EasyEDA measured: pads 0.25 x 0.52; centre span 1.90, EP 0.90 x 1.60 (#9)
- Automatic checks: pads = pin map; symbol names agree 9/9; pin 1 at top-left; numbering CCW (not mirrored)
- Verdict: **PASS** - EasyEDA pads 0.52 x 0.25 at x +-0.95 (row centres 1.90), pitch 0.50, EP 0.90 x 1.60: TI's land within 0.02 mm. Pin 1 top-left, 1-4 down the left, 5-8 up the right (CCW, not mirrored). EP paste of the reviewed copy: one window at 87 % (TI stencil p.34). The land fits turned 180 deg (2F): preview + G10 (e).

### C5217869 TXU0101DRYR - U21 - **PASS**

- EasyEDA footprint `easyeda:C5217869_SON-6_L1.5-W1.0-P0.50-TL` (package `SON-6_L1.5-W1.0-P0.50-TL`, corner token `TL`), 6 pads; 3D `None`
- Datasheet: SCES940A (February 2022, revised May 2024), pin table Figure 4-4 DRY 6-pin SON transparent top view and Table 4-1, p.3; pin 1: USON-6: pins 1-3 on one side (1 at the pin-1 corner), 4-6 on the other; the land is symmetric except the slightly longer pin-1 pad of the EasyEDA footprint
- Datasheet land/package: TI SCES940A p.36 DRY0006A land example: 6 pads 0.3 x 0.2 at pitch 0.5, column centres (0.6); pad 1 longer (0.35) toward the centre
- EasyEDA measured: pads 0.20 x 0.30 / 0.20 x 0.35; centre span 1.00
- Automatic checks: pads = pin map; symbol names agree 6/6; pin 1 at top-left; numbering CCW (not mirrored)
- Verdict: **PASS** - EasyEDA: pad 1 0.35 x 0.20 at x -0.28, pads 2-6 0.30 x 0.20 at x +-0.30, rows -0.5 / 0 / +0.5: TI's land including the longer pin-1 pad. 1-3 down the left, 4-6 up the right (CCW). The 0.05 mm longer pad 1 does not prevent a 180 deg fit (2F).

### C5220164 TPS7A2030PDQNR - U3 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C5220164_X2SON-4_L1.0-W1.0-P0.65-TL-EP` (package `X2SON-4_L1.0-W1.0-P0.65-TL-EP`, corner token `TL`), 5 pads; 3D `X2SON-4_L1.0-W1.0-H0.4-P0.65-TL-EPSLDPRT`
- Datasheet: SBVS338H (Jul 2024), pin table Pin Functions: X2SON, SOT-23, p.4 (Figure 4-3 DQN top view); pin 1: Pin 1 (OUT) index area / optional pin-1 ID on the top (DQN0004A note 4: use the top pin-1 marking for orientation); pins 1-2 on one side, 3-4 on the other
- Datasheet land/package: TI DQN0004A p.60-61: X2SON-4 1.0 x 1.0, pitch 0.65 (2X), leads 0.28 x 0.30, thermal pad 0.48 (diamond), pin-1 index top
- EasyEDA measured: pads 0.01 x 0.01 / 0.48 x 0.48; centre span 0.86
- Automatic checks: pads = pin map; symbol names agree 5/5; pin 1 at top-left; numbering CCW (not mirrored)
- Verdict: **PASS-NOTE** - Pin 1 (OUT) top-left, 2 GND bottom-left, 3 EN bottom-right, 4 IN top-right = CCW top view as Fig. 4-3; leads drawn as custom polygons (0.36 x 0.22 each), EP 0.48 square at 45 deg as TI. EasyEDA symbol names OUT/GND/EN/IN/EP = datasheet. 4 equal leads on a 1 x 1 body: the copper set is near-symmetric, so pin-1 needs a human check in the JLC preview (pin map human_review).

### C5328762 MAX86141ENP+T - U8 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C5328762_BGA-20_L2.0-W1.8-R4-C5-P0.40-TL` (package `BGA-20_L2.0-W1.8-R4-C5-P0.40-TL`, corner token `TL`), 20 pads; 3D `BGA-20_L2.0-W1.8-R4-C5-P0.40-TL`
- Datasheet: MAX86140/MAX86141 data sheet rev 4, pin table Pin Configurations p.11, Pin Description p.12; pin 1: Bump A1 (VLED) top-left in the top view (bump side down); A1 marking on top per 21-100134
- Datasheet land/package: ADI 21-100134: 20 bumps 4 x 5, pitch 0.40, bump 0.27, body 2.048 x 1.848; land pattern per ADI AN1891 (not cached); ARCHITECTURE 5.3 intent 0.25 NSMD
- EasyEDA measured: pads 0.20 x 0.20; centre span 1.60
- Automatic checks: pads = pin map; symbol names agree 20/20; pin A1 at top-left; A1 top-left, cols 1-5 left->right, rows A-D downward (top view, not mirrored)
- Verdict: **PASS-NOTE** - A1 top-left, rows A-D downward, columns 1-5 rightward = datasheet top view (not mirrored). Round lands 0.20 mm (vs the 0.25 mm NSMD intent in ARCHITECTURE 5.3): inside JLC's >= 0.20 BGA pad rule; confirm against AN1891 before layout.

### C549275 BAT54CM,315 - D17, D19 - **FLAG**

- EasyEDA footprint `easyeda:C549275_DFN1006-3_L1.0-W0.6-P0.35-BR_BAT54CM` (package `DFN1006-3_L1.0-W0.6-P0.35-BR_BAT54CM`, corner token `-`), 3 pads; 3D `None`
- Datasheet: BAT54CM product data sheet (2003 Nov 11, NXP/Nexperia), pin table Pinning table and Fig. 1, p.3 (document page 2); pin 1: SOT883: pins 1 (a1) and 2 (a2) on the small lands, pin 3 (common cathode) on the large land; cathode mark on top (Fig. 1)
- Datasheet land/package: Nexperia SOT883 reflow footprint sot883_fr (BAV70M p.8, same package): solder lands 0.4 wide, small-land centres 0.45 apart, land rows 0.7 apart; package terminals b 0.22-0.30 (pins 1, 2), b1 0.55-0.62 (pin 3) (BAT54CM p.6)
- EasyEDA measured: pads 0.16 x 0.40 / 0.40 x 0.60; centre span 0.64
- Automatic checks: pads = pin map; symbol names agree 0/3; pin 1 at bottom-right
- Symbol name differences (informational, schematic uses datasheet names): 1: EasyEDA 'A' vs DS 'A1'; 2: EasyEDA 'A' vs DS 'A2'; 3: EasyEDA 'K' vs DS 'CC'
- Verdict: **FLAG** - EasyEDA draws the small lands 0.40 x 0.16 mm, narrower than the 0.22-0.30 mm terminals. FIXED in the reviewed copy (lib/easyeda_rev.pretty): the pad set of C478155 (PMZ290UNE2YL, Nexperia SOT883, v2-reviewed: 0.45 x 0.25 / 0.45 x 0.70 mm at x +-0.35, y +-0.23) with the same numbers, orientation (pad 3 at -x) and origin, so JLC's centroid and 0 deg are those of the C549275 record. Three unequal lands: a turn does not fit (1F, placement_proof).

### C549313 None - D12 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C549313_PROXY-C549275_DFN1006-3_L1.0-W0.6-P0.35-BR_BAT54CM` (package `PROXY of C549275 (no EasyEDA record)`, corner token `-`), 3 pads; 3D `None`
- Datasheet: BAV70M product data sheet (1 July 2022), pin table Table 2 Pinning information, p.2; pin 1: SOT883: pins 1 (A1) and 2 (A2) are the two small lands on one side, pin 3 (common cathode) the large land on the other (transparent top view, p.2)
- Datasheet land/package: Nexperia BAV70M p.7-8: SOT883 outline and sot883_fr footprint (as C549275)
- EasyEDA measured: pads 0.16 x 0.40 / 0.40 x 0.60; centre span 0.64
- Automatic checks: pads = pin map; symbol names agree 0/3; pin 1 at bottom-right
- Symbol name differences (informational, schematic uses datasheet names): 1: EasyEDA 'None' vs DS 'A1'; 2: EasyEDA 'None' vs DS 'A2'; 3: EasyEDA 'None' vs DS 'CC'
- Verdict: **PASS-NOTE** - No EasyEDA footprint exists for C549313 (API 404, 2026-11-13 20:41 UTC). The board uses the reviewed C549275 land (same Nexperia SOT883, pins 1 / 2 small lands, 3 large land, BAV70M p.2). Geometry proves the orientation (1F), but JLC's library 0 deg for C549313 cannot be compared with an EasyEDA record: the JLC preview of the cathode (large) land is mandatory, plus G10 (f).

### C5603826 CT DBLP31.12 - D3, D4 - **PASS**

- EasyEDA footprint `easyeda:C5603826_LED-SMD_3P-L2.2-W1.8_C5D-56-J6U6-20-R18` (package `LED-SMD_3P-L2.2-W1.8_C5D-56-J6U6-20-R18`, corner token `-`), 3 pads; 3D `LED-SMD_3P-L2.2-W1.8_C5D-56-J6U6-20-R18`
- Datasheet: CT DBLP31.12 datasheet Version 1.3 (2021-03-29), pin table Dimensional drawing (anode / cathode leaders), p.11; electrical internal circuit and recommended solder pad, p.12; pin 1: Anode = one of the two small lands; cathode = the other small land and the large land (p.11 pad view). In the top view of the board the anode is the small land on the LEFT when the small lands are at the top
- Datasheet land/package: ams-OSRAM CT DBLP31.12 v1.3 p.12 recommended solder pad E062.3010.218-01: lands 0.55 x 0.35 (2x, 0.34 apart) and 1.45 x 1.25, 0.25 between; p.11 pad view with anode / cathode
- EasyEDA measured: pads 0.35 x 0.55 / 1.25 x 1.45; centre span 1.05
- Automatic checks: pads = pin map; symbol names agree 0/3; pin 1 at top-left
- Symbol name differences (informational, schematic uses datasheet names): 1: EasyEDA 'None' vs DS 'A'; 2: EasyEDA 'None' vs DS 'C'; 3: EasyEDA 'None' vs DS 'C'
- Verdict: **PASS** - Exact match: lands 0.55 x 0.35 at (-0.44 / +0.45, -0.52) and 1.45 x 1.25 at (0, +0.53). Not its own 180 deg image. EasyEDA symbol: pad 1 '+', pad 2 '-', pad 3 unnamed; datasheet p.11 (pad view): anode = one small land, cathode = the other small land + the large land. Which small land is the anode rests on reading p.11 as a bottom view: human review, and the G10 LED/PD loop-back on every board.

### C5687033 MX25R1635FZUIH0 - U11 - **PASS**

- EasyEDA footprint `easyeda:C5687033_USON-8_L3.0-W2.0-P0.50-BL-EP1.6_MX25R1635FZUIH0` (package `USON-8_L3.0-W2.0-P0.50-BL-EP1.6_MX25R1635FZUIH0`, corner token `BL`), 9 pads; 3D `USON-8_L3.0-W2.0-P0.50-BL-EP1.6_MX25R1635FZUIH0`
- Datasheet: MX25R1635F Rev 1.6 (Dec 2018), pin table 3. Pin configurations / 4. Pin description, p.8; pin 1: Pin 1 corner marked on the top view (lower-left); pins counter-clockwise
- Datasheet land/package: Macronix p.81 USON-8 2x3x0.6: e 0.50, b 0.25, L 0.45, E 3.00, exposed strip D1 1.60 x E1 0.20
- EasyEDA measured: pads 0.30 x 0.50; centre span 2.50, EP 1.60 x 0.20 (#9)
- Automatic checks: pads = pin map; symbol names agree 8/9; pin 1 at bottom-left; numbering CCW (not mirrored)
- Symbol name differences (informational, schematic uses datasheet names): 9: EasyEDA '9' vs DS 'EP'
- Verdict: **PASS** - Pads 0.30 x 0.50 cover the 0.25 x 0.45 terminals; pad 9 = the 1.60 x 0.20 exposed strip (tied to GND per the package note). Pin 1 lower-left in the top view, CCW.

### C598214 KA-2810ASURSK - D10 - **PASS**

- EasyEDA footprint `easyeda:C598214_LED-SMD_L2.5-W1.2_KA-2810AVBS-D` (package `LED-SMD_L2.5-W1.2_KA-2810AVBS-D`, corner token `-`), 2 pads; 3D `LED-SMD_L2.5-W1.2_KA-2810AVBS-D`
- Datasheet: KA-2810ASURSK data sheet, Spec No DSAK2457, Rev V.7A (2019-05-07), pin table Package dimensions with the polarity symbol (1 = cathode side of the diode symbol, 2 = anode), p.1; pin 1: Terminal 1 = cathode: the diode symbol on p.1 has its bar at terminal 1; front view (looking into the lens) has terminal 1 on the left
- Datasheet land/package: Kingbright KA-2810ASURSK p.1 recommended soldering pattern: lands 1.4 x 0.9 mm (2x), gap 1.0 mm, 0.5 mm of land beyond the body at each end; body 2.8 x 1.2 x 0.8 mm; polarity symbol: terminal 1 = cathode
- EasyEDA measured: pads 0.90 x 1.40; centre span 2.40
- Automatic checks: pads = pin map; symbol names agree 2/2
- Verdict: **PASS** - Exact match: lands 1.40 x 0.90 at +-1.20 (gap 1.00) = Kingbright's pattern. EasyEDA symbol 1 = K, 2 = A = datasheet. Right-angle part with two equal lands: a 180 deg turn fits the copper, swaps the polarity AND turns the light away from the window; which side carries the lens in the EasyEDA 0 deg drawing (courtyard -0.82 ... +0.38 in y, lens outline on the -y side) was not proven against the tape drawing here -> human check in the JLC preview (lens toward the board edge) and the G10 item 'ALERT_LED on: current rises, red light at the board edge' on every board.

### C6736531 PMEG10020AELR-QX - D14 - **PASS**

- EasyEDA footprint `easyeda:C6736531_SOD-123F_L2.8-W1.8-LS3.7-RD` (package `SOD-123F_L2.8-W1.8-LS3.7-RD`, corner token `-`), 2 pads; 3D `None`
- Datasheet: PMEG10020AELR product data sheet (1 January 2023), pin table Table 2 pinning information, p.2 (1 K cathode, 2 A anode; the marking bar indicates the cathode); pin 1: pin 1 = cathode at the marking bar (Table 2, Fig. 16)
- Datasheet land/package: Nexperia PMEG10020AELR (1 January 2023) Fig. 17 p.10 reflow footprint SOD123W: solder lands 1.2 x 1.2 at centres 2.8 (gap 1.6, outer 4.0), paste 1.1, resist 1.4, occupied 4.4 x 2.1; Fig. 16 p.9: leads 0.75-1.05 wide, 0.3-0.6 long, 3.3-3.7 overall, body 1.5-1.9 wide, 0.9-1.1 high; Table 2 p.2: pin 1 = cathode (marking bar)
- EasyEDA measured: pads 1.00 x 1.20; centre span 3.30
- Automatic checks: pads = pin map; symbol names agree 0/2
- Symbol name differences (informational, schematic uses datasheet names): 1: EasyEDA '1' vs DS 'K'; 2: EasyEDA '2' vs DS 'A'
- Verdict: **PASS** - [S2b E-4] EasyEDA C6736531 (SOD-123F_L2.8-W1.8-LS3.7) draws pads 1.00 x 1.20 at x +-1.65 (gap 2.30, outer 4.30): its inner edge 1.15 sits outside the shortest lead's inner end (1.05), so the land was replaced by Nexperia's (2 pads 1.2 x 1.2 at +-1.40) and checked pad by pad below (MAKER LAND). Pad 1 = cathode at -x, as EasyEDA's silk bar. 2-pad polar part (class P): JLC preview of the cathode bar + G10 (e).

### C718072 X201632MKB4SI - X1 - **PASS**

- EasyEDA footprint `easyeda:C718072_CRYSTAL-SMD_4P-L2.0-W1.6-BL` (package `CRYSTAL-SMD_4P-L2.0-W1.6-BL`, corner token `BL`), 4 pads; 3D `CRYSTAL-SMD_4P-L2.0-W1.6-BL`
- Datasheet: YXC YSX211SL series sheet, pin table Top view crystal connection, p.1; pin 1: No top-side pin-1 mark on the lid; the chamfered terminal is #4 (GND) in the bottom view; #1 is lower-left in the top view (EasyEDA silk L-mark at pad 1). #1/#3 crystal, #2/#4 GND: the land is 2F (180 deg electrically identical)
- Datasheet land/package: YXC YSX211SL p.1 recommended land: 0.90 x 0.80, gaps 0.50 (x) / 0.30 (y); #1 lower-left, #2/#4 GND
- EasyEDA measured: pads 0.80 x 0.90; centre span 1.40
- Automatic checks: pads = pin map; symbol names agree 4/4; pin 1 at bottom-left
- Verdict: **PASS** - Exact match (pads 0.90 x 0.80 at +-0.70/+-0.55), #1 lower-left, #3 upper-right, #2/#4 GND.

### C727398 SIP32431DNP3-T1GE4 - U12, U13 - **PASS**

- EasyEDA footprint `easyeda:C727398_TDFN-4_L1.2-W1.6-P0.50-BL-EP` (package `TDFN-4_L1.2-W1.6-P0.50-BL-EP`, corner token `BL`), 5 pads; 3D `TDFN-4_L1.2-W1.6-H0.6-P0.50-BL-EP`
- Datasheet: Document 66597 Rev. G (06-Jul-2020), pin table Fig. 3 TDFN4 1.2 mm x 1.6 mm package (bottom view) and Pin Description table, p.3; pin 1: TDFN4 (Fig. 3 is a BOTTOM view, rendered in cache/v2/ds/png/sip32431_fig3_tdfn4.png): pin 1 = OUT at the dot corner, 2 = GND on the same side; 3 = IN opposite pin 2, 4 = ON/OFF opposite pin 1; centre pad GND
- Datasheet land/package: Vishay 'Recommended minimum pads for TDFN4 1.2 x 1.6' (doc 66558, p.14 of the cached sip32431.pdf): lands 0.30 x 0.55, pitch 0.50, centre pad 0.86 x 0.50, gaps 0.20, overall 2.0; pin configuration Fig. 3 p.3 (bottom view)
- EasyEDA measured: pads 0.30 x 0.55 / 0.50 x 0.86; centre span 1.46
- Automatic checks: pads = pin map; symbol names agree 5/5; pin 1 at bottom-left; numbering CCW (not mirrored)
- Verdict: **PASS** - Exact match: lands 0.30 x 0.55 at +-0.25 / +-0.73, centre pad 0.86 x 0.50; pad numbers as Vishay's pattern (1, 2 on one side; 4, 3 on the other; 4 opposite 1). EasyEDA symbol 1 OUT, 2 GND, 3 IN, 4 ON/OFF, 5 GND = datasheet table. 2 x 2 lands: a 180 deg turn fits the copper -> identity by pin map + G10.

### C896422 NSR0240MX2T5G - D16 - **PASS-NOTE**

- EasyEDA footprint `easyeda:C896422_X2DFN-2_L1.0-W0.6-RD` (package `X2DFN-2_L1.0-W0.6-RD`, corner token `-`), 2 pads; 3D `None`
- Datasheet: NSR0240MX2/D Rev. 3 (March 2022), pin table Pin assignment p.1 (1 CATHODE, 2 ANODE) and case 714AB, p.4; pin 1: pin 1 = cathode at the pin-1 indicator (case 714AB, p.4)
- Datasheet land/package: onsemi NSR0240MX2 p.4 case 714AB recommended footprint: 2 pads 0.47 x 0.60, outer span 1.20 (centres +-0.365); terminals e 0.65, L 0.20-0.30, b 0.45-0.55
- EasyEDA measured: pads 0.30 x 0.55; centre span 0.66
- Automatic checks: pads = pin map; symbol names agree 2/2
- Verdict: **PASS-NOTE** - EasyEDA pads 0.30 x 0.55 at x +-0.33: smaller than onsemi's (0.47 x 0.60) but covering the terminal (|x| 0.20-0.45). Pad 1 = cathode at +x. 2-pad polar part: 180 deg fits (class P): preview of the cathode mark + G10 (e) (a reversed D14 blocks the head: no /PG, no current).

### C105226 CL05A226MQ5QUNC - C105, C114, C115, C116, C117, C118(DNP) - **PASS**

- EasyEDA footprint `easyeda:C105226_C0402` (package `C0402`, corner token `-`), 2 pads; 3D `C0402_L1.0-W0.5-H0.5`
- EasyEDA measured: pads 0.50 x 0.54; centre span 0.84
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C1518204 GRM1555C1H472JE01D - C305, C306 - **PASS**

- EasyEDA footprint `easyeda:C1518204_C0402` (package `C0402`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.50 x 0.54; centre span 0.84
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C1546 0402CG101J500NT - C213(DNP) - **PASS**

- EasyEDA footprint `easyeda:C1546_C0402` (package `C0402`, corner token `-`), 2 pads; 3D `C0402_L1.0-W0.5-H0.5`
- EasyEDA measured: pads 0.50 x 0.54; centre span 0.84
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C15525 CL05A106MQ5NUNC - C307, C402, C502 - **PASS**

- EasyEDA footprint `easyeda:C15525_C0402` (package `C0402`, corner token `-`), 2 pads; 3D `C0402_L1.0-W0.5-H0.5`
- EasyEDA measured: pads 0.50 x 0.54; centre span 0.84
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C161408 GRM0335C1H151JA01D - C304 - **PASS**

- EasyEDA footprint `easyeda:C161408_C0201` (package `C0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.32 x 0.37; centre span 0.54
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C161418 GRM0335C1H221JA01D - C175 - **PASS**

- EasyEDA footprint `easyeda:C161418_C0201` (package `C0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.32 x 0.37; centre span 0.54
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C166160 RTT015362FTH - R172 - **PASS**

- EasyEDA footprint `easyeda:C166160_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C19666 CL10A475KO8NNNC - C101 - **PASS**

- EasyEDA footprint `easyeda:C19666_C0603` (package `C0603`, corner token `-`), 2 pads; 3D `C0603_L1.6-W0.8-H0.8`
- EasyEDA measured: pads 0.80 x 0.90; centre span 1.40
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C19702 CL10A106KP8NNNC - C102, C404 - **PASS**

- EasyEDA footprint `easyeda:C19702_C0603` (package `C0603`, corner token `-`), 2 pads; 3D `C0603_L1.6-W0.8-H0.8`
- EasyEDA measured: pads 0.80 x 0.90; centre span 1.40
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C23733 CL05A475MP5NRNC - C121, C209 - **PASS**

- EasyEDA footprint `easyeda:C23733_C0402` (package `C0402`, corner token `-`), 2 pads; 3D `C0402_L1.0-W0.5-H0.5`
- EasyEDA measured: pads 0.50 x 0.54; centre span 0.84
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C237514 GJM0335C1H1R0BB01D - C203 - **PASS**

- EasyEDA footprint `easyeda:C237514_C0201` (package `C0201`, corner token `-`), 2 pads; 3D `C0201_L0.6-W0.3-H0.3`
- EasyEDA measured: pads 0.32 x 0.37; centre span 0.54
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C25076 0402WGF1000TCE - R318, R319 - **PASS**

- EasyEDA footprint `easyeda:C25076_R0402` (package `R0402`, corner token `-`), 2 pads; 3D `R0402_L1.0-W0.5-H0.4`
- EasyEDA measured: pads 0.54 x 0.57; centre span 0.86
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C2691509 0201WMF1623TEE - R171 - **PASS**

- EasyEDA footprint `easyeda:C2691509_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C270345 0201WMF4702TEE - R129 - **PASS**

- EasyEDA footprint `easyeda:C270345_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C270346 0201WMF4701TEE - R127, R505, R506 - **PASS**

- EasyEDA footprint `easyeda:C270346_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `R0201_L0.6-W0.3-H0.3`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C270358 0201WMF2001TEE - R141 - **PASS**

- EasyEDA footprint `easyeda:C270358_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C270364 0201WMF1003TEE - R116, R165, R315, R316, R401, R402, R501, R503, R504, R509 - **PASS**

- EasyEDA footprint `easyeda:C270364_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `R0201_L0.6-W0.3-H0.3`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C270365 0201WMF1001TEE - R162 - **PASS**

- EasyEDA footprint `easyeda:C270365_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C270366 0201WMF1000TEE - R133, R160 - **PASS**

- EasyEDA footprint `easyeda:C270366_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C270612 0402WGF330KTCE - R117 - **PASS**

- EasyEDA footprint `easyeda:C270612_R0402` (package `R0402`, corner token `-`), 2 pads; 3D `R0402_L1.0-W0.5-H0.4`
- EasyEDA measured: pads 0.54 x 0.57; centre span 0.86
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C2766851 0402WGF5764TCE_C2766851 - R101 - **PASS**

- EasyEDA footprint `easyeda:C2766851_R0402` (package `R0402`, corner token `-`), 2 pads; 3D `R0402_L1.0-W0.5-H0.4`
- EasyEDA measured: pads 0.54 x 0.57; centre span 0.86
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C285010 0201B103K250NT - C113, C120 - **PASS**

- EasyEDA footprint `easyeda:C285010_C0201` (package `C0201`, corner token `-`), 2 pads; 3D `C0201_L0.6-W0.3-H0.3`
- EasyEDA measured: pads 0.32 x 0.37; centre span 0.54
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C295786 RC0201FR-071ML - R124, R128, R144, R145, R146, R149, R161, R163, R164, R167, R175, R176, R508, R510 - **PASS**

- EasyEDA footprint `easyeda:C295786_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `R0201_L0.6-W0.3-H0.3`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C309454 CC0201KRX7R8BB472 - C132 - **PASS**

- EasyEDA footprint `easyeda:C309454_C0201` (package `C0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.32 x 0.37; centre span 0.54
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C384960 GRM0335C1H120FA01D - C201, C202 - **PASS**

- EasyEDA footprint `easyeda:C384960_C0201` (package `C0201`, corner token `-`), 2 pads; 3D `C0201_L0.6-W0.3-H0.3`
- EasyEDA measured: pads 0.32 x 0.37; centre span 0.54
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C3855387 GRM1555C1E103JE01D - C104 - **PASS**

- EasyEDA footprint `easyeda:C3855387_C0402` (package `C0402`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.50 x 0.54; centre span 0.84
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C413063 ERJ2RKF1000X - R507 - **PASS**

- EasyEDA footprint `easyeda:C413063_R0402` (package `R0402`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.54 x 0.57; centre span 0.86
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C423135 0402WGF7504TCE - R106 - **PASS**

- EasyEDA footprint `easyeda:C423135_R0402` (package `R0402`, corner token `-`), 2 pads; 3D `R0402_L1.0-W0.5-H0.4`
- EasyEDA measured: pads 0.54 x 0.57; centre span 0.86
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C423137 0402WGF7324TCE - R102 - **PASS**

- EasyEDA footprint `easyeda:C423137_R0402` (package `R0402`, corner token `-`), 2 pads; 3D `R0402_L1.0-W0.5-H0.4`
- EasyEDA measured: pads 0.54 x 0.57; centre span 0.86
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C423177 0402WGF4024TCE - R107 - **PASS**

- EasyEDA footprint `easyeda:C423177_R0402` (package `R0402`, corner token `-`), 2 pads; 3D `R0402_L1.0-W0.5-H0.4`
- EasyEDA measured: pads 0.54 x 0.57; centre span 0.86
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C423179 0402WGF3924TCE - R103 - **PASS**

- EasyEDA footprint `easyeda:C423179_R0402` (package `R0402`, corner token `-`), 2 pads; 3D `R0402_L1.0-W0.5-H0.4`
- EasyEDA measured: pads 0.54 x 0.57; centre span 0.86
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C423439 0201WMF7323TEE - R170 - **PASS**

- EasyEDA footprint `easyeda:C423439_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C423582 0201WMF3304TEE - R126 - **PASS**

- EasyEDA footprint `easyeda:C423582_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C423797 0201WMF1005TEE - R108, R125, R131, R174, R307(DNP), R308(DNP), R309(DNP) - **PASS**

- EasyEDA footprint `easyeda:C423797_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C43676 0402WGF3602TCE - R142 - **PASS**

- EasyEDA footprint `easyeda:C43676_R0402` (package `R0402`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.54 x 0.57; centre span 0.86
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C441935 ERJPA3F3303V - R301, R302, R303, R304, R305, R306 - **PASS**

- EasyEDA footprint `easyeda:C441935_R0603` (package `R0603`, corner token `-`), 2 pads; 3D `R0603`
- EasyEDA measured: pads 0.81 x 0.86; centre span 1.50
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C45993 0402WGF3833TCE - R105 - **PASS**

- EasyEDA footprint `easyeda:C45993_R0402` (package `R0402`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.54 x 0.57; centre span 0.86
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C473048 0201WMF1002TEE - R311, R312, R313, R314, R511 - **PASS**

- EasyEDA footprint `easyeda:C473048_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `R0201_L0.6-W0.3-H0.3`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C473458 0201WMF2203TEE - R123, R143 - **PASS**

- EasyEDA footprint `easyeda:C473458_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C473473 0201WMF0000TEE - FB1, FB2, FB3, FB4, FB5, FB6 - **PASS**

- EasyEDA footprint `easyeda:C473473_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C473560 0201WMF4703TEE - R317 - **PASS**

- EasyEDA footprint `easyeda:C473560_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C477775 RC0402FR-076M81L - R104 - **PASS**

- EasyEDA footprint `easyeda:C477775_R0402` (package `R0402`, corner token `-`), 2 pads; 3D `R0402_L1.0-W0.5-H0.4`
- EasyEDA measured: pads 0.54 x 0.57; centre span 0.86
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C52923 CL05A105KA5NQNC - C111, C112, C130, C131, C210, C309, C310, C311, C403, C1501, C1502 - **PASS**

- EasyEDA footprint `easyeda:C52923_C0402` (package `C0402`, corner token `-`), 2 pads; 3D `C0402_L1.0-W0.5-H0.5`
- EasyEDA measured: pads 0.50 x 0.54; centre span 0.84
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C59461 CL10A226MQ8NRNC - C106 - **PASS**

- EasyEDA footprint `easyeda:C59461_C0603` (package `C0603`, corner token `-`), 2 pads; 3D `C0603_L1.6-W0.8-H0.8`
- EasyEDA measured: pads 0.80 x 0.90; centre span 1.40
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C6807729 MPH160809S100MT - L202 - **PASS**

- EasyEDA footprint `easyeda:C6807729_L0603` (package `L0603`, corner token `-`), 2 pads; 3D `L0603_L1.6-W0.8-H0.5_BEAD`
- EasyEDA measured: pads 0.80 x 0.86; centre span 1.40
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C7393837 TCC0201X7R104K100ZT - C103, C107, C108, C170, C174, C204, C205, C308, C312, C314, C401, C405, C501, C504, C505, C1503, C1601, C1602, C1603 - **PASS**

- EasyEDA footprint `easyeda:C7393837_C0201` (package `C0201`, corner token `-`), 2 pads; 3D `C0201_L0.6-W0.3-H0.3`
- EasyEDA measured: pads 0.32 x 0.37; centre span 0.54
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C76922 GRM0335C1H101JA01D - C206, C207, C303(DNP) - **PASS**

- EasyEDA footprint `easyeda:C76922_C0201` (package `C0201`, corner token `-`), 2 pads; 3D `C0201_L0.6-W0.3-H0.3`
- EasyEDA measured: pads 0.32 x 0.37; centre span 0.54
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C76923 GRM0335C1H200JA01D - C211, C212 - **PASS**

- EasyEDA footprint `easyeda:C76923_C0201` (package `C0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.32 x 0.37; centre span 0.54
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C76924 GRM0335C1H220JA01D - C301(DNP), C302(DNP) - **PASS**

- EasyEDA footprint `easyeda:C76924_C0201` (package `C0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.32 x 0.37; centre span 0.54
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C76935 GRM033R61A105ME44D - C119, C122, C313 - **PASS**

- EasyEDA footprint `easyeda:C76935_C0201` (package `C0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.32 x 0.37; centre span 0.54
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C851635 RC0201DR-0710K2L - R140 - **PASS**

- EasyEDA footprint `easyeda:C851635_R0201` (package `R0201`, corner token `-`), 2 pads; 3D `None`
- EasyEDA measured: pads 0.30 x 0.32; centre span 0.48
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C86059 LQG15HS15NJ02D - L203 - **PASS**

- EasyEDA footprint `easyeda:C86059_L0402` (package `L0402`, corner token `-`), 2 pads; 3D `L0402_L1.0-W0.5-H0.5_BEAD`
- EasyEDA measured: pads 0.54 x 0.54; centre span 0.84
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C861215 RT0603BRD071RL - R111, R112 - **PASS**

- EasyEDA footprint `easyeda:C861215_R0603` (package `R0603`, corner token `-`), 2 pads; 3D `R0603`
- EasyEDA measured: pads 0.81 x 0.86; centre span 1.50
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

### C98045 LQP03TN3N3B02D - L201 - **PASS**

- EasyEDA footprint `easyeda:C98045_L0201-RD` (package `L0201-RD`, corner token `-`), 2 pads; 3D `L0201-RD`
- EasyEDA measured: pads 0.32 x 0.37; centre span 0.54
- Verdict: **PASS** - Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.

## Reviewed copy used by the board (`lib/easyeda_rev.pretty`)

Generated by `tools/review_footprints.py` (Integrate 2026-11-12; land diameter added by the V2-B review fix). Numbered copper pads are compared with the raw easyeda2kicad output below; only paste, unnumbered EP via holes (U6), courtyards and the duplicate `LCSC Part` field differ, plus the land DIAMETER of C509405 and C4371025 (0.17 / 0.149 -> 0.20 mm, review R-12: number, centre, rotation and shape of every pad are checked identical). Full change list: `lib/easyeda_rev_manifest.json`.

| Footprint | Numbered copper pads | Changes |
|---|---|---|
| C105226_C0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.64 x 0.86 mm (pads + body + 0.15 mm) |
| C130414_SOD-523_L1.2-W0.8-LS1.6-RD.kicad_mod | identical (2) | F.CrtYd 1.20 x 0.80 (body only) -> 2.40 x 1.30 mm (pads + body + 0.25 mm) |
| C139059_QFN-32_L4.0-W4.0-P0.40-BL-EP2.9.kicad_mod | identical (33) | EP pad 33 2.90 x 2.90: full paste -> 2 x 2 window(s) 1.272 x 1.272 mm with 0.20 mm webs, coverage 77 %; TI SBAS502C p.82 example stencil: 77 % printed solder coverage; F.CrtYd 4.00 x 4.00 (body only) -> 5.30 x 5.30 mm (pads + body + 0.25 mm) |
| C1518204_C0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.64 x 0.86 mm (pads + body + 0.15 mm) |
| C1546_C0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.64 x 0.86 mm (pads + body + 0.15 mm) |
| C15525_C0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.64 x 0.86 mm (pads + body + 0.15 mm) |
| C161408_C0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.22 x 0.64 mm (pads + body + 0.15 mm) |
| C161418_C0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.22 x 0.64 mm (pads + body + 0.15 mm) |
| C166160_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C17445_R0805.kicad_mod | identical (2) | F.CrtYd 2.00 x 1.28 (body only) -> 3.64 x 1.88 mm (pads + body + 0.25 mm) |
| C189624_LGA-12_L2.0-W2.0-P0.50-BL.kicad_mod | identical (12) | F.CrtYd 2.00 x 2.00 (body only) -> 2.76 x 2.76 mm (pads + body + 0.25 mm) |
| C19666_C0603.kicad_mod | identical (2) | F.CrtYd 1.60 x 0.80 (body only) -> 2.50 x 1.20 mm (pads + body + 0.15 mm) |
| C19702_C0603.kicad_mod | identical (2) | F.CrtYd 1.60 x 0.80 (body only) -> 2.50 x 1.20 mm (pads + body + 0.15 mm) |
| C20345399_X1SON-2_L1.0-W0.6-P0.65-BI.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.60 (body only) -> 2.10 x 1.12 mm (pads + body + 0.25 mm) |
| C2048575_IND-SMD_L1.0-W0.6.kicad_mod | MAKER LAND: pads 1, 2 = Murata LQW15AN JELF243A 12.1 land (a 0.6, b 1.42, c 0.66) [F]; each pad on the same side as EasyEDA's (numbering unchanged) | COPPER: pad 1 (-0.43, 0.00) 0.50 x 0.65 -> (-0.505, 0.000) 0.41 x 0.66; Murata LQW15AN spec JELF243A 12.1 land (same series): 2 pads 0.41 x 0.66 at +-0.505; numbers, origin, 0 deg unchanged [F]; COPPER: pad 2 (0.43, 0.00) 0.50 x 0.65 -> (0.505, 0.000) 0.41 x 0.66; Murata LQW15AN spec JELF243A 12.1 land (same series): 2 pads 0.41 x 0.66 at +-0.505; numbers, origin, 0 deg unchanged [F]; F.CrtYd 1.00 x 0.60 (body only) -> 1.92 x 1.18 mm (pads + body + 0.25 mm) |
| C2050114_IND-SMD_L2.0-W1.6.kicad_mod | identical (2) | F.CrtYd 2.00 x 1.60 (body only) -> 3.16 x 2.22 mm (pads + body + 0.25 mm) |
| C221907_SW-SMD_4P-L3.5-W3.5_PTS840GKSMTRLFS.kicad_mod | MAKER LAND: pads 1, 2, 3, 4 = C&K PTS840 B-41 recommended PCB layout (4 pads 1.05 x 1.40 mm); pad 5 (ESD-pin land) deleted: GK has no pin 5 [S1 D-9]; each pad on the same side as EasyEDA's (numbering unchanged) | COPPER: pad 5 deleted at (1.22, 0.00) 0.50 x 1.10; C&K PTS840 B-40/B-41: GK has no ground pin; EasyEDA pad 5 (ESD-pin land, F.Paste) deleted, review D-9; COPPER: pad 2 (-1.22, -2.12) 0.84 x 1.78 -> (-1.195, -1.800) 1.05 x 1.40; C&K PTS840 B-41 recommended PCB layout: 4 pads 1.05 x 1.40 at lead-line +-0.725 / +-1.80 (was EasyEDA 0.84 x 1.785 at +-0.75 / +-2.12); numbers, origin, 0 deg unchanged; COPPER: pad 4 (0.28, -2.12) 0.84 x 1.78 -> (0.255, -1.800) 1.05 x 1.40; C&K PTS840 B-41 recommended PCB layout: 4 pads 1.05 x 1.40 at lead-line +-0.725 / +-1.80 (was EasyEDA 0.84 x 1.785 at +-0.75 / +-2.12); numbers, origin, 0 deg unchanged; COPPER: pad 3 (0.28, 2.12) 0.84 x 1.78 -> (0.255, 1.800) 1.05 x 1.40; C&K PTS840 B-41 recommended PCB layout: 4 pads 1.05 x 1.40 at lead-line +-0.725 / +-1.80 (was EasyEDA 0.84 x 1.785 at +-0.75 / +-2.12); numbers, origin, 0 deg unchanged; COPPER: pad 1 (-1.22, 2.12) 0.84 x 1.78 -> (-1.195, 1.800) 1.05 x 1.40; C&K PTS840 B-41 recommended PCB layout: 4 pads 1.05 x 1.40 at lead-line +-0.725 / +-1.80 (was EasyEDA 0.84 x 1.785 at +-0.75 / +-2.12); numbers, origin, 0 deg unchanged; courtyard body box C&K PTS840 B-41: body 2.9 x 3.5 mm + actuator 0.65 mm at -x (EasyEDA silk -2.56 .. 0.98); F.CrtYd 3.54 x 3.50 (body only) -> 4.04 x 5.50 mm (pads + body + 0.25 mm) |
| C23733_C0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.64 x 0.86 mm (pads + body + 0.15 mm) |
| C237514_C0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.22 x 0.64 mm (pads + body + 0.15 mm) |
| C25076_R0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.74 x 0.86 mm (pads + body + 0.15 mm) |
| C2691509_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C270345_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C270346_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C270358_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C270364_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C270365_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C270366_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C270612_R0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.74 x 0.86 mm (pads + body + 0.15 mm) |
| C2766851_R0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.74 x 0.86 mm (pads + body + 0.15 mm) |
| C2803242_WSON-6_L2.0-W2.0-P0.65-BL-EP.kicad_mod | identical (7) | pad 7: paste removed; TI TMP117 SNOSD82 p.35: thermal pad best left unsoldered (floating copper island to E1); F.CrtYd 2.00 x 2.00 (body only) -> 2.50 x 2.92 mm (pads + body + 0.25 mm) |
| C2826518_ANT-SMD_L3.5-W1.5.kicad_mod | identical (1) | F.CrtYd 3.50 x 1.50 (body only) -> 4.00 x 2.00 mm (pads + body + 0.25 mm) |
| C2826535_SMD_L2.9-W1.0-2108613-5.kicad_mod | identical (1) | F.CrtYd 2.90 x 1.00 (body only) -> 3.66 x 1.72 mm (pads + body + 0.25 mm) |
| C285010_C0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.22 x 0.64 mm (pads + body + 0.15 mm) |
| C2863637_SC-70-5_L2.1-W1.3-P0.65-LS2.2-BR.kicad_mod | identical (5) | F.CrtYd 1.30 x 2.10 (body only) -> 3.60 x 2.60 mm (pads + body + 0.25 mm) |
| C2867950_UDFN-4_L1.0-W1.0-P0.65-TL.kicad_mod | identical (5) | F.CrtYd 1.00 x 1.00 (body only) -> 1.78 x 1.56 mm (pads + body + 0.25 mm) |
| C295786_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C309454_C0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.22 x 0.64 mm (pads + body + 0.15 mm) |
| C324723_FFC-SMD_10P-P0.50_FH34SRJ-10S-0.5SH.kicad_mod | MAKER LAND: pads 1, 10, 11, 12, 2, 3, 4, 5, 6, 7, 8, 9 = Hirose FH34 p.8-9 recommended pattern, 10 pos (B 4.5, E 6.1, F 6.9, 3.3 overall) [S2a]; each pad on the same side as EasyEDA's (numbering unchanged) | courtyard body box Hirose FH34 p.6: body 7.15 (A max) x 3.8 mm, lead / actuator side at -y [S2a]; F.CrtYd 7.15 x 3.80 (body only) -> 7.66 x 4.30 mm (pads + body + 0.25 mm) |
| C384960_C0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.22 x 0.64 mm (pads + body + 0.15 mm) |
| C3855387_C0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.64 x 0.86 mm (pads + body + 0.15 mm) |
| C398713_CRYSTAL-SMD_L1.6-W1.0.kicad_mod | identical (2) | F.CrtYd 1.60 x 1.00 (body only) -> 2.22 x 1.50 mm (pads + body + 0.25 mm) |
| C413063_R0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.74 x 0.86 mm (pads + body + 0.15 mm) |
| C423135_R0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.74 x 0.86 mm (pads + body + 0.15 mm) |
| C423137_R0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.74 x 0.86 mm (pads + body + 0.15 mm) |
| C423177_R0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.74 x 0.86 mm (pads + body + 0.15 mm) |
| C423179_R0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.74 x 0.86 mm (pads + body + 0.15 mm) |
| C423439_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C423582_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C423797_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C434843_IND-SMD_L2.0-W1.6.kicad_mod | identical (2) | F.CrtYd 2.00 x 1.60 (body only) -> 3.16 x 2.22 mm (pads + body + 0.25 mm) |
| C43676_R0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.74 x 0.86 mm (pads + body + 0.15 mm) |
| C4371025_DSBGA-8_L1.5-W0.7-R2-C4-P0.40-BL.kicad_mod | numbers, centres, rotation and shape identical (8); land diameter 0.149 -> 0.20 mm | COPPER: every round land 0.149 -> 0.20 mm diameter (centres, numbers and count unchanged; paste and mask follow the pad); JLC capability page (BGA pad 0.2 mm minimum); TI YBJ0006 drawing 4226653/A of the same YBJ family (cache/v2/ds_review/ti_mxbg457.pdf, as read by the review): land 0.20 mm NSMD. The YBJ0008 drawing itself was not found; F.CrtYd 1.50 x 0.70 (body only) -> 2.00 x 1.20 mm (pads + body + 0.25 mm) |
| C441935_R0603.kicad_mod | identical (2) | F.CrtYd 1.60 x 0.80 (body only) -> 2.62 x 1.18 mm (pads + body + 0.15 mm) |
| C45993_R0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.74 x 0.86 mm (pads + body + 0.15 mm) |
| C471381_IND-SMD_L1.0-W0.6.kicad_mod | MAKER LAND: pads 1, 2 = Murata LQW15AN JELF243A 12.1 land (a 0.6, b 1.42, c 0.66) [F]; each pad on the same side as EasyEDA's (numbering unchanged) | COPPER: pad 1 (-0.43, 0.00) 0.50 x 0.65 -> (-0.505, 0.000) 0.41 x 0.66; Murata LQW15AN spec JELF243A 12.1 land (same series): 2 pads 0.41 x 0.66 at +-0.505; numbers, origin, 0 deg unchanged [F]; COPPER: pad 2 (0.43, 0.00) 0.50 x 0.65 -> (0.505, 0.000) 0.41 x 0.66; Murata LQW15AN spec JELF243A 12.1 land (same series): 2 pads 0.41 x 0.66 at +-0.505; numbers, origin, 0 deg unchanged [F]; F.CrtYd 1.00 x 0.60 (body only) -> 1.92 x 1.18 mm (pads + body + 0.25 mm) |
| C473048_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C473458_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C473473_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C473560_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C477775_R0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.74 x 0.86 mm (pads + body + 0.15 mm) |
| C478155_DFN1006-3L_L1.0-W0.6-LS1.0-BR.kicad_mod | identical (3) | F.CrtYd 1.00 x 0.60 (body only) -> 1.66 x 1.22 mm (pads + body + 0.25 mm) |
| C478207_X1-DFN1006-3_L1.0-W0.6-P0.35-BR.kicad_mod | identical (3) | F.CrtYd 1.00 x 0.60 (body only) -> 1.60 x 1.22 mm (pads + body + 0.25 mm) |
| C48260_X1SON-2_L1.0-W0.6-P0.65-BI-1.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.60 (body only) -> 2.10 x 1.12 mm (pads + body + 0.25 mm) |
| C504101_DFN1006-3L_L1.0-W0.6-BL.kicad_mod | identical (3) | F.CrtYd 1.00 x 0.60 (body only) -> 1.66 x 1.22 mm (pads + body + 0.25 mm) |
| C506250_VQFN-20_L3.5-W3.5-P0.50-BL-EP2.0.kicad_mod | identical (21) | EP pad 21 2.05 x 2.05: full paste -> 2 x 2 window(s) 0.922 x 0.922 mm with 0.20 mm webs, coverage 81 %; TI SLUSBH2G p.45 example stencil: 81 % printed solder coverage; F.CrtYd 3.50 x 3.50 (body only) -> 4.80 x 4.80 mm (pads + body + 0.25 mm) |
| C509405_WLCSP-50_L3.2-W3.0-TL_NRF52832.kicad_mod | numbers, centres, rotation and shape identical (50); land diameter 0.170 -> 0.20 mm | COPPER: every round land 0.170 -> 0.20 mm diameter (centres, numbers and count unchanged; paste and mask follow the pad); JLC capability page (BGA pad 0.2 mm minimum, 0.2-0.25 mm needs ENIG; read 2026-11-12, cache/v2/jlc_review/pages/pcb-capabilities.html); nRF52832 PS v1.4 Table 132 p.541: ball b = 0.20 mm nominal. Gap between lands at 0.40 mm pitch: 0.20 mm (JLC SMD pad-to-pad >= 0.15 mm); F.CrtYd 3.00 x 3.20 (body only) -> 3.50 x 3.70 mm (pads + body + 0.25 mm) |
| C511402_SENSOR-SMD_8P-L4.8-W2.5-P1.31.kicad_mod | identical (8) | F.CrtYd 4.80 x 2.50 (body only) -> 5.30 x 3.44 mm (pads + body + 0.25 mm) |
| C5187176_XQFN-12_L2.0-W1.7-P0.40-BL.kicad_mod | identical (12) | F.CrtYd 2.00 x 1.70 (body only) -> 2.80 x 2.60 mm (pads + body + 0.25 mm) |
| C5208201_WSON-8_L2.0-W2.0-P0.50-TL-EP.kicad_mod | identical (9) | EP pad 9 0.90 x 1.60: full paste -> 1 x 1 window(s) 0.839 x 1.492 mm, coverage 87 %; [V3F] TI SLUSDJ8A p.34 example stencil (DSG0008A): 87 % printed solder coverage under the package; F.CrtYd 2.00 x 2.00 (body only) -> 2.94 x 2.50 mm (pads + body + 0.25 mm) |
| C5217869_SON-6_L1.5-W1.0-P0.50-TL.kicad_mod | identical (6) | F.CrtYd 1.00 x 1.45 (body only) -> 1.50 x 1.95 mm (pads + body + 0.25 mm) |
| C5220164_X2SON-4_L1.0-W1.0-P0.65-TL-EP.kicad_mod | identical (5) | F.CrtYd 1.00 x 1.00 (body only) -> 1.83 x 1.50 mm (pads + body + 0.25 mm) |
| C52923_C0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.64 x 0.86 mm (pads + body + 0.15 mm) |
| C5328762_BGA-20_L2.0-W1.8-R4-C5-P0.40-TL.kicad_mod | identical (20) | F.CrtYd 2.00 x 1.80 (body only) -> 2.50 x 2.30 mm (pads + body + 0.25 mm) |
| C549275_DFN1006-3_L1.0-W0.6-P0.35-BR_BAT54CM.kicad_mod | numbers identical (3), copper replaced: SOT883 pad set of C478155 (FLAG fixed) | F.CrtYd 0.98 x 0.58 (body only) -> 1.54 x 1.12 mm (pads + body + 0.25 mm); COPPER: small lands 0.40 x 0.16 -> 0.45 x 0.25 mm and large land 0.40 x 0.60 -> 0.45 x 0.70 mm, centres x +-0.32 -> +-0.35, y +-0.18 -> +-0.23 (pad set of C478155, same Nexperia SOT883; EasyEDA's 0.16 mm lands are narrower than the 0.22-0.30 mm terminals, BAT54CM p.6); numbers and orientation unchanged |
| C549313_PROXY-C549275_DFN1006-3_L1.0-W0.6-P0.35-BR_BAT54CM.kicad_mod | identical (3) | F.CrtYd 0.98 x 0.58 (body only) -> 1.54 x 1.12 mm (pads + body + 0.25 mm) |
| C5603826_LED-SMD_3P-L2.2-W1.8_C5D-56-J6U6-20-R18.kicad_mod | identical (3) | F.CrtYd 1.80 x 2.20 (body only) -> 2.30 x 2.70 mm (pads + body + 0.25 mm) |
| C5687033_USON-8_L3.0-W2.0-P0.50-BL-EP1.6_MX25R1635FZUIH0.kicad_mod | identical (9) | F.CrtYd 2.00 x 3.00 (body only) -> 2.50 x 3.50 mm (pads + body + 0.25 mm) |
| C59461_C0603.kicad_mod | identical (2) | F.CrtYd 1.60 x 0.80 (body only) -> 2.50 x 1.20 mm (pads + body + 0.15 mm) |
| C598214_LED-SMD_L2.5-W1.2_KA-2810AVBS-D.kicad_mod | identical (2) | F.CrtYd 2.50 x 1.20 (body only) -> 4.30 x 1.77 mm (pads + body + 0.25 mm) |
| C6736531_SOD-123F_L2.8-W1.8-LS3.7-RD.kicad_mod | MAKER LAND: pads 1, 2 = Nexperia PMEG10020AELR Fig. 17 SOD123W reflow land (1.2 x 1.2 at 2.8 centres) [S2b E-4]; each pad on the same side as EasyEDA's (numbering unchanged) | COPPER: pad 2 (1.65, 0.00) 1.00 x 1.20 -> (1.400, 0.000) 1.20 x 1.20; Nexperia PMEG10020AELR Fig. 17 reflow land: 2 pads 1.2 x 1.2 at +-1.40 (was EasyEDA 1.00 x 1.20 at +-1.65); numbers, origin, 0 deg unchanged [S2b]; COPPER: pad 1 (-1.65, 0.00) 1.00 x 1.20 -> (-1.400, 0.000) 1.20 x 1.20; Nexperia PMEG10020AELR Fig. 17 reflow land: 2 pads 1.2 x 1.2 at +-1.40 (was EasyEDA 1.00 x 1.20 at +-1.65); numbers, origin, 0 deg unchanged [S2b]; courtyard body box Nexperia PMEG10020AELR Fig. 16: 3.3-3.7 x 1.5-1.9 mm (max kept) [S2b]; F.CrtYd 3.70 x 1.90 (body only) -> 4.50 x 2.40 mm (pads + body + 0.25 mm) |
| C6807729_L0603.kicad_mod | identical (2) | F.CrtYd 1.60 x 0.80 (body only) -> 2.50 x 1.18 mm (pads + body + 0.15 mm) |
| C718072_CRYSTAL-SMD_4P-L2.0-W1.6-BL.kicad_mod | identical (4) | F.CrtYd 2.00 x 1.60 (body only) -> 2.80 x 2.42 mm (pads + body + 0.25 mm) |
| C727398_TDFN-4_L1.2-W1.6-P0.50-BL-EP.kicad_mod | identical (5) | F.CrtYd 1.20 x 1.60 (body only) -> 1.70 x 2.52 mm (pads + body + 0.25 mm) |
| C7393837_C0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.22 x 0.64 mm (pads + body + 0.15 mm) |
| C76922_C0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.22 x 0.64 mm (pads + body + 0.15 mm) |
| C76923_C0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.22 x 0.64 mm (pads + body + 0.15 mm) |
| C76924_C0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.22 x 0.64 mm (pads + body + 0.15 mm) |
| C76935_C0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.22 x 0.64 mm (pads + body + 0.15 mm) |
| C851635_R0201.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.10 x 0.64 mm (pads + body + 0.15 mm) |
| C86059_L0402.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.50 (body only) -> 1.68 x 0.86 mm (pads + body + 0.15 mm) |
| C861215_R0603.kicad_mod | identical (2) | F.CrtYd 1.60 x 0.80 (body only) -> 2.62 x 1.18 mm (pads + body + 0.15 mm) |
| C896422_X2DFN-2_L1.0-W0.6-RD.kicad_mod | identical (2) | F.CrtYd 1.00 x 0.60 (body only) -> 1.50 x 1.12 mm (pads + body + 0.25 mm) |
| C98045_L0201-RD.kicad_mod | identical (2) | F.CrtYd 0.60 x 0.30 (body only) -> 1.22 x 0.64 mm (pads + body + 0.15 mm) |
