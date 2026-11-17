# JLC stock, library class and price - SolarBand V3-F main board

JLC parts API (`selectSmtComponentList`, public, no login), queried 2026-11-15T01:30:58+00:00 to 2026-11-16T19:41:57+00:00 UTC by `tools/jlc_query.py`; raw answers in `data/jlc/<C>.json` (fields used; raw answers outside the project). Stock changes hourly. Rule: flag a line when the orderable quantity = min(stockCount, canPresaleNumber) is < 50 or < 5 x the quantity for 10 boards, or when JLC marks the part as not SMT-placed (`assemblyComponentFlag`). `canPresaleNumber` is not documented by JLC (review R-05); only the BOM tool, an account action that was not taken, settles what can really be ordered.

| Variant | BOM lines | Placements | Basic | Preferred | Extended | Flagged |
|---|---|---|---|---|---|---|
| v3f | 91 | 207 | 7 | 0 | 84 | 4 |
| v3f_fldnp | 91 | 204 | 7 | 0 | 84 | 4 |
| v3f_o2m | 91 | 206 | 7 | 0 | 84 | 4 |
| v3f_o2pack | 85 | 191 | 7 | 0 | 78 | 4 |
| v3f_noled | 89 | 203 | 7 | 0 | 82 | 4 |
| v3f_noled_o2pack | 83 | 187 | 7 | 0 | 76 | 4 |
| v3f_nofl | 91 | 204 | 7 | 0 | 84 | 4 |
| v3f_nomotor | 90 | 202 | 7 | 0 | 83 | 4 |
| v3f_erm7 | 91 | 207 | 7 | 0 | 84 | 4 |
| v3f_erm6 | 91 | 207 | 7 | 0 | 84 | 4 |
| v3f_nofl_noled_nomotor | 88 | 195 | 7 | 0 | 81 | 4 |

## Flagged lines (any variant)

| LCSC | Part | Refs | Qty/board | Stock | canPresale | Why | Variant |
|---|---|---|---|---|---|---|---|
| C23733 | CL05A475MP5NRNC | C121,C209 | 2 | 624037 | -15705 | LOW: orderable 0 (stock 624037, canPresale -15705) < 50 | all |
| C4371025 | INA236AIYBJR | U4,U5 | 2 | 94 | 48 | LOW: orderable 48 (stock 94, canPresale 48) < 50 | all |
| C5328762 | MAX86141ENP+T | U8 | 1 | 51 | 43 | LOW: orderable 43 (stock 51, canPresale 43) < 50 | all |
| C5208201 | BQ25170DSGR | U15 | 1 | 149 | -67 | LOW: orderable 0 (stock 149, canPresale -67) < 50 | all |

## Parts not in the v1 BOM (V2-B and V3-F additions)

| LCSC | MPN | Manufacturer | Package | Library | Stock | USD @100 | Refs (baseline or variant) | Queried UTC |
|---|---|---|---|---|---|---|---|---|
| C7393837 | TCC0201X7R104K100ZT | CCTC | 0201 | Extended | 659227 | 0.0019 | C103,C107,C108,C170,C174,C204,C205,C308,C312,C314,C401,C405,C501,C504,C505,C1503,C1601,C1602,C1603 | 2026-11-15T01:34:47+00:00 |
| C3855387 | GRM1555C1E103JE01D | Murata Electronics | 0402 | Extended | 65300 | 0.0807 | C104 | 2026-11-15T01:35:53+00:00 |
| C105226 | CL05A226MQ5QUNC | Samsung Electro-Mechanics | 0402 | Extended | 170691 | 0.1134 | C105,C114,C115,C116,C117 | 2026-11-15T01:30:58+00:00 |
| C285010 | 0201B103K250NT | FH (Guangdong Fenghua Advanced Tech) | 0201 | Extended | 1154288 | 0.0023 | C113,C120 | 2026-11-15T01:32:54+00:00 |
| C76935 | GRM033R61A105ME44D | Murata Electronics | 0201 | Extended | 413121 | 0.0225 | C119,C122,C313 | 2026-11-15T01:35:40+00:00 |
| C23733 | CL05A475MP5NRNC | Samsung Electro-Mechanics | 0402 | Basic | 624037 | 0.0113 | C121,C209 | 2026-11-15T01:31:58+00:00 |
| C309454 | CC0201KRX7R8BB472 | YAGEO | 0201 | Extended | 8124 | 0.0038 | C132 | 2026-11-15T01:35:42+00:00 |
| C161418 | GRM0335C1H221JA01D | Murata Electronics | 0201 | Extended | 34128 | 0.0072 | C175 | 2026-11-15T01:35:12+00:00 |
| C161371 | GRM0335C1E102JA01D | Murata Electronics | 0201 | Extended | 83387 | 0.0171 | C175 (v3f_o2m) | 2026-11-15T01:36:04+00:00 |
| C384960 | GRM0335C1H120FA01D | Murata Electronics | 0201 | Extended | 123947 | 0.0092 | C201,C202 | 2026-11-15T01:33:05+00:00 |
| C237514 | GJM0335C1H1R0BB01D | Murata Electronics | 0201 | Extended | 36948 | 0.0197 | C203 | 2026-11-15T01:32:00+00:00 |
| C76922 | GRM0335C1H101JA01D | Murata Electronics | 0201 | Extended | 304216 | 0.0067 | C206,C207 | 2026-11-15T01:34:50+00:00 |
| C76923 | GRM0335C1H200JA01D | Murata Electronics | 0201 | Extended | 9364 | 0.0062 | C211,C212 | 2026-11-15T01:35:45+00:00 |
| C2048575 | LQW15AN7N6G80D | Murata Electronics | 0402 | Extended | 6846 | 0.0631 | C215 | 2026-11-16T19:17:55+00:00 |
| C161408 | GRM0335C1H151JA01D | Murata Electronics | 0201 | Extended | 5980 | 0.0121 | C304 | 2026-11-15T01:35:48+00:00 |
| C1518204 | GRM1555C1H472JE01D | Murata Electronics | 0402 | Extended | 265905 | 0.0158 | C305,C306 | 2026-11-15T01:35:56+00:00 |
| C5603826 | CT DBLP31.12 | OSRAM Opto Semicon | SMD,2.2x1.8mm | Extended | 295 | 1.322 | D3,D4 | 2026-11-15T01:34:28+00:00 |
| C130414 | BAS521,115 | Nexperia | SOD-523 | Extended | 82200 | 0.076 | D9,D11 | 2026-11-15T01:31:01+00:00 |
| C598214 | KA-2810ASURSK | Kingbright | SMD,2.8x1.2mm | Extended | 1610 | 0.2615 | D10 | 2026-11-15T01:34:36+00:00 |
| C549313 | BAV70M,315 | Nexperia | SOT-883 | Extended | 1481 | 0.169 | D12 | 2026-11-15T01:34:25+00:00 |
| C20345399 | ESD761DPYR | Texas Instruments | X1-SON-2(0.6x1) | Extended | 24136 | 0.0989 | D13 | 2026-11-15T12:37:09+00:00 |
| C6736531 | PMEG10020AELR-QX | Nexperia | SOD-123W | Extended | 6422 | 0.2078 | D14 | 2026-11-15T12:38:37+00:00 |
| C896422 | NSR0240MX2T5G | onsemi | DFN-2(0.6x1) | Extended | 604 | 0.2607 | D16 | 2026-11-15T12:54:04+00:00 |
| C549275 | BAT54CM,315 | Nexperia | SOT-883 | Extended | 7036 | 0.0745 | D17,D19 | 2026-11-15T01:34:22+00:00 |
| C473473 | 0201WMF0000TEE | UNI-ROYAL(Uniroyal Elec) | 0201 | Extended | 3405792 | 0.0011 | FB1,FB2,FB3,FB4,FB5,FB6 | 2026-11-15T01:35:37+00:00 |
| C2826535 | BW0036BG-L3.0W1.0H1.4 | BAT WIRELESS | SMD | Extended | 6372 | 0.0254 | J11,J15,J18,J19 | 2026-11-15T12:37:14+00:00 |
| C324723 | FH34SRJ-10S-0.5SH(50) | HRS(Hirose) | SMD,P=0.5mm,Surface Mount，Right Angle | Extended | 22427 | 0.1532 | J13 | 2026-11-15T11:11:28+00:00 |
| C2826518 | BW0020AG-L3.5W1.5H3.0 | BAT WIRELESS | - | Extended | 51250 | 0.0234 | J40 | 2026-11-15T18:33:44+00:00 |
| C98045 | LQP03TN3N3B02D | Murata Electronics | 0201 | Extended | 129031 | 0.0128 | L201 | 2026-11-15T01:35:09+00:00 |
| C471381 | LQW15AN4N3B80D | Murata Electronics | 0402 | Extended | 21380 | 0.0919 | L204 | 2026-11-16T19:17:59+00:00 |
| C478155 | PMZ290UNE2YL | Nexperia | DFN1006-3L | Extended | 2271 | 0.0392 | Q1,Q4,Q5,Q6,Q7,Q8,Q9,Q10,Q11,Q12,Q13,Q16,Q17,Q19 | 2026-11-15T12:37:11+00:00 |
| C478207 | PMZ350UPEYL | Nexperia | X1-DFN1006-3 | Extended | 21158 | 0.0588 | Q14,Q18 | 2026-11-15T01:33:49+00:00 |
| C504101 | CJBA7002K | Jiangsu Changjing Electronics Technology Co., Ltd. | DFN-3L(1x0.6) | Extended | 6167 | 0.0318 | Q20 | 2026-11-15T18:33:41+00:00 |
| C423179 | 0402WGF3924TCE | UNI-ROYAL(Uniroyal Elec) | 0402 | Extended | 3741 | 0.0009 | R103 | 2026-11-15T01:33:22+00:00 |
| C477775 | RC0402FR-076M81L | YAGEO | 0402 | Extended | 9560 | 0.0008 | R104 | 2026-11-15T01:33:44+00:00 |
| C45993 | 0402WGF3833TCE | UNI-ROYAL(Uniroyal Elec) | 0402 | Extended | 20725 | 0.0012 | R105 | 2026-11-15T12:37:01+00:00 |
| C423177 | 0402WGF4024TCE | UNI-ROYAL(Uniroyal Elec) | 0402 | Extended | 9811 | 0.001 | R107 | 2026-11-15T01:33:19+00:00 |
| C423797 | 0201WMF1005TEE | UNI-ROYAL(Uniroyal Elec) | 0201 | Extended | 91110 | 0.0018 | R108,R125,R131,R174 | 2026-11-15T01:35:18+00:00 |
| C270364 | 0201WMF1003TEE | UNI-ROYAL(Uniroyal Elec) | 0201 | Extended | 3101195 | 0.0014 | R116,R165,R315,R316,R401,R402,R501,R503,R504,R509 | 2026-11-15T12:54:08+00:00 |
| C270612 | 0402WGF330KTCE | UNI-ROYAL(Uniroyal Elec) | 0402 | Extended | 12971 | 0.0014 | R117 | 2026-11-15T01:32:37+00:00 |
| C473458 | 0201WMF2203TEE | UNI-ROYAL(Uniroyal Elec) | 0201 | Extended | 59448 | 0.0019 | R123,R143 | 2026-11-15T01:35:20+00:00 |
| C295786 | RC0201FR-071ML | YAGEO | 0201 | Extended | 2217739 | 0.0015 | R124,R128,R144,R145,R146,R149,R161,R163,R164,R167,R175,R176,R508,R510 | 2026-11-15T12:54:11+00:00 |
| C423582 | 0201WMF3304TEE | UNI-ROYAL(Uniroyal Elec) | 0201 | Extended | 7196 | 0.0027 | R126 | 2026-11-15T01:35:23+00:00 |
| C270346 | 0201WMF4701TEE | UNI-ROYAL(Uniroyal Elec) | 0201 | Extended | 482961 | 0.0016 | R127,R505,R506 | 2026-11-15T01:32:20+00:00 |
| C270345 | 0201WMF4702TEE | UNI-ROYAL(Uniroyal Elec) | 0201 | Extended | 257939 | 0.0014 | R129 | 2026-11-15T01:35:26+00:00 |
| C17445 | 0805W8F120JT5E | UNI-ROYAL(Uniroyal Elec) | 0805 | Extended | 23356 | 0.0041 | R130 | 2026-11-15T01:36:01+00:00 |
| C270366 | 0201WMF1000TEE | UNI-ROYAL(Uniroyal Elec) | 0201 | Extended | 408327 | 0.0011 | R133,R160 | 2026-11-15T01:32:34+00:00 |
| C851635 | RC0201DR-0710K2L | YAGEO | 0201 | Extended | 2531 | 0.0057 | R140 | 2026-11-15T01:35:29+00:00 |
| C270358 | 0201WMF2001TEE | UNI-ROYAL(Uniroyal Elec) | 0201 | Extended | 103169 | 0.0023 | R141 | 2026-11-15T01:35:31+00:00 |
| C43676 | 0402WGF3602TCE | UNI-ROYAL(Uniroyal Elec) | 0402 | Extended | 262954 | 0.0013 | R142 | 2026-11-15T01:33:30+00:00 |
| C270365 | 0201WMF1001TEE | UNI-ROYAL(Uniroyal Elec) | 0201 | Extended | 1919713 | 0.0011 | R162 | 2026-11-15T01:32:31+00:00 |
| C423439 | 0201WMF7323TEE | UNI-ROYAL(Uniroyal Elec) | 0201 | Extended | 11995 | 0.0013 | R170 | 2026-11-15T01:33:25+00:00 |
| C2691509 | 0201WMF1623TEE | UNI-ROYAL(Uniroyal Elec) | 0201 | Extended | 14900 | 0.0013 | R171 | 2026-11-15T01:32:17+00:00 |
| C166160 | RTT015362FTH | RALEC | 0201 | Extended | 38487 | 0.001 | R172 | 2026-11-16T19:41:57+00:00 |
| C473048 | 0201WMF1002TEE | UNI-ROYAL(Uniroyal Elec) | 0201 | Extended | 8353397 | 0.0013 | R311,R312,R313,R314,R511 | 2026-11-15T12:37:17+00:00 |
| C473560 | 0201WMF4703TEE | UNI-ROYAL(Uniroyal Elec) | 0201 | Extended | 31237 | 0.0012 | R317 | 2026-11-15T01:35:34+00:00 |
| C25076 | 0402WGF1000TCE | UNI-ROYAL(Uniroyal Elec) | 0402 | Basic | 10851593 | 0.0012 | R318,R319 | 2026-11-15T01:32:03+00:00 |
| C413063 | ERJ2RKF1000X | PANASONIC | 0402 | Extended | 319975 | 0.0052 | R507 | 2026-11-15T01:35:59+00:00 |
| C221907 | PTS840GKSMTRLFS | C&K | SMD-5P,3.55x3.5mm | Extended | 9802 | 0.2635 | SW1 | 2026-11-15T01:31:49+00:00 |
| C4371025 | INA236AIYBJR | Texas Instruments | DSBGA-8(0.7x1.5) | Extended | 94 | 1.8685 | U4,U5 | 2026-11-15T01:33:33+00:00 |
| C509405 | NRF52832-CIAA-R | Nordic Semicon | WLCSP-50(3x3.2) | Extended | 9325 | 3.8564 | U6 | 2026-11-15T01:33:58+00:00 |
| C727398 | SIP32431DNP3-T1GE4 | Vishay Intertech | TDFN-4-EP(1.2x1.6) | Extended | 10143 | 0.3093 | U12,U13 | 2026-11-15T01:34:44+00:00 |
| C5208201 | BQ25170DSGR | Texas Instruments | WSON-8(2x2) | Extended | 149 | 0.5809 | U15 | 2026-11-15T01:34:06+00:00 |
| C2867950 | TPS7A0230PDQNR | Texas Instruments | X2-SON-4-EP(1x1) | Extended | 419 | 0.5416 | U16 | 2026-11-15T01:32:57+00:00 |
| C5187176 | TXU0104RUTR | Texas Instruments | UQFN-12(1.7x2) | Extended | 2708 | 0.5482 | U17 | 2026-11-15T01:34:03+00:00 |
| C2863637 | TLV7031DCKR | Texas Instruments | SC-70-5 | Extended | 5100 | 0.5433 | U19,U20 | 2026-11-16T14:09:18+00:00 |
| C5217869 | TXU0101DRYR | Texas Instruments | SON-6(1x1.4) | Extended | 5672 | 0.3305 | U21 | 2026-11-15T01:34:11+00:00 |
| C398713 | SC-16S 32.768kHz 20PPM 12.5pF | Seiko | SMD1610-2P | Extended | 4453 | 0.2453 | X2 | 2026-11-15T01:33:08+00:00 |

## Tightest lines of the baseline (lowest orderable quantity / 10-board need)

| LCSC | Part | Stock | canPresale | Need (10 boards) | Ratio | Library |
|---|---|---|---|---|---|---|
| C23733 | CL05A475MP5NRNC | 624037 | -15705 | 20 | 0.0x | Basic |
| C5208201 | BQ25170DSGR | 149 | -67 | 10 | 0.0x | Extended |
| C4371025 | INA236AIYBJR | 94 | 48 | 20 | 2.4x | Extended |
| C5328762 | MAX86141ENP+T | 51 | 43 | 10 | 4.3x | Extended |
| C478155 | PMZ290UNE2YL | 2271 | 1682 | 140 | 12.0x | Extended |
| C5603826 | CT DBLP31.12 | 295 | 292 | 20 | 14.6x | Extended |
| C139059 | ADS1291IRSMR | 258 | 251 | 10 | 25.1x | Extended |
| C2867950 | TPS7A0230PDQNR | 419 | 392 | 10 | 39.2x | Extended |
| C861215 | RT0603BRD071RL | 2325 | 926 | 20 | 46.3x | Extended |
| C896422 | NSR0240MX2T5G | 604 | 604 | 10 | 60.4x | Extended |
| C506250 | BQ25570RGRR | 764 | 703 | 10 | 70.3x | Extended |
| C2803242 | TMP117MAIDRVR | 924 | 875 | 10 | 87.5x | Extended |

## Options, alternates and rejected parts (queried in the same run)

| LCSC | MPN | Library | Stock | Note |
|---|---|---|---|---|
| C17913 | 1206W4F120JT5E | Extended | 97688 | 1206W4F120JT5E 12 Ohm 1206 250 mW: R130 until gate-1 level 0 (now C17445 0805) |
| C441935 | ERJPA3F3303V | Extended | 11663 | ERJ-PA3F3303V 330 k 0603 anti-surge: R301-R306 until stage 2b; now 680 k C25822 (0603WAF6803T5E, 75 V working, 150 V overload; no anti-surge 680 k 0603 stocked at JLC 2026-11-15) |
| C427255 | ERJPA2F3303X | Extended | 5027 | ERJPA2F3303X 330 k 0402 anti-surge: NOT used (50 V limiting / 100 V overload against SIM-08's 110 V peak) |
| C2876046 | TLV7041DPWR | Extended | 0 | TLV7041DPWR open drain X2SON: would drive the Q14 gate without a FET; stock 0 |
| C702121 | TLV7021DPWR | Extended | 64 | TLV7021DPWR open drain X2SON, 5 uA: rejected (stock about 60, 5 uA load on the PV at the check) |
| C319184 | GRM033R61A225ME47D | Extended | 160946 | GRM033R61A225ME47D 2.2 uF 10 V 0201: candidate for the LDO capacitors once its DC-bias curve is read (not used) |
| C3682876 | ? | ? | ? | BQ25170JDSGR (JEITA): stock fallback for U15 only with the written 45-55 C exception (usbc lane 4.2) |
| C2876045 | TLV7031DPWR | Extended | 6923 | TLV7031DPWR X2SON-5: U19 / U20 until ECO3 (2026-11-16); centre VEE pad cannot be escaped under JLC rules (v3/eco3/ECO3.md) |
| C180352 | TLV3691IDCKR | Extended | 3407 | TLV3691IDCKR (0.9 V, 75 nA): rejected for the O-2 window: offset +-15 mV (25 C) / +-22 mV |
| C2867149 | ? | ? | ? | TLV7041DCKR SC-70-5 open drain: would replace Q17, larger; the X2SON TLV7041DPWR (C2876046) has stock 0 |
| C5244996 | SDM02M30CLP3-7B | Extended | 19975 | SDM02M30CLP3-7B: second source for D17 / D19 (Diodes, DFN1006-3 common cathode) |
| C240197 | WSB5546N-2/TR | Extended | 396284 | WSB5546N-2 40 V Schottky DFN1006-2: second source for D14 (EasyEDA land exists) |
| C5247957 | PMEG4002ELD,315 | Extended | 2688 | PMEG4002ELD: not used (no EasyEDA footprint, 404) |
| C547294 | ? | ? | ? | PMZB290UNE2YL SOT883B: higher-stock alternate for the 13 PMZ290UNE2YL (different land, needs its own review) |
