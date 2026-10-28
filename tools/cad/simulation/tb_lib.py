"""TB5..TB7 — load switch + LIB hold-up, SYNC edge, 3V3 rail.
Each test prints PASS/FAIL against an explicit criterion and stores its numbers in tb_misc.json."""
import sys, json, numpy as np
sys.path.insert(0, "."); from ngs import NGS
LIB = open("models.lib").read()
RES = {}
def sim(net):
    s = NGS(); log = s.run(net)
    if "No. of Data Rows : 0" in log or "aborted" in log: print(log[-1500:]); raise RuntimeError("sim failed")
    return s
def check(name, ok, detail): RES[name] = dict(pass_=bool(ok), detail=detail); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

# ---------------------------------------------------------------- TB5 load switch + W06 cable + LIB (LM66100 + supercaps) — averaged, long time
def lib_net(t_cable_pull, t_end, load_off_at=None, rbal="100k", bit_ma=65, c10="1u", vb=3.80):
    pull = f"Scab vl_j6 vl_lib cab 0 SCAB\n.model SCAB SW (VT=0.5 VH=0.1 RON=0.09 ROFF=1G)\nVcab cab 0 PWL(0 1 {t_cable_pull} 1 {t_cable_pull + 1e-3} 0 {t_cable_pull + 60} 0 {t_cable_pull + 60.001} 1)"
    len_ = f"PWL(0 0 1 0 1.001 3.3 {load_off_at} 3.3 {load_off_at + 1e-3} 0)" if load_off_at else "PWL(0 0 1 0 1.001 3.3)"
    return f"""lib
{LIB}
.options METHOD=gear RELTOL=1e-3
Vbat bocv 0 DC {vb}
Rbat bocv vsys 0.08
RS3 vsys vlin 0.1
XQ5 vload q5g vlin AO3401A
R12 vlin q5g 100k
C10 vlin q5g {c10}
R13 q5g q6d 10k
XQ6 q6d loaden 0 AO3400A
Vlen loaden 0 {len_}
C11 vload 0 22u
D6 0 vload SMF5V0A
Rcab_j6 vload vl_j6 0.01
{pull}
* LIB
D1L 0 vl_lib SMF5V0A
C1L vl_lib 0 22u
XU1 vl_lib 0 vsc st vbit LM66100
R1L st vbit 100k
XQ1L vsc st vbit AO3401A
C3L vbit 0 22u
D2L vl_lib pre B5819W
R2L pre vsc 33
Csc1 vsc sc1x 10
Resr1 sc1x mid 0.08
Rlk1 vsc mid 70k
Csc2 mid sc2x 10
Resr2 sc2x 0 0.08
Rlk2 mid 0 70k
R3L vsc mid {rbal}
R4L mid 0 {rbal}
* BITalino Core B: {bit_ma} mA average, stops below 3.3 V (brown-out)
Bbit vbit 0 I = {bit_ma}m * (0.05 + 0.95 * 0.5 * (1 + tanh((V(vbit) - 3.3) * 200)))
Cbit vbit 0 10u
.ic v(vsc)=0 v(mid)=0 v(vbit)=0 v(vload)=0
.tran 2m {t_end} 0 50m uic
.end"""
s = sim(lib_net(t_cable_pull=700, t_end=900))
t = s.vec("time"); vbit = s.vec("vbit"); vsc = s.vec("vsc"); vload = s.vec("vload"); ib = (s.vec("bocv") - s.vec("vsys")) / 0.08
mid = s.vec("mid")
k0 = (t > 1.0) & (t < 1.2)
check("load switch soft-start inrush < 1.5 A", ib[k0].max() < 1.5, f"battery peak {ib[k0].max():.2f} A during turn-on (Q5 AO3401A rated 4 A)")
def first_cross(x, thr, tmin): k = np.nonzero((t > tmin) & (x > thr))[0]; return float(t[k[0]]) if len(k) else None
t90 = first_cross(vsc, 0.9 * 3.62, 1.0)
check("supercap precharge", t90 is not None and t90 < 600, f"VSC reaches 90 % in {t90 - 1 if t90 else float('nan'):.0f} s; precharge current start {(vload[k0].mean() - 0.2) / 33 * 1e3:.0f} mA")
k1 = t > 700.0
vb_after = vbit[k1]; tb = t[k1]
dead = tb[np.argmax(vb_after < 3.3)] - 700 if (vb_after < 3.3).any() else None
check("cable-pull hold-up ≥ 10 s (connector glitch / re-plug; Core B 65 mA, 3.3 V brown-out)", dead is None or dead > 10, f"VBIT dip at switchover {vbit[(t > 700) & (t < 700.05)].min():.3f} V; Core B runs {('%.0f s' % dead) if dead else '> 60 s (cable back first)'} on supercaps")
k2 = (t > 760.0)
check("recovery after reconnect", vbit[-1] > 3.6 and vsc[-1] > 1.0, f"VBIT {vbit[-1]:.2f} V, VSC {vsc[-1]:.2f} V at t = {t[-1]:.0f} s")
imb = float(np.max(np.abs((vsc - mid) - mid)[(t > 400) & (t < 700)]))
check("supercap balance (each ≤ 2.7 V)", max(float((vsc - mid).max()), float(mid.max())) < 2.7, f"max cell {max(float((vsc - mid).max()), float(mid.max())):.2f} V, imbalance {imb*1e3:.0f} mV")
RES["lib"] = dict(t90=t90, holdup_s=dead, vbit_min=float(vbit[(t > 700) & (t < 700.05)].min()))
np.save("tb5.npy", np.c_[t, vbit, vsc, vload, ib])

# ---------------------------------------------------------------- TB6 SYNC: XIAO GPIO -> 1k -> cable -> 1k -> BAT54S clamp -> Core B I1
s = sim(f"""sync
{LIB}
Vgpio g 0 PULSE(0 3.3 10u 5n 5n 500u 1m)
R15 g j6 1k
Ccab j6 0 70p
R5 j6 i1 1k
Dcl1 0 i1 BAT54
Dcl2 i1 vbit BAT54
Vbit vbit 0 DC {{VBIT}}
Cin i1 0 15p
Rpu i1 vbit 30k
.param VBIT=4.0
.tran 10n 1.2m
.end""".replace("{{VBIT}}", "4.0"))
t = s.vec("time"); vi = s.vec("i1")
k = (t > 10e-6) & (t < 300e-6); tr = t[k][np.argmax(vi[k] > 0.9 * 3.3)] - 10e-6 if (vi[k] > 0.9 * 3.3).any() else None
check("SYNC edge at Core B I1", tr is not None and tr < 5e-6 and vi.max() < 4.3, f"10-90 % rise ≈ {tr*1e9 if tr else float('nan'):.0f} ns, high level {vi[k].max():.2f} V (Core VIH ≈ 2 V)")

# ---------------------------------------------------------------- TB7 3V3 rail at low battery with BLE bursts
s = sim(f"""ldo
{LIB}
Vb vb 0 PWL(0 4.2 10m 4.2 60m 3.2 100m 3.2)
XU8 vb 0 v3 ME6211
C13 v3 0 1u
C14 v3 0 10u
Ixiao v3 0 PULSE(0.5m 18m 1m 1u 1u 3m 10m)
Rina v3 0 1.65k
.tran 5u 100m
.end""")
t = s.vec("time"); v3 = s.vec("v3")
check("3V3 rail ≥ 3.1 V down to VBAT 3.2 V with BLE bursts", v3[t > 1e-3].min() > 3.1, f"3V3 min {v3[t > 1e-3].min():.3f} V (nRF52840 needs ≥ 1.7 V, INA226 ≥ 2.7 V)")
json.dump(RES, open("tb_lib.json", "w"), indent=1, default=str)
