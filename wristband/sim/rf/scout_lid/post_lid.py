#!/usr/bin/env python3
"""Scout post-processing, same basis for the board radiator (../runs/PA_body_c.npz) and the lid runs:
(a) LQG15HS / GJM multilayer pi-net (../matchlib.py, lands, l_b 0.5 mm), ranked by in-band minimum eta_tot on the body
    (body-only: no free run in the scout); board also with its fixed net (results/pinet_PA_c_fixnet.json);
(b) ideal-part Q_L 60 estimate (../hiq_estimate.py).   usage: python post_lid.py runs/L1_body_c.npz runs/L2_body_c.npz"""
import sys, os, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); RF = os.path.join(HERE, "..")
sys.path.insert(0, RF); sys.dont_write_bytecode = True
import numpy as np, matchlib as ML
PY = sys.executable


def one(path, fixnet=None):
    r = ML.load_run(path); f = r["f"]; sel = ML.band_sel(f); fb = f[sel]; eb = ML.eta_on(r, fb)
    zat = lambda x: complex(np.interp(x, f, r["Z"].real), np.interp(x, f, r["Z"].imag))
    top, _ = ML.search(fb, r["Z"][sel], r["Z"][sel], eb, eb, 0.5, top=100000, body_only=True)
    top.sort(key=lambda q: -q["eta_tot_body_min"]); b = top[0]
    ef = ML.eta_on(r, f)
    ch, cur = ML.evaluate(f, r["Z"], r["Z"], ef, ef, b["pi"], 0.5)
    out = dict(run=os.path.relpath(path, HERE), f_res_GHz=[round(x / 1e9, 3) for x in ML.f_res(f, r["Z"])],
               Z={f"{x/1e9:.2f}": str(np.round(zat(x), 1)) for x in (2.40e9, 2.44e9, 2.48e9)},
               eta_rad={f"{x/1e9:.2f}": round(float(e), 4) for x, e in zip(r["eta_f"], r["eta"])},
               multilayer=dict(pinet=ML.pi_desc(b["pi"]), l_b_mm=0.5, eta_tot_body_min=b["eta_tot_body_min"],
                               RL_body_min_dB=b["RL_body_min"], eta_tot_body=ch["eta_tot_body"],
                               f_eta_max_GHz=float(f[np.argmax(cur["etb"])] / 1e9),
                               network_loss_dB_band_max=ch["network_loss_dB_band_max"]["body"]))
    if fixnet:
        pj = json.load(open(fixnet)); pi = ML.pi_from_json(pj)
        c2, _ = ML.evaluate(f, r["Z"], r["Z"], ef, ef, pi, pj["l_b_mm"])
        out["fixed_net"] = dict(pinet=c2["pinet"], eta_tot_body_min=c2["eta_tot_body_min"])
    h = subprocess.run([PY, os.path.join(RF, "hiq_estimate.py"), path, "60"], capture_output=True, text=True).stdout
    out["hiq_Q60"] = json.loads(h.strip().splitlines()[-1])
    return out


R = dict(board=one(os.path.join(RF, "runs", "PA_body_c.npz"), os.path.join(RF, "results", "pinet_PA_c_fixnet.json")))
for p in sys.argv[1:]:
    k = os.path.basename(p).split("_")[0]; R[k] = one(p)
db = lambda a, b: round(10 * np.log10(a / b), 2)
for k in [k for k in R if k != "board"]:
    R[k]["gain_vs_board_dB"] = dict(multilayer=db(R[k]["multilayer"]["eta_tot_body_min"], R["board"]["multilayer"]["eta_tot_body_min"]),
                                    hiq_Q60=db(R[k]["hiq_Q60"]["eta_tot_body_min"], R["board"]["hiq_Q60"]["eta_tot_body_min"]),
                                    eta_rad_244=db(R[k]["eta_rad"]["2.44"], R["board"]["eta_rad"]["2.44"]))
json.dump(R, open(os.path.join(HERE, "results", "post_lid.json"), "w"), indent=1, default=str)
print(json.dumps(R, indent=1, default=str))
