"""Final design (with C15): all 14 charger cases -> tb_charger_final.json"""
import sys, json, time; sys.path.insert(0, ".")
import tb_charger2 as C
cases = [(1000, 55, 3.7), (1000, 25, 3.7), (1000, 0, 3.7), (1000, 55, 3.0), (1000, 55, 4.15), (700, 45, 3.7), (400, 37, 3.7),
         (200, 32, 3.7), (120, 29, 3.7), (60, 27, 3.7), (30, 26, 3.7), (10, 25, 3.7), (120, 29, 3.0), (30, 26, 4.15)]
out = []
for G, Tc, vb in cases:
    t0 = time.time()
    try: r = C.run(G, Tc, vb)
    except Exception as e: print(f"G={G} ERROR {e}", flush=True); continue
    r["pmax"], r["vmp"] = C.pmax(G, Tc); r["capture"] = r["ppanel"] / r["pmax"]; out.append(r)
    json.dump(out, open("tb_charger_final.json", "w"), indent=1)
    print(f"G={G:4d} T={Tc:3d} Vb={vb:.2f} | VPV {r['vpv']:.3f} pp {r['vpv_pp']*1e3:3.0f} mV | Ppv {r['ppanel']:.3f} W = {r['capture']:.1%} | Ibat {r['ibat']*1e3:7.1f} mA | "
          f"IL {r['il_min']:.2f}..{r['il_pk']:.2f} A | D {r['duty']:.2f} | eff {r['eff']:.1%} | Vgs {r['vgs']:.1f} Vds {r['vds']:.1f} | {'settled' if r['settled'] else 'NOT settled'} | {time.time()-t0:.0f} s", flush=True)
