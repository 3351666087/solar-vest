"""pi-net search ranked by the in-band minimum total efficiency on the body (gate 3a minimum), <= 2 parts, Murata S2P
usage: python eta_search.py runs/X_body.npz runs/X_free.npz TAG [lbs]  -> results/eta_search_TAG.json, results/pinet_eta_TAG.json"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.dont_write_bytecode = True
import numpy as np, matchlib as ML
rb, rf_ = ML.load_run(sys.argv[1]), ML.load_run(sys.argv[2]); tag = sys.argv[3]
lbs = [float(x) for x in (sys.argv[4] if len(sys.argv) > 4 else "0.5,1,2,3,4,6,8,10,12").split(",")]
f = rb["f"]; sel = ML.band_sel(f); fb = f[sel]
eb, ef = ML.eta_on(rb, fb), ML.eta_on(rf_, fb)
allr = []
for lb in lbs:
    top, n = ML.search(fb, rb["Z"][sel], rf_["Z"][sel], eb, ef, lb, top=100000)
    allr += top
allr.sort(key=lambda r: -r["eta_tot_body_min"])
best = allr[0]
ebf, eff = ML.eta_on(rb, f), ML.eta_on(rf_, f)
ch, cur = ML.evaluate(f, rb["Z"], rf_["Z"], ebf, eff, best["pi"], best["l_b_mm"])
ch["tolerance_mc"] = ML.tolerance_check(f, best["pi"], best["l_b_mm"], rb["Z"], rf_["Z"])
fmin_b = float(f[np.argmin(cur["S11b"])] / 1e9); fmin_f = float(f[np.argmin(cur["S11f"])] / 1e9)
# total-efficiency centre (frequency of the efficiency maximum) body vs free
fe_b = float(f[np.argmax(cur["etb"])] / 1e9); fe_f = float(f[np.argmax(cur["etf"])] / 1e9)
top10 = [dict(pinet=ML.pi_desc(r["pi"]), l_b_mm=r["l_b_mm"], eta_tot_body_min=r["eta_tot_body_min"], eta_tot_free_min=r["eta_tot_free_min"],
              RL_body_min=r["RL_body_min"], RL_free_min=r["RL_free_min"]) for r in allr[:10]]
R = dict(tag=tag, chosen=ch, f_S11min_GHz=dict(body=fmin_b, free=fmin_f), f_eta_max_GHz=dict(body=fe_b, free=fe_f),
         detuning_free_to_body_MHz=dict(S11_min=round((fmin_b - fmin_f) * 1e3, 1), eta_max=round((fe_b - fe_f) * 1e3, 1)), top10=top10)
os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
json.dump(R, open(os.path.join(HERE, "results", f"eta_search_{tag}.json"), "w"), indent=1, default=str)
json.dump(dict(ML.pi_to_json(best["pi"]), l_b_mm=best["l_b_mm"], from_tag=tag), open(os.path.join(HERE, "results", f"pinet_eta_{tag}.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in R.items()}, indent=1, default=str))
