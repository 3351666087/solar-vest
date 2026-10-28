"""TB2 (final values) — night battery drain with the shipped divider 200k/51k, R19 1M hold-off, Q8 off, CN3791 sleep current."""
import sys, json; sys.path.insert(0, "."); from ngs import NGS
LIB = open("models.lib").read()
def net(pv_en_fix, rsh):
    gate = "R1 q1g 0 22k" if not pv_en_fix else "R1 q1g q8d 22k\nR19 q1g vpv 1Meg\nXQ8 q8d pven 0 AO3400A\nR20 pven 0 100k"
    return f"""night2
{LIB}
X_PV pvp 0 PV12 PARAMS: G=0 RSH={rsh}
XQ1 pvp q1g vpv AO3401A
{gate}
D1 q1g vpv BZT52C10
D2 0 vpv SMAJ10A
R5 vpv mppt 200k
R6 mppt 0 51k
Rbus1 vpv 0 830k
Rbus2 vpv 0 830k
XM1 sw m1g vpv AO3401A
Rm1g m1g vpv 1k
D5 0 sw SS34
L1 sw csp 22u
R8 csp vb 0.1
Icn vb 0 30u
Vb vb 0 DC 3.7
.op
.end"""
out = {}
for fix in (False, True):
    for rsh in ("300", "3k", "30k"):
        s = NGS(); s.run(net(fix, rsh)); i = -s.vec("vb#branch")[0]; out[f"{'PV_EN' if fix else 'Q1_on'}_Rsh{rsh}"] = i * 1e3
        print(f"{'PV_EN low (Q1 off)' if fix else 'Q1 on (orig)      '} Rsh {rsh:>4s}: {i*1e6:7.1f} µA -> {i*1e3*12:.2f} mAh/12 h, VPV {s.vec('vpv')[0]:.2f} V")
json.dump(out, open("tb_night2.json", "w"), indent=1)
