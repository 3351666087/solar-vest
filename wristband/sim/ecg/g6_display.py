"""V3-G6 / SIM-06 + SIM-07 case 1: the display and the strap conductors against M2 (10 uVpp, 0.5-40 Hz, display running).
H_COM : AC transfer (lib/frontend.py, FINAL network, V2-B plate capacitances) from the panel COM (vs device GND) through
        C(COM-finger) into the finger (node rf) and C(COM-E3 net) into the E3 pad (node e3); capacitances from
        results/com_caps.json (g6_com_caps.py). COM waveform: 3.0 V square (VDD_DISP 2.955-3.045 V, CALC_V3F 6.3) at
        f_COM = EXTCOMIN / 2 = 30 Hz (EXTCOMIN 60 Hz, pin_budget / V3_ARCH: COM toggles on each EXTCOMIN rising edge, the
        V3_ARCH reading 'about 3 V at 30 Hz'); 35 Hz (EXTCOMIN 70 Hz) and 60 Hz (COM toggling on both edges) as corners.
        Output = steady-state periodic waveform through the ARCH 7.2 0.5-40 Hz filter, + aliases of the harmonics in a
        500 SPS sinc3 stream (data rate assumed).
        Optional: a second finger on the top-rim GND contact (rf -> device GND through 1 k / 100 k).
SIM-06: VDD_DISP load on VSTOR_SW (U16 and U3 share it): panel <= 50 uW hold (LD-29Y03 Table 6-4 via CALC_V3F 6.1) taken as
        charge pulses at f_COM through the source resistance of the battery path; then TPS7A2030 PSRR (curves.ln_ldo_psrr_db,
        as sim06_v2_supply.py), the AVDD -> differential transfer of the network and the ADS1291 PSRR.
Strap : a 1.8 V step on a strap conductor (NTC line) and the BATT_P conductor's motion (dC 50 % of 0.08 pF at 2.2 V) into the
        skin under the root (node lw).
Writes results/g6_display.json."""
import json, time
import numpy as np
from sim07_v2_common import (S, ENVS, V, HERE, FINAL, STRUCT, base, mm, add_caps, transfer, step_response, F_T, bp, Q, DF)
from curves import ads_psrr_db, ln_ldo_psrr_db

t0 = time.time()
CAPS = STRUCT["V2-B rule: B.Cu + L5 void"]
CC = json.loads((HERE / "results" / "com_caps.json").read_text())
EL = {"in-vivo nominal (E3 0.75 cm2)": ((1, 1, 1), -60.0, 0.75), "in-vivo dry x2, E3 0.5 cm2": ((2, 2, 2), -60.0, 0.5),
      "in-vivo E3 dry x2 on 0.5 cm2, plates x0.5": ((0.5, 0.5, 2), -60.0, 0.5), "in-vivo moist x0.5, E3 1.0 cm2": ((0.5, 0.5, 0.5), -60.0, 1.0),
      "ARCH 1M|10n (-50/+50 %)": (1e6, 10e-9, -1), "ARCH 10M|1n (-50/+50 %)": (10e6, 1e-9, -1)}


def cfg_el(name, extra=""):
    b = base(FINAL, None, Rin=V("ads_rin_loff"), **ENVS["typical"])
    if name.startswith("in-vivo"):
        k, ph, a3 = EL[name]; c = add_caps(b, CAPS); c["Re"] = Q.invivo_electrodes(k, ph, a3)
    else:
        Rr, C, s = EL[name]; c = mm(Rr, C, s, 0, b, CAPS)
    c["extra"] = extra
    return c


def periodic_pp(H, f0, vpp, fd=500.0):
    """steady-state in-band pp (V) of a vpp square wave at f0 through H (on F_T), the 0.5-40 Hz filter and sinc3 aliases"""
    t = np.linspace(0, 2.0 / f0 if f0 < 40 else 2.0, 4000, endpoint=False)
    y = np.zeros_like(t); ya = np.zeros_like(t)
    for n in range(1, int(F_T[-1] / f0) + 1, 2):
        f = n * f0; k = int(round(f / DF)) - 1
        if k >= len(F_T): break
        a = 2 * vpp / (np.pi * n); g = H[k]
        if f <= 250:
            G = g * bp(f); y += a * abs(G) * np.cos(2 * np.pi * f * t + np.angle(G))
        if f > fd / 2:
            fa = abs(f - round(f / fd) * fd)
            if 0.5 <= fa <= 40:
                gs = abs(np.sinc(f / fd)) ** 3
                ya += a * abs(g) * gs * abs(bp(fa)) * np.cos(2 * np.pi * fa * t)
    return float(y.max() - y.min()), float(ya.max() - ya.min())


R = dict(criterion="M2: <= 10 uVpp input-referred over 0.5-40 Hz with the display running; bench floor (input short) 3.99 uVpp "
                   "(v2/sim/ecg sim07_v2.json F_noise) -> display + supply budget 6.0 uVpp (linear sum)", cases={})
FLOOR = 3.99; BUDGET = 10.0 - FLOOR
rows = [r for r in CC["rows"] if r["xf_mm"] is not None] + [r for r in CC["rows"] if r["xf_mm"] is None]
FCOM = {"30 Hz (EXTCOMIN 60 Hz)": 30.0, "35 Hz (EXTCOMIN 70 Hz)": 35.0, "60 Hz (COM on both edges)": 60.0}
GNDF = {"no GND-contact finger": "", "second finger on the GND contact, dry 100k": "Rcmf rf dg 100k", "second finger on the GND contact, wet 1k": "Rcmf rf dg 1k"}
print("COM artefact (uVpp in band | alias) per geometry, worst electrode; f_COM 30 Hz unless noted")
for r in rows:
    cf, ce = r["finger_pF"] * 1e-12, r["e3_pF"] * 1e-12
    if r["xf_mm"] is None:          # no finger on E3: not a recording state, E3 net coupling only (lead-off)
        continue
    for gn, gx in GNDF.items():
        if gn != "no GND-contact finger" and r["frame"] != "floating": continue
        lines = "Vcom pcom dg DC 0 AC 1" + ("\nCcf pcom rf %g" % cf if cf > 0 else "") + ("\nCce pcom e3 %g" % ce if ce > 0 else "")
        res = {}
        for en in EL:
            H = transfer(cfg_el(en, gx), lines)
            res[en] = {fn: dict(zip(("inband_uVpp", "alias_uVpp"), [v * 1e6 for v in periodic_pp(H, f0, 3.045)])) for fn, f0 in FCOM.items()}
            res[en]["edge_step_pp_uV"] = step_response(H)[1] * 3.045 * 1e6
        w = max(res.items(), key=lambda kv: kv[1]["30 Hz (EXTCOMIN 60 Hz)"]["inband_uVpp"])
        wall = max(max(v[fn]["inband_uVpp"] + v[fn]["alias_uVpp"] for fn in FCOM) for v in res.values())
        key = f"frame {r['frame']} | finger edge {r['xf_mm']:+.1f} mm | {gn}"
        R["cases"][key] = dict(frame=r["frame"], xf_mm=r["xf_mm"], C_finger_pF=r["finger_pF"], C_e3_pF=r["e3_pF"], gnd_finger=gn,
                               per_electrode=res, worst30_electrode=w[0], worst30_uVpp=w[1]["30 Hz (EXTCOMIN 60 Hz)"]["inband_uVpp"],
                               worst_any_fcom_uVpp=wall, pass_budget=bool(wall <= BUDGET))
        print(f"  {key:86s} Cf {r['finger_pF']:.3f} Ce {r['e3_pF']:.4f} pF | nominal {res[list(EL)[0]]['30 Hz (EXTCOMIN 60 Hz)']['inband_uVpp']:7.2f} | worst30 {w[1]['30 Hz (EXTCOMIN 60 Hz)']['inband_uVpp']:7.2f} ({w[0][:24]}) | worst any f {wall:7.2f} uVpp", flush=True)

# sensitivity per pF (nominal and worst electrode) for budgets
sens = {}
for node in ("rf", "e3"):
    s = {}
    for en in EL:
        H = transfer(cfg_el(en), "Vcom pcom dg DC 0 AC 1\nCs pcom %s 1p" % node)
        s[en] = max(periodic_pp(H, f0, 3.045)[0] for f0 in FCOM.values()) * 1e6
    sens[node] = dict(per_electrode_uVpp_per_pF=s, worst=max(s.values()), c_max_pF_for_budget=BUDGET / max(s.values()))
R["sensitivity_3V_square_per_pF"] = sens
print("sensitivity uVpp per pF (worst electrode, worst f_COM): finger %.2f, E3 net %.2f -> C max for %.1f uVpp: finger %.3f pF, E3 net %.4f pF" %
      (sens["rf"]["worst"], sens["e3"]["worst"], BUDGET, sens["rf"]["c_max_pF_for_budget"], sens["e3"]["c_max_pF_for_budget"]), flush=True)

# SIM-06: VDD_DISP / VSTOR_SW -> AVDD -> input
r_src = 1.0 + 0.05 + 0.5 + 1.0 + 1.5 + 0.2         # cell (V2 r_dc max) + PCM + F1 (bound) + RSH2 + BQ PFET + U12 (Ohm) [estimates]
i_panel = 50e-6 / 2.955
s06 = {}
for fn, f0 in FCOM.items():
    v_ripple = 2 * i_panel * r_src                  # fundamental amplitude bound of the pulse train through r_src (V peak)
    psrr_ldo = float(ln_ldo_psrr_db(np.array([f0]))[0]); v_avdd = v_ripple * 10 ** (-psrr_ldo / 20)
    c = dict(base(FINAL, None, Rin=V("ads_rin_loff"), **ENVS["typical"]), avdd_ac=1.0)
    c = add_caps(c, CAPS); c["Re"] = Q.invivo_electrodes((1, 1, 1), -60.0, 0.75)
    H = transfer(c, "Rdum xdum dg 1e12"); k = int(round(f0 / DF)) - 1
    h_net = float(abs(H[k])); h_ads = 10 ** (-float(ads_psrr_db(np.array([f0]), 4)[0]) / 20)
    v_in = 2 * v_avdd * (h_net + h_ads) * abs(bp(f0))
    s06[fn] = dict(r_src_ohm=r_src, i_panel_uA=i_panel * 1e6, vstor_sw_ripple_uVpk=v_ripple * 1e6, ldo_psrr_db=psrr_ldo, avdd_ripple_nVpk=v_avdd * 1e9,
                   h_net=h_net, h_ads_psrr=h_ads, input_referred_uVpp=v_in * 1e6)
    print(f"SIM-06 {fn}: VSTOR_SW {v_ripple*1e6:.0f} uVpk -> AVDD {v_avdd*1e9:.2f} nVpk (LDO PSRR {psrr_ldo:.0f} dB) -> input {v_in*1e6:.5f} uVpp", flush=True)
R["sim06_vdd_disp"] = s06

# strap conductors -> skin under the root
st = {}
for name, (amp, cpf, kind) in {"NTC line 1.8 V step, 0.08 pF to the skin": (1.8, 0.08, "step"),
                               "BATT_P conductor motion, dC 0.04 pF at 2.2 V (equivalent step)": (2.2, 0.04, "step"),
                               "NTC line 1.8 V, 10 ms sampling pulse, 0.08 pF": (1.8, 0.08, 0.01)}.items():
    w = 0.0
    for en in EL:
        H = transfer(cfg_el(en), "Vst pst dg DC 0 AC 1\nCst pst lw %gp" % cpf)
        pp = step_response(H, None if kind == "step" else kind)[1] * amp * 1e6; w = max(w, pp)
    st[name] = dict(worst_uVpp=w)
    print(f"strap: {name}: worst {w:.4f} uVpp", flush=True)
R["strap"] = st
R["budget_uVpp"] = BUDGET; R["floor_uVpp"] = FLOOR; R["runtime_s"] = time.time() - t0
(HERE / "results" / "g6_display.json").write_text(json.dumps(R, indent=1))
print("done %.0f s" % (time.time() - t0))
