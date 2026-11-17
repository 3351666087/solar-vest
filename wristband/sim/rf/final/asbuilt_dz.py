#!/usr/bin/env python3
"""[rf final] Antenna impedance shift for the as-built feed (J40 +0.40 mm along its axis, LAYOUT N-5) -> asbuilt_dz.json.
Two estimates, the run decides which is used:
 (1) coarse run M_body_c (lid_copy, feed "asbuilt", pins, body) minus fine E_body_f, corrected by the mesh bias of the only
     same-geometry c/f pair of this scene family (../runs/PA_body_c vs PA_body_f: dZ_cf = Z_f - Z_c) ⚠ (other radiator);
 (2) first-order extrapolation along the A->E feed move: dZ = 0.40 / 1.13 * (Z_E - Z_A) ⚠.
usage: emsim-python asbuilt_dz.py"""
import sys, os, json
LID = "/path/to/SolarVest_work/wristband/v3/sim/rf/lid"
sys.path.insert(0, LID); sys.path.insert(0, os.path.join(LID, "..")); sys.dont_write_bytecode = True
import numpy as np, matchlib as ML, post_lid as PL
HERE = os.path.dirname(os.path.abspath(__file__)); RF = os.path.join(LID, "..")
E, A = PL.load("E_body"), PL.load("A_body"); f = E["f"]
M = ML.load_run(os.path.join(HERE, "lid_copy", "runs", "M_body_c.npz"))
Pc, Pf = ML.load_run(os.path.join(RF, "runs", "PA_body_c.npz")), ML.load_run(os.path.join(RF, "runs", "PA_body_f.npz"))
I = lambda r: np.interp(f, r["f"], r["Z"].real) + 1j * np.interp(f, r["f"], r["Z"].imag)
bias = I(Pf) - I(Pc)
dz1 = I(M) + bias - E["Z"]
dz2 = 0.40 / 1.13 * (E["Z"] - A["Z"])
pick = lambda x: {k: str(np.round(complex(np.interp(v, f, x.real), np.interp(v, f, x.imag)), 2)) for k, v in (("2.40", 2.40e9), ("2.44", 2.44e9), ("2.48", 2.48e9))}
R = dict(Z_E_f=pick(E["Z"]), Z_M_c=pick(I(M)), bias_cf_PA=pick(bias), dZ_coarse_corrected=pick(dz1), dZ_extrapolated=pick(dz2),
         eta_rad_M_c=dict(zip([f"{x/1e9:.2f}" for x in M["eta_f"]], np.round(M["eta"], 4).tolist())),
         eta_rad_E_f=dict(zip([f"{x/1e9:.2f}" for x in E["eta_f"]], np.round(E["eta"], 4).tolist())))
# [result] M_body_c is a grid artefact: the moved land reaches X 4.923 (board), 0.077 mm from the inner GND at the pocket edge X 5.0;
# on the 0.25 mm coarse grid the land snaps onto the ground edge -> short (Z_M_c ~ 0.6 + 56j). Not usable (no fine budget left).
# Used: extrapolation (2) plus the land-corner-to-ground edge capacitance C_EDGE in parallel at the feed ⚠ (estimate 0.01-0.05 pF).
CE = float(os.environ.get("C_EDGE_PF", "0.02")) * 1e-12
src = os.environ.get("DZ_SRC", "extrap")
Zx = E["Z"] + dz2; Zp = 1.0 / (1.0 / Zx + 1j * 2 * np.pi * f * CE)
dz = dz1 if src == "coarse" else Zp - E["Z"]
R["C_edge_pF"] = CE * 1e12; R["dZ_used"] = pick(dz)
R.update(source=("coarse run M_body_c - E_body_f + PA c->f bias" if src == "coarse" else "extrapolation 0.40/1.13 (Z_E - Z_A) + land-corner edge C %.3f pF in parallel" % (CE * 1e12)),
         f=f.tolist(), dZ_re=dz.real.tolist(), dZ_im=dz.imag.tolist())
json.dump(R, open(os.path.join(HERE, "asbuilt_dz.json"), "w"))
print(json.dumps({k: v for k, v in R.items() if k not in ("f", "dZ_re", "dZ_im")}, indent=1))
