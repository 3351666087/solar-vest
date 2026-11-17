"""SIM-08: IEC 61000-4-2 ±8 kV contact discharge on E1, E2, E3 and C+ (ngspice transient).

Models
  generator  'iec'        : 'plain' + a fast branch (C2-R2-L2) and series L1, fitted (Nelder-Mead) to the IEC 61000-4-2
                            Annex B ideal current into 2 Ω; meets all four Table 2 calibration points (checked below)
             'plain'      : 150 pF charged to ±8 kV, 330 Ω (as specified in the task / ARCH SIM-08) + 121 nH so the
                            current rises in the IEC 0.8 ns instead of a non-physical step (a step makes L·di/dt
                            spikes of kV in the 1 nH trace/TVS inductances – a numerical artefact)
  TVS        TPD1E10B06   : odd-symmetric I(V) table from the vendor TLP curves (SLLSEB1G p6 Fig 5-3/5-4) as a
                            ngspice B-source, 13.5 pF (Fig 5-8), package/via inductance L_tvs tuned so that the first
                            clamp spike for +8 kV matches Fig 5-1 (≈80 V); validated against the 8/20 µs clamp maxima (p5)
  ERJ-PA3 330 kΩ          : R ‖ 0.05 pF, + 0.5 nH
  ADS1291 pin             : 2 pF routing, 1 nH bond/lead, pad with ESD diodes to AVDD/AVSS and 3 pF, then the internal
                            EMI RC (SBAS502C p19: -3 dB ≈ 3 MHz; modelled 2.65 kΩ + 17 pF so the pin still shows 20 pF, E)
  RLDOUT                  : amplifier output 100 Ω to 1.5 V, ESD diodes
  C+ path                 : TVS D2 -> BAS116 D1 (forward junction with TT 0.8 µs + separate 85 V breakdown branch) -> PV node (10 nF cell capacitance, E)
                            -> RSH1 1 Ω -> VIN_DC with CIN 4.7 µF (DC-bias derated to 50 %)
Return path: the generator return is tied to the device ground (worst case for a floating band).
Criteria: AFE pin within abs max (SBAS502C p6), TVS within its IEC rating (±30 kV, SLLSEB1G p4), energy and voltage
in each ERJ-PA3 inside what Panasonic characterised (3 kV / 150 pF / 150 Ω, < 1 % drift, datasheet p4).
Writes results/sim08_iec.json and plots/sim08_iec_*.png (names differ from the interrupted run's sim08.json/sim08_*.png).
"""
import json, math, time, sys, pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import minimize
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
from ngs import NGS          # noqa: E402
from params import P         # noqa: E402

V = lambda k: P[k]["value"]
S = NGS()
t0 = time.time()
R = {"model_version": "heidler-fit generator, EMI-RC pin model, 121 nH plain generator, BAS116 breakdown branch without TT, Gear, BAS21 and BAS21+bead variants"}
(HERE / "plots").mkdir(exist_ok=True)

# ------------------------------------------------------------------------------------------------ TVS model
tlp12, tlp21 = V("tvs_tlp_12"), V("tvs_tlp_21")


def tvs_table(tlp):
    """I(V) points for V >= 0: leakage spec (100 nA at 5 V), DC breakdown ≥ 6 V at 1 mA (p5), knee to the TLP curve,
    linear extrapolation beyond the last TLP point with the last TLP slope"""
    v0 = tlp[0][0]
    pts = [(0.0, 0.0), (5.0, 1e-7), (6.0, 1e-6), (v0 - 0.4, 1e-3), (v0, 0.05)]
    pts += [(v, i) for v, i in tlp[1:]]
    (v1, i1), (v2, i2) = tlp[-2], tlp[-1]
    s = (i2 - i1) / (v2 - v1)
    pts.append((v2 + 30, i2 + 30 * s))
    return pts


def tvs_lines(name, a, b, tlp, ctvs=None, ltvs=None):
    tab = tvs_table(tlp)
    pw = ", ".join(f"{v:g}, {i:g}" for v, i in tab)
    ltvs = V("l_tvs") if ltvs is None else ltvs
    return [f"L{name} {a} {name}t {ltvs}",
            f"B{name} {name}t {b} I = sgn(V({name}t,{b}))*pwl(abs(V({name}t,{b})), {pw})",
            f"C{name} {name}t {b} {V('c_tvs') if ctvs is None else ctvs}"]


# ------------------------------------------------------------------------------------------------ generator
def gen_lines(vkv, kind, p=None):
    v = vkv * 1e3
    L = [f"C1g g1 0 150p IC={v}", "R1g g1 g1r 330"]
    if kind == "plain":     # 150 pF / 330 Ω with a series L giving the IEC 0.8 ns 10-90 % rise (tr = 2.2 L/R)
        L.append(f"L1g g1r gout {0.8e-9 * 332 / 2.2}")
    else:
        c2, r2, l2, l1 = p
        L += [f"L1g g1r gout {l1}", f"C2g g2 0 {c2} IC={v}", f"R2g g2 g2r {r2}", f"L2g g2r gout {l2}"]
    return L


def calib_measure(kind, p=None, vkv=8.0):
    net = ["* IEC generator into 2 ohm"] + gen_lines(vkv, kind, p) + ["Rt gout 0 2", ".tran 0.01n 150n 0 0.01n uic", ".end"]
    S.run("\n".join(net))
    t = S.vec("time"); i = S.vec("gout") / 2.0
    ipk = i.max(); k10 = np.argmax(i >= 0.1 * ipk); k90 = np.argmax(i >= 0.9 * ipk)
    tr = t[k90] - t[k10]
    t10 = t[k10]
    return dict(ipk=float(ipk), tr=float(tr), i30=float(np.interp(t10 + 30e-9, t, i)),
                i60=float(np.interp(t10 + 60e-9, t, i))), t, i


cal = V("iec_cal_8kv")


def heidler(t, vkv=8.0):
    """IEC 61000-4-2:2008 Annex B ideal contact-discharge current (sum of two Heidler functions), scaled from 4 kV.
    Constants from memory of the standard (E); they reproduce the Table 2 calibration points (30 A, 0.81 ns, 16.0 A at
    30 ns, 8.0 A at 60 ns at 8 kV) and carry 1.14 µC ≈ 150 pF × 8 kV, which is the self-consistency check."""
    s = abs(vkv) / 4.0
    t1, t2, t3, t4, i1, i2, n = 1.1e-9, 2e-9, 12e-9, 37e-9, 16.6 * s, 9.3 * s, 1.8
    k1 = math.exp(-t1 / t2 * (n * t2 / t1) ** (1 / n)); k2 = math.exp(-t3 / t4 * (n * t4 / t3) ** (1 / n))
    return (i1 / k1 * (t / t1) ** n / (1 + (t / t1) ** n) * np.exp(-t / t2) +
            i2 / k2 * (t / t3) ** n / (1 + (t / t3) ** n) * np.exp(-t / t4))


TG = np.linspace(0, 100e-9, 2001); HG = heidler(TG); WG = np.where(TG < 10e-9, 4.0, 1.0)


def cost(x):
    """weighted rms distance (fraction of 30 A) between the circuit's current into 2 Ω and the IEC ideal waveform.
    (A fit to the four calibration points alone, as in the interrupted run, converged on a ringing 0.36 pF branch.)"""
    m, t, i = calib_measure("iec", [10 ** v for v in x])
    return float(np.sqrt(np.mean(WG * (np.interp(TG, t, i) - HG) ** 2)) / 30.0)


# start point = converged result of a 2-start Nelder-Mead from (7 pF, 300 Ω, 100 nH, 2 µH) and (4 pF, 250 Ω, 60 nH,
# 1.5 µH), both of which ended at the same point (rms error 3.6 %)
x0 = [math.log10(8.98e-12), math.log10(211.0), math.log10(1.94e-7), math.log10(2.75e-6)]
opt = minimize(cost, x0, method="Nelder-Mead", options=dict(maxiter=60, xatol=1e-3, fatol=1e-7))
PG = [10 ** v for v in opt.x]
m_iec, t_iec, i_iec = calib_measure("iec", PG)
m_pl, t_pl, i_pl = calib_measure("plain")
tol = dict(ipk=0.15, tr=0.25, i30=0.30, i60=0.30)
R["generator"] = dict(
    iec_fit=dict(C2=PG[0], R2=PG[1], L2=PG[2], L1=PG[3], measured=m_iec, rms_err_vs_ideal=float(opt.fun),
                 within_iec_tolerance={k: bool(abs(m_iec[k] / cal[k] - 1) <= tol[k]) for k in tol}),
    plain=dict(measured=m_pl, within_iec_tolerance={k: bool(abs(m_pl[k] / cal[k] - 1) <= tol[k]) for k in tol}),
    targets=cal, tolerances=tol)
print("generator iec fit", {k: round(v, 3) if isinstance(v, float) else v for k, v in m_iec.items()}, "params", [f"{v:.3g}" for v in PG])
print("generator plain  ", {k: round(v, 3) for k, v in m_pl.items()})
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.plot(t_iec * 1e9, i_iec, label="calibrated (150 pF/330 Ω + fast branch)")
ax.plot(t_pl * 1e9, i_pl, label="plain 150 pF / 330 Ω (+121 nH)")
ax.plot(TG * 1e9, HG, "k--", lw=0.8, label="IEC ideal waveform (Annex B)")
for tt, ii in ((30, 16), (60, 8)): ax.errorbar(tt + 0.0, ii, yerr=0.3 * ii, fmt="ko", ms=3, capsize=3)
ax.errorbar(1.0, 30, yerr=4.5, fmt="ks", ms=3, capsize=3)
ax.set_xlabel("ns"); ax.set_ylabel("A into 2 Ω"); ax.legend(fontsize=8); ax.set_title("+8 kV contact generator vs IEC 61000-4-2 calibration points")
fig.tight_layout(); fig.savefig(HERE / "plots" / "sim08_iec_generator.png", dpi=110); plt.close(fig)

# ------------------------------------------------------------------------------------------------ TVS validation
def tvs_alone(vkv, ltvs, tlp, kind="iec"):
    net = ["* gen into TVS"] + gen_lines(vkv, kind, PG) + [f"Ltr gout pad {V('l_trace')}"] + tvs_lines("X", "pad", "0", tlp, ltvs=ltvs)
    net += [".tran 0.01n 300n 0 0.02n uic", ".end"]
    S.run("\n".join(net))
    return S.vec("time"), S.vec("pad")


# tune L_tvs so the +8 kV first spike at the pad equals Fig 5-1 (80 V)
best = None
for lt in np.linspace(0.2e-9, 4e-9, 39):
    t, v = tvs_alone(8, lt, tlp12)
    err = abs(v.max() - V("tvs_clamp_8kv")["peak"])
    if best is None or err < best[0]: best = (err, lt)
LTVS = float(best[1])
t, v = tvs_alone(8, LTVS, tlp12)
val = dict(L_tvs=LTVS, peak=float(v.max()), v30ns=float(np.interp(30e-9, t, v)), v100ns=float(np.interp(100e-9, t, v)),
           fig51=V("tvs_clamp_8kv"))
# 8/20 µs check of the static curve against the datasheet maxima (10 V at 1 A, 14 V at 5 A)
tab = tvs_table(tlp21)
vv = np.array([p[0] for p in tab]); ii = np.array([p[1] for p in tab])
val["vclamp_1A"] = float(np.interp(1.0, ii, vv)); val["vclamp_5A"] = float(np.interp(5.0, ii, vv))
val["vclamp_ok"] = bool(val["vclamp_1A"] <= 10.0 and val["vclamp_5A"] <= 14.0)
R["tvs_validation"] = val
print("TVS validation", {k: (round(x, 3) if isinstance(x, float) else x) for k, x in val.items()})
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.plot(t * 1e9, v, label=f"model, L_tvs {LTVS*1e9:.1f} nH")
ax.plot([1, 30, 100], [80, 15, 11], "ks", label="SLLSEB1G Fig 5-1 (read)")
ax.set_xlim(-5, 225); ax.set_xlabel("ns"); ax.set_ylabel("V at TVS"); ax.legend(); ax.set_title("+8 kV contact clamp: model vs datasheet")
fig.tight_layout(); fig.savefig(HERE / "plots" / "sim08_iec_tvs_validation.png", dpi=110); plt.close(fig)

# ------------------------------------------------------------------------------------------------ circuits
RP = V("r_prot")


def chain(i, pad, pinnode):
    return [f"Lra{i} {pad} ra{i} 0.5n", f"Rra{i} ra{i} m{i} {RP}", f"Cra{i} ra{i} m{i} {V('c_par_0603')}",
            f"Lrb{i} m{i} rb{i} 0.5n", f"Rrb{i} rb{i} {pinnode} {RP}", f"Crb{i} rb{i} {pinnode} {V('c_par_0603')}"]


COMMON = [".model DESD D(IS=1e-15 N=1 RS=5)", "Vavdd avdd 0 DC 3.0", "Vmid mid 0 DC 1.5",
          # BAS116: forward junction with charge storage, and its reverse breakdown as a separate branch without
          # charge storage (ngspice applies TT to the breakdown current too, which produced a self-sustaining
          # 30 A 'forward' current at 60 V reverse bias in the C+ -8 kV case – a model artefact)
          ".model DBAS D(IS=1.0e-12 N=1.69 RS=0.8 CJO=2p TT=0.8u)",
          ".model DBASBK D(IS=1e-14 N=1 RS=1)",
          # BAS21 (proposed D1, same SOT-23 pinning): VF ≤ 1 V at 100 mA / 1.25 V at 200 mA, Cd 5 pF, trr 50 ns, VRRM 250 V
          ".model DB21 D(IS=2e-9 N=1.9 RS=1.5 CJO=5p TT=50n)"]


def electrode_net(which, vkv, kind, tvs=True, tlp=None, d1="BAS116"):
    tlp = tlp or (tlp12 if vkv > 0 else tlp21)
    L = ["* ESD on " + which] + gen_lines(vkv, kind, PG) + COMMON + [f"Ltr gout pad {V('l_trace')}"]
    if tvs:
        L += tvs_lines("X", "pad", "0", tlp, ltvs=LTVS)
    if which in ("E1", "E3"):
        L += chain(1, "pad", "pin") + ["Crt pin 0 2p", "Lbw pin pinint 1n", "Cpad pinint 0 3p",
                                       "Vdu pinint du DC 0", "Du du avdd DESD", "Vdd dd pinint DC 0", "Dd 0 dd DESD",
                                       "Remi pinint core 2.65k", "Ccore core 0 17p", "Rin core mid 500Meg",
                                       ".ic v(pin)=1.5 v(pinint)=1.5 v(core)=1.5 v(m1)=1.5 v(pad)=1.5"]
    elif which == "E2":
        L += chain(1, "pad", "pin") + ["Crt pin 0 2p", "Lbw pin pinint 1n", "Cpad pinint 0 3p",
                                       "Vdu pinint du DC 0", "Du du avdd DESD", "Vdd dd pinint DC 0", "Dd 0 dd DESD",
                                       "Ro pinint core 100", "Vamp core 0 DC 1.5",
                                       ".ic v(pin)=1.5 v(pinint)=1.5 v(m1)=1.5 v(pad)=1.5"]
    elif which == "C+":
        cin = V("cin_vin") * V("mlcc_dcbias")
        if "FB" in d1:          # ferrite bead between the C+ pad (TVS node) and D1
            fb, k_ = V("fb_model"), (0.75 if d1.endswith("-25%") else 1.0)
            L += [f"Rbd pad bd1 {V('fb_c_plus')['rdc']}", f"Lbd bd1 bd2 {fb['l'] * k_}", f"Rbp bd1 bd2 {fb['r'] * k_}",
                  f"Cbp bd1 bd2 {fb['c']}"]
            a1 = "bd2"
        else:
            a1 = "pad"
        L += [f"Ld1a {a1} d1a 2n", ("D1 d1a d1k DBAS" if d1.startswith("BAS116") else "D1 d1a d1k DB21"),
              f"Vbk1 d1k bk1 DC {84.3 if d1.startswith('BAS116') else 249.3}", "Dbk1 bk1 d1a DBASBK", "Ld1k d1k pv 2n", "Cpv pv 0 10n", "Rsh pv vin 1.0",
              "Lcin vin cinx 0.5n", f"Cin cinx 0 {cin}", "Rload vin 0 100k", ".ic v(pv)=2.0 v(vin)=2.0 v(cinx)=2.0 v(pad)=0"]
    return L


def run_case(which, vkv, kind, tvs=True, tstop=None, tlp=None, d1="BAS116"):
    # 1 µs = 20 generator time constants (330 Ω × 150 pF): the event is over. Gear integration: with the trapezoidal
    # rule the C+ -8 kV case (TVS knee + BAS116 charge storage + 2.75 µH generator L) stalls with ever-smaller steps.
    tstop = tstop or (1e-6 if tvs else 1.5e-3)
    tstep = 0.02e-9 if tvs else 20e-9
    net = electrode_net(which, vkv, kind, tvs, tlp, d1) + [".options method=gear",
                                                       f".tran {tstep} {tstop} 0 {tstep if tvs else 1e-6} uic", ".end"]
    S.run("\n".join(net))
    t = S.vec("time")
    g = lambda n: S.vec(n)
    out = dict(case=f"{which} {vkv:+.0f} kV {kind}{'' if tvs else ' TVS OPEN'}{'' if d1 == 'BAS116' else ' D1=' + d1}")
    i_gen = -S.vec("c1g#branch") if False else None
    if tvs:
        vt = g("xt"); itvs = S.vec("lx#branch")
        out["tvs_ipk_A"] = float(np.max(np.abs(itvs)))
        out["tvs_vpk_V"] = float(np.max(np.abs(vt)))
        out["tvs_E_uJ"] = float(np.trapezoid(np.abs(vt * itvs), t) * 1e6)
        out["pad_vpk_V"] = float(np.max(np.abs(g("pad"))))
    if which in ("E1", "E2", "E3"):
        va = g("ra1") - g("m1"); vb = g("rb1") - g("pin")
        out["Ra_vpk_V"] = float(np.max(np.abs(va))); out["Rb_vpk_V"] = float(np.max(np.abs(vb)))
        out["Ra_E_uJ"] = float(np.trapezoid(va ** 2 / RP, t) * 1e6); out["Rb_E_uJ"] = float(np.trapezoid(vb ** 2 / RP, t) * 1e6)
        out["Ra_Ppk_W"] = float(np.max(va ** 2 / RP))
        vpin = g("pinint")
        out["pin_vmax_V"] = float(vpin.max()); out["pin_vmin_V"] = float(vpin.min())
        if which != "E2":
            vc = g("core"); out["core_vmax_V"] = float(vc.max()); out["core_vmin_V"] = float(vc.min())
        iu = S.vec("lbw#branch")
        out["pin_ipk_mA"] = float(np.max(np.abs(iu)) * 1e3)          # includes displacement current into 22 pF
        out["pin_q_nC"] = float(np.trapezoid(np.abs(iu), t) * 1e9)
        # current actually conducted by the pin's ESD diodes (what stresses the silicon)
        idio = np.abs(S.vec("vdu#branch")) + np.abs(S.vec("vdd#branch"))
        out["diode_ipk_mA"] = float(idio.max() * 1e3)
        out["diode_q_nC"] = float(np.trapezoid(idio, t) * 1e9)
        tu = np.arange(0, t[-1], 0.1e-9); iu_ = np.interp(tu, t, idio); w = int(100e-9 / 0.1e-9)
        out["diode_i100ns_mA"] = float(np.convolve(iu_, np.ones(w) / w, mode="valid").max() * 1e3) if len(iu_) > w else float(iu_.mean() * 1e3)
    if which == "C+":
        iD = S.vec("ld1a#branch")
        out["D1_ipk_A"] = float(np.max(np.abs(iD))); out["D1_I2t_A2s"] = float(np.trapezoid(iD ** 2, t))
        vr = g("d1k") - g("d1a")
        out["D1_vrev_pk_V"] = float(vr.max())
        over = vr > V("bas116" if d1.startswith("BAS116") else "bas21")["vrrm"]
        out["D1_t_over_vrrm_ns"] = float(np.trapezoid(over.astype(float), t) * 1e9)
        # energy the diode absorbs while reverse-biased (avalanche + junction charging), J
        out["D1_E_rev_nJ"] = float(np.trapezoid(np.where(vr > 0, np.maximum(-iD, 0) * vr, 0), t) * 1e9)
        out["vin_dc_max_V"] = float(g("vin").max()); out["pv_max_V"] = float(g("pv").max())
        out["pv_min_V"] = float(g("pv").min())
        out["ina_vdiff_pk_V"] = float(np.max(np.abs(g("pv") - g("vin"))))     # across RSH1 = INA236 #1 IN+/IN-
    return out, t, S


RES = []
for which in ("E1", "E2", "E3", "C+"):
    for vkv in (8.0, -8.0):
        for kind in ("iec", "plain"):
            o, t, _ = run_case(which, vkv, kind)
            RES.append(o)
            print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in o.items()}, flush=True)
# informational: ±15 kV air-like (plain 150 pF/330 Ω, no fast branch)
for which in ("E1", "C+"):
    o, t, _ = run_case(which, 15.0, "plain"); o["case"] += " (air-like, info)"; RES.append(o)
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in o.items()}, flush=True)
# design change for C+: D1 = BAS21 (250 V) instead of BAS116 (85 V), same footprint and pinning, alone and with a
# 600 Ω ferrite bead (BLM15AX601SN1D) between the TVS node and D1 (nominal and -25 % impedance); BAS116 + bead too
for d1v, vkv, kind in [(d, v, k) for d in ("BAS116+FB", "BAS21", "BAS21+FB", "BAS21+FB-25%") for v in (8.0, -8.0) for k in ("iec", "plain")]:
        o, t, _ = run_case("C+", vkv, kind, d1=d1v)
        RES.append(o)
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in o.items()}, flush=True)
# fault: TVS open on E1
o_open, t_open, _ = run_case("E1", 8.0, "plain", tvs=False)
RES.append(o_open)
print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in o_open.items()}, flush=True)

# ------------------------------------------------------------------------------------------------ criteria
esd = V("erj_pa3_esd")
E_vendor = 0.5 * esd["c"] * esd["v"] ** 2 * RP / (RP + esd["r"])      # energy into a 330 kΩ sample in the vendor test
crit = []
for o in RES:
    row = dict(case=o["case"], info=bool("TVS OPEN" in o["case"] or "info" in o["case"]))
    if "pin_vmax_V" in o:
        # SBAS502C p6: analog input AVSS-0.3…AVDD+0.3 V, input current ±100 mA momentary / ±10 mA continuous,
        # HBM ±1000 V (100 pF / 1.5 kΩ: 0.67 A peak, 100 nC). The pin passes if its pad stays inside the voltage limits,
        # or if the current its ESD diodes conduct stays inside the momentary limit (100 ns average) AND inside the
        # peak current and charge of the 1 kV HBM event the pin is rated for.
        row["pin_within_rails"] = bool(o["pin_vmax_V"] <= 3.3 and o["pin_vmin_V"] >= -0.3)
        row["diode_vs_hbm_q"] = o["diode_q_nC"] / 100.0
        row["diode_vs_hbm_ipk"] = o["diode_ipk_mA"] / 667.0
        row["diode_vs_momentary"] = o["diode_i100ns_mA"] / 100.0
        row["pin_ok"] = row["pin_within_rails"] or bool(row["diode_vs_hbm_q"] < 1 and row["diode_vs_hbm_ipk"] < 1
                                                        and row["diode_vs_momentary"] < 1)
        if "core_vmax_V" in o:
            row["core_within_rails"] = bool(o["core_vmax_V"] <= 3.3 and o["core_vmin_V"] >= -0.3)
        row["erj_E_ratio"] = max(o["Ra_E_uJ"], o["Rb_E_uJ"]) / (E_vendor * 1e6)
        row["erj_V_ratio"] = max(o["Ra_vpk_V"], o["Rb_vpk_V"]) / esd["v"]
        # also against the continuous-rating limits (ERJ-PA3 p2: limiting element 150 V, max overload 200 V for 5 s),
        # which a ns spike may exceed without harm; reported because it is the stricter, datasheet-printed number
        row["erj_V_vs_overload200"] = max(o["Ra_vpk_V"], o["Rb_vpk_V"]) / V("erj_pa3")["v_ovl"]
        row["erj_E_vs_overload_5s"] = max(o["Ra_E_uJ"], o["Rb_E_uJ"]) * 1e-6 / (V("erj_pa3")["v_ovl"] ** 2 / RP * 5.0)
        row["erj_ok"] = bool(row["erj_E_ratio"] < 1 and row["erj_V_ratio"] < 1)
    if "D1_ipk_A" in o:
        bas = V("bas21") if "D1=BAS21" in o["case"] else V("bas116")       # covers the +FB variants
        row["D1_I2t_ratio"] = o["D1_I2t_A2s"] / (bas["ifsm_1us"] ** 2 * 1e-6)
        row["D1_vrev_ok"] = bool(o["D1_vrev_pk_V"] < bas["vrrm"])
        row["D1_t_over_vrrm_ns"] = o["D1_t_over_vrrm_ns"]; row["D1_E_rev_nJ"] = o["D1_E_rev_nJ"]
        row["vin_ok"] = bool(o["vin_dc_max_V"] <= 5.5)
        # INA236 SBOSA81D p4: IN+/IN- common mode GND-0.3…50 V, differential ±26 V
        row["inaok"] = bool(o["pv_max_V"] <= 50 and o["pv_min_V"] >= -0.3 and o["ina_vdiff_pk_V"] <= 26)
    row["tvs_ok"] = bool(abs(float(o["case"].split()[1])) <= V("tvs_iec") / 1e3) if "TVS OPEN" not in o["case"] else None
    crit.append(row)
R.update(results=RES, criteria=crit, erj_vendor_test_energy_uJ=E_vendor * 1e6,
         notes=dict(E_vendor="0.5·150 pF·(3 kV)²·R/(R+150 Ω): energy dissipated in a 330 kΩ sample during Panasonic's "
                             "ESD characterisation (datasheet p4), < 1 % resistance change",
                    return_path="generator return tied to device ground (worst case for a floating band)",
                    pin_abs_max="SBAS502C p6: AVSS-0.3…AVDD+0.3 V, ±10 mA continuous, ±100 mA momentary"))
for c in crit:
    print(c)

# plot one representative case
o, t, s = run_case("E1", 8.0, "iec")
fig, ax = plt.subplots(3, 1, figsize=(8, 7), sharex=True)
ax[0].plot(t * 1e9, s.vec("pad")); ax[0].set_ylabel("pad (TVS) V")
ax[1].plot(t * 1e9, s.vec("ra1") - s.vec("m1"), label="first 330 kΩ"); ax[1].plot(t * 1e9, s.vec("rb1") - s.vec("pin"), label="second 330 kΩ")
ax[1].set_ylabel("V across R"); ax[1].legend()
ax[2].plot(t * 1e9, s.vec("pinint"), label="pin pad"); ax[2].plot(t * 1e9, s.vec("core"), label="behind EMI RC")
ax[2].set_ylabel("ADS1291 IN1P V"); ax[2].set_xlabel("ns"); ax[2].legend()
ax[0].set_xlim(-5, 600); fig.suptitle("SIM-08: +8 kV contact on E1 (IEC-calibrated generator)")
fig.tight_layout(); fig.savefig(HERE / "plots" / "sim08_iec_E1_8kV.png", dpi=110); plt.close(fig)

(HERE / "results" / "sim08_iec.json").write_text(json.dumps(R, indent=1, default=float))
print(f"done {time.time()-t0:.0f} s")
