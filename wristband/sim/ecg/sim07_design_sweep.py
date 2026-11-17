"""SIM-07 design sweep: choose C_CM / C_DIFF (stage 1) and the RLD feedback network (stage 2).

Stage 1 (RLD fixed at TI's typical REXT 1 MΩ ‖ CEXT 1.5 nF, internal RLDREF): for each (C_CM, C_DIFF) candidate
  - signal attenuation 1-|H| over 0.5-40 Hz on the 3×3 electrode grid (matched and ±50 % mismatched electrodes)
  - 50 Hz CM->DM at the pins (typical environment, worst of 4 mismatch patterns)
  Rule: both metrics only get worse with added capacitance (see table), so the smallest values win unless the RF
  estimate (sim07_verify.py G) shows the board needs them.
Stage 2 (C_CM / C_DIFF from stage 1): grid REXT × CEXT × Rz (Rz = lead resistor in series with CEXT)
  - phase margin and gain margin, worst over 9 electrode corners × 2 environments × E2 ±50 % × 3 model cases
    (nominal, PGA common-mode bandwidth 50 kHz, RLD open-loop gain 80 dB)
  - 50 Hz DM, worst over the grid and 4 mismatch patterns (typical environment)
  Rule: among candidates with worst PM ≥ 60° and worst GM ≥ 10 dB over this 3-case set, take the one with the lowest
  worst-case 50 Hz DM; ties (within 3 %) go to the larger PM. 60° (not 45°) because sim07_verify.py re-checks the
  choice against 6 model cases (adds PGA bandwidth 20 kHz, RLD GBW -30 %, 10 pF on RLDINV), which cost up to ≈10°,
  and because the PGA common-mode bandwidth and the RLD open-loop gain have no datasheet value.
  (DM is computed for every candidate with PM ≥ 50°, so the table also shows what a 50° screen would have picked.)
Writes results/sim07_sweep.json. Run time ≈ 15 min (longer on a loaded machine).
SELECT_ONLY=1 re-applies the selection rule to an existing results/sim07_sweep.json without simulating.
"""
import json, os, time, itertools
import numpy as np
from sim07_common import (S, GRID, ENVS, M, default_cfg, mismatch_cfg, signal_att, dm50, loop, zscale, V, HERE)
from designs import FINAL

t0 = time.time()
PM_SCREEN, GM_SCREEN = 60.0, 10.0
RES = {"stage1": [], "stage2": []}
CCM = [0.0, 4.7e-12, 10e-12, 22e-12]
CDIFF = [0.0, 10e-12, 47e-12, 100e-12]
base_rld = dict(rext=1e6, cext=1.5e-9, rz=0)
key = lambda R, C: f"{R/1e6:g}M_{C*1e9:g}n"

# ------------------------------------------------------------------------------------------------ stage 1
SELECT_ONLY = os.environ.get("SELECT_ONLY") == "1"
if SELECT_ONLY:
    RES = json.loads((HERE / "results" / "sim07_sweep.json").read_text())
for ccm, cdiff in ([] if SELECT_ONLY else itertools.product(CCM, CDIFF)):
    row = dict(ccm=ccm, cdiff=cdiff, att={}, dm50={})
    for R, C in GRID:
        worst = 0.0
        for pat in ("matched", "m+", "m-"):
            cfg = default_cfg(Ccm=[ccm, ccm], Cdiff=cdiff, **base_rld, **ENVS["typical"])
            if pat == "matched":
                cfg["Re"] = [(R, C)] * 3
            else:
                cfg = mismatch_cfg(R, C, 1 if pat == "m+" else -1, 0, cfg)
            worst = max(worst, signal_att(cfg)[0])
        row["att"][key(R, C)] = worst
        dms = [dm50(mismatch_cfg(R, C, s_, m2, default_cfg(Ccm=[ccm, ccm], Cdiff=cdiff, **base_rld, **ENVS["typical"])))[0]
               for s_, m2 in itertools.product((1, -1), (1, -1))]
        row["dm50"][key(R, C)] = max(dms)
    RES["stage1"].append(row)
    print(f"C_CM {ccm*1e12:5.1f} pF C_DIFF {cdiff*1e12:5.0f} pF | att% " +
          " ".join(f"{row['att'][k]*100:5.2f}" for k in row["att"]) + " | dm50 µV " +
          " ".join(f"{row['dm50'][k]:6.2f}" for k in row["dm50"]), flush=True)
print("electrode corners:", list(RES["stage1"][0]["att"]))
# stage-1 outcome: are attenuation (in C_CM and C_DIFF) and 50 Hz DM (in C_CM) monotone non-decreasing?
s1 = {(r["ccm"], r["cdiff"]): r for r in RES["stage1"]}
mono = all(s1[(a, d)]["att"][k] <= s1[(b, d)]["att"][k] + 1e-6 and s1[(a, d)]["dm50"][k] <= s1[(b, d)]["dm50"][k] * 1.001
           for d in CDIFF for a, b in zip(CCM[:-1], CCM[1:]) for k in s1[(a, d)]["att"])
mono &= all(s1[(c, a)]["att"][k] <= s1[(c, b)]["att"][k] + 1e-6 for c in CCM for a, b in zip(CDIFF[:-1], CDIFF[1:])
            for k in s1[(c, a)]["att"])
CHOICE = dict(Ccm=[0.0, 0.0], Cdiff=0.0)
RES["stage1_choice"] = dict(CHOICE, monotone=bool(mono),
                            reason="attenuation and 50 Hz DM both grow with C_CM and C_DIFF (monotone=%s); "
                                   "RF benefit assessed in sim07_verify G" % mono)
print(f"stage 1 done {time.time()-t0:.0f} s; monotone in C: {mono} -> C_CM DNP, C_DIFF DNP", flush=True)
(HERE / "results").mkdir(exist_ok=True)
(HERE / "results" / "sim07_sweep.json").write_text(json.dumps(RES, indent=1))

# ------------------------------------------------------------------------------------------------ stage 2
REXT = [1e6, 10e6, 0]                   # 0 = DNP
CEXT = [1.5e-9, 470e-12, 220e-12, 150e-12, 100e-12, 68e-12, 47e-12]
RZ = [0, 100e3, 220e3, 470e3, 1e6]
SENS = {"nominal": {}, "pga_bw_50k": dict(pga_bw=50e3), "a0_80dB": dict(a0=1e4)}
for rext, cext, rz in ([] if SELECT_ONLY else itertools.product(REXT, CEXT, RZ)):
    rld = dict(rext=rext, cext=cext, rz=rz)
    worst = dict(pm=999.0, gm=999.0, case=None)
    for (R, C), env, m2, sk in itertools.product(GRID, ENVS, (1, -1), SENS):
        cfg = default_cfg(**CHOICE, **rld, **ENVS[env], **SENS[sk])
        cfg["Re"] = [(R, C), zscale(R, C, m2 * M), (R, C)]
        o, _, _ = loop(cfg)
        pm = o["pm"] if o["pm"] is not None else -999.0
        gm = o["gm"] if o["gm"] is not None else 999.0
        if pm < worst["pm"]:
            worst.update(pm=pm, fc=o["fc"], case=f"{key(R, C)} {env} E2{m2:+d} {sk}")
        worst["gm"] = min(worst["gm"], gm)
    o_nom, _, _ = loop(default_cfg(**CHOICE, **rld, Re=[(1e6, 10e-9)] * 3, **ENVS["typical"]))
    row = dict(rld=rld, pm_worst=worst, nominal=o_nom, stable=bool(worst["pm"] >= 50 and worst["gm"] >= 10))
    if row["stable"]:
        dmg = {}
        for R, C in GRID:
            dms = [dm50(mismatch_cfg(R, C, s_, m2, default_cfg(**CHOICE, **rld, **ENVS["typical"])))[0]
                   for s_, m2 in itertools.product((1, -1), (1, -1))]
            dmg[key(R, C)] = max(dms)
        row["dm50"] = dmg
        row["dm50_worst"] = max(dmg.values())
    RES["stage2"].append(row)
    print(f"REXT {('DNP' if not rext else f'{rext/1e6:g}M'):>4s} CEXT {cext*1e12:5.0f}p Rz {rz/1e3:5.0f}k | "
          f"|T50| {o_nom['T50']:6.1f} fc {o_nom['fc'] or 0:7.0f} PMnom {o_nom['pm'] or -999:6.1f} | "
          f"PMworst {worst['pm']:6.1f} GMworst {worst['gm']:5.1f} @ {worst['case']}" +
          (f" | dm50 worst {row['dm50_worst']:6.2f} µV" if row["stable"] else " | rejected"), flush=True)
    (HERE / "results" / "sim07_sweep.json").write_text(json.dumps(RES, indent=1))

ok = [r for r in RES["stage2"] if r["stable"] and r["pm_worst"]["pm"] >= PM_SCREEN and r["pm_worst"]["gm"] >= GM_SCREEN]
alt = min((r for r in RES["stage2"] if r["stable"]), key=lambda r: r["dm50_worst"])
RES["stage2_alt_50deg_screen"] = dict(alt["rld"], dm50_worst=alt["dm50_worst"], pm_worst=alt["pm_worst"])
best_dm = min(r["dm50_worst"] for r in ok)
tied = [r for r in ok if r["dm50_worst"] <= best_dm * 1.03]
pick = max(tied, key=lambda r: r["pm_worst"]["pm"])
RES["stage2_choice"] = dict(pick["rld"], dm50_worst=pick["dm50_worst"], pm_worst=pick["pm_worst"],
                            rule=f"min worst-case 50 Hz DM among PM ≥ {PM_SCREEN:g}°, GM ≥ {GM_SCREEN:g} dB; ties within 3 % -> larger PM")
agree = all(abs(pick["rld"][k] - FINAL[k]) <= 1e-15 + 1e-6 * abs(FINAL[k]) for k in ("rext", "cext", "rz"))
RES["stage2_choice"]["agrees_with_designs_FINAL"] = bool(agree)
print(f"stage 2 choice: {pick['rld']} worst dm50 {pick['dm50_worst']:.2f} µV, worst PM {pick['pm_worst']['pm']:.1f}°"
      f" -> {'matches' if agree else 'DIFFERS FROM'} lib/designs.py FINAL", flush=True)
print(f"stage 2 done {time.time()-t0:.0f} s")
(HERE / "results" / "sim07_sweep.json").write_text(json.dumps(RES, indent=1))
