"""SIM-06 (ECG part): harvester ripple and MPPT steps -> VSTOR -> TPS7A02 PSRR -> AVDD_ECG -> ADS1291 -> input-referred.

Paths from AVDD to the ECG input that are evaluated (SIM-07 network, gain 4), for three designs (lib/designs.py):
  'intref' = FINAL network, internal RLDREF, U3 = TPS7A0230 (ARCH as frozen; the 'before' case)
  'extref' = same with RLDREF from AVDD by 2 × 10 MΩ + 1 µF (first change candidate; rejected, see README)
  'final'  = FINAL network, internal RLDREF, U3 = TPS7A2030 (drop-in low-noise LDO; the adopted change)
  P1  direct ADS1291 PSRR                        (SBAS502C p13 Fig 8, digitised; > 1 kHz extrapolated, E)
  P2  RLDREF -> RLD loop -> body CM -> electrode-mismatch CM->DM                       (ngspice AC, frontend)
  P3  ADS1291 input impedance (SBAS502C p7 gives magnitudes only, so three bounds, ngspice AC):
      'asym' nA lead-off source/sink impedance to AVDD/AVSS + 1000 MΩ to mid (pessimistic), 'mid' 500 MΩ to AVDD/2,
      'avss' 500 MΩ to AVSS (no AVDD path, optimistic)
Sources on AVDD:
  S1  harvester/load disturbances on VSTOR (ngspice transient of the cell/shunt/PFET/MLCC network with an averaged
      charger, MPPT 256 ms sampling gap, BLE connection events, optional PPG pulses) × LDO PSRR
      (TPS7A0230: SBVS277C p15 Fig 6-43; TPS7A2030: SBVS338H p18 Fig 5-63)
  S2  LDO intrinsic output noise (TPS7A0230 Fig 6-48 ×3.0/1.8; TPS7A2030 Fig 5-65 ×3.0/2.8)
  S3  switching ripple (boost DCM pulses, buck bursts) at 10-130 kHz: aliasing bound at the ΔΣ modulator (fMOD 128 kHz)
  S4  DVDD (VDD_1V8 buck ripple, SLUSBH2G p8/p12): ADS1291 gives no DVDD rejection -> required rejection reported
Composition: the front end is linear, so input-referred(f) = VSTOR(f)·|H_LDO(f)|·|H_AVDD->DM(f)| (band RMS exact by
Parseval); a whole-chain ngspice AC run (VSTOR -> s_xfer LDO fit -> front end) cross-checks the plumbing.
Criterion (ARCH SIM-06): input-referred < 1 µVrms over 0.5-40 Hz from supply coupling, harvester running.
Writes results/sim06_supply.json, plots/sim06_supply_*.png.  Run time ≈ 10 min.
"""
import json, math, time, sys, pathlib, itertools
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import least_squares
from scipy.signal import butter, sosfiltfilt
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib")); sys.path.insert(0, str(HERE))
from sim07_common import S, GRID, ENVS, M, default_cfg, mismatch_cfg, netlist, V, P     # noqa: E402
from curves import ldo_psrr_db, ldo_noise, ads_psrr_db, ln_ldo_psrr_db, ln_ldo_noise   # noqa: E402
from designs import FINAL, EXTREF                                                      # noqa: E402

t0 = time.time()
GAIN = 4
DES = {"intref": FINAL, "extref": EXTREF, "final": FINAL}
LDOF = {"intref": (ldo_psrr_db, ldo_noise), "extref": (ldo_psrr_db, ldo_noise), "final": (ln_ldo_psrr_db, ln_ldo_noise)}
LDON = {"intref": "TPS7A0230", "extref": "TPS7A0230", "final": "TPS7A2030"}
R = {"gain": GAIN, "ldo": LDON,
     "networks": {k: {kk: (list(vv) if isinstance(vv, tuple) else vv) for kk, vv in v.items()} for k, v in DES.items()}}
FB = (0.5, 40.0)
CRIT = 1.0e-6

# ============================================================================================ 0  LDO PSRR s-domain fit
fz = np.logspace(0, 6.5, 140)
target = -ldo_psrr_db(fz)                                  # dB of |H| = |ΔAVDD/ΔVSTOR|
W0 = 2 * math.pi * 1e3


def hfit(x, f):
    k, z1, z2, p1, p2, p3 = 10 ** np.asarray(x)
    s = 2j * math.pi * f
    return k * (1 + s / z1) * (1 + s / z2) / ((1 + s / p1) * (1 + s / p2) * (1 + s / p3))


res = least_squares(lambda x: 20 * np.log10(np.abs(hfit(x, fz))) - target,
                    x0=np.log10([5e-3, 2 * math.pi * 3e3, 2 * math.pi * 3e5, 2 * math.pi * 1.5e4, 2 * math.pi * 3e4, 2 * math.pi * 2e5]))
XF = res.x
err = 20 * np.log10(np.abs(hfit(XF, fz))) - target
k, z1, z2, p1, p2, p3 = 10 ** XF
# s_xfer coefficients in descending powers of s/W0
num = np.polymul([W0 / z1, 1], [W0 / z2, 1]) * k
den = np.polymul(np.polymul([W0 / p1, 1], [W0 / p2, 1]), [W0 / p3, 1])
R["ldo_fit"] = dict(k=k, zeros_hz=[z1 / 2 / math.pi, z2 / 2 / math.pi], poles_hz=[p / 2 / math.pi for p in (p1, p2, p3)],
                    max_abs_err_db=float(np.abs(err).max()), max_err_db_0p5_40Hz=float(np.abs(err[fz <= 40]).max()),
                    note="fitted to min(0 mA, 1 mA) of Fig 6-43 minus 6 dB headroom derate; used only by the cross-check transient")
print(f"LDO PSRR fit: max |err| {np.abs(err).max():.2f} dB (1 Hz-3 MHz), in band {np.abs(err[fz<=40]).max():.2f} dB")
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.semilogx(fz, -target, "k", lw=2, label="design curve: worst of Fig 6-43 0/1 mA, -6 dB")
ax.semilogx(fz, -20 * np.log10(np.abs(hfit(XF, fz))), "r--", label="s_xfer fit")
ax.set_xlabel("Hz"); ax.set_ylabel("PSRR dB"); ax.legend(fontsize=8); ax.grid(True, which="both", lw=0.3)
ax.set_title("TPS7A0230 PSRR used in SIM-06"); fig.tight_layout(); fig.savefig(HERE / "plots" / "sim06_supply_ldo_fit.png", dpi=110); plt.close(fig)
# the two regulators side by side (design curves as used, including the stated extrapolations)
fq = np.logspace(np.log10(0.5), 6, 300)
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
ax[0].loglog(fq, ldo_noise(fq) * 1e6, "r", label="TPS7A0230 (SBVS277C Fig 6-48 max of 0.1/1 mA, ×3.0/1.8)")
ax[0].loglog(fq, ln_ldo_noise(fq) * 1e6, "b", label="TPS7A2030 (SBVS338H Fig 5-65 1 mA, ×3.0/2.8)")
ax[0].axvspan(0.5, 10, color="0.9", label="below the vendor plots: f^-0.5 extrapolation (E)")
ax[0].axvspan(0.5, 40, color="0.95"); ax[0].set_ylabel("AVDD noise µV/√Hz"); ax[0].legend(fontsize=7)
ax[1].semilogx(fq, ldo_psrr_db(fq), "r", label="TPS7A0230: worst 0/1 mA − 6 dB")
ax[1].semilogx(fq, ln_ldo_psrr_db(fq), "b", label="TPS7A2030: lower envelope 0.01/20 mA")
ax[1].set_ylabel("PSRR dB"); ax[1].legend(fontsize=7)
for a_ in ax: a_.set_xlabel("Hz"); a_.grid(True, which="both", lw=0.3)
fig.suptitle("SIM-06: AVDD_ECG regulator, as frozen (red) and proposed drop-in (blue)"); fig.tight_layout()
fig.savefig(HERE / "plots" / "sim06_supply_ldo_compare.png", dpi=110); plt.close(fig)


# ============================================================================================ 1  VSTOR disturbances
def vstor_net(case, rcell, rpfet, vocv, t_end, mppt_at=None, tstep=1e-4):
    der = V("mlcc_dcbias")
    L = ["* VSTOR network", f"Vocv bo 0 DC {vocv}", f"Rcell bo b1 {rcell}", f"Rpcm b1 b2 {V('r_pcm')}",
         f"Rsh2 b2 vbat {V('rsh2')}", f"Cbat vbat cb {V('cbat') * der}", "Rcb cb 0 5m",
         f"Rpfet vbat vstor {rpfet}", f"Cstor vstor cs {V('cstor') * der}", "Rcs cs 0 5m", f"Cldo vstor 0 {1e-6 * der}",
         f"Iavdd vstor 0 DC {V('i_ads_avdd')}"]
    ich = case.get("ichg", 0.0)
    if case.get("bursts"):                       # low light: one 230 mA-peak DCM pulse per burst (triangle ≈ 115 mA × 3.44 µs)
        q = 0.5 * V("bq_ichg_cbc")[0] * V("l1") * V("bq_ichg_cbc")[0] / (3.7 - V("v_mpp"))
        tw = q / 0.115
        L.append(f"Ich 0 vstor PULSE(0 0.115 1m 0.1u 0.1u {tw} {q / ich})")
    elif ich > 0:
        if mppt_at is not None:
            L.append(f"Ich 0 vstor PWL(0 {ich} {mppt_at} {ich} {mppt_at + 5e-6} 0 {mppt_at + 0.256} 0 {mppt_at + 0.256 + 5e-6} {ich})")
        else:
            L.append(f"Ich 0 vstor DC {ich}")
    # buck input current: VDD_1V8 load × 1.8 / (η·VSTOR); BLE connection events as a pulse train
    L.append(f"Vble ble 0 PULSE(0 {V('i_ble_peak')} 2m 20u 20u {V('t_ble_evt')} {V('t_conn')})")
    L.append(f"Bbuck vstor 0 I = ({V('i_sys_base')} + V(ble)) * 1.8 / ({V('eta_buck')} * max(V(vstor), 2.5))")
    if case.get("ppg"):
        L.append(f"Vppg ppg 0 PULSE(0 {case['ppg']} 3m 1u 1u 117u 40m)")
        L.append(f"Bppg vstor 0 I = V(ppg) * {V('vled')} / ({V('eta_vled')} * max(V(vstor), 2.5))")
    L += [".options interp", f".tran {tstep} {t_end} 0 {tstep / 2}", ".end"]
    return "\n".join(L)


CASES = {
    "sun_mppt": dict(ichg=V("i_chg_sun"), desc="full sun 24.7 mA charge, one 256 ms MPPT sample, BLE 33 Hz"),
    "50klx_mppt": dict(ichg=11.1e-3, desc="50 klx wrist sun 11.1 mA, MPPT sample, BLE"),
    "1klx_bursts": dict(ichg=V("i_chg_1klx"), bursts=True, desc="1000 lx: boost bursts at ≈150 Hz, BLE"),
    "dark": dict(ichg=0.0, desc="harvester idle (W-C reference), BLE only"),
    "sun_mppt_ppg30": dict(ichg=V("i_chg_sun"), ppg=30e-3, desc="as sun_mppt plus PPG 30 mA LED pulses at 25 Hz"),
}
T_END = 16.0
WAVES = {}
for name, case in CASES.items():
    t_end = 4.0 if case.get("bursts") else T_END
    S.run(vstor_net(case, V("r_cell")[1], V("bq_rds_bat")[1], 3.70, t_end, mppt_at=8.0 if "mppt" in name else None,
                    tstep=1e-4 if not case.get("bursts") else 2e-5))
    t = S.vec("time"); v = S.vec("vstor")
    k = t > 1.0                                                    # drop the start-up second
    WAVES[name] = (t[k] - t[k][0], v[k] - v[k].mean())
    print(f"VSTOR {name:16s} p-p {np.ptp(v[k])*1e3:7.2f} mV  rms {np.std(v[k])*1e3:6.3f} mV", flush=True)
R["vstor"] = {n: dict(desc=CASES[n]["desc"], pp_mV=float(np.ptp(w[1]) * 1e3), rms_mV=float(np.std(w[1]) * 1e3)) for n, w in WAVES.items()}
R["vstor_assumptions"] = dict(r_cell=V("r_cell")[1], r_pfet=V("bq_rds_bat")[1], vocv=3.70, mlcc_derate=V("mlcc_dcbias"))


# ============================================================================================ 2  AVDD -> DM transfer
FH = np.logspace(np.log10(0.05), np.log10(5e3), 400)


def h_avdd_dm(R_, C_, rin_mode, loff, s_, des):
    cfg = mismatch_cfg(R_, C_, s_, 0, default_cfg(**DES[des], Rin=V("ads_rin_loff") if loff else V("ads_rin"),
                                                  rin_mode=rin_mode, avdd_ac=1.0, **ENVS["typical"]))
    S.run(netlist(cfg, f".ac dec 40 {FH[0]} {FH[-1]}"))
    f = S.vec("frequency").real
    return np.interp(np.log10(FH), np.log10(f), np.abs(S.vec("inp") - S.vec("inn")))


# ADS1291 input-impedance reference (datasheet gives magnitudes only, SBAS502C p7): three bounds
#   asym : lead-off nA source/sink output impedance to AVDD (IN1P) / AVSS (IN1N) + 1000 MΩ to mid   (pessimistic)
#   mid  : 500 MΩ per pin to AVDD/2                                                                  (previous run's 'sym')
#   avss : 500 MΩ per pin to AVSS: no AVDD path through the input impedance                        (optimistic)
VARIANTS = {f"{des}|{mode}": (mode, True, des) for des in DES for mode in ("asym", "mid", "avss")}
HN = {}
for vn, (mode, loff, des) in VARIANTS.items():
    for R_, C_ in GRID:
        HN[(vn, R_, C_)] = np.maximum(h_avdd_dm(R_, C_, "sym" if mode == "mid" else mode, loff, 1, des),
                                      h_avdd_dm(R_, C_, "sym" if mode == "mid" else mode, loff, -1, des))
HD = 10 ** (-ads_psrr_db(FH, GAIN) / 20)
HL = 10 ** (-ldo_psrr_db(FH) / 20)                                   # TPS7A0230 (used by the cross-check below)
HLD = {d: 10 ** (-LDOF[d][0](FH) / 20) for d in DES}


def band_rms_from_wave(t, x, H_f, H_vals):
    """rms in 0.5-40 Hz of x(t) filtered by |H(f)| (zero-phase), plus the band-passed peak"""
    dt = t[1] - t[0]
    X = np.fft.rfft(x * np.hanning(len(x)) / np.sqrt(np.mean(np.hanning(len(x)) ** 2)))
    f = np.fft.rfftfreq(len(x), dt)
    h = np.interp(np.log10(np.maximum(f, 1e-3)), np.log10(H_f), H_vals, left=H_vals[0], right=H_vals[-1])
    kb = (f >= FB[0]) & (f <= FB[1])
    Y = np.where(kb, X * h, 0)
    y = np.fft.irfft(Y, n=len(x))
    rms = math.sqrt(2 * np.sum(np.abs(Y) ** 2)) / len(x)
    return rms, float(np.max(np.abs(y)))


TABLE = {}
for (vn, R_, C_), hn in HN.items():
    key = f"{vn}|{R_/1e6:g}M_{C_*1e9:g}n"
    row = {}
    des = vn.split("|")[0]
    hl_, nfun = HLD[des], LDOF[des][1]
    # S2 LDO noise
    band = (FH >= FB[0]) & (FH <= FB[1])
    nl = nfun(FH)
    row["ldo_noise_net_uV"] = float(math.sqrt(np.trapezoid((nl * hn)[band] ** 2, FH[band])) * 1e6)
    row["ldo_noise_direct_uV"] = float(math.sqrt(np.trapezoid((nl * HD)[band] ** 2, FH[band])) * 1e6)
    nlw = np.where(FH < 10.6, nfun(np.array([10.6]))[0], nl)                  # sensitivity: white below 10.6 Hz
    row["ldo_noise_net_white_lowf_uV"] = float(math.sqrt(np.trapezoid((nlw * hn)[band] ** 2, FH[band])) * 1e6)
    # S1 harvester/load disturbances
    for cn, (t, w) in WAVES.items():
        r_net, pk_net = band_rms_from_wave(t, w, FH, hl_ * hn)
        r_dir, pk_dir = band_rms_from_wave(t, w, FH, hl_ * HD)
        row[f"{cn}_uV"] = (r_net + r_dir) * 1e6
        row[f"{cn}_peak_uV"] = (pk_net + pk_dir) * 1e6
    row["total_harvester_sun_uV"] = row["sun_mppt_uV"]
    row["total_with_ldo_noise_uV"] = math.hypot(row["sun_mppt_uV"], row["ldo_noise_net_uV"] + row["ldo_noise_direct_uV"])
    TABLE[key] = row
R["table"] = TABLE
for vn in VARIANTS:
    print(f"--- {vn}")
    for R_, C_ in GRID:
        r = TABLE[f"{vn}|{R_/1e6:g}M_{C_*1e9:g}n"]
        print(f"  {R_/1e6:4.1f}M {C_*1e9:4.0f}n  sun+MPPT {r['sun_mppt_uV']:6.3f} (pk {r['sun_mppt_peak_uV']:6.2f})  50klx {r['50klx_mppt_uV']:6.3f}  "
              f"1klx {r['1klx_bursts_uV']:6.3f}  dark {r['dark_uV']:6.3f}  +PPG {r['sun_mppt_ppg30_uV']:6.3f}  | LDO noise {r['ldo_noise_net_uV']:6.3f}  "
              f"| total {r['total_with_ldo_noise_uV']:6.3f} µVrms", flush=True)

# ============================================================================================ 3  composition cross-check
# The table multiplies magnitudes: |VSTOR(f)|·|H_LDO(f)|·|H_AVDD->DM(f)|. For an LTI chain the band RMS computed this
# way is exact (Parseval: phase does not enter |Y(f)|); only the quoted peaks ignore phase. What can still go wrong is
# the plumbing (node references, the floating ground, the LDO model inside the netlist), so one ngspice AC run of the
# whole chain – VSTOR AC source -> s_xfer LDO (fit of the TPS7A0230 design curve) -> AVDD -> front end – is compared
# with the product of the separately computed pieces at 10M‖1n +50 %, 'asym', internal RLDREF (the largest coupling).
# (The interrupted run attempted a 12 s full transient of the same chain instead; under the s_xfer code model it ran
#  for > 1 h without finishing, so it was replaced by this check.)
numc = "[" + " ".join(f"{c:.6e}" for c in num) + "]"
denc = "[" + " ".join(f"{c:.6e}" for c in den) + "]"
xcheck = {}
Rx, Cx = 10e6, 1e-9
cfg = mismatch_cfg(Rx, Cx, 1, 0, default_cfg(**FINAL, Rin=V("ads_rin_loff"), rin_mode="asym", **ENVS["typical"]))
cfg["avdd_src"] = "\n".join(["Vstac vstor dg DC 0 AC 1",
                              "aldo %vd(vstor dg) %vd(ldoo dg) ldox",
                              f".model ldox s_xfer(num_coeff={numc} den_coeff={denc} denormalized_freq={W0})",
                              "Bavdd avdd dg V = 3.0 + V(ldoo) - V(dg)"])
FX = np.array([0.5, 1, 2, 5, 10, 20, 40, 100, 1e3])
S.run(netlist(cfg, f".ac dec 40 {FH[0]} {FH[-1]}"))
fa = S.vec("frequency").real; ha = np.abs(S.vec("inp") - S.vec("inn"))
chain = np.interp(np.log10(FX), np.log10(fa), ha)
hx = np.abs(h_avdd_dm(Rx, Cx, "asym", True, 1, "intref"))
prod = np.abs(hfit(XF, FX)) * np.interp(np.log10(FX), np.log10(FH), hx)
err_db = 20 * np.log10(chain / prod)
xcheck = dict(f_hz=FX.tolist(), chain_ac=chain.tolist(), product=prod.tolist(), err_db=err_db.tolist(),
              max_abs_err_db=float(np.abs(err_db).max()))
R["cross_check"] = xcheck
print("cross-check, whole-chain AC vs product of pieces (dB):", [round(e, 3) for e in err_db], flush=True)

# ============================================================================================ 4  switching ripple, aliasing bound
# boost DCM pulses at full sun into the VSTOR network (switch level), 2 ms
q = 0.5 * V("bq_ichg_cbc")[1] * V("l1") * V("bq_ichg_cbc")[1] / (3.7 - V("v_mpp"))       # 285 mA max peak
tw = 2 * q / V("bq_ichg_cbc")[1]
fsw = V("i_chg_sun") / q
der = V("mlcc_dcbias")
hf = f"""* boost ripple
Vocv bo 0 DC 3.7
Rbat bo vbat {V('r_cell')[0] + V('r_pcm') + V('rsh2')}
Cbat vbat cb {V('cbat') * der}
Rcb cb 0 5m
Rpfet vbat vstor {V('bq_rds_bat')[0]}
Cstor vstor cs {V('cstor') * der}
Rcs cs 0 5m
Lcs cs cs2 0.5n
Cldo vstor 0 {1e-6 * der}
Ich 0 vstor PULSE(0 {V('bq_ichg_cbc')[1]} 10u 0.05u {tw} 0.05u {1 / fsw})
.tran 20n 2m 0 20n
.end"""
S.run(hf)
t = S.vec("time"); v = S.vec("vstor"); k = t > 1e-3
vpp = float(np.ptp(v[k]))
x = v[k] - v[k].mean()
X = np.abs(np.fft.rfft(x)) * 2 / len(x); f = np.fft.rfftfreq(len(x), t[1] - t[0])
harm = []
for n_ in range(1, 6):
    kk = np.argmin(np.abs(f - n_ * fsw)); harm.append((float(f[kk]), float(X[max(kk - 2, 0):kk + 3].max())))
fmod = 128e3
alias = []
for fh, a in harm:
    avdd = a * 10 ** (-ldo_psrr_db([fh])[0] / 20)
    avdd2 = a * 10 ** (-ln_ldo_psrr_db([fh])[0] / 20)
    alias.append(dict(f_hz=fh, vstor_mV=a * 1e3, avdd_uV=avdd * 1e6,
                      input_if_aliased_uV=avdd * 10 ** (-ads_psrr_db([fh], GAIN)[0] / 20) * 1e6,
                      input_if_aliased_tps7a20_uV=avdd2 * 10 ** (-ads_psrr_db([fh], GAIN)[0] / 20) * 1e6))
R["switching"] = dict(boost_f_hz=fsw, vstor_pp_mV=vpp * 1e3, harmonics=alias,
                      note="worst case: a harmonic within ±40 Hz of k·128 kHz aliases into the band unattenuated by sinc3; "
                           "ADS1291 PSRR above 1 kHz is extrapolated at -20 dB/dec (no vendor data)")
print(f"boost ripple {fsw/1e3:.1f} kHz, VSTOR {vpp*1e3:.1f} mVpp; alias bound per harmonic µV:",
      [round(a['input_if_aliased_uV'], 3) for a in alias])
# buck bursts: VDD_1V8 load ≈ 1.5 mA in an ECG session, burst ≈ 15 kHz (Fig 17/18); VSTOR draw per burst
ibuck = (V("i_sys_base") + V("i_ble_peak") * V("t_ble_evt") / V("t_conn") + 0.4e-3) * 1.8 / (V("eta_buck") * 3.7)
fb = 15e3
qb = ibuck / fb
vb = qb / ((V("cstor") + 1e-6) * der)
R["buck_burst"] = dict(f_hz=fb, vstor_mVpp=vb * 1e3, avdd_uVpp=vb * 10 ** (-ldo_psrr_db([fb])[0] / 20) * 1e6,
                       input_if_aliased_uV=vb * 10 ** (-ldo_psrr_db([fb])[0] / 20) * 10 ** (-ads_psrr_db([fb], GAIN)[0] / 20) * 1e6)
print("buck bursts:", {k_: round(v_, 4) for k_, v_ in R["buck_burst"].items()})

# ============================================================================================ 5  DVDD
dv = V("bq_buck_ripple")
R["dvdd"] = dict(vdd1v8_ripple_mVpp_vendor=dv * 1e3, required_rejection_db_for_0p1uV=float(20 * math.log10(dv / 2 / math.sqrt(2) / 0.1e-6)),
                 note="SBAS502C gives PSRR for AVDD only; DVDD rejection must be checked on the bench (input short, buck on/off)")

# ============================================================================================ 6  verdict per variant
verdict = {}
for vn in VARIANTS:
    ok = {}
    for R_, C_ in GRID:
        r = TABLE[f"{vn}|{R_/1e6:g}M_{C_*1e9:g}n"]
        ok[f"{R_/1e6:g}M_{C_*1e9:g}n"] = dict(harvester_ok=bool(r["sun_mppt_uV"] < 1.0), total_ok=bool(r["total_with_ldo_noise_uV"] < 1.0))
    verdict[vn] = ok
R["verdict"] = verdict
(HERE / "results" / "sim06_supply.json").write_text(json.dumps(R, indent=1, default=float))
print(f"done {time.time()-t0:.0f} s")
