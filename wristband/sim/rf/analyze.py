#!/usr/bin/env python3
"""Gate 3a post-processing of one candidate: antenna impedance, radiation efficiency, 2-part pi-net search
(with the pi-net-to-feed line length as a free, part-less parameter), S11 / total efficiency at the 50-ohm RF
node on the wrist and in free space; optional frequency-scaling surrogate for a re-dimensioned radiator.

  python analyze.py --body runs/A1_body_c.npz --free runs/A1_free_c.npz --tag A1_c
        [--lbs 0.5,2,4,6,8,10,12] [--scales 0.96,0.98,1.0,1.02,1.04] [--pinet results/pinet_X.json]
-> results/sim10_<tag>.json, results/sim10_<tag>.png, results/pinet_<tag>.json
"""
import os, sys, json, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
import numpy as np
import matchlib as ML

OUT = os.path.join(HERE, "results")


def best_for(rb, rf_, lbs, body_only=False):
    f = rb["f"]; sel = ML.band_sel(f)
    fb = f[sel]
    eb, ef = ML.eta_on(rb, fb), ML.eta_on(rf_, fb)
    best = None; per_lb = []
    for lb in lbs:
        top, n = ML.search(fb, rb["Z"][sel], rf_["Z"][sel], eb, ef, lb, top=3, body_only=body_only)
        per_lb.append(dict(l_b_mm=lb, score=top[0]["score"], pinet=ML.pi_desc(top[0]["pi"]),
                           RL_body_min=top[0]["RL_body_min"], RL_free_min=top[0]["RL_free_min"],
                           eta_tot_body_min=top[0]["eta_tot_body_min"]))
        if best is None or (top[0]["score"] >= 0, min(top[0]["score"], 3.0), top[0]["eta_tot_body_min"]) > \
                (best["score"] >= 0, min(best["score"], 3.0), best["eta_tot_body_min"]):
            best = top[0]
    return best, per_lb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--body", required=True); ap.add_argument("--free", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--lbs", default="0.5,2,4,6,8,10,12")
    ap.add_argument("--scales", default="")
    ap.add_argument("--pinet", default=None)
    ap.add_argument("--no-mc", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    rb, rf_ = ML.load_run(a.body), ML.load_run(a.free)
    f = rb["f"]; assert np.allclose(f, rf_["f"])
    sel = ML.band_sel(f)
    lbs = [float(x) for x in a.lbs.split(",")]
    eb, ef = ML.eta_on(rb, f), ML.eta_on(rf_, f)
    zat = lambda r, x: complex(np.interp(x, f, r["Z"].real), np.interp(x, f, r["Z"].imag))
    R = dict(tag=a.tag, body=a.body, free=a.free,
             cand=rb["meta"].get("cand"), var_body=rb["meta"].get("var"),
             min_dist_radiator_to_skin_mm=rb["meta"].get("min_dist_radiator_to_skin_mm"),
             antenna=dict(f_res_body_GHz=[x / 1e9 for x in ML.f_res(f, rb["Z"])],
                          f_res_free_GHz=[x / 1e9 for x in ML.f_res(f, rf_["Z"])],
                          Z_body={f"{x/1e9:.2f}": str(np.round(zat(rb, x), 1)) for x in (2.40e9, 2.44e9, 2.48e9)},
                          Z_free={f"{x/1e9:.2f}": str(np.round(zat(rf_, x), 1)) for x in (2.40e9, 2.44e9, 2.48e9)},
                          eta_rad_body={f"{x/1e9:.2f}": float(e) for x, e in zip(rb["eta_f"], rb["eta"])},
                          eta_rad_free={f"{x/1e9:.2f}": float(e) for x, e in zip(rf_["eta_f"], rf_["eta"])},
                          RL_raw_50_body_band_min=float((-20 * np.log10(np.abs((rb["Z"][sel] - 50) / (rb["Z"][sel] + 50)))).min()),
                          RL_raw_50_free_band_min=float((-20 * np.log10(np.abs((rf_["Z"][sel] - 50) / (rf_["Z"][sel] + 50)))).min()),
                          t_sim_ns=dict(body=float(rb["D"]["t_sim_ns"]), free=float(rf_["D"]["t_sim_ns"])),
                          t_run_s=dict(body=float(rb["D"]["t_run_s"]), free=float(rf_["D"]["t_run_s"]))))
    if a.pinet:
        pj = json.load(open(a.pinet)); pi = ML.pi_from_json(pj); lb = pj["l_b_mm"]
    else:
        best, per_lb = best_for(rb, rf_, lbs)
        R["search_per_line_length"] = per_lb
        pi, lb = best["pi"], best["l_b_mm"]
        bo, per_lb_bo = best_for(rb, rf_, lbs, body_only=True)
        R["body_only_optimum"] = dict(pinet=ML.pi_desc(bo["pi"]), l_b_mm=bo["l_b_mm"], RL_body_min=bo["RL_body_min"],
                                      RL_free_min=bo["RL_free_min"], eta_tot_body_min=bo["eta_tot_body_min"])
    ch, cur = ML.evaluate(f, rb["Z"], rf_["Z"], eb, ef, pi, lb)
    R["chosen"] = ch
    if not a.no_mc:
        R["chosen"]["tolerance_mc"] = ML.tolerance_check(f, pi, lb, rb["Z"], rf_["Z"])
    if a.scales:
        R["frequency_scaling_surrogate"] = []
        for k in [float(x) for x in a.scales.split(",")]:
            sb, sf = ML.scaled(rb, k), ML.scaled(rf_, k)
            b2, _ = best_for(sb, sf, lbs)
            R["frequency_scaling_surrogate"].append(dict(k=k, score=b2["score"], pinet=ML.pi_desc(b2["pi"]), l_b_mm=b2["l_b_mm"],
                                                         RL_body_min=b2["RL_body_min"], RL_free_min=b2["RL_free_min"],
                                                         eta_tot_body_min=b2["eta_tot_body_min"]))
    R["curves"] = dict(f_GHz=(f / 1e9).round(4).tolist(), Zb_re=rb["Z"].real.round(3).tolist(), Zb_im=rb["Z"].imag.round(3).tolist(),
                       Zf_re=rf_["Z"].real.round(3).tolist(), Zf_im=rf_["Z"].imag.round(3).tolist(),
                       S11b_dB=cur["S11b"].round(3).tolist(), S11f_dB=cur["S11f"].round(3).tolist(),
                       eta_tot_b=cur["etb"].round(5).tolist(), eta_tot_f=cur["etf"].round(5).tolist())
    json.dump(R, open(os.path.join(OUT, f"sim10_{a.tag}.json"), "w"), indent=1, default=str)
    json.dump(dict(ML.pi_to_json(pi), l_b_mm=lb, from_tag=a.tag), open(os.path.join(OUT, f"pinet_{a.tag}.json"), "w"), indent=1)
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.4))
    for r, lab in ((rb, "wrist"), (rf_, "free")):
        ax[0].plot(f / 1e9, r["Z"].real, label=f"Re Z {lab}"); ax[0].plot(f / 1e9, r["Z"].imag, "--", label=f"Im Z {lab}")
        ax[1].plot(f / 1e9, 20 * np.log10(np.abs((r["Z"] - 50) / (r["Z"] + 50))), ":", label=f"raw radiator vs 50 ohm, {lab}")
    ax[1].plot(f / 1e9, cur["S11b"], "b-", lw=2, label="with pi-net, wrist"); ax[1].plot(f / 1e9, cur["S11f"], "r-", lw=2, label="with pi-net, free")
    ax[1].axhline(-10, color="k", lw=0.6); ax[1].axhline(-6, color="k", lw=0.6, ls="--")
    ax[2].plot(f / 1e9, 100 * cur["etb"], "b-", label="eta_tot wrist"); ax[2].plot(f / 1e9, 100 * cur["etf"], "r-", label="eta_tot free")
    ax[2].plot(rb["eta_f"] / 1e9, 100 * rb["eta"], "bo", ms=3, label="eta_rad wrist"); ax[2].plot(rf_["eta_f"] / 1e9, 100 * rf_["eta"], "ro", ms=3, label="eta_rad free")
    ax[2].axhline(5, color="k", lw=0.6); ax[2].axhline(1, color="k", lw=0.6, ls=":")
    for x in ax:
        x.axvspan(2.40, 2.48, color="g", alpha=0.12); x.grid(True); x.set_xlabel("GHz"); x.legend(fontsize=7)
    ax[0].set_ylabel("ohm"); ax[1].set_ylabel("S11 (dB) at the 50-ohm RF node"); ax[2].set_ylabel("%")
    ax[1].set_ylim(-35, 0); ax[2].set_ylim(0, 100); ax[2].set_yscale("symlog", linthresh=10)
    fig.suptitle(f"gate 3a {a.tag}: {ch['pinet']}, line pi-net to feed {lb:g} mm")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, f"sim10_{a.tag}.png"), dpi=110)
    print(json.dumps({k: v for k, v in R.items() if k != "curves"}, indent=1, default=str))


if __name__ == "__main__":
    main()
