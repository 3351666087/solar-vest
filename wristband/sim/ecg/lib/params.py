"""Every number used by the ECG simulations, with its provenance.

Tags:  V = verified against a vendor datasheet/JLC record (document + page given)
       A = taken from ARCHITECTURE.md (frozen design input)
       E = engineering estimate (reason given); these are what the bench must confirm
Datasheets are the copies cached under wristband/cache/datasheets (sha256 in refs/*.pages.txt)."""

P = {}


def p(name, value, tag, src):
    P[name] = dict(value=value, tag=tag, src=src)
    return value


# ----------------------------------------------------------------------------------------- ADS1291 (SBAS502C)
VREF = p("ads_vref", 2.42, "V", "ADS1291 SBAS502C p9: internal reference 2.42 V (VREF_4V = 0)")
AVDD = p("avdd", 3.0, "A", "ARCHITECTURE.md D10/§4.1: AVDD_ECG = 3.0 V from TPS7A0230")
p("ads_fs", "±VREF/gain", "V", "SBAS502C p7: full-scale differential input ±VREF/gain")
CIN_ADS = p("ads_cin", 20e-12, "V", "SBAS502C p7: input capacitance 20 pF (modelled per pin to AVSS)")
RIN_ADS = p("ads_rin", 1000e6, "V", "SBAS502C p7: DC input impedance 1000 MΩ, no lead-off current source")
RIN_ADS_LOFF = p("ads_rin_loff", 500e6, "V", "SBAS502C p7: 500 MΩ with nA lead-off current source enabled")
IB_25 = p("ads_ib_25C", 200e-12, "V", "SBAS502C p7: input bias current ±200 pA at 25 °C (chop 8 kHz)")
IB_HOT = p("ads_ib_fullT", 1e-9, "V", "SBAS502C p7: ±1 nA over −40…+85 °C")
p("ads_cmrr", 120, "V", "SBAS502C p7: CMRR 105 min / 120 typ dB at 50/60 Hz")
CMRR_MIN = p("ads_cmrr_min", 105, "V", "SBAS502C p7: CMRR 105 dB min at 50/60 Hz (added to the external CM->DM as a worst-case term)")
p("ads_cfilter", 4.7e-9, "V", "SBAS502C p23 §8.3.4: CFILTER 4.7 nF across PGA1P/PGA1N (CP1/CP2) required, >= 4 nF; not in ARCH §3.3 BOM")
p("ads_emi_filter", 3e6, "V", "SBAS502C p19 §8.3.1: internal input RC EMI filter, -3 dB ≈ 3 MHz")
PSRR_SPEC = p("ads_psrr_spec", 90, "V", "SBAS502C p7: PSRR 90 dB typ at 50/60 Hz (no min)")
RLD_GBW = p("rld_gbw", 100e3, "V", "SBAS502C p8: RLD amplifier GBP 100 kHz (50 kΩ‖10 pF, gain 1)")
p("rld_sr", 0.07e6, "V", "SBAS502C p8: slew rate 0.07 V/µs")
RLD_ISC = p("rld_isc", 1.1e-3, "V", "SBAS502C p8: RLD short-circuit current 1.1 mA")
p("rld_cmir", (0.3, AVDD - 0.3), "V", "SBAS502C p8: RLD common-mode input range AVSS+0.3 … AVDD−0.3")
R_RLD_SUM = p("rld_sum_r", 400e3, "V", "SBAS502C p36 Fig 40: 400 kΩ from each PGA output (RLD1P, RLD1N) to RLDINV")
p("rld_rext_cext_typ", (1e6, 1.5e-9), "V", "SBAS502C p36 Fig 40: REXT 1 MΩ, CEXT 1.5 nF 'typical values'")
p("rld_ref_int", "(AVDD+AVSS)/2", "V", "SBAS502C p36 Fig 40 + p61 RESP2.RLDREF_INT: internal (AVDD+AVSS)/2 or external RLDIN/RLDREF pin")
RLD_A0 = p("rld_a0", 1e5, "E", "RLD open-loop DC gain not specified; 100 dB assumed (sensitivity 80 dB run)")
PGA_CM_BW = p("pga_cm_bw", 200e3, "E", "PGA common-mode (follower) bandwidth not specified; 200 kHz assumed (sensitivity 50 kHz run)")
RLD_ROUT = p("rld_rout", 100.0, "E", "RLD output resistance not specified; 100 Ω assumed (irrelevant against 660 kΩ load)")
ILOFF = p("ileadoff", {"00": 6e-9, "01": 22e-9, "10": 6e-6, "11": 22e-6}, "V",
          "SBAS502C p8 and p54 LOFF[3:2]: 6 nA, 22 nA, 6 µA, 22 µA; accuracy ±10 % (p8)")
ILOFF_TOL = p("ileadoff_tol", 0.10, "V", "SBAS502C p8: current accuracy ±10 %")
p("loff_comp_th", {"pos": [0.95, 0.925, 0.90, 0.875, 0.85, 0.80, 0.75, 0.70],
                   "neg": [0.05, 0.075, 0.10, 0.125, 0.15, 0.20, 0.25, 0.30]}, "V",
  "SBAS502C p54 LOFF[7:5] COMP_TH: positive side 95 %…70 %, negative side 5 %…30 % (of AVDD)")
p("ads_abs_ain", (-0.3, AVDD + 0.3), "V", "SBAS502C p6: analog input to AVSS −0.3 … AVDD+0.3 V")
ADS_IIN_CONT = p("ads_abs_iin_cont", 10e-3, "V", "SBAS502C p6: input current ±10 mA continuous")
ADS_IIN_MOM = p("ads_abs_iin_mom", 100e-3, "V", "SBAS502C p6: input current ±100 mA momentary")
p("ads_cm_eq5", "AVDD−0.2−G·Vd/2 > CM > AVSS+0.2+G·Vd/2", "V", "SBAS502C p24 Eq. 5 input common-mode range")
NOISE_TAB = p("ads_noise_500sps", {3: (1.3, 7.7), 4: (1.1, 6.6), 6: (0.9, 5.6), 8: (0.8, 5.5)}, "V",
              "SBAS502C p15 Tables 1-2, p16 Table 3: input-referred noise µVrms/µVpp, 3 V AVDD, 500 SPS (131 Hz BW)")
p("ads_psrr_curve", "refs/curves.json ads1291_psrr_g*", "V", "SBAS502C p13 Fig 8 PSRR vs frequency (digitised)")

# ----------------------------------------------------------------------------------------- TPS7A0230 (SBVS277C)
p("ldo_psrr_curve", "refs/curves.json tps7a02_psrr_0mA/1mA", "V", "SBVS277C p15 Fig 6-43 (VOUT 1.8 V, VIN 2.8 V, COUT 1 µF)")
p("ldo_noise_curve", "refs/curves.json tps7a02_noise_100uA/1mA", "V", "SBVS277C p15 Fig 6-48 (VOUT 1.8 V)")
LDO_NOISE_VSCALE = p("ldo_noise_vscale", 3.0 / 1.8, "E",
                     "noise ∝ VOUT: SBVS277C p15 Fig 6-47 gives 269.5 µVrms @1.8 V vs 710 µVrms @5.0 V (ratio 2.63 for 2.78×VOUT)")
LDO_NOISE_DIGCAL = p("ldo_noise_digcal", 1.05, "E",
                     "digitised density integrates to 95-97 % of TI's printed RMS (Fig 6-48); scaled up by 1/0.954")
LDO_PSRR_LOWHEAD = p("ldo_psrr_headroom_derate_db", 6.0, "E",
                     "VSTOR ≥ 3.40 V in ECG mode (firmware ladder §4.2) gives ≥ 0.40 V headroom vs 1.0 V in Fig 6-43; "
                     "Fig 6-44/45 show ≈2-5 dB loss at 0.5 V headroom; 6 dB taken")

# ----------------------------------------------------------------------------------------- BQ25570 (SLUSBH2G)
ICHG_CBC = p("bq_ichg_cbc", (0.230, 0.285), "V", "SLUSBH2G p6: charger cycle-by-cycle current limit 230 typ / 285 max mA")
RDS_BAT = p("bq_rds_bat", (0.95, 1.50), "V", "SLUSBH2G p6: VBAT–VSTOR switch 0.95 typ / 1.50 max Ω")
p("bq_mppt", (16.0, 0.256), "V", "SLUSBH2G p7: VOC sample every 16 s, 256 ms settling with charger off")
p("bq_buck_ripple", 30e-3, "V", "SLUSBH2G p8: buck output ripple 30 mVpp typ (VSTOR 4.2 V, 1 mA, COUT 22 µF); Fig 19/20 p12: 12-40 mVpp")
p("bq_buck_fsw", "2-100 kHz major", "V", "SLUSBH2G p12 Fig 17/18: buck major switching frequency vs load")
BUCK_CBC = p("bq_buck_cbc", 0.185, "V", "SLUSBH2G p8: buck cycle-by-cycle limit 160/185/205 mA")
L1_BOOST = p("l1", 22e-6, "A", "ARCHITECTURE.md §3.1 L1 22 µH (TDK VLS201610CX-220M-1)")
CSTOR = p("cstor", 10e-6, "A", "ARCHITECTURE.md §3.1 CSTOR 10 µF 0603 X5R 10 V (C19702)")
CBAT = p("cbat", 22e-6, "A", "ARCHITECTURE.md §3.1 CBAT 22 µF 0603 X5R 6.3 V (C59461)")
MLCC_DERATE = p("mlcc_dcbias", 0.5, "E", "0603 X5R 10-22 µF at 3.7 V DC bias keeps ≈50 % of nominal (typical Samsung curves)")
RSH2 = p("rsh2", 1.0, "A", "ARCHITECTURE.md D9: 1.00 Ω shunt in the battery path")
R_CELL = p("r_cell", (1.0, 2.0), "E", "60 mAh LiPo DC resistance ≈1 Ω, 2 Ω cold/low SoC (no EEMB impedance figure available)")
R_PCM = p("r_pcm", 0.06, "E", "DW01 + dual-FET PCM ≈ 2×25 mΩ + traces")
I_CHG_SUN = p("i_chg_sun", 24.7e-3, "A", "ARCHITECTURE.md §4.6: full sun 24.7 mA into the cell (50 klx: 11.1 mA)")
I_CHG_1KLX = p("i_chg_1klx", 219e-6 / 3.7, "A", "ARCHITECTURE.md §4.6: 1000 lx → 219 µW into the battery")
V_MPP = p("v_mpp", 2.23, "A", "ARCHITECTURE.md §2: PV Vmp 2.23 V")

# ----------------------------------------------------------------------------------------- system loads in an ECG session
I_BLE_PEAK = p("i_ble_peak", 7.0e-3, "E",
               "nRF52832 radio TX 0 dBm / RX with DC/DC ≈ 5-7 mA at the 1.8 V rail incl. CPU; 7 mA taken")
T_BLE_EVT = p("t_ble_evt", 1.5e-3, "E", "connection event with 2-3 packets of ECG stream ≈ 1.5 ms")
T_CONN = p("t_conn", 30e-3, "E", "connection interval for a 1.5 kB/s ECG stream; 30 ms (33 Hz, in band)")
I_SYS_BASE = p("i_sys_base", 0.6e-3, "E", "VDD_1V8 base load in ECG mode (nRF idle+CPU duty, ADS DVDD, IMU, flash) ≈ 0.6 mA")
I_ADS_AVDD = p("i_ads_avdd", 150e-6, "A", "ARCHITECTURE.md §4.5: ADS1291 ≈150 µA AVDD (⚠ there)")
ETA_BUCK = p("eta_buck", 0.85, "A", "ARCHITECTURE.md §4.5: buck efficiency 0.85")
I_LED = p("i_led", 15e-3, "A", "ARCHITECTURE.md §4.5: PPG LED 15 mA, 117 µs, 25 sps (30 mA worst case in SIM-06)")
VLED = p("vled", 4.30, "A", "ARCHITECTURE.md D10: VLED 4.30 V from TPS61099")
ETA_VLED = p("eta_vled", 0.80, "A", "ARCHITECTURE.md §4.5: TPS61099 efficiency 0.80")

# ----------------------------------------------------------------------------------------- input network (frozen + to choose)
R_PROT = p("r_prot", 330e3, "A", "ARCHITECTURE.md D4/§3.3: 2 × 330 kΩ ERJ-PA3F3303V (C441935) per electrode")
R_PROT_TOL = p("r_prot_tol", 0.01, "V", "ERJ-PA3 datasheet p2: ±1 % (F); JLC C441935 record")
C_TVS = p("c_tvs", 13.5e-12, "V", "TPD1E10B06 SLLSEB1G p7 Fig 5-8: 13.5 pF at 1.5 V bias (12 pF at 2.5 V, p5)")
C_TVS_MM = p("c_tvs_mismatch", 0.10, "E", "part-to-part capacitance spread ±10 % (no min/max in datasheet)")
I_TVS_MAX = p("i_tvs_leak_max", 100e-9, "V", "SLLSEB1G p5: leakage 100 nA max at 5 V")
I_TVS_WC = p("i_tvs_leak_wc", 100e-9 * 1.5 / 5.0, "E", "worst case at the 1.5 V operating bias: spec max scaled linearly (pessimistic)")
I_TVS_TYP = p("i_tvs_leak_typ", 1e-9, "E", "typical leakage at 1.5 V bias (no typ in datasheet; bench item)")
C_ROUTE = p("c_route", 2e-12, "E", "pin + 15 mm L3 stripline between GND planes ≈ 2 pF per input")
C_ROUTE_MM = p("c_route_mismatch", 0.5e-12, "E", "routing mismatch ±0.5 pF (symmetric layout per R-ECG-1)")
C_PAR_R = p("c_par_0603", 0.05e-12, "E", "0603 thick-film parasitic capacitance ≈ 0.05 pF")
C0G_TOL = p("c0g_tol", 0.05, "V", "JLC C1555/C32949/C1546 records: C0G ±5 % (J)")

# ----------------------------------------------------------------------------------------- body / environment
R_E = p("electrode_R", (0.1e6, 1e6, 10e6), "A", "ARCHITECTURE.md SIM-07: 0.1-10 MΩ")
C_E = p("electrode_C", (1e-9, 10e-9, 100e-9), "A", "ARCHITECTURE.md SIM-07: 1-100 nF")
V_HC = p("halfcell", 0.300, "A", "ARCHITECTURE.md SIM-07: ±300 mV (taken as differential E1−E3 and as E2 vs mean of E1/E3)")
MISMATCH = p("electrode_mismatch", 0.5, "A", "ARCHITECTURE.md SIM-07: ±50 % electrode mismatch")
V_MAINS = p("v_mains", 230.0, "A", "China mains 230 Vrms 50 Hz (ARCH §7.2 notch at 50 Hz)")
C_PW = p("c_mains_body", (3e-12, 10e-12), "E", "mains-to-body coupling ≈ 3 pF typical (Metting van Rijn et al. 1990), 10 pF harsh")
C_BODY = p("c_body_earth", 200e-12, "E", "body-to-earth ≈ 200 pF (same source)")
C_SUP = p("c_dev_earth", (3e-12, 20e-12), "E", "floating band GND-to-earth: ≈3 pF on the wrist, 20 pF near grounded metal")
C_DB = p("c_dev_body", (20e-12, 0.0), "E", "band GND plane to skin ≈ εr 3 · 10.7 cm² / 1.6 mm ≈ 18 pF; 0 pF taken as worst case")
R_BODY = p("r_body", 300.0, "E", "arm-to-arm internal resistance ≈ 300 Ω (negligible next to MΩ electrodes)")
R_E_FAULT = p("electrode_R_fault", 1e3, "E", "wet/sweaty skin contact for the fault-current worst case")

# ----------------------------------------------------------------------------------------- ESD
p("iec_cal_8kv", dict(ipk=30.0, tr=0.8e-9, i30=16.0, i60=8.0), "E",
  "IEC 61000-4-2:2008 Table 2 contact-discharge calibration at 8 kV into 2 Ω (first peak 30 A ±15 %, rise 0.8 ns ±25 %, "
  "16 A ±30 % at 30 ns, 8 A ±30 % at 60 ns) – standard values from memory, not re-checked against the standard text")
p("iec_rc", (150e-12, 330.0), "A", "task / ARCH SIM-08: 150 pF / 330 Ω network")
TVS_TLP = p("tvs_tlp_12", [(7.4, 0.0), (8.0, 0.5), (10.0, 3.0), (12.0, 6.0), (14.0, 10.0), (16.0, 15.5), (18.0, 21.0), (20.0, 27.0)],
            "V", "SLLSEB1G p6 Fig 5-3 TLP pin1→pin2 (digitised by eye from 300-dpi render img/tpd1e10b06_tlp12.png)")
p("tvs_tlp_21", [(8.7, 0.0), (10.0, 2.0), (12.0, 5.5), (14.0, 10.0), (16.0, 14.8), (18.0, 19.5), (20.0, 24.5), (21.4, 28.0)],
  "V", "SLLSEB1G p6 Fig 5-4 TLP pin2→pin1 (img/tpd1e10b06_tlp21.png)")
p("tvs_clamp_8kv", dict(peak=80.0, t30ns=15.0, t100ns=11.0), "V", "SLLSEB1G p6 Fig 5-1: +8 kV contact clamp ≈80 V spike, ≈15 V at 30 ns, ≈11 V at 100 ns")
p("tvs_vclamp_8_20", {1.0: 10.0, 5.0: 14.0}, "V", "SLLSEB1G p5: VClamp max 10 V at 1 A, 14 V at 5 A (8/20 µs)")
p("tvs_iec", 30e3, "V", "SLLSEB1G p4: IEC 61000-4-2 ±30 kV contact, all pins")
L_TVS = p("l_tvs", 1.0e-9, "E", "TVS package + via + pad loop ≈ 1 nH (tuned so the first clamp spike matches Fig 5-1)")
L_TRACE = p("l_trace", 1.0e-9, "E", "electrode spring/landing pad to TVS ≈ 1 nH")
p("erj_pa3", dict(p_w=0.25, v_lim=150.0, v_ovl=200.0), "V", "ERJ-PA3 datasheet (LCSC copy, 29-Sep-23) p2: 0.25 W, limiting element 150 V, max overload 200 V")
p("erj_pa3_esd", dict(c=150e-12, r=150.0, v=3000.0, drift_pct=1.0), "V",
  "ERJ-PA3 datasheet p4 'ESD Characteristic': 150 pF / 150 Ω (R > 1.5 kΩ) / ±3 kV, resistance change < 1 % around 330 kΩ")
p("bas116", dict(vrrm=85.0, vr=75.0, ifsm_1us=4.0, ifsm_1ms=1.0, cd=2e-12), "V",
  "Nexperia BAS116 data sheet (5 Aug 2020) p2 limiting values, p3 Cd 2 pF")
CIN_PV = p("cin_vin", 4.7e-6, "A", "ARCHITECTURE.md §3.1 CIN 4.7 µF on VIN_DC (R-PMIC-2)")
p("bas21", dict(vrrm=250.0, vr=200.0, ifsm_1us=9.0, ir_200v=100e-9, cd=5e-12, trr=50e-9, lcsc="C8661", stock=26642), "V",
  "Nexperia BAS21 data sheet 1 Jul 2022 (cache/datasheets/bas21.pdf) p1/p3/p4: VRRM 250 V, IFSM 9 A (1 µs), IR 100 nA "
  "at 200 V, Cd ≤ 5 pF, trr ≤ 50 ns; p2 pinning 1 A / 2 n.c. / 3 K = BAS116; JLC C8661 BAS21,215 Extended 26,642 "
  "(API 2026-11-12T00:45Z)")
p("bas116_pin", "1 A / 2 n.c. / 3 K", "V", "Nexperia BAS116 data sheet (cache/datasheets/bas116.pdf) Table 2")
p("fb_c_plus", dict(mpn="BLM15AX601SN1D", lcsc="C76886", z100=600.0, tol=0.25, rdc=0.34, imax=0.5, stock=350728), "V",
  "JLC API search 2026-11-12 (cache/jlc/search/BLM15AX601SN1D.json): Murata 0402, 600 Ω ±25 % at 100 MHz, 340 mΩ, 500 mA, Extended")
p("fb_model", dict(l=1.2e-6, r=800.0, c=0.5e-12), "E",
  "generic bead model (L ‖ R ‖ C + Rdc) giving ≈ 550 Ω at 100 MHz and ≈ 0.8 kΩ near 1 GHz; the -25 % case scales L and R")

# ----------------------------------------------------------------------------------------- TPS7A2030 (SBVS338H) – SIM-06 design change
p("ln_ldo", dict(mpn="TPS7A2030PDBVR", lcsc="C963429", lib="Extended", stock=17183, p100=0.1893), "V",
  "JLC API selectSmtComponentList 2026-11-12T00:15:56Z (cache/jlc/C963429.json): TPS7A2030PDBVR, SOT-23-5, Extended")
p("ln_ldo_pinout", "DBV: 1 IN, 2 GND, 3 EN, 4 N/C, 5 OUT", "V",
  "SBVS338H p4 Fig 4-4 = TPS7A02 SBVS277C p3 Fig 5-2 DBV (1 IN, 2 GND, 3 EN, 4 NC, 5 OUT): drop-in on the same footprint")
LN_IQ = p("ln_ldo_iq", (6.5e-6, 8.5e-6, 10e-6), "V", "SBVS338H p6: IGND 6.5 typ / 8.5 max (25 °C) / 10 max (-40…85 °C) µA at IOUT 0")
p("ln_ldo_psrr_pts", [(10, 70), (100, 69.5), (300, 68), (1e3, 60.5), (3e3, 65), (1e4, 70), (3e4, 73), (1e5, 71), (2e5, 63),
                      (4e5, 58), (7e5, 43), (1e6, 44), (2e6, 50), (5e6, 55), (1e7, 50)], "E",
  "SBVS338H p18 Fig 5-63 (VIN = VOUT+0.3 V, COUT 1 µF): lower envelope of the 0.01 mA and 20 mA curves, read by eye "
  "from the 300-dpi render refs/img/tps7a20_f563.png; held flat below 10 Hz; measured at 0.3 V headroom, so no derate")
p("ln_ldo_noise_pts", [(10, 0.75), (20, 0.42), (30, 0.26), (50, 0.18), (100, 0.12), (200, 0.075), (500, 0.052), (1e3, 0.045),
                       (1e4, 0.032), (1e5, 0.022), (2e5, 0.012), (5e5, 0.004), (1e6, 0.002), (1e7, 0.0012)], "E",
  "SBVS338H p18 Fig 5-65, IOUT 1 mA, VOUT 2.8 V, µV/√Hz read by eye from refs/img/tps7a20_f565.png; scaled ×3.0/2.8; "
  "below 10 Hz the same f^-0.5 rule as for the TPS7A02; integral checked against the printed 8.63 µVrms (curves.py)")

# ----------------------------------------------------------------------------------------- design change candidate (SIM-06)
RREF_EXT = p("rldref_ext", dict(r_top=10e6, r_bot=10e6, c=1e-6, r_tol=0.01), "E",
             "proposed: RLDREF_INT = 0 (RESP2, SBAS502C p36/p61) and RLDIN/RLDREF fed from AVDD_ECG by 2 × 10 MΩ 1 % "
             "+ 1 µF X7R to AVSS (τ = 5 s, fc = 0.032 Hz); U3 is always on (EN = VDD_1V8, ARCH §4.1) so the RC stays charged")
p("i_rldref_div", 3.0 / 20e6, "E", "divider current 150 nA continuous = 0.45 µW at AVDD (0.1 % of the 406 µW MON budget)")
p("ldo_noise_lowf_alt", "white below 10.6 Hz", "E",
  "optimistic alternative to the f^-0.5 extrapolation of Fig 6-48 below its 10 Hz edge (sensitivity only)")
