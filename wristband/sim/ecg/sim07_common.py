"""Shared helpers for the SIM-07 scripts: electrode grid, environments, worst-case mismatch builder and the
three basic measurements (signal transfer, 50 Hz CM->DM, RLD loop gain). All AC voltages are taken relative
to the floating device ground 'dg' (the band floats; earth is node 0)."""
import sys, pathlib, math
import numpy as np
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
from ngs import NGS          # noqa: E402
from frontend import default_cfg, netlist   # noqa: E402
from params import P         # noqa: E402
from designs import INITIAL, FINAL, FINAL_INTREF, FINAL_REXT, DESIGNS   # noqa: E402,F401

V = lambda k: P[k]["value"]
S = NGS()
RGRID = list(V("electrode_R"))
CGRID = list(V("electrode_C"))
GRID = [(r, c) for r in RGRID for c in CGRID]
M = V("electrode_mismatch")
ENVS = {"typical": dict(cpw=V("c_mains_body")[0], csup=V("c_dev_earth")[0], cdb=V("c_dev_body")[0]),
        "harsh": dict(cpw=V("c_mains_body")[1], csup=V("c_dev_earth")[1], cdb=V("c_dev_body")[1])}
F_BAND = np.logspace(np.log10(0.5), np.log10(40), 25)


def zscale(R, C, m):
    """electrode impedance scaled by (1+m) at every frequency"""
    return (R * (1 + m), C / (1 + m))


def mismatch_cfg(R, C, s, m2, base):
    """worst-case pairing: E1 impedance x(1+s*M), E3 x(1-s*M); the larger-impedance input also gets the larger
    TVS (+10 %), C_CM (+5 %), routing (+0.5 pF) and resistor (+1 %) values. E2 x(1+m2*M)."""
    cfg = dict(base)
    cfg["Re"] = [zscale(R, C, s * M), zscale(R, C, m2 * M), zscale(R, C, -s * M)]
    kt, kc, kr = V("c_tvs_mismatch"), V("c0g_tol"), V("r_prot_tol")
    ct = V("c_tvs")
    cfg["Ctvs"] = [ct * (1 + s * kt), ct, ct * (1 - s * kt)]
    ccm = base["Ccm"][0]
    cfg["Ccm"] = [ccm * (1 + s * kc), ccm * (1 - s * kc)]
    cr, dcr = V("c_route"), V("c_route_mismatch")
    cfg["Croute"] = [cr + s * dcr, cr - s * dcr]
    r = V("r_prot")
    cfg["Rprot"] = [(r * (1 + s * kr),) * 2, (r, r), (r * (1 - s * kr),) * 2]
    return cfg


def signal_att(cfg):
    """max attenuation 1-|H| over 0.5-40 Hz of the Lead-I signal (body -> pins), and the phase at 40 Hz"""
    S.run(netlist(dict(cfg, vecg_ac=1.0, vmains_ac=0.0), ".ac dec 20 0.5 40"))
    f = S.vec("frequency").real
    H = S.vec("inp") - S.vec("inn")
    return float((1 - np.abs(H)).max()), float(np.degrees(np.angle(H[-1]))), f, H


def dm50(cfg, vm=None):
    """50 Hz DM (µVrms) and CM at the pins (mVrms, vs device ground) for 230 Vrms mains.
    DM = external CM->DM conversion (network + electrodes, ngspice) + the ADS1291's own worst-case conversion
    CM_pins / CMRR_min (105 dB, SBAS502C p7), added in magnitude (worst case)."""
    S.run(netlist(dict(cfg, vmains_ac=vm or V("v_mains"), vecg_ac=0.0), ".ac lin 1 50 50"))
    inp, inn, dg = S.vec("inp")[0], S.vec("inn")[0], S.vec("dg")[0]
    cm = abs((inp + inn) / 2 - dg)
    dm = abs(inp - inn) + cm * 10 ** (-V("ads_cmrr_min") / 20)
    return float(dm * 1e6), float(cm * 1e3), float(abs(S.vec("bc")[0]))


def loop(cfg, fmin=0.1, fmax=1e7):
    """Middlebrook voltage injection at RLDOUT (Z_out 100 Ω << Z_load ≥ 660 kΩ): T = -v(rldout)/v(rldn), both vs dg.
    Returns dict(fc, pm, gm, T50, T0)."""
    S.run(netlist(dict(cfg, loopbreak=True, vmains_ac=0.0, vecg_ac=0.0), f".ac dec 60 {fmin} {fmax}"))
    f = S.vec("frequency").real
    dg = S.vec("dg")
    T = -(S.vec("rldout") - dg) / (S.vec("rldn") - dg)
    ph = np.degrees(np.unwrap(np.angle(T)))
    mag = np.abs(T)
    k = np.where(mag < 1)[0]
    out = dict(T0=float(mag[0]), T50=float(np.interp(50, f, mag)))
    if len(k) == 0:
        out.update(fc=None, pm=None, gm=None)
        return out, f, T
    k = k[0]
    # interpolate the crossover
    a = (np.log10(1) - np.log10(mag[k - 1])) / (np.log10(mag[k]) - np.log10(mag[k - 1]))
    fc = 10 ** (np.log10(f[k - 1]) + a * (np.log10(f[k]) - np.log10(f[k - 1])))
    pmv = 180 + ph[k - 1] + a * (ph[k] - ph[k - 1])
    j = np.where(ph < -180)[0]
    gm = float(-20 * np.log10(mag[j[0]])) if len(j) else None
    out.update(fc=float(fc), pm=float(pmv), gm=gm)
    return out, f, T


def dc_point(cfg, nodes=("inp", "inn", "rldout", "e1", "e2", "e3", "lw", "rf"), tstop=2.0):
    """DC operating point vs device ground. Uses .op; if ngspice had to fall back to its 'transient op'
    (gmin and source stepping failed), it retries .op with gmin 1e-12 S, rshunt 1e12 Ω, abstol 1 fA (≤ 0.05 % on the 500 MΩ
    input nodes), and only then re-solves by a real transient to steady state."""
    bad = lambda lg: "Transient op" in lg or "stepping failed" in lg
    log = S.run(netlist(cfg, ".op"))
    how = "op"
    if bad(log):
        log = S.run(netlist(cfg, ".op").replace("rshunt=1e15 gmin=1e-15 reltol=1e-5 abstol=1e-16", "rshunt=1e12 gmin=1e-12 reltol=1e-5 abstol=1e-15", 1))
        how = "op_gmin12"
        if bad(log):
            S.run(netlist(cfg, f".options method=gear\n.tran 5m {tstop} 0 20m uic"))
            how = "tran"
    g = lambda n: float(S.vec(n)[-1])
    dg = g("dg")
    out = {n: g(n) - dg for n in nodes}
    out["i"] = [float(S.vec(f"vhc{i}#branch")[-1]) for i in (1, 2, 3)]
    out["how"] = how
    return out
