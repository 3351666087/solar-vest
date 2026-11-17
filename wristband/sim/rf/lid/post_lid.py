#!/usr/bin/env python3
"""Post-processing of the lid antenna L1x runs (gate V3-G3a). Basis: ../matchlib.py (same chain: 50-ohm node, CPWG 3 mm, pi-net
with loaded empty lands, l_b to the feed point), ranked by in-band minimum body total efficiency.
Part sets:
  ML  : Murata LQG15HS multilayer + GJM1555 S2P (library of RF.md)                                    [S2P ✅]
  HQ  : JLC-stocked Murata LQW15AN_80 wire-wound (model below) + GJM1555 S2P high-Q C0G caps           [model ⚠]
LQW model: Z = R + j w L_eff, L_eff = L / (1 - (f/SRF)^2), R = w L / Q(f), Q(f) = KQ * Q250 * sqrt(f / 250 MHz)
  (Q250 = datasheet Q min at 250 MHz, KQ 0.7 margin for the unread Q-f curve ⚠; SRF = datasheet or 9.6 GHz * sqrt(4.3 nH / L) ⚠).
usage: python post_lid.py  (reads runs/*_f.npz present) -> results/post.json"""
import sys, os, json, glob
HERE = os.path.dirname(os.path.abspath(__file__)); RF = os.path.join(HERE, "..")
sys.path.insert(0, RF); sys.dont_write_bytecode = True
import numpy as np, matchlib as ML

KQ = float(os.environ.get("KQ", "0.7"))
# JLC-stocked LQW15AN_80 values (JLC parts API 2026-11-15): value nH -> (MPN, C-number, stock, Q250 min, SRF GHz or None)
LQW = {1.3: ("LQW15AN1N3C80D", "C412260", 5522), 1.5: ("LQW15AN1N5C80D", "C412261", 6836), 1.7: ("LQW15AN1N7C80D", "C412263", 1496),
       2.3: ("LQW15AN2N3B80D", "C1332768", 13955), 2.4: ("LQW15AN2N4G80D", "C412266", 9457), 2.6: ("LQW15AN2N6G80D", "C412268", 19907),
       2.7: ("LQW15AN2N7B80D", "C527595", 11377), 3.3: ("LQW15AN3N3B80D", "C341785", 19909), 3.4: ("LQW15AN3N4B80D", "C471377", 6660),
       3.7: ("LQW15AN3N7G80D", "C412277", 28726), 3.8: ("LQW15AN3N8G80D", "C412278", 19907), 3.9: ("LQW15AN3N9G80D", "C412279", 5578),
       4.1: ("LQW15AN4N1G80D", "C412281", 10346), 4.3: ("LQW15AN4N3B80D", "C471381", 21380), 4.6: ("LQW15AN4N6G80D", "C412336", 9581),
       4.7: ("LQW15AN4N7G80D", "C412337", 15466), 5.2: ("LQW15AN5N2B80D", "C2048612", 6909), 5.5: ("LQW15AN5N5B80D", "C2044478", 9901),
       5.6: ("LQW15AN5N6B80D", "C464439", 16184), 6.2: ("LQW15AN6N2B80D", "C668465", 8018), 6.5: ("LQW15AN6N5G80D", "C6217566", 8784),
       6.7: ("LQW15AN6N7G80D", "C6652895", 9350), 6.8: ("LQW15AN6N8G80D", "C882467", 8995), 7.1: ("LQW15AN7N1G80D", "C2043904", 5426),
       7.2: ("LQW15AN7N2G80D", "C2044544", 6627), 7.3: ("LQW15AN7N3G80D", "C2042200", 7325), 7.6: ("LQW15AN7N6G80D", "C2048575", 6846),
       7.9: ("LQW15AN7N9G80D", "C2046240", 6319), 8.2: ("LQW15AN8N2G80D", "C307610", 9041), 8.4: ("LQW15AN8N4G80D", "C5788422", 8457),
       8.9: ("LQW15AN8N9G80D", "C3224011", 9541), 9.0: ("LQW15AN9N0G80D", "C6652901", 5395), 9.9: ("LQW15AN9N9G80D", "C2044471", 8930)}
# datasheet Q min at 250 MHz and SRF min (Murata reference specification, read 2026-11-15 via web search snippets; others interpolated ⚠)
Q250_READ = {1.3: (20, 18.0), 1.5: (20, 18.0), 2.4: (30, 15.5), 4.3: (32, 9.6), 6.2: (33, None)}


def q250(L):
    if L in Q250_READ: return Q250_READ[L][0]
    if L < 2.4: return 20.0 + (L - 1.5) / 0.9 * 10.0    # ⚠ between the read points 1.5 nH (20) and 2.4 nH (30)
    return 32.0


def srf(L):
    if L in Q250_READ and Q250_READ[L][1]: return Q250_READ[L][1] * 1e9
    return 9.6e9 * (4.3 / L) ** 0.5


TOL = {"B": ("abs", 0.1e-9), "C": ("abs", 0.2e-9), "G": ("rel", 0.02)}

_orig = ML.C.part_Z


def part_Z(spec, fr):
    if spec is not None and spec[0] == "L" and isinstance(spec[2], str) and spec[2].startswith("LQW"):
        L = spec[1]; f = fr.f; w = 2 * np.pi * f
        Q = KQ * q250(round(L * 1e9, 1)) * np.sqrt(f / 250e6)
        Le = L / (1 - (f / srf(round(L * 1e9, 1))) ** 2)
        return w * Le / Q + 1j * w * Le
    return _orig(spec, fr)


ML.C.part_Z = part_Z


def lqw_spec(Lnh):
    return ("L", Lnh * 1e-9, "LQW:" + LQW[Lnh][0])


def hq_catalogue():
    caps = [c for c in ML.catalogue() if c["kind"] == "C"]
    return [ML.spec_of(c) for c in caps] + [lqw_spec(v) for v in sorted(LQW)]


def desc(spec):
    if spec is None: return "DNP"
    if spec[0] == "R0": return "0R"
    if isinstance(spec[2], str) and spec[2].startswith("LQW"):
        m = spec[2][4:]; v = round(spec[1] * 1e9, 1); return f"{v} nH ({m}, {LQW[v][1]})"
    return ML.describe(spec)


def pdesc(pi): return f"A:{desc(pi['shuntA'])} | S:{desc(pi['ser'])} | B:{desc(pi['shuntB'])}"


def search(fb, Zb, Zf, eb, ef, lb, parts):
    fc = ML.FastChain(fb, lb); res = []
    for ser in parts:
        for side in ("A", "B"):
            for sh in [None] + parts:
                if sh is None and side == "B": continue
                pi = dict(shuntA=sh if side == "A" else None, ser=ser, shuntB=sh if side == "B" else None)
                M = fc.full(pi)
                Gb, GTb, _ = fc.eval(M, Zb); Gf, GTf, _ = fc.eval(M, Zf)
                res.append(dict(pi=pi, eta_b=float((eb * GTb).min()), eta_f=float((ef * GTf).min()),
                                RLb=float((-20 * np.log10(np.abs(Gb))).min()), RLf=float((-20 * np.log10(np.abs(Gf))).min())))
    return res


def load(tag):
    p = os.path.join(HERE, "runs", f"{tag}_f.npz")
    return ML.load_run(p) if os.path.exists(p) else None


def evalnet(run, pi, lb, f):
    fc = ML.FastChain(f, lb); M = fc.full(pi); G, GT, _ = fc.eval(M, run["Z"]); e = ML.eta_on(run, f)
    sel = ML.band_sel(f); et = e * GT; s11 = 20 * np.log10(np.abs(G))
    return dict(eta_tot_min=float(et[sel].min()), eta_tot={f"{x/1e9:.2f}": float(np.interp(x, f, et)) for x in (2.40e9, 2.44e9, 2.48e9)},
                S11_band_max_dB=float(s11[sel].max()), f_S11min_GHz=float(f[np.argmin(s11)] / 1e9), f_eta_max_GHz=float(f[np.argmax(et)] / 1e9),
                eta_rad={f"{x/1e9:.2f}": round(float(v), 4) for x, v in zip(run["eta_f"], run["eta"])},
                Z={f"{x/1e9:.2f}": str(np.round(complex(np.interp(x, f, run["Z"].real), np.interp(x, f, run["Z"].imag)), 1)) for x in (2.40e9, 2.44e9, 2.48e9)},
                net_loss_dB_max=float(np.nanmax((-10 * np.log10(np.clip(GT / (1 - np.abs(G) ** 2), 1e-12, None)))[sel]))), s11, et


def mc(A, D, pi, lb, n=600, s_mech=0.6, d_len=0.1 / 14.0, seed=5):
    """parts (tolerance code), lands +-30 %, shunt return +-50 %, l_b +-0.25 mm, mechanical (spring height + strip-frame gap):
    t ~ U(-1, 1), Z = Z_A + |t| s_mech (Z_D - Z_A) (worst-sided, s_mech = real tolerance / modelled offset ⚠), strip print
    length +-0.1 mm on ~14 mm feed-to-open path as a frequency scaling (matchlib.scaled) ⚠."""
    f = A["f"]; sel = ML.band_sel(f); fb = f[sel]; w = 2 * np.pi * fb
    rng = np.random.default_rng(seed); out = []; rl = []
    ZA = A["Z"]; ZD = D["Z"] if D is not None else A["Z"]
    fcs = {}
    for _ in range(n):
        t = abs(rng.uniform(-1, 1)) * s_mech
        run = dict(A, Z=ZA + t * (ZD - ZA), eta=A["eta"] + t * ((D["eta"] if D is not None else A["eta"]) - A["eta"]))
        run = ML.scaled(run, 1.0 + rng.uniform(-d_len, d_len))
        Zb = run["Z"][sel]; eb = ML.eta_on(run, fb)
        l = max(0.25, round((lb + rng.uniform(-0.25, 0.25)) * 20) / 20)
        fc = fcs.setdefault(l, ML.FastChain(fb, l))
        PADs = fc.Ypad * rng.uniform(0.7, 1.3); Lg = fc.Lgnd * rng.uniform(0.5, 1.5)
        def Zp(spec):
            if spec is None: return None
            Z = fc.Zpart(spec)
            if spec[0] == "L":
                if spec[2].startswith("LQW"):
                    k, d = TOL[LQW[round(spec[1] * 1e9, 1)][0][10]]
                else:
                    k, d = ("abs", {"B": 0.1e-9, "C": 0.2e-9, "S": 0.3e-9}.get(spec[2][10], 0.05 * spec[1]))
                dl = d if k == "abs" else d * spec[1]
                return Z + 1j * w * rng.uniform(-dl, dl)
            if spec[0] == "C":
                dc = {"W": 0.05e-12, "B": 0.1e-12, "C": 0.25e-12, "D": 0.5e-12}.get(spec[2][13], 0.05 * spec[1])
                return 1 / (1 / Z + 1j * w * rng.uniform(-dc, dc))
            return Z
        def sh(spec):
            Z = Zp(spec); return ML.abcd_shunt(PADs + (0 if Z is None else 1.0 / (Z + Lg)))
        M = ML.mm(fc.A_lineA, sh(pi["shuntA"]), ML.abcd_shunt(PADs), ML.abcd_series(Zp(pi["ser"])), ML.abcd_shunt(PADs), sh(pi["shuntB"]), fc.A_tail)
        G, GT, _ = fc.eval(M, Zb)
        out.append((eb * GT).min()); rl.append((-20 * np.log10(np.abs(G))).min())
    out = np.array(out); rl = np.array(rl)
    return dict(n=n, s_mech=s_mech, eta_min_median=float(np.median(out)), p5=float(np.percentile(out, 5)), p95=float(np.percentile(out, 95)),
                yield_ge_1pct=float((out >= 0.01).mean()), yield_ge_5pct=float((out >= 0.05).mean()),
                RL_body_median=float(np.median(rl)), RL_body_p5=float(np.percentile(rl, 5)), yield_S11_le_m10=float((rl >= 10).mean()))


def main():
    """reference = E_body (as built, pins); free as built = B_free + (E_body - A_body) [estimate]; D = worst-case corner of E"""
    A, B, E = load("A_body"), load("B_free"), load("E_body")
    Bx = dict(B, Z=B["Z"] + (E["Z"] - A["Z"]))
    f = E["f"]; sel = ML.band_sel(f); fb = f[sel]
    eb, ef = ML.eta_on(E, fb), ML.eta_on(B, fb)
    R = dict(KQ=KQ, reference="E_body_f (as built: BW0019BG feed, strip X 5.125-12.375, frame cut to X 13, strap-bar pins)",
             free_as_built="B_free_f + (E_body_f - A_body_f) impedance shift [estimate]; eta_rad free from B_free_f")
    sets = dict(ML=[("R0",)] + [ML.spec_of(c) for c in ML.catalogue()], HQ=[("R0",)] + hq_catalogue())
    best = {}
    for name, parts in sets.items():
        allr = []
        for r in search(fb, E["Z"][sel], Bx["Z"][sel], eb, ef, 0.5, parts):
            r["lb"] = 0.5; allr.append(r)
        allr.sort(key=lambda r: -r["eta_b"])
        top = allr[0]
        okf = [r for r in allr if r["RLf"] >= 6]
        ok = [r for r in allr if r["RLb"] >= 10 and r["RLf"] >= 6]
        best[name] = dict(eta=top, free6=(okf[0] if okf else None), s11ok=(ok[0] if ok else None), maxRLb=max(allr, key=lambda r: r["RLb"]))
        mk = lambda r: dict(pinet=pdesc(r["pi"]), eta_b=r["eta_b"], eta_f=r["eta_f"], RLb=r["RLb"], RLf=r["RLf"]) if r else None
        R[name] = dict(best_eta=mk(top), best_with_free_S11_le_m6=mk(best[name]["free6"]), best_meeting_both_S11=mk(best[name]["s11ok"]),
                       max_RL_body_any_net=mk(best[name]["maxRLb"]),
                       top8=[dict(pinet=pdesc(r["pi"]), eta_b=round(r["eta_b"], 4), RLb=round(r["RLb"], 2), RLf=round(r["RLf"], 2)) for r in allr[:8]])
    pick = best["HQ"]["s11ok"] or best["HQ"]["free6"] or best["HQ"]["eta"]
    pi = pick["pi"]; lb = pick["lb"]
    R["chosen"] = dict(set="HQ", rule="max in-band min body eta_tot among nets meeting S11 body <= -10 dB and free <= -6 dB (else free only)", pinet=pdesc(pi), l_b_mm=lb,
                       pi=json.loads(json.dumps(pi)))
    cases = {}
    for tag, run in (("A_body", A), ("B_free_raw", B), ("B_free_as_built", Bx), ("E_body", E), ("D_body", load("D_body")), ("H_body", load("H_body"))):
        if run is None: cases[tag] = "NOT_RUN"; continue
        cases[tag] = evalnet(run, pi, lb, f)[0]
    cases["E_body_ML_best_net"] = evalnet(E, best["ML"]["eta"]["pi"], 0.5, f)[0]
    cases["E_body_ML_best_net"]["pinet"] = pdesc(best["ML"]["eta"]["pi"])
    R["cases"] = cases
    R["detuning_free_to_body_MHz"] = dict(
        S11_min=round((cases["E_body"]["f_S11min_GHz"] - cases["B_free_as_built"]["f_S11min_GHz"]) * 1e3, 1),
        eta_max=round((cases["E_body"]["f_eta_max_GHz"] - cases["B_free_as_built"]["f_eta_max_GHz"]) * 1e3, 1),
        ideal_feed_runs_A_vs_B_S11_min=round((cases["A_body"]["f_S11min_GHz"] - cases["B_free_raw"]["f_S11min_GHz"]) * 1e3, 1))
    D = load("D_body")
    R["mc"] = mc(E, D, pi, lb)
    R["mc_ML_best"] = mc(E, D, best["ML"]["eta"]["pi"], 0.5)
    R["mc_mech_full"] = mc(E, D, pi, lb, s_mech=1.0)
    json.dump(R, open(os.path.join(HERE, "results", "post.json"), "w"), indent=1, default=str)
    print(json.dumps({k: R[k] for k in R if k not in ("cases",)}, indent=1, default=str))
    for k, v in cases.items(): print(k, json.dumps(v)[:500])


if __name__ == "__main__":
    main()
