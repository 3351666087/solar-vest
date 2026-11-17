#!/usr/bin/env python3
"""V3-G2 extra 2-D runs after strap2d_v3f.py: the passing wing mitigation on every wrist and in wind, the capsule's skin
corner (perfusion 1e-3, h 5) with a reference strap and one underside fix.
Run: python3 -B strap2d_extra.py > logs/strap2d_extra.log -> out/strap2d_extra.json"""
import sys, os, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import strap2d_v3f as S                                                              # noqa: E402

W3 = dict(w=3e-3)
for Cw in (140.0, 165.0, 200.0):
    S.case(f'C2 mit-b light zone from s 9.5 {Cw:.0f} mm w3e-3', 'wing', Cw, bkw=dict(active=(2.0, 9.5), outer_light=9.5), skw=W3, rng=(2.0, 13.7))
    S.case(f'C2 mit-b light zone from s 10 + strap a 0.30 {Cw:.0f} mm w3e-3', 'wing', Cw, bkw=dict(active=(2.0, 10.0), outer_light=10.0, a_strap=0.30), skw=W3, rng=(2.0, 13.7))
S.case('C2 mit-b light zone from s 9 165 mm w3e-3 wind x0.6', 'wing', 165.0, bkw=dict(active=(2.0, 9.0), outer_light=9.0), skw=dict(w=3e-3, h_conv=6.0), rng=(2.0, 13.7))
S.case('C2 mit-b light zone from s 9 165 mm w6e-3', 'wing', 165.0, bkw=dict(active=(2.0, 9.0), outer_light=9.0), skw=dict(w=6e-3), rng=(2.0, 13.7))
S.case('C2 reference: no wing, strap a 0.6, 165 mm w3e-3 wind x0.6', 'wing', 165.0, bkw=dict(wing_s1=2.0), skw=dict(w=3e-3, h_conv=6.0))
S.case('C2 reference: no wing, strap a 0.6, 165 mm w1e-3', 'wing', 165.0, bkw=dict(wing_s1=2.0), skw=dict(w=1e-3))
S.case('C3 reference: no device, strap a 0.30, 165 mm w1e-3 h 5', 'wing', 165.0, bkw=dict(wing_s1=2.0, a_strap=0.30), skw=dict(w=1e-3, h_conv=5.0), rng=(2.0, 13.9))
S.case('C3 reference: no device, strap a 0.60, 165 mm w1e-3 h 5', 'wing', 165.0, bkw=dict(wing_s1=2.0), skw=dict(w=1e-3, h_conv=5.0), rng=(2.0, 13.9))
for Cw in (140.0, 165.0, 200.0):
    S.case(f'C2 mit-b light zone from s 10 + strap a 0.30 {Cw:.0f} mm w3e-3 wind x0.6', 'wing', Cw, bkw=dict(active=(2.0, 10.0), outer_light=10.0, a_strap=0.30), skw=dict(w=3e-3, h_conv=6.0), rng=(2.0, 13.7))
    S.case(f'C2 mit-a wing to s 10 + strap a 0.30 {Cw:.0f} mm w3e-3 wind x0.6', 'wing', Cw, bkw=dict(active=(2.0, 10.0), wing_s1=10.0, a_strap=0.30), skw=dict(w=3e-3, h_conv=6.0), rng=(2.0, 13.7))
S.case('C2 as designed + strap a 0.30, 165 mm w3e-3', 'wing', 165.0, bkw=dict(a_strap=0.30), skw=W3)
S.case('C2 mit-a wing to s 10 + strap a 0.30 165 mm w1e-3', 'wing', 165.0, bkw=dict(active=(2.0, 10.0), wing_s1=10.0, a_strap=0.30), skw=dict(w=1e-3), rng=(2.0, 13.7))
S.case('C2 mit-a wing to s 8 + strap a 0.30 165 mm w1e-3', 'wing', 165.0, bkw=dict(active=(2.0, 8.0), wing_s1=8.0, a_strap=0.30), skw=dict(w=1e-3), rng=(2.0, 13.7))
for a in (0.15, 0.30):
    S.case(f'C3 capsule a {a:.2f} + strap a 0.30, 165 mm w1e-3 h 5', 'capsule', 165.0, bkw=dict(a_top=a, a_strap=0.30), skw=dict(w=1e-3, h_conv=5.0))
json.dump(S.R, open(os.path.join(HERE, 'out', 'strap2d_extra.json'), 'w'), indent=1)
