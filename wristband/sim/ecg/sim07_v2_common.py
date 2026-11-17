"""Shared helpers for the V2-B SIM-07 scripts. Builds on sim07_common.py (v1 model, unchanged) and lib/params_v2.py.

What V2-B changes in the electrode / input network (REDESIGN 5.5, 5.7; netlist v2/design/src/ecg.py, io_block.py):
  - E1, E2: Ti plates bonded 0.10 mm (carrier film) from the board; extra capacitance from each plate (= the pad node
    ahead of the 2 x 330 kOhm) to device ground: board copper through the voids, the cell pouch, the floating TMP117 island
  - E3: Ti strip on the top rim, spring finger: only a small stray -> the two ECG inputs are no longer symmetric
  - nothing else in the chain changes (TVS, 2 x 330 kOhm, C_CM / C_DIFF DNP, RLD CEXT 150 pF + Rz 470 kOhm, gain 4)
STRUCT[name] = extra capacitance (F) at the pad nodes (E1, E2, E3).
"""
import sys, math, itertools
import numpy as np
from sim07_common import (S, GRID, ENVS, M, V, HERE, default_cfg, mismatch_cfg, signal_att, dm50, loop, zscale, netlist,
                          dc_point, INITIAL, FINAL, FINAL_REXT)   # noqa: F401
import params_v2 as Q        # noqa: E402  (lib/ is on sys.path through sim07_common)

RULE = "B.Cu and L5 void, copper on L4 (design rule PLATE_VOID)"
E3S = Q.P["c_e3_stray"]["value"]


def struct(case=RULE, island=16.0, cell=True, e3=None, bal=0.0):
    c1, c2, _ = Q.plate_caps(case, island, cell)
    return (c1, c2, (E3S[0] if e3 is None else e3) + bal)


STRUCT = {
    "v1 (springs, no plates)": (0.0, 0.0, 0.0),
    "V2-B rule: B.Cu + L5 void": struct(),
    "V2-B rule, max (E3 stray 2 pF, island 25 mm2)": struct(island=25.0, e3=E3S[1]),
    "V2-B, only B.Cu void (L5 copper)": struct("B.Cu void, copper on L5"),
    "V2-B, no void (B.Cu copper)": struct("B.Cu copper (ground or pour) under the plate"),
    "V2-B rule + L4 void too": struct("B.Cu, L5 and L4 void, copper on L3"),
}
PLATE_TOL = 0.20      # +-20 % on the structure capacitance (film 0.10 +-0.02 mm, overlap, er): estimate


def add_caps(cfg, caps, s=0):
    """add the structure capacitances at the pad nodes; s = +1/-1 puts the tolerance on the side that already has the larger impedance"""
    cfg = dict(cfg); ct = list(cfg["Ctvs"])
    ct[0] += caps[0] * (1 + s * PLATE_TOL); ct[1] += caps[1]; ct[2] += caps[2] * (1 - s * PLATE_TOL)
    cfg["Ctvs"] = ct
    return cfg


def base(net=FINAL, caps=None, **kw):
    cfg = default_cfg(**net, **kw)
    return add_caps(cfg, caps) if caps else cfg


def mm(R, C, s, m2, cfg0, caps):
    """ARCH worst-case mismatch pairing (sim07_common.mismatch_cfg) plus the V2-B structure capacitances"""
    return add_caps(mismatch_cfg(R, C, s, m2, cfg0), caps, s)


def bp(f, f_hp=0.5, f_lp=40.0):
    """0.5 Hz 2nd-order high-pass and 40 Hz 4th-order Butterworth low-pass (the ARCH 7.2 digital filter class)"""
    s = 1j * f / f_hp; hp = s * s / (s * s + 1.4142 * s + 1)
    s = 1j * f / f_lp; lp = 1 / ((s * s + 0.7654 * s + 1) * (s * s + 1.8478 * s + 1))
    return hp * lp


N_T, DF = 40000, 0.05          # 20 s window, 2 kHz sample rate equivalent
F_T = np.arange(1, N_T // 2 + 1) * DF


def step_response(H, pulse=None):
    """in-band (0.5-40 Hz) response of the differential input to a unit voltage step (pulse = None) or to a unit
    rectangular pulse of the given length (s) on the source. H = transfer source -> V(inp)-V(inn) on F_T.
    Returns (peak, peak-to-peak) in V per V."""
    w = 2j * np.pi * F_T
    src = 1 / w if pulse is None else (1 - np.exp(-w * pulse)) / w
    X = H * bp(F_T) * src
    spec = np.zeros(N_T, complex); spec[1:N_T // 2 + 1] = X; spec[N_T // 2 + 1:] = np.conj(X[:-1][::-1])
    y = np.fft.ifft(spec).real * N_T * DF
    return float(np.abs(y).max()), float(y.max() - y.min()), y


def transfer(cfg, extra_lines):
    """AC transfer of the sources named in extra_lines (one of them with AC 1) to the differential input, on F_T"""
    c = dict(cfg, vmains_ac=0.0, vecg_ac=0.0, extra=(cfg.get("extra", "") + "\n" + extra_lines).strip())
    S.run(netlist(c, ".ac lin %d %g %g" % (N_T // 2, DF, N_T // 2 * DF)))
    return S.vec("inp") - S.vec("inn")


key = lambda Rr, C: f"{Rr/1e6:g}M_{C*1e9:g}n"
