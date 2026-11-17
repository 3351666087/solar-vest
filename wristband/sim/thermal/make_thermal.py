#!/usr/bin/env python3
"""V3-G2: collect out/*.json into thermal_results.json (verdicts as written). Run after the four model scripts."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); O = os.path.join(HERE, 'out')
P = json.load(open(os.path.join(O, 'pod3d.json'))); P.update(json.load(open(os.path.join(O, 'pod3d_extra.json'))))
S = json.load(open(os.path.join(O, 'strap2d.json'))); S.update(json.load(open(os.path.join(O, 'strap2d_extra.json'))))
sk = lambda k: P[k]['skin_max_C']                                                   # noqa: E731
ws = lambda k: S[k]['skin_max_C']                                                   # noqa: E731
V2B = dict(w3=41.17, w1=41.81, w6=40.72, wind=41.99, print025=41.75)              # REDESIGN_V2 5.7 (review model)
pods = [k for k in P if k.startswith('C1 ') and 'task' not in k]
podsF = [k for k in P if k.startswith('FIXP C1 ') and 'print 0.60' not in k]
caps = [k for k in S if k.startswith('C3 capsule')]
cold = [k for k in S if k.startswith('C3 cold')]
R = dict(
    gate='V3-G2 (SIM-13 thermal), V3-F stage 2a pod 41 x 34', date='2026-11-15',
    models=dict(pod='pod3d_v3f.py: physics review 3-D FV model (review_fv3d_v2b.py, copy) with the V3-F geometry; reproduces V2-B rev1 41.17 C',
                strap='strap2d_v3f.py: 2-D section along the strap over 2-D Pennes tissue (arterial 37 C at 30 mm), gap profile from geom_v3f worn geometry',
                bias='review model reads 0.4-0.5 K low against SIM-13 (REDESIGN 5.7); absolute values below are model values without the bias'),
    reference_V2B_C=V2B, reproduced_V2B_w3_C=sk('REF V2-B rev1, print 0.15, w3e-3 (review 41.17)'),
    O2_window_C=dict(cold_stop=[0.84, 3.97], hot_stop=[34.88, 43.31], TS_USB_cold=[1.85, 6.04], TS_USB_hot=[38.79, 44.84],
                     source='v3/design/calc/o2_inhibit.json threshold_design.corners, ts_window.alone'),
    cases=[
        dict(id='1a', what='pod full sun, skin <= 43 C (disp 0.45-0.75, print 0.15, perfusion 1e-3..6e-3, wind x0.6)',
             as_designed_max_C=max(sk(k) for k in pods if 'print 0.60' not in k and 'print 0.25' not in k),
             as_designed_range_no_wind_C=[min(sk(k) for k in pods if 'wind' not in k and 'print' in k), max(sk(k) for k in pods if 'wind' not in k and 'print 0.15' in k)],
             verdict='FAIL', with_FIXP_max_C=max(sk(k) for k in podsF), verdict_with_fix='PASS'),
        dict(id='1b', what='pod not hotter than V2-B (41.17 at 3e-3; matching conditions)', as_designed_C={a: sk(f'C1 disp {a} print 0.15 w3e-3') for a in ('0.45', '0.60', '0.75')},
             verdict='FAIL', with_FIXP_C={'w3 disp 0.75': sk('FIXP C1 disp 0.75 print 0.15 w3e-3'), 'w1': sk('FIXP C1 disp 0.75 print 0.15 w1e-3'),
                                          'w6': sk('FIXP C1 disp 0.75 print 0.15 w6e-3'), 'wind': sk('FIXP C1 disp 0.75 print 0.15 w3e-3 wind x0.6'),
                                          'print 0.25': sk('FIXP C1 disp 0.75 print 0.25 w3e-3')}, verdict_with_fix='PASS (margin 0.02-0.21 K)'),
        dict(id='1c', what='interim build, masked window a 0.6', as_designed_C={'w3': sk('C1m mask 0.60 w3e-3'), 'w1': sk('C1m mask 0.60 w1e-3'), 'wind': sk('C1m mask 0.60 w3e-3 wind x0.6'),
             'w1 wind': sk('C1m mask 0.60 w1e-3 wind x0.6')}, verdict='FAIL',
             fix='PV raise 0.655 + mask a <= 0.35', with_fix_C={'w3': sk('raise only C1m mask 0.35 w3e-3'), 'w1': sk('raise only mask 0.35 w1e-3'),
                                                                 'wind': sk('raise only mask 0.35 w3e-3 wind x0.6'), 'w1 wind': sk('raise only C1m mask 0.35 w1e-3 wind x0.6')}, verdict_with_fix='PASS'),
        dict(id='2', what='c-Si wing on root B per sub-cell, skin <= 43 C (hard gate before wear)',
             as_designed={k.replace('C2 wing as designed ', ''): dict(skin_max_C=S[k]['skin_max_C'], sub_cells_C=S[k]['sub_cell_skin_max_C'], gap_mm=S[k]['sub_cell_mean_gap_mm'])
                          for k in S if k.startswith('C2 wing as designed')}, verdict='FAIL',
             mitigations={k.replace('C2 ', ''): ws(k) for k in S if k.startswith('C2 mit') or k.startswith('C2 reference') or 'as designed + strap' in k},
             smallest_passing='(b) light outer zone a <= 0.30 from s 9 mm (active 2.0-9.0, -40 % wing silicon): 42.61-42.97 C on 140/165/200 mm at 3e-3; '
                              'fails in wind x0.6 (43.58) where a bare a 0.6 strap already gives 43.67. Every case incl. wind and 1e-3: (a) active wing to s 8 mm + light strap root/band a <= 0.30 (42.46 at 1e-3)'),
        dict(id='3a', what='capsule cell in sun (glass top 0.40, a 0.15 / 0.30, h 5-20)', cell_C={k.replace('C3 capsule ', ''): S[k]['cell_max_C'] for k in caps},
             verdict='PASS (cell > 45 only with a 0.15 h 5 1e-3 (45.74) and a 0.30 h <= 10; the hot stop (O-2 <= 43.31, firmware 45, TS <= 44.84) inhibits charging there; max 49.42 <= 60)'),
        dict(id='3b', what='skin under the capsule <= 43 C', skin_C={k.replace('C3 capsule ', ''): S[k]['skin_max_C'] for k in caps}, verdict='FAIL',
             worst_C=ws('C3 capsule a 0.15 h 5 165 mm w1e-3'), fix='light strap root/band a <= 0.30', with_fix_C=ws('C3 capsule a 0.15 + strap a 0.30, 165 mm w1e-3 h 5'), verdict_with_fix='PASS'),
        dict(id='3c', what='cold: -10 / -20 C air, wind, sun 0 / 500 W/m2, worn and off the wrist', cell_C={k.replace('C3 cold ', ''): [S[k]['cell_mean_C'], S[k]['cell_max_C']] for k in cold},
             note='worn 2-D values are optimistic (37 C held at 30 mm depth); physics-lens lumped worn values 2 C (-10) / -10 C (-20); off the wrist the cell is at air temperature',
             verdict='PASS: the cell goes below 0 C (off the wrist -20 C, worn plausibly -10 C); O-2 cold stop 0.84-3.97 C and USB TS 1.85-6.04 C stop charging above 0 C at every corner'),
        dict(id='4a', what='charging heat in the pod, BQ25170 22/50/70 mW', indoor_C={k: sk(k) for k in P if k.startswith('C4 indoor')},
             sunny_window_C={k: sk(k) for k in P if 'sunny window' in k}, verdict='PASS'),
        dict(id='4b', what='charging in full sun (70 mW)', as_designed_C=sk('C4 sun disp 0.75 w3e-3 + charge 70 mW'), FIXP_C=sk('FIXP C4 sun disp 0.75 w3e-3 + charge 70 mW'),
             verdict='PASS (CHG_DIS at 41 C skin: the sun alone gives 42.92, so steady charging there is not reached; 44.16 without CHG_DIS; 42.59 with FIXP)'),
        dict(id='4c', what='skin-hot motor event 0.11 W x 257 s', steady_as_designed_C=sk('C4 motor 0.11 W steady, sun disp 0.75 w3e-3'),
             transient_factor=P['motor_transient_factor'], est_257s_as_designed_C=round(sk('C1 disp 0.75 print 0.15 w3e-3') + P['motor_transient_factor']['257 s'] * (sk('C4 motor 0.11 W steady, sun disp 0.75 w3e-3') - sk('C1 disp 0.75 print 0.15 w3e-3')), 2),
             steady_FIXP_C=sk('FIXP C4 motor 0.11 W steady, sun disp 0.75 w3e-3'), verdict='FAIL',
             fix='alert at <= 5 % duty (mean <= 5.5 mW)', with_fix_worst_C=sk('FIXP motor 5.5 mW mean, sun disp 0.75 w1e-3 wind x0.6'),
             ten_pct_duty_worst_C=sk('FIXP motor 11.0 mW mean, sun disp 0.75 w1e-3 wind x0.6'), verdict_with_fix='PASS'),
        dict(id='5', what='TMP117 coupling <= 0.5 K (U10 at pod 5.5 / 25.6 over E1, 4 x 4 via island, filled contact)',
             err_K={k: P[k]['tmp_err_vs_plate_K'] for k in P if k.startswith('C5')}, verdict='PASS (0.16-0.30 K with the island; 1.11 K without it)')],
    fixes=dict(FIXP='PV laminate raised 0.655 mm (laminate top flush with the window top, air under the laminate 0.15 -> 0.805 mm; pod maximum unchanged at 5.305) '
                    '+ IR-cut (hot-mirror) coating on the window glass removing about 40 % of the display heat [E]',
               rules=['window border and laminate prints a <= 0.25 (a 0.60 gives 45.07 C even with FIXP)', 'TMP117 via island 4 x 4 mm with filled contact to E1, no parts on it',
                      'strap roots and band a <= 0.30 (light)', 'motor alert <= 5 % duty']),
    files=['pod3d_v3f.py', 'pod3d_extra.py', 'strap2d_v3f.py', 'strap2d_extra.py', 'out/pod3d.json', 'out/pod3d_extra.json', 'out/strap2d.json', 'out/strap2d_extra.json'])
json.dump(R, open(os.path.join(HERE, 'thermal_results.json'), 'w'), indent=1)
for c in R['cases']:
    print(c['id'], c['verdict'], {k: v for k, v in c.items() if k in ('as_designed_max_C', 'with_FIXP_max_C', 'as_designed_C', 'with_FIXP_C', 'worst_C', 'with_fix_C', 'est_257s_as_designed_C', 'with_fix_worst_C')})
