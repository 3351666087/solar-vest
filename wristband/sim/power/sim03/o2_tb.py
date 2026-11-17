#!/usr/bin/env python3
"""SIM-03 (V3-G4): ngspice testbench of the V3-F PV front end with the O-2 inhibit AS BUILT (v3/design src/o2.py, SB_O2=std, 16 parts)
and src/power.py (R111, Q1, Q8 + R144/R145, Q14, R130, C101), driven by the project PV model.

PV:  node I-V of the lid (4 strips 27.7 x w mm) + radial wing (WR31) from v3/integrate/energy/v3_energy.py (read-only import), fed to
     ngspice as a B-source pwl table; light, wing ratio and string temperature per case.
BQ25570 input (behavioural, E): 'none' (Q14 drain open: the decision alone), 'cs' (cold start: VIN_DC clamped at 0.6 V, SLUSBH2G p.18),
     'mppt' (VIN_DC regulated at 0.8 x Voc), 'dd' (deep-discharged cell: three diodes from VIN_DC to the cell, 0.55 V each at 30 mA).
MOSFETs: EKV-type B-source model, n 1.5 (90 mV/decade), threshold at 250 uA = VGSth (PMZ350UPE / PMZ290UNE2 p.6: 0.45 / 0.70 / 0.95 V),
     beta from RDS(on) at 1.8 V (PMZ350 0.52-0.94 Ohm, PMZ290 0.47-0.68 Ohm); body diodes; Ciss 50 pF.
TLV7031: VOS +-8 mV, hysteresis 2-17 mV (SLVSE13J p.8), 3 us delay, POR holds OUT low below VPOR (E: 1.50 V +-25 mV hysteresis, 10 us; 1.6 V is the
     minimum specified supply, p.6), ICC 335 nA, below POR 1 uA/V (calc assumption), push-pull output 200 Ohm; U20 is supplied by U19 OUT.
NTC 10 k B 3950 K (pack). Every result here is a model result (E) unless the source is a datasheet line.
"""
import os, sys, json, math, itertools
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'common'))
sys.path.insert(0, '/path/to/SolarVest_work/wristband/v3/integrate/energy')
from ngs import NGS
import v3_energy as VE            # read-only import (no compute() call: nothing is written there)
M = VE.M
NG = NGS()
PVSET = 'LID2+WR31'

def pv_table(lux=None, sun=None, wing=None, t_pv=25.0, w=2.30, npts=70):
    old = VE.A_LID2; VE.A_LID2 = 27.7 * w / 100.0
    try:
        key = 'desk|indoor_iso' if lux is not None else 'walking|sun30'
        G = M.g_si(lux=lux) if lux is not None else M.g_si(sun=sun)
        srcs = VE.sources(PVSET, key, G, dvoc=VE.dvoc_T(t_pv), wing_ratio=wing)
        voc = M.node_voc(srcs)
        V = np.unique(np.concatenate([np.linspace(0, voc, npts), [voc + 0.05, voc + 0.15, voc + 0.4]]))
        I = np.array([float(M.node_I(v, srcs)[0]) for v in V])
    finally:
        VE.A_LID2 = old
    return V, I, voc

def pwl_expr(V, I):
    return 'pwl(V(pv),' + ','.join(f'{v:.5g},{i:.6g}' for v, i in zip(V, I)) + ')'

MODELS = """
.func sp(x) {x>30 ? x : ln(1+exp(x))}
.model DB D(IS=2e-8 N=1.05 RS=2 BV=30 IBV=1u)
.model DBODY D(IS=1e-12 N=1.2 RS=0.1)
.subckt NM d g s vth=0.70 beta=1.9
.param ut=0.02585 nn=1.5 isx={2*nn*beta*ut*ut}
B1 d s I={isx}*(sp(((V(g,s)-vth-0.08)/nn)/(2*ut))**2 - sp(((V(g,s)-vth-0.08)/nn-V(d,s))/(2*ut))**2)
Dbd s d DBODY
Cg g s 50p
Rl d s 1e10
.ends
.subckt PM d g s vth=0.70 beta=1.4
.param ut=0.02585 nn=1.5 isx={2*nn*beta*ut*ut}
B1 s d I={isx}*(sp(((V(s,g)-vth-0.08)/nn)/(2*ut))**2 - sp(((V(s,g)-vth-0.08)/nn-V(s,d))/(2*ut))**2)
Dbd d s DBODY
Cg g s 50p
Rl d s 1e10
.ends
.subckt CMP inp inn vcc out vos=0 vh=7m vpor=1.5
Bx xs 0 V=0.5*(1+tanh(((V(inp)-V(inn)+vos)+vh*(V(x)-0.5))/0.3m))
Rx xs x 1k
Cx x 0 3n
Bp ps 0 V=0.5*(1+tanh((V(vcc)-vpor+0.05*(V(por)-0.5))/1m))
Rp ps por 1k
Cp por 0 10n
Bo oi 0 V=V(vcc)*V(x)*V(por)
Vs oi o2 0
Ro o2 out 200
Bq vcc 0 I=335n*V(por)+(1-V(por))*max(V(vcc),0)/1Meg+max(I(Vs),0)
.ends
"""

def netlist(c):
    V, I, voc = c['pv']
    q14 = c.get('q14_vth', 0.70); vos = c.get('vos', (0.0, 0.0)); vh = c.get('vh', 7e-3)
    r = dict(R116=100e3, R170=732e3, R171=162e3, R172=52.3e3, r25=10e3, B=3950.0); r.update(c.get('res', {}))
    L = ['* o2 tb', MODELS, f"Bpv 0 pv I={pwl_expr(V, I)}", "Rpvl pv 0 1e9", "R111 pv pvsw 1",
         "XQ1 pvsw pvinh 0 NM vth=0.70 beta=1.9", "R108 pvinh 0 10Meg", f"Vpvinh pvinh_s 0 {c.get('pvinh', 'DC 0')}", "Rpvinh pvinh_s pvinh 1k",
         f"Vvbus vbus 0 {c.get('vbus', 'DC 0')}", "R144 vbus vbdet 1Meg", "R145 vbdet 0 1Meg", "Cvb vbdet 0 100p",
         "XQ8 pvsw vbdet 0 NM vth=0.70 beta=1.9" if not c.get('q8_open') else "* Q8 open (single fault)",
         f"XQ14 pvq o2g pvsw PM vth={q14} beta=1.4", "R174 o2g pvsw 10Meg", "C174 o2g pvsw 100n",
         "Vmeas pvq pvq2 0", "R130 pvq2 vin 12", "C101 vin 0 4.7u",
         f"Vok vbatok 0 {c.get('vbatok', 'DC 0')}", "XQ18 o2pv vbatok pvsw PM vth=0.70 beta=1.4",
         "D19A o2pv vo2 DB", f"Vntcen ntcen_s 0 {c.get('ntcen', 'DC 0')}", "Rntcen ntcen_s ntcen 100", "D19B ntcen vo2 DB", "C170 vo2 0 100n",
         f"R116 vo2 ntc {r['R116']}", f"R170 vo2 tc {r['R170']}", f"R171 tc th {r['R171']}", f"R172 th 0 {r['R172']}",
         f"Vtemp tmp 0 {c.get('temp', 'DC 25')}",
         f"Bntc ntc 0 I=V(ntc)/({r['r25']}*exp({r['B']}*(1/(V(tmp)+273.15)-1/298.15)))",
         "R149 ntc ntcadc 1Meg", "C113 ntcadc 0 10n",
         f"XU19 tc ntc vo2 o2nc CMP vos={vos[0]} vh={vh} vpor={c.get('vpor', 1.5)}", f"XU20 ntc th o2nc o2ok CMP vos={vos[1]} vh={vh} vpor={c.get('vpor', 1.5)}",
         "XQ17 o2g o2ok 0 NM vth=0.70 beta=1.9", "R175 o2ok 0 1Meg",
         f"Vchg chgdis 0 {c.get('chgdis', 'DC 0')}", "C175 chgdis o2hb 220p", "R176 o2hb 0 1Meg",
         f"XQ16 o2g o2hb 0 NM vth={c.get('q16_vth', 0.70)} beta=1.9"]
    load = c.get('load', 'none')
    if load == 'none': L.append("Rld vin 0 1e9")
    elif load == 'cs': L.append("Bcs vin 0 I=max(V(vin)-0.6,0)/20")
    elif load == 'mppt': L.append(f"Bmp vin 0 I=max(V(vin)-{0.8 * voc:.4f},0)/2")
    elif load == 'dd': L.append(f"Bdd vin 0 I=1.8e-11*(exp(min((V(vin)-{c['vcell']})/(3*0.02585),60))-1)")
    L += [".options method=gear reltol=1e-4 abstol=1e-12 vntol=1e-7 itl4=200", f".tran {c.get('tstep', '20u')} {c['tstop']} 0 {c.get('tmax', '1m')} uic", ".end"]
    return '\n'.join(L)

VECS = ['time', 'pv', 'pvsw', 'vo2', 'o2ok', 'o2nc', 'o2g', 'o2hb', 'vin', 'tmp', 'vmeas#branch']
def run(c):
    out = NG.run(netlist(c))
    try: d = {k: NG.vec(k) for k in VECS}
    except KeyError as e: raise RuntimeError('ngspice failed: ' + out[-1500:])
    d['iq14'] = d.pop('vmeas#branch'); d['vgs14'] = d['pvsw'] - d['o2g']
    return d

def edges(t, x, thr):
    s = x > thr; k = np.nonzero(s[1:] != s[:-1])[0]
    return [(float(t[i + 1]), bool(s[i + 1])) for i in k]

def tavg(t, x, t0, t1):
    m = (t >= t0) & (t <= t1)
    if m.sum() < 2: return float('nan')
    return float(np.trapezoid(x[m], t[m]) / (t[m][-1] - t[m][0]))

# ------------------------------------------------------------------------------------------------ corner selection (python, same formulas)
T0K = 298.15
def t_of(rn, r25, B): return 1 / (1 / T0K + math.log(rn / r25) / B) - 273.15
def corner_temps(f, vo2):
    R116 = 100e3 * f['R116']; R170 = 732e3 * f['R170']; R171 = 162e3 * f['R171']; R172 = 52.3e3 * f['R172']; S = R170 + R171 + R172
    vth_h = vo2 * R172 / S + f['vos_h'] - f['hh']; vth_c = vo2 * (R171 + R172) / S + f['vos_c'] + f['hh']
    out = {}
    for lab, vt in (('hot_stop', vth_h), ('cold_stop', vth_c)):
        k = vt / vo2; N = k * R116 / (1 - k); out[lab] = t_of(N, 10e3 * f['r25'], 3950 * f['B'])
    return out
def worst_corners(vo2=1.8):
    best = {}
    for c in itertools.product((0.99, 1.01), (0.99, 1.01), (0.99, 1.01), (0.99, 1.01), (0.99, 1.01), (0.99, 1.01), (-8e-3, 8e-3), (-8e-3, 8e-3), (1e-3, 8.5e-3)):
        f = dict(r25=c[0], B=c[1], R116=c[2], R170=c[3], R171=c[4], R172=c[5], vos_c=c[6], vos_h=c[7], hh=c[8])
        t = corner_temps(f, vo2)
        if 'hot' not in best or t['hot_stop'] > best['hot'][0]: best['hot'] = (t['hot_stop'], f)
        if 'cold' not in best or t['cold_stop'] < best['cold'][0]: best['cold'] = (t['cold_stop'], f)
    return best
def spice_corner(f):
    """map a python corner to the SPICE case: comparator VOS in the input sense of each comparator, total hysteresis = 2 x hh"""
    # U19 (inp = O2_TC, inn = NTC): +vos raises the effective cold threshold; U20 (inp = NTC, inn = O2_TH): +vos lowers the hot threshold
    return dict(res=dict(R116=100e3 * f['R116'], R170=732e3 * f['R170'], R171=162e3 * f['R171'], R172=52.3e3 * f['R172'], r25=10e3 * f['r25'], B=3950 * f['B']),
                vos=(f['vos_c'], -f['vos_h']), vh=2 * f['hh'])

if __name__ == '__main__':
    print(netlist(dict(pv=pv_table(lux=1000), tstop=0.01))[:300])
