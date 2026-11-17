"""SIM-06 (ECG part) for V2-B: supply disturbances -> VSTOR_SW -> TPS7A2030 -> AVDD_ECG -> ADS1291 -> input-referred.
Method = sim06_supply.py (v1), 'final' design only (TPS7A2030, FINAL network, internal RLDREF). What V2-B changes:
  - cell 43 mAh bare, DC resistance up to 1.0 Ohm, protector FET 54 mOhm in the return, RSH2 1 Ohm, BQ25570 PFET 1.5 Ohm max
  - the LDO input is VSTOR_SW behind the load switch U12; the PPG LED current now flows straight from VSTOR_SW through
    R117 3.3 Ohm (no boost converter), reservoir C404 10 uF only (C118 not fitted)
  - charge current limited by R_LIM: 11.7 mA planning, 20.6 mA worst (0.48 C); MPPT gap 256 ms every 16 s
  - pad capacitances of the V2-B electrode structure in the AVDD -> differential-input transfer
Criterion (ARCH 9 SIM-06, ECG part): input-referred < 1 uVrms over 0.5-40 Hz from supply coupling with the harvester running.
(VDD_1V8 ripple and the LED headroom / droop criteria of SIM-06 belong to v2/sim/power.)
Writes results/sim06_v2_supply.json.  Run time about 5 min."""
import json, math, time, sys, pathlib
import numpy as np
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib")); sys.path.insert(0, str(HERE))
from sim07_v2_common import S, GRID, ENVS, default_cfg, netlist, V, FINAL, STRUCT, mm, add_caps, Q, key     # noqa: E402
from curves import ads_psrr_db, ln_ldo_psrr_db, ln_ldo_noise                                             # noqa: E402

t0 = time.time(); P = Q.P; VV = lambda k: P[k]["value"]
GAIN = 4; FB = (0.5, 40.0); CAPS = STRUCT["V2-B rule: B.Cu + L5 void"]
R = {"gain": GAIN, "ldo": "TPS7A2030", "caps_pF": [c * 1e12 for c in CAPS]}


def vstor_net(case, t_end, mppt_at=None, tstep=1e-4, rcell=None, vocv=3.70):
    der = V("mlcc_dcbias"); rcell = VV("cell_v2")["r_dc"][1] if rcell is None else rcell
    L = ["* V2-B VSTOR / VSTOR_SW / VLED network", f"Vocv bo 0 DC {vocv}", f"Rcell bo b1 {rcell}", f"Rprot b1 b2 {VV('r_prot_fet')[2]}",
         f"Rsh2 b2 vbat {V('rsh2')}", f"Cbat vbat cb {V('cbat') * der}", "Rcb cb 0 5m",
         f"Rpfet vbat vstor {V('bq_rds_bat')[1]}", f"Cstor vstor cs {(V('cstor') + 1.1e-6) * der}", "Rcs cs 0 5m",
         f"Ru12 vstor vsw {VV('r_u12')[1]}", f"Cldo vsw 0 {1e-6 * der}", f"Iavdd vsw 0 DC {V('i_ads_avdd')}",
         f"R117 vsw vled {VV('r117')}", f"C404 vled c4 {VV('c404') * der}", "Rc4 c4 0 5m"]
    ich = case.get("ichg", 0.0)
    if case.get("bursts"):
        q = 0.5 * V("bq_ichg_cbc")[0] * V("l1") * V("bq_ichg_cbc")[0] / (3.7 - 1.6); tw = q / 0.115
        L.append(f"Ich 0 vstor PULSE(0 0.115 1m 0.1u 0.1u {tw} {q / ich})")
    elif ich > 0:
        if mppt_at is not None:
            L.append(f"Ich 0 vstor PWL(0 {ich} {mppt_at} {ich} {mppt_at + 5e-6} 0 {mppt_at + 0.256} 0 {mppt_at + 0.256 + 5e-6} {ich})")
        else: L.append(f"Ich 0 vstor DC {ich}")
    L.append(f"Vble ble 0 PULSE(0 {V('i_ble_peak')} 2m 20u 20u {V('t_ble_evt')} {V('t_conn')})")
    L.append(f"Bbuck vstor 0 I = ({V('i_sys_base')} + V(ble)) * 1.86 / ({V('eta_buck')} * max(V(vstor), 2.5))")
    if case.get("ppg"):
        L.append(f"Ippg vled 0 PULSE(0 {case['ppg']} 3m 1u 1u 117u 40m)")          # MAX86141 current sink: LED current = supply current
    L += [".options interp", f".tran {tstep} {t_end} 0 {tstep / 2}", ".end"]
    return "\n".join(L)


CASES = {
    "sun_worst_mppt": dict(ichg=20.6e-3, desc="worst charge current of the limiter 20.6 mA (0.48 C), one 256 ms MPPT gap, BLE 33 Hz"),
    "sun_plan_mppt": dict(ichg=11.7e-3, desc="planning point 11.7 mA (0.27 C), MPPT gap, BLE"),
    "1klx_bursts": dict(ichg=207e-6 / 3.7, bursts=True, desc="1000 lx: 207 uW into the cell (REDESIGN 5.6), boost bursts, BLE"),
    "dark": dict(ichg=0.0, desc="harvester idle (W-C band), BLE only"),
    "sun_worst_mppt_ppg20": dict(ichg=20.6e-3, ppg=20e-3, desc="sun_worst plus PPG 20 mA LED pulses, 117 us at 25 sps, straight from VSTOR_SW"),
    "sun_worst_mppt_ppg30": dict(ichg=20.6e-3, ppg=30e-3, desc="same with 30 mA"),
    "dark_ppg30": dict(ichg=0.0, ppg=30e-3, desc="W-C band with 30 mA LED pulses"),
}
WAVES = {}
for name, case in CASES.items():
    t_end = 4.0 if case.get("bursts") else 16.0
    S.run(vstor_net(case, t_end, mppt_at=8.0 if "mppt" in name else None, tstep=1e-4 if not case.get("bursts") else 2e-5))
    t = S.vec("time"); v = S.vec("vsw"); vl = S.vec("vled"); k = t > 1.0
    WAVES[name] = (t[k] - t[k][0], v[k] - v[k].mean())
    R.setdefault("vstor_sw", {})[name] = dict(desc=case["desc"], pp_mV=float(np.ptp(v[k]) * 1e3), rms_mV=float(np.std(v[k]) * 1e3), vled_pp_mV=float(np.ptp(vl[k]) * 1e3))
    print(f"VSTOR_SW {name:22s} p-p {np.ptp(v[k])*1e3:7.2f} mV rms {np.std(v[k])*1e3:6.3f} mV | VLED p-p {np.ptp(vl[k])*1e3:7.2f} mV", flush=True)
R["assumptions"] = dict(r_cell=VV("cell_v2")["r_dc"][1], r_prot=VV("r_prot_fet")[2], r_pfet=V("bq_rds_bat")[1], r_u12=VV("r_u12")[1], vocv=3.70, mlcc_derate=V("mlcc_dcbias"),
                        note="pulse sampling of the transient is 100 us per step (the 117 us LED pulse is resolved by the breakpoints of PULSE)")

FH = np.logspace(np.log10(0.05), np.log10(5e3), 400)
def h_avdd(cfg, mode):
    c = dict(cfg, rin_mode="sym" if mode == "mid" else mode, avdd_ac=1.0, vmains_ac=0.0, vecg_ac=0.0)
    S.run(netlist(c, f".ac dec 40 {FH[0]} {FH[-1]}")); f = S.vec("frequency").real
    return np.interp(np.log10(FH), np.log10(f), np.abs(S.vec("inp") - S.vec("inn")))
ELS = {key(Rr, C): ("grid", Rr, C) for Rr, C in GRID}
ELS["in-vivo nominal"] = ("iv", (1, 1, 1), -60.0, 0.75); ELS["in-vivo dry x2, E3 0.5 cm2"] = ("iv", (2, 2, 2), -60.0, 0.5); ELS["in-vivo dry x2 resistive, E3 0.5 cm2"] = ("iv", (2, 2, 2), -30.0, 0.5)
HD = 10 ** (-ads_psrr_db(FH, GAIN) / 20); HL = 10 ** (-ln_ldo_psrr_db(FH) / 20); HL10 = HL * 10 ** (10 / 20)

def band_rms(t, x, Hv):
    dt = t[1] - t[0]; win = np.hanning(len(x)); X = np.fft.rfft(x * win / np.sqrt(np.mean(win ** 2))); f = np.fft.rfftfreq(len(x), dt)
    h = np.interp(np.log10(np.maximum(f, 1e-3)), np.log10(FH), Hv, left=Hv[0], right=Hv[-1]); kb = (f >= FB[0]) & (f <= FB[1])
    Y = np.where(kb, X * h, 0); y = np.fft.irfft(Y, n=len(x))
    return math.sqrt(2 * np.sum(np.abs(Y) ** 2)) / len(x), float(np.max(np.abs(y)))

TABLE = {}; band = (FH >= FB[0]) & (FH <= FB[1]); nl = ln_ldo_noise(FH)
for mode in ("asym", "mid", "avss"):
    for en, spec in ELS.items():
        hn = np.zeros_like(FH)
        for s_ in (1, -1):
            b0 = default_cfg(**FINAL, Rin=V("ads_rin_loff"), **ENVS["typical"])
            if spec[0] == "grid": cfg = mm(spec[1], spec[2], s_, 0, b0, CAPS)
            else:
                cfg = add_caps(b0, CAPS, s_); cfg["Re"] = Q.invivo_electrodes(spec[1], spec[2], spec[3])
            hn = np.maximum(hn, h_avdd(cfg, mode))
        row = dict(ldo_noise_uV=float(math.sqrt(np.trapezoid((nl * hn)[band] ** 2, FH[band])) * 1e6 + math.sqrt(np.trapezoid((nl * HD)[band] ** 2, FH[band])) * 1e6),
                   h_avdd_dm_10Hz=float(np.interp(10, FH, hn)))
        for cn, (t, w) in WAVES.items():
            r1, p1 = band_rms(t, w, HL * hn); r2, p2 = band_rms(t, w, HL * HD)
            row[cn + "_uV"] = (r1 + r2) * 1e6; row[cn + "_peak_uV"] = (p1 + p2) * 1e6
            r3, _ = band_rms(t, w, HL10 * hn); r4, _ = band_rms(t, w, HL10 * HD); row[cn + "_psrr-10dB_uV"] = (r3 + r4) * 1e6
        worst_h = max(row[c + "_uV"] for c in WAVES)
        row["total_worst_uV"] = math.hypot(worst_h, row["ldo_noise_uV"]); row["total_worst_psrr-10dB_uV"] = math.hypot(max(row[c + "_psrr-10dB_uV"] for c in WAVES), row["ldo_noise_uV"])
        TABLE[f"{mode}|{en}"] = row
    print(f"--- Zin model {mode}")
    for en in ELS:
        r = TABLE[f"{mode}|{en}"]
        print(f"  {en:38s} sun worst {r['sun_worst_mppt_uV']:6.3f} (pk {r['sun_worst_mppt_peak_uV']:5.2f}) plan {r['sun_plan_mppt_uV']:6.3f} 1klx {r['1klx_bursts_uV']:6.3f} dark {r['dark_uV']:6.3f} "
              f"+PPG20 {r['sun_worst_mppt_ppg20_uV']:6.3f} +PPG30 {r['sun_worst_mppt_ppg30_uV']:6.3f} | LDO noise {r['ldo_noise_uV']:6.3f} | total {r['total_worst_uV']:6.3f} (PSRR -10 dB: {r['total_worst_psrr-10dB_uV']:6.3f}) uVrms", flush=True)
R["table"] = TABLE
R["worst_total_uV"] = {m: max(v["total_worst_uV"] for k, v in TABLE.items() if k.startswith(m)) for m in ("asym", "mid", "avss")}
R["worst_total_psrr-10dB_uV"] = {m: max(v["total_worst_psrr-10dB_uV"] for k, v in TABLE.items() if k.startswith(m)) for m in ("asym", "mid", "avss")}
R["worst_total_grid_le_1M_uV"] = max(v["total_worst_uV"] for k, v in TABLE.items() if "|10M" not in k)

# switching ripple, alias bound (TPS7A2030)
ich = 20.6e-3; q = 0.5 * V("bq_ichg_cbc")[1] * V("l1") * V("bq_ichg_cbc")[1] / (3.7 - 2.2); tw = 2 * q / V("bq_ichg_cbc")[1]; fsw = ich / q; der = V("mlcc_dcbias")
hf = f"""* boost ripple V2-B
Vocv bo 0 DC 3.7
Rbat bo vbat {VV('cell_v2')['r_dc'][0] + VV('r_prot_fet')[1] + V('rsh2')}
Cbat vbat cb {V('cbat') * der}
Rcb cb 0 5m
Rpfet vbat vstor {V('bq_rds_bat')[0]}
Cstor vstor cs {(V('cstor') + 1.1e-6) * der}
Rcs cs 0 5m
Lcs cs cs2 0.5n
Ru12 vstor vsw {VV('r_u12')[0]}
Cldo vsw 0 {1e-6 * der}
Ich 0 vstor PULSE(0 {V('bq_ichg_cbc')[1]} 10u 0.05u {tw} 0.05u {1 / fsw})
.tran 20n 2m 0 20n
.end"""
S.run(hf); t = S.vec("time"); v = S.vec("vsw"); k = t > 1e-3; x = v[k] - v[k].mean()
X = np.abs(np.fft.rfft(x)) * 2 / len(x); f = np.fft.rfftfreq(len(x), t[1] - t[0]); alias = []
for n_ in range(1, 6):
    kk = np.argmin(np.abs(f - n_ * fsw)); a = float(X[max(kk - 2, 0):kk + 3].max()); fh = float(f[kk])
    alias.append(dict(f_hz=fh, vsw_mV=a * 1e3, input_if_aliased_uV=a * 10 ** (-ln_ldo_psrr_db([fh])[0] / 20) * 10 ** (-ads_psrr_db([fh], GAIN)[0] / 20) * 1e6))
R["switching"] = dict(boost_f_hz=fsw, vsw_pp_mV=float(np.ptp(v[k]) * 1e3), harmonics=alias)
print(f"boost ripple {fsw/1e3:.1f} kHz, VSTOR_SW {np.ptp(v[k])*1e3:.1f} mVpp; alias bound per harmonic uV:", [round(a['input_if_aliased_uV'], 4) for a in alias])
dv = V("bq_buck_ripple")
R["dvdd"] = dict(vdd1v8_ripple_mVpp_vendor=dv * 1e3, required_rejection_db_for_0p1uV=float(20 * math.log10(dv / 2 / math.sqrt(2) / 0.1e-6)),
                 note="no DVDD rejection figure in SBAS502C: bench item (input short, buck on / off), unchanged from v1")
R["verdict"] = {m: bool(R["worst_total_uV"][m] < 1.0) for m in R["worst_total_uV"]}
(HERE / "results" / "sim06_v2_supply.json").write_text(json.dumps(R, indent=1, default=float))
print("worst total uVrms by Zin model:", R["worst_total_uV"], "| with PSRR -10 dB:", R["worst_total_psrr-10dB_uV"])
print(f"done {time.time()-t0:.0f} s")
