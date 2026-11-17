#!/usr/bin/env python3
"""V3-G2 re-run on the stage-2b design (v3/LEAD_NOTES.md 2c / 2d; CAD v3/stage2b/cad/CAD2B.md). The fix cases are now the design:
  pod  : laminate flush with the window top at the final 5.395 mm pod (pv_raise 0.745 = T-1 0.655 + M-2 0.09), window seat +0.09 (air over the
         panel 0.245 nominal), IR-cut coating removing 40 % of the display heat (T-2, assumed), prints 0.15 nominal / 0.25 allowed (T-2),
         stainless rail section (M-2), U10 + 4 x 4 via island at (6.05, 25.55) (T-5), motor alert <= 5 % duty (T-4), mask <= 0.35 (T-6)
  strap: wing active silicon and laminate to s 8 mm, strap roots and band a 0.30 (T-3); capsule 4.6 mm with a 0.50 mm glass top (M-3)
Same models and boundary sets as pod3d_v3f.py / strap2d_v3f.py (their stage-2a results stay in out/pod3d*.json, out/strap2d*.json = 'before').
Run: python3 -B s2b_final.py > logs/s2b_final.log  -> out/pod3d_s2b.json, out/strap2d_s2b.json"""
import sys, os, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pod3d_v3f as P                                                                 # noqa: E402
import strap2d_v3f as S                                                               # noqa: E402

FIN = dict(pv_raise=0.745, win_raise=0.09, a_win_ir=0.40, u10=(6.05, 25.55), rail_ss=True)
r, b = P.run, P.bcx
r('CHECK stage-2a C1 disp 0.75 print 0.15 w3e-3 (before 42.92)', P.pod(a_disp=0.75), b('w3e-3'))
for a in (0.45, 0.60, 0.75):
    for w in ('w1e-3', 'w3e-3', 'w6e-3'):
        r(f'S2B C1 disp {a:.2f} print 0.15 {w}', P.pod(a_disp=a, **FIN), b(w))
for a in (0.60, 0.75):
    r(f'S2B C1 disp {a:.2f} print 0.15 w3e-3 wind x0.6', P.pod(a_disp=a, **FIN), b('w3e-3', hf=0.6))
    r(f'S2B C1 disp {a:.2f} print 0.15 w1e-3 wind x0.6', P.pod(a_disp=a, **FIN), b('w1e-3', hf=0.6))
for w, hf in (('w3e-3', 1.0), ('w1e-3', 1.0), ('w6e-3', 1.0), ('w3e-3', 0.6), ('w1e-3', 0.6)):
    r(f'S2B C1 disp 0.75 print 0.25 {w}' + (' wind x0.6' if hf < 1 else ''), P.pod(a_disp=0.75, a_print=0.25, **FIN), b(w, hf=hf))
r('S2B C1 disp 0.75 print 0.60 w3e-3 (outside the T-2 rule, sensitivity)', P.pod(a_disp=0.75, a_print=0.60, **FIN), b('w3e-3'))
for w, hf in (('w3e-3', 1.0), ('w1e-3', 1.0), ('w3e-3', 0.6), ('w1e-3', 0.6)):
    r(f'S2B C1m mask 0.35 {w}' + (' wind x0.6' if hf < 1 else ''), P.pod(mask=0.35, **FIN), b(w, hf=hf))
for q in (0.022, 0.050, 0.070):
    r(f'S2B C4 indoor 25 C still air, no sun, charge {q * 1e3:.0f} mW', P.pod(G=0.0, q_chg=q, **FIN), b('w3e-3', T_amb=25.0, hf=0.4, T_skin=33.0))
r('S2B C4 indoor 25 C still air, no sun, no charge', P.pod(G=0.0, **FIN), b('w3e-3', T_amb=25.0, hf=0.4, T_skin=33.0))
for q in (0.0, 0.070):
    r(f'S2B C4 sunny window 800 W/m2 30 C still air disp 0.75, charge {q * 1e3:.0f} mW', P.pod(a_disp=0.75, G=800.0, q_chg=q, **FIN), b('w3e-3', T_amb=30.0, hf=0.4))
r('S2B C4 sun disp 0.75 w3e-3 + charge 70 mW', P.pod(a_disp=0.75, q_chg=0.070, **FIN), b('w3e-3'))
r('S2B C4 sun disp 0.75 print 0.25 w1e-3 wind x0.6 + charge 70 mW', P.pod(a_disp=0.75, a_print=0.25, q_chg=0.070, **FIN), b('w1e-3', hf=0.6))
for q in (0.0055, 0.011):
    r(f'S2B C4 motor {q * 1e3:.1f} mW mean, sun disp 0.75 w1e-3 wind x0.6', P.pod(a_disp=0.75, q_motor=q, **FIN), b('w1e-3', hf=0.6))
r('S2B C4 motor 5.5 mW mean, sun disp 0.75 print 0.25 w1e-3 wind x0.6', P.pod(a_disp=0.75, a_print=0.25, q_motor=0.0055, **FIN), b('w1e-3', hf=0.6))
r('S2B C4 motor 0.11 W steady, sun disp 0.75 w3e-3 (continuous, not the design)', P.pod(a_disp=0.75, q_motor=0.11, **FIN), b('w3e-3'))
r('S2B C5 TMP task BC disp 0.60', P.pod(a_disp=0.60, **FIN), b(task=True))
r('S2B C5 TMP task BC disp 0.75 print 0.25', P.pod(a_disp=0.75, a_print=0.25, **FIN), b(task=True))
r('S2B C5 TMP w3e-3 disp 0.75', P.pod(a_disp=0.75, **FIN), b('w3e-3'))
r('S2B C5 TMP indoor charge 70 mW', P.pod(G=0.0, q_chg=0.070, **FIN), b('w3e-3', T_amb=25.0, hf=0.4, T_skin=33.0))
r('S2B C5 TMP indoor 25 C no sun', P.pod(G=0.0, **FIN), b('w3e-3', T_amb=25.0, hf=0.4, T_skin=33.0))
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
json.dump(P.R, open(os.path.join(HERE, 'out', 'pod3d_s2b.json'), 'w'), indent=1)

WING = dict(active=(2.0, 8.0), wing_s1=8.0, a_strap=0.30)
CAPS = dict(t_top=0.50, cap_t=4.6, a_strap=0.30)
c = S.case
c('CHECK stage-2a C2 wing as designed 165 mm w0.003 (before 44.97)', 'wing', 165.0, skw=dict(w=3e-3))
for Cw in (140.0, 165.0, 200.0):
    for w in (1e-3, 3e-3, 6e-3):
        c(f'S2B C2 wing {Cw:.0f} mm w{w:g}', 'wing', Cw, bkw=WING, skw=dict(w=w), rng=(2.0, 13.7))
    c(f'S2B C2 wing {Cw:.0f} mm w0.003 wind x0.6 (h 6)', 'wing', Cw, bkw=WING, skw=dict(w=3e-3, h_conv=6.0), rng=(2.0, 13.7))
    c(f'S2B C2 wing {Cw:.0f} mm w0.001 wind x0.6 (h 6)', 'wing', Cw, bkw=WING, skw=dict(w=1e-3, h_conv=6.0), rng=(2.0, 13.7))
for a in (0.15, 0.30):
    for hc in (5.0, 10.0, 20.0):
        for Cw in (140.0, 165.0, 200.0):
            c(f'S2B C3 capsule a {a:.2f} h {hc:g} {Cw:.0f} mm w3e-3', 'capsule', Cw, bkw=dict(a_top=a, **CAPS), skw=dict(w=3e-3, h_conv=hc))
    for w in (1e-3, 6e-3):
        c(f'S2B C3 capsule a {a:.2f} h 5 165 mm w{w:g}', 'capsule', 165.0, bkw=dict(a_top=a, **CAPS), skw=dict(w=w, h_conv=5.0))
for Ta in (-10.0, -20.0):
    for w, hc, Gs in ((1e-3, 20.0, 0.0), (5e-4, 30.0, 0.0), (5e-4, 30.0, 500.0)):
        c(f'S2B C3 cold worn air {Ta:g} w{w:g} h {hc:g} sun {Gs:g}', 'capsule', 165.0, bkw=dict(a_top=0.15, **CAPS),
          skw=dict(w=w, h_conv=hc, T_air=Ta, Gsun=Gs, T_pod=Ta + 0.5 * (34 - Ta)))
    for Gs in (0.0, 500.0):
        c(f'S2B C3 cold off-wrist air {Ta:g} h 20 sun {Gs:g}', 'capsule', 165.0, bkw=dict(a_top=0.15, **CAPS), skw=dict(worn=False, h_conv=20.0, T_air=Ta, Gsun=Gs))
json.dump(S.R, open(os.path.join(HERE, 'out', 'strap2d_s2b.json'), 'w'), indent=1)
print('wrote out/pod3d_s2b.json, out/strap2d_s2b.json', flush=True)

# [S2b] print limit at the all-worst pod corner (1e-3 + wind x0.6): T-2 allows 0.25; the largest print that keeps 43.0 C
for ap in (0.20, 0.22):
    r(f'S2B C1 disp 0.75 print {ap:.2f} w1e-3 wind x0.6', P.pod(a_disp=0.75, a_print=ap, **FIN), b('w1e-3', hf=0.6))
    r(f'S2B C4 motor 5.5 mW mean, sun disp 0.75 print {ap:.2f} w1e-3 wind x0.6', P.pod(a_disp=0.75, a_print=ap, q_motor=0.0055, **FIN), b('w1e-3', hf=0.6))
json.dump(P.R, open(os.path.join(HERE, 'out', 'pod3d_s2b.json'), 'w'), indent=1)
