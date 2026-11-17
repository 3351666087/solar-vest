"""[rf final] Line impedance of the measured RF segments (copy of planb/cpwg_z.py formula; 8L est. L1-L2 1080 0.0764 mm, er 3.91 ⚠; mask, t ignored ⚠)."""
import json, math, statistics as st
from scipy.special import ellipk
def KK(k): return ellipk(k * k) / ellipk(1 - k * k)
def cpwg(W, G, h, er):
    a, b = W / 2, W / 2 + G; k = a / b; k1 = math.tanh(math.pi * a / (2 * h)) / math.tanh(math.pi * b / (2 * h))
    q = KK(k1) / KK(k); ee = (1 + er * q) / (1 + q)
    return 60 * math.pi / math.sqrt(ee) / (KK(k) + KK(k1)), ee
H, ER = 0.0764, 3.91
g = json.load(open("rf_geom_final.json"))["gaps"]
R = {}
for net in ("ANT_FEED", "RF_50R"):
    for w in sorted({x["w"] for x in g[net]}):
        segs = [x for x in g[net] if x["w"] == w]
        go = st.median([x["gap"] for x in segs]); gg = st.median([min(x["gap_gnd_fill"], 3.0) for x in segs])
        z_o, e_o = cpwg(w, go, H, ER); z_g, e_g = cpwg(w, gg, H, ER)
        R[f"{net} w{w}"] = dict(n=len(segs), gap_other_cu_med=go, gap_gnd_med=gg, Z_gnd_gap=round(z_g, 1), eeff_gnd_gap=round(e_g, 2),
                                Z_other_gap=round(z_o, 1), eeff_other_gap=round(e_o, 2))
        print(net, w, R[f"{net} w{w}"])
json.dump(R, open("line_z.json", "w"), indent=1)
