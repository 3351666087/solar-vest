"""TB1b — MPPT loop stability vs the CN3791 error-amplifier transconductance (not given in the datasheet).
The behavioural model is made linear (I = GM·ΔV_MPPT, clamped ±0.5 mA) and swept over the range of real OTAs."""
import sys, json, time, numpy as np; sys.path.insert(0, "."); from ngs import NGS
import tb_charger as T
BASE = open("models.lib", encoding="utf-8").read()
OLD = "Bcom GND COM I = 0.5m*tanh(V(err)*10)"  # only the amplifier law is swapped; the anti-windup ramps stay
assert OLD in BASE
def lib_gm(gm): return BASE.replace(OLD, f"Bcom GND COM I = max(-0.5m, min(0.5m, {gm}/40*V(err)))")
out = []
for gm in (0.1e-3, 0.5e-3, 2e-3, 10e-3):
    for G, Tc in ((1000, 55), (400, 37), (120, 29)):
        t0 = time.time(); net = T.netlist(G, Tc, 3.7, tstop=15e-3).replace(T.LIB, lib_gm(gm)).replace(".tran", "* pre-set the COM capacitor to the operating point for the first 50 µs, then release (we study the loop, not soft-start)\nVpre pre 0 DC 1.40\nSpre pre comrc ctlp 0 SPRE\n.model SPRE SW (VT=0.5 VH=0.1 RON=1 ROFF=1e12)\nVctlp ctlp 0 PWL(0 1 50u 1 51u 0)\n.tran", 1)
        s = NGS(); s.run(net); t = s.vec("time"); m = t > 12e-3; v = s.vec("vpv")[m]; il = (s.vec("lx")[m] - s.vec("csp")[m]) / 0.09
        m2 = (t > 9e-3) & (t <= 12e-3); dv = float(v.mean() - s.vec("vpv")[m2].mean())
        tu = np.linspace(t[m][0], t[m][-1], 12000); vu = np.interp(tu, t[m], v); vu -= vu.mean(); f = np.fft.rfftfreq(len(tu), tu[1] - tu[0]); A = np.abs(np.fft.rfft(vu)) * 2 / len(tu)
        lo = (f > 200) & (f < 100e3); fk = float(f[lo][np.argmax(A[lo])]); ak = float(A[lo].max())
        r = dict(gm=gm, G=G, T=Tc, vpv=float(v.mean()), vpv_pp=float(np.ptp(v)), il_min=float(il.min()), il_max=float(il.max()), lf_freq=fk, lf_amp_mV=ak * 1e3, drift_mV=dv * 1e3)
        out.append(r)
        print(f"gm {gm*1e3:4.1f} mA/V  G {G:4d}: VPV {r['vpv']:.3f} V pp {r['vpv_pp']*1e3:4.0f} mV  IL {r['il_min']:.2f}..{r['il_max']:.2f} A  "
              f"largest 0.2–100 kHz component {r['lf_amp_mV']:.1f} mV @ {fk/1e3:.1f} kHz  drift {dv*1e3:+.1f} mV  ({time.time()-t0:.0f} s)", flush=True)
json.dump(out, open("tb_loop_gm.json", "w"), indent=1)
