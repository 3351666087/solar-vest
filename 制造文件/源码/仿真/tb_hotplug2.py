"""TB3b (fixed) — hot-plug a cold panel (−10 °C, 1000 W/m², Voc 8.76 V) through 5 m of cable onto empty input caps; run to steady state."""
import sys, json, numpy as np; sys.path.insert(0, "."); from ngs import NGS
LIB = open("models.lib").read()
res = {}
for load, tag in (("1k", "CN3791 not yet started"), ("6.5", "charger drawing ~1 A")):
    s = NGS(); s.run(f"""hotplug2
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
C15 vpv c15x 100u
Rc15 c15x 0 0.6
Rload vpv 0 {load}
.tran 5n 3m 0 20n
.end""")
    t = s.vec("time"); v = s.vec("vpv"); vg = s.vec("q1g"); vin = s.vec("pvp")
    r = dict(peak=float(v.max()), final=float(v[-1]), panel_open_peak=float(vin.max()), vgs_min=float((vg - v).min()), vds_q1=float((s.vec("pvf") - v).max()))
    res[tag] = r
    print(f"[{'PASS' if r['peak'] < 11.1 and r['vgs_min'] > -12 else 'FAIL'}] hot-plug ({tag}): VPV peak {r['peak']:.2f} V, settles {r['final']:.2f} V; panel side peak {r['panel_open_peak']:.2f} V; Q1 Vgs min {r['vgs_min']:.2f} V (abs max ±12 V); TVS VBR min 11.1 V, caps 25 V, CN3791 30 V")
json.dump(res, open("tb_hotplug2.json", "w"), indent=1)
