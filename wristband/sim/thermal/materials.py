"""Material and boundary data for SIM-13 (SolarBand thermal model).

Each entry: k_xy, k_z [W/mK], rho [kg/m3], cp [J/kgK], src.  Status markers as in ARCHITECTURE.md:
  V = verified against a cited source, E = estimate / handbook-typical (bounded by a sensitivity case).
Source notes are cached in cache/web/thermal/sources_thermal_mech.md.
"""

MAT = {
    # name        k_xy    k_z    rho    cp     status, source
    "air":      (0.030, 0.030, 1.1, 1007, "E", "dry air 0.027 W/mK at 40 C (Incropera Table A.4) + ~10 % for radiation across mm gaps"),
    "glass":    (1.00, 1.00, 2420, 800, "E", "aluminosilicate cover glass ~1.0 W/mK (Corning Astra PI sheet 1.04 as proxy; Gorilla sheets list no k)"),
    "resin":    (0.20, 0.20, 1200, 1200, "V/E", "PC 0.20 W/mK ISO 8302 (Covestro Makrolon); SLA resin assumed equal"),
    "pv_cell":  (15.0, 0.60, 1740, 800, "E", "IXOLAR TF: ~0.2 mm mono-Si (148 W/mK) on a ~1 mm laminate; rho from 1.2 g / 23x25x1.2 mm [DS KXOB121K04TF p1]"),
    "snbi_jnt": (2.0, 2.0, 5000, 300, "E", "0.05 mm layer: SnBi pads (~8 % of area) + air"),
    "pv_board": (30.0, 0.40, 1900, 1100, "E", "2-layer 0.6 mm FR4, 2 x 35 um Cu ~70 % fill; FR4 0.3 W/mK [JLC blog]"),
    "foam":     (0.05, 0.05, 300, 1500, "E", "PU foam (PORON class) 0.04-0.06 W/mK"),
    "pe_tape":  (0.05, 0.05, 300, 1500, "E", "0.15 mm double-sided PE-foam tape under the cell (v0), ~0.05 W/mK"),
    "psa":      (0.20, 0.20, 1100, 1500, "E", "acrylic PSA ~0.2 W/mK"),
    "battery":  (25.0, 0.60, 1030, 1000, "V/E", "pouch cell through-plane 0.52-0.7, in-plane 20-30 W/mK (Lin et al.; Chalmers thesis); rho = 1.4 g [DS EEMB] / envelope"),
    "pcb":      (40.0, 1.00, 2100, 1000, "E", "6-layer 0.8 mm: Cu 1 oz outer 50 %, 0.5 oz inner (2 solid GND, 70 %, 20 %) -> k_xy ~40; k_z FR4 0.3 + GND-stitch vias ~0.7"),
    "pcb_ko":   (0.30, 0.30, 1900, 1100, "V", "FR4 laminate only (all-layer keep-out under the TMP117 island) 0.25-0.35 W/mK [JLC blog]"),
    "cu_island":(270.0, 50.0, 8900, 385, "E", "L1 copper island 35 um in a 0.05 mm cell (390 x 0.035/0.05)"),
    "ic":       (1.00, 1.00, 2000, 900, "E", "mould compound / ferrite / ceramic average for SMD bodies"),
    "steel316": (16.3, 16.3, 8000, 500, "E", "316L stainless 16.3 W/mK (handbook)"),
    "slot_bridged": (0.30, 0.05, 500, 1100, "E", "1.0 mm NPTH slot ring (JLC min non-plated slot 1.0 mm) with 4 x 1 mm FR4 bridges carrying 6 x 0.1 mm L1 traces (radial k dominated by the traces)"),
    "gap_pad":  (3.00, 3.00, 3000, 1000, "E", "silicone gap pad, 3 W/mK class (Bergquist/t-Global 3 W/mK grades)"),
}

# optical / surface data
SOLAR = dict(
    G=1000.0,            # W/m2, normal incidence [task]
    lens_R_front=0.04,   # Fresnel n=1.5 [E]
    lens_abs=0.015,      # bulk absorption, 0.7 mm aluminosilicate, solar-weighted [E]
    lens_R_back=0.04,    # [E]
    alpha_cell=0.90,     # solar absorptance of an ARC-coated mono-Si cell incl. sub-bandgap IR absorbed in the substrate [E]
    alpha_print=0.95,    # black ink on the lens underside (masks everything but the cells) [E]
    alpha_frame=0.50,    # light-grey resin frame rim [E]; sensitivity 0.9 (black)
    eps_lens=0.90, eps_shell=0.90, eps_skin=0.98,   # [E] glass / polymer / skin (skin 0.98 handbook)
)
PV = dict(
    P_stc=0.1353,        # W, KXOB121K04TF 105.3 + KXOB25-03X4TF 30.0 mW [DS p1 each]
    Isc_stc=0.0646,      # A, 50.2 + 14.4 mA [DS p1 each]
    Vmp=2.23,            # V [DS]
    gamma_P=-0.0035,     # 1/K Pmpp temperature coefficient [E, mono-Si typical; ANYSOLAR gives Voc -0.25 %/K]
    alpha_Isc=0.0004,    # 1/K [E]
    eta_harv=0.88,       # BQ25570 efficiency above 1 mW [ARCH §4.6, estimate]
    R_sh=1.0, R_q1=0.10, R_wire=0.10,   # ohm: RSH1 [ARCH], Si2302 at Vgs 1.8 V [OPEN] (0.075 at 2.5 V [DS]), leads [E]
    P_load=0.0004,       # W, MON 406 uW [ARCH §4.5]
    R_cell_int=1.0,      # ohm, LP301230 internal resistance [E]
    Vbat=3.8,
)
ENV = dict(
    T_amb=35.0, T_skin=34.0,       # [task]
    R_contact=0.0025,              # m2K/W, skin-object contact at a few kPa: 0.002-0.003 (Rykaczewski, NSF PAR 10182000 p18) [V]
    h_top=12.0, h_side=10.0,       # W/m2K forced convection at 0.5 m/s [E: laminar flat plate L=40 mm gives 13.9,
                                   #   cylinder D=60 mm (wrist) gives 9.3, Incropera eqs. 7.30 / 7.54]
    indent=1.2,                    # mm, mesa indentation into the wrist under strap pressure [E]
)


def h_rad(eps, T_mean_C=45.0, eps2=1.0):
    """Linearised radiation coefficient, W/m2K (grey two-surface, large enclosure when eps2 = 1)."""
    s = 5.670374419e-8
    T = T_mean_C + 273.15
    e = 1.0 / (1.0 / eps + 1.0 / eps2 - 1.0)
    return 4.0 * e * s * T ** 3


def h_conv_check():
    """Order-of-magnitude check of the convection coefficient (printed in the README)."""
    import math
    nu, k, Pr = 1.70e-5, 0.0271, 0.705
    U = 0.5
    L = 0.040
    ReL = U * L / nu
    h_plate = 0.664 * ReL ** 0.5 * Pr ** (1 / 3) * k / L
    D = 0.060
    ReD = U * D / nu
    Nu = 0.3 + 0.62 * ReD ** 0.5 * Pr ** (1 / 3) / (1 + (0.4 / Pr) ** (2 / 3)) ** 0.25 * (1 + (ReD / 282000) ** 0.625) ** 0.8
    h_cyl = Nu * k / D
    # natural convection, hot plate facing up, L = A/P, dT = 10 K
    g, beta, dT, alpha = 9.81, 1 / 313.0, 10.0, 2.4e-5
    Lc = (40 * 32) / (2 * (40 + 32)) * 1e-3
    Ra = g * beta * dT * Lc ** 3 / (nu * alpha)
    h_nat = 0.54 * Ra ** 0.25 * k / Lc
    return dict(Re_L=ReL, h_flat_plate=h_plate, Re_D=ReD, h_wrist_cylinder=h_cyl, Ra_nat=Ra, h_natural=h_nat,
                h_mixed=(h_plate ** 3 + h_nat ** 3) ** (1 / 3))


if __name__ == "__main__":
    print(h_conv_check())
    print("h_rad glass->env", round(h_rad(0.9), 2), " shell->skin", round(h_rad(0.9, 37, 0.98), 2))
