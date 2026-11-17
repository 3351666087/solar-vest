#!/usr/bin/env python3
"""[rf final 2026-11-17] Lid antenna L1: re-tune of C213 / C215 / L204 for the CLOSED board (v3/finish/solarband_v3f_final.kicad_pcb).
Model: v3/sim/rf/lid FDTD runs (E/D/H/A/B, read-only) + post_lid part models (LQW KQ 0.70, GJM S2P) + matchlib ABCD chain, as
prechecks/rf_match_layout.py, extended to the measured layout (rf_geom_final.json, line_z.json):
  50-ohm node (L201.2) - 0.90 mm w0.09 - C213 land (chip-side shunt) - l_a 6.09 mm (w0.09 / w0.15 / w0.09 neck-down, measured order)
  - C215.1 land - C215 series - C215.2 land (node N) - [stub 1.16 mm w0.17 - L204 land + part + return] - 0.648 mm w0.17 - feed.
Line Z: CPWG / microstrip on the 8-layer estimate (h 0.0764, er 3.91 ⚠): w0.17 g0.15 48.8 ohm; w0.15 55 ohm; w0.09 74 ohm (70-79).
Antenna Z: E_body (as modelled) and E_body + dZ_asb (J40 moved +0.40 mm along its axis; dZ from the one coarse run, see RF_FINAL.md).
usage: emsim-python rf_final.py [--dz-json asbuilt_dz.json] -> rf_final.json"""
import sys, os, json, math, argparse
LID = "/path/to/SolarVest_work/wristband/v3/sim/rf/lid"
sys.path.insert(0, LID); sys.path.insert(0, os.path.join(LID, "..")); sys.path.insert(0, os.path.join(LID, "..", "common")); sys.dont_write_bytecode = True
import numpy as np
import matchlib as ML, chain as C
import post_lid as PL
from rfnet import tline
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("--dz-json", default=os.path.join(HERE, "asbuilt_dz.json")); ap.add_argument("--mc", type=int, default=600)
a = ap.parse_args()

E, D, Hh, A, B = (PL.load(t) for t in ("E_body", "D_body", "H_body", "A_body", "B_free"))
Bx = dict(B, Z=B["Z"] + (E["Z"] - A["Z"]))
f = E["f"]; sel = ML.band_sel(f); fb = f[sel]
G = json.load(open(os.path.join(HERE, "rf_geom_final.json")))
LZ = json.load(open(os.path.join(HERE, "line_z.json")))
Z09 = 0.5 * (LZ["RF_50R w0.09"]["Z_gnd_gap"] + LZ["RF_50R w0.09"]["Z_other_gap"]); E09 = 0.5 * (LZ["RF_50R w0.09"]["eeff_gnd_gap"] + LZ["RF_50R w0.09"]["eeff_other_gap"])
Z15 = 0.5 * (LZ["RF_50R w0.15"]["Z_gnd_gap"] + LZ["RF_50R w0.15"]["Z_other_gap"]); E15 = 0.5 * (LZ["RF_50R w0.15"]["eeff_gnd_gap"] + LZ["RF_50R w0.15"]["eeff_other_gap"])
Z17, E17 = LZ["ANT_FEED w0.17"]["Z_gnd_gap"], LZ["ANT_FEED w0.17"]["eeff_gnd_gap"]
# measured (rf_geom_final.json): chip side 0.897 (w0.09), l_a: w0.09 near C215 1.49, w0.15 2.346, w0.09 near C213 rest; in-land remainder 0.71 at 50 ohm
LA_TOT = G["l_a_C213pad1_to_C215pad1_mm"]; L09 = G["l_a_by_width_mm"]["0.09"]; L15 = G["l_a_by_width_mm"]["0.15"]
L09_C215 = 1.489                     # C215.1 -> (104.725,124.975): 0.389 + 1.1 mm of w0.09 (dump)
SEG_A = [(L09 - L09_C215, Z09, E09, 0.025), (L15, Z15, E15, 0.02), (L09_C215, Z09, E09, 0.025), (LA_TOT - L09 - L15, 50.0, 3.0, 0.02)]   # C213 side -> C215 side
LCHIP = G["chip_side_to_C213pad1_mm"]
LB = G["l_b_C215pad2_centre_to_feed_mm"]; LS = G["stub_L204pad1_centre_to_C215pad2_centre_mm"]
NOM = dict(z09=Z09, z15=Z15, z17=Z17)


def lines(fr, segs):
    M = None
    for L, Zc, ee, al in segs:
        if L <= 1e-6: continue
        n = tline(fr, L, Zc=Zc, eeff=ee, alpha_db_per_mm_at_f0=al)
        M = n if M is None else M ** n
    return M.a


class ChainF:
    """real layout chain; k: dict of perturbations (line Z factor, lengths) for the MC"""
    def __init__(self, fr_hz, lb=LB, ls=LS, kz=1.0, la_scale=1.0):
        self.fc = ML.FastChain(fr_hz, lb, l_a=LCHIP)
        fr = self.fc.fr
        self.A_chip = lines(fr, [(LCHIP, Z09 * kz, E09, 0.025)])
        self.A_a = lines(fr, [(L * la_scale, Zc * kz, ee, al) for L, Zc, ee, al in SEG_A])
        self.A_tail = lines(fr, [(lb, Z17 * kz, E17, 0.02)])
        self.A_stub = lines(fr, [(ls, Z17 * kz, E17, 0.02)]) if ls > 0 else None

    def full(self, pi, Ypad=None, Lg=None, Zp=None):
        fc = self.fc; Yp = fc.Ypad if Ypad is None else Ypad; Lgn = fc.Lgnd if Lg is None else Lg
        zp = (lambda s: None if s is None else fc.Zpart(s)) if Zp is None else Zp
        def shy(s):
            z = zp(s); return Yp + (0 if z is None else 1.0 / (z + Lgn))
        Aa = ML.abcd_shunt(shy(pi["shuntA"])); P = ML.abcd_shunt(Yp); S = ML.abcd_series(zp(pi["ser"]))
        Yl = shy(pi["shuntB"])
        if self.A_stub is None or pi["shuntB"] is None:
            Bs = ML.abcd_shunt(Yl)
        else:
            Zl = 1.0 / Yl; s = self.A_stub
            Zin = (s[:, 0, 0] * Zl + s[:, 0, 1]) / (s[:, 1, 0] * Zl + s[:, 1, 1]); Bs = ML.abcd_shunt(1.0 / Zin)
        return ML.mm(self.A_chip, Aa, self.A_a, P, S, P, Bs, self.A_tail)


def ev(run, pi, ch=None, freq=f):
    ch = ch or ChainF(freq); M = ch.full(pi); Gm, GT, _ = ML.FastChain.eval(M, run["Z"])
    e = ML.eta_on(run, freq); s = ML.band_sel(freq); et = e * GT; s11 = 20 * np.log10(np.abs(Gm))
    return dict(eta_min=float(et[s].min()), eta={k: float(np.interp(x, freq, et)) for k, x in (("2.40", 2.40e9), ("2.44", 2.44e9), ("2.48", 2.48e9))},
                S11_max_dB=float(s11[s].max()), f_S11min_GHz=float(freq[np.argmin(s11)] / 1e9))


# as-built antenna impedance (J40 moved): dZ(f) from asbuilt_dz.json (written by asbuilt_dz.py), else zero
dz = np.zeros_like(E["Z"]); DZ_SRC = "none"
if os.path.exists(a.dz_json):
    J = json.load(open(a.dz_json)); dz = np.interp(f, np.array(J["f"]), np.array(J["dZ_re"])) + 1j * np.interp(f, np.array(J["f"]), np.array(J["dZ_im"])); DZ_SRC = J["source"]
deta = 1.0
Eas = dict(E, Z=E["Z"] + dz); Das = dict(D, Z=D["Z"] + dz); Has = dict(Hh, Z=Hh["Z"] + dz); Bas = dict(Bx, Z=Bx["Z"] + dz)
RUNS = {"body as built": Eas, "body as modelled (E)": E, "corner D": Das, "hand": Has, "free (est.)": Bas}

R = dict(model=__doc__.split("\n")[1], dz_source=DZ_SRC, lines=dict(Z09=Z09, eeff09=E09, Z15=Z15, Z17=Z17, eeff17=E17, chip_mm=LCHIP, seg_a=SEG_A, l_b=LB, l_s=LS))
INFORCE = dict(shuntA=None, ser=PL.lqw_spec(9.0), shuntB=PL.lqw_spec(6.2))
PRE = dict(shuntA=PL.lqw_spec(7.2), ser=PL.lqw_spec(7.2), shuntB=PL.lqw_spec(5.2))
R["parts_in_force_9n0_6n2"] = {k: ev(r, INFORCE) for k, r in RUNS.items()}
R["prechecks_retune_7n2_7n2_5n2"] = {k: ev(r, PRE) for k, r in RUNS.items()}
for nm in ("parts_in_force_9n0_6n2", "prechecks_retune_7n2_7n2_5n2"):
    print(nm, {k: (round(v["eta_min"] * 100, 2), round(v["S11_max_dB"], 2)) for k, v in R[nm].items()}, flush=True)

# 3-element search on the as-built body impedance (rule of post_lid: max in-band min body eta with S11 body <= -10 dB and free <= -6 dB)
parts = [("R0",)] + PL.hq_catalogue()
ch = ChainF(fb); ebb, ebf = ML.eta_on(Eas, fb), ML.eta_on(Bas, fb); Zb, Zf = Eas["Z"][sel], Bas["Z"][sel]
res = []
for ser in parts[1:]:
    for sa in parts:
        for sb in parts:
            pi = dict(shuntA=None if sa == ("R0",) else sa, ser=ser, shuntB=None if sb == ("R0",) else sb)
            M = ch.full(pi)
            Gb, GTb, _ = ML.FastChain.eval(M, Zb); Gf, GTf, _ = ML.FastChain.eval(M, Zf)
            res.append(dict(pi=pi, eta_b=float((ebb * GTb).min()), RLb=float((-20 * np.log10(np.abs(Gb))).min()), RLf=float((-20 * np.log10(np.abs(Gf))).min())))
res.sort(key=lambda r: -r["eta_b"])
ok = [r for r in res if r["RLb"] >= 10 and r["RLf"] >= 6]
print("nets", len(res), "meeting S11 rule", len(ok), flush=True)


def mc(pi, n=a.mc, s_mech=0.6, d_len=0.1 / 14.0, seed=5, base=Eas, Dr=Das, Ar=None):
    """post_lid.mc adapted to the real chain: parts (tolerance code), lands +-30 %, returns +-50 %, line Z +-10 % (stack ❓),
    line lengths +-0.05 mm (l_b, stub) and l_a +-3 %, mechanical t~|U(-1,1)| s_mech (Z_A -> Z_D direction of post_lid, as-built offset kept),
    strip length +-0.1 mm as frequency scaling."""
    rng = np.random.default_rng(seed); out = []; rl = []; rlf = []
    ZD = Dr["Z"]; ZB = base["Z"]          # post_lid.mc: Z = Z_E + t (Z_D - Z_E)
    for _ in range(n):
        t = abs(rng.uniform(-1, 1)) * s_mech
        run = dict(base, Z=ZB + t * (ZD - ZB), eta=base["eta"] + t * (Dr["eta"] - base["eta"]))
        run = ML.scaled(run, 1.0 + rng.uniform(-d_len, d_len))
        Zb_ = run["Z"][sel]; eb_ = ML.eta_on(run, fb)
        chm = ChainF(fb, lb=max(0.3, LB + rng.uniform(-0.05, 0.05)), ls=max(0.3, LS + rng.uniform(-0.05, 0.05)), kz=rng.uniform(0.9, 1.1), la_scale=rng.uniform(0.97, 1.03))
        fc = chm.fc; w = 2 * np.pi * fb
        Yp = fc.Ypad * rng.uniform(0.7, 1.3); Lg = fc.Lgnd * rng.uniform(0.5, 1.5)
        def Zp(spec):
            if spec is None: return None
            Z = fc.Zpart(spec)
            if spec[0] == "L":
                k, d = PL.TOL[PL.LQW[round(spec[1] * 1e9, 1)][0][10]] if spec[2].startswith("LQW") else ("abs", 0.1e-9)
                dl = d if k == "abs" else d * spec[1]; return Z + 1j * w * rng.uniform(-dl, dl)
            if spec[0] == "C":
                dc = {"W": 0.05e-12, "B": 0.1e-12, "C": 0.25e-12, "D": 0.5e-12}.get(spec[2][13], 0.05 * spec[1])
                return 1 / (1 / Z + 1j * w * rng.uniform(-dc, dc))
            return Z
        M = chm.full(pi, Ypad=Yp, Lg=Lg, Zp=Zp)
        Gm, GT, _ = ML.FastChain.eval(M, Zb_)
        Gf_, _, _ = ML.FastChain.eval(M, Bas["Z"][sel])
        out.append((eb_ * GT).min()); rl.append((-20 * np.log10(np.abs(Gm))).min()); rlf.append((-20 * np.log10(np.abs(Gf_))).min())
    out = np.array(out); rl = np.array(rl); rlf = np.array(rlf)
    return dict(n=n, s_mech=s_mech, eta_min_median=float(np.median(out)), p5=float(np.percentile(out, 5)), yield_ge_1pct=float((out >= 0.01).mean()),
                yield_ge_5pct=float((out >= 0.05).mean()), RL_body_median=float(np.median(rl)), RL_body_p5=float(np.percentile(rl, 5)),
                yield_S11_le_m10=float((rl >= 10).mean()), yield_free_S11_le_m6=float((rlf >= 6).mean()))


# robustness pick among the top 25 nets meeting the rule: highest S11 yield (then eta), MC n=200 each, final MC n=a.mc
cand = ok[:25]
for r in cand:
    r["mc200"] = mc(r["pi"], n=200)
cand.sort(key=lambda r: (-round(r["mc200"]["yield_S11_le_m10"], 2), -r["eta_b"]))
ymax = cand[0]["mc200"]["yield_S11_le_m10"] if cand else 0
nfit = lambda pi: sum(pi[k] is not None for k in ("shuntA", "ser", "shuntB"))
allq = lambda pi: all(pi[k] is None or (pi[k][0] == "L" and str(pi[k][2]).startswith("LQW")) for k in ("shuntA", "ser", "shuntB"))
near = [r for r in cand if r["mc200"]["yield_S11_le_m10"] >= ymax - 0.03]      # within MC noise (n 200) of the best yield
near.sort(key=lambda r: (nfit(r["pi"]), not allq(r["pi"]), -r["eta_b"]))      # fewest fitted parts, LQW only (C-number + stock known), then eta
pick = near[0] if near else res[0]
top_eta = ok[0] if ok else res[0]
R["search"] = dict(n=len(res), n_meeting_rule=len(ok), rule="S11 body <= -10 dB and free <= -6 dB in 2.40-2.48 GHz (as-built body / free), then highest S11 tolerance yield among the 25 best by body eta",
                   top_eta=dict(pinet=PL.pdesc(top_eta["pi"]), eta_b=top_eta["eta_b"], RLb=top_eta["RLb"], RLf=top_eta["RLf"]),
                   candidates=[dict(pinet=PL.pdesc(r["pi"]), eta_b=round(r["eta_b"], 4), RLb=round(r["RLb"], 2), RLf=round(r["RLf"], 2),
                                    y_S11=r["mc200"]["yield_S11_le_m10"], y5=r["mc200"]["yield_ge_5pct"]) for r in cand[:10]])
R["chosen"] = dict(pinet=PL.pdesc(pick["pi"]), pi=json.loads(json.dumps(pick["pi"])))
R["chosen_cases"] = {k: ev(r, pick["pi"]) for k, r in RUNS.items()}
R["chosen_mc"] = mc(pick["pi"]); R["chosen_mc_mech_full"] = mc(pick["pi"], s_mech=1.0)
R["inforce_mc"] = mc(INFORCE)
R["prechecks_retune_mc"] = mc(PRE)
# sensitivity of the chosen net: line Z of the w0.09 neck at 70 / 79 ohm, lengths edge-to-edge
sens = {}
for nm, kw in (("stub edge-to-edge 0.50", dict(ls=G["stub_edge_to_edge_mm"])), ("l_b +0.1", dict(lb=LB + 0.1)), ("line Z x0.9", dict(kz=0.9)), ("line Z x1.1", dict(kz=1.1))):
    chs = ChainF(f, **kw); v = ev(Eas, pick["pi"], ch=chs); sens[nm] = (round(v["eta_min"] * 100, 2), round(v["S11_max_dB"], 2))
R["chosen_sensitivity_body_asbuilt"] = sens

# link margin (sim11_link.py rule: +4 dBm / -96 dBm both ends, phone -5 dBi, 15 dB body shadow, 2 m, Nordic match IL of SIM-09)
S9 = json.load(open("/path/to/SolarVest_work/wristband/sim/rf/sim09_match/results/sim09_results.json"))
IL = S9["nordic_murata_pads"]["IL_dB_band_max"]


def margin(eta_by_f):
    m = []
    for k, eta in eta_by_f.items():
        L = 20 * math.log10(4 * math.pi * 2.0 * float(k) * 1e9 / 299792458.0)
        m.append(4.0 - IL + 10 * math.log10(eta) - 5.0 - L - 15.0 + 96.0)
    return min(m)


R["link"] = dict(IL_nordic_dB=IL, check_model_in_force_12p6pct=round(margin({"2.44": 0.1263}), 2))
for nm, cs in (("chosen", R["chosen_cases"]), ("parts_in_force", R["parts_in_force_9n0_6n2"]), ("prechecks_retune", R["prechecks_retune_7n2_7n2_5n2"])):
    R["link"][nm] = {k: round(margin(v["eta"]), 2) for k, v in cs.items()}
R["link"]["chosen_mc_p5_eta"] = round(margin({"2.44": R["chosen_mc"]["p5"]}), 2)
json.dump(R, open(os.path.join(HERE, "rf_final.json"), "w"), indent=1, default=str)
print("chosen:", R["chosen"]["pinet"])
print({k: (round(v["eta_min"] * 100, 2), round(v["S11_max_dB"], 2)) for k, v in R["chosen_cases"].items()})
print("mc", json.dumps(R["chosen_mc"]), "\nmc full", json.dumps(R["chosen_mc_mech_full"]), "\ninforce mc", json.dumps(R["inforce_mc"]), "\npre mc", json.dumps(R["prechecks_retune_mc"]))
print("sens", sens, "\nlink", json.dumps(R["link"]))
print(json.dumps(R["search"], indent=0)[:3000])
