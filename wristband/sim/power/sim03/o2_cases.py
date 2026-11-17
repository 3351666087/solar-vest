#!/usr/bin/env python3
"""SIM-03 O-2 cases on o2_tb.py (ngspice). usage: python -B o2_cases.py [part]   part = window | matrix | dyn | coldstart | all
Writes o2_<part>.json. Every number is a model result (E)."""
import sys, os, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import o2_tb as T

def rnd(x, n=3): return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), n)
def after(t, x, t0): m = t >= t0; return x[m]

PART = sys.argv[1] if len(sys.argv) > 1 else 'all'
R = {}

# ------------------------------------------------------------------------------------------------ A. window at the corners
if PART in ('window', 'all'):
    ramp = 'PWL(0 -15 2 55 4 -15)'
    out = {}
    for llab, kw in (('600 lx (V_O2 near the POR edge)', dict(lux=600)), ('0.1 sun', dict(sun=0.1)), ('1.2 sun', dict(sun=1.2))):
        pv = T.pv_table(**kw)
        d0 = T.run(dict(pv=pv, tstop=0.05, load='none')); vo2 = float(d0['vo2'][-1])
        wc = T.worst_corners(max(vo2, 1.45))
        for clab, cc in (('nominal', {}), ('worst hot corner', T.spice_corner(wc['hot'][1])), ('worst cold corner', T.spice_corner(wc['cold'][1]))):
            for vpor in (1.5,):
                c = dict(pv=pv, tstop=4.0, load='none', temp=ramp, tmax='0.5m'); c.update(cc)
                d = T.run(c); t = d['time']
                e = T.edges(t, d['o2ok'] / np.maximum(d['vo2'], 1e-3), 0.5)
                ev = [(rnd(np.interp(te, t, d['tmp']), 2), 'approve' if up else 'stop', 'rising T' if te < 2 else 'falling T') for te, up in e]
                hot = [x[0] for x in ev if x[1] == 'stop' and x[2] == 'rising T']; cold = [x[0] for x in ev if x[1] == 'stop' and x[2] == 'falling T']
                out[f'{llab} | {clab}'] = dict(V_O2=rnd(vo2), edges=ev, hot_stop_C=hot[:1], cold_stop_C=cold[-1:],
                                               python_corner_C=(rnd(wc['hot'][0], 2) if 'hot' in clab else rnd(wc['cold'][0], 2) if 'cold' in clab else None),
                                               n_edges=len(ev))
                print(llab, clab, out[f'{llab} | {clab}'])
    # python corners below the 1.6 V specified supply (POR edge assumption 1.40-1.60 V)
    pc = {}
    for v in (1.40, 1.50, 1.60, 1.75, 2.0, 2.6):
        hot = max(T.corner_temps(f, v)['hot_stop'] for f in [T.worst_corners(v)['hot'][1]]); cold = T.worst_corners(v)['cold'][0]
        pc[f'{v:.2f} V'] = dict(hot_stop_max_C=rnd(hot, 2), cold_stop_min_C=rnd(cold, 2))
    out['python corners vs V_O2 (every corner: NTC R25, B, 4 resistors +-1 %, VOS +-8 mV, hysteresis 2-17 mV)'] = pc
    print(pc); R['window'] = out

# ------------------------------------------------------------------------------------------------ B. MCU off: out-of-window temperatures, every cell state
if PART in ('matrix', 'all'):
    out = {}
    loads = [('cold start (cell 0-1.6 V, VSTOR < 1.73 V)', dict(load='cs'))] + \
            [(f'deep-discharged cell {v:g} V (three diodes)', dict(load='dd', vcell=v)) for v in (0.0, 0.5, 1.2, 2.0)] + \
            [('PCM tripped, cell 2.5 V + body diode', dict(load='dd', vcell=3.1))]
    for tc in (-10.0, 50.0, 25.0):
        for llab, kw in (('0.1 sun', dict(sun=0.1)), ('1.2 sun', dict(sun=1.2)), ('1000 lx', dict(lux=1000))):
            pv = T.pv_table(t_pv=tc, **kw)
            for ld, lkw in loads:
                if tc == 25.0 and llab != '1.2 sun': continue
                c = dict(pv=pv, tstop=0.6, temp=f'DC {tc}', q14_vth=0.45); c.update(lkw)
                d = T.run(c); t = d['time']; i = after(t, d['iq14'], 0.005)
                out[f'{tc:g} C | {llab} | {ld}'] = dict(iq14_max_uA=rnd(i.max() * 1e6, 4), iq14_mean_uA=rnd(T.tavg(t, d['iq14'], 0.1, 0.6) * 1e6, 4),
                                                       V_O2_max=rnd(d['vo2'].max()), c_rate_70mAh=rnd(T.tavg(t, d['iq14'], 0.1, 0.6) * 1e3 / 70.0, 3))
                print(tc, llab, ld, out[f'{tc:g} C | {llab} | {ld}'])
    R['matrix'] = out

# ------------------------------------------------------------------------------------------------ dynamic cases
if PART in ('dyn', 'all'):
    out = {}
    pv1 = T.pv_table(sun=1.0); pv12 = T.pv_table(sun=1.2)
    HB = 'PULSE(0 1.8 0.05 1u 1u 10u 0.1 10)'          # 10 us at 10 Hz, 10 pulses (0.05-0.95 s), then the firmware stops
    # heartbeat override: VBAT_OK high, MPPT load, 1 sun
    for q14 in (0.45, 0.95):
        for q16 in (0.45, 0.95):
            d = T.run(dict(pv=pv1, tstop=3.5, load='mppt', vbatok='DC 3.3', chgdis=HB, q14_vth=q14, q16_vth=q16, tmax='0.2m'))
            t = d['time']; i = d['iq14']; ion = float(np.median(i[(t > 0.3) & (t < 0.9)]))
            k1 = (t > 0.05) & (t < 0.0505)
            last = 0.95; m = (t > last) & (i < 0.1 * ion); t_rel = float(t[m][0] - last) if m.any() else None
            between = (t > 0.15) & (t < 0.95)
            out[f'heartbeat | Q14 Vth {q14} | Q16 Vth {q16}'] = dict(
                o2hb_first_pulse_peak_V=rnd(d['o2hb'][k1].max()), vgs14_first_pulse_V=rnd(d['vgs14'][(t > 0.05) & (t < 0.06)].max()),
                vgs14_min_between_pulses_V=rnd(d['vgs14'][between].min()), iq14_on_mA=rnd(ion * 1e3), release_after_last_pulse_s=rnd(t_rel),
                iq14_before_first_pulse_uA=rnd(d['iq14'][t < 0.049].max() * 1e6, 4))
            print('HB', q14, q16, out[f'heartbeat | Q14 Vth {q14} | Q16 Vth {q16}'])
    for lab, kw in (('static CHG_DIS high from 0.05 s (MCU halted with the pin high)', dict(chgdis='PWL(0 0 0.05 0 0.050001 1.8)')),
                    ('no heartbeat, VBAT_OK high (MCU in reset / off at a healthy cell)', dict())):
        d = T.run(dict(pv=pv1, tstop=3.0, load='mppt', vbatok='DC 3.3', q14_vth=0.45, tmax='0.5m', **kw)); t = d['time']; i = d['iq14']
        on = t[i > 1e-3]
        out[lab] = dict(iq14_max_mA=rnd(i.max() * 1e3), on_from_s=rnd(on[0]) if len(on) else None, on_until_s=rnd(on[-1]) if len(on) else None)
        print(lab, out[lab])
    # PV_INH probe with the MCU running (heartbeat continuous), Q1 on for 20 ms at 0.5 s
    HBc = 'PULSE(0 1.8 0.05 1u 1u 10u 0.1)'
    d = T.run(dict(pv=pv1, tstop=1.2, load='mppt', vbatok='DC 3.3', chgdis=HBc, pvinh='PWL(0 0 0.5 0 0.5001 1.8 0.52 1.8 0.5201 0)', q14_vth=0.95, tmax='0.1m'))
    t = d['time']; i = d['iq14']; ion = float(np.median(i[(t > 0.3) & (t < 0.49)]))
    pr = (t > 0.505) & (t < 0.519)
    isc = float(T.np.interp(0.0, pv1[0], pv1[1]))
    i_r111 = (d['pv'] - d['pvsw']) / 1.0
    rec = (t > 0.52) & (i > 0.9 * ion)
    out['PV_INH probe (MCU on, 1 sun, Q14 Vth 0.95)'] = dict(iq14_during_probe_uA=rnd(np.abs(i[pr]).max() * 1e6, 3), pvsw_during_probe_mV=rnd(d['pvsw'][pr].max() * 1e3, 3),
        INA_PV_over_Isc=rnd(float(np.median(i_r111[pr])) / isc, 4), recovery_to_90pct_ms=rnd((t[rec][0] - 0.52) * 1e3, 2) if rec.any() else None,
        o2g_min_during_probe_V=rnd(d['o2g'][pr].min()))
    print('probe', out['PV_INH probe (MCU on, 1 sun, Q14 Vth 0.95)'])
    # Q1 shorts the PV with the MCU off (fault: PV_INH high) and Q1 toggled at 10 Hz: no oscillation
    for lab, pvinh in (('Q1 static on from 0.5 s', 'PWL(0 0 0.5 0 0.5001 1.8)'), ('Q1 toggled 10 Hz from 0.5 s', 'PULSE(0 1.8 0.5 1u 1u 50m 100m)')):
        d = T.run(dict(pv=pv12, tstop=2.0, load='cs', pvinh=pvinh, q14_vth=0.45, tmax='0.5m')); t = d['time']
        e_after = [x for x in T.edges(t, d['o2ok'], 0.8) if x[0] > 0.6]
        out[f'MCU off, 1.2 sun | {lab}'] = dict(o2ok_edges_after_short=len(e_after) if 'static' in lab else len(e_after),
                                               iq14_max_after_0p6s_uA=rnd(after(t, d['iq14'], 0.6).max() * 1e6, 3) if 'static' in lab else None,
                                               edges_per_Q1_cycle=rnd(len(e_after) / 14.0, 2) if 'toggled' in lab else None)
        print(lab, out[f'MCU off, 1.2 sun | {lab}'])
    # Q8 at plug-in under full sun, and the Q8 single fault
    VB = 'PWL(0 0 0.5 0 0.5005 5)'
    for lab, kw in (('MCU on (heartbeat), 1.2 sun', dict(vbatok='DC 3.3', chgdis=HBc, load='mppt')),
                    ('MCU off, flat cell 3.0 V (VBAT_OK low), 1.2 sun', dict(load='mppt')),
                    ('Q8 OPEN (single fault), MCU off, flat cell, 1.2 sun', dict(load='mppt', q8_open=True)),
                    ('Q8 OPEN (single fault), MCU on, Q1 backup 5 ms after VBUS, 1.2 sun', dict(load='mppt', q8_open=True, vbatok='DC 3.3', chgdis=HBc,
                                                                                               pvinh='PWL(0 0 0.505 0 0.5051 1.8)'))):
        d = T.run(dict(pv=pv12, tstop=3.0, vbus=VB, q14_vth=0.45, tmax='0.5m', **kw)); t = d['time']; i = d['iq14']
        ion = float(np.median(i[(t > 0.3) & (t < 0.49)])); m = (t > 0.5) & (i < 0.01 * max(ion, 1e-9))
        out[f'Q8 | {lab}'] = dict(iq14_before_mA=rnd(ion * 1e3), iq14_after_mean_mA=rnd(T.tavg(t, i, 0.6, 3.0) * 1e3, 4),
                                  t_to_1pct_ms=rnd((t[m][0] - 0.5) * 1e3, 2) if m.any() else None,
                                  i_shorted_PV_mA=rnd(float(np.median(((d['pv'] - d['pvsw']) / 1.0)[t > 0.6])) * 1e3, 2))
        print('Q8', lab, out[f'Q8 | {lab}'])
    # dark load (battery-side sources of the O-2: VBAT_OK gate drive, NTC_EN)
    pv0 = (np.array([0.0, 1.0, 5.0]), np.array([0.0, -1e-9, -1e-6]), 0.0)
    for vok in (0.0, 3.3):
        d = T.run(dict(pv=pv0, tstop=1.0, load='none', vbatok=f'DC {vok}', tmax='5m'))
        out[f'dark | VBAT_OK {vok} V'] = dict(vo2_V=rnd(d['vo2'][-1], 6), pvsw_V=rnd(d['pvsw'][-1], 6))
    R['dyn'] = out

# ------------------------------------------------------------------------------------------------ C. cold start through the O-2 (MCU off, dead band), per wing ratio
if PART in ('coldstart', 'all'):
    out = {}
    def ok(lux, wing, q14=0.95, w=2.30):
        d = T.run(dict(pv=T.pv_table(lux=lux, wing=wing, w=w), tstop=2.0, load='cs', q14_vth=q14, tmax='1m'))
        return T.tavg(d['time'], d['iq14'], 0.5, 2.0)
    for wing in (1.0, 0.5, 0.25, 0.1, 0.0):
        for w in (2.30, 2.80):
            i200 = ok(200, wing, w=w)
            lo, hi = 100.0, 6000.0
            if ok(hi, wing, w=w) < 21.4e-6: lux = None
            else:
                for _ in range(9):
                    m = math.sqrt(lo * hi)
                    if ok(m, wing, w=w) >= 21.4e-6: hi = m
                    else: lo = m
                lux = round(hi, -1)
            out[f'wing {wing:g} x lid | strips {w:.2f} mm'] = dict(i_cold_start_200lx_uA=rnd(i200 * 1e6, 2), lux_for_21p4uA_through_O2=lux)
            print(wing, w, out[f'wing {wing:g} x lid | strips {w:.2f} mm'])
    for lux in (200, 500, 711, 1000):
        for q14 in (0.45, 0.95):
            out[f'Q14 Vth {q14} | {lux} lx | wing 1'] = dict(i_avg_uA=rnd(ok(lux, 1.0, q14) * 1e6, 2))
    # reference without the O-2 (BASELINE 11.5 convention: current at 0.70 V)
    ref = {}
    for w in (2.30, 2.80):
        old = T.VE.A_LID2; T.VE.A_LID2 = 27.7 * w / 100.0
        for wing in (1.0, 0.5, 0.25, 0.1, 0.0):
            ref[f'wing {wing:g} | strips {w:.2f} mm'] = dict(i_200lx_uA=rnd(T.VE.cs_at(T.PVSET, 200, wing) * 1e6, 1), lux_needed=T.VE.lux_for_cold_start(T.PVSET, wing))
        T.VE.A_LID2 = old
    out['reference without the O-2 (v3_energy cs_at at 0.70 V)'] = ref; print(ref)
    R['coldstart'] = out

json.dump(R, open(os.path.join(HERE, f'o2_{PART}.json'), 'w'), indent=1)
