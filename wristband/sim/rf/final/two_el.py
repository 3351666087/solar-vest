"""[rf final] best 2-element net (C213 DNP, LQW only) on the as-built chain, with the same MC. usage: emsim-python two_el.py -> two_el.json"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.argv = [sys.argv[0]]
s = open(os.path.join(HERE, "rf_final.py")).read()
exec(s.split("# 3-element search")[0])
exec("def mc" + s.split("def mc", 1)[1].split("# robustness pick")[0])
ch = ChainF(fb); res = []
for a_ in PL.LQW:
    for b_ in PL.LQW:
        pi = dict(shuntA=None, ser=PL.lqw_spec(a_), shuntB=PL.lqw_spec(b_)); M = ch.full(pi)
        Gb, GTb, _ = ML.FastChain.eval(M, Eas["Z"][sel]); Gf, _, _ = ML.FastChain.eval(M, Bas["Z"][sel])
        res.append(dict(pi=pi, eta=float((ML.eta_on(Eas, fb) * GTb).min()), RLb=float((-20 * np.log10(np.abs(Gb))).min()), RLf=float((-20 * np.log10(np.abs(Gf))).min())))
ok = sorted([r for r in res if r["RLb"] >= 10 and r["RLf"] >= 6], key=lambda r: -r["eta"]) or sorted(res, key=lambda r: -r["RLb"])
p = ok[0]["pi"]
out = dict(pinet=PL.pdesc(p), cases={k: (round(v["eta_min"] * 100, 2), round(v["S11_max_dB"], 2)) for k, v in ((k, ev(r, p)) for k, r in RUNS.items())}, mc=mc(p))
json.dump(out, open(os.path.join(HERE, "two_el.json"), "w"), indent=1); print(json.dumps(out))
