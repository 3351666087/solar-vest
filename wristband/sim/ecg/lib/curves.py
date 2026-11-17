"""Vendor curves (digitised in refs/digitise.py) as functions, with every extrapolation stated.

ldo_psrr_db(f)  : TPS7A02 PSRR, worst of the 0 mA and 1 mA curves (Fig 6-43, SBVS277C p15); our AVDD load is
                  ≈0.15-0.3 mA, i.e. between them. Minus the low-headroom derate (params.ldo_psrr_headroom_derate_db).
                  Below 10.6 Hz: held at the lowest value of the 10-100 Hz decade (E). Above 9.4 MHz: held (E).
ldo_noise(f)    : TPS7A02 output noise density, worst of the 100 µA and 1 mA curves (Fig 6-48, p15), × VOUT
                  scale 3.0/1.8 (Fig 6-47) × digitising calibration 1.05. Below 10.6 Hz: 1/f power law (density
                  ∝ f^-0.5) from the highest density in 10.6-15 Hz (E).
ads_psrr_db(f,g): ADS1291 AVDD PSRR for PGA gain g (Fig 8, SBAS502C p13, digitised to 981 Hz). Below 10 Hz held
                  (E); above 1 kHz extrapolated at -20 dB/decade from the 1 kHz value, floored at 30 dB (E) – the
                  datasheet gives nothing above 1 kHz.
"""
import json, pathlib
import numpy as np
from params import P

C = json.loads((pathlib.Path(__file__).resolve().parents[1] / "refs" / "curves.json").read_text())


def _interp(name, f):
    fx = np.log10(np.asarray(C[name]["f_hz"])); y = np.asarray(C[name]["y"])
    return np.interp(np.log10(np.asarray(f, dtype=float)), fx, y)


def ldo_psrr_db(f):
    f = np.atleast_1d(np.asarray(f, dtype=float))
    lo = min(_interp("tps7a02_psrr_0mA", np.logspace(np.log10(10.6), 2, 30)).min(),
             _interp("tps7a02_psrr_1mA", np.logspace(np.log10(10.6), 2, 30)).min())
    v = np.minimum(_interp("tps7a02_psrr_0mA", f), _interp("tps7a02_psrr_1mA", f))
    v = np.where(f < 10.6, lo, v)
    return v - P["ldo_psrr_headroom_derate_db"]["value"]


def ldo_noise(f):
    """V/sqrt(Hz) at AVDD = 3.0 V"""
    f = np.atleast_1d(np.asarray(f, dtype=float))
    k = P["ldo_noise_vscale"]["value"] * P["ldo_noise_digcal"]["value"] * 1e-6
    v = np.maximum(10 ** _interp_log("tps7a02_noise_100uA", f), 10 ** _interp_log("tps7a02_noise_1mA", f))
    fl = np.logspace(np.log10(10.6), np.log10(15), 10)
    a = np.maximum(10 ** _interp_log("tps7a02_noise_100uA", fl), 10 ** _interp_log("tps7a02_noise_1mA", fl)).max()
    v = np.where(f < 10.6, a * np.sqrt(10.6 / np.maximum(f, 1e-3)), v)
    return v * k


def _interp_log(name, f):
    fx = np.log10(np.asarray(C[name]["f_hz"])); y = np.log10(np.asarray(C[name]["y"]))
    return np.interp(np.log10(np.asarray(f, dtype=float)), fx, y)


def ads_psrr_db(f, gain):
    f = np.atleast_1d(np.asarray(f, dtype=float))
    name = f"ads1291_psrr_g{gain}"
    v = _interp(name, f)
    v1k = _interp(name, [970.0])[0]
    v = np.where(f > 970.0, np.maximum(v1k - 20 * np.log10(f / 970.0), 30.0), v)
    return v


# ------------------------------------------------------------------------------- TPS7A2030 (SIM-06 design change)
def _pts(name):
    a = np.asarray(P[name]["value"], dtype=float)
    return np.log10(a[:, 0]), a[:, 1]


def ln_ldo_psrr_db(f):
    """TPS7A20 PSRR (SBVS338H p18 Fig 5-63, read by eye, E); flat below 10 Hz and above 10 MHz"""
    fx, y = _pts("ln_ldo_psrr_pts")
    return np.interp(np.log10(np.atleast_1d(np.asarray(f, dtype=float))), fx, y)


def _ln_raw(f):
    fx, y = _pts("ln_ldo_noise_pts")
    f = np.atleast_1d(np.asarray(f, dtype=float))
    v = 10 ** np.interp(np.log10(np.maximum(f, 1e-3)), fx, np.log10(y))
    return np.where(f < 10, y[0] * np.sqrt(10 / np.maximum(f, 1e-3)), v)


_fchk = np.logspace(1, 5, 2000)
LN_DIGCAL = 8.63 / float(np.sqrt(np.trapezoid(_ln_raw(_fchk) ** 2, _fchk)))   # read points vs TI's printed 8.63 µVrms


def ln_ldo_noise(f):
    """V/sqrt(Hz) at 3.0 V: read points × 3.0/2.8 × max(1, calibration to TI's printed RMS)"""
    return _ln_raw(f) * (3.0 / 2.8) * max(1.0, LN_DIGCAL) * 1e-6
