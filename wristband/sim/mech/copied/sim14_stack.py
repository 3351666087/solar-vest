"""SIM-14  Mechanical tolerance stack of the SolarBand (ARCHITECTURE.md §6.2) with datasheet part heights.

Method
  Every requirement is a 1-D chain  gap = sum(sign_i * d_i). Each contributor d_i is (min, max) -> mean +- half-range t_i.
    worst case (WC) : mean -/+ sum t_i
    RSS             : mean -/+ sqrt(sum t_i^2)    (t_i read as +-3 sigma)
    Monte Carlo (MC): 1e6 samples, every contributor uniform in [min, max] (more pessimistic than normal)
  Enclosure links follow the one-link-per-part rule: each part contributes ONE directly dimensioned feature-to-feature
  (functional) dimension per chain, e.g. the back shell contributes "standoff top -> rim", not "inner face -> rim" and
  "inner face -> standoff top" separately. This is a DRAWING REQUIREMENT (README, "drawing rules"), not an assumption
  that comes for free.
  Verdicts: hard contacts (A part->shell, B3/B4 part->window, C lens->cell, P plan fit) and the optical-gap limits
  (B1/B2) and overall thickness (E) are judged WORST CASE; the swelling allowance (D) is reported WC and RSS and must
  pass WC in the recommended variant.

Datums (v0)
  PCB F.Cu rests on back-shell standoffs (variant "S") or on two legs of the PPG window insert ("W"); the frame
  sits on the back-shell rim (hard stop, gasket in a groove); the PV board rests on frame ribs; the lens on a PSA
  ring on the frame ledge; the battery on tape on L6.

Inputs: mech/geom_v0.py (Z stack, HEIGHTS with datasheet page refs) and design/BOM.csv (the schematic BOM).
Outputs: out/sim14_stack.json, out/sim14_stack.md, out/sim14.log
"""
import csv, json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WB = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(WB, "mech"))
import geom_v0 as G   # noqa: E402

OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
H = {k: v["h"] for k, v in G.HEIGHTS.items()}
Z = G.Z
NMC = 1_000_000
SOLD = (G.SOLDER_STANDOFF[0], G.SOLDER_STANDOFF[2])
SRC_SOLD = "reflowed solder under the body, 0.10 mm stencil [E]"
FLAT = (-0.06, 0.06)
SRC_FLAT = "PCB local flatness between supports: IPC-6012 0.75 % bow/twist x 16 mm span, halved by clamping [E]"
FLAT_W = (-0.03, 0.03)
SRC_FLAT_W = ("PCB flatness between the two window-insert legs (10.0 mm span, geom_v0.WINDOW_INSERT): 0.75 % bow over the "
              "46.6 mm diagonal as a circular arc -> 0.35 x (10/46.6)^2 = 0.016 mm, x2 margin [E]")
LEDS = {"LT_QH9G": "LT QH9G (ARCH D3/D4)", "XL_1005UGC": "XL-1005UGC (schematic, BOM D-1)", "LTST_C281": "LTST-C281TGKT-5A (alt)"}
CELL_MAX = 3.5     # EEMB LiPo overview p1 LP301230 3.5 x 12.5 x 31 (treated as the max envelope) [OPEN] no LP301230 sheet
SWELL = 0.08       # [task / ARCH §6.2] swelling allowance >= 8 % of the cell envelope


def sym(nom, tol):
    return (nom - tol, nom + tol)


def chain(name, terms, req, limit, judge="wc", note="", rng=None):
    mean = sum(s * 0.5 * (lo + hi) for (_, s, (lo, hi), _) in terms)
    t = [0.5 * (hi - lo) for (_, _, (lo, hi), _) in terms]
    wc_tol, rss_tol = sum(t), math.sqrt(sum(x * x for x in t))
    x = np.zeros(NMC)
    for (_, s, (lo, hi), _) in terms:
        x += s * rng.uniform(lo, hi, NMC)
    if req == ">=":
        wc, rss = mean - wc_tol, mean - rss_tol
        ok_wc, ok_rss, p_fail = wc >= limit - 1e-9, rss >= limit - 1e-9, float((x < limit - 1e-12).mean())
    else:
        wc, rss = mean + wc_tol, mean + rss_tol
        ok_wc, ok_rss, p_fail = wc <= limit + 1e-9, rss <= limit + 1e-9, float((x > limit + 1e-12).mean())
    verdict = ok_wc if judge == "wc" else ok_rss
    return dict(name=name, req=f"{req} {limit:g}", judge=judge, mean=mean, worst_case=wc, rss=rss, pass_wc=bool(ok_wc),
                pass_rss=bool(ok_rss), verdict="PASS" if verdict else "FAIL", mc_fail_fraction=p_fail, note=note,
                terms=[dict(label=l, sign=s, min=lo, max=hi, src=src) for (l, s, (lo, hi), src) in terms])


# ----------------------------------------------------------------------------------- functional dimensions
M05 = "moulded PC +-0.05 [E, ISO 20457 fine class, features < 10 mm]"
SLA = "JLC3DP SLA resin +-0.2 [JLC3DP design guideline, cache/web/thermal/sources_thermal_mech.md]"
CNC = "CNC-machined PC +-0.05 [E] (JLC CNC capability not checked [OPEN])"
GLASS = "window glass thickness +-0.05 [E]"


def dims(back=(0.05, M05), frame=(0.05, M05), t_bs=Z.t_backshell, extra_space=0.0, extra_d3=0.0, lens=Z.t_lens,
         ppg="S", glass=(0.05, GLASS)):
    """Functional dimensions (nominal, +-tol, source). One per part per chain.
    extra_space: raises the PV ribs (more battery space); extra_d3: raises the lens ledge above the PV ribs."""
    tb, sb = back
    tf, sf = frame
    so_in = Z.h_standoff                                   # standoff top -> shell inner face (general zone)
    so_rim = Z.joint_z - Z.z_fcu + (t_bs - Z.t_backshell)  # standoff top -> rim (joint)
    rim_rib = Z.z_pvb_bot - Z.joint_z + extra_space        # rim seat -> PV-rib top
    rib_ledge = Z.z_ledge - Z.z_pvb_bot + extra_d3         # PV-rib top -> lens-ledge top
    glass_t = G.MESA["h"] + Z.t_backshell + G.P_WIN       # window glass, mesa face -> window inner face (1.55)
    so_mesa = Z.z_fcu + G.MESA["h"] + (t_bs - Z.t_backshell)   # standoff top -> mesa face (glass outer face bonded flush)
    d = {
        "so_in": (so_in, tb, "back shell: standoff top -> inner face; " + sb),
        "so_pocket": (so_in + G.TALL_POCKET, tb, "back shell: standoff top -> tall-zone pocket floor; " + sb),
        "so_local": (so_in + 0.15, tb, "back shell: standoff top -> U7 local-pocket floor; " + sb),
        "so_u3": (so_in + 0.60, tb, "back shell: standoff top -> 0.60 local pocket floor (U3 DBV option); " + sb),
        "so_mesa": (so_mesa, tb, "back shell: standoff top -> mesa face; " + sb),
        "glass": (glass_t, glass[0], glass[1]),
        "leg": (so_mesa - glass_t, tb, f"window insert: inner face -> leg tip (one part) +-{tb:g}; " + sb),
        "so_rim": (so_rim, tb, "back shell: standoff top -> rim; " + sb),
        "mesa_rim": (G.MESA["h"] + Z.joint_z + (t_bs - Z.t_backshell), tb, "back shell: mesa face -> rim; " + sb),
        "rim_rib": (rim_rib, tf, "frame: rim seat -> PV-rib top; " + sf),
        "rib_ledge": (rib_ledge, tf, "frame: PV-rib top -> lens-ledge top; " + sf),
        "rim_ledge": (rim_rib + rib_ledge, tf, "frame: rim seat -> lens-ledge top; " + sf),
        "psa": (Z.t_lens_psa, 0.02, "lens PSA ring 0.10 +-0.02 [E]"),
        "lens": (lens, 0.05, "chemically strengthened glass +-0.05 [E]"),
        "tape": (Z.t_tape, 0.02, "battery tape, double-sided PE foam 0.15 +-0.02 [E]"),
        "ppg": (ppg, 0, ""),
        "t_bs": (t_bs, 0, ""),
    }
    return d


def T(d, k):
    return sym(d[k][0], d[k][1])


def variant(name, d, notes="", rng=None, leds=tuple(LEDS)):
    R = []
    PCB = ("PCB 0.8 +-0.1", -1, sym(0.8, 0.1), "JLC: thickness tolerance +-0.1 below 1.0 mm (cache/web/jlc/jlcpcb_pcb-capabilities.html)")
    sold = ("solder standoff", -1, SOLD, SRC_SOLD)
    flat = ("PCB local flatness", -1, FLAT, SRC_FLAT)

    def a_chain(label, link, hkey, refs):
        lo, _, hi = H[hkey]
        return chain(f"A {label}: {hkey} ({refs}) -> back shell", [
            (d[link][2].split(";")[0], +1, T(d, link), d[link][2]), flat,
            (f"part height {hkey}", -1, (lo, hi), G.HEIGHTS[hkey]["src"]), sold], ">=", 0.0, "wc", rng=rng)
    gen = max((p[1] for p in G.PARTS if p[6] == "general"), key=lambda k: H[k][2])
    tall = max((p[1] for p in G.PARTS if p[6] == "tall"), key=lambda k: H[k][2])
    loc = max((p[1] for p in G.PARTS if p[6] == "local"), key=lambda k: H[k][2])
    R.append(a_chain("general zone, tallest", "so_in", gen, G.HEIGHTS[gen]["refs"]))
    R.append(a_chain("tall-part zone, tallest", "so_pocket", tall, G.HEIGHTS[tall]["refs"]))
    R.append(a_chain("U7 local pocket", "so_local", loc, "U7"))
    R.append(a_chain("schematic U3 TPS7A0230PDBVR in the tall-zone pocket", "so_pocket", "SOT-23-5_DBV", "U3 as captured"))
    if d["so_u3"] is not None:
        R.append(a_chain("schematic U3 DBV in a 0.60 mm local pocket (option)", "so_u3", "SOT-23-5_DBV", "U3 as captured"))
    # B: PPG optical gap, for every LED option
    if d["ppg"][0] == "S":
        base = [(d["so_mesa"][2].split(";")[0], +1, T(d, "so_mesa"), d["so_mesa"][2]),
                ("window glass, mesa face -> inner face", -1, T(d, "glass"), d["glass"][2]), flat]
    else:
        base = [(d["leg"][2].split(";")[0], +1, T(d, "leg"), d["leg"][2]),
                ("PCB flatness between the legs", -1, FLAT_W, SRC_FLAT_W)]
    pd = H["VEMD8080"]
    pdt = [("PD VEMD8080 height", -1, (pd[0], pd[2]), G.HEIGHTS["VEMD8080"]["src"]), sold]
    R.append(chain("B2 PPG PD -> window air gap at min material", base + pdt, "<=", 0.8, "wc", "ADI <= 0.8 mm [PV §5.3]", rng=rng))
    R.append(chain("B3 PPG PD -> window clearance at max material (no contact)", base + pdt, ">=", 0.0, "wc", rng=rng))
    for lk in leds:
        led = H[lk]
        lt = [(f"LED {LEDS[lk]} height", -1, (led[0], led[2]), G.HEIGHTS[lk]["src"]), sold]
        R.append(chain(f"B1 PPG LED -> window air gap at min material [{LEDS[lk]}]", base + lt, "<=", 0.8, "wc",
                       "ADI <= 0.8 mm [PV §5.3]", rng=rng))
        R.append(chain(f"B4 PPG LED -> window clearance at max material [{LEDS[lk]}]", base + lt, ">=", 0.0, "wc", rng=rng))
    # C: lens -> PV cell air gap
    R.append(chain("C lens -> PV cell clearance at max material (no contact)", [
        (d["rib_ledge"][2].split(";")[0], +1, T(d, "rib_ledge"), d["rib_ledge"][2]),
        ("lens PSA", +1, T(d, "psa"), d["psa"][2]),
        ("PV board 0.6 +-0.1", -1, sym(0.6, 0.1), "JLC 2-layer 0.6: thickness tolerance +-0.1 [JLC capabilities]"),
        ("SnBi joint", -1, (0.02, 0.08), "[E] hot-plate SnBi joint under the cell"),
        ("PV cell 1.2 +-0.3", -1, sym(1.2, 0.3), "ANYSOLAR KXOB121K04TF / KXOB25-03X4TF p1 'H 1.2 +- 0.3'"),
    ], ">=", 0.0, "wc", "ANYSOLAR: no coating on the cells, keep an air gap [PV §1.1]", rng=rng))
    # D: battery compartment and swelling
    space = [(d["so_rim"][2].split(";")[0], +1, T(d, "so_rim"), d["so_rim"][2]),
             (d["rim_rib"][2].split(";")[0], +1, T(d, "rim_rib"), d["rim_rib"][2]),
             PCB, flat, ("battery tape", -1, T(d, "tape"), d["tape"][2])]
    cell = ("LP301230 envelope 3.5 (max)", -1, (CELL_MAX, CELL_MAX), "EEMB LiPo overview p1: LP301230 3.5 x 12.5 x 31 (read as max [OPEN])")
    R.append(chain(f"D1 free gap above the cell at max material (swelling allowance >= {SWELL*100:.0f} % of {CELL_MAX})",
                   space + [cell], ">=", SWELL * CELL_MAX, "wc", "[task, ARCH §6.2] swelling allowance >= 8 %", rng=rng))
    R.append(chain("D2 cell swollen by 8 % still clears the PV board", space + [
        ("LP301230 3.5 x 1.08", -1, (CELL_MAX * (1 + SWELL),) * 2, "EEMB p1 x 1.08")], ">=", 0.0, "wc", rng=rng))
    # E: overall thickness
    over = [(d["mesa_rim"][2].split(";")[0], +1, T(d, "mesa_rim"), d["mesa_rim"][2]),
            (d["rim_ledge"][2].split(";")[0], +1, T(d, "rim_ledge"), d["rim_ledge"][2]),
            ("lens PSA", +1, T(d, "psa"), d["psa"][2]), ("lens", +1, T(d, "lens"), d["lens"][2])]
    R.append(chain("E overall thickness, mesa face -> lens top", over, "<=", 10.5, "wc", "[ARCH §1.4] <= 10.5 mm", rng=rng))
    # F: JLC3DP SLA minimum wall, informative for SLA variants
    if d.get("sla"):
        tb = d["t_bs"][0]
        R.append(dict(name="F back-shell plate vs JLC3DP SLA min wall (1.0 mm for a 50 x 50 part)", req=">= 1", judge="wc", mean=tb,
                      worst_case=tb, rss=tb, pass_wc=tb >= 1.0, pass_rss=tb >= 1.0, verdict="PASS" if tb >= 1.0 else "FAIL",
                      mc_fail_fraction=0.0 if tb >= 1.0 else 1.0, note="JLC3DP 3D printing design guideline", terms=[]))
    # P: plan-view fit and PD alignment
    shell_tol = d["so_in"][1]
    for ax, cavL, brdL in (("X", 40 - 2 * G.WALL, G.BOARD_L), ("Y", 32 - 2 * G.WALL, G.BOARD_W)):
        for lab, bt in (("regular routing +-0.2", 0.2), ("precision routing +-0.1", 0.1)):
            R.append(chain(f"P1 main board in the cavity along {ax} ({lab})", [
                (f"cavity {cavL:.1f} (back shell)", +1, sym(cavL, shell_tol), d["so_in"][2].split(";")[1].strip()),
                (f"board {brdL:.1f}, JLC {lab}", -1, sym(brdL, bt), "JLC: 'Dimension Tolerance +-0.1mm (Precision) and +-0.2mm "
                 "(Regular) for CNC routing, +-0.4mm for V-scoring' (cache/web/jlc/jlcpcb_pcb-capabilities.html)")],
                ">=", 0.0, "wc", "total clearance (both sides); mouse-bite nubs must be sanded or sit at relieved edges", rng=rng))
    # PD optical area inside the window (Y, worst direction): window half-aperture - sensitive-area half-size - shifts
    R.append(chain("P2 PD sensitive area inside the window clear aperture (Y)", [
        ("window half-aperture 2.5", +1, sym(G.WINDOW["W"] / 2, shell_tol), "window 9 x 5 [ARCH §6.3]"),
        ("PD sensitive area half-size", -1, (1.07, 1.07), "VEMD8080 p1: radiant sensitive area 4.6 mm2 -> 2.14 mm square [shape E]"),
        ("board shift in the cavity (floating, worst wall contact)", -1, (0.0, 0.5 * (32 - 2 * G.WALL + shell_tol - (G.BOARD_W - 0.2))),
         "half the max total Y clearance, regular routing"),
        ("PD placement on the board", -1, (0.0, 0.10), "[E] JLC SMT placement"),
    ], ">=", 0.0, "wc", "locating pins would remove the float term", rng=rng))
    nom_over = sum(0.5 * (lo + hi) for (_, _, (lo, hi), _) in over)
    return dict(variant=name, notes=notes, dims={k: (list(v) if isinstance(v, tuple) else v) for k, v in d.items() if v is not None}, overall_nominal=nom_over, results=R)


# ------------------------------------------------------------------------------------------- BOM table
BOM_MAP = {   # LCSC -> HEIGHTS key (every skin-side part of design/BOM.csv)
    "C19666": "0603_MLCC_0.8", "C19702": "0603_MLCC_0.8", "C85973": "0603_MLCC_0.8", "C29936": "0603_MLCC_0.8",
    "C85980": "0603_MLCC_0.8", "C59461": "0603_MLCC_22u", "C15525": "0402_MLCC_10u", "C52923": "0402_MLCC_1u",
    "C1525": "0402_PASSIVE", "C15195": "0402_PASSIVE", "C161527": "0402_PASSIVE", "C88902": "0402_PASSIVE",
    "C1546": "0402_PASSIVE", "C325459": "0402_PASSIVE", "C1555": "0402_PASSIVE", "C668348": "0402_PASSIVE",
    "C5452416": "0402_PASSIVE", "C86059": "0402_PASSIVE", "C6807729": "MPH160809",
    "C2050114": "VLS201610CX", "C434843": "VLS201610CX", "C2041554": "VLS201610CX",
    "C48502": "SOT23_BAS116", "C10488": "SOT-23_Si2302", "C48260": "X1SON_DPY", "C965793": "XL_1005UGC",
    "C511402": "VEMD8080", "C861215": "0603_RES", "C441935": "0603_RES",
    "C506250": "VQFN20_RGR", "C2842395": "WSON6_DRV", "C3747031": "SOT-23-5_DBV", "C5443912": "TSOT-23-8_DDF",
    "C77540": "QFN48_nRF", "C139059": "VQFN32_RSM", "C5328762": "MAX86141", "C189624": "LGA12_LIS2DW12",
    "C2803242": "WSON6_DRV", "C5687033": "USON8_MX25R", "C718072": "X201632", "C97604": "SC-32S",
}
R0402 = ("0402 thick-film resistor (UNI-ROYAL 0402WGF) 0.35 +-0.05 class, <= 0.55 [E, not individually checked; "
         "never the driving dimension]")


def allowances(d):
    """Max part height (body, above the pad) that still clears at worst case, per zone."""
    f = FLAT[1]; s = SOLD[1]
    out = {
        "general zone": d["so_in"][0] - d["so_in"][1] - f - s,
        "tall-part zone (0.45 pocket)": d["so_pocket"][0] - d["so_pocket"][1] - f - s,
        "U7 local pocket (0.15)": d["so_local"][0] - d["so_local"][1] - f - s,
    }
    if d["ppg"][0] == "S":
        out["under the PPG window"] = (d["so_mesa"][0] - d["so_mesa"][1]) - (d["glass"][0] + d["glass"][1]) - f - s
    else:
        out["under the PPG window"] = d["leg"][0] - d["leg"][1] - FLAT_W[1] - s
    return out


def bom_table(allow):
    rows = []
    fn = os.path.join(WB, "design", "BOM.csv")
    for r in csv.DictReader(open(fn)):
        lc = r["LCSC"]
        if lc in BOM_MAP:
            k = BOM_MAP[lc]; hmax = H[k][2]; src = G.HEIGHTS[k]["src"]
        elif r["Footprint"].endswith("R0402") or "_R0402" in r["Footprint"]:
            k = "0402_RES"; hmax = 0.55; src = R0402
        else:
            k = "?"; hmax = float("nan"); src = "UNMAPPED"
        if k in ("VEMD8080", "XL_1005UGC"):
            zone = "PPG window (PASS)" if hmax <= allow["under the PPG window"] + 1e-9 else \
                   f"PPG window: FAIL at WC ({hmax:.2f} > {allow['under the PPG window']:.2f})"
        elif hmax <= allow["general zone"] + 1e-9:
            zone = "any (general zone)"
        elif hmax <= allow["U7 local pocket (0.15)"] + 1e-9:
            zone = "TALL-PART ZONE or a 0.15 local pocket"
        elif hmax <= allow["tall-part zone (0.45 pocket)"] + 1e-9:
            zone = "TALL-PART ZONE ONLY"
        else:
            zone = "DOES NOT FIT: change package or add a deeper local pocket"
        rows.append(dict(refs=r["Designator"], part=r["MPN"], lcsc=lc, key=k, h_max=hmax, zone=zone, src=src))
    return rows


# --------------------------------------------------------------------------------------------- variants
def run():
    rng = np.random.default_rng(14)
    arch = dims()
    # ARCHITECTURE.md §6.2 as written: 1.1 mm cavity for every part (no pockets), window flush (no protrusion is
    # favourable), lens 0.70, foam 0.2 counted under the cell, no lens PSA, swelling 0.30 nominal
    arch.update({
        "so_pocket": (1.10, 0.05, "§6.2: one 1.1 mm skin-side cavity, no pockets; " + M05),
        "so_local": (1.10, 0.05, "§6.2: no pocket; " + M05), "so_u3": None,
        "so_mesa": (1.10 + 0.7 + 0.6, 0.05, "§6.2: standoff top -> mesa face; " + M05),
        "glass": (1.30, 0.05, "§6.2 window in the 0.7 shell + 0.6 mesa, inner face flush with the shell inner face (favourable reading)"),
        "so_rim": (2.5 - 1.1 + 0.0, 0.05, "back shell; " + M05),
        "rim_rib": (3.50, 0.05, "§6.2: PV board bottom at Z 6.7 (PCB 0.9 max + swelling 0.3 + cell 3.5 + foam 0.2 above F.Cu 1.8); " + M05),
        "rib_ledge": (0.7 + 1.55 + 0.2, 0.05, "§6.2 PV board 0.7 + cells 1.55 + air 0.2; " + M05),
        "mesa_rim": (0.6 + 2.5 + 0.7, 0.05, "back shell; " + M05),
        "psa": (0.0, 0.0, "§6.2 lists no lens PSA"), "lens": (0.70, 0.05, "[ARCH §6.2] 0.70"),
        "tape": (0.20, 0.02, "§6.2 foam/PSA 0.2 (counted under the cell here)"),
    })
    arch["rim_ledge"] = (arch["rim_rib"][0] + arch["rib_ledge"][0], 0.05, "frame; " + M05)
    gen_all = dict(arch)
    V = [
        variant("ARCH §6.2 as written (moulded +-0.05, one 1.1 mm skin-side cavity, U3 SOT-23-5, lens 0.70)", gen_all,
                "the part-height chains A use the v0 zone assignment; ARCH has no pockets, so 'tall zone' = general here", rng),
        variant("V0-PRODUCT-S (moulded PC +-0.05, PCB on back-shell standoffs)", dims(), "", rng),
        variant("V0-PRODUCT-W (moulded PC +-0.05, PCB on two legs of the PPG window insert) - RECOMMENDED", dims(ppg="W"), "", rng),
        variant("V0-PROTO-A (CNC back shell + window insert +-0.05, JLC3DP SLA frame +-0.2)",
                dims(back=(0.05, CNC), frame=(0.2, SLA), ppg="W"), "", rng),
        variant("V0-PROTO-A+ (as PROTO-A, +0.30 battery space, +0.15 lens ledge: prototype-only thickness)",
                dims(back=(0.05, CNC), frame=(0.2, SLA), ppg="W", extra_space=0.30, extra_d3=0.15), "", rng),
        variant("V0-PROTO-B (all JLC3DP SLA +-0.2, back shell 1.0 per JLC3DP, window-leg datum)",
                dict(dims(back=(0.2, SLA), frame=(0.2, SLA), t_bs=1.0, ppg="W"), sla=True), "", rng),
    ]
    allow = {v["variant"]: allowances({k: (tuple(x) if isinstance(x, list) else x) for k, x in v["dims"].items()}) for v in V[1:3]}
    bom = bom_table(allowances(dims(ppg="W")))
    return V, allow, bom


def md(V, allow, bom):
    L = ["# SIM-14 tolerance stack: results", "",
         "Generated by `sim14_stack.py` (rev b). WC = worst case, RSS = root-sum-square (each tolerance read as +-3 sigma), "
         "MC = Monte Carlo exceedance with uniform contributors (1e6 samples). Every chain is judged worst case. "
         "Enclosure links are functional dimensions, one per part per chain (drawing rule).", ""]
    for v in V:
        L += [f"## {v['variant']}", "", f"Nominal overall thickness {v['overall_nominal']:.2f} mm. {v['notes']}", "",
              "| check | requirement | mean | worst case | RSS | verdict (WC) | RSS verdict | MC exceed |",
              "|---|---|---|---|---|---|---|---|"]
        for r in v["results"]:
            L.append(f"| {r['name']} | {r['req']} | {r['mean']:.3f} | {r['worst_case']:.3f} | {r['rss']:.3f} | "
                     f"**{r['verdict']}** | {'pass' if r['pass_rss'] else 'fail'} | {r['mc_fail_fraction']*100:.3f} % |")
        L.append("")
    L += ["## Maximum part height per zone that still clears at worst case (body height above the pad, mm)", "",
          "| zone | " + " | ".join(allow) + " |", "|---|" + "---|" * len(allow)]
    zones = list(next(iter(allow.values())))
    for z in zones:
        L.append(f"| {z} | " + " | ".join(f"{allow[v][z]:.3f}" for v in allow) + " |")
    L += ["", "## Every skin-side BOM line (design/BOM.csv) against the V0-PRODUCT-W allowances", "",
          "| refs | part | LCSC | height key | max h | where it may go | source |", "|---|---|---|---|---|---|---|"]
    for r in sorted(bom, key=lambda r: -(r["h_max"] if r["h_max"] == r["h_max"] else 9)):
        L.append(f"| {r['refs']} | {r['part']} | {r['lcsc']} | {r['key']} | {r['h_max']:.2f} | {r['zone']} | {r['src']} |")
    rec = V[2]
    L += ["", f"## Contributors of the recommended variant ({rec['variant']})", ""]
    for r in rec["results"]:
        if not r["terms"]:
            continue
        L += [f"**{r['name']}**  (mean {r['mean']:.3f}, WC {r['worst_case']:.3f}, RSS {r['rss']:.3f}, {r['verdict']})", "",
              "| term | sign | min | max | source |", "|---|---|---|---|---|"]
        for t in r["terms"]:
            L.append(f"| {t['label']} | {'+' if t['sign'] > 0 else '-'} | {t['min']:.3f} | {t['max']:.3f} | {t['src']} |")
        L.append("")
    L += ["## Skin-side part heights (seated body height above the pad, mm)", "",
          "| key | refs | min | nom | max | source |", "|---|---|---|---|---|---|"]
    for k, v in sorted(G.HEIGHTS.items(), key=lambda kv: -kv[1]["h"][2]):
        L.append(f"| {k} | {v['refs']} | {v['h'][0]:.2f} | {v['h'][1]:.2f} | {v['h'][2]:.2f} | {v['src']} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    V, allow, bom = run()
    json.dump(dict(variants=V, zone_allowances=allow, bom=bom), open(os.path.join(OUT, "sim14_stack.json"), "w"), indent=1, default=float)
    open(os.path.join(OUT, "sim14_stack.md"), "w").write(md(V, allow, bom))
    for v in V:
        print(f"== {v['variant']}   (nominal overall {v['overall_nominal']:.2f})")
        for r in v["results"]:
            print(f"   {r['name'][:84]:84s} {r['req']:>7s} mean {r['mean']:7.3f} WC {r['worst_case']:7.3f} RSS {r['rss']:7.3f} "
                  f"{r['verdict']:4s} MC {r['mc_fail_fraction']*100:7.3f}%")
    print("zone allowances:", json.dumps(allow, indent=1))
    for r in bom:
        if "general" not in r["zone"] and "PASS" not in r["zone"]:
            print(f"   BOM {r['refs']:<14s} {r['part']:<22s} max {r['h_max']:.2f} -> {r['zone']}")
    print("unmapped:", [r["refs"] for r in bom if r["key"] == "?"])
