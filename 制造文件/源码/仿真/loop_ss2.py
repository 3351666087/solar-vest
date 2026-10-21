import sys; sys.path.insert(0, ".")
import numpy as np, loop_ss as LS
f = np.logspace(1, 5.3, 4000)
for Cd in (47e-6, 100e-6):
    for Rd in (0.5, 1.0, 2.0, 4.0):
        worst_pm, worst_gm, worst_case = 999, 999, ""
        for G, Tc, D, IL in LS.cases:
            ipv, r_pv = LS.pv_point(G, Tc)
            for gm in (0.05e-3, 0.2e-3, 1e-3, 5e-3, 20e-3):
                m = LS.margins(f, LS.loop(f, D, 5.93, IL, r_pv, gm, (Cd, Rd)))
                if m["pm"] is not None and m["pm"] < worst_pm: worst_pm, worst_case = m["pm"], f"G{G} gm{gm*1e3:g}"
                if m["gm_db"] is not None and m["gm_db"] < worst_gm: worst_gm = m["gm_db"]
        # also: worst PM restricted to gm <= 5 mA/V
        w5 = min(LS.margins(f, LS.loop(f, D, 5.93, IL, LS.pv_point(G, Tc)[1], gm, (Cd, Rd)))["pm"] or 999 for G, Tc, D, IL in LS.cases for gm in (0.05e-3, 0.2e-3, 1e-3, 5e-3))
        print(f"Cd {Cd*1e6:4.0f} µF ESR {Rd:3.1f} Ω: worst PM {worst_pm:4.0f}° ({worst_case}), worst PM for gm ≤ 5 mA/V {w5:4.0f}°, worst GM {'∞' if worst_gm == 999 else '%.0f dB' % worst_gm}")
