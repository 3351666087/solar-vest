#!/usr/bin/env python3
"""V3-G2 extra runs after pod3d_v3f.py: motor duty limit (fix) and the 257 s transient factor of the motor event.
Transient factor: centre rise of a uniformly heated disc (radius a = 4 mm, the ERM footprint) on semi-infinite tissue
(alpha = 0.37 / 4e6 m2/s), dT(t)/dT_ss = (2 sqrt(alpha t)/a) [1/sqrt(pi) - ierfc(a / (2 sqrt(alpha t)))]; perfusion and the
device's heat capacity are neglected (the first makes it faster, the second slower) [E].
Run: python3 -B pod3d_extra.py > logs/pod3d_extra.log -> out/pod3d_extra.json"""
import sys, os, json, math
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pod3d_v3f as P                                                                 # noqa: E402

FIXP = dict(pv_raise=0.655, a_win_ir=0.40)
for q in (0.0, 0.0055, 0.011):
    P.run(f'FIXP motor {q * 1e3:.1f} mW mean, sun disp 0.75 w1e-3 wind x0.6', P.pod(a_disp=0.75, q_motor=q, **FIXP), P.bcx('w1e-3', hf=0.6))

P.run('FIXP disp 0.75 print 0.60 w1e-3 wind x0.6 (all worst)', P.pod(a_disp=0.75, a_print=0.60, **FIXP), P.bcx('w1e-3', hf=0.6))
P.run('raise only mask 0.35 w1e-3', P.pod(mask=0.35, pv_raise=0.655), P.bcx('w1e-3'))
P.run('raise only mask 0.35 w3e-3 wind x0.6', P.pod(mask=0.35, pv_raise=0.655), P.bcx('w3e-3', hf=0.6))


def ierfc(x): return math.exp(-x * x) / math.sqrt(math.pi) - x * math.erfc(x)


def factor(t, a=4e-3, al=0.37 / 4.0e6):
    r = math.sqrt(al * t); return (2 * r / a) * (1 / math.sqrt(math.pi) - ierfc(a / (2 * r)))


P.R['motor_transient_factor'] = {f'{t} s': round(factor(t), 3) for t in (20, 60, 120, 257)}
print(P.R['motor_transient_factor'])
json.dump(P.R, open(os.path.join(HERE, 'out', 'pod3d_extra.json'), 'w'), indent=1)
