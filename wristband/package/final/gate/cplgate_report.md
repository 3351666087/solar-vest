# cplgate report

Board: `/path/to/SolarVest_work/wristband/v3/package/final/board/solarband_v3f_final_rf_silk.kicad_pcb` sha256 0c095cb6f60dc2e5..., run 2026-11-16T19:50:23Z

**Shippable: YES (GREEN)**  counts: {'GREEN': 192, 'PREVIEW': 15}

## Board-level

- note R1: the board file carries no LCSC field; the gate takes the C-number from BOM_full_v3f.csv and checks it against the footprint name
- note G1: U10.7 is unconnected in the netlist and on board net TMP117_ISLAND (deliberate board-only net, e.g. R-5 island)
- note R2: the board pads carry no pinfunction; the gate reads pin functions from v3/design/netlist/solarband_v3f_kicad.net (pad nets on the board agree with that netlist: yes)
- note R5: polarized 2-terminal parts point 3 ways (reference terminal direction, deg: refs): 0: D10,D11; 90: D14,D16; 270: D9 -> YELLOW without a waiver

## Parts (not GREEN first)

| Ref | LCSC | Side | Verdict | theta | CPL rot | rms | margin | sym | Class | Reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| D10 | C598214 | top | PREVIEW | 0 | 180.0 | 0.0 | 1.6971 | 2 | P | PREVIEW: G3 (P-6): pin map reviewed by an independent agent on 2026-11-16 (agrees); the human check is this preview row |
| D11 | C130414 | top | PREVIEW | 0 | 180.0 | 0.0 | 0.9192 | 2 | P | PREVIEW: G3 (P-6): pin map reviewed by an independent agent on 2026-11-16 (agrees; two fixes); the human check is this preview row |
| D12 | C549313 | top | PREVIEW | 0 | 180.0 | 0.0497 | 0.4571 | 1 | 1F | PREVIEW: P-6 (no EasyEDA record for C549313 (404 on 2026-11-13 and 2026-11-16): the CPL uses the labelled proxy land of C549275; JLC's own 0 deg is unknown (no second mark source)): PROXY: no EasyEDA record for C549313; the fit and the CPL use the labelled proxy land of C549275 (C549313_PROXY-C549275_DFN1006-3_L1.0-W0.6-P0.35-BR_BAT54CM.kicad_mod); JLC's own 0 deg for C549313 is unknown |
| D14 | C6736531 | top | PREVIEW | 0 | 270.0 | 0.25 | 1.9139 | 2 | P | PREVIEW: G3 (P-6): pin map reviewed by an independent agent on 2026-11-16 (agrees for the PMEG10020AELR type; the -Q data sheet itself was not found); the human check is this preview row |
| D16 | C896422 | top | PREVIEW | 0 | 90.0 | 0.0 | 0.4667 | 2 | P | PREVIEW: G3 (P-6): pin map reviewed by an independent agent on 2026-11-16 (agrees; the EasyEDA contradiction is resolved: cathode = pad 1); the human check is this preview row |
| D3 | C5603826 | bottom | PREVIEW | 0 | 0.0 | 0.0 | 0.8684 | 1 | 1F | PREVIEW: G3 (P-6): pin map reviewed by an independent agent on 2026-11-16 (agrees (with a caution)); the human check is this preview row; PREVIEW: P-6 (bottom-side part (skin side); the CPL bottom convention D_b is self-consistent in G7 but unverified at JLC (no bottom canary)): R3: JLC-placed on the bottom side and no bottom canary verified within 60 days (§6.6) |
| D4 | C5603826 | bottom | PREVIEW | 0 | 0.0 | 0.0 | 0.8684 | 1 | 1F | PREVIEW: G3 (P-6): pin map reviewed by an independent agent on 2026-11-16 (agrees (with a caution)); the human check is this preview row; PREVIEW: P-6 (bottom-side part (skin side); the CPL bottom convention D_b is self-consistent in G7 but unverified at JLC (no bottom canary)): R3: JLC-placed on the bottom side and no bottom canary verified within 60 days (§6.6) |
| D9 | C130414 | top | PREVIEW | 0 | 90.0 | 0.0 | 0.9192 | 2 | P | PREVIEW: G3 (P-6): pin map reviewed by an independent agent on 2026-11-16 (agrees; two fixes); the human check is this preview row |
| J11 | C2826535 | top | PREVIEW | 0 | 90.0 | 0.0 | 0.0 | 2 | M | PREVIEW: P-6 (single-pad spring finger; 0 and 180 deg fit the same land and differ mechanically (contact tip 0.6-0.8 mm off the pad centre)): UNKNOWN: 1 shared pad number(s); copper fits at 0 and 180 deg alike: geometry cannot decide (JLC preview + waiver) |
| J15 | C2826535 | top | PREVIEW | 0 | 90.0 | 0.0 | 0.0 | 2 | M | PREVIEW: P-6 (single-pad spring finger; 0 and 180 deg fit the same land and differ mechanically (contact tip 0.6-0.8 mm off the pad centre)): UNKNOWN: 1 shared pad number(s); copper fits at 0 and 180 deg alike: geometry cannot decide (JLC preview + waiver) |
| J18 | C2826535 | top | PREVIEW | 0 | 90.0 | 0.0 | 0.0 | 2 | M | PREVIEW: P-6 (single-pad spring finger; 0 and 180 deg fit the same land and differ mechanically (contact tip 0.6-0.8 mm off the pad centre)): UNKNOWN: 1 shared pad number(s); copper fits at 0 and 180 deg alike: geometry cannot decide (JLC preview + waiver) |
| J19 | C2826535 | top | PREVIEW | 0 | 90.0 | 0.0 | 0.0 | 2 | M | PREVIEW: P-6 (single-pad spring finger; 0 and 180 deg fit the same land and differ mechanically (contact tip 0.6-0.8 mm off the pad centre)): UNKNOWN: 1 shared pad number(s); copper fits at 0 and 180 deg alike: geometry cannot decide (JLC preview + waiver) |
| J40 | C2826518 | top | PREVIEW | 0 | 340.0 | 0.0 | 0.0 | 2 | M | PREVIEW: P-6 (single-pad spring finger at 340 deg (ruling L-1 / J-1); 0 and 180 deg fit the same land; R7 non-orthogonal angle placed by JLC as given): R7: rotation 340.0 deg is not a multiple of 90 (no waiver); PREVIEW: P-6 (single-pad spring finger at 340 deg (ruling L-1 / J-1); 0 and 180 deg fit the same land; R7 non-orthogonal angle placed by JLC as given): UNKNOWN: 1 shared pad number(s); copper fits at 0 and 180 deg alike: geometry cannot decide (JLC preview + waiver) |
| PD1 | C511402 | bottom | PREVIEW | 0 | 90.0 | 0.0 | 2.7034 | 2 | 2F | PREVIEW: G3 (P-6): pin map reviewed by an independent agent on 2026-11-16 (agrees); the human check is this preview row; PREVIEW: P-6 (bottom-side part; D_b unverified at JLC): R3: JLC-placed on the bottom side and no bottom canary verified within 60 days (§6.6) |
| SW1 | C221907 | top | PREVIEW | 0 | 180.0 | 0.321 | 2.6493 | 2 | M | PREVIEW: P-6 (mechanically polar (class M); 4-pad copper is 2-fold symmetric; actuator side settled by the EasyEDA silk and the maker drawing (pin 5 opposite the actuator), still only visible in the preview) |
| C101 | C19666 | top | GREEN | 0 | 270.0 | 0.0 | 0.9899 | 2 | - | non-polar passive: 180 deg equivalent |
| C102 | C19702 | top | GREEN | 0 | 90.0 | 0.0 | 0.9899 | 2 | - | non-polar passive: 180 deg equivalent |
| C103 | C7393837 | top | GREEN | 0 | 180.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C104 | C3855387 | top | GREEN | 0 | 270.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C105 | C105226 | top | GREEN | 0 | 0.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C106 | C59461 | top | GREEN | 0 | 0.0 | 0.0 | 0.9899 | 2 | - | non-polar passive: 180 deg equivalent |
| C107 | C7393837 | top | GREEN | 0 | 270.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C108 | C7393837 | top | GREEN | 0 | 90.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C111 | C52923 | top | GREEN | 0 | 180.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C112 | C52923 | top | GREEN | 0 | 0.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C113 | C285010 | top | GREEN | 0 | 270.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C114 | C105226 | top | GREEN | 0 | 0.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C115 | C105226 | top | GREEN | 0 | 270.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C116 | C105226 | top | GREEN | 0 | 0.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C117 | C105226 | top | GREEN | 0 | 270.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C119 | C76935 | top | GREEN | 0 | 90.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C120 | C285010 | top | GREEN | 0 | 270.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C121 | C23733 | top | GREEN | 0 | 0.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C122 | C76935 | top | GREEN | 0 | 0.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C130 | C52923 | top | GREEN | 0 | 90.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C131 | C52923 | top | GREEN | 0 | 270.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C132 | C309454 | top | GREEN | 0 | 90.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C1501 | C52923 | top | GREEN | 0 | 180.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C1502 | C52923 | top | GREEN | 0 | 90.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C1503 | C7393837 | top | GREEN | 0 | 180.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C1601 | C7393837 | top | GREEN | 0 | 0.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C1602 | C7393837 | top | GREEN | 0 | 270.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C1603 | C7393837 | top | GREEN | 0 | 180.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C170 | C7393837 | top | GREEN | 0 | 0.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C174 | C7393837 | top | GREEN | 0 | 90.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C175 | C161418 | top | GREEN | 0 | 90.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C201 | C384960 | top | GREEN | 0 | 180.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C202 | C384960 | top | GREEN | 0 | 180.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C203 | C237514 | top | GREEN | 0 | 0.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C204 | C7393837 | top | GREEN | 0 | 180.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C205 | C7393837 | top | GREEN | 0 | 0.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C206 | C76922 | top | GREEN | 0 | 0.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C207 | C76922 | top | GREEN | 0 | 0.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C209 | C23733 | top | GREEN | 0 | 90.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C210 | C52923 | top | GREEN | 0 | 270.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C211 | C76923 | top | GREEN | 0 | 90.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C212 | C76923 | top | GREEN | 0 | 90.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C215 | C2048575 | top | GREEN | 0 | 270.0 | 0.075 | 0.5883 | 2 | - | non-polar passive: 180 deg equivalent |
| C304 | C161408 | top | GREEN | 0 | 90.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C305 | C1518204 | top | GREEN | 0 | 180.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C306 | C1518204 | top | GREEN | 0 | 0.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C307 | C15525 | top | GREEN | 0 | 180.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C308 | C7393837 | top | GREEN | 0 | 180.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C309 | C52923 | top | GREEN | 0 | 270.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C310 | C52923 | top | GREEN | 0 | 90.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C311 | C52923 | top | GREEN | 0 | 90.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C312 | C7393837 | top | GREEN | 0 | 180.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C313 | C76935 | top | GREEN | 0 | 270.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C314 | C7393837 | top | GREEN | 0 | 270.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C401 | C7393837 | top | GREEN | 0 | 0.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C402 | C15525 | top | GREEN | 0 | 0.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C403 | C52923 | top | GREEN | 0 | 90.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C404 | C19702 | top | GREEN | 0 | 90.0 | 0.0 | 0.9899 | 2 | - | non-polar passive: 180 deg equivalent |
| C405 | C7393837 | top | GREEN | 0 | 90.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C501 | C7393837 | top | GREEN | 0 | 270.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C502 | C15525 | top | GREEN | 0 | 180.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| C504 | C7393837 | top | GREEN | 0 | 0.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| C505 | C7393837 | top | GREEN | 0 | 270.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| D13 | C20345399 | top | GREEN | 0 | 270.0 | 0.0 | 0.7071 | 2 | N | no polarity per pin map, identical pads: 180 deg equivalent (G5 modulo-180 rule) |
| D15 | C48260 | top | GREEN | 0 | 0.0 | 0.0 | 0.7071 | 2 | N | no polarity per pin map, identical pads: 180 deg equivalent (G5 modulo-180 rule) |
| D17 | C549275 | top | GREEN | 0 | 180.0 | 0.0497 | 0.4571 | 1 | 1F |  |
| D18 | C48260 | top | GREEN | 0 | 0.0 | 0.0 | 0.7071 | 2 | N | no polarity per pin map, identical pads: 180 deg equivalent (G5 modulo-180 rule) |
| D19 | C549275 | top | GREEN | 0 | 180.0 | 0.0497 | 0.4571 | 1 | 1F |  |
| D5 | C48260 | top | GREEN | 0 | 180.0 | 0.0 | 0.7071 | 2 | N | no polarity per pin map, identical pads: 180 deg equivalent (G5 modulo-180 rule) |
| D6 | C48260 | top | GREEN | 0 | 180.0 | 0.0 | 0.7071 | 2 | N | no polarity per pin map, identical pads: 180 deg equivalent (G5 modulo-180 rule) |
| D7 | C48260 | top | GREEN | 0 | 180.0 | 0.0 | 0.7071 | 2 | N | no polarity per pin map, identical pads: 180 deg equivalent (G5 modulo-180 rule) |
| D8 | C48260 | top | GREEN | 0 | 0.0 | 0.0 | 0.7071 | 2 | N | no polarity per pin map, identical pads: 180 deg equivalent (G5 modulo-180 rule) |
| FB1 | C473473 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| FB2 | C473473 | top | GREEN | 0 | 180.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| FB3 | C473473 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| FB4 | C473473 | top | GREEN | 0 | 270.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| FB5 | C473473 | top | GREEN | 0 | 180.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| FB6 | C473473 | top | GREEN | 0 | 270.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| J13 | C324723 | top | GREEN | 0 | 90.0 | 0.0 | 2.9486 | 1 | 1F |  |
| L1 | C2050114 | top | GREEN | 0 | 90.0 | 0.0 | 1.1738 | 2 | - | non-polar passive: 180 deg equivalent |
| L2 | C434843 | top | GREEN | 0 | 270.0 | 0.0 | 1.1738 | 2 | - | non-polar passive: 180 deg equivalent |
| L201 | C98045 | top | GREEN | 0 | 180.0 | 0.0 | 0.3818 | 2 | - | non-polar passive: 180 deg equivalent |
| L202 | C6807729 | top | GREEN | 0 | 180.0 | 0.0 | 0.9899 | 2 | - | non-polar passive: 180 deg equivalent |
| L203 | C86059 | top | GREEN | 0 | 90.0 | 0.0 | 0.594 | 2 | - | non-polar passive: 180 deg equivalent |
| L204 | C471381 | top | GREEN | 0 | 90.0 | 0.075 | 0.5883 | 2 | - | non-polar passive: 180 deg equivalent |
| Q1 | C478155 | top | GREEN | 0 | 180.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q10 | C478155 | top | GREEN | 0 | 180.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q11 | C478155 | top | GREEN | 0 | 270.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q12 | C478155 | top | GREEN | 0 | 180.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q13 | C478155 | top | GREEN | 0 | 0.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q14 | C478207 | top | GREEN | 0 | 0.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q16 | C478155 | top | GREEN | 0 | 270.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q17 | C478155 | top | GREEN | 0 | 270.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q18 | C478207 | top | GREEN | 0 | 90.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q19 | C478155 | top | GREEN | 0 | 180.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q20 | C504101 | top | GREEN | 0 | 180.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q4 | C478155 | top | GREEN | 0 | 0.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q5 | C478155 | top | GREEN | 0 | 0.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q6 | C478155 | top | GREEN | 0 | 0.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q7 | C478155 | top | GREEN | 0 | 90.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q8 | C478155 | top | GREEN | 0 | 0.0 | 0.0 | 0.5369 | 1 | 1F |  |
| Q9 | C478155 | top | GREEN | 0 | 0.0 | 0.0 | 0.5369 | 1 | 1F |  |
| R101 | C2766851 | top | GREEN | 0 | 0.0 | 0.0 | 0.6081 | 2 | - | non-polar passive: 180 deg equivalent |
| R102 | C423137 | top | GREEN | 0 | 180.0 | 0.0 | 0.6081 | 2 | - | non-polar passive: 180 deg equivalent |
| R103 | C423179 | top | GREEN | 0 | 270.0 | 0.0 | 0.6081 | 2 | - | non-polar passive: 180 deg equivalent |
| R104 | C477775 | top | GREEN | 0 | 180.0 | 0.0 | 0.6081 | 2 | - | non-polar passive: 180 deg equivalent |
| R105 | C45993 | top | GREEN | 0 | 0.0 | 0.0 | 0.6081 | 2 | - | non-polar passive: 180 deg equivalent |
| R106 | C423135 | top | GREEN | 0 | 0.0 | 0.0 | 0.6081 | 2 | - | non-polar passive: 180 deg equivalent |
| R107 | C423177 | top | GREEN | 0 | 180.0 | 0.0 | 0.6081 | 2 | - | non-polar passive: 180 deg equivalent |
| R108 | C423797 | top | GREEN | 0 | 270.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R111 | C861215 | top | GREEN | 0 | 0.0 | 0.0 | 1.0607 | 2 | - | non-polar passive: 180 deg equivalent |
| R112 | C861215 | top | GREEN | 0 | 180.0 | 0.0 | 1.0607 | 2 | - | non-polar passive: 180 deg equivalent |
| R116 | C270364 | top | GREEN | 0 | 0.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R117 | C270612 | top | GREEN | 0 | 270.0 | 0.0 | 0.6081 | 2 | - | non-polar passive: 180 deg equivalent |
| R123 | C473458 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R124 | C295786 | top | GREEN | 0 | 270.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R125 | C423797 | top | GREEN | 0 | 180.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R126 | C423582 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R127 | C270346 | top | GREEN | 0 | 0.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R128 | C295786 | top | GREEN | 0 | 180.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R129 | C270345 | top | GREEN | 0 | 180.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R130 | C17445 | top | GREEN | 0 | 270.0 | 0.0 | 1.4142 | 2 | - | non-polar passive: 180 deg equivalent |
| R131 | C423797 | top | GREEN | 0 | 180.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R133 | C270366 | top | GREEN | 0 | 180.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R140 | C851635 | top | GREEN | 0 | 270.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R141 | C270358 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R142 | C43676 | top | GREEN | 0 | 270.0 | 0.0 | 0.6081 | 2 | - | non-polar passive: 180 deg equivalent |
| R143 | C473458 | top | GREEN | 0 | 0.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R144 | C295786 | top | GREEN | 0 | 270.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R145 | C295786 | top | GREEN | 0 | 180.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R146 | C295786 | top | GREEN | 0 | 0.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R149 | C295786 | top | GREEN | 0 | 270.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R160 | C270366 | top | GREEN | 0 | 0.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R161 | C295786 | top | GREEN | 0 | 270.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R162 | C270365 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R163 | C295786 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R164 | C295786 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R165 | C270364 | top | GREEN | 0 | 0.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R167 | C295786 | top | GREEN | 0 | 270.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R170 | C423439 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R171 | C2691509 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R172 | C166160 | top | GREEN | 0 | 270.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R174 | C423797 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R175 | C295786 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R176 | C295786 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R301 | C441935 | top | GREEN | 0 | 0.0 | 0.0 | 1.0607 | 2 | - | non-polar passive: 180 deg equivalent |
| R302 | C441935 | top | GREEN | 0 | 90.0 | 0.0 | 1.0607 | 2 | - | non-polar passive: 180 deg equivalent |
| R303 | C441935 | top | GREEN | 0 | 90.0 | 0.0 | 1.0607 | 2 | - | non-polar passive: 180 deg equivalent |
| R304 | C441935 | top | GREEN | 0 | 270.0 | 0.0 | 1.0607 | 2 | - | non-polar passive: 180 deg equivalent |
| R305 | C441935 | top | GREEN | 0 | 270.0 | 0.0 | 1.0607 | 2 | - | non-polar passive: 180 deg equivalent |
| R306 | C441935 | top | GREEN | 0 | 90.0 | 0.0 | 1.0607 | 2 | - | non-polar passive: 180 deg equivalent |
| R311 | C473048 | top | GREEN | 0 | 180.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R312 | C473048 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R313 | C473048 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R314 | C473048 | top | GREEN | 0 | 180.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R315 | C270364 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R316 | C270364 | top | GREEN | 0 | 180.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R317 | C473560 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R318 | C25076 | top | GREEN | 0 | 0.0 | 0.0 | 0.6081 | 2 | - | non-polar passive: 180 deg equivalent |
| R319 | C25076 | top | GREEN | 0 | 270.0 | 0.0 | 0.6081 | 2 | - | non-polar passive: 180 deg equivalent |
| R401 | C270364 | top | GREEN | 0 | 270.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R402 | C270364 | top | GREEN | 0 | 180.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R501 | C270364 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R503 | C270364 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R504 | C270364 | top | GREEN | 0 | 90.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R505 | C270346 | top | GREEN | 0 | 270.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R506 | C270346 | top | GREEN | 0 | 180.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R507 | C413063 | top | GREEN | 0 | 180.0 | 0.0 | 0.6081 | 2 | - | non-polar passive: 180 deg equivalent |
| R508 | C295786 | top | GREEN | 0 | 180.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R509 | C270364 | top | GREEN | 0 | 0.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R510 | C295786 | top | GREEN | 0 | 0.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| R511 | C473048 | top | GREEN | 0 | 180.0 | 0.0 | 0.3394 | 2 | - | non-polar passive: 180 deg equivalent |
| U1 | C506250 | top | GREEN | 0 | 270.0 | 0.0 | 2.6049 | 4 | 4F | pin 1 settled (pin-1 identity (G3), footprint pin-1 dot, package corner token) |
| U10 | C2803242 | top | GREEN | 0 | 90.0 | 0.0 | 1.4592 | 2 | 2F | pin 1 settled (pin-1 identity (G3), footprint pin-1 dot, package corner token) |
| U11 | C5687033 | top | GREEN | 0 | 270.0 | 0.0 | 1.8257 | 2 | 2F | pin 1 settled (pin-1 identity (G3), footprint pin-1 dot, package corner token) |
| U12 | C727398 | top | GREEN | 0 | 90.0 | 0.0 | 0.976 | 2 | 2F | pin 1 settled (pin-1 identity (G3), footprint pin-1 dot, package corner token) |
| U13 | C727398 | top | GREEN | 0 | 270.0 | 0.0 | 0.976 | 2 | 2F | pin 1 settled (pin-1 identity (G3), footprint pin-1 dot, package corner token) |
| U15 | C5208201 | top | GREEN | 0 | 90.0 | 0.0 | 1.4697 | 2 | 2F | pin 1 settled (pin-1 identity (G3), footprint pin-1 dot, package corner token) |
| U16 | C2867950 | top | GREEN | 0 | 0.0 | 0.0 | 0.6718 | 2 | 2F | pin 1 settled (pin-1 identity (G3), footprint pin-1 dot, package corner token) |
| U17 | C5187176 | top | GREEN | 0 | 270.0 | 0.0 | 1.2503 | 2 | 2F | pin 1 settled (pin-1 identity (G3), footprint pin-1 dot, package corner token) |
| U19 | C2863637 | top | GREEN | 0 | 0.0 | 0.0 | 1.7318 | 1 | 1F |  |
| U20 | C2863637 | top | GREEN | 0 | 90.0 | 0.0 | 1.7318 | 1 | 1F |  |
| U21 | C5217869 | top | GREEN | 0 | 180.0 | 0.0 | 0.7138 | 1 | 2F |  |
| U3 | C5220164 | top | GREEN | 0 | 90.0 | 0.0 | 0.678 | 2 | 2F | pin 1 settled (pin-1 identity (G3), footprint pin-1 dot, package corner token) |
| U4 | C4371025 | top | GREEN | 0 | 0.0 | 0.0 | 0.6928 | 2 | 2F | pin 1 settled (pin-1 identity (G3), footprint pin-1 dot, package corner token) |
| U5 | C4371025 | top | GREEN | 0 | 270.0 | 0.0 | 0.6928 | 2 | 2F | pin 1 settled (pin-1 identity (G3), footprint pin-1 dot, package corner token) |
| U6 | C509405 | top | GREEN | 0 | 180.0 | 0.0 | 1.767 | 1 | 1F |  |
| U7 | C139059 | top | GREEN | 0 | 270.0 | 0.0 | 3.1272 | 4 | 4F | pin 1 settled (pin-1 identity (G3), footprint pin-1 dot, package corner token) |
| U8 | C5328762 | top | GREEN | 0 | 270.0 | 0.0 | 1.0198 | 2 | 2F | pin 1 settled (pin-1 identity (G3), footprint pin-1 dot, package corner token) |
| U9 | C189624 | top | GREEN | 0 | 90.0 | 0.0 | 1.4167 | 2 | 2F | pin 1 settled (pin-1 identity (G3), footprint pin-1 dot, package corner token) |
| X1 | C718072 | top | GREEN | 0 | 90.0 | 0.0 | 1.259 | 2 | N | pin 1 settled (pin-1 identity (G3), footprint pin-1 dot, package corner token) |
| X2 | C398713 | top | GREEN | 0 | 180.0 | 0.0 | 0.7778 | 2 | N | no polarity per pin map, identical pads: 180 deg equivalent (G5 modulo-180 rule) |
