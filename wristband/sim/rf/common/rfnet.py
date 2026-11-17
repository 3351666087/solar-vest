"""RF network building blocks for SIM-09/SIM-10 (scikit-rf).

Component models come from Murata S2P files (series-thru fixture, 50 ohm):
the element impedance is extracted as Z = 2*Z0*(1/S21 - 1) and re-used as a
series or a shunt element.  Board parasitics (0402 pad excess capacitance,
ground-via inductance, the L1->L6 feed via, CPWG lines) are added explicitly.
All parasitic values are labelled [SIM12] (from the 2-D solver) or [E].
"""
import os, glob, math, json
import numpy as np
import skrf as rf

C0 = 299792458.0
HERE = os.path.dirname(os.path.abspath(__file__))
S2P_DIR = "/path/to/SolarVest_work/wristband/cache/rf/murata/sel"   # read-only (Murata S2P library, sim/rf README section 5)


def freq(f0=0.5e9, f1=8.0e9, n=1501):
    return rf.Frequency(f0, f1, n, unit="hz")


# ------------------------------------------------------------------ parts
def load_part_Z(fname, fr):
    """Element impedance from a Murata series-thru S2P, interpolated on fr."""
    nt = rf.Network(os.path.join(S2P_DIR, fname))
    s21 = nt.s[:, 1, 0]
    z0 = np.real(nt.z0[:, 0])
    Z = 2 * z0 * (1 / s21 - 1)
    # interpolate real/imag on fr (linear); outside the measured range -> nan
    f = nt.f
    Zr = np.interp(fr.f, f, Z.real, left=np.nan, right=np.nan)
    Zi = np.interp(fr.f, f, Z.imag, left=np.nan, right=np.nan)
    return Zr + 1j * Zi, (f.min(), f.max())


def ideal_Z(kind, value, fr, q=None, esr=0.0):
    w = 2 * np.pi * fr.f
    if kind == "L":
        return esr + 1j * w * value
    if kind == "C":
        return esr + 1 / (1j * w * value)
    if kind == "R":
        return value + 0j * w
    raise ValueError(kind)


def series(Z, fr, z0=50.0):
    """2-port series element with impedance Z(f)."""
    s = np.zeros((len(fr), 2, 2), complex)
    d = Z + 2 * z0
    s[:, 0, 0] = Z / d; s[:, 1, 1] = Z / d
    s[:, 0, 1] = 2 * z0 / d; s[:, 1, 0] = 2 * z0 / d
    return rf.Network(frequency=fr, s=s, z0=z0)


def shunt(Z, fr, z0=50.0):
    """2-port shunt element to ground with impedance Z(f)."""
    s = np.zeros((len(fr), 2, 2), complex)
    Y = 1 / Z
    d = 2 + Y * z0
    s[:, 0, 0] = -Y * z0 / d; s[:, 1, 1] = -Y * z0 / d
    s[:, 0, 1] = 2 / d; s[:, 1, 0] = 2 / d
    return rf.Network(frequency=fr, s=s, z0=z0)


def thru(fr, z0=50.0):
    s = np.zeros((len(fr), 2, 2), complex); s[:, 0, 1] = 1; s[:, 1, 0] = 1
    return rf.Network(frequency=fr, s=s, z0=z0)


def tline(fr, length_mm, Zc=50.0, eeff=3.088, alpha_db_per_mm_at_f0=0.02, f0=2.44e9, z0=50.0):
    """Lossy TEM line: alpha scales ~ sqrt(f) (conductor) + f (dielectric); we
    split the 2.44 GHz value 60/40 conductor/dielectric [E]."""
    f = fr.f
    a0 = alpha_db_per_mm_at_f0 / 8.686 * 1e3          # Np/m at f0
    alpha = a0 * (0.6 * np.sqrt(f / f0) + 0.4 * (f / f0))
    beta = 2 * np.pi * f * np.sqrt(eeff) / C0
    gamma = alpha + 1j * beta
    L = length_mm * 1e-3
    # ABCD of a line, then to S in z0
    ch, sh = np.cosh(gamma * L), np.sinh(gamma * L)
    A = ch; B = Zc * sh; C = sh / Zc; D = ch
    abcd = np.zeros((len(f), 2, 2), complex)
    abcd[:, 0, 0] = A; abcd[:, 0, 1] = B; abcd[:, 1, 0] = C; abcd[:, 1, 1] = D
    s = rf.network.a2s(abcd, z0)
    return rf.Network(frequency=fr, s=s, z0=z0)


def cascade(*nets):
    out = nets[0]
    for n in nets[1:]:
        out = out ** n
    return out


def terminate(net, Zload):
    """input reflection of a 2-port terminated by Zload(f) (z0 of the net)"""
    z0 = np.real(net.z0[:, 1])
    GL = (Zload - z0) / (Zload + z0)
    s = net.s
    return s[:, 0, 0] + s[:, 0, 1] * s[:, 1, 0] * GL / (1 - s[:, 1, 1] * GL)


def delivered_fraction(net, Zload):
    """Power delivered to Zload / power available from a z0 source at port 1."""
    z0 = np.real(net.z0[:, 1])
    GL = (Zload - z0) / (Zload + z0)
    s = net.s
    Gin = s[:, 0, 0] + s[:, 0, 1] * s[:, 1, 0] * GL / (1 - s[:, 1, 1] * GL)
    # transducer gain with Gs = 0
    GT = np.abs(s[:, 1, 0]) ** 2 * (1 - np.abs(GL) ** 2) / np.abs(1 - s[:, 1, 1] * GL) ** 2
    return GT, Gin


def dissipated_fraction(net, Zload):
    """fraction of the power accepted at port 1 that the network dissipates"""
    GT, Gin = delivered_fraction(net, Zload)
    acc = 1 - np.abs(Gin) ** 2
    return 1 - GT / acc


# ------------------------------------------------------------------ catalogue
def murata_catalogue():
    """values available as S2P: GJM1555C1H (C0G, 0402, W/B tolerance) and LQG15HS (0402)."""
    cat = []
    for p in sorted(glob.glob(os.path.join(S2P_DIR, "GJM1555C1H*.s2p"))):
        n = os.path.basename(p)[:-4]
        code = n[10:13]   # e.g. R80, 1R0, 2R2, 100
        try:
            if "R" in code:
                v = float(code.replace("R", ".")) if code[0] != "R" else float("0." + code[1:])
            else:
                v = float(code[:2]) * 10 ** int(code[2])
        except Exception:
            continue
        cat.append(dict(kind="C", value=v * 1e-12, file=os.path.basename(p), part=n))
    for p in sorted(glob.glob(os.path.join(S2P_DIR, "LQG15HS*.s2p"))):
        n = os.path.basename(p)[:-4]
        code = n[7:10]    # 3N9, 12N
        try:
            v = float(code.replace("N", ".")) if "N" in code else None
        except Exception:
            v = None
        if v is None:
            continue
        cat.append(dict(kind="L", value=v * 1e-9, file=os.path.basename(p), part=n))
    return cat
