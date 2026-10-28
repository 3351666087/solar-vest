"""TB1 — PMB-H input + CN3791 MPPT buck, switching level (300 kHz), real component values from pmbh.py.
Measures: VPV regulation, battery current, inductor peak/ripple, M1/D5/L1/R losses, efficiency, MOSFET Vgs/Vds stress."""
import sys, json, numpy as np
sys.path.insert(0, "."); from ngs import NGS
LIB = open("models.lib").read()
R5 = float(sys.argv[1]) if len(sys.argv) > 1 else 200e3     # MPPT divider top: 200k / 51k (5.93 V) after the setpoint study

def netlist(G, T, vbat, tstop=4e-3, cable_len=0.5, rsh="3k"):
    rc, lc = 0.04 * cable_len, 0.6e-6 * cable_len               # 2-core 0.5 mm² pair: ~40 mΩ/m loop, ~0.6 µH/m
    return f"""charger
{LIB}
.options TEMP={T} TNOM=25 RELTOL=1e-3 ABSTOL=1e-7 VNTOL=1e-5 METHOD=gear
* ---- panel + cable + J1
X_PV pvp pvn PV12 PARAMS: G={G} RSH={rsh}
Rcab pvp j1p {rc}
Lcab j1p j1pp {lc}
Rcab2 pvn j1n {rc}
* ---- input protection: PPTC (≈0.1 Ω cold), reverse-polarity P-MOS Q1 (gate 22k to GND, 10 V zener), TVS
Rfuse j1pp pvf 0.1
XQ1 pvf q1g vpv AO3401A
R1 q1g 0 22k
D1 q1g vpv BZT52C10
D2 0 vpv SMAJ10A
* input caps: 2 x 22 µF 25 V X5R 0805 derated to ~45 % at 6 V bias, 1 µF, 100 nF (ESR 5 mΩ)
C1 vpv c1x 10u
Rc1 c1x 0 5m
C2 vpv c2x 10u
Rc2 c2x 0 5m
C3 vpv 0 1u
C4 vpv 0 100n
* C15: 100 µF 35 V aluminium electrolytic (C2836437), ESR 0.6 Ω @100 kHz — damps the input LC resonance
C15 vpv c15x 100u
Rc15 c15x 0 0.6
* ---- low-side panel current sense: RS1A 0.05 Ω always, RS1B 0.22 Ω bypassed by Q2 (ON, gate from VPV via 100k, 10 V zener)
RS1A 0 pvmid 0.05
RS1B pvmid j1n 0.22
XQ2 pvmid q2g j1n AO3400A
R2 vpv q2g 100k
D3 j1n q2g BZT52C10
D4 j1n 0 B5819W
* ---- CN3791 + MPPT divider + COM network + VG cap
XU1 vpv 0 drv csp vbatn mppt com chrgn CN3791
R5 vpv mppt {R5}
R6 mppt 0 51k
R4 com comrc 120
C6 comrc 0 220n
* ---- power stage: M1 AO3401A (S = VPV), D5 SS34, L1 22 µH (SWPA6045S, DCR 0.09 Ω), R8 0.1 Ω sense
XM1 sw drv vpv AO3401A
D5 0 sw SS34
L1 sw lx 22u
RL1 lx csp 0.09
R8 csp vbatn 0.1
C7 vbatn c7x 10u
Rc7 c7x 0 5m
C8 vbatn 0 100n
* ---- battery (Li-Po at the given OCV, 80 mΩ) + system load (ME6211 + XIAO + 6 x INA226 ≈ 8 mA)
Vbat bocv 0 DC {vbat}
Rbat vbatn bocv 0.08
Isys vbatn 0 8m
.nodeset v(vpv)=6.0 v(c15x)=6.0 v(pvp)=6.1 v(j1p)=6.1 v(j1pp)=6.1 v(pvf)=6.0 v(com)=1.0 v(mppt)=1.15 v(vbatn)={vbat} v(csp)={vbat} v(lx)={vbat} v(sw)={vbat}
.tran 10n {tstop} 0 20n
.end"""

def run(G, T, vbat, tstop=4e-3):
    s = NGS(); log = s.run(netlist(G, T, vbat, tstop))
    t = s.vec("time"); m = t > tstop * 0.6                      # steady-state window
    def w(name): return s.vec(name)[m]
    tt = t[m]; dt = np.gradient(tt)
    avg = lambda x: float(np.sum(x * dt) / np.sum(dt))
    vpv, vbatn, sw, csp, drv = w("vpv"), w("vbatn"), w("sw"), w("csp"), w("drv")
    il = (w("lx") - csp) / 0.09
    ibat = (vbatn - w("bocv")) / 0.08
    ipv = (w("pvp") - w("j1p")) / (0.04 * 0.5)
    ppv = avg(w("pvp") * ipv - w("pvn") * ipv)
    pin = avg(vpv * ipv)
    pout = avg(vbatn * (ibat + 8e-3))
    r = dict(G=G, T=T, vbat=vbat, vpv=avg(vpv), vpv_pp=float(np.ptp(vpv)), ipv=avg(ipv), ppanel=ppv, ibat=avg(ibat),
             il_pk=float(il.max()), il_pp=float(np.ptp(il)), duty=avg((vpv - drv) > 3.0),
             p_out=pout, eff=pout / pin if pin > 1e-3 else float("nan"),
             p_d5=avg(-sw * np.maximum(-sw, 0) * 0 + np.maximum(-sw, 0) * np.maximum(il, 0) * (sw < -0.05)),
             p_l1=avg(il ** 2 * 0.09), p_r8=avg(il ** 2 * 0.1) if True else 0.0,
             vgs_m1_min=float((drv - vpv).min()), vds_m1_max=float((vpv - sw).max()), sw_min=float(sw.min()), vpv_max=float(vpv.max()))
    r["p_m1"] = max(pin - pout - r["p_d5"] - r["p_l1"] - r["p_r8"] - avg(vpv * 0) , 0.0)
    return r

if __name__ == "__main__":
    cases = [(1000, 55, 3.7), (1000, 25, 3.7), (1000, 0, 3.7), (400, 37, 3.7), (120, 29, 3.7), (1000, 55, 3.0), (1000, 55, 4.15), (30, 26, 3.7)]
    out = []
    for G, T, vb in cases:
        r = run(G, T, vb); out.append(r)
        print(f"G={G:4d} T={T:3d}°C Vbat={vb:.2f} | VPV {r['vpv']:.3f} V (pp {r['vpv_pp']*1000:.0f} mV) Ipv {r['ipv']:.3f} A Ppanel {r['ppanel']:.2f} W | "
              f"Ibat {r['ibat']:.3f} A  IL pk {r['il_pk']:.2f} A pp {r['il_pp']:.2f} A  D {r['duty']:.2f} | eff {r['eff']:.1%} "
              f"| P_D5 {r['p_d5']:.3f} P_L {r['p_l1']:.3f} P_R8 {r['p_r8']:.3f} P_M1≈{r['p_m1']:.3f} W | Vgs {r['vgs_m1_min']:.1f} V Vds {r['vds_m1_max']:.1f} V")
    json.dump(out, open(f"tb_charger_R5_{int(R5/1000)}k.json", "w"), indent=1)
