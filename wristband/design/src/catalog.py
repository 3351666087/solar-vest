"""Part catalogue for the SolarBand V2-B main board: key -> LCSC C-number, value, kind.

Every JLC-placed part has exactly one LCSC C-number, and its footprint is the EasyEDA footprint of that C-number
(tools/fetch_easyeda.py -> lib/easyeda.pretty/<C>_<package>.kicad_mod, reviewed copy lib/easyeda_rev.pretty), so the KiCad
footprint geometry and 0 deg are JLC's own (ARCHITECTURE section 10.1). Parts of kind 'pinmap' take their pins (numbers +
datasheet names) from pinmap/<C>.yaml. Copper-only items (pads, fiducials, net ties, antenna) use lib/solarband.pretty,
have no LCSC number and are never JLC-placed. Value rationale and sources: CHANGES.md, CALC.md, design_notes.md.
V2-B (REDESIGN_V2 rev 1, 2026-11-12): entries marked [V2] are new or changed against v1; v1 entries that the V2-B netlist no
longer uses are kept for the RADIO=qfn / CHARGE=contacts variants or marked (v1 only).
"""
CAT = {
    # ---------------- ICs and semiconductors: pins from pinmap/<C>.yaml ----------------
    "BQ25570":    dict(lcsc="C506250",  kind="pinmap", value="BQ25570RGRR"),
    "TPS61099":   dict(lcsc="C2842395", kind="pinmap", value="TPS61099DRVR"),
    "TPS7A0230":  dict(lcsc="C3747031", kind="pinmap", value="TPS7A0230PDBVR"),
    "INA236":     dict(lcsc="C5443912", kind="pinmap", value="INA236AIDDFR"),          # [FIX R-05] U4/U5 with SB_INA=ddf (stock fallback for the YBJ part)
    "NRF52832":   dict(lcsc="C77540",   kind="pinmap", value="nRF52832-QFAA-R"),
    "ADS1291":    dict(lcsc="C139059",  kind="pinmap", value="ADS1291IRSMR"),
    "MAX86141":   dict(lcsc="C5328762", kind="pinmap", value="MAX86141ENP+T"),
    "LIS2DW12":   dict(lcsc="C189624",  kind="pinmap", value="LIS2DW12TR"),
    "TMP117":     dict(lcsc="C2803242", kind="pinmap", value="TMP117MAIDRVR"),
    "MX25R1635F": dict(lcsc="C5687033", kind="pinmap", value="MX25R1635FZUIH0"),
    "SI2302":     dict(lcsc="C10488",   kind="pinmap", value="Si2302CDS-T1-GE3"),
    "BAS116":     dict(lcsc="C48502",   kind="pinmap", value="BAS116,215"),
    "TPD1E10B06": dict(lcsc="C48260",   kind="pinmap", value="TPD1E10B06DPYR"),
    "LED_G":      dict(lcsc="C965793",  kind="pinmap", value="XL-1005UGC green"),
    "VEMD8080":   dict(lcsc="C511402",  kind="pinmap", value="VEMD8080"),
    # Integrate 2026-11-12 (ARCHITECTURE changelog C-xx): drop-in / added parts
    "TPS7A2030":  dict(lcsc="C5220164", kind="pinmap", value="TPS7A2030PDQNR"),     # U3: low-noise AVDD_ECG LDO, X2SON 0.4 mm (SIM-06 ECG, SIM-14)
    "SIP32431":   dict(lcsc="C141606",  kind="pinmap", value="SiP32431DR3-T1GE3"),  # U12: VSTOR load switch (SIM-03a cold start)
    "BAS21":      dict(lcsc="C8661",    kind="pinmap", value="BAS21,215"),          # D1: 250 V cradle diode (SIM-08 C+)
    "MMBT3904":   dict(lcsc="C20526",   kind="pinmap", value="MMBT3904"),           # Q2/Q3: cradle detector (review power #1)
    "XTAL32M":    dict(lcsc="C718072",  kind="pinmap", value="32MHz 8pF X201632MKB4SI"),
    "XTAL32K":    dict(lcsc="C97604",   kind="pinmap", value="32.768kHz 7pF SC-32S"),
    # ---------------- inductors ----------------
    "L22u":      dict(lcsc="C2050114", kind="L", value="22uH 420mA VLS201610CX-220M-1"),
    "L10u":      dict(lcsc="C434843",  kind="L", value="10uH 550mA VLS201610CX-100M-1"),
    "L2u2":      dict(lcsc="C2041554", kind="L", value="2.2uH 1.31A VLS201610CX-2R2M-1"),
    "L10u_0603": dict(lcsc="C6807729", kind="L", value="10uH 0603 MPH160809S100MT"),
    "L15n":      dict(lcsc="C86059",   kind="L", value="15nH 0402 LQG15HS15NJ02D"),
    "L3n9":      dict(lcsc="C5452416", kind="L", value="3.9nH 0402 LQG15HS3N9B02D"),
    "L1n8":      dict(lcsc="C521065",  kind="L", value="1.8nH 0402 LQG15HS1N8B02D"),      # pi-net antenna-side shunt (SIM-10)
    "FB600":     dict(lcsc="C76886",   kind="L", value="600R@100MHz bead BLM15AX601SN1D"),  # C+ ESD bead (SIM-08)
    # ---------------- capacitors ----------------
    "C4u7_0603":     dict(lcsc="C19666",  kind="C", value="4.7uF 16V X5R 0603"),
    "C10u_0603":     dict(lcsc="C19702",  kind="C", value="10uF 10V X5R 0603"),
    "C22u_0603":     dict(lcsc="C59461",  kind="C", value="22uF 6.3V X5R 0603"),
    "C1u_X7R_0603":  dict(lcsc="C29936",  kind="C", value="1uF 25V X7R 0603"),
    "C10n_C0G_0603": dict(lcsc="C85973",  kind="C", value="10nF 50V C0G 0603"),
    "C4n7_C0G_0603": dict(lcsc="C85980",  kind="C", value="4.7nF 50V C0G 0603"),
    "C10n":   dict(lcsc="C15195",  kind="C", value="10nF 50V X7R 0402"),
    "C100n":  dict(lcsc="C1525",   kind="C", value="100nF 16V X7R 0402"),
    "C1u":    dict(lcsc="C52923",  kind="C", value="1uF 25V X5R 0402"),
    "C10u":   dict(lcsc="C15525",  kind="C", value="10uF 6.3V X5R 0402"),
    "C12p_2": dict(lcsc="C161527", kind="C", value="12pF 2% C0G 0402"),
    "C10p_2": dict(lcsc="C325459", kind="C", value="10pF 2% NP0 0402"),
    "C0p8":   dict(lcsc="C88902",  kind="C", value="0.8pF C0G 0402"),
    "C100p":  dict(lcsc="C1546",   kind="C", value="100pF 5% C0G 0402"),
    "C22p":   dict(lcsc="C1555",   kind="C", value="22pF 5% C0G 0402"),
    "C1n5":   dict(lcsc="C668348", kind="C", value="1.5nF 5% C0G 0402"),
    "C150p":  dict(lcsc="C76951",  kind="C", value="150pF 5% C0G 0402 GRM1555C1H151JA01D"),   # RLD CEXT (SIM-07)
    "C2p1":   dict(lcsc="C2220990", kind="C", value="2.1pF C0G 0402 GJM1555C1H2R1WB01D"),    # pi-net series (SIM-10)
    # ---------------- resistors ----------------
    "R1R_01":   dict(lcsc="C861215",  kind="R", value="1R 0.1% 25ppm 0603"),
    "R5M76":    dict(lcsc="C2766851", kind="R", value="5.76M 1% 0402"),
    "R7M32":    dict(lcsc="C423137",  kind="R", value="7.32M 1% 0402"),
    "R4M32":    dict(lcsc="C423169",  kind="R", value="4.32M 1% 0402"),
    "R7M50":    dict(lcsc="C423135",  kind="R", value="7.5M 1% 0402"),
    "R1M20":    dict(lcsc="C43675",   kind="R", value="1.2M 1% 0402"),
    "R8M66":    dict(lcsc="C407659",  kind="R", value="8.66M 1% 0402"),
    "R4M22":    dict(lcsc="C423173",  kind="R", value="4.22M 1% 0402"),
    "R3M3":     dict(lcsc="C270613",  kind="R", value="3.3M 1% 0402"),          # [FIX R-02, R-13] R126 EN_HOLD <- PV node
    "R1M":      dict(lcsc="C26083",   kind="R", value="1M 1% 0402"),
    "R10M":     dict(lcsc="C144806",  kind="R", value="10M 1% 0402 AC0402FR-0710ML"),   # [FIX R-05] was C26082 (canPresaleNumber <= 0); only R125 uses it now
    "R330k_PA": dict(lcsc="C441935",  kind="R", value="330k 1% 0603 ERJ-PA3 anti-surge"),
    "R100k":    dict(lcsc="C25741",   kind="R", value="100k 1% 0402"),
    "R10k":     dict(lcsc="C25744",   kind="R", value="10k 1% 0402"),
    "R4k7":     dict(lcsc="C25900",   kind="R", value="4.7k 1% 0402"),
    "R0":       dict(lcsc="C17168",   kind="R", value="0R 0402"),
    # BQ25570 dividers at the ROC minimum sum (11-15 MOhm, SLUSBH2G p.5): SIM-02 leak 0.584 -> 0.505 % (Integrate)
    "R3M74":    dict(lcsc="C477705",  kind="R", value="3.74M 1% 0402"),        # ROK1
    "R6M49":    dict(lcsc="C172111",  kind="R", value="6.49M 1% 0402"),        # ROK2
    "R1M05":    dict(lcsc="C423258",  kind="R", value="1.05M 1% 0402"),        # ROK3
    "R3M65":    dict(lcsc="C477700",  kind="R", value="3.65M 1% 0402"),        # ROUT2 (ROUT1 = 7.50 M R7M50)
    "R3M40":    dict(lcsc="C477696",  kind="R", value="3.4M 1% 0402"),         # R_FB1 -> VLED 4.40 V (SIM-06)
    "R470k":    dict(lcsc="C25790",   kind="R", value="470k 1% 0402"),         # RLD Rz (SIM-07) / NPN base-emitter
    "R47k":     dict(lcsc="C25792",   kind="R", value="47k 1% 0402"),          # [FIX R-17a] R129 VBAT_OK -> VOUT_EN (v1: cradle detector base resistor)
    "R22k":     dict(lcsc="C25768",   kind="R", value="22k 1% 0402"),          # cradle detector base resistor (Q2)
    "R220k":    dict(lcsc="C25767",   kind="R", value="220k 1% 0402"),         # ECG_PWR_EN series (U3 EN)
    "R220":     dict(lcsc="C25091",   kind="R", value="220R 1% 0402"),         # U2 input filter R_F (review power #3)
    # ---------------- copper-only items (no LCSC, never JLC-placed) ----------------
    "PAD_ELECTRODE": dict(lcsc=None, kind="pad1", value="ELECTRODE PAD 2.5x2.5", fp="solarband:Pad_Electrode_2.5x2.5mm"),
    "PAD_CRADLE":    dict(lcsc=None, kind="pad1", value="CRADLE PAD 2.0x2.5", fp="solarband:Pad_Contact_2.0x2.5mm"),
    "PAD_BATT":      dict(lcsc=None, kind="pad1", value="BATT PAD 1.5x2.5 (L6)", fp="solarband:Pad_Wire_1.5x2.5mm"),
    "PAD_PVWIRE":    dict(lcsc=None, kind="pad1", value="PV WIRE PAD 1.5x2.0 (L6)", fp="solarband:Pad_Wire_1.5x2.0mm"),
    "TEST_ARRAY":    dict(lcsc=None, kind="testarray", value="POGO 2x5 P1.27 (L6)", fp="solarband:TestPad_2x5_P1.27mm_D0.9mm"),
    "FIDUCIAL":      dict(lcsc=None, kind="fid", value="FIDUCIAL 1.0/2.0", fp="solarband:Fiducial_1.0mm_Mask2.0mm"),
    "NETTIE":        dict(lcsc=None, kind="nettie", value="NetTie", fp="solarband:NetTie_2_SMD_0.3mm"),
    "ANT_IFA":       dict(lcsc=None, kind="antenna", value="Printed meander IFA (TI AN043) L6", fp="solarband:ANT_IFA_AN043_placeholder"),
    # PV board
    "PV_KXOB121":    dict(lcsc=None, kind="pvcell", value="KXOB121K04TF", fp="pv:KXOB121K04TF"),
    "PV_KXOB25":     dict(lcsc=None, kind="pvcell", value="KXOB25-03X4TF", fp="pv:KXOB25-03X4TF"),
    "PV_TP":         dict(lcsc=None, kind="pad1", value="TEST PAD 1.5", fp="pv:TestPad_D1.5mm"),
    "PV_JUMPER":     dict(lcsc=None, kind="jumper", value="SOLDER JUMPER (open)", fp="pv:SolderJumper_2_Open_1.0x1.5mm"),
    "PV_WIREPAD":    dict(lcsc=None, kind="pad1", value="LEAD PAD 0.6 drill", fp="pv:WirePad_TH_D1.6mm_Drill0.6mm"),

    # ================= V2-B additions (REDESIGN_V2 rev 1 section 3, 5.8; sources per part in CHANGES.md) =================
    # ---- ICs / semiconductors with pin maps ----
    "NRF52832_CIAA": dict(lcsc="C509405",  kind="pinmap", value="nRF52832-CIAA-R"),          # [V2] U6 WLCSP-50 (RADIO=wlcsp)
    "INA236_YBJ":    dict(lcsc="C4371025", kind="pinmap", value="INA236AIYBJR"),             # [V2] U4/U5 DSBGA-8
    "XB5358D0":      dict(lcsc="C2760012", kind="pinmap", value="XB5358D0"),                 # [V2] U14 cell protector
    "SIP32431DNP3":  dict(lcsc="C727398",  kind="pinmap", value="SiP32431DNP3-T1GE4"),       # [V2] U12, U13 TDFN4
    "PMZ290UNE2":    dict(lcsc="C478155",  kind="pinmap", value="PMZ290UNE2YL"),             # [V2] Q1, Q4, Q5, Q6 DFN1006-3
    "EMX1":          dict(lcsc="C253326",  kind="pinmap", value="EMX1T2R"),                  # [V2] Q2 dual NPN (CHARGE=contacts)
    "BAS521":        dict(lcsc="C130414",  kind="pinmap", value="BAS521,115"),               # [V2] D9 (hold diode), D1 (CHARGE=contacts)
    "LED_HRM":       dict(lcsc="C5603826", kind="pinmap", value="CT DBLP31.12 green"),       # [V2] D3, D4 heart-rate LED
    "LED_SIDE_RED":  dict(lcsc="C598214",  kind="pinmap", value="KA-2810ASURSK hyper-red right-angle"),  # [FIX R-06] D10 skin-hot warning: 150 mcd min / 300 typ at 20 mA (was LTST-S270KRKT C125114, 18 / 54 mcd)
    "XTAL32K_1610":  dict(lcsc="C398713",  kind="pinmap", value="32.768kHz 12.5pF SC-16S"),  # [V2] X2
    "SPRING":        dict(lcsc="C2826535", kind="spring", value="BW0036BG spring finger 3.0x1.0x1.4"),    # [FIX R-04] E3 (+C+/C-, lid feed): SMT-placed at JLC, working height 1.00 mm (was BW0025BG C2826523 = wave / manual at JLC)
    # ---- passives ----
    "C22u_0402":     dict(lcsc="C105226",  kind="C", value="22uF 6.3V X5R 0402 CL05A226MQ5QUNC"),  # [V2] COUT x5
    "C4u7_0402":     dict(lcsc="C23733",   kind="C", value="4.7uF 10V X5R 0402"),            # [V2] C209 (nRF VDD); [FIX R-02] C121 (EN hold)
    "C20p":          dict(lcsc="C1554",    kind="C", value="20pF 5% C0G 0402"),              # [V2] LFXO load for the 12.5 pF crystal
    "C12p_0201":     dict(lcsc="C384960",  kind="C", value="12pF 1% C0G 0201 GRM0335C1H120FA01D"),   # [V2] Nordic CIAA C1, C2
    "C1p0_0201":     dict(lcsc="C237514",  kind="C", value="1.0pF +-0.1pF C0G 0201 GJM0335C1H1R0BB01D"),  # [V2] Nordic CIAA C3
    "C100n_0201":    dict(lcsc="C7393837", kind="C", value="100nF 10V X7R 0201"),            # [V2] Nordic CIAA C4, C5
    "C100p_0201":    dict(lcsc="C76922",   kind="C", value="100pF 5% C0G 0201 GRM0335C1H101JA01D"),  # [V2] Nordic CIAA C6, C7
    "L3n3_0201":     dict(lcsc="C98045",   kind="L", value="3.3nH +-0.1nH 0201 LQP03TN3N3B02D"),      # [V2] Nordic CIAA L1
    "R18R":          dict(lcsc="C25084",   kind="R", value="18R 1% 0402"),                   # (not used after the review fix: R_LIM is an 0603 part, R-11 / R-18)
    "R22R_0603":     dict(lcsc="C23345",   kind="R", value="22R 1% 0603 100mW"),             # [FIX R-18, R-11] R130 R_LIM, baseline value (SB_RLIM=22)
    "R18R_0603":     dict(lcsc="C22830",   kind="R", value="18R 1% 0603 100mW"),             # [FIX R-11] R130 with SB_RLIM=18 (REDESIGN 5.6 value)
    "R100R_0603":    dict(lcsc="C22775",   kind="R", value="100R 1% 0603 100mW"),            # [FIX R-01, R-06] R132 protector R1, R507 warning LED
    "R3R3":          dict(lcsc="C270612",  kind="R", value="3.3R 1% 0402"),                  # [V2] R117 LED supply (P-6)
    "R100R":         dict(lcsc="C25076",   kind="R", value="100R 1% 0402"),                  # [V2] electrode dot-loop links R318, R319; [FIX R-02] R133 VDD discharge
    "R1k":           dict(lcsc="C11702",   kind="R", value="1k 1% 0402"),                    # [V2] cradle detector base (G-6, contacts)
    "R4M02":         dict(lcsc="C423177",  kind="R", value="4.02M 1% 0402"),                 # [V2] ROUT2 (G-5)
    "R3M92":         dict(lcsc="C423179",  kind="R", value="3.92M 1% 0402"),                 # [V2] ROK1
    "R6M81":         dict(lcsc="C477775",  kind="R", value="6.81M 1% 0402"),                 # [V2] ROK2
    "R294k":         dict(lcsc="C159047",  kind="R", value="294k 1% 0402"),                  # [V2] ROK3 (VBAT_OK rising 3.40 V)
    # ---- generic passives in 0201 (build option SB_PASSIVES=0201 = gate-1 fallback "0201 for all generic passives", REDESIGN 8.2) ----
    "R1M_0201":      dict(lcsc="C295786",  kind="R", value="1M 1% 0201"),
    "R100k_0201":    dict(lcsc="C270364",  kind="R", value="100k 1% 0201"),
    "R10k_0201":     dict(lcsc="C473048",  kind="R", value="10k 1% 0201"),
    "R4k7_0201":     dict(lcsc="C270346",  kind="R", value="4.7k 1% 0201"),
    "C10n_0201":     dict(lcsc="C285010",  kind="C", value="10nF 25V X7R 0201"),
    # ---- copper-only items of the V2-B board (no LCSC, never JLC-placed) ----
    "PAD_DOT":       dict(lcsc=None, kind="pad1", value="PLATE DOT PAD 2.0 ENIG (B.Cu)", fp="solarband:Pad_PlateDot_D2.0mm"),
    "PAD_CELLTAB":   dict(lcsc=None, kind="pad1", value="CELL TAB PAD 3.0x4.0", fp="solarband:Pad_CellTab_3.0x4.0mm"),
    "PAD_NTC":       dict(lcsc=None, kind="pad1", value="NTC LEAD PAD 1.5x2.2", fp="solarband:Pad_Wire_1.5x2.2mm"),
    "PAD_LIDTAIL":   dict(lcsc=None, kind="lidtail", value="LID FLEX TAIL 3 x 1.2x3.0 P2.0", fp="solarband:Pad_LidTail_3x1.2x3.0_P2.0mm"),
    "TP_EOL":        dict(lcsc=None, kind="pad1", value="EOL TEST PAD 1.0", fp="solarband:TestPad_D1.0mm"),
    "SWD_GROUP":     dict(lcsc=None, kind="swd6", value="SWD/RESET GROUP 2x3 P1.27", fp="solarband:TestPad_2x3_P1.27mm_D0.9mm"),
    "ANT_PRINTED":   dict(lcsc=None, kind="antenna", value="Printed radiator (gate 3a) - placeholder", fp="solarband:ANT_PRINTED_V2_placeholder"),

    # ================= V3-F additions (v3/decide/BASELINE.md section 5.1; sources per part in CHANGES_V3F.md, numbers in CALC_V3F.md) =================
    # ---- ICs / semiconductors with pin maps (pinmap/<C>.yaml from tools/pinmap_data_v3.py) ----
    "BQ25170":       dict(lcsc="C5208201", kind="pinmap", value="BQ25170DSGR"),        # [V3F] U15 linear charger 4.10 V, fed from the top-rim contacts
    "TPS7A0230_DQN": dict(lcsc="C2867950", kind="pinmap", value="TPS7A0230PDQNR"),     # [V3F] U16 3.0 V display rail (X2SON-4, same package as U3)
    "TXU0104":       dict(lcsc="C5187176", kind="pinmap", value="TXU0104RUTR"),        # [V3F] U17 4-bit translator SCLK / SI / SCS / EXTCOMIN
    "TXU0101":       dict(lcsc="C5217869", kind="pinmap", value="TXU0101DRYR"),        # [V3F] U21 1-bit translator for DISP (spec edge <= 50 ns, sequence p.19-21)
    "BAV70M":        dict(lcsc="C549313",  kind="pinmap", value="BAV70M,315",          # [V3F] D12 common-cathode pair: VBUS wake + button wake into EN_HOLD
                          fp="easyeda_rev:C549313_SOT883_BAV70M_land_of_C549275"),     # EasyEDA has no footprint for C549313 (404, 2026-11-13): Nexperia SOT883 land, see footprint_audit
    "BAT54CM":       dict(lcsc="C549275",  kind="pinmap", value="BAT54CM,315"),        # [V3F] D17 motor flyback (both halves), D19 O-2 supply / MCU-bias OR
    "ESD761":        dict(lcsc="C20345399", kind="pinmap", value="ESD761DPYR"),        # [V3F] D13 contact ESD (bidirectional, 24 V)
    "NSR0240":       dict(lcsc="C896422",  kind="pinmap", value="NSR0240MX2T5G"),      # [V3F] D14 40 V Schottky in VBUS: reverse-attach block (BQ25170 IN abs. max -0.3 V)
    "PTS840":        dict(lcsc="C221907",  kind="pinmap", value="PTS840GKSMTRLFS"),    # [V3F] SW1 side-actuated tact switch (C&K B-41); [G1 L0] the reviewed footprint copy carries C&K's recommended land    # [V3F] SW1 side-actuated tact switch (C&K B-41: "Microminiature SMT Side Actuated")
    "TLV7031":       dict(lcsc="C2863637", kind="pinmap", value="TLV7031DCKR"),        # [V3F] U19, U20 O-2 window comparators; [ECO3 2026-11-16] SC70-5 (DCK) instead of X2SON-5 C2876045: the X2SON centre VEE pad cannot be escaped (v3/eco3/ECO3.md)
    "PMZ350UPE":     dict(lcsc="C478207",  kind="pinmap", value="PMZ350UPEYL"),        # [V3F] Q14 O-2 series PV switch, Q18 O-2 supply gate (P-channel, SOT883)
    # ---- passives ----
    "R12R_1206":     dict(lcsc="C17913",   kind="R", value="12R 1% 1206 250mW 1206W4F120JT5E"),   # [V3F] R130 R_LIM, locked to a >= 66 mAh pack (BASELINE 11.5)
    "R2k":           dict(lcsc="C4109",    kind="R", value="2k 1% 0402"),                 # [V3F] R141 ISET RC (TI SLUAAG9 p.7)
    "C4n7":          dict(lcsc="C1538",    kind="C", value="4.7nF 50V X7R 0402"),         # [V3F] C132 ISET RC
    "R36k":          dict(lcsc="C43676",   kind="R", value="36k 1% 0402"),                # [V3F] R142 VSET 4.10 V (BQ25170 Table 7-1)
    "R220R_0201":    dict(lcsc="C270356",  kind="R", value="220R 1% 0201 0201WMF2200TEE"),  # [V3F] first R160 value (too little current at VSTOR 3.31 V: CALC_V3F 6)
    "R100R_0201":    dict(lcsc="C270366",  kind="R", value="100R 1% 0201 0201WMF1000TEE"),  # [V3F] R160 front-light LED resistor (CALC_V3F section 6)
    "R1k_0201":      dict(lcsc="C270365",  kind="R", value="1k 1% 0201 0201WMF1001TEE"),    # [V3F] R162 motor gate series resistor
    # ---- stage 1 (2026-11-14): review fixes D-1 (O-2 heartbeat) and D-8 (RISET) ----
    "C220p_0201":    dict(lcsc="C161418",  kind="C", value="220pF 5% C0G 0201 GRM0335C1H221JA01D"),  # [S1 D-1] C175 heartbeat coupling CHG_DIS -> O2_HB (JLC 2026-11-14: 34,128 / 24,048)
    "R10k2":         dict(lcsc="C11660",   kind="R", value="10.2k 1% 0402 0402WGF1022TCE"),          # [S1 D-8] R140 RISET 10.2 k: <= 0.5 C at 66 mAh, KISET max, R -1 % (JLC 2026-11-14: 60,305 / 46,407)
    # ---- copper-only items of the V3-F board (no LCSC, never JLC-placed) ----
    "PAD_ROOT":      dict(lcsc=None, kind="pad1", value="ROOT ENTRY PAD 1.0x4.0", fp="solarband:Pad_RootEntry_1.0x4.0mm"),
    "FPC_DISP":      dict(lcsc=None, kind="fpc10", value="LS011B7DH03 FPC LAND 10P P0.5 + KEY", fp="solarband:FPC_Solder_10P_P0.5mm_Key"),
    "TAIL_FL":       dict(lcsc=None, kind="tail2", value="FRONT-LIGHT TAIL 2 PADS KEYED", fp="solarband:Pad_Tail2_Keyed_FL"),
    "PADS_ERM":      dict(lcsc=None, kind="tail2", value="ERM WIRE PADS 2 x 1.0x1.5", fp="solarband:Pad_Wire2_ERM_1.0x1.5mm"),
    # ---- O-2 reference chain (calc/o2_inhibit.py picks the values; 0201 UNI-ROYAL with JLC stock 2026-11-13) ----
    "R732k_0201":    dict(lcsc="C423439",  kind="R", value="732k 1% 0201 0201WMF7323TEE"),   # [V3F] R170 O-2 chain top
    "R162k_0201":    dict(lcsc="C2691509", kind="R", value="162k 1% 0201 0201WMF1623TEE"),   # [V3F] R171 O-2 chain middle (cold tap above it)
    "R52k3_0201":    dict(lcsc="C473632",  kind="R", value="52.3k 1% 0201 0201WMF5232TEE"),  # [V3F] R172 O-2 chain bottom (hot tap above it)
    # ================= Gate-1 level 0 (2026-11-15, v3/g1/dense/DENSE.md): smaller cases where the rating allows; JLC records in data/jlc =================
    # ---- 0402 -> 0201 resistors (UNI-ROYAL 0201WMF: 1/20 W, 25 V working, jumper 0.5 A; YAGEO RC0201: 1/20 W, 25 V) ----
    "R10M_0201":     dict(lcsc="C423797",  kind="R", value="10M 1% 0201 0201WMF1005TEE"),        # [L0] R108, R125, R131, R174 (pulls: leakage across the part only strengthens the pull); DNP R307-R309
    "R220k_0201":    dict(lcsc="C473458",  kind="R", value="220k 1% 0201 0201WMF2203TEE"),       # [L0] R123, R143
    "R3M3_0201":     dict(lcsc="C423582",  kind="R", value="3.3M 1% 0201 0201WMF3304TEE"),       # [L0] R126
    "R47k_0201":     dict(lcsc="C270345",  kind="R", value="47k 1% 0201 0201WMF4702TEE"),        # [L0] R129
    "R10k2_0201":    dict(lcsc="C851635",  kind="R", value="10.2k 0.5% 0201 RC0201DR-0710K2L"),  # [L0] R140 RISET (0.5 %: the 0.495 C bound was computed at -1 %)
    "R2k_0201":      dict(lcsc="C270358",  kind="R", value="2k 1% 0201 0201WMF2001TEE"),         # [L0] R141
    "R470k_0201":    dict(lcsc="C473560",  kind="R", value="470k 1% 0201 0201WMF4703TEE"),       # [L0] R317
    "R0_0201":       dict(lcsc="C473473",  kind="R", value="0R 0201 0201WMF0000TEE"),            # [L0] FB1-FB6 (jumper < 50 mOhm, rated 0.5 A, overload 1 A)
    # ---- 0402 -> 0201 capacitors ----
    "C1u_0201":      dict(lcsc="C76935",   kind="C", value="1uF 10V X5R 0201 GRM033R61A105ME44D"),   # [L0] C119, C122, C313 (bulk on the same net, or a timer)
    "C4n7_0201":     dict(lcsc="C309454",  kind="C", value="4.7nF 25V X7R 0201 CC0201KRX7R8BB472"), # [L0] C132 ISET RC
    "C20p_0201":     dict(lcsc="C76923",   kind="C", value="20pF 5% C0G 0201 GRM0335C1H200JA01D"),   # [L0] C211, C212 LFXO load
    "C150p_0201":    dict(lcsc="C161408",  kind="C", value="150pF 5% C0G 0201 GRM0335C1H151JA01D"),  # [L0] C304 RLD CEXT
    "C22p_0201":     dict(lcsc="C76924",   kind="C", value="22pF 5% C0G 0201 GRM0335C1H220JA01D"),   # [L0] DNP lands C301, C302
    "C1n_0201":      dict(lcsc="C161371",  kind="C", value="1nF 5% C0G 0201 GRM0335C1E102JA01D"),    # [L0] C175 heartbeat coupling of the dense O-2
    # ---- 0603 -> 0402, 1206 -> 0805 ----
    "C10n_C0G_0402": dict(lcsc="C3855387", kind="C", value="10nF 25V C0G 0402 GRM1555C1E103JE01D"),  # [L0] C104 CREF
    "C4n7_C0G_0402": dict(lcsc="C1518204", kind="C", value="4.7nF 50V C0G 0402 GRM1555C1H472JE01D"), # [L0] C305, C306 PGA filter
    "R100R_0402_0W1": dict(lcsc="C413063", kind="R", value="100R 1% 0402 100mW ERJ2RKF1000X"),       # [L0] R507 warning-LED series (<= 65 mW)
    "R12R_0805":     dict(lcsc="C17445",   kind="R", value="12R 1% 0805 125mW 0805W8F120JT5E"),      # [L0] R130 R_LIM: <= 52 mW = 42 % of the rating
    # ---- trimmed copper-only lands (tools/gen_footprints.py; tail assumptions in DENSE.md section 3) ----
    "PAD_ROOT_T":    dict(lcsc=None, kind="pad1", value="ROOT ENTRY PAD 1.0x2.5", fp="solarband:Pad_RootEntry_1.0x2.5mm"),
    "PAD_LIDTAIL_T": dict(lcsc=None, kind="lidtail", value="LID FLEX TAIL 3 x 1.0x2.0 P1.5", fp="solarband:Pad_LidTail_3x1.0x2.0_P1.5mm"),
    "ZIF_FH34_10":   dict(lcsc="C324723", kind="pinmap", value="FH34SRJ-10S-0.5SH(50)"),   # [S2a] J13 top-contact ZIF, Hirose FH34 p.6 / p.8 (lead decision c)
    "FPC_BRIDGE":    dict(lcsc=None, kind="fpc10b", value="DISPLAY BRIDGE-FLEX LAND 10P P0.5", fp="solarband:FPC_Bridge_10P_P0.5mm"),
    # ================= Stage 2b ECO (2026-11-15, v3/stage2b/eco/ECO.md; LEAD_NOTES 2b, 2d) =================
    "R53k6_0201":    dict(lcsc="C166160",  kind="R", value="53.6k 1% 0201 RTT015362FTH"),        # [S2b 2b] R172 O-2 chain bottom: hot stop <= 45.0 C down to 1.30 V; [F R-172] was C423488 0201WMF5362TEE (stock 0 on 2026-11-16), RALEC C166160 same value/0201/1 %, EasyEDA pads identical
    "R383k":         dict(lcsc="C45993",   kind="R", value="383k 1% 0402 0402WGF3833TCE"),       # [S2b 2b] R105 ROK3: VBAT_OK hysteresis 118 mV
    "R680k_0603":    dict(lcsc="C25822",   kind="R", value="680k 1% 0603 75V 0603WAF6803T5E"),   # [S2b E-3] R301-R306 electrode chains 2 x 680 k (no anti-surge 680 k 0603 stocked at JLC 2026-11-15)
    "PMEG10020AELR": dict(lcsc="C6736531", kind="pinmap", value="PMEG10020AELR-QX"),         # [S2b E-4] D14 100 V Schottky, SOD123W, Nexperia land (review_footprints SET_PAD)
    # [S2c] lid antenna L1 (v3/sim/rf/lid) and ruling F-8
    "LQW15AN9N0":    dict(lcsc="C6652901", kind="L", value="9.0nH 0402 LQW15AN9N0G80D"),    # C215 pi-net series (wire-wound, Murata land via review_footprints SET_PAD)
    "LQW15AN6N2":    dict(lcsc="C668465",  kind="L", value="6.2nH 0402 LQW15AN6N2B80D"),    # L204 pi-net antenna-side shunt (wire-wound, Murata land)
    # [F] final re-tune on the closed board (v3/sim/rf/final/RF_FINAL.md, 2026-11-16): C215 7.6 nH, L204 4.3 nH, C213 DNP
    "LQW15AN7N6":    dict(lcsc="C2048575", kind="L", value="7.6nH 0402 LQW15AN7N6G80D"),    # [F] C215 pi-net series (Murata land)
    "LQW15AN4N3":    dict(lcsc="C471381",  kind="L", value="4.3nH 0402 LQW15AN4N3B80D"),    # [F] L204 pi-net antenna-side shunt (Murata land)
    "SPRING_BW0019": dict(lcsc="C2826518", kind="spring", value="BW0020AG spring finger 3.5x1.5x3.0",
                          fp="easyeda_rev:C2826516_ANT-SMD_L3.5-W1.5-H3.8"),   # J40 lid-antenna feed finger (on AE1's FEED copper); [S2d J-1] BW0020AG-L3.5W1.5H3.0 (C2826518), same land as BW0019BG
    "ANT_LID_L1":    dict(lcsc=None, kind="antenna", value="lid strip L1 feed", fp="solarband:AE1_lid_L1"),   # AE1 copper + keep-out of v3/sim/rf/lid/export
    "CJBA7002K":     dict(lcsc="C504101",  kind="pinmap", value="CJBA7002K"),                 # [F-8] Q20 60 V N-FET, DFN1006-3 (copper = C478155 land turned 180 deg)
}
