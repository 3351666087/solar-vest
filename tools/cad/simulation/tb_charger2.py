"""TB1 (long) — switching-level CN3791 MPPT charger run to steady state (25 ms; metrics over the last 3 ms,
settling checked against the 3 ms before). Same netlist as tb_charger.py (real values from pmbh.py)."""
import sys, json, time, numpy as np; sys.path.insert(0, "."); from ngs import NGS
import tb_charger as T

def run(G, Tc, vbat, tstop=25e-3, win=3e-3):
    s = NGS(); s.run(T.netlist(G, Tc, vbat, tstop))
    t = s.vec("time")
    def stats(m):
        tt = t[m]; dt = np.gradient(tt); avg = lambda x: float(np.sum(x * dt) / np.sum(dt))
        g = lambda n: s.vec(n)[m]
        vpv, vb, csp, drv, sw = g("vpv"), g("vbatn"), g("csp"), g("drv"), g("sw")
        il = (g("lx") - csp) / 0.09; ibat = (vb - g("bocv")) / 0.08; ipv = (g("pvp") - g("j1p")) / 0.02
        pin, pout = avg(vpv * ipv), avg(vb * (ibat + 8e-3))
        return dict(vpv=avg(vpv), vpv_pp=float(np.ptp(vpv)), ipv=avg(ipv), ppanel=avg(g("pvp") * ipv - g("pvn") * ipv), ibat=avg(ibat),
                    il_pk=float(il.max()), il_min=float(il.min()), il_pp=float(np.ptp(il)), duty=avg((vpv - drv) > 3.0), com=avg(g("com")),
                    pin=pin, pout=pout, eff=pout / pin if pin > 1e-3 else float("nan"), vgs=float((drv - vpv).min()), vds=float((vpv - sw).max()), sw_min=float(sw.min()))
    a = stats((t > tstop - 2 * win) & (t <= tstop - win)); b = stats(t > tstop - win)
    b["settled"] = abs(a["vpv"] - b["vpv"]) < 0.01 and abs(a["ibat"] - b["ibat"]) < max(0.005, 0.01 * abs(b["ibat"]))
    b["drift_vpv_mV"] = (b["vpv"] - a["vpv"]) * 1e3; b["drift_ibat_mA"] = (b["ibat"] - a["ibat"]) * 1e3
    return dict(G=G, T=Tc, vbat=vbat, **b)

# panel maximum power at each condition (for the MPPT capture ratio)
def pmax(G, Tc):
    s = NGS(); s.run(f"""pv\n{T.LIB}\n.options TEMP={Tc} TNOM=25\nX_PV p 0 PV12 PARAMS: G={G} RSH=3k\nVt p 0 DC 0\n.dc Vt 0 9 0.005\n.end""")
    v = s.vec("v-sweep"); i = s.vec("vt#branch"); p = v * i; k = int(np.argmax(p)); return float(p[k]), float(v[k])

if __name__ == "__main__":
    cases = [(1000, 55, 3.7), (1000, 25, 3.7), (1000, 0, 3.7), (1000, 55, 3.0), (1000, 55, 4.15), (700, 45, 3.7), (400, 37, 3.7),
             (200, 32, 3.7), (120, 29, 3.7), (60, 27, 3.7), (30, 26, 3.7), (10, 25, 3.7), (120, 29, 3.0), (30, 26, 4.15)]
    out = []
    for G, Tc, vb in cases:
        t0 = time.time()
        try: r = run(G, Tc, vb)
        except Exception as e: print(f"G={G:4d} T={Tc:3d} Vb={vb:.2f} | ERROR {e}", flush=True); continue
        r["pmax"], r["vmp"] = pmax(G, Tc); r["capture"] = r["ppanel"] / r["pmax"]; out.append(r)
        print(f"G={G:4d} T={Tc:3d} Vb={vb:.2f} | VPV {r['vpv']:.3f} (pp {r['vpv_pp']*1e3:3.0f} mV, Vmp {r['vmp']:.2f}) Ppv {r['ppanel']:.3f} W = {r['capture']:.1%} of Pmax | "
              f"Ibat {r['ibat']*1e3:7.1f} mA  IL {r['il_min']:.2f}..{r['il_pk']:.2f} A  D {r['duty']:.2f}  eff {r['eff']:.1%} | Vgs {r['vgs']:.1f} Vds {r['vds']:.1f} | "
              f"{'settled' if r['settled'] else 'NOT settled'} (ΔVPV {r['drift_vpv_mV']:+.1f} mV, ΔIbat {r['drift_ibat_mA']:+.1f} mA)  {time.time()-t0:.0f} s", flush=True)
        json.dump(out, open("tb_charger_long.json", "w"), indent=1)
    json.dump(out, open("tb_charger_long.json", "w"), indent=1)
