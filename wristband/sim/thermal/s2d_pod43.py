#!/usr/bin/env python3
"""V3-G2 quick re-check for stage 2d (v3/LEAD_NOTES.md 2k K-1, K-2; v3/stage2d/STAGE2D.md): the stage-2b pod model of pod3d_v3f.pod() with the
43 x 34 geometry of the CAD option L43W34_fold1p9_fpcdwg_jointzif_raise0p15_s2d1 (+2 mm in the strip between the plates: E2, rib / insert /
posts, rail end, glass / laminate / E3 block move +2 mm; lid silicon 333.59 mm2 from the CAD) and the motor over plate E2 at (35.75, 25.55),
standing on the kept carrier film (PSA Z 0.35-0.40, motor 0.40-2.60). Same solver, boundary sets and stage-2b fixes (s2b_final.FIN).
The pod() source is copied at run time and only its coordinates are replaced (each replacement asserted).
Run: python3 -B s2d_pod43.py > logs/s2d_pod43.log  -> out/pod3d_s2d.json"""
import sys, os, json, inspect
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pod3d_v3f as P                                                                 # noqa: E402

SRC = inspect.getsource(P.pod)
REPL = [  # (old, new, count)
    ("m.box('ti', 27.5, 39.5, 6.0, 28.0, 0, 0.25)", "m.box('ti', 29.5, 41.5, 6.0, 28.0, 0, 0.25)", 1),
    ("m.box('air_cav', MOTOR_C[0] - 4.3, MOTOR_C[0] + 4.3, MOTOR_C[1] - 4.3, MOTOR_C[1] + 4.3, 0.25, 2.65 + pv_raise)",
     "m.box('air_cav', MOTOR_C[0] - 4.3, MOTOR_C[0] + 4.3, MOTOR_C[1] - 4.3, MOTOR_C[1] + 4.3, 0.35, 2.65 + pv_raise)", 1),
    ("MOTOR_C[1] + 4.05, 0.30, 2.50)", "MOTOR_C[1] + 4.05, 0.40, 2.60)", 1),
    ("m.box('psa', MOTOR_C[0] - 4.05, MOTOR_C[0] + 4.05, MOTOR_C[1] - 4.05, MOTOR_C[1] + 4.05, 0.25, 0.30)",
     "m.box('psa', MOTOR_C[0] - 4.05, MOTOR_C[0] + 4.05, MOTOR_C[1] - 4.05, MOTOR_C[1] + 4.05, 0.35, 0.40)", 1),
    ("m.box('air', 1.0, 37.5,", "m.box('air', 1.0, 40.5,", 1),
    ("m.box('resin', 1.1, 33.7, 5.0, 5.4", "m.box('resin', 1.1, 35.7, 5.0, 5.4", 1),
    ("m.box('steel', 11.5, 33.7, 5.0, 5.4", "m.box('steel', 11.5, 35.7, 5.0, 5.4", 1),
    ("0.5, 37.5, 0.5, 20.45", "0.5, 40.5, 0.5, 20.45", 4),
    ("m.box('resin', 0, 37.5, 0, 0.5,", "m.box('resin', 0, 40.5, 0, 0.5,", 1),
    ("m.box('resin', 3.8, 37.0, 20.0, 21.0", "m.box('resin', 3.8, 39.0, 20.0, 21.0", 1),
    ("m.box('steel', 3.8, 34.0, 20.0, 20.5", "m.box('steel', 3.8, 36.0, 20.0, 20.5", 1),
    ("for x in (4.1, 10.0, 16.0, 22.0, 28.0, 33.0):", "for x in (4.1, 10.0, 16.0, 22.0, 26.0, 30.0, 35.0):", 1),
    ("m.box('resin', 3.65, 37.5, 20.45, 20.55", "m.box('resin', 3.65, 40.5, 20.45, 20.55", 1),
    ("X0, X1, Y0, Y1 = 3.65, 37.5, 20.55, 33.5", "X0, X1, Y0, Y1 = 3.65, 40.5, 20.55, 33.5", 1),
    ("m.box('si', 4.1, 31.8,", "m.box('si', 4.1, 33.8,", 1),
    ("a_si = 311.1", "a_si = 333.59", 1),
    ("m.box('resin', 37.5, L, 0, W,", "m.box('resin', 40.5, L, 0, W,", 1),
    ("38.0, 40.5, 2.0, 32.0", "41.0, 42.5, 2.0, 32.0", 2),
    ("a_wg = 37.0 * 19.95", "a_wg = 40.0 * 19.95", 1),
]
src = SRC.replace("def pod(", "def pod43(", 1)
for a, b, n in REPL:
    assert src.count(a) == n, (a, src.count(a)); src = src.replace(a, b)
NS = dict(vars(P)); NS.update(L=43.0, W=34.0, MOTOR_C=(35.75, 25.55), ZB=sorted(set(P.ZB + [0.40])))
exec(compile(src, "pod43", "exec"), NS)
pod43 = NS["pod43"]

FIN = dict(pv_raise=0.745, win_raise=0.09, a_win_ir=0.40, u10=(6.05, 25.55), rail_ss=True)   # = s2b_final.FIN (stage-2b design)

if __name__ == '__main__':
    r, b = P.run, P.bcx
    r('CHECK stage-2b 41 mm C1 disp 0.75 print 0.15 w1e-3 wind x0.6 (before 42.67)', P.pod(a_disp=0.75, **FIN), b('w1e-3', hf=0.6))
    for a in (0.45, 0.60, 0.75):
        for w in ('w1e-3', 'w3e-3', 'w6e-3'):
            r(f'S2D C1 disp {a:.2f} print 0.15 {w}', pod43(a_disp=a, **FIN), b(w))
    for a in (0.60, 0.75):
        r(f'S2D C1 disp {a:.2f} print 0.15 w3e-3 wind x0.6', pod43(a_disp=a, **FIN), b('w3e-3', hf=0.6))
        r(f'S2D C1 disp {a:.2f} print 0.15 w1e-3 wind x0.6', pod43(a_disp=a, **FIN), b('w1e-3', hf=0.6))
    for w, hf in (('w3e-3', 1.0), ('w1e-3', 1.0), ('w6e-3', 1.0), ('w3e-3', 0.6), ('w1e-3', 0.6)):
        r(f'S2D C1 disp 0.75 print 0.25 {w}' + (' wind x0.6' if hf < 1 else ''), pod43(a_disp=0.75, a_print=0.25, **FIN), b(w, hf=hf))
    r('S2D C1 disp 0.75 print 0.20 w1e-3 wind x0.6', pod43(a_disp=0.75, a_print=0.20, **FIN), b('w1e-3', hf=0.6))
    for q in (0.0055, 0.011):
        r(f'S2D C4 motor {q * 1e3:.1f} mW mean, sun disp 0.75 w1e-3 wind x0.6', pod43(a_disp=0.75, q_motor=q, **FIN), b('w1e-3', hf=0.6))
    for ap in (0.20, 0.25):
        r(f'S2D C4 motor 5.5 mW mean, sun disp 0.75 print {ap:.2f} w1e-3 wind x0.6', pod43(a_disp=0.75, a_print=ap, q_motor=0.0055, **FIN), b('w1e-3', hf=0.6))
    r('S2D C4 motor 5.5 mW mean, sun disp 0.75 w3e-3', pod43(a_disp=0.75, q_motor=0.0055, **FIN), b('w3e-3'))
    r('S2D C4 motor 0.11 W steady, sun disp 0.75 w3e-3 (continuous, not the design)', pod43(a_disp=0.75, q_motor=0.11, **FIN), b('w3e-3'))
    r('S2D C5 TMP w3e-3 disp 0.75', pod43(a_disp=0.75, **FIN), b('w3e-3'))
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    json.dump(P.R, open(os.path.join(HERE, 'out', 'pod3d_s2d.json'), 'w'), indent=1)
    print('wrote out/pod3d_s2d.json', flush=True)
