"""SIM-07 verification of the chosen input network against the ARCHITECTURE.md criteria, with the same checks on the
initial (ARCH §3.3) network so both are reported. Designs come from lib/designs.py.

Checks
  A  signal attenuation 0.5-40 Hz, electrode grid, lead-off off (Rin 1000 MΩ) and on (500 MΩ)   crit < 1 %
  B  50 Hz CM->DM with ±50 % electrode mismatch (+ component tolerances), typical and harsh environment
                                       crit < AFE noise floor (SBAS502C Table 2/3, 500 SPS: G4 1.1, G6 0.9 µVrms)
  C  RLD loop phase margin, worst case over grid × env × E2 ±50 % × 6 model sensitivities         crit ≥ 45°
  D  DC offset vs full scale for gain 3/4/6, Eq. 5 common-mode window, RLDOUT swing
  E  lead-off: detection vs TVS leakage for each current / COMP_TH, false-alarm margin with electrodes on
  F  noise budget 0.5-40 Hz (ngspice .noise + shot noise + ADS Table 2)       target ARCH M2 ≤ 10 µVpp
  G  RF estimate at 2.4 GHz: what C_CM would add (informational)
Writes results/sim07.json and plots/sim07_*.png.  Run time ≈ 6-8 min.
"""
import json, itertools, math, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sim07_common import (S, GRID, ENVS, M, default_cfg, mismatch_cfg, signal_att, dm50, loop, zscale,
                          netlist, dc_point, V, HERE, INITIAL, FINAL, FINAL_REXT)
from designs import EXTREF

t0 = time.time()
(HERE / "plots").mkdir(exist_ok=True)
DESIGNS = {"initial": (INITIAL, 6), "final": (FINAL, 4), "final+REXT10M": (FINAL_REXT, 4), "extref(rejected)": (EXTREF, 4)}
NOISE_FLOOR = {g: V("ads_noise_500sps")[g][0] for g in (3, 4, 6, 8)}       # µVrms at 500 SPS
R = {"designs": {k: dict(net={kk: (list(vv) if isinstance(vv, tuple) else vv) for kk, vv in v[0].items()}, gain=v[1])
                 for k, v in DESIGNS.items()}, "noise_floor_uVrms": NOISE_FLOOR}
key = lambda Rr, C: f"{Rr/1e6:g}M_{C*1e9:g}n"
VERDICT = {}

# ============================================================================== A  attenuation
A = {}
for dn in ("initial", "final"):
    net, g = DESIGNS[dn]
    A[dn] = {}
    for loff, rin in (("off", V("ads_rin")), ("on", V("ads_rin_loff"))):
        row = {}
        for Rr, C in GRID:
            worst = 0.0
            for pat in ("matched", 1, -1):
                cfg = default_cfg(**net, Rin=rin, **ENVS["typical"])
                if pat == "matched": cfg["Re"] = [(Rr, C)] * 3
                else: cfg = mismatch_cfg(Rr, C, pat, 0, cfg)
                worst = max(worst, signal_att(cfg)[0])
            row[key(Rr, C)] = worst
        A[dn][loff] = row
    print(f"A {dn:14s} off " + " ".join(f"{v*100:5.2f}" for v in A[dn]["off"].values()) +
          " | on " + " ".join(f"{v*100:5.2f}" for v in A[dn]["on"].values()), flush=True)
# floor: no board capacitance at all (no TVS, no routing, no C_CM/C_DIFF): what the ADS1291 input alone costs
floor = {}
for Rr, C in GRID:
    cfg = default_cfg(**FINAL, Rin=V("ads_rin_loff"), **ENVS["typical"]); cfg["Re"] = [(Rr, C)] * 3
    cfg["Ctvs"] = [1e-18] * 3; cfg["Croute"] = [1e-18] * 2
    floor[key(Rr, C)] = signal_att(cfg)[0]
print("A floor (ADS1291 input only, lead-off on) %:", {k: round(v * 100, 2) for k, v in floor.items()}, flush=True)
# largest electrode resistance that still meets < 1 % (C 1-100 nF), final design
rmax = {}
for loff, rin in (("off", V("ads_rin")), ("on", V("ads_rin_loff"))):
    rmax[loff] = {}
    for C in (1e-9, 10e-9, 100e-9):
        best = 0
        for Rr in np.logspace(5, 7, 41):
            cfg = default_cfg(**FINAL, Rin=rin, **ENVS["typical"]); cfg["Re"] = [(Rr, C)] * 3
            if signal_att(cfg)[0] < 0.01: best = Rr
            else: break
        rmax[loff][f"{C*1e9:g}n"] = best
R["A_attenuation"] = dict(worst_over_band=A, floor_ads_input_only=floor, rmax_for_1pct=rmax, crit="< 1 % over 0.5-40 Hz")
VERDICT["A_attenuation"] = {dn: {k: bool(max(A[dn]["off"][k], A[dn]["on"][k]) < 0.01) for k in A[dn]["on"]} for dn in A}
print("A Rmax for <1 % (final):", {k: {c: f'{r/1e6:.2f}M' for c, r in v.items()} for k, v in rmax.items()}, flush=True)
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for Rr, C in [(0.1e6, 100e-9), (1e6, 10e-9), (1e6, 1e-9), (10e6, 10e-9), (10e6, 1e-9)]:
    for dn, ls in (("final", "-"), ("initial", ":")):
        cfg = default_cfg(**DESIGNS[dn][0], Rin=V("ads_rin_loff"), **ENVS["typical"]); cfg["Re"] = [(Rr, C)] * 3
        S.run(netlist(dict(cfg, vecg_ac=1.0), ".ac dec 30 0.1 1000"))
        f = S.vec("frequency").real; H = S.vec("inp") - S.vec("inn")
        l = ax[0].semilogx(f, 100 * (1 - abs(H)), ls, label=f"{dn} {key(Rr, C)}")[0]
        ax[1].semilogx(f, np.degrees(np.angle(H)), ls, color=l.get_color())
ax[0].axhline(1, color="k", lw=0.8); ax[0].axvspan(0.5, 40, color="0.92")
ax[0].set_ylabel("attenuation 1-|H| (%)"); ax[0].set_ylim(-0.5, 25); ax[0].legend(fontsize=6)
ax[1].set_ylabel("phase (deg)"); [a.set_xlabel("Hz") for a in ax]
fig.suptitle("SIM-07 A: Lead-I signal, body -> ADS1291 pins (lead-off on, Rin 500 MΩ)"); fig.tight_layout()
fig.savefig(HERE / "plots" / "sim07_A_attenuation.png", dpi=110); plt.close(fig)

# ============================================================================== B  50 Hz
B = {}
for dn, (net, g) in DESIGNS.items():
    B[dn] = {}
    for env in ENVS:
        row = {}
        for Rr, C in GRID:
            vals = [dm50(mismatch_cfg(Rr, C, s_, m2, default_cfg(**net, Rin=V("ads_rin_loff"), **ENVS[env])))
                    for s_, m2 in itertools.product((1, -1), (1, -1))]
            w = max(vals, key=lambda x: x[0])
            row[key(Rr, C)] = dict(dm_uVrms=w[0], cm_pins_mVrms=w[1], v_body_Vrms=w[2])
        B[dn][env] = row
        print(f"B {dn:14s} {env:8s} DM µVrms " + " ".join(f"{v['dm_uVrms']:7.2f}" for v in row.values()), flush=True)
# body-internal floor: identical electrodes and parts; only the arm resistance carries the RLD/supply current
fl = {}
for env in ENVS:
    cfg = default_cfg(**FINAL, Rin=V("ads_rin_loff"), **ENVS[env]); cfg["Re"] = [(0.1e6, 100e-9)] * 3
    fl[env] = dm50(cfg)[0]
R["B_50Hz"] = dict(dm=B, floor_matched_parts=fl, crit_uVrms=NOISE_FLOOR,
                   note="DM = worst of 4 mismatch patterns + CM/CMRR_min; floor = DM with identical electrodes (I_sup × R_arm)")
VERDICT["B_50Hz"] = {dn: {env: {k: bool(v["dm_uVrms"] < NOISE_FLOOR[DESIGNS[dn][1]]) for k, v in B[dn][env].items()}
                          for env in ENVS} for dn in B}
print("B floor (identical electrodes):", {k: round(v, 2) for k, v in fl.items()}, flush=True)

# ============================================================================== C  RLD loop
SENS = {"nominal": {}, "pga_bw_50k": dict(pga_bw=50e3), "pga_bw_20k": dict(pga_bw=20e3), "a0_80dB": dict(a0=1e4),
        "gbw_70k": dict(gbw=70e3), "cinv_10p": dict(extra="Cinv rldinv dg 10p")}
C_ = {}
# the sweep's runner-up (best 50 Hz DM under a 50° screen) is re-checked here to show why the 60° screen was used
CDES = {k: v for k, v in DESIGNS.items() if not k.startswith("extref")}      # RLDREF does not enter the loop gain
CDES["alt_cext100p"] = (dict(FINAL, cext=100e-12), 4)
for dn, (net, g) in CDES.items():
    worst = dict(pm=999)
    allpm, allgm = [], []
    for (Rr, C), env, m2, sk in itertools.product(GRID, ENVS, (1, -1), SENS):
        cfg = default_cfg(**net, **ENVS[env], **SENS[sk]); cfg["Re"] = [(Rr, C), zscale(Rr, C, m2 * M), (Rr, C)]
        o, _, _ = loop(cfg)
        pm = o["pm"] if o["pm"] is not None else -999
        allpm.append(pm); allgm.append(o["gm"] if o["gm"] is not None else 999)
        if pm < worst["pm"]:
            worst = dict(pm=pm, fc=o["fc"], gm=o["gm"], T50=o["T50"], case=f"{key(Rr, C)} {env} E2{m2:+d} {sk}")
    nom, f, T = loop(default_cfg(**net, Re=[(1e6, 10e-9)] * 3, **ENVS["typical"]))
    C_[dn] = dict(nominal=nom, worst=worst, n_cases=len(allpm), pm_min=min(allpm), gm_min=min(allgm),
                  pm_median=float(np.median(allpm)))
    print(f"C {dn:14s} nominal fc {nom['fc']:.0f} Hz PM {nom['pm']:.1f}° GM {nom['gm']} |T50| {nom['T50']:.1f}; "
          f"worst PM {worst['pm']:.1f}° @ {worst['case']}, worst GM {min(allgm):.1f} dB ({len(allpm)} cases)", flush=True)
R["C_rld_loop"] = dict(results=C_, sensitivities=list(SENS), crit="PM ≥ 45°",
                       rld_amp=dict(gbw_hz=V("rld_gbw"), src="SBAS502C p8"))
VERDICT["C_rld_pm"] = {dn: bool(v["pm_min"] >= 45) for dn, v in C_.items()}
fig, ax = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
for dn in ("initial", "final"):
    for Rr, C in [(0.1e6, 100e-9), (1e6, 10e-9), (10e6, 1e-9)]:
        o, f, T = loop(default_cfg(**DESIGNS[dn][0], Re=[(Rr, C)] * 3, **ENVS["typical"]))
        l = ax[0].semilogx(f, 20 * np.log10(abs(T)), "-" if dn == "final" else ":", label=f"{dn} {key(Rr, C)} PM {o['pm']:.0f}°")[0]
        ax[1].semilogx(f, np.degrees(np.unwrap(np.angle(T))), "-" if dn == "final" else ":", color=l.get_color())
ax[0].axhline(0, color="k", lw=0.8); ax[1].axhline(-135, color="r", lw=0.8)
ax[0].set_ylabel("|T| (dB)"); ax[1].set_ylabel("∠T (deg)"); ax[1].set_xlabel("Hz"); ax[0].legend(fontsize=7)
ax[0].set_ylim(-60, 100); ax[1].set_ylim(-270, 30)
fig.suptitle("SIM-07 C: RLD loop gain (voltage injection at RLDOUT)"); fig.tight_layout()
fig.savefig(HERE / "plots" / "sim07_C_rld_loop.png", dpi=110); plt.close(fig)


# ============================================================================== D  DC operating point
def op(cfg):
    o = dc_point(cfg)
    return dict(vdm=o["inp"] - o["inn"], cm=(o["inp"] + o["inn"]) / 2, rld=o["rldout"], i=o["i"], how=o["how"],
                inp=o["inp"], inn=o["inn"])


D = {}
VR = V("ads_vref") * (1 - 0.005)                         # VREF accuracy ±0.5 % (SBAS502C p9)
REFS = {"final": ["int"], "initial": ["int"]}
PIN = {}                                                  # pin voltage envelope with electrodes on (for E)
for dn in ("final", "initial"):
    net = DESIGNS[dn][0]
    for loff_name, iloff in (("none", 0.0), ("6nA", 6e-9), ("22nA", 22e-9)):
        for tvs_name, itvs in (("typ", V("i_tvs_leak_typ")), ("wc", V("i_tvs_leak_wc"))):
            if dn != "final" and tvs_name == "typ":
                continue
            res = {}
            for Rr in (0.1e6, 1e6, 3e6, 10e6):
                worst, rl, cm, how, pins = None, [], [], [], []
                for d, e, s_, ib, rf in itertools.product((0.3, -0.3), (0.3, -0.3), (1, -1), (1, -1), REFS[dn]):
                    cfg = default_cfg(**dict(net, rldref=rf), Rin=V("ads_rin_loff") if iloff else V("ads_rin"), Iloff=iloff * 1.1)
                    cfg["Re"] = [(Rr * (1 + s_ * M), 10e-9), (Rr, 10e-9), (Rr * (1 - s_ * M), 10e-9)]
                    cfg["Vhc"] = [d / 2, e, -d / 2]
                    cfg["Itvs"] = [itvs if s_ < 0 else 0.0, 0.0, itvs if s_ > 0 else 0.0]
                    cfg["Ib"] = [ib * V("ads_ib_fullT"), -ib * V("ads_ib_fullT")]
                    o = op(cfg)
                    rl.append(o["rld"]); cm.append(o["cm"]); how.append(o["how"]); pins += [o["inp"], o["inn"]]
                    if worst is None or abs(o["vdm"]) > abs(worst["vdm"]): worst = dict(o, case=dict(d=d, e=e, s=s_, ib=ib))
                vd = abs(worst["vdm"]) + 5e-3                     # + 5 mV for ECG and motion
                fit = {}
                for g in (3, 4, 6):
                    fs_ok = vd <= VR / g
                    eq5 = (V("avdd") - 0.2 - g * vd / 2 > max(cm)) and (min(cm) > 0.2 + g * vd / 2)
                    fit[g] = dict(fs_ok=bool(fs_ok), eq5_ok=bool(eq5), fs=VR / g, ok=bool(fs_ok and eq5))
                res[f"{Rr/1e6:g}M"] = dict(vdm_worst=worst["vdm"], cm=(min(cm), max(cm)), rldout=(min(rl), max(rl)),
                                           pin_range=(min(pins), max(pins)), gains=fit, case=worst["case"],
                                           solved_by=sorted(set(how)))
                PIN[(dn, loff_name, tvs_name, Rr)] = (min(pins), max(pins))
            D[f"{dn}|loff_{loff_name}|tvs_{tvs_name}"] = res
            print(f"D {dn:12s} lead-off {loff_name:4s} TVS {tvs_name:3s} |Vdm| mV " +
                  " ".join(f"{k}:{abs(v['vdm_worst'])*1e3:6.1f}" for k, v in res.items()) + " | G4 " +
                  " ".join(f"{k}:{'Y' if v['gains'][4]['ok'] else 'n'}" for k, v in res.items()) + " | G6 " +
                  " ".join(f"{k}:{'Y' if v['gains'][6]['ok'] else 'n'}" for k, v in res.items()) +
                  " | RLDOUT " + " ".join(f"{v['rldout'][0]:.2f}-{v['rldout'][1]:.2f}" for v in res.values()), flush=True)
R["D_dc"] = dict(results=D, vref_min=VR, signal_headroom_V=5e-3,
                 note="half-cell: E1-E3 = ±300 mV and E2 vs mean(E1,E3) = ±300 mV; electrodes ±50 %; lead-off +10 %; "
                      "TVS leakage on one input only; bias ±1 nA (full temperature)")
VERDICT["D_dc"] = {k: {r: {g: x["ok"] for g, x in v["gains"].items()} for r, v in res.items()} for k, res in D.items()}

# ============================================================================== E  lead-off
E = {}
TH = V("loff_comp_th")
for iname, i0 in (("6nA", 6e-9), ("22nA", 22e-9)):
    E[iname] = {}
    # E1 (IN1P, source side) lifted: IN1P must rise above the positive threshold against the TVS leakage
    # (TVS modelled as a resistance to AVSS that leaks the stated current at 1.5 V) with the source at -10 %.
    vin = {}
    for itvs in np.logspace(-11, -7, 41):
        cfg = default_cfg(**FINAL, Rin=V("ads_rin_loff"), Iloff=i0 * 0.9)
        cfg["Re"] = [(1e12, 1e-15), (1e6, 10e-9), (1e6, 10e-9)]
        cfg["extra"] = f"Rtl1 e1 dg {1.5 / itvs}"
        o = op(cfg)
        vin[float(itvs)] = (o["inp"], o["inn"])
    # E3 (IN1N, sink side) lifted: IN1N must fall below the negative threshold; TVS leakage helps here, the
    # ADS input impedance to mid-supply works against it
    cfg = default_cfg(**FINAL, Rin=V("ads_rin_loff"), Iloff=i0 * 0.9)
    cfg["Re"] = [(1e6, 10e-9), (1e6, 10e-9), (1e12, 1e-15)]
    o3 = op(cfg)
    for k, (tp, tn) in enumerate(zip(TH["pos"], TH["neg"])):
        vth = tp * V("avdd")
        ok = [i for i, (p_, n_) in vin.items() if p_ >= vth]
        lim = max(ok) if ok else 0.0
        # false-alarm margin with electrodes on: worst pin excursion from D (10 MΩ, worst TVS, this current)
        lo, hi = PIN[("final", iname, "wc", 10e6)]
        lo1, hi1 = PIN[("final", iname, "wc", 1e6)]
        E[iname][f"COMP_TH {int(tp*100)}/{int(tn*100)} %"] = dict(
            vth_pos=vth, vth_neg=tn * V("avdd"), max_tvs_leak_1V5_for_E1_detect=lim,
            e3_off_inn=o3["inn"], e3_detected=bool(o3["inn"] <= tn * V("avdd")),
            false_alarm_margin_10M_V=float(min(vth - hi, lo - tn * V("avdd"))),
            false_alarm_margin_1M_V=float(min(vth - hi1, lo1 - tn * V("avdd"))))
    best = max(E[iname].items(), key=lambda kv: kv[1]["max_tvs_leak_1V5_for_E1_detect"] if kv[1]["false_alarm_margin_10M_V"] > 0.1 else -1)
    print(f"E lead-off {iname}: " + "; ".join(f"{k}: E1 needs TVS ≤ {v['max_tvs_leak_1V5_for_E1_detect']*1e9:.2f} nA, "
                                             f"E3 {'Y' if v['e3_detected'] else 'n'}, margin(10M) {v['false_alarm_margin_10M_V']:+.2f} V"
                                             for k, v in E[iname].items()) + f" | best: {best[0]}", flush=True)
R["E_leadoff"] = dict(detection=E, settings=V("ileadoff"),
                      tvs_leak_spec="TPD1E10B06 100 nA max at 5 V (SLLSEB1G p5), no typical value and no low-voltage curve",
                      patient_current_note="the forbidden 6 µA/22 µA settings would deliver ≤ 2.8 µA through the 2 × 330 kΩ "
                                           "chain (sim07_faults.py), so a corrupted LOFF register is not a shock hazard")

# ============================================================================== F  noise
k = 1.380649e-23 * 310
q = 1.602e-19
F = {}
for Rr, C in GRID:
    row = {}
    for iname, il in (("6nA", 6e-9), ("22nA", 22e-9)):
        cfg = default_cfg(**FINAL, Rin=V("ads_rin_loff")); cfg["Re"] = [(Rr, C)] * 3
        S.run(netlist(dict(cfg, vecg_ac=1.0), ".noise v(inp,inn) Vecg dec 40 0.5 40"))
        S.cmd("setplot noise1")
        f = S.vec("frequency").real; on = np.abs(S.vec("onoise_spectrum"))
        th = math.sqrt(np.trapezoid(on ** 2, f))
        z = abs(Rr / (1 + 2j * math.pi * f * Rr * C))
        shot_tvs = math.sqrt(np.trapezoid(2 * 2 * q * V("i_tvs_leak_typ") * z ** 2, f))
        shot_tvs_wc = math.sqrt(np.trapezoid(2 * 2 * q * V("i_tvs_leak_wc") * z ** 2, f))
        shot_loff = math.sqrt(np.trapezoid(2 * 2 * q * il * (z + 660e3) ** 2, f))
        ads = NOISE_FLOOR[4] * math.sqrt((40 - 0.5) / 131) * 1e-6
        tot = math.sqrt(th ** 2 + shot_tvs ** 2 + shot_loff ** 2 + ads ** 2)
        tot_wc = math.sqrt(th ** 2 + shot_tvs_wc ** 2 + shot_loff ** 2 + ads ** 2)
        row[iname] = dict(thermal_uV=th * 1e6, tvs_shot_typ_uV=shot_tvs * 1e6, tvs_shot_wc_uV=shot_tvs_wc * 1e6,
                          leadoff_shot_uV=shot_loff * 1e6, ads_uV=ads * 1e6, total_uVrms=tot * 1e6,
                          total_wc_uVrms=tot_wc * 1e6, total_uVpp=tot * 1e6 * 6.6, total_wc_uVpp=tot_wc * 1e6 * 6.6)
    F[key(Rr, C)] = row
    r6 = row["6nA"]
    print(f"F {key(Rr, C):9s} thermal {r6['thermal_uV']:5.2f} TVS {r6['tvs_shot_typ_uV']:5.2f}/{r6['tvs_shot_wc_uV']:5.2f} "
          f"loff6 {r6['leadoff_shot_uV']:5.2f} loff22 {row['22nA']['leadoff_shot_uV']:5.2f} ADS {r6['ads_uV']:4.2f} -> "
          f"{r6['total_uVrms']:5.2f} µVrms ({r6['total_uVpp']:5.1f} µVpp; wc TVS {r6['total_wc_uVpp']:5.1f}; 22 nA {row['22nA']['total_uVpp']:5.1f})", flush=True)
R["F_noise"] = dict(results=F, target="ARCH M2 ≤ 10 µVpp over 0.5-40 Hz (bench: input short); pp ≈ 6.6 × rms (SBAS502C p15)",
                    input_short_uVpp=NOISE_FLOOR[4] * math.sqrt((40 - 0.5) / 131) * 6.6,
                    note="thermal = ngspice .noise of electrodes (real part), 2×330 kΩ, model resistors; shot noise of TVS "
                         "leakage and lead-off current added analytically (both inputs); ADS Table 2 G4 scaled to 39.5 Hz")

# ============================================================================== G  RF estimate
G = {}
rf = """* RF path electrode pad -> ADS1291 pin at 2.4 GHz (lumped, estimate)
Vs src 0 AC 1
Rs src pad 50
Ltv pad tv1 0.4n
Ctv tv1 tv2 {ctvs}
Rtv tv2 0 0.3
Lr1 pad r1a 0.5n
Rr1 r1a mid 330k
Cr1 r1a mid 0.05p
Lr2 mid r2a 0.5n
Rr2 r2a pin 330k
Cr2 r2a pin 0.05p
Crt pin 0 2p
{ccm}
Lbw pin pinint 1n
Cpad pinint 0 3p
Remi pinint core 2.65k
Cin core 0 17p
Rin core 0 1G
.ac dec 1000 1e6 6e9
.end"""
for ccm in (0, 4.7e-12, 10e-12, 22e-12):
    cc = f"Lcm pin cm1 0.4n\nRcm cm1 cm2 0.2\nCcm cm2 0 {ccm}" if ccm else ""
    S.run(rf.format(ctvs=V("c_tvs"), ccm=cc))
    f = S.vec("frequency").real; vin = abs(S.vec("core"))
    G[f"{ccm*1e12:g}pF"] = {f"{fx/1e6:g}MHz": float(20 * np.log10(np.interp(fx, f, vin))) for fx in (10e6, 100e6, 900e6, 2.44e9)}
    G[f"{ccm*1e12:g}pF"]["worst_2.40-2.48GHz"] = float(20 * np.log10(vin[(f >= 2.40e9) & (f <= 2.48e9)].max()))
print("G RF pad->internal node (dB):", {k: {kk: round(vv, 1) for kk, vv in v.items()} for k, v in G.items()}, flush=True)
R["G_rf"] = dict(results=G, note="estimate: 0603 R parasitic 0.05 pF + 0.5 nH, TVS ESL 0.4 nH, C_CM ESL 0.4 nH + ESR 0.2 Ω, "
                                 "pin lead 1 nH, ESD pad 3 pF, internal EMI RC 2.65 kΩ/17 pF (≈3 MHz, SBAS502C p19); source 50 Ω. "
                                 "Differences between rows are what C_CM buys; values near C_CM self-resonance are not robust.")

R["verdict"] = VERDICT
(HERE / "results" / "sim07.json").write_text(json.dumps(R, indent=1, default=float))
print(f"done {time.time()-t0:.0f} s")
