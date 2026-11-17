"""Stage-2b ECO re-check of SIM-08 (copy of g6_esd.py with the real ECO parts; g6_esd.py and results/g6_esd.json stay as "before").
+ contact J15 -> VBUS_K: D13 ESD761, D14 PMEG10020AELR (100 V), D16 NSR0240 clamp GND -> VBUS, C130, R144+R145; R509 100 k / R510 1 M / Q20 gate.
- contact J18 -> GND_K: D15 ESD761 (as ruled, E-2) to GND, Q20 PMZ290UNE2 off (drain GND_K, source GND): body diode + Coss + avalanche branch.
  Alternative run: TPD1E10B06 instead of the ESD761 on J18 (the ESD761 clamps above Q20's VDS 20 V).
Button: TPD1E10B06 on BTN at SW1 + R511 10 k into the Q13 gate (fix of ECG.md 5d) with the real TLP table (tlp12).
PMEG10020AELR (datasheet 1 Jan 2023, read 2026-11-15): V(BR)R >= 100 V at 1 mA; VF 470 mV at 0.1 A, 580 mV at 0.5 A, 650 mV at 1 A (typ);
  Cd 135 / 80 / 50 pF at 1 / 4 / 10 V. Model: IS / N / RS fitted to the typ VF points, CJO 220 p VJ 0.5 M 0.5 (127 / 82 / 48 pF), BV 100 V (min).
PMZ290UNE2 (pin map C478155.yaml): VDS 20 V, VGS +-8 V, Ciss 46 pF; Crss / Coss not in the pin map: Coss 8 pF, Cgd 5 pF assumed (E);
  avalanche branch at 24 V (no rating published: the stress is reported as the current into it).
Writes results/eco/g6_esd_eco.json."""
# ===== stage-2c copy (LEAD_NOTES 2g F-8): Q20 = CJBA7002K (JSCJ, C504101) 60 V N-FET, D15 TPD1E10B06 on J18 as built. Only the J18 cases.
# CJBA7002K Rev 1.0 (read 2026-11-15): V(BR)DSS >= 60 V, VGS +-20 V, Ciss 41 / Coss 3.6 / Crss 2.9 pF typ (80 / 7 / 5.6 max), VSD 0.84 V at 300 mA,
# IDSS <= 100 nA at 60 V. No avalanche rating. Model: Coss 7 p (max), Cgd 5.6 p (max), Cgs 41 p, avalanche branch at VAV (60 V = the minimum
# breakdown, and 70 V as a typical-breakdown sensitivity), 2 Ohm. Writes results/s2c/g6_esd_s2c.json.
# ===== (was) mini-ECO copy (LEAD_NOTES 2f F-1): D15 on J18 = TPD1E10B06 as built; only the J18 cases are run. Writes results/mini/g6_esd_mini.json.
import json, time, pathlib, math
import numpy as np
from scipy.optimize import least_squares
HERE = pathlib.Path(__file__).resolve().parent
src = (HERE / "sim08_esd.py").read_text().split("# ------------------------------------------------------------------------------------------------ TVS validation")[0]
exec(compile(src, "sim08_esd_defs", "exec"))
t1 = time.time()
(HERE / "results" / "s2c").mkdir(parents=True, exist_ok=True)
OUT = dict(generator=dict(iec_fit=[float(v) for v in PG]), cases=[])

# PMEG10020AELR DC fit (typ, 25 C)
VT = 0.02569; PTS = [(0.1, 0.470), (0.5, 0.580), (1.0, 0.650)]
def res(x):
    lis, n, rs = x
    return [math.log(i / math.exp(lis)) * n * VT + i * rs - v for i, v in PTS]
fit = least_squares(res, [math.log(1e-6), 1.1, 0.05], bounds=([math.log(1e-12), 0.9, 0.0], [math.log(1e-3), 2.0, 1.0])).x
IS, N, RS = math.exp(fit[0]), fit[1], fit[2]
VF33 = N * VT * math.log(0.033 / IS) + 0.033 * RS
OUT["pmeg_fit"] = dict(IS=IS, N=N, RS=RS, VF_33mA_typ_25C_V=VF33)
DMOD = f".model DPMEG D(IS={IS:g} N={N:g} RS={RS:g} CJO=220p VJ=0.5 M=0.5 BV=100 IBV=1e-3)"


def esd761(name, a, b, rdyn=0.53, vt=27.8):
    pts = [(0, 0), (24.0, 5e-8), (25.5, 1e-3), (vt, 0.02), (vt + rdyn * 60, 60.0), (vt + rdyn * 200, 200.0)]
    pw = ", ".join(f"{v:g}, {i:g}" for v, i in pts)
    return [f"L{name} {a} {name}t 0.4n", f"B{name} {name}t {b} I = sgn(V({name}t,{b}))*pwl(abs(V({name}t,{b})), {pw})", f"C{name} {name}t {b} 1.1p"]


def contact_plus(vkv, kind, rdyn=0.53, vt=27.8):
    L = ["* + contact, ECO"] + gen_lines(vkv, kind, PG if kind == "iec" else None)
    L += ["Lpin gout k 1.5n"] + esd761("X", "k", "0", rdyn, vt)
    L += [DMOD, ".model DNSR D(IS=3e-7 N=1.05 RS=1.0 CJO=12p M=0.45 BV=44 IBV=1e-4)", "Lt k ka 1n", "D14 ka vbus DPMEG",
          "D16 0 vbus DNSR", "C130 vbus c1 0.6u", "Rc1 c1 0 10m", "R144 vbus 0 2Meg",
          "R509 k g 100k", "R510 g 0 1Meg", "Cgs g 0 41p", "Cgd g gk 5p", "Rgk gk 0 1Meg"]
    L += [".options method=gear", ".tran 0.02n 1u 0 0.02n uic", ".end"]
    S.run("\n".join(L))
    t = S.vec("time"); vk = S.vec("k"); vb = S.vec("vbus"); ix = S.vec("lx#branch"); id14 = S.vec("lt#branch"); vg = S.vec("g")
    vrev = vb - vk
    return dict(case=f"+contact {vkv:+.0f} kV {kind} RDYN {rdyn} Vt {vt} D14 PMEG10020AELR (BV 100)", esd761_ipk_A=float(np.abs(ix).max()),
                vk_peak_V=float(vk.max() if vkv > 0 else vk.min()), d14_vrev_pk_V=float(vrev.max()),
                d14_t_over_100V_ns=float(np.trapezoid((vrev > 100).astype(float), t) * 1e9), d14_irev_pk_A=float(max(0, -id14.min())),
                vbus_max_V=float(vb.max()), vbus_min_V=float(vb.min()), q20_gate_max_V=float(vg.max()), q20_gate_min_V=float(vg.min()))


VAV = 60.0
def contact_gnd(vkv, kind, tvs="ESD761", rdyn=0.53, vt=27.8):
    L = ["* - contact J18 -> GND_K, ECO"] + gen_lines(vkv, kind, PG if kind == "iec" else None)
    L += ["Lpin gout gk 1.5n"]
    L += esd761("X", "gk", "0", rdyn, vt) if tvs == "ESD761" else tvs_lines("X", "gk", "0", tlp12)
    # Q20 off: body diode source(0) -> drain(gk), Coss, avalanche drain -> source above 24 V, gate network
    L += [".model DBODY D(IS=1e-12 N=1.0 RS=0.3 CJO=7p M=0.4)", "Dbody 0 gk DBODY",
          f"Bav gk 0 I = V(gk) > {VAV} ? (V(gk) - {VAV}) / 2.0 : 0",
          "Cgd gk g 5.6p", "Cgs g 0 41p", "R510 g 0 1Meg", "R509 g 0 100k"]
    L += [".options method=gear", ".tran 0.02n 1u 0 0.02n uic", ".end"]
    S.run("\n".join(L))
    t = S.vec("time"); vd = S.vec("gk"); vg = S.vec("g"); ix = S.vec("lx#branch")
    iav = np.where(vd > VAV, (vd - VAV) / 2.0, 0.0)
    return dict(case=f"GND contact {vkv:+.0f} kV {kind} {tvs} on J18, Q20 CJBA7002K off, avalanche at {VAV:.0f} V", tvs_ipk_A=float(np.abs(ix).max()),
                q20_vds_max_V=float(vd.max()), q20_vds_min_V=float(vd.min()), q20_t_over_20V_ns=float(np.trapezoid((vd > 20).astype(float), t) * 1e9), q20_t_over_60V_ns=float(np.trapezoid((vd > 60).astype(float), t) * 1e9),
                q20_vgs_max_V=float((vg).max()), q20_vgs_min_V=float((vg).min()),
                q20_avalanche_ipk_A=float(iav.max()), q20_avalanche_E_uJ=float(np.trapezoid(iav * vd, t) * 1e6),
                q20_gate_max_V=float(vg.max()), q20_gate_min_V=float(vg.min()))


def button(vkv, kind):
    L = ["* BTN node after a membrane puncture, ECO: D18 TPD1E10B06 + R511 10 k"] + gen_lines(vkv, kind, PG if kind == "iec" else None)
    L += ["Lsw gout btn 3n", "R167 btn 0 1Meg", ".model DSW D(IS=2.5e-9 N=1.75 RS=0.6 CJO=1.5p BV=100 IBV=1e-6)", "D12B btn enh DSW", "C121 enh 0 4.7u"]
    L += tvs_lines("T", "btn", "0", tlp12) + ["Rg btn g 10k", "Cgs g 0 46p", ".options method=gear", ".tran 0.02n 1u 0 0.02n uic", ".end"]
    S.run("\n".join(L))
    vg = S.vec("g"); vb = S.vec("btn"); it = S.vec("lt#branch")
    return dict(case=f"BTN {vkv:+.0f} kV {kind} ECO (D18 TPD1E10B06 + R511 10 k)", vgate_max_V=float(vg.max()), vgate_min_V=float(vg.min()),
                vbtn_max_V=float(vb.max()), vbtn_min_V=float(vb.min()), d18_ipk_A=float(np.abs(it).max()))


for VAV in (60.0, 70.0):
    for vkv in (8.0, -8.0):
        OUT["cases"].append(contact_gnd(vkv, "iec", "TPD1E10B06"))
    for vkv in (15.0, -15.0):
        OUT["cases"].append(contact_gnd(vkv, "plain", "TPD1E10B06"))
print(OUT["pmeg_fit"])
for c in OUT["cases"]:
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in c.items()}, flush=True)
OUT["runtime_s"] = time.time() - t1
(HERE / "results" / "s2c" / "g6_esd_s2c.json").write_text(json.dumps(OUT, indent=1))
print("done %.0f s" % (time.time() - t1))
