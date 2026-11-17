"""V3-G6 / SIM-08 for V3-F: IEC 61000-4-2 at the + charge contact (J15 -> VBUS_K: D13 ESD761, D14 NSR0240 40 V, VBUS C130),
and at the button node BTN (only reached if the arc punctures the TPE membrane and jumps from SW1's floating metal cover).
Generator and TVS models: sim08_esd.py (definitions part, exec'd unchanged: Heidler-fitted 150 pF / 330 Ohm generator,
TPD1E10B06 TLP table). Generator return tied to device GND (worst case for a floating band).
ESD761 (TI product page, read 2026-11-15): VRWM 24 V, VBR min 25.5 V, clamp 36.3 V typ, RDYN 0.53 typ, 1.1 pF.
  Model: no snap-back, I = (|V| - Vt) / RDYN above Vt = 36.3 - 16 x 0.53 = 27.8 V (clamp read as the 16 A TLP point, assumed);
  corners RDYN x1.5 and Vt +2 V (no max published).
NSR0240 (JLC C896422 record): VR 40 V, 200 mA, 550 nA at 25 V. Model: Schottky, BV 200 V (no breakdown) to read the raw
  reverse stress; a second run with BV 44 V shows where the avalanche current would go.
Contact - (J18) is board GND: the discharge goes straight into the ground plane (no part in series), not simulated.
Writes results/g6_esd.json."""
import json, time, pathlib
import numpy as np
HERE = pathlib.Path(__file__).resolve().parent
src = (HERE / "sim08_esd.py").read_text().split("# ------------------------------------------------------------------------------------------------ TVS validation")[0]
exec(compile(src, "sim08_esd_defs", "exec"))
t1 = time.time()
OUT = dict(generator=dict(iec_fit=[float(v) for v in PG]), cases=[])


def esd761(name, a, b, rdyn=0.53, vt=27.8):
    pts = [(0, 0), (24.0, 5e-8), (25.5, 1e-3), (vt, 0.02), (vt + rdyn * 60, 60.0), (vt + rdyn * 200, 200.0)]
    pw = ", ".join(f"{v:g}, {i:g}" for v, i in pts)
    return [f"L{name} {a} {name}t 0.4n", f"B{name} {name}t {b} I = sgn(V({name}t,{b}))*pwl(abs(V({name}t,{b})), {pw})", f"C{name} {name}t {b} 1.1p"]


def contact(vkv, kind, rdyn=0.53, vt=27.8, bv=200):
    L = ["* V3-F + contact"] + gen_lines(vkv, kind, PG if kind == "iec" else None)
    L += ["Lpin gout k 1.5n"] + esd761("X", "k", "0", rdyn, vt)
    L += [f".model DSCH D(IS=3e-7 N=1.05 RS=1.0 CJO=12p M=0.45 BV={bv} IBV=1e-4)", "Lt k ka 1n", "D14 ka vbus DSCH",
          "C130 vbus c1 0.6u", "Rc1 c1 0 10m", "R144 vbus 0 2Meg"]
    L += [".options method=gear", ".tran 0.02n 1u 0 0.02n uic", ".end"]
    S.run("\n".join(L))
    t = S.vec("time"); vk = S.vec("k"); vb = S.vec("vbus"); ix = S.vec("lx#branch"); id14 = S.vec("lt#branch")
    vrev = vb - vk
    return dict(case=f"+contact {vkv:+.0f} kV {kind} RDYN {rdyn} Vt {vt} D14 BV {bv}", esd761_ipk_A=float(np.abs(ix).max()),
                vk_peak_V=float(vk.max() if vkv > 0 else vk.min()), d14_vrev_pk_V=float(vrev.max()),
                d14_t_over_40V_ns=float(np.trapezoid((vrev > 40).astype(float), t) * 1e9), d14_irev_pk_A=float(max(0, -id14.min())),
                d14_E_rev_uJ=float(np.trapezoid(np.where(vrev > 0, np.maximum(-id14, 0) * vrev, 0), t) * 1e6),
                vbus_max_V=float(vb.max()), vbus_min_V=float(vb.min()))


def button(vkv, kind, fix=False):
    L = ["* BTN node after a membrane puncture"] + gen_lines(vkv, kind, PG if kind == "iec" else None)
    L += ["Lsw gout btn 3n", "R167 btn 0 1Meg", ".model DSW D(IS=2.5e-9 N=1.75 RS=0.6 CJO=1.5p BV=100 IBV=1e-6)", "D12B btn enh DSW",
          "C121 enh 0 4.7u"]
    if fix:
        L += tvs_lines("T", "btn", "0", tlp12) + ["Rg btn g 10k"]
    else:
        L += ["Rg btn g 1m"]
    L += ["Cgs g 0 46p", ".options method=gear", ".tran 0.02n 1u 0 0.02n uic", ".end"]
    S.run("\n".join(L))
    vg = S.vec("g"); vb = S.vec("btn")
    return dict(case=f"BTN {vkv:+.0f} kV {kind}{' FIX: TPD1E10B06 on BTN + 10k gate R' if fix else ''}", vgate_max_V=float(vg.max()), vgate_min_V=float(vg.min()),
                vbtn_max_V=float(vb.max()), vbtn_min_V=float(vb.min()))


for vkv in (8.0, -8.0):
    for rd, vt in ((0.53, 27.8), (0.80, 29.8)):
        OUT["cases"].append(contact(vkv, "iec", rd, vt))
OUT["cases"].append(contact(-8.0, "iec", 0.53, 27.8, bv=44))
for vkv in (15.0, -15.0):
    OUT["cases"].append(contact(vkv, "plain"))
for vkv in (8.0, -8.0):
    for fx in (False, True):
        OUT["cases"].append(button(vkv, "iec", fx))
for c in OUT["cases"]:
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in c.items()}, flush=True)
OUT["runtime_s"] = time.time() - t1
(HERE / "results" / "g6_esd.json").write_text(json.dumps(OUT, indent=1))
print("done %.0f s" % (time.time() - t1))
