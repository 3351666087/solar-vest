"""Stage 1 (C-1, C-10, C-19): 5-bar check of the window glass on the stage-1 supports, BASELINE 13.4 method (Navier plate, simply supported
upper bound; clamped ~3.2x is BASELINE's factor, not used for a pass here), and the antenna-side rail as a beam between its posts.
Inputs: v3/cad/src/geom_v3f.py (read-only import: supports, Z levels). Method copied from the stage-1 CAD review (indep/check1.py navier()),
which reproduces BASELINE's 4.33 bar SS on 33 x 14.5 mm. All results E (model). Writes window_plate_s1.json next to this file.
usage: python3 -B window_plate_s1.py"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/path/to/SolarVest_work/wristband/v3/cad/src")
os.environ.setdefault("V3F_POD_L", "40")
import geom_v3f as G   # noqa: E402
Z = G.Z


def navier_w(a, b, t, q, E=70e3, nu=0.22, terms=79):
    """centre deflection (mm) of a simply supported a x b plate, thickness t, pressure q (MPa)"""
    D = E * t ** 3 / (12 * (1 - nu ** 2)); w = 0.0
    for m in range(1, terms + 1, 2):
        for n in range(1, terms + 1, 2):
            s = (-1) ** ((m + n) // 2 - 1); w += s / (m * n * (m * m / a ** 2 + n * n / b ** 2) ** 2)
    return w * 16 * q / (math.pi ** 6 * D)


def contact_bar(a, b, t, gap):
    """pressure (bar) at which the SS plate centre closes the gap"""
    return gap / navier_w(a, b, t, 0.1) * 1.0     # w is linear in q; 0.1 MPa = 1 bar


R = {}
R["check_BASELINE_33x14p5_t0.70_gap0.10_SS_bar"] = round(contact_bar(33.0, 14.5, 0.70, 0.10), 2)        # BASELINE 13.4: 4.3
# stage-0 CAD span (review C-1): X 1.0-37.0, Y 1.0-20.0, gap 0.045 at the max-material panel
R["stage0_cad_36x19_t0.70_gap0.10_SS_bar"] = round(contact_bar(36.0, 19.0, 0.70, 0.10), 2)
R["stage0_cad_36x19_t0.70_gap0.045_SS_bar"] = round(contact_bar(36.0, 19.0, 0.70, 0.045), 2)
# stage-1 span: elbow wall X 1.0 to the E3 shelf X 37.0; rail top edge Y 5.4 to the rib insert Y 20.0
a = (G.E3_BLOCK["x0"]) - G.WALL; b = G.INSERT["y0"] - G.RAIL["y1"]
gap = Z.film0 - (Z.panel0 + G.PANEL_NOM["t"] + G.PANEL_NOM["t_tol"])           # air gap at the max-material panel (C-10: 0.10)
R["stage1_span_mm"] = [round(a, 2), round(b, 2)]; R["stage1_gap_at_max_panel_mm"] = round(gap, 3)
R["stage1_t0.70_SS_bar"] = round(contact_bar(a, b, 0.70, gap), 2)
R["stage1_t0.70_clamped_long_edges_E_bar"] = round(contact_bar(a, b, 0.70, gap) * 3.2, 1)   # BASELINE's ~3.2x factor (E)
for t in (0.80, 0.90, 1.0):
    R[f"stage1_t{t:.2f}_SS_bar"] = round(contact_bar(a, b, t, gap), 2)
# glass thickness for 5 bar SS (bisection)
lo, hi = 0.5, 2.0
for _ in range(60):
    m = (lo + hi) / 2
    if contact_bar(a, b, m, gap) < 5.0: lo = m
    else: hi = m
R["stage1_t_needed_for_5bar_SS_mm"] = round(hi, 3)
# rail between posts: simply supported beam, line load = q x (b / 2) (half the window span) at 5 bar
q5 = 0.5                                   # MPa
w_line = q5 * b / 2                        # N/mm
E_r = G.RAIL_E_GPA * 1e3
hb = (Z.win_seat - Z.rail0); hb_ant = (Z.ant_seat - Z.rail0); bw = G.RAIL["y1"] - G.RAIL["y0"]
I = bw * hb ** 3 / 12; I_ant = bw * hb_ant ** 3 / 12
gaps = [G.RAIL_POST_X[i + 1] - G.RAIL_POST_X[i] for i in range(len(G.RAIL_POST_X) - 1)]
defl = [5 * w_line * p ** 4 / (384 * E_r * (I_ant if G.RAIL_POST_X[i] < 11.45 else I)) for i, p in enumerate(gaps)]
R["rail"] = dict(line_load_N_per_mm_5bar=round(w_line, 2), section_mm=[bw, round(hb, 3)], section_antenna_part_mm=[bw, round(hb_ant, 3)],
                 E_GPa_assumed=G.RAIL_E_GPA, post_gaps_mm=gaps, deflection_between_posts_mm=[round(d, 4) for d in defl],
                 max_deflection_mm=round(max(defl), 4), criterion_mm=0.05, ok=max(defl) <= 0.05,
                 note="E: GF-LCP E 12 GPa assumed (grade not chosen); criterion as the PV rib (BASELINE 13.4: <= 0.05 mm between posts)")
# rib insert 0.5 x 0.755 stainless between posts (window + laminate halves on it)
Ei = 193e3; Ii = 0.5 * (Z.insert1 - Z.insert0) ** 3 / 12
w_rib = q5 * (b / 2 + 10.45 / 2)                    # window half-span + half the laminate span (Y 21.0-31.45) [E]
pg = max(G.POST_X[i + 1] - G.POST_X[i] for i in range(len(G.POST_X) - 1))
R["rib_insert"] = dict(section_mm=[0.5, round(Z.insert1 - Z.insert0, 3)], line_load_N_per_mm_5bar=round(w_rib, 2), max_post_gap_mm=pg,
                       deflection_mm=round(5 * w_rib * pg ** 4 / (384 * Ei * Ii), 4), criterion_mm=0.05)
R["verdict"] = ("5 bar holds only with the structural bond on the rail and the rib insert (SS bound {:.2f} bar < 5; clamped long edges ~{:.0f} bar, E): "
                "the same basis as BASELINE 13.4 (4.3 bar SS / about 14 clamped on 33 x 14.5); SIM-14 decides").format(R["stage1_t0.70_SS_bar"], R["stage1_t0.70_clamped_long_edges_E_bar"])
json.dump(R, open(os.path.join(HERE, "window_plate_s1.json"), "w"), indent=1)
print(json.dumps(R, indent=1))
