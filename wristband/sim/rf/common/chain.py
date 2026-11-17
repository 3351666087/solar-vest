"""RF chain of the SolarBand (SIM-09 / SIM-10), scikit-rf.

  nRF52832 ANT pin -- [C6 pad, DNP] -- L1n 3.9 nH series -- C3n 0.8 pF shunt -- "RF" 50-ohm node
  -- CPWG 3 mm -- pi-net (shunt A | series S | shunt B) -- CPWG 2 mm -- feed via L1->L6 -- IFA port

Topology of the Nordic match: the nRF52832 PS v1.x reference schematic (QFAA DC/DC,
Figure 170 / Table 146; cached text cache/datasheets/nrf52832_lcsc.txt) reads in the
order RF - C3 0.8 pF - L1 3.9 nH - C6 N.C. - ANT, i.e. a pi with the C6 position empty:
series L1 at the pin, shunt C3 at the 50-ohm side.  This order is inferred from the
extracted schematic text (unverified, open item); sim09.py also reports the mirrored
order as a sensitivity case.

Part models: Murata S2P (series-thru fixture), element impedance Z = 2 Z0 (1/S21 - 1)
[Murata].  Board parasitics: results/parasitics.json of sim09_match ([SIM12] pad C,
[CF]/[E] vias).  CPWG: Z0 50.0 ohm, eps_eff 3.088 [SIM12], loss 0.02 dB/mm at 2.44 GHz [E].
"""
import os, json, math
import numpy as np
import skrf as rf
from rfnet import load_part_Z, series, shunt, thru, tline, cascade, ideal_Z

HERE = os.path.dirname(os.path.abspath(__file__))
PARA = json.load(open(os.path.join(HERE, "parasitics_v1.json")))   # copy of sim/rf/sim09_match/results/parasitics.json (v1, 0.8 mm stack) [E for the 1.0 mm stack]
C_PAD = PARA["pad_0402"]["C_excess_pF"] * 1e-12         # per 0402 land [SIM12]
L_GND = PARA["gnd_via_L1L2"]["used_nH"] * 1e-9           # shunt-part return [E]
EEFF = PARA["cpwg"]["eps_eff"]
Z0_LINE = PARA["cpwg"]["Z0"]
VIA = PARA["feed_via"]
R0 = PARA["zero_ohm_0402"]


def freq(f0=0.5e9, f1=8.0e9, n=1501):
    return rf.Frequency(f0, f1, n, unit="hz")


def pad(fr):
    return shunt(ideal_Z("C", C_PAD, fr), fr)


def part_Z(spec, fr):
    """spec: None | ('R0',) | ('L'|'C', value, file or None).  Returns Z(f) or None (open)."""
    if spec is None:
        return None
    if spec[0] == "R0":
        return R0["R_ohm"] + 1j * 2 * np.pi * fr.f * R0["ESL_nH"] * 1e-9
    kind, val, fname = spec
    if fname:
        Z, _ = load_part_Z(fname, fr)
        return Z
    return ideal_Z(kind, val, fr)


def series_part(spec, fr, with_pads=True):
    """series 0402 between two lands (each land = shunt C_PAD)."""
    n = series(part_Z(spec, fr), fr)
    return cascade(pad(fr), n, pad(fr)) if with_pads else n


def shunt_part(spec, fr, with_pads=True):
    """shunt 0402: land on the signal side (C_PAD) + part + ground land/vias (L_GND)."""
    if spec is None:
        return pad(fr) if with_pads else thru(fr)        # DNP: the empty land still loads the line
    Z = part_Z(spec, fr) + (1j * 2 * np.pi * fr.f * L_GND if with_pads else 0)
    n = shunt(Z, fr)
    return cascade(pad(fr), n) if with_pads else n


def feed_via(fr):
    return tline(fr, VIA["length_mm"], Zc=VIA["Zc_ohm"], eeff=VIA["er"], alpha_db_per_mm_at_f0=0.0)


def cpwg(fr, mm):
    return tline(fr, mm, Zc=Z0_LINE, eeff=EEFF, alpha_db_per_mm_at_f0=0.02)


NORDIC_REAL = dict(L1=("L", 3.9e-9, "LQG15HS3N9B02.s2p"), C3=("C", 0.8e-12, "GJM1555C1HR80WB01.s2p"), C6=None)
NORDIC_IDEAL = dict(L1=("L", 3.9e-9, None), C3=("C", 0.8e-12, None), C6=None)


def nordic(fr, parts=NORDIC_REAL, with_pads=True, mirrored=False):
    """2-port: port 1 = ANT pin, port 2 = 50-ohm RF node."""
    c6 = shunt_part(parts["C6"], fr, with_pads)
    l1 = series_part(parts["L1"], fr, with_pads)
    c3 = shunt_part(parts["C3"], fr, with_pads)
    if mirrored:                 # C3 at the pin, C6 (empty) at the RF side
        return cascade(c3, l1, c6)
    return cascade(c6, l1, c3)


def pinet(fr, shuntA=None, ser=("R0",), shuntB=None, with_pads=True):
    """pi-net: shunt A (chip side) | series | shunt B (antenna side).  Empty shunt lands stay."""
    return cascade(shunt_part(shuntA, fr, with_pads), series_part(ser, fr, with_pads),
                   shunt_part(shuntB, fr, with_pads))


def antenna_side(fr, pi=None, l_a=3.0, l_b=2.0, via=False):
    """2-port from the 50-ohm RF node to the radiator port.  V2-B: the RF line, the pi-net and the
    radiator feed are all on the sky-side outer layer, so there is no feed via (via=False)."""
    pi = pi or {}
    if via:
        return cascade(cpwg(fr, l_a), pinet(fr, **pi), cpwg(fr, l_b), feed_via(fr))
    return cascade(cpwg(fr, l_a), pinet(fr, **pi), cpwg(fr, l_b))


def z_opt(fr, mirrored=False):
    """Target load at the ANT pin = ideal Nordic network terminated in 50 ohm."""
    n = nordic(fr, NORDIC_IDEAL, with_pads=False, mirrored=mirrored)
    s = n.s
    G = s[:, 0, 0]          # port 2 terminated in z0 = 50 -> Gamma_in = S11
    return 50.0 * (1 + G) / (1 - G)


def gamma_in(net, ZL):
    z0 = 50.0
    GL = (ZL - z0) / (ZL + z0)
    s = net.s
    return s[:, 0, 0] + s[:, 0, 1] * s[:, 1, 0] * GL / (1 - s[:, 1, 1] * GL)


def transducer(net, ZS, ZL):
    """P_load / P_available for a source ZS at port 1 and load ZL at port 2 (ABCD form).
    Returns (G_T, Zin)."""
    abcd = net.a
    A, B, C, D = abcd[:, 0, 0], abcd[:, 0, 1], abcd[:, 1, 0], abcd[:, 1, 1]
    Zin = (A * ZL + B) / (C * ZL + D)
    I1 = 1.0 / (ZS + Zin)
    I2 = I1 / (C * ZL + D)
    PL = 0.5 * np.abs(I2) ** 2 * np.real(ZL)
    Pav = 1.0 / (8 * np.real(ZS))
    return PL / Pav, Zin
