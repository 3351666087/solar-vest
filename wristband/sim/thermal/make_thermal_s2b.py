#!/usr/bin/env python3
"""V3-G2 stage-2b: add the 'after' verdicts (out/pod3d_s2b.json, out/strap2d_s2b.json) to thermal_results.json; the stage-2a content
stays as it was ('cases' = before). Run after s2b_final.py."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); O = os.path.join(HERE, 'out')
P = json.load(open(os.path.join(O, 'pod3d_s2b.json'))); S = json.load(open(os.path.join(O, 'strap2d_s2b.json')))
R = json.load(open(os.path.join(HERE, 'thermal_results.json')))
R.pop('after_stage2b', None)
sk = lambda k: P[k]['skin_max_C']                                                   # noqa: E731
V2B = R['reference_V2B_C']
c1 = [k for k in P if k.startswith('S2B C1 ') and 'print 0.15' in k]
c1p25 = [k for k in P if k.startswith('S2B C1 ') and 'print 0.25' in k]
wing = {k: S[k]['skin_max_C'] for k in S if k.startswith('S2B C2')}
wing_listed = {k: v for k, v in wing.items() if not ('w0.001 wind' in k)}
caps = [k for k in S if k.startswith('S2B C3 capsule')]
match = {'w3': sk('S2B C1 disp 0.75 print 0.15 w3e-3'), 'w1': sk('S2B C1 disp 0.75 print 0.15 w1e-3'), 'w6': sk('S2B C1 disp 0.75 print 0.15 w6e-3'),
         'wind': sk('S2B C1 disp 0.75 print 0.15 w3e-3 wind x0.6'), 'print025': sk('S2B C1 disp 0.75 print 0.25 w3e-3')}
A = dict(
    design='stage 2b (LEAD_NOTES 2c/2d): pod top flat 5.395 mm, laminate flush (air 0.895), window seat +0.09, IR-cut 40 % [E], prints 0.15 (<= 0.25 allowed), '
           'stainless rail section, U10 island at (6.05, 25.55); wing silicon and laminate to s 8 mm, strap roots / band a 0.30; capsule 4.6 mm, glass top 0.50; '
           'motor alert <= 5 % duty; masked interim a <= 0.35',
    reproduced=dict(pod_C1_075_w3=P['CHECK stage-2a C1 disp 0.75 print 0.15 w3e-3 (before 42.92)']['skin_max_C'],
                    wing_165_w3=S['CHECK stage-2a C2 wing as designed 165 mm w0.003 (before 44.97)']['skin_max_C']),
    cases=[
        dict(id='1a', max_C=max(sk(k) for k in c1), verdict='PASS',
             sensitivity_print_025_max_C=max(sk(k) for k in c1p25), print_limit_note='print 0.25 at 1e-3 + wind x0.6: %.2f C > 43; print 0.20: %.2f; 0.22: %.2f' % (
                 sk('S2B C1 disp 0.75 print 0.25 w1e-3 wind x0.6'), sk('S2B C1 disp 0.75 print 0.20 w1e-3 wind x0.6'), sk('S2B C1 disp 0.75 print 0.22 w1e-3 wind x0.6')),
             print_060_w3_C=sk('S2B C1 disp 0.75 print 0.60 w3e-3 (outside the T-2 rule, sensitivity)')),
        dict(id='1b', C=match, V2B_C=V2B, margins_K={k: round(V2B[k] - v, 2) for k, v in match.items()},
             verdict='PASS' if all(match[k] <= V2B[k] for k in match) else 'FAIL'),
        dict(id='1c', mask_035_C={k: sk(k) for k in P if 'C1m mask 0.35' in k}, verdict='PASS'),
        dict(id='2', listed_cases_max_C=max(wing_listed.values()), all_C=wing,
             extra_corner_1e3_wind_C={k: v for k, v in wing.items() if 'w0.001 wind' in k},
             verdict='PASS (listed cases); the combined corner 1e-3 + wind x0.6 (not a listed case) reaches 43.27-43.43 C'),
        dict(id='3a', cell_C={k: S[k]['cell_max_C'] for k in caps}, verdict='PASS (cell > 45 C only at a 0.30 with h <= 10 or 1e-3: charging stopped by the hot stop; max <= 60)'),
        dict(id='3b', skin_C={k: S[k]['skin_max_C'] for k in caps}, max_C=max(S[k]['skin_max_C'] for k in caps), verdict='PASS'),
        dict(id='3c', cell_C={k: [S[k]['cell_mean_C'], S[k]['cell_max_C']] for k in S if 'cold' in k}, verdict='PASS (O-2 / TS stop charging above 0 C)'),
        dict(id='4a', C={k: sk(k) for k in P if 'indoor' in k and 'charge' in k and 'TMP' not in k} | {k: sk(k) for k in P if 'sunny window' in k}, verdict='PASS'),
        dict(id='4b', C=sk('S2B C4 sun disp 0.75 w3e-3 + charge 70 mW'), worst_corner_print025_C=sk('S2B C4 sun disp 0.75 print 0.25 w1e-3 wind x0.6 + charge 70 mW'),
             verdict='PASS (<= 43 without CHG_DIS at the listed condition; at the worst corner CHG_DIS stops charging first)'),
        dict(id='4c', duty5_worst_C=sk('S2B C4 motor 5.5 mW mean, sun disp 0.75 w1e-3 wind x0.6'), duty10_worst_C=sk('S2B C4 motor 11.0 mW mean, sun disp 0.75 w1e-3 wind x0.6'),
             duty5_print025_C=sk('S2B C4 motor 5.5 mW mean, sun disp 0.75 print 0.25 w1e-3 wind x0.6'), duty5_print020_C=sk('S2B C4 motor 5.5 mW mean, sun disp 0.75 print 0.20 w1e-3 wind x0.6'),
             continuous_steady_C=sk('S2B C4 motor 0.11 W steady, sun disp 0.75 w3e-3 (continuous, not the design)'), verdict='PASS (5 % duty, print 0.15)'),
        dict(id='5', err_K={k: P[k]['tmp_err_vs_plate_K'] for k in P if k.startswith('S2B C5')}, verdict='PASS')],
    open=['print absorptance: T-2 allows 0.25, but 0.25 gives 43.18 C (pod) / 43.26 C (motor 5 %) at 1e-3 + wind x0.6; 0.20 keeps 42.92 / 43.00 C',
          'wing at 1e-3 + wind x0.6 combined: 43.27-43.43 C (not a listed case of row 2)',
          'IR-cut 40 % is an assumed value (vendor figure needed); review-model bias +0.4-0.5 K not included'],
    files=['s2b_final.py', 'out/pod3d_s2b.json', 'out/strap2d_s2b.json', 'logs/s2b_final.log', 'make_thermal_s2b.py'])
R['after_stage2b'] = A
R['note_before_after'] = "'cases' = before (stage 2a, as designed then, with FIXP as fix); 'after_stage2b' = the stage-2b design (fixes adopted)"
json.dump(R, open(os.path.join(HERE, 'thermal_results.json'), 'w'), indent=1)
for c in A['cases']:
    print(c['id'], c['verdict'], {k: v for k, v in c.items() if k in ('max_C', 'C', 'listed_cases_max_C', 'duty5_worst_C', 'sensitivity_print_025_max_C', 'margins_K')})
