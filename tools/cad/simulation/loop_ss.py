"""TB1c — small-signal loop gain of the CN3791 input-voltage (MPPT) loop, averaged model.
Plant (battery = stiff source):  L s il = D vpv + Vpv d − R il ;  Zin^-1 vpv = −vpv/r_pv − D il − IL d
Controller: i_com = gm · (51/251) · vpv  into  R4 + 1/(s C6);  d = v_com / Vramp  (Vramp = 1.8 V in the model).
Unknown: gm/Vramp (CN3791 datasheet gives neither) -> swept. Damping branch option: C_d with ESR R_d on VPV."""
import sys, json, numpy as np; sys.path.insert(0, ".")
from ngs import NGS; import tb_charger as T
L, R4, C6, K_DIV, VRAMP = 22e-6, 120.0, 220e-9, 51 / 251, 1.8
R_LOOP = 0.09 + 0.10 + 0.08 + 0.66 * 0.045 + 0.05            # DCR + R8 + Rbat + D·Rds(M1) + diode dynamic
def pv_point(G, Tc, v0=5.93):
    s = NGS(); s.run(f"pv\n{T.LIB}\n.options TEMP={Tc} TNOM=25\nX_PV p 0 PV12 PARAMS: G={G} RSH=3k\nVt p 0 DC 0\n.dc Vt 5.80 6.06 0.01\n.end")
    v = s.vec("v-sweep"); i = s.vec("vt#branch"); k = np.argmin(abs(v - v0)); r = -(v[k + 1] - v[k - 1]) / (i[k + 1] - i[k - 1])
    return float(i[k]), float(r)
def loop(f, D, Vpv, IL, r_pv, gm, damp=None):
    s = 2j * np.pi * f
    Ycin = s * 21.1e-6 / (1 + s * 21.1e-6 * 0.0025)           # 2×10 µF (derated) + 1 µF + 0.1 µF ceramics, ~2.5 mΩ
    if damp: Cd, Rd = damp; Ycin = Ycin + 1 / (Rd + 1 / (s * Cd))
    Zl = L * s + R_LOOP
    Gvd = -(D * Vpv + IL * Zl) / ((Ycin + 1 / r_pv) * Zl + D ** 2)
    Gc = gm * K_DIV * (R4 + 1 / (s * C6)) / VRAMP
    return -Gvd * Gc                                          # loop gain (sign so that negative feedback = +1 crossing at −180°)
def margins(f, Tl):
    mag = np.abs(Tl); ph = np.unwrap(np.angle(Tl)) * 180 / np.pi
    out = dict(fc=None, pm=None, gm_db=None, f180=None)
    k = np.nonzero((mag[:-1] >= 1) & (mag[1:] < 1))[0]
    if len(k): i = k[-1]; out["fc"] = float(f[i]); out["pm"] = float(180 + ph[i])
    k2 = np.nonzero((ph[:-1] > -180) & (ph[1:] <= -180))[0]
    if len(k2): j = k2[0]; out["f180"] = float(f[j]); out["gm_db"] = float(-20 * np.log10(mag[j]))
    return out
f = np.logspace(1, 5.3, 4000)
cases = [(1000, 55, 0.69, 1.10), (700, 45, 0.68, 0.81), (400, 37, 0.66, 0.47), (200, 32, 0.65, 0.24), (120, 29, 0.64, 0.14), (60, 27, 0.49, 0.065)]
res = []
for damp_name, damp in (("ceramic only (before)", None), ("C15 100 µF, ESR 0.6 Ω (25 °C)", (100e-6, 0.6)), ("C15 at −10 °C (ESR ×3 = 1.8 Ω)", (100e-6, 1.8))):
    print(f"\n== {damp_name}")
    for G, Tc, D, IL in cases:
        ipv, r_pv = pv_point(G, Tc)
        row = []
        for gm in (0.05e-3, 0.2e-3, 1e-3, 5e-3, 20e-3):
            m = margins(f, loop(f, D, 5.93, IL, r_pv, gm, damp)); row.append((gm, m))
            res.append(dict(damp=damp_name, G=G, gm=gm, r_pv=r_pv, **m))
        def fmt(m):
            if m["pm"] is None: return "  no x-over"
            ok = m["pm"] > 45 and (m["gm_db"] is None or m["gm_db"] > 6)
            return f"{'✓' if ok else '✗'}PM {m['pm']:5.0f}° GM {('%4.0f dB' % m['gm_db']) if m['gm_db'] is not None else '  ∞ '}"
        print(f"G {G:4d} (r_pv {r_pv:5.1f} Ω): " + " | ".join(f"gm {g*1e3:5.2f}: {fmt(m)}" for g, m in row))
json.dump(res, open("loop_ss.json", "w"), indent=1)
