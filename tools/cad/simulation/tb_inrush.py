"""TB5a — load-switch inrush vs soft-start capacitor C10 (Q5 gate-source) and battery voltage."""
import sys, json, numpy as np; sys.path.insert(0, "."); from ngs import NGS
import importlib.util
src = open("tb_lib.py", encoding="utf-8").read(); src = src[:src.index("s = sim(lib_net(")]
ns = {}; exec(compile(src, "tb_lib_head", "exec"), ns)
out = {}
for c10 in ("100n", "1u"):
    for vb in (3.4, 3.8, 4.2):
        net = ns["lib_net"](t_cable_pull=50, t_end=3, c10=c10, vb=vb).replace(".tran 2m 3 0 50m uic", ".tran 1u 3 0 20u uic")
        s = NGS(); s.run(net); t = s.vec("time"); ib = (s.vec("bocv") - s.vec("vsys")) / 0.08; vl = s.vec("vload")
        k = (t > 1.0) & (t < 1.2); tt = t[k]; ii = ib[k]
        dur = float(np.sum(np.diff(tt)[ii[:-1] > 1.0])) * 1e3
        i2t = float(np.sum(ii[:-1] ** 2 * np.diff(tt)))
        k90 = np.nonzero((t > 1.0) & (vl > 0.9 * vb))[0]; trise = (t[k90[0]] - 1.0) * 1e3 if len(k90) else float("nan")
        out[f"{c10}_{vb}"] = dict(peak=float(ii.max()), ms_above_1A=dur, i2t=i2t, vload_rise_ms=trise)
        print(f"C10 {c10:>4s} Vbat {vb:.1f} V: inrush peak {ii.max():.2f} A, {dur:.2f} ms above 1 A, I²t {i2t*1e3:.2f} mA²s, VLOAD 0→90 % in {trise:.2f} ms", flush=True)
json.dump(out, open("tb_inrush.json", "w"), indent=1)
