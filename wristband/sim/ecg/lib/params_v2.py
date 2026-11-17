"""V2-B numbers added to (or overriding) lib/params.py, each with its provenance.

Tags:  V = verified (datasheet page / cached API record / project file), A = taken from REDESIGN_V2.md rev 1, the v2 netlist or
       ARCHITECTURE.md (design input), E = estimate (method given), S = result of a simulation in this folder.
REDESIGN = /path/to/SolarVest_work/wristband/redesign/REDESIGN_V2.md ; netlist = v2/design/src/*.py (FIX state, 2026-11-12).
"""
import math
from params import P, p

EPS0 = 8.854e-12

# ----------------------------------------------------------------------------------------- board and floor stack (skin side)
p("stack_id", "JLC06101H-3313", "V", "JLC stack API record cache/v2/jlc_cap/stack_6L_1p0_1oz_0p5oz.json: 6 layers, 1.0 mm, 1 oz outer / 0.5 oz inner")
p("stack_mm", dict(cu_outer=0.035, pp_outer=0.0994, cu_inner=0.0152, core=0.25, pp_mid=0.2104), "V",
  "same record: L1 0.035 / PP 3313 0.0994 / L2 0.0152 / core 0.25 / L3 0.0152 / PP 7628 0.2104 / L4 0.0152 / core 0.25 / L5 0.0152 / PP 3313 0.0994 / L6 0.035")
p("er_pp3313", 4.1, "E", "JLC impedance tables give Dk 4.1 for 3313 and 4.6 for core / 7628 (value used by v1 SIM-12: 4.16 / 4.6); +-10 %")
p("er_core", 4.6, "E", "see er_pp3313")
p("film_carrier", dict(t=0.10e-3, er=3.3, t_pi_min=25e-6), "A", "REDESIGN 5.2 / 5.5: polyimide-carrier double-sided film 0.10 mm +-0.02, >= 25 um of polyimide; er 3.3 E (PI 3.4, acrylic 3.0-3.5)")
p("mask", dict(t=0.02e-3, er=3.5), "E", "LPI solder mask over B.Cu clearances, 15-25 um")
p("floor_film", dict(t=0.25e-3, er=3.0), "A", "REDESIGN 5.2: 0.25 mm polycarbonate film, flush with the 0.25 mm Ti plates; er 3.0-3.1 V (Makrolon 2458 sheet p.2, cache/redesign/enclosure)")
p("shim", dict(t=0.15e-3, er=4.5), "A", "REDESIGN 5.2: 0.15 mm glass-epoxy support shim under the cell; er E")
p("psa_cell", dict(t=0.10e-3, er=3.0), "A", "REDESIGN 5.2: PSA under the cell 0.10 mm; er E")

# ----------------------------------------------------------------------------------------- electrode plates and their capacitances
p("plate_E1", dict(x=12.5e-3, y=18.5e-3, contact_cm2=1.49), "A", "redesign/enclosure.md line 225 / REDESIGN 5.5: antenna-side plate 12.5 x 18.5 mm, about 1.5 cm2 in contact (estimate there)")
p("plate_E2", dict(x=13.0e-3, y=22.5e-3, contact_cm2=1.94), "A", "same: far-side plate 13 x 22.5 mm, about 1.9 cm2 in contact")
p("plate_over_board_cm2", (1.75, 2.08), "E", "overlap of E1 / E2 with the 18 mm board strip (physics review ecg_plate_cap.py: 12.5 x 14.0 and 13.0 x 16.0 mm); "
  "own estimate from REDESIGN 5.3 with the plates centred on the case: 1.59 / 1.92 cm2. The larger pair is used")
p("plate_under_cell_cm2", (0.56, 0.85), "E", "rest of each plate lies under the cell bay (REDESIGN 5.3: plates extend under the cell ends): 12.5 x 4.5 and 13 x 6.5 mm")
p("tmp117_island_mm2", (9.0, 16.0, 25.0), "E", "floating thermal-via island on B.Cu under plate E1 (netclasses.json TMP117_ISLAND; sensors_storage.py: thermal pad NC): 3x3 / 4x4 / 5x5 mm")
p("c_island_to_gnd", 3e-12, "E", "floating island + 9-16 thermal vias through four planes with antipads + TMP117 die paddle: 2-5 pF to GND")
p("c_dot_pads", 1.0e-12, "E", "two ENIG dot pads, 100 Ohm link, test pad and trace to D5/R301 on the sky side: about 1 pF per electrode net")
p("c_e3_stray", (0.8e-12, 2.0e-12), "E", "E3 net ahead of R303: Ti strip 26 x 3.5 mm on the PC rim, tab, spring finger J11, TP5, trace to D6: 0.8-2 pF to GND "
  "(strip to board ground 2.85 mm below through air/PC: 0.3 pF; spring + pads 0.5-1.5 pF)")

def c_area(layers):
    """series dielectric stack -> F per m2; layers = [(t_m, er), ...]"""
    return EPS0 / sum(t / er for t, er in layers)

_f, _m, _s = P["film_carrier"]["value"], P["mask"]["value"], P["stack_mm"]["value"]
_pp, _co = P["er_pp3313"]["value"], P["er_core"]["value"]
CAP_PER_CM2 = {      # pF per cm2 of plate over the board, by what the first copper is
    "B.Cu copper (ground or pour) under the plate": c_area([(_f["t"], _f["er"]), (_m["t"], _m["er"])]) * 1e-4 * 1e12,
    "B.Cu void, copper on L5": c_area([(_f["t"], _f["er"]), (_m["t"], _m["er"]), ((_s["cu_outer"] + _s["pp_outer"]) * 1e-3, _pp)]) * 1e-4 * 1e12,
    "B.Cu and L5 void, copper on L4 (design rule PLATE_VOID)": c_area([(_f["t"], _f["er"]), (_m["t"], _m["er"]), ((_s["cu_outer"] + _s["pp_outer"]) * 1e-3, _pp),
                                                                       ((_s["cu_inner"] + _s["core"]) * 1e-3, _co)]) * 1e-4 * 1e12,
    "B.Cu, L5 and L4 void, copper on L3": c_area([(_f["t"], _f["er"]), (_m["t"], _m["er"]), ((_s["cu_outer"] + _s["pp_outer"]) * 1e-3, _pp),
                                                  ((_s["cu_inner"] + _s["core"]) * 1e-3, _co), ((_s["cu_inner"] + _s["pp_mid"]) * 1e-3, _co)]) * 1e-4 * 1e12,
}
p("cap_plate_per_cm2", CAP_PER_CM2, "S", "parallel-plate values from the stack above (fringe adds < 5 % at 12 mm plate width over 0.5 mm)")
_sh, _ps = P["shim"]["value"], P["psa_cell"]["value"]
C_CELL_PER_CM2 = c_area([(_f["t"], _f["er"]), (_sh["t"], _sh["er"]), (_ps["t"], _ps["er"])]) * 1e-4 * 1e12
p("cap_cell_per_cm2", C_CELL_PER_CM2, "S", "plate to cell pouch foil through film 0.10 + shim 0.15 + PSA 0.10 (review R-15: about 7 pF per plate)")


def plate_caps(case="B.Cu and L5 void, copper on L4 (design rule PLATE_VOID)", island_mm2=16.0, cell=True):
    """extra capacitance to device ground at the E1 / E2 pad nodes (F) and its breakdown"""
    a1, a2 = P["plate_over_board_cm2"]["value"]; b1, b2 = P["plate_under_cell_cm2"]["value"]
    cpp = CAP_PER_CM2[case]
    isl_series = 0.0
    if island_mm2:
        c_pi = CAP_PER_CM2["B.Cu copper (ground or pour) under the plate"] * island_mm2 / 100.0      # plate -> island, pF
        cg = P["c_island_to_gnd"]["value"] * 1e12
        isl_series = c_pi * cg / (c_pi + cg) - cpp * island_mm2 / 100.0      # island replaces that much voided area
    c1 = cpp * a1 + (C_CELL_PER_CM2 * b1 if cell else 0.0) + isl_series + P["c_dot_pads"]["value"] * 1e12
    c2 = cpp * a2 + (C_CELL_PER_CM2 * b2 if cell else 0.0) + P["c_dot_pads"]["value"] * 1e12
    return c1 * 1e-12, c2 * 1e-12, dict(board=(cpp * a1, cpp * a2), cell=(C_CELL_PER_CM2 * b1, C_CELL_PER_CM2 * b2), island=isl_series)


# ----------------------------------------------------------------------------------------- dry-skin electrode impedance
p("z10_ti_invivo", 2.06e6, "V", "Sensors 22(21) 8510 (PMC9656728, cache/redesign/enclosure/pmc9656728.xml) section 3.3.1: mean area-normalised |Z| at 10 Hz, "
  "titanium grade 2, in vivo on the thigh, N = 10: 2.06 MOhm cm2 (stainless 304: 2.68; dry phantom Ti 1.70)")
p("z10_spread", (0.5, 1.0, 2.0), "E", "inter-subject spread: the paper's text gives only means (Figure 8 / 12 are images); x0.5 ... x2 taken. Wrist and fingertip skin are not thigh skin: bench item")
p("z10_phase_deg", (-30.0, -60.0, -80.0), "E", "phase of the dry-skin impedance at 10 Hz: the paper fits CPE exponents 0.9 (stratum corneum) and 0.5-0.6 (contact): -45 ... -80 deg; -30 added as the resistive bound")
p("e3_contact_cm2", (0.5, 0.75, 1.0), "E", "finger pad on the 26 x 3.5 mm top-rim strip (REDESIGN 5.5: strip 1.0-1.2 cm2): a 15 mm wide finger across the strip covers 0.5 cm2; lying along it up to 0.9-1.0 cm2")


def rc_from_z(z10, phase_deg):
    """parallel R, C with |Z(10 Hz)| = z10 and the given phase"""
    t = math.tan(math.radians(abs(phase_deg)))
    R = z10 * math.sqrt(1 + t * t)
    return R, t / (2 * math.pi * 10.0 * R)


def invivo_electrodes(k=(1.0, 1.0, 1.0), phase=-60.0, a3=0.75):
    """[(R, C)] for E1, E2, E3 from the in-vivo value scaled by area and the spread factors k"""
    z0 = P["z10_ti_invivo"]["value"]
    areas = (P["plate_E1"]["value"]["contact_cm2"], P["plate_E2"]["value"]["contact_cm2"], a3)
    return [rc_from_z(z0 / a * kk, phase) for a, kk in zip(areas, k)]


# ----------------------------------------------------------------------------------------- lid, PV node, harvester
p("lid_stack", dict(glass=(0.50e-3, 7.2), enc_top=(0.20e-3, 2.8), cell=0.165e-3, enc_bot=(0.15e-3, 2.8), flex=0.12e-3), "A",
  "REDESIGN 5.2: glass 0.50 / encapsulant 0.20 / cells 0.165 / encapsulant 0.15 / flex backsheet 0.12 mm; glass er 7.2 V (Corning Gorilla Glass 3 PI sheet p.1, "
  "2.47 GHz; low-frequency value about 7.4 E); encapsulant er 2.8 E (EVA / POE 2.6-3.0)")
p("lid_geom", dict(strip_x=(3.7e-3, 31.4e-3), strip_w=5.2e-3, n=4, pv_y=(6.0e-3, 28.0e-3), rest_x=(31.4e-3, 37.1e-3), e3_x=(37.1e-3, 40.0e-3), e3_len=26e-3), "A",
  "REDESIGN 5.3: four strips 27.7 x 5.2 mm from X 3.7 to 31.4, Y 6.0 to 28.0; no silicon within 5.7 mm of the E3 strip, backsheet copper there tied to PV- (= GND, io_block.py J6); "
  "E3 strip 26 x 3.5 mm on the top rim at the hand-side end, lid set back 2.5 mm")
p("pv_model", dict(jsc=0.0502 / (21.5 * 5.65 / 100), i0_per_cm2=3.889e-11 / (21.5 * 5.65 / 100), n=1.28, ns=4, vt=0.025693, rs_a=3.375 / 4 * (21.5 * 5.65 / 100),
                   rsh_a=131600.0 / 4 * (21.5 * 5.65 / 100), k_opt=0.87, a_strip_cm2=27.7 * 5.2 / 100, r_ic=0.2, lux_to_sun=3.4e-6), "A",
  "single-diode string model of REDESIGN 5.6 (redesign/v2_rev1_checks.py ibc_string; KXOB121K04TF fit of sim/power/common/params.py scaled by area, k = 0.87): estimate")
p("bq_focv", dict(ratio=0.80, ratio_tol=(0.72, 0.88), t_sample=16.0, t_settle=0.256), "V", "BQ25570 SLUSBH2G p.7: VOC sampled every 16 s for 256 ms, MPPT 80 % (VOC_SAMP = VSTOR); regulation tolerance 10 % (v2/design CALC.md 3)")
p("r_lim", (22.0, 18.0), "A", "netlist R130: 22 Ohm 0603 (FIX R-18); SB_RLIM=18 builds 18 Ohm (working decision 3)")
p("rsh1", 1.0, "A", "netlist R111 1.00 Ohm PV shunt ahead of Q1")
p("c_pv_node_board", 15e-12, "E", "PV_NODE copper on the board (J6 land, D8 13.5 pF TVS, RSH1, INA_PV pins, D10-side trace): the TVS dominates; only its field to the E3 net matters")
p("cin_vin", 4.7e-6, "A", "netlist C101 4.7 uF on VIN_DC behind R_LIM")
p("bq_ripple_vin", dict(v_pp=0.05, f=(1e3, 100e3)), "E", "VIN_DC ripple of the PFM boost charger: CIN 4.7 uF (x0.6 DC bias) and 230 mA peak inductor bursts -> 20-60 mVpp at 1-100 kHz")

# ----------------------------------------------------------------------------------------- cell and its protector (VSTOR network of SIM-06)
p("cell_v2", dict(c_mAh=43.0, r_dc=(0.5, 1.0), i_chg_max=21.5e-3), "V", "GMB201030 UN 38.3 report p.2 (43 mAh, 21.5 mA) and sister cell 201021 spec p.4-5 (impedance <= 1000 mOhm) as re-read in REDESIGN 11")
p("r_prot_fet", (0.040, 0.045, 0.054), "V", "XB5358D0 REV0.4 p.3: RSS(ON) 40 / 45 / 54 mOhm at VDD 3.6 V (text copy cache/v2/sim_ecg/xb5358d0.pages.txt)")
p("r117", 3.3, "A", "netlist R117 3.3 Ohm VSTOR_SW -> VLED")
p("c404", 10e-6, "A", "netlist C404 10 uF 0603 on VLED = the only LED reservoir (C118 is a DNP pad set, FIX R-08)")
p("r_u12", (0.105, 0.2), "E", "SiP32431 load switch on-resistance at 3.3-4.2 V: 105 mOhm typ, 200 mOhm bound (data sheet figure not re-read in this lane)")
p("cell_step_at_voc_sample", (4e-3, 12e-3), "A", "review R-15: cell terminal steps by 4-12 mV at each Voc sample (12 mA x ESR), estimate there")

# ----------------------------------------------------------------------------------------- PPG parts
p("led_hrm", dict(lam_dom=536e-9, lam_range=(526e-9, 544e-9), iv_mcd_20mA=(3150, 5000), phi_v_mlm_20mA=(10100, 14300), vf_20mA=(2.0, 2.3, 2.8),
                  if_min=2.5e-3, size=(1.8e-3, 2.2e-3, 0.6e-3), half_angle=60.0), "V",
  "OSRAM CT DBLP31.12 data sheet v1.3 2021-03-29 p.1, p.3-5 (text copy cache/v2/sim_ecg/osram_ct_dblp31_12.pages.txt): true green 536 nm, "
  "3150-5000 mcd and 10.1-14.3 lm typ per brightness group at 20 mA, Lambertian 120 deg, IF 2.5-140 mA")
p("led_lm_per_W", (520.0, 580.0, 620.0), "E", "luminous efficacy of radiation of an InGaN green LED at 536 nm dominant, 30-35 nm FWHM: 520-620 lm/W")
p("pd", dict(area=4.6e-6, ira_525=(3.4e-6, 4.4e-6, 5.3e-6), ee_525=2.5, ira_850=(23e-6, 28e-6, 33e-6), ee_850=10.0, cd_0V=47e-12, cd_3V=17e-12,
             idark_10V=(0.2e-9, 10e-9), half_angle=65.0, size=(4.8e-3, 2.5e-3, 0.48e-3)), "V",
  "Vishay VEMD8080 Rev. 1.1 05-Sep-2023 p.1-2: 4.6 mm2, Ira 3.4/4.4/5.3 uA at 0.25 mW/cm2 525 nm, 23/28/33 uA at 1 mW/cm2 850 nm, CD 47 pF at 0 V, dark 0.2 nA typ / 10 nA max at 10 V")
p("max86141", dict(fs_uA=(4, 8, 16, 32), tint_us=(14.8, 29.4, 58.7, 117.3), noise_pA=(262, 128, 83, 56), alr_dc_max=200e-6, alr_ac_db=70.0, dc_alr_nA=0.5,
                   cpd_max_pF=(65, 130, 260, 520), led_vol_31mA=(0.160, 0.253), led_psr_uA_per_V=(-1.0, 400.0), bits=19), "V",
  "MAX86140/MAX86141 data sheet p.5-6 (cache/datasheets/max86141.txt): ADC full scale 4/8/16/32 uA, tINT 14.8-117.3 us, dark-current input-referred noise 262/128/83/56 pArms "
  "(16 uA range, CPD 65 pF), maximum DC ambient rejection 200 uA, AC ambient rejection 70 dB at 120 Hz, DC ambient rejection 0.5 nA (0-30 uA), LED driver VOL 160 typ / 253 max mV (31 mA range), "
  "LED driver DC PSR -1 / +400 uA/V (124 mA range, full scale)")
p("ppg_plan", dict(i_led_v1=15e-3, gain=(1.0, 2.0, 4.0), tint=117.3e-6, sps=25.0, agc_floor=2.5e-3), "A",
  "ARCH 4.5: 1 LED at 15 mA, 117 us, 25 sps; REDESIGN 5.6: same photodiode signal at a quarter of the current (gain 4 planning, 2 and 1 shown); firmware AGC floor 2.5 mA (CHANGES.md 8)")
p("cap_geom", dict(l=11e-3, w=7e-3, h=1.15e-3, roof=0.30e-3, inner_h=0.85e-3, led_top_to_skin=0.5e-3, pitch=(2.75e-3, 3.3e-3, 3.8e-3)), "A",
  "REDESIGN 5.5: two-shot PC cap 11 x 7 x 1.15 mm, clear windows with a 0.30 mm roof, inner height 0.85 mm, black ribs between each LED and the photodiode, LED to skin about 0.5 mm; "
  "LED-PD centre pitch: ARCH R-PPG-1 2.75 mm (v1); 3.3 and 3.8 mm are what an 11 mm cap allows with the 4.8 x 2.5 mm photodiode across the line (E, no layout exists)")
