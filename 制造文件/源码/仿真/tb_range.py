"""TB4 — auto-range: Q2 OFF (indoor range, 0.52 Ω shunt) when light jumps to full sun before firmware reacts (10 ms)."""
import sys, json, numpy as np, time; sys.path.insert(0, "."); from ngs import NGS
LIB = open("models.lib").read()
t0 = time.time(); s = NGS(); log = s.run(f"""range
{LIB}
.options METHOD=gear
X_PV pvp pvn PV12 PARAMS: G=1000 RSH=3k
Vsun pvp j1p DC 0
Vret pvn j1n DC 0
Rfuse j1p vpv 0.1
C1 vpv 0 20u
Rload vpv 0 7.5
RS1A 0 pvmid 0.05
RS1B pvmid j1n 0.22
XQ2 pvmid q2g j1n AO3400A
R2 vpv q2g 100k
D3 j1n q2g BZT52C10
XQ3 q2g rlo 0 AO3400A
Vrlo rlo 0 PWL(0 3.3 10m 3.3 10.01m 0)
D4 j1n 0 B5819W
Desd 0 j1n ESD
.tran 1u 15m 0 5u
.end""")
t = s.vec("time"); vn = s.vec("j1n"); m = t < 10e-3; ipv = -s.vec("vret#branch")
idesd = float(1e-15 * (np.exp(-vn[m].min() / 0.0257) - 1))
r = dict(vmin_q2off=float(vn[m].min()), i_q2off=float(np.abs(ipv[m]).max()), vmin_q2on=float(vn[t > 11e-3].min()), idesd_uA=idesd * 1e6, p_rs1b=float(np.mean((s.vec('pvmid')[m] - vn[m]) ** 2) / 0.22))
print(f"[{'PASS' if r['vmin_q2off'] > -0.3 and r['p_rs1b'] < 0.25 else 'FAIL'}] auto-range at full sun with Q2 off: PV_IN− {r['vmin_q2off']:.3f} V (INA226 common-mode abs max −0.3 V), ESD-diode current {r['idesd_uA']:.3f} µA, RS1B dissipation {r['p_rs1b']:.2f} W; after firmware turns Q2 on: {r['vmin_q2on']:.3f} V  ({time.time()-t0:.1f} s)")
json.dump(r, open("tb_range.json", "w"), indent=1)
