"""Matching-network evaluation for gate 3a (adapted from sim/rf/sim10_ifa/analyze_ifa.py, same definitions):

  50-ohm RF node -- CPWG l_a (3 mm) -- pi-net (shunt A | series | shunt B, <= 2 parts fitted, empty lands still
  loaded) -- CPWG l_b -- radiator port (delta gap at the board ground edge on F.Cu; no feed via in V2-B).

  S11      = reflection at the 50-ohm RF node
  eta_rad  = P_rad / P_acc at the radiator port (FDTD flux box / port V-I)
  eta_tot  = eta_rad * G_T(network, 50 ohm -> Z_ant)   (mismatch + part, land and line losses)
Part models: Murata GJM1555C1H / LQG15HS S2P files (cache/rf/murata/sel), lands 0.058 pF, shunt return 0.10 nH,
CPWG 50.0 ohm / eps_eff 3.088 / 0.02 dB/mm: values of the v1 0.8 mm stack (common/parasitics_v1.json), used here
as estimates for the 1.0 mm stack (SIM-12 for JLC06101H-3313 is another lane).
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "common"))
import numpy as np
import skrf as rf
import chain as C
from post import port_Z
from rfnet import murata_catalogue

BAND = (2.40e9, 2.48e9)
TOL_PREF = {"C": ["W", "B", "C", "D", "F", "G", "J"], "L": ["B", "C", "S", "G", "H", "J"]}


def load_run(path):
    D = dict(np.load(path, allow_pickle=True))
    f, Z, V, I, P = port_Z(D)
    ff = D["flux_freqs_hz"]
    eta = D["P_flux"] / np.interp(ff, f, P)
    meta = {}
    mp_ = path.replace(".npz", "_meta.json")
    if os.path.exists(mp_):
        meta = json.load(open(mp_))
    return dict(f=f, Z=Z, eta_f=ff, eta=eta, D=D, meta=meta, path=path)


def scaled(run, k):
    """frequency-scaled copy: the response the same structure would have with every resonance moved by the
    factor k (f_new = k * f_old), i.e. Z_new(f) = Z(f / k).  Used as a first-order model of a small change of
    the radiator length; a surrogate, not an FDTD result."""
    f = run["f"]
    Zr = np.interp(f / k, f, run["Z"].real); Zi = np.interp(f / k, f, run["Z"].imag)
    eta = np.interp(run["eta_f"] / k, run["eta_f"], run["eta"])
    return dict(run, Z=Zr + 1j * Zi, eta=eta, scale=k)


def eta_on(run, f):
    return np.interp(f, run["eta_f"], run["eta"])


def f_res(f, Z):
    im = Z.imag
    k = np.where((np.sign(im[:-1]) < 0) & (np.sign(im[1:]) > 0) | (np.sign(im[:-1]) > 0) & (np.sign(im[1:]) < 0))[0]
    return [float(f[i] - im[i] * (f[i + 1] - f[i]) / (im[i + 1] - im[i])) for i in k]


def abcd_series(Z):
    n = len(Z); M = np.zeros((n, 2, 2), complex)
    M[:, 0, 0] = 1; M[:, 1, 1] = 1; M[:, 0, 1] = Z
    return M


def abcd_shunt(Y):
    n = len(Y); M = np.zeros((n, 2, 2), complex)
    M[:, 0, 0] = 1; M[:, 1, 1] = 1; M[:, 1, 0] = Y
    return M


def mm(*Ms):
    out = Ms[0]
    for M in Ms[1:]:
        out = np.einsum("fij,fjk->fik", out, M)
    return out


class FastChain:
    def __init__(self, f, l_b=2.0, l_a=3.0, via=False):
        self.f = f; self.l_b = l_b; self.l_a = l_a; self.via = via
        self.fr = rf.Frequency.from_f(f, unit="hz")
        w = 2 * np.pi * f
        self.Ypad = 1j * w * C.C_PAD
        self.Lgnd = 1j * w * C.L_GND
        self.A_lineA = C.cpwg(self.fr, l_a).a
        self.A_tail = (C.cascade(C.cpwg(self.fr, l_b), C.feed_via(self.fr)) if via else C.cpwg(self.fr, l_b)).a
        self.Zcache = {}

    def Zpart(self, spec):
        key = tuple(spec) if spec else None
        if key not in self.Zcache:
            self.Zcache[key] = C.part_Z(spec, self.fr)
        return self.Zcache[key]

    def pinet_abcd(self, shuntA, ser, shuntB):
        P = abcd_shunt(self.Ypad)
        A = abcd_shunt(self.Ypad + (0 if shuntA is None else 1.0 / (self.Zpart(shuntA) + self.Lgnd)))
        S = abcd_series(self.Zpart(ser))
        B = abcd_shunt(self.Ypad + (0 if shuntB is None else 1.0 / (self.Zpart(shuntB) + self.Lgnd)))
        return mm(A, P, S, P, B)

    def full(self, pi):
        return mm(self.A_lineA, self.pinet_abcd(**pi), self.A_tail)

    @staticmethod
    def eval(M, ZL, Rs=50.0):
        A, B, Cc, D = M[:, 0, 0], M[:, 0, 1], M[:, 1, 0], M[:, 1, 1]
        Zin = (A * ZL + B) / (Cc * ZL + D)
        G = (Zin - Rs) / (Zin + Rs)
        GT = 4 * Rs * np.real(ZL) / np.abs((A * ZL + B) + Rs * (Cc * ZL + D)) ** 2
        return G, GT, Zin


_CAT = None


def catalogue(lmax=27e-9, cmax=10e-12):
    global _CAT
    if _CAT is None:
        cat = {}
        for c in murata_catalogue():
            if (c["kind"] == "L" and c["value"] > lmax) or (c["kind"] == "C" and c["value"] > cmax):
                continue
            key = (c["kind"], round(c["value"] * 1e15))
            tol = c["part"][-4] if c["kind"] == "C" else c["part"][-3]
            rank = TOL_PREF[c["kind"]].index(tol) if tol in TOL_PREF[c["kind"]] else 99
            if key not in cat or rank < cat[key][0]:
                cat[key] = (rank, c)
        _CAT = [v[1] for v in sorted(cat.values(), key=lambda r: (r[1]["kind"], r[1]["value"]))]
    return _CAT


def spec_of(c):
    return (c["kind"], c["value"], c["file"]) if c else None


def describe(spec):
    if spec is None:
        return "DNP"
    if spec[0] == "R0":
        return "0R"
    v = spec[1]
    return f"{v*1e9:.2g} nH ({spec[2][:-4]})" if spec[0] == "L" else f"{v*1e12:.2g} pF ({spec[2][:-4]})"


def pi_desc(pi):
    return f"A:{describe(pi['shuntA'])} | S:{describe(pi['ser'])} | B:{describe(pi['shuntB'])}"


def band_sel(f):
    return (f >= BAND[0] - 1e3) & (f <= BAND[1] + 1e3)


def search(fb, Zb, Zf, eb, ef, l_b, top=8, body_only=False):
    """exhaustive pi-net search (<= 2 fitted parts) on the in-band frequency points fb only.
    score = min(RL_body - 10, RL_free - 6) dB (>= 0 meets both ARCH 9 S11 criteria)."""
    fc = FastChain(fb, l_b)
    cat = catalogue()
    parts = [None] + [spec_of(c) for c in cat]
    sers = [("R0",)] + [spec_of(c) for c in cat]
    res = []
    for ser in sers:
        for side in ("A", "B"):
            for sh in parts:
                if sh is None and side == "B":
                    continue
                pi = dict(shuntA=sh if side == "A" else None, ser=ser, shuntB=sh if side == "B" else None)
                M = fc.full(pi)
                Gb, GTb, _ = fc.eval(M, Zb)
                Gf, GTf, _ = fc.eval(M, Zf)
                rlb = (-20 * np.log10(np.abs(Gb))).min()
                rlf = (-20 * np.log10(np.abs(Gf))).min()
                etb = (eb * GTb).min(); etf = (ef * GTf).min()
                score = (rlb - 10.0) if body_only else min(rlb - 10.0, rlf - 6.0)
                res.append(dict(pi=pi, nparts=1 + (sh is not None), l_b_mm=l_b, RL_body_min=float(rlb),
                                RL_free_min=float(rlf), eta_tot_body_min=float(etb), eta_tot_free_min=float(etf),
                                score=float(score)))
    res.sort(key=lambda r: (-(r["score"] >= 0), -min(r["score"], 3.0), -r["eta_tot_body_min"]))
    return res[:top], len(res)


def evaluate(f, Zb, Zf, eb, ef, pi, l_b):
    """full-grid evaluation of one pi-net: curves + band numbers"""
    fc = FastChain(f, l_b)
    M = fc.full(pi)
    Gb, GTb, _ = fc.eval(M, Zb); Gf, GTf, _ = fc.eval(M, Zf)
    sel = band_sel(f)
    S11b = 20 * np.log10(np.abs(Gb)); S11f = 20 * np.log10(np.abs(Gf))
    out = dict(pinet=pi_desc(pi), l_b_mm=l_b,
               S11_body_dB_band_max=float(S11b[sel].max()), S11_free_dB_band_max=float(S11f[sel].max()),
               eta_tot_body_min=float((eb * GTb)[sel].min()), eta_tot_free_min=float((ef * GTf)[sel].min()),
               eta_tot_body={f"{x/1e9:.2f}": float(np.interp(x, f, eb * GTb)) for x in (2.40e9, 2.44e9, 2.48e9)},
               eta_tot_free={f"{x/1e9:.2f}": float(np.interp(x, f, ef * GTf)) for x in (2.40e9, 2.44e9, 2.48e9)},
               eta_rad_body={f"{x/1e9:.2f}": float(np.interp(x, f, eb)) for x in (2.40e9, 2.44e9, 2.48e9)},
               eta_rad_free={f"{x/1e9:.2f}": float(np.interp(x, f, ef)) for x in (2.40e9, 2.44e9, 2.48e9)},
               network_loss_dB_band_max=dict(
                   body=float((-10 * np.log10(GTb / (1 - np.abs(Gb) ** 2)))[sel].max()),
                   free=float((-10 * np.log10(GTf / (1 - np.abs(Gf) ** 2)))[sel].max())),
               score=float(min(-S11b[sel].max() - 10, -S11f[sel].max() - 6)))
    out["criteria_ARCH9"] = dict(S11_body_le_m10=bool(S11b[sel].max() <= -10), S11_free_le_m6=bool(S11f[sel].max() <= -6),
                                 eta_tot_body_ge_5pct=bool(out["eta_tot_body_min"] >= 0.05))
    return out, dict(S11b=S11b, S11f=S11f, etb=eb * GTb, etf=ef * GTf, Gb=Gb, Gf=Gf, GTb=GTb, GTf=GTf)


def tolerance_check(f, pi, l_b, Zb, Zf, n=300, seed=2):
    """Monte Carlo of the fitted parts (tolerance code of the S2P part), lands +-30 %, shunt return +-50 %"""
    fc = FastChain(f, l_b)
    sel = band_sel(f)
    rng = np.random.default_rng(seed)
    w = 2 * np.pi * f
    tol_abs = {"W": 0.05e-12, "B": 0.1e-12, "C": 0.25e-12, "D": 0.5e-12}
    ob, of_ = [], []
    for _ in range(n):
        PADs = fc.Ypad * rng.uniform(0.7, 1.3)
        Lg = fc.Lgnd * rng.uniform(0.5, 1.5)

        def Zp(spec):
            if spec is None:
                return None
            Z = fc.Zpart(spec)
            if spec[0] == "L":
                dl = {"B": 0.1e-9, "C": 0.2e-9, "S": 0.3e-9}.get(spec[2][10], 0.05 * spec[1])
                return Z + 1j * w * rng.uniform(-dl, dl)
            if spec[0] == "C":
                dc = tol_abs.get(spec[2][13], 0.05 * spec[1])
                return 1.0 / (1.0 / Z + 1j * w * rng.uniform(-dc, dc))
            return Z

        def sh(spec):
            Z = Zp(spec)
            return abcd_shunt(PADs + (0 if Z is None else 1.0 / (Z + Lg)))
        M = mm(fc.A_lineA, sh(pi["shuntA"]), abcd_shunt(PADs), abcd_series(Zp(pi["ser"])), abcd_shunt(PADs),
               sh(pi["shuntB"]), fc.A_tail)
        Gb, _, _ = fc.eval(M, Zb); Gf, _, _ = fc.eval(M, Zf)
        ob.append((-20 * np.log10(np.abs(Gb[sel]))).min()); of_.append((-20 * np.log10(np.abs(Gf[sel]))).min())
    return dict(n=n, RL_body_min_p5=float(np.percentile(ob, 5)), RL_body_min_worst=float(np.min(ob)),
                RL_free_min_p5=float(np.percentile(of_, 5)), RL_free_min_worst=float(np.min(of_)))


def pi_from_json(pj):
    conv = lambda v: None if v is None else (tuple(v) if v[0] == "R0" else (v[0], float(v[1]), v[2]))
    return dict(shuntA=conv(pj["shuntA"]), ser=conv(pj["ser"]), shuntB=conv(pj["shuntB"]))


def pi_to_json(pi):
    return dict(shuntA=pi["shuntA"], ser=pi["ser"], shuntB=pi["shuntB"], desc=pi_desc(pi))
