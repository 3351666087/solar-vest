#!/usr/bin/env python3
"""SIM-05 (V3-G5) for the V3-F netlist (variant v3f), 2026-11-15.
Model: the project's SIM-05 energy model as used for BASELINE 11 (copy sim05/baseline_calc_v3f.py -> v3_calc_copy.py ->
v3/integrate/energy/v3_energy.py, read-only import), run with the final v3f loads (v3/design/calc/v3f_calc.json -> standby).
Columns: lid 41 x 32 (4 strips 27.7 x 2.30 mm) and lid 41 x 34 (4 strips 27.7 x 2.80 mm, +21.6 % lid silicon, LEAD_NOTES 2a).
Cases: T1-T7, worn weeks W1-W7 from 50 % SoC, sleeve (wing at 0.25 of the lid) and dark wing (0), office downlights, edge-dominated shunt.
Usage: SIM05_MODE=typ|bounds python3 -B run_sim05.py   -> sim05_<mode>.json
"""
import os, sys, json, math, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import baseline_calc_v3f as B          # computes BASE in the mode of SIM05_MODE
VE = B.VE; M = VE.M
MODE = B.FINAL['mode']
V3F = B.V3F; PV = B.PVSET; RL = 12.0
COLS = {'41x32 strips 2.30 mm': 2.30, '41x34 strips 2.80 mm': 2.80}

def tables_kw(w, tag, **kw):
    """posture tables (VE.table method) with extra source options (wing_ratio, rsh_lid, rsh_wing); cached in this folder"""
    path = os.path.join(HERE, f'pv_tables_R12_w{int(round(w * 100))}_{tag}.json')
    sig = hashlib.sha1(json.dumps([PV, RL, w, VE.LUX_GRID, VE.SUN_GRID, VE.VOC_TC, sorted(kw.items()), 'sim05-v1'], sort_keys=True).encode()).hexdigest()
    if os.path.exists(path):
        c = json.load(open(path))
        if c.get('sig') == sig: return c['tables']
    T = {}
    with B.lid_strip(w):
        for pk, key in VE.POST.items():
            indoor = pk in ('desk', 'lap'); grid = VE.LUX_GRID if indoor else VE.SUN_GRID; vals = []
            for x in grid:
                G = M.g_si(lux=x) if indoor else M.g_si(sun=x)
                vals.append(M.bq_point(VE.sources(PV, key, G, **kw), r_lim=RL, vbat=VE.VBAT_H)['p_bat_mW'] * 1e-3)
            T[pk] = ([float(v) for v in grid], vals)
    json.dump(dict(sig=sig, w=w, kw=kw, tables=T), open(path, 'w'))
    return T

def weeks(T, e_cfg):
    """SIM-05 weeks with table set T and the final MON loads (same call as energy())"""
    base = dict(cell=e_cfg['cell'], display=False, usb=True, asbuilt=True, pulldown_fix=True, gain=4)
    LT = VE.loads(dict(base, which='typ'))[0]; L = B.LOAD
    add = L['fl_typ'] + L['erm'] + L['tap']                         # o2 removed (no battery load as built)
    pmon = LT['MON'] + add + B.final_extra('WEEK_always'); d_on = L['disp_on'] + B.final_extra('WEEK_face_on'); d_rtw = L['disp_rtw']
    U = VE.usable_Wh(e_cfg['cell']); out = {}
    for wn in VE.WEEKS:
        r = VE.sim_week(VE.trace(wn), T, pmon, U, p_disp_on=d_on, p_disp_rtw=d_rtw, dark_policy_min=30)
        out[wn] = {k: r[k] for k in ('harvest_mWh_day', 'load_mWh_day', 'min_soc', 'days_to_empty_from_50pct', 'days_from_full_if_negative')}
    return out

R = dict(meta=dict(mode=MODE, date='2026-11-15', model='v3_energy (SIM-05 conventions) via baseline_calc_v3f.py; all values E (model estimates)'))
for col, w in COLS.items():
    cfg = dict(V3F, strip_w=w)
    e = B.energy(cfg, weeks=tuple(VE.WEEKS))                         # T1-T7, weeks, harvest points (builds the 2.80 mm tables once)
    c = dict(energy=e)
    plit = e['loads_uW']['MON_lit'] * 1e-6
    with B.lid_strip(w):
        sun = {}
        for lab, kw in (('wing lit (convention)', {}), ('sleeve: wing 0.25 x lid', dict(wing_ratio=0.25)), ('dark wing: 0 x lid', dict(wing_ratio=0.0))):
            h045 = VE.harvest_point(PV, 'walking|sun30', M.g_si(sun=0.45), RL, **kw); h01 = VE.harvest_point(PV, 'walking|overcast', M.g_si(sun=0.1), RL, **kw)
            sun[lab] = dict(h045_uW=round(h045, 0), T3_min=round(plit * 24 / (h045 * 1e-6) * 60, 1), overcast_min=round(plit * 24 / (h01 * 1e-6) * 60, 0))
        hl = VE.hot_lid_points(PV, r_lim=RL)
        sun['hot lid 35 / 45 C (T3 range)'] = dict(T3_min=[round(plit * 24 / (hl[k] * 1e-6) * 60, 1) for k in hl if 'lid at' in k])
        rl_ = 1.0 / VE.edge_ratio(w, 27.7); rw_ = 1.0 / VE.edge_ratio(2.7, 31.0)
        edge = dict(rsh_scale_lid=round(rl_, 3), rsh_scale_wing=round(rw_, 3))
        for lab, kw in (('base', {}), ('edge-dominated shunt', dict(rsh_lid=rl_, rsh_wing=rw_))):
            edge[lab] = dict(desk_300lx_uW=round(VE.harvest_point(PV, 'desk|indoor_iso', M.g_si(lux=300), RL, **kw), 1),
                             desk_1000lx_uW=round(VE.harvest_point(PV, 'desk|indoor_iso', M.g_si(lux=1000), RL, **kw), 1),
                             lap_150lx_uW=round(VE.harvest_point(PV, 'lap|indoor_iso', M.g_si(lux=150), RL, **kw), 1),
                             sun045_uW=round(VE.harvest_point(PV, 'walking|sun30', M.g_si(sun=0.45), RL, **kw), 0),
                             cold_start_uA_200lx=round(VE.cs_at(PV, 200, None, None, kw.get('rsh_lid', 1.0), kw.get('rsh_wing', 1.0)) * 1e6, 1))
        down = dict(desk_300lx_uW=round(VE.harvest_point(PV, 'desk|indoor_down', M.g_si(lux=300), RL), 1),
                    desk_1000lx_uW=round(VE.harvest_point(PV, 'desk|indoor_down', M.g_si(lux=1000), RL), 1))
    c['sun_cases'] = sun; c['edge_shunt'] = edge; c['office_downlights'] = down
    c['weeks_sleeve_wing_0p25'] = weeks(tables_kw(w, 'wing025', wing_ratio=0.25), cfg)
    c['weeks_dark_wing'] = weeks(tables_kw(w, 'wing0', wing_ratio=0.0), cfg)
    c['weeks_edge_shunt'] = weeks(tables_kw(w, 'edge', rsh_lid=rl_, rsh_wing=rw_), cfg)
    R[col] = c
    print(col, json.dumps({k: v for k, v in e.items() if k not in ('weeks_from_50pct', 'harvest_uW')}, default=float))
    print('  weeks', {k: v['days_from_full_if_negative'] for k, v in e['weeks_from_50pct'].items()})
    print('  sun', sun); print('  edge', edge); print('  down', down)
    for t in ('weeks_sleeve_wing_0p25', 'weeks_dark_wing', 'weeks_edge_shunt'):
        print(' ', t, {k: v['days_from_full_if_negative'] for k, v in c[t].items()})
json.dump(R, open(os.path.join(HERE, f'sim05_{MODE}.json'), 'w'), indent=1, default=float)
