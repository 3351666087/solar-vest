"""Monte Carlo of the in-band minimum body total efficiency for one pi-net (same tolerance model as matchlib.tolerance_check:
parts +-tolerance code, lands +-30 %, shunt return +-50 %; plus the pi-net-to-feed line l_b +-0.25 mm [E]).
usage: python eta_mc.py runs/X_body.npz results/pinet_eta_X.json -> results/eta_mc_<tag>.json"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.dont_write_bytecode = True
import numpy as np, matchlib as ML
rb = ML.load_run(sys.argv[1]); pj = json.load(open(sys.argv[2])); pi = ML.pi_from_json(pj); lb0 = pj["l_b_mm"]
f = rb["f"]; sel = ML.band_sel(f); fb = f[sel]; Zb = rb["Z"][sel]; eb = ML.eta_on(rb, fb); w = 2 * np.pi * fb
rng = np.random.default_rng(3); out = []
fcs = {}
for _ in range(400):
    lb = max(0.25, lb0 + rng.uniform(-0.25, 0.25)); lb = round(lb * 20) / 20
    fc = fcs.setdefault(lb, ML.FastChain(fb, lb))
    PADs = fc.Ypad * rng.uniform(0.7, 1.3); Lg = fc.Lgnd * rng.uniform(0.5, 1.5)
    def Zp(spec):
        if spec is None: return None
        Z = fc.Zpart(spec)
        if spec[0] == "L":
            dl = {"B": 0.1e-9, "C": 0.2e-9, "S": 0.3e-9}.get(spec[2][10], 0.05 * spec[1]); return Z + 1j * w * rng.uniform(-dl, dl)
        if spec[0] == "C":
            dc = {"W": 0.05e-12, "B": 0.1e-12, "C": 0.25e-12, "D": 0.5e-12}.get(spec[2][13], 0.05 * spec[1]); return 1 / (1 / Z + 1j * w * rng.uniform(-dc, dc))
        return Z
    def sh(spec):
        Z = Zp(spec); return ML.abcd_shunt(PADs + (0 if Z is None else 1.0 / (Z + Lg)))
    M = ML.mm(fc.A_lineA, sh(pi["shuntA"]), ML.abcd_shunt(PADs), ML.abcd_series(Zp(pi["ser"])), ML.abcd_shunt(PADs), sh(pi["shuntB"]), fc.A_tail)
    G, GT, _ = fc.eval(M, Zb)
    out.append((eb * GT).min())
out = np.array(out)
R = dict(pinet=pj["desc"], l_b_mm=lb0, n=len(out), eta_tot_body_min_median=float(np.median(out)), p5=float(np.percentile(out, 5)),
         p95=float(np.percentile(out, 95)), yield_ge_1pct=float((out >= 0.01).mean()))
tag = os.path.basename(sys.argv[1]).replace(".npz", "")
json.dump(R, open(os.path.join(HERE, "results", f"eta_mc_{tag}.json"), "w"), indent=1); print(json.dumps(R))
