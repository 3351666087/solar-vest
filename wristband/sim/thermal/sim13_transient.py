"""SIM-13 transient on the 3-D finite-volume model, with the firmware charge-inhibit loop in the loop.

Same geometry, materials and boundary conditions as sim13_fv3d.py (task BC: skin 34 C behind R_c, 35 C ambient,
0.5 m/s). Implicit (backward Euler) in time:  (C/dt + A) T_new = C/dt T_old + b_bc + Q(T_old).
Profile: steady shade (G = 0) -> 1000 W/m2 normal incidence at t = 0 for 60 min -> shade for 30 min.

Runs
  WC        : W-C control band, PV always shorted (PV_INH = 1)
  WS_fw45   : W-S, firmware rule as in ARCHITECTURE.md §4.2.5: NTC > 45.0 C -> PV_INH = 1; release below 43.0 C
              (the 2 K hysteresis is an assumption: ARCH gives no release threshold)
  WS_fw43.5 : W-S, proposed threshold NTC > 43.5 C (compensates the NTC-to-hot-spot offset), release 41.5 C
Checks: does the inhibit trigger, how long the cell is charged above 45 C anywhere in its volume, TMP117 lag vs E1.
usage: python sim13_transient.py [--dt 5] [--grid coarse|default]
"""
import argparse, json, math, os, sys, time
import numpy as np
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sim13_fv3d import Band, OUT, MID, G          # noqa: E402
from materials import PV, SOLAR                     # noqa: E402


def board_loads(b, mode, Tcell):
    """Same electrical model as Band.run(): returns (P_cell_out, P_board list, P_batt_heat)."""
    p = b.p
    tl = (1 - SOLAR["lens_R_front"]) * (1 - SOLAR["lens_abs"]) * (1 - SOLAR["lens_R_back"])
    irr = p["G"] / 1000.0 * tl
    if p["G"] <= 0:
        return 0.0, [(28.5, 10.0, PV["P_load"])], 0.0, 0.0
    if mode == "harvest":
        P_mpp = PV["P_stc"] * irr * (1 + PV["gamma_P"] * (Tcell - 25))
        I = P_mpp / PV["Vmp"]
        P_bat = PV["eta_harv"] * (P_mpp - I * I * PV["R_sh"]) - PV["P_load"]
        Ib = max(P_bat, 0) / PV["Vbat"]
        loads = [(12.0, 9.0, (1 - PV["eta_harv"]) * (P_mpp - I * I * PV["R_sh"])), (8.0, 4.0, I * I * PV["R_sh"]),
                 (28.5, 10.0, PV["P_load"])]
        return P_mpp, loads, Ib * Ib * PV["R_cell_int"], Ib
    Isc = PV["Isc_stc"] * irr * (1 + PV["alpha_Isc"] * (Tcell - 25))
    loads = [(8.0, 4.0, Isc * Isc * PV["R_sh"]), (16.0, 4.0, Isc * Isc * PV["R_q1"]), (28.5, 10.0, PV["P_load"])]
    return Isc * Isc * (PV["R_sh"] + PV["R_q1"] + PV["R_wire"]), loads, 0.0, 0.0


def heat(b, mode, Tcell):
    Pc, loads, Pbh, Ib = board_loads(b, mode, Tcell)
    Q = b.sources(Pc, loads)
    if Pbh > 0:
        mb = b.M == MID["battery"]
        Q[mb] += Pbh * b.C[mb] / b.C[mb].sum()
    return Q, Ib


def probes(b, T):
    M = b.M
    bat = M == MID["battery"]
    i = int(np.searchsorted(b.xc, G.BATTERY["x0"] + 1.5)); j = int(np.searchsorted(b.yc, G.BATTERY["y0"] + G.BATTERY["W"] / 2))
    kk = np.where(bat[i, j, :])[0]
    tx, ty = G.TMP117_XY
    pk = np.broadcast_to(b.masks["pkg"][:, :, None], b.shape) & (M == MID["ic"]) & \
        (np.broadcast_to(b.zc[None, None, :], b.shape) > b.zlev["zf"] - 0.3)
    b.T = T
    Tf, _ = b.face_T((2, -1))
    cont = b.contact
    e1m = np.broadcast_to(b.masks["e1"][:, :, None], b.shape)
    return dict(battery_max=float(T[bat].max()), battery_mean=float(T[bat].mean()), NTC=float(T[i, j, kk].mean()),
                pv_cell_mean=float(T[M == MID["pv_cell"]].mean()), TMP117=float(T[pk].mean()),
                E1_face=float(np.nanmean(np.where(cont & e1m, Tf, np.nan))),
                skin_contact_max=float(np.nanmax(np.where(cont, Tf, np.nan))),
                lens_top_max=float(T[:, :, -1][b.masks["lens"]].max()))


TOL = 1e-8   # relative to |rhs|; checked: 30 steps at 1e-8 vs 1e-11 differ by <= 9 mK (battery), <= 0.5 mK (TMP117/E1)


def simulate(b, policy, dt, t_sun=3600.0, t_end=5400.0, save_every=30.0):
    import pyamg
    nx, ny, nz = b.shape
    Cv = np.where(b.solid, b.C, 0.0).ravel()
    At = (b.A + sp.diags(Cv / dt)).tocsr()
    ml = pyamg.smoothed_aggregation_solver(At, symmetry="symmetric", max_coarse=500)
    # initial state: steady shade
    b.p["G"] = 0.0
    Q0, _ = heat(b, "open", 35.0)
    T = b.solve(Q0)
    mode = "shorted" if policy["kind"] == "WC" else "harvest"
    t, rows, n_inhibit, t_first = 0.0, [], 0, None
    above45_charging = 0.0
    while t < t_end - 1e-9:
        b.p["G"] = 1000.0 if t < t_sun else 0.0
        pr = probes(b, T) if (len(rows) == 0 or t - rows[-1]["t"] >= save_every - 1e-9) else None
        # firmware: 1 Hz NTC check, evaluated once per step (dt <= 5 s)
        if policy["kind"] == "WS":
            ntc = pr["NTC"] if pr else float(T[b._ntc_idx].mean())
            if mode == "harvest" and ntc > policy["on"]:
                mode = "shorted"; n_inhibit += 1; t_first = t if t_first is None else t_first
            elif mode == "shorted" and ntc < policy["off"]:
                mode = "harvest"
        Tcell = float(T[b.M == MID["pv_cell"]].mean())
        Q, Ib = heat(b, mode, Tcell)
        bmax = float(T[b.M == MID["battery"]].max())
        if mode == "harvest" and Ib > 0 and bmax > 45.0:
            above45_charging += dt
        if pr:
            pr.update(t=t, mode=mode, G=b.p["G"], I_charge_mA=Ib * 1e3)
            rows.append(pr)
        rhs = (b.rhs_bc + np.where(b.solid, Q, 0)).ravel() + Cv / dt * T.ravel()
        x = ml.solve(rhs, x0=T.ravel(), tol=TOL, accel="cg", maxiter=200)
        T = x.reshape(b.shape)
        t += dt
    pr = probes(b, T); pr.update(t=t, mode=mode, G=b.p["G"], I_charge_mA=0.0); rows.append(pr)
    return dict(rows=rows, n_inhibit_events=n_inhibit, t_first_inhibit_s=t_first, s_charging_with_cell_above_45C=above45_charging)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", type=float, default=10.0)
    ap.add_argument("--grid", default="coarse")
    ap.add_argument("--runs", default="WC,WS_fw45,WS_fw43.5")
    ap.add_argument("--plot", action="store_true", help="merge out/transient3d_<run>.json and plot")
    a = ap.parse_args()
    dm, df = (1.0, 0.5) if a.grid == "coarse" else (0.5, 0.25)
    ALL = {"WC": dict(kind="WC"), "WS_fw45": dict(kind="WS", on=45.0, off=43.0), "WS_fw43.5": dict(kind="WS", on=43.5, off=41.5)}
    if a.plot:
        res = {k: json.load(open(os.path.join(OUT, f"transient3d_{k}.json")))[k] for k in ALL}
        json.dump(res, open(os.path.join(OUT, "transient3d.json"), "w"), indent=1, default=float)
        plot(res)
        print("merged + plotted")
        return
    runs = {k: ALL[k] for k in a.runs.split(",")}
    res = {}
    t0 = time.time()
    for tag, pol in runs.items():
        b = Band(mode="shorted", dmax=dm, dfine=df)
        b.assemble()
        bat = b.M == MID["battery"]
        i = int(np.searchsorted(b.xc, G.BATTERY["x0"] + 1.5)); j = int(np.searchsorted(b.yc, G.BATTERY["y0"] + G.BATTERY["W"] / 2))
        idx = np.zeros(b.shape, bool); idx[i, j, np.where(bat[i, j, :])[0]] = True
        b._ntc_idx = idx
        r = simulate(b, pol, a.dt)
        R = r["rows"]
        sun = [x for x in R if x["t"] <= 3600]
        r["summary"] = dict(
            battery_max_C=max(x["battery_max"] for x in R), NTC_max_C=max(x["NTC"] for x in R),
            skin_contact_max_C=max(x["skin_contact_max"] for x in R),
            TMP117_minus_E1_max_K=max(x["TMP117"] - x["E1_face"] for x in R),
            TMP117_minus_E1_min_K=min(x["TMP117"] - x["E1_face"] for x in R),
            TMP117_minus_E1_end_of_sun_K=sun[-1]["TMP117"] - sun[-1]["E1_face"],
            t_NTC_45_s=next((x["t"] for x in R if x["NTC"] >= 45.0), None),
            t_battery_max_45_s=next((x["t"] for x in R if x["battery_max"] >= 45.0), None),
            battery_max_minus_NTC_end_of_sun_K=sun[-1]["battery_max"] - sun[-1]["NTC"])
        r["policy"] = pol; r["grid"] = list(b.shape); r["dt_s"] = a.dt
        res[tag] = r
        s = r["summary"]
        print(f"{tag:10s} grid={b.shape} first inhibit {r['t_first_inhibit_s']} s, events {r['n_inhibit_events']}, "
              f"charging with cell>45 C for {r['s_charging_with_cell_above_45C']:.0f} s | bat max {s['battery_max_C']:.2f} "
              f"NTC max {s['NTC_max_C']:.2f} skin max {s['skin_contact_max_C']:.2f} TMP-E1 [{s['TMP117_minus_E1_min_K']:+.3f}, "
              f"{s['TMP117_minus_E1_max_K']:+.3f}] t(NTC 45) {s['t_NTC_45_s']} t(bat 45) {s['t_battery_max_45_s']}  "
              f"{time.time()-t0:.0f}s", flush=True)
        json.dump({tag: r}, open(os.path.join(OUT, f"transient3d_{tag}.json"), "w"), indent=1, default=float)
    print("done", round(time.time() - t0), "s")


def plot(res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
    CRIT = "#d03b3b"
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2, "xtick.color": MUTED,
                         "ytick.color": INK2, "figure.facecolor": SURF, "axes.facecolor": SURF, "text.color": INK})
    f, axs = plt.subplots(1, 3, figsize=(15, 4.6), sharey=False)
    cols = {"battery_max": "#2a78d6", "NTC": "#1baa8f", "skin_contact_max": "#e08a1e", "TMP117": "#7b52c7", "E1_face": "#9a9893"}
    labs = {"battery_max": "battery max", "NTC": "battery NTC", "skin_contact_max": "skin-contact max", "TMP117": "TMP117",
            "E1_face": "E1 skin face"}
    for ax, tag in zip(axs, ("WC", "WS_fw45", "WS_fw43.5")):
        R = res[tag]["rows"]
        t = np.array([x["t"] for x in R]) / 60
        for k in cols:
            ax.plot(t, [x[k] for x in R], color=cols[k], lw=1.6 if k in ("battery_max", "NTC") else 1.2, label=labs[k])
        inh = np.array([x["mode"] == "shorted" for x in R])
        if tag != "WC":
            ax.fill_between(t, 30, 52, where=inh, color=GRID, alpha=0.6, lw=0, label="PV_INH = 1")
        ax.axhline(45, color=CRIT, lw=1, ls="--"); ax.axhline(41, color=CRIT, lw=0.8, ls=":")
        ax.axvline(60, color=MUTED, lw=0.8)
        ax.set_ylim(33, 51); ax.set_xlabel("min (sun on at 0, off at 60)"); ax.set_ylabel("°C")
        pol = res[tag]["policy"]
        ttl = {"WC": "W-C, PV always shorted", "WS_fw45": f"W-S, inhibit NTC > {pol.get('on')} / release < {pol.get('off')}",
               "WS_fw43.5": f"W-S, inhibit NTC > {pol.get('on')} / release < {pol.get('off')}"}[tag]
        ax.set_title(ttl, loc="left", fontsize=10)
        ax.grid(color=GRID, lw=0.6); [ax.spines[s].set_visible(False) for s in ("top", "right")]
    axs[0].legend(fontsize=7.5, loc="lower right", frameon=False)
    axs[1].legend(fontsize=7.5, loc="lower right", frameon=False)
    f.suptitle("SIM-13 3-D transient: 1000 W/m², 35 °C, 0.5 m/s, skin 34 °C + contact R (task BC)", x=0.01, ha="left")
    f.tight_layout(); f.savefig(os.path.join(OUT, "transient3d.png"), dpi=120); plt.close(f)


if __name__ == "__main__":
    main()
