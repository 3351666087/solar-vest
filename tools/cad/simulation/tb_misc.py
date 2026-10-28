"""TB2..TB7 — protection, night leakage, auto-range transient, load switch + LIB hold-up, SYNC, 3V3 rail.
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

# ---------------------------------------------------------------- TB2 night back-feed (dark panel, battery 3.7 V)
def night(pv_en_fix, rsh):
    gate = "R1 q1g 0 22k" if not pv_en_fix else "R1 q1g q8d 22k\nRpu q1g vpv 1Meg\nXQ8 q8d pven 0 AO3400A\nVpven pven 0 DC 0"
    return f"""night
{LIB}
X_PV pvp 0 PV12 PARAMS: G=0 RSH={rsh}
XQ1 pvp q1g vpv AO3401A
{gate}
D1 q1g vpv BZT52C10
D2 0 vpv SMAJ10A
R5 vpv mppt 20k
R6 mppt 0 5.1k
Rbus1 vpv 0 830k
Rbus2 vpv 0 830k
XM1 sw m1g vpv AO3401A
Rm1g m1g vpv 1k
D5 0 sw SS34
L1 sw csp 22u
R8 csp vb 0.1
Vb vb 0 DC 3.7
.op
.end"""
for fix in (False, True):
    for rsh in ("300", "3k", "30k"):
        s = sim(night(fix, rsh)); i = -s.vec("vb#branch")[0]
        RES.setdefault("night_leak_mA", {})[f"{'PV_EN' if fix else 'orig'}_Rsh{rsh}"] = float(i * 1e3)
        print(f"night: {'with PV_EN (Q1 off)' if fix else 'original design  '} Rsh={rsh:>4s}: battery drain {i*1e3:.3f} mA  -> {i*1e3*12:.1f} mAh / 12 h night")
leak = RES["night_leak_mA"]
check("night back-feed blocked by PV_EN", leak["PV_EN_Rsh300"] < 0.2, f"orig {leak['orig_Rsh300']:.2f}/{leak['orig_Rsh3k']:.2f}/{leak['orig_Rsh30k']:.2f} mA (Rsh 0.3/3/30 kΩ) -> PV_EN {leak['PV_EN_Rsh300']:.3f} mA")

# ---------------------------------------------------------------- TB3a reverse polarity (panel connected backwards, full sun)
s = sim(f"""rev
{LIB}
.options TEMP=25
X_PV pvn_rev j1p PV12 PARAMS: G=1000 RSH=3k
Vshort pvn_rev j1n DC 0
Rfuse j1p pvf 0.1
XQ1 pvf q1g vpv AO3401A
R1 q1g 0 22k
D1 q1g vpv BZT52C10
D2 0 vpv SMAJ10A
C1 vpv 0 20u
R5 vpv mppt 20k
R6 mppt 0 5.1k
RS1A 0 pvmid 0.05
RS1B pvmid j1n 0.47
XQ2 pvmid q2g j1n AO3400A
R2 vpv q2g 100k
D3 j1n q2g BZT52C10
D4 j1n 0 B5819W
Rbat vpv 0 100k
.op
.end""")
i_rev = abs(s.vec("vshort#branch")[0]); vq = s.vec("vpv")[0]
check("reverse polarity: no current, board unpowered", i_rev < 5e-3 and abs(vq) < 0.5, f"reverse current {i_rev*1e3:.2f} mA, VPV {vq:.3f} V")

# ---------------------------------------------------------------- TB3b hot-plug: cold panel (−10 °C, Voc ≈ 8.9 V) plugged through 5 m cable onto empty caps
s = sim(f"""hotplug
{LIB}
.options TEMP=-10 TNOM=25 METHOD=gear
X_PV pvp pvn PV12 PARAMS: G=1000 RSH=3k
Cpv pvp pvn 2n
Rcab pvp a 0.2
Lcab a b 3u
Sw b j1p ctl 0 SWM
.model SWM SW (VT=0.5 VH=0.1 RON=10m ROFF=100Meg)
Vctl ctl 0 PWL(0 0 10u 0 10.001u 1)
Rcab2 pvn 0 0.2
Rfuse j1p pvf 0.1
XQ1 pvf q1g vpv AO3401A
R1 q1g 0 22k
D1 q1g vpv BZT52C10
D2 0 vpv SMAJ10A
C1 vpv c1x 10u
Rc1 c1x 0 5m
C2 vpv c2x 10u
Rc2 c2x 0 5m
C3 vpv 0 1u
C4 vpv 0 100n
Rload vpv 0 1k
.tran 2n 200u 0 5n
.end""")
t = s.vec("time"); v = s.vec("vpv"); vg = s.vec("q1g")
check("hot-plug overshoot below TVS clamp / 25 V caps / CN3791 30 V", v.max() < 17.0, f"VPV peak {v.max():.2f} V (Voc cold {v[-1]:.2f} V), Q1 Vgs min {float((vg - v).min()):.2f} V (limit −12 V)")
RES["hotplug_peak_V"] = float(v.max())

# ---------------------------------------------------------------- TB4 auto-range: Q2 OFF (indoor range), light jumps to full sun before firmware reacts
s = sim(f"""range
{LIB}
.options METHOD=gear
X_PV pvp pvn PV12 PARAMS: G=1000 RSH=3k
Vsun pvp j1p DC 0
Vret pvn j1n DC 0
Rfuse j1p vpv 0.1
C1 vpv 0 20u
Rload vpv 0 7.5
RS1A 0 pvmid 0.05
RS1B pvmid j1n 0.47
XQ2 pvmid q2g j1n AO3400A
R2 vpv q2g 100k
D3 j1n q2g BZT52C10
XQ3 q2g rlo 0 AO3400A
Vrlo rlo 0 PWL(0 3.3 10m 3.3 10.01m 0)
D4 j1n 0 B5819W
Desd 0 j1n ESD
.tran 1u 15m
.end""")
t = s.vec("time"); vn = s.vec("j1n"); m = t < 10e-3
idesd = float(1e-15 * (np.exp(-vn[m].min() / 0.0257) - 1))
check("range-switch transient keeps INA226 input within ESD-safe region", vn[m].min() > -0.6 and idesd < 1e-3,
      f"PV_IN− min {vn[m].min():.3f} V while Q2 off at full sun (D4 clamps); INA226 ESD diode current ≈ {idesd*1e6:.3f} µA; after firmware turns Q2 on: {vn[~m].min():.3f} V")
RES["range_vmin_V"] = float(vn[m].min())

# ---------------------------------------------------------------- TB5 load switch + W06 cable + LIB (LM66100 + supercaps) — averaged, long time
def lib_net(t_cable_pull, t_end, load_off_at=None, rbal="100k", bit_ma=65):
    pull = f"Scab vl_j6 vl_lib cab 0 SCAB\n.model SCAB SW (VT=0.5 VH=0.1 RON=0.09 ROFF=1G)\nVcab cab 0 PWL(0 1 {t_cable_pull} 1 {t_cable_pull + 1e-3} 0 {t_cable_pull + 60} 0 {t_cable_pull + 60.001} 1)"
    len_ = f"PWL(0 0 1 0 1.001 3.3 {load_off_at} 3.3 {load_off_at + 1e-3} 0)" if load_off_at else "PWL(0 0 1 0 1.001 3.3)"
    return f"""lib
{LIB}
.options METHOD=gear RELTOL=1e-3
Vbat bocv 0 DC 3.80
Rbat bocv vsys 0.08
RS3 vsys vlin 0.1
XQ5 vload q5g vlin AO3401A
R12 vlin q5g 100k
C10 vlin q5g 100n
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
Bbit vbit 0 I = {bit_ma}m * (V(vbit) > 3.3 ? 1 : 0.05)
Cbit vbit 0 10u
.ic v(vsc)=0 v(mid)=0 v(vbit)=0 v(vload)=0
.tran 2m {t_end} 0 50m uic
.end"""
s = sim(lib_net(t_cable_pull=700, t_end=900))
t = s.vec("time"); vbit = s.vec("vbit"); vsc = s.vec("vsc"); vload = s.vec("vload"); ib = (s.vec("bocv") - s.vec("vsys")) / 0.08
mid = s.vec("mid")
k0 = (t > 1.0) & (t < 1.2)
check("load switch soft-start inrush", ib[k0].max() < 1.5, f"battery peak {ib[k0].max():.2f} A during turn-on (Q5 AO3401A rated 4 A)")
def first_cross(x, thr, tmin): k = np.nonzero((t > tmin) & (x > thr))[0]; return float(t[k[0]]) if len(k) else None
t90 = first_cross(vsc, 0.9 * 3.62, 1.0)
check("supercap precharge", t90 is not None and t90 < 600, f"VSC reaches 90 % in {t90 - 1 if t90 else float('nan'):.0f} s; precharge current start {(vload[k0].mean() - 0.2) / 33 * 1e3:.0f} mA")
k1 = t > 700.0
vb_after = vbit[k1]; tb = t[k1]
dead = tb[np.argmax(vb_after < 3.3)] - 700 if (vb_after < 3.3).any() else None
check("cable-pull hold-up (Core B 65 mA)", dead is None or dead > 30, f"VBIT dip at switchover {vbit[(t > 700) & (t < 700.05)].min():.3f} V; Core B runs {('%.0f s' % dead) if dead else '> 60 s (cable back first)'} on supercaps")
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
json.dump(RES, open("tb_misc.json", "w"), indent=1, default=str)
