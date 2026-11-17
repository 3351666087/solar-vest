"""SIM-13 lumped RC thermal network of the SolarBand (first-principles conductances, no fitting).

Nodes: L lens, F frame (upper walls + rim + ledge + PV ribs), C PV cells, P PV board, B battery, M main PCBA,
S back shell (+ lower walls, mesa, window, E2), E E1 electrode + pedestal, T TMP117 island/package.
Fixed: ambient, skin.  Steady state for W-S / W-C, transient for shade->sun->shade steps (TMP117 lag, time to
the 45 C charge-inhibit), and comparison against the 3-D FV model (out/fv3d_results.json).

Every conductance is computed below from geometry (mech/geom_v0.py) and materials.py; the comments give the
arithmetic. They are estimates (E) whose purpose is the transient and a cross-check of the 3-D model.
"""
import json, math, os, sys
import numpy as np
from scipy.integrate import solve_ivp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "mech"))
import geom_v0 as G                                   # noqa: E402
from materials import MAT, SOLAR, PV, ENV, h_rad     # noqa: E402

OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
NODES = ["L", "F", "C", "P", "B", "M", "S", "E", "T"]
ix = {n: i for i, n in enumerate(NODES)}
mm2 = 1e-6


def k(m, d="z"):
    return MAT[m][1] if d == "z" else MAT[m][0]


def network(p):
    """Returns (Gnode dict {(a,b): W/K}, G_amb {node: W/K}, G_skin {node: W/K}, C {node: J/K})."""
    hT = p["h_top"] + h_rad(SOLAR["eps_lens"]); hS = p["h_side"] + h_rad(SOLAR["eps_shell"])
    A_top = 40 * 32 - (4 - math.pi) * 36            # 1249 mm2
    A_lens = G.LENS["L"] * G.LENS["W"] - (4 - math.pi) * G.LENS["R"] ** 2
    A_rim = A_top - A_lens
    A_cells = sum(c["L"] * c["W"] for c in G.PV_CELLS)
    perim = 2 * (40 + 32) - 8 * 6 + 2 * math.pi * 6  # 133.7 mm
    A_bat = G.BATTERY["L"] * G.BATTERY["W"]
    A_pvb = G.PV_BOARD["L"] * G.PV_BOARD["W"]
    A_board = G.BOARD_L * G.BOARD_W - (4 - math.pi) * G.BOARD_R ** 2
    Rc = p["R_c"]
    g = {}
    ga = {}
    gs = {}
    # to ambient
    ga["L"] = hT * A_lens * mm2
    ga["F"] = hT * A_rim * mm2 + hS * perim * (p["z_top"] - G.Z.joint_z) * mm2
    ga["S"] = hS * perim * G.Z.joint_z * mm2
    # lens <-> frame: PSA ring (1.5 mm x lens perimeter, 0.15 mm, 0.2 W/mK) in series with in-plane spreading of a
    # uniformly heated 0.7 mm glass plate to its edge, R = 1/(8 pi k t)
    psa = 0.2 * (1.5 * (2 * (G.LENS["L"] + G.LENS["W"]))) * mm2 / 0.15e-3
    R_lat = 1 / (8 * math.pi * k("glass") * G.Z.t_lens * 1e-3)
    g[("L", "F")] = 1 / (R_lat + 1 / psa)
    # cells <-> lens: air gap
    g[("C", "L")] = k("air") * A_cells * mm2 / (p["lens_gap"] * 1e-3)
    # cells <-> PV board: half cell + joint + half PV board (through-plane)
    R_cp = (0.6e-3 / (k("pv_cell") * A_cells * mm2) + 0.05e-3 / (k("snbi_jnt") * A_cells * mm2) +
            0.3e-3 / (k("pv_board") * A_pvb * mm2))
    g[("C", "P")] = 1 / R_cp
    # PV board <-> frame: two resin ribs (1 x 24 mm, 0.7 mm tall) + edge air (perimeter x 0.6 mm over ~1 mm)
    g[("P", "F")] = k("resin") * 2 * 24 * mm2 / 0.7e-3 * 0.5 + k("air") * 2 * (G.PV_BOARD["L"] + G.PV_BOARD["W"]) * 0.6 * mm2 / 1e-3
    # PV board <-> battery: air swelling gap (z_pvb_bot - z_batt_top) + half battery through-plane
    gap_sw = G.Z.z_pvb_bot - G.Z.z_batt_top
    R_fb = gap_sw * 1e-3 / (k("air") * A_bat * mm2) + (G.Z.t_batt_max / 2) * 1e-3 / (k("battery") * A_bat * mm2)
    g[("P", "B")] = 1 / R_fb
    # PV board <-> PCB through the air cavity beside the battery (~4 mm)
    g[("P", "M")] = k("air") * (A_pvb - A_bat) * mm2 / 4.0e-3
    # battery <-> PCB: 0.15 mm PE-foam tape (minus the TMP117 cut-out) + half battery + half PCB (z)
    A_hole = (p["island"] + 3) ** 2
    R_bm = (G.Z.t_tape * 1e-3 / (k("pe_tape") * (A_bat - A_hole) * mm2) + (G.Z.t_batt_max / 2) * 1e-3 / (k("battery") * A_bat * mm2) +
            0.4e-3 / (k("pcb") * A_bat * mm2))
    g[("B", "M")] = 1 / R_bm
    # battery sides <-> frame walls via ~2 mm of air
    g[("B", "F")] = k("air") * 2 * (G.BATTERY["L"] + G.BATTERY["W"]) * G.Z.t_batt_max * mm2 / 2.0e-3
    # PCB <-> back shell: 1.1 mm air cavity over the board (minus parts), parts with ~0.4 mm mean gap, 6 resin posts,
    # board edge 0.2 mm from the wall (perimeter x 0.8 mm), half shell resin
    A_parts = sum(L * W for (_, _, _, _, L, W, _) in G.PARTS) + sum(q["L"] * q["W"] for q in G.PPG_PARTS)
    g_cav = (k("air") * (A_board - A_parts - 36) * mm2 / 1.1e-3 + k("air") * A_parts * mm2 / 0.4e-3 +
             6 * k("resin") * math.pi * 0.8 ** 2 * mm2 / 1.1e-3)
    g_edge = k("air") * 2 * (G.BOARD_L + G.BOARD_W) * 0.8 * mm2 / 0.2e-3
    g[("M", "S")] = 1 / (1 / (g_cav + g_edge) + 0.35e-3 / (k("resin") * A_board * mm2))
    # frame <-> back shell across the joint: wall cross-section over ~4 mm
    g[("F", "S")] = k("resin") * perim * G.WALL * mm2 / 4.0e-3
    # TMP117 island: to PCB via 4 slot bridges (6 x 0.1 mm x 35 um Cu traces + FR4 bridges, 1 mm long)
    isl = p["island"]
    g[("T", "M")] = (390 * 6 * 0.1 * 0.035 + 0.3 * 4 * 1 * 0.8) * mm2 / 1e-3 if p["slot"] else 0.3 * 4 * isl * 0.8 * mm2 / 0.5e-3
    # to battery: FR4 keep-out column (0.75 mm) + air hole (0.3 mm) above the island
    A_ko = (isl + 1) ** 2
    g[("T", "B")] = 1 / (0.75e-3 / (k("pcb_ko") * A_ko * mm2) + G.Z.t_tape * 1e-3 / ((k("air") if p["foam_hole"] else k("pe_tape")) * A_ko * mm2))
    # island -> E1: gap pad (pedestal area minus the 2.4 mm recess) + 316L pedestal
    A_ped = p["pedestal"] ** 2 - 2.4 ** 2
    R_te = p["pad_t"] * 1e-3 / (p["k_pad"] * A_ped * mm2) + (G.Z.z_fcu - p["pad_t"] - 0.3) * 1e-3 / (k("steel316") * p["pedestal"] ** 2 * mm2)
    g[("T", "E")] = 1 / R_te
    # E1 <-> back shell (sides in the resin pocket) and <-> PCB (air above E1 outside the pedestal)
    g[("E", "S")] = k("resin") * 2 * (G.E1["L"] + G.E1["W"]) * G.ELECTRODE_T * mm2 / 1.0e-3
    g[("E", "M")] = k("air") * (G.E1["L"] * G.E1["W"] - p["pedestal"] ** 2) * mm2 / 1.1e-3
    # skin
    A_c = p["A_contact"]
    A_E1 = G.E1["L"] * G.E1["W"]
    gs["E"] = A_E1 * mm2 / Rc
    g_shell_through = k("resin") * A_top * mm2 / 0.35e-3
    gs["S"] = 1 / (1 / ((A_c - A_E1) * mm2 / Rc) + 1 / g_shell_through) + (A_top - A_c) * mm2 * (k("air") * 0.9 / 1.3e-3 + 6.0)
    # capacitances, J/K = rho cp V
    def cap(m, V_mm3):
        return MAT[m][2] * MAT[m][3] * V_mm3 * 1e-9
    C = {
        "L": cap("glass", A_lens * G.Z.t_lens),
        "F": cap("resin", perim * G.WALL * (p["z_top"] - G.Z.joint_z) + (A_top - G.APERTURE["L"] * G.APERTURE["W"]) * 0.6 + 2 * 24 * 2.4 * 0.7),
        "C": cap("pv_cell", A_cells * G.Z.t_cell),
        "P": cap("pv_board", A_pvb * G.Z.t_pvb),
        "B": cap("battery", A_bat * G.Z.t_batt_max),
        "M": cap("pcb", A_board * G.Z.t_pcb) + cap("ic", A_parts * 0.7),
        "S": cap("resin", A_top * G.Z.t_backshell + perim * G.WALL * G.Z.joint_z + G.MESA["L"] * G.MESA["W"] * 0.6),
        "E": cap("steel316", A_E1 * G.ELECTRODE_T + p["pedestal"] ** 2 * 1.1),
        "T": cap("cu_island", isl * isl * 0.035) + cap("ic", 4 * 0.75) + cap("gap_pad", A_ped * p["pad_t"]),
    }
    return g, ga, gs, C


def sources(p, Tcell):
    Gs = p["G"] * mm2
    tl = 1 - SOLAR["lens_R_front"]
    T_lens = tl * (1 - SOLAR["lens_abs"]) * (1 - SOLAR["lens_R_back"])
    A_lens = G.LENS["L"] * G.LENS["W"] - (4 - math.pi) * G.LENS["R"] ** 2
    A_cells = sum(c["L"] * c["W"] for c in G.PV_CELLS)
    A_top = 40 * 32 - (4 - math.pi) * 36
    q = dict.fromkeys(NODES, 0.0)
    q["L"] = Gs * A_lens * tl * SOLAR["lens_abs"] + Gs * (A_lens - A_cells) * tl * (1 - SOLAR["lens_abs"]) * p["alpha_print"]
    q["F"] = Gs * (A_top - A_lens) * p["alpha_frame"]
    q["C"] = Gs * A_cells * T_lens * SOLAR["alpha_cell"]
    irr = p["G"] / 1000 * T_lens
    if p["mode"] == "harvest" and p["G"] > 0:
        P = PV["P_stc"] * irr * (1 + PV["gamma_P"] * (Tcell - 25)); I = P / PV["Vmp"]
        q["C"] -= P
        q["M"] += (1 - PV["eta_harv"]) * (P - I * I * PV["R_sh"]) + I * I * PV["R_sh"] + PV["P_load"]
    elif p["mode"] == "shorted" and p["G"] > 0:
        Isc = PV["Isc_stc"] * irr
        q["C"] -= Isc ** 2 * (PV["R_sh"] + PV["R_q1"] + PV["R_wire"])
        q["M"] += Isc ** 2 * (PV["R_sh"] + PV["R_q1"]) + PV["P_load"]
    else:
        q["M"] += PV["P_load"]
    return q


def matrices(p):
    g, ga, gs, C = network(p)
    n = len(NODES)
    K = np.zeros((n, n)); b = np.zeros(n)
    for (a, c), v in g.items():
        i, j = ix[a], ix[c]
        K[i, i] += v; K[j, j] += v; K[i, j] -= v; K[j, i] -= v
    for a, v in ga.items():
        K[ix[a], ix[a]] += v; b[ix[a]] += v * p["T_amb"]
    for a, v in gs.items():
        K[ix[a], ix[a]] += v; b[ix[a]] += v * p["T_skin"]
    Cv = np.array([C[nm] for nm in NODES])
    return K, b, Cv, g, ga, gs, C


def steady(p):
    K, b, Cv, *_ = matrices(p)
    T = np.full(len(NODES), 50.0)
    for _ in range(20):
        q = sources(p, T[ix["C"]])
        Tn = np.linalg.solve(K, b + np.array([q[nm] for nm in NODES]))
        if np.max(np.abs(Tn - T)) < 1e-6:
            break
        T = Tn
    return dict(zip(NODES, Tn))


def transient(p, profile, t_end, T0=None):
    """profile(t) -> dict of overrides (e.g. G). Returns t, T[n,len(t)]."""
    K, b, Cv, *_ = matrices(p)
    if T0 is None:
        p0 = dict(p); p0.update(profile(-1))
        T0 = np.array([steady(p0)[nm] for nm in NODES])

    def f(t, T):
        pp = dict(p); pp.update(profile(t))
        q = sources(pp, T[ix["C"]])
        return (b + np.array([q[nm] for nm in NODES]) - K @ T) / Cv
    sol = solve_ivp(f, (0, t_end), T0, method="BDF", max_step=5.0, dense_output=True, rtol=1e-6, atol=1e-6)
    t = np.linspace(0, t_end, 1201)
    return t, sol.sol(t)


BASE = dict(G=1000.0, T_amb=ENV["T_amb"], T_skin=ENV["T_skin"], R_c=ENV["R_contact"], h_top=ENV["h_top"], h_side=ENV["h_side"],
            alpha_frame=SOLAR["alpha_frame"], alpha_print=SOLAR["alpha_print"], lens_gap=G.Z.z_lens_bot - G.Z.z_cell_top,
            mode="shorted", island=G.TMP_ISLAND, pedestal=G.PEDESTAL, pad_t=0.2, k_pad=5.0, slot=True, foam_hole=True,
            A_contact=595.0, z_top=G.Z.z_top)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    res = {}
    g, ga, gs, C = network(BASE)
    res["conductances_W_K"] = {f"{a}-{b}": v for (a, b), v in g.items()}
    res["to_ambient_W_K"] = ga; res["to_skin_W_K"] = gs; res["capacitance_J_K"] = C
    res["total_C_J_K"] = sum(C.values())
    for mode in ("harvest", "shorted"):
        p = dict(BASE, mode=mode)
        T = steady(p)
        res[f"steady_{mode}"] = T
        print(mode, {k_: round(v, 2) for k_, v in T.items()})
    # compare with 3-D
    fv = os.path.join(OUT, "fv3d_results.json")
    if os.path.exists(fv):
        F = json.load(open(fv))
        cmp_ = {}
        for mode, tag in (("harvest", "WS_harvest"), ("shorted", "WC_shorted")):
            T = res[f"steady_{mode}"]; r = F[tag]
            cmp_[mode] = {
                "battery (lumped B vs 3-D mean)": (T["B"], r["battery_mean_C"]),
                "PV cells (C vs 3-D mean)": (T["C"], r["pv_cell_mean_C"]),
                "PCB (M vs 3-D mean)": (T["M"], r["pcb_mean_C"]),
                "E1 (E vs 3-D E1 face)": (T["E"], r["E1_face_mean_C"]),
                "TMP117 (T vs 3-D)": (T["T"], r["TMP117_C"]),
                "TMP117 error (T-E)": (T["T"] - T["E"], r["TMP117_error_vs_E1_face_K"]),
            }
        res["vs_3d"] = cmp_
        for mode, d in cmp_.items():
            for kk, (a, b_) in d.items():
                print(f"  {mode:8s} {kk:34s} lumped {a:7.2f}  3-D {b_:7.2f}  diff {a-b_:+.2f}")
    # transient: shade (steady, G=0) -> sun at t=0 for 60 min -> shade for 30 min
    out_tr = {}
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
    for mode, ax in (("shorted", axs[0]), ("harvest", axs[1])):
        p = dict(BASE, mode=mode)
        prof = lambda t: {"G": 0.0} if (t < 0 or t > 3600) else {"G": 1000.0}  # noqa: E731
        t, T = transient(p, prof, 5400)
        for nm, lab in (("C", "PV cells"), ("L", "lens"), ("B", "battery"), ("M", "PCB"), ("S", "back shell"), ("E", "E1"), ("T", "TMP117")):
            ax.plot(t / 60, T[ix[nm]], label=lab)
        ax.axhline(45, color="k", ls=":", lw=0.8); ax.axhline(41, color="r", ls=":", lw=0.8)
        ax.set_xlabel("min"); ax.set_ylabel("°C"); ax.set_title(f"lumped RC, shade->sun(1000 W/m², 35 °C)->shade, {mode}")
        ax.grid(alpha=0.3); ax.legend(fontsize=7, ncol=2)
        B = T[ix["B"]]; E = T[ix["E"]]; Tt = T[ix["T"]]
        on = t <= 3600
        t45 = float(t[np.argmax(B >= 45)]) if (B >= 45).any() else None
        Bss = B[on][-1]; B0 = B[0]
        t63 = float(t[on][np.argmax(B[on] >= B0 + 0.632 * (Bss - B0))])
        err = Tt - E
        out_tr[mode] = dict(t_battery_45C_s=t45, battery_tau63_s=t63, battery_end_of_sun_C=float(Bss),
                            TMP117_err_max_K=float(err[on].max()), TMP117_err_min_K=float(err.min()),
                            TMP117_err_end_of_sun_K=float(err[on][-1]),
                            E1_tau63_s=float(t[on][np.argmax(E[on] >= E[0] + 0.632 * (E[on][-1] - E[0]))]),
                            TMP117_tau63_s=float(t[on][np.argmax(Tt[on] >= Tt[0] + 0.632 * (Tt[on][-1] - Tt[0]))]))
        print(mode, out_tr[mode])
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "lumped_transient.png"), dpi=110); plt.close(fig)
    res["transient"] = out_tr
    json.dump(res, open(os.path.join(OUT, "lumped_results.json"), "w"), indent=1, default=float)
    print("wrote", os.path.join(OUT, "lumped_results.json"))


if __name__ == "__main__":
    main()
