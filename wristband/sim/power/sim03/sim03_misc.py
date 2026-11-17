#!/usr/bin/env python3
"""SIM-03 (V3-G4) remaining cases for the V3-F netlist (v3/design src/power.py, charger.py, hmi.py; values CALC_V3F.md).
ngspice (KiCad libngspice): (g) EN / ship mode / wake pair, haptic droop at VBAT 3.60 V (averaged PWM model), reversed head (-5 V, D14).
Python on the project PV model (v3_energy, read-only): R_LIM 12 ohm + Q14 charge bound at -10 / -20 C, deep-discharge currents, the
Q8 single fault (PV + USB at once), VBAT_OK chatter margin. All results are model estimates (E). Writes misc_results.json."""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'common')); sys.path.insert(0, '/path/to/SolarVest_work/wristband/v3/integrate/energy')
from ngs import NGS
import v3_energy as VE
NG = NGS(); R = {}
def rnd(x, n=3): return None if x is None else round(float(x), n)
def run(net, vecs):
    o = NG.run(net)
    try: return {k: NG.vec(k) for k in vecs}
    except KeyError: raise RuntimeError(o[-1500:])
def t_cross(t, x, thr):
    k = np.nonzero(x >= thr)[0]; return float(t[k[0]]) if len(k) else None

# ------------------------------------------------------------------------------------------------ (g) EN, ship mode, wake pair
DM = ".model DBAV D(IS=4e-14 N=1 RS=5 CJO=1.5p BV=100)"
en = {}
for lab, src in (('head VBUS 5.0 V', 'vbus 0 PWL(0 0 0.01 0 0.0101 5.0)'), ('head VBUS 4.75 V (minimum at the band)', 'vbus 0 PWL(0 0 0.01 0 0.0101 4.75)')):
    d = run(f"en\n{DM}\nV1 {src}\nR144 vbus vbdet 1Meg\nR145 vbdet 0 1Meg\nD12A vbdet enh DBAV\nC121 enh 0 4.7u\nR126 enh 0 3.3Meg\n"
            ".tran 1m 8 0 5m uic\n.end", ['time', 'enh'])
    tc = t_cross(d['time'], d['enh'], 1.0)
    en[lab] = dict(t_to_EN_HOLD_1V_s=rnd(tc - 0.01) if tc else None, EN_HOLD_final_V=rnd(d['enh'][-1]))
for vb in (2.8, 3.0, 3.3, 3.7, 4.1):
    d = run(f"btn\n{DM}\nV1 vb 0 {vb}\nSW vb bs ctl 0 SWM\nVc ctl 0 PWL(0 0 0.01 0 0.0101 1 0.31 1 0.3101 0)\n.model SWM SW(VT=0.5 RON=0.5 ROFF=1e12)\n"
            "R165 bs btn 100k\nR167 btn 0 1Meg\nD12B btn enh DBAV\nC121 enh 0 4.7u\nR126 enh 0 3.3Meg\n.tran 1m 2 0 2m uic\n.end", ['time', 'enh'])
    tc = t_cross(d['time'], d['enh'], 1.0)
    en[f'button at VBAT {vb} V (press 0.30 s)'] = dict(t_to_1V_s=rnd(tc - 0.01) if tc else None, EN_HOLD_at_release_V=rnd(np.interp(0.31, d['time'], d['enh'])),
                                                      wakes_within_0p3s=bool(tc is not None and tc - 0.01 <= 0.30))
# wake by light through R126 (PV node, open circuit): time to 1.0 V
sys.path.insert(0, HERE); import o2_tb as T
for lux in (100, 200, 300):
    voc = T.pv_table(lux=lux)[2]
    en[f'light wake {lux} lx (PV node {voc:.2f} V through R126 3.3 M)'] = dict(t_to_1V_s=rnd(-15.51 * math.log(1 - 1.0 / voc), 1) if voc > 1.0 else None)
en['ship mode leakage'] = 'D12 unbiased (both anodes at 0 V through R145 / R167, cathode at EN_HOLD 0 V): 0 A; Q12 IDSS bound 3.7 uW counted in SIM-05 (CALC_V3F 7, 9)'
R['EN_ship_wake'] = en; print('EN', en)

# ------------------------------------------------------------------------------------------------ haptic droop at VBAT 3.60 V
# averaged model: OCV 3.60 V -> R_path -> VBAT_IC (C106 22 uF x 0.4) -> motor (duty D x VBAT_IC into 37.5 ohm + back-EMF (Cm || Rm),
# 30 mA at 3.0 V average running, mechanical tau ~ 30 ms, CALC_V3F 4.2); PV support = charge current into VBAT_IC; system load 1 mA.
hap = {}
for rlab, rp in (('typical path 1.40 ohm', 1.40), ('maximum path 2.25 ohm (25 C)', 2.25), ('0 C cell 3.75 ohm', 3.75)):
    for slab, mode in (('step to 3.0 V average (no soft start)', 'step'), ('30 ms PWM soft start', 'ramp'),
                       ('firmware rule CALC_V3F 4.3 (ramp while I_bat <= 40 mA and VBAT_IC - I x 1 ohm >= 3.50 V)', 'fw')):
        for plab, ipv in (('no PV', 0.0), ('PV 0.1 sun', 2.2e-3), ('PV 0.45 sun', 9.2e-3)):
            v0 = 3.60 - (1e-3 - ipv) * rp
            if mode == 'step': dn = "Bd dd 0 V=3.0/max(V(vb),2)"
            elif mode == 'ramp': dn = "Bd dd 0 V=min(time/30m,1)*3.0/max(V(vb),2)"
            else: dn = ("Bc 0 dn I=((V(vb)-I(Vb0)*1>=3.50)&&(I(Vb0)<=0.040)) ? 33.3 : -100\nCd dn 0 1 IC=0\nRd dn 0 1e9\n"
                        "Bd dd 0 V=min(max(V(dn),0),3.0/max(V(vb),2))\nBlim 0 dn I=V(dn)>3.0/max(V(vb),2) ? -(V(dn)-3.0/max(V(vb),2))*1e3 : (V(dn)<0 ? -V(dn)*1e3 : 0)")
            net = (f"hap\nVo oc 0 3.60\nVb0 oc ob 0\nRp ob vb {rp}\nC106 vb 0 8.8u IC={v0}\nIsys vb 0 1m\nIpv 0 vb {ipv}\n{dn}\n"
                   f"Bm mi 0 V=V(dd)*V(vb)\nVm mi m1 0\nRc m1 emf 37.5\nCm emf 0 1.3m IC=0\nRm emf 0 62.5\n"
                   f"Bb vb 0 I=V(dd)*I(Vm)\n.tran 0.1m 0.4 0 0.1m uic\n.end")
            d = run(net, ['time', 'vb', 'vm#branch', 'vb0#branch', 'dd', 'emf'])
            vmin = float(d['vb'][d['time'] > 1e-4].min()) - 0.014          # PWM ripple bound 14 mV (CALC_V3F 4.4)
            vavg_max = float((d['dd'] * d['vb']).max())
            hap[f'{rlab} | {slab} | {plab}'] = dict(VBAT_IC_min_incl_ripple_V=rnd(vmin), margin_to_VBAT_OK_fall_max_3p441_mV=rnd((vmin - 3.441) * 1e3, 0),
                                                   battery_peak_mA=rnd(d['vb0#branch'].max() * 1e3, 1), motor_avg_V_max=rnd(vavg_max, 2),
                                                   starts_E=bool(vavg_max >= 2.3), back_emf_end_V=rnd(d['emf'][-1], 2))
R['haptic'] = hap
for k, v in hap.items(): print('HAP', k, v)

# ------------------------------------------------------------------------------------------------ reversed head (-5 V on the contacts)
DN = ".model DNSR D(IS=3e-7 N=1.0 RS=0.5 CJO=40p BV=45 IBV=1u)\n.model DESDB D(IS=1e-14 BV=26 IBV=1m CJO=1p)\n.model DIN D(IS=1e-14 N=1 CJO=5p)"
rev = {}
for lab, v in (('reversed head -5 V (stiff, 0.5 ohm)', -5.0), ('correct head +5 V (reference)', 5.0), ('reversed head -5.5 V', -5.5)):
    net = (f"rev\n{DN}\nVh hp 0 PWL(0 0 1u 0 2u {v})\nRs hp vbk 0.5\nD13a vbk x DESDB\nD13b 0 x DESDB\nD14 vbk vbus DNSR\nC130 vbus 0 1u\n"
           "R144 vbus vbdet 1Meg\nR145 vbdet 0 1Meg\nDin 0 vbus DIN\nRin vbus 0 2Meg\nIchg vbus 0 PWL(0 0 1 0)\n.tran 0.1u 20m 0 10u\n.end")
    d = run(net, ['time', 'vbus', 'vbk', 'vh#branch'])
    rev[lab] = dict(VBUS_min_V=rnd(d['vbus'].min(), 4), VBUS_end_V=rnd(d['vbus'][-1], 4), contact_current_end_uA=rnd(-d['vh#branch'][-1] * 1e6, 3),
                    contact_current_peak_mA=rnd(np.abs(d['vh#branch']).max() * 1e3, 3))
rev['note'] = 'U15 IN absolute minimum -0.3 V (SLUSDJ8A p.4); D14 NSR0240 VR 40 V, IR <= 0.55 uA at 25 V (p.2); ESD761 VRWM +-24 V (SLVSH10C)'
R['reversed_head'] = rev; print('REV', rev)

# ------------------------------------------------------------------------------------------------ R_LIM bound, deep discharge, Q8 single fault
def with_strip(w, f):
    old = VE.A_LID2; VE.A_LID2 = 27.7 * w / 100.0
    try: return f()
    finally: VE.A_LID2 = old
RQ_LO = 12.0 * 0.99 + 0.33                    # R130 -1 % + Q14 RDS(on) min (PMZ350UPE p.6): the lowest series R
cb = {}
for w in (2.30, 2.50, 2.80):
    for tc in (-10.0, -20.0, 0.0, 25.0):
        G = 1.0 if tc == 25.0 else 1.2
        for k in (0.80, 0.72):
            r = with_strip(w, lambda: VE.charge_point(VE.sources('LID2+WR31', 'walking|sun30', G, dvoc=VE.dvoc_T(tc), wing_ratio=1.0), RQ_LO, 3.0, k))
            cb[f'strips {w:.2f} mm | {G:g} sun strings {tc:g} C | k {k}'] = dict(i_bat_mA=rnd(r['i_bat_inst_mA'], 2), C_70=rnd(r['i_bat_inst_mA'] / 70, 3), C_66=rnd(r['i_bat_inst_mA'] / 66, 3))
R['charge_bound_R12_plus_Q14'] = cb
dd = {}
for w in (2.30, 2.80):
    for lab, G, tc in (('1 sun 25 C', 1.0, 25.0), ('1.2 sun 0 C (O-2 window edge)', 1.2, 0.0), ('1.2 sun -10 C (only with the MCU running and the O-2 bypassed: not reachable)', 1.2, -10.0)):
        srcs = with_strip(w, lambda: VE.sources('LID2+WR31', 'walking|sun30', G, dvoc=VE.dvoc_T(tc), wing_ratio=1.0))
        for vc in (0.0, 0.5, 1.0, 1.2):
            i = with_strip(w, lambda: VE.series_i(srcs, vc + 1.65, 1.0 + RQ_LO))
            dd[f'strips {w:.2f} mm | {lab} | cell {vc:g} V'] = dict(i_mA=rnd(i * 1e3, 1), C_70=rnd(i * 1e3 / 70, 2))
R['deep_discharge'] = dd
usb_max = 330.0 / (10.2 * 0.995 * 0.993)        # mA, CALC_V3F G1 L0: 32.75 mA
q8 = {}
for w in (2.30, 2.80):
    for tc in (0.0, 25.0, 45.0):
        r = with_strip(w, lambda: VE.charge_point(VE.sources('LID2+WR31', 'walking|sun30', 1.2, dvoc=VE.dvoc_T(tc), wing_ratio=1.0), RQ_LO, 3.0, 0.80))
        q8[f'strips {w:.2f} mm | 1.2 sun strings {tc:g} C | Q8 open, MCU off (cell 3.0-3.40 V, VBAT_OK low): PV + USB'] = dict(
            pv_mA=rnd(r['i_bat_inst_mA'], 2), usb_mA=rnd(usb_max, 2), C_70=rnd((r['i_bat_inst_mA'] + usb_max) / 70, 3), C_66=rnd((r['i_bat_inst_mA'] + usb_max) / 66, 3))
R['q8_single_fault'] = q8
# VBAT_OK chatter margin: hysteresis 3.403 - 3.312 = 91 mV against the VSTOR step when the PV charge stops (VSTOR-to-cell path R)
ch = {}
for w in (2.30, 2.80):
    for G, tc in ((1.0, 25.0), (1.2, 0.0)):
        r = with_strip(w, lambda: VE.charge_point(VE.sources('LID2+WR31', 'walking|sun30', G, dvoc=VE.dvoc_T(tc), wing_ratio=1.0), RQ_LO, 3.4, 0.80))
        for rlab, rp in (('VSTOR path typical 2.90 ohm', 2.90), ('VSTOR path max 25 C 3.75 ohm', 3.75), ('VSTOR path 0 C cell 5.25 ohm', 5.25)):
            step = r['i_bat_inst_mA'] * rp
            ch[f'strips {w:.2f} | {G:g} sun {tc:g} C | {rlab}'] = dict(i_mA=rnd(r['i_bat_inst_mA'], 1), step_mV=rnd(step, 0), hysteresis_mV=91, chatter_possible=bool(step >= 91))
R['vbat_ok_chatter'] = ch
for k in ('charge_bound_R12_plus_Q14', 'deep_discharge', 'q8_single_fault', 'vbat_ok_chatter'):
    for kk, v in R[k].items(): print(k, kk, v)
json.dump(R, open(os.path.join(HERE, 'misc_results.json'), 'w'), indent=1)
