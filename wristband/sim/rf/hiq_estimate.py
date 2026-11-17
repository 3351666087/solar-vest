#!/usr/bin/env python3
"""ESTIMATE (not a part library): best <= 2-part pi-net with ideal L / C of a given Q (no lands, no line), to show how much of
the total efficiency is lost in the LQG15HS multilayer inductors.  usage: python hiq_estimate.py runs/X_body_f.npz QL [QC]"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.dont_write_bytecode = True
import numpy as np
import matchlib as ML
r = ML.load_run(sys.argv[1]); QL = float(sys.argv[2]); QC = float(sys.argv[3]) if len(sys.argv) > 3 else 200.0
f = r["f"]; sel = ML.band_sel(f); fb = f[sel]; Z = r["Z"][sel]; eta = ML.eta_on(r, fb); w = 2 * np.pi * fb
Ls = np.geomspace(0.3e-9, 27e-9, 120); Cs = np.geomspace(0.1e-12, 10e-12, 120)
el = [("L", v, 1j * w * v * (1 - 1j / QL)) for v in Ls] + [("C", v, 1 / (1j * w * v) * (1 - 1j / QC)) for v in Cs]
def run(ZL, ser, shA, shB):
    Zx = ZL
    if shB is not None: Zx = 1 / (1 / Zx + 1 / shB)
    Zin = Zx + ser
    if shA is not None: Zin = 1 / (1 / Zin + 1 / shA)
    # power to the antenna: P_ant / P_avail via the network (lossy parts): compute with currents
    G = (Zin - 50) / (Zin + 50)
    V1 = 2 * 50 / (Zin + 50) * 50 / 50   # source 1 V-equivalent amplitude scaling: Vs=1 -> V1 = Zin/(Zin+50)
    V1 = Zin / (Zin + 50); I1 = 1 / (Zin + 50)
    Iser = I1 - (V1 / shA if shA is not None else 0)
    V2 = V1 - Iser * ser
    Pant = np.real(V2 * np.conj(V2 / ZL))
    return Pant / (1 / (4 * 50)), G
best = None
for e_ser in el:
    for side in ("A", "B", None):
        for e_sh in (el if side else [None]):
            sh = e_sh[2] if e_sh else None
            GT, G = run(Z, e_ser[2], sh if side == "A" else None, sh if side == "B" else None)
            et = (eta * GT).min()
            if best is None or et > best[0]:
                best = (et, e_ser[:2], side, e_sh[:2] if e_sh else None, float((-20 * np.log10(np.abs(G))).min()))
et, ser, side, sh, rl = best
print(json.dumps(dict(run=os.path.basename(sys.argv[1]), Q_L=QL, Q_C=QC, eta_tot_body_min=et, series=[ser[0], ser[1]],
                      shunt_side=side, shunt=[sh[0], sh[1]] if sh else None, RL_min_dB=rl)))
