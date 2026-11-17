"""[ECG final, copy of v3/prechecks/sim07_vias.py] SIM-07 re-check on the CLOSED 8-layer board (v3/finish/solarband_v3f_final), args: FIX_IMU / FIX_P2_BROKEN.\n[prechecks C1] SIM-07 re-check with the signal copper over the ECG plates (LEAD_NOTES R-2 / R-4).
Uses the v3/sim/ecg model unchanged (sim07_v2_common: ngspice SIM-07 network, FINAL, STRUCT "V2-B rule: B.Cu + L5 void",
0.5-40 Hz filter of ARCH 7.2), the per-net copper over the plates measured on the routed board by plate_geom.py,
and the firmware activity of each net during an ECG session (BASELINE 14, design/src, design/calc/v3f_calc.py).
  A) aggressor nets: C(net -> plate E1) from the via pads and inner-layer tracks; in-band artefact of the net's real waveform
  B) front-end nets of the ECG chain itself over the plates: cross capacitances added to the network, noise re-run (M2 floor part)
M2 (ARCH, as written): <= 10 uVpp input-referred over 0.5-40 Hz; display off in every ECG session (F-9): floor 3.99 uVpp.
usage: venv python sim07_vias.py  -> sim07_vias.json (about 1-2 min, one core)"""
import json, math, sys, time, pathlib
import numpy as np
ECG = pathlib.Path("/path/to/SolarVest_work/wristband/v3/sim/ecg")
sys.path.insert(0, str(ECG)); sys.path.insert(0, str(ECG / "lib"))
from sim07_v2_common import (S, ENVS, V, FINAL, STRUCT, base, mm, add_caps, transfer, bp, F_T, N_T, DF, Q, default_cfg, netlist)
HERE = pathlib.Path(__file__).resolve().parent
t0 = time.time()
G = json.loads((HERE / "plate_geom_final.json").read_text())
FIX = set(sys.argv[1:])   # scenario flags
CAPS = STRUCT["V2-B rule: B.Cu + L5 void"]
EPS0 = 8.854e-15                               # F/mm

# ------------------------------------------------------------------ capacitance estimates (own, from the geometry) ⚠
# via pad on B.Cu, tented: mask 0.02 mm (er 3.5) + carrier film 0.10 mm (er 3.3) to the Ti plate (params_v2 film_carrier, mask)
H_PAD = 0.10 + 0.02; ER_PAD = H_PAD / (0.10 / 3.3 + 0.02 / 3.5)


def c_via(d, bound):
    a = d / 2
    pp = EPS0 * ER_PAD * math.pi * a * a / H_PAD                             # parallel plate, no fringe (lower bound)
    if bound == "low":
        return pp
    kirch = EPS0 * ER_PAD * (math.pi * a * a / H_PAD + a * (math.log(16 * math.pi * a / H_PAD) - 1))   # Kirchhoff disc, fringe
    return kirch * 1.15                                                        # + barrel and unused L5 pad below the L4 pour (+15 %)


# inner-layer track over a plate, w 0.09-0.10 mm. L5 (In4.Cu): 0.134 mm FR4 + mask + film = 0.254 mm to the plate, L4 pour 0.265 mm
# above -> stripline-like, about half of the total C goes to the plate: 0.042 pF/mm (wire-over-plane alone 0.069). L4 (In3.Cu): 0.52 mm
# to the plate through the L5 / B voids, coplanar L4 pour 0.1-0.2 mm away: 0.02-0.045 pF/mm. In2.Cu under the L4 pour: shielded (0).
# 8-layer stack (P-5, PLANB 2 estimate): In6 0.076 mm FR4 above B (+ mask + film) with the In4 plane 0.36 mm above: more than half
# of a wire-over-plane C goes to the plate (0.05-0.08 pF/mm ⚠); In5 0.21 mm FR4 above B, In4 plane 0.116 mm above: 0.02-0.04 pF/mm ⚠;
# In2/In3 where the In4 fill is missing under the track or within 0.1 mm of its edges ('In4 gap', shield_check rule): upper bound = the
# 6-layer L4-through-voids figure 0.045 pF/mm, lower bound x 0.1 (aperture) ⚠. F.Cu: behind the In1 GND plane (0). Shielded In2/In3: 0.
C_TRK = {"In6.Cu": (0.050e-12, 0.080e-12), "In5.Cu": (0.020e-12, 0.040e-12), "B.Cu": (0.10e-12, 0.14e-12),
         "In2.Cu In4 gap": (0.0045e-12, 0.045e-12), "In3.Cu In4 gap": (0.0045e-12, 0.045e-12)}

# ------------------------------------------------------------------ net activity during an ECG session (sources in the json)
# kind "pulses": list of (amplitude V, width s, period s or None for a single event)
P2 = "FIX_P2_BROKEN" not in FIX           # firmware P-2 obeyed (default)
ACT = {
    # ---- E1
    "I2C_SDA": dict(pulses=[] if P2 else [(-0.9, 0.4e-3, 1.0), (-0.9, 0.4e-3, 1.0), (-0.9, 4.8e-3, 1.0)],
                    src="P-2: no I2C traffic in a session: idle high 1.8 V (R505), static. (P-2 broken: TMP117 + INA 1 Hz, IMU FIFO 4.8 ms, H3 convention)"),
    "SPI_MISO": dict(pulses=([] if "FIX_PPG" in FIX else [(0.9, 0.3e-3, 1.0)]) + ([] if "FIX_FLASH" in FIX else [(0.9, 0.1e-3, 1 / 6)]), step=0.0162,
                     src="PPG FIFO read 1 Hz 0.3 ms mean 0.9 V; flash status/read traffic about 6 Hz 0.1 ms ⚠; ADS1291 DOUT data-dependent part 16.2 mV step bound"),
    "SPI_SCK": dict(pulses=([] if "FIX_PPG" in FIX else [(0.9, 0.3e-3, 1.0)]) + ([] if "FIX_FLASH" in FIX else [(0.9, 0.5e-3, 1 / 6)]),
                    src="clock bursts, mean 0.9 V: PPG read 1 Hz 0.3 ms; flash page programs about 6 Hz 0.5 ms (1.5 kB/s ECG log in 256 B pages) ⚠; "
                        "ADS1291 reads 500 Hz 18 us: data-independent, synchronous with sampling, out of band"),
    "CS_FLASH": dict(pulses=[] if "FIX_FLASH" in FIX else [(-1.8, 0.5e-3, 1 / 6)], src="flash selected (low) about 0.5 ms per 256 B page at about 6 Hz ⚠ (ECG log; no SPI display writes)"),
    "ECG_DRDY": dict(pulses=[(-1.8, 20e-6, 2e-3)], src="ADS1291 DRDY low about 20 us every 2 ms (500 SPS): line at 500 Hz and harmonics, nothing in 0.5-40 Hz"),
    "PPG_INT": dict(pulses=[] if "FIX_PPG" in FIX else [(-1.8, 1.0e-3, 1.0)], src="PPG FIFO interrupt 1 Hz, low until the SPI read (about 1 ms) ⚠"),
    "IMU_INT1": dict(pulses=[], step=0.0 if "FIX_IMU" in FIX else 1.8,
                     src="IMU FIFO-threshold interrupt on INT1 (CTRL4 INT1_FTH). P-2 stops the IMU reads, so the flag is not cleared: INT1 rises once "
                         "(1.8 V step) inside the session and stays high. With the fix (INT1 disabled / IMU idle before the recording): static"),
    "DEC1": dict(pulses=[(0.020, 2e-3, 30e-3)], src="nRF DEC1 core rail: radio-event load steps <= 20 mV, 2 ms per 30 ms connection event ⚠ (as DEC4 in prechecks)"),
    "PV_SW": dict(pulses=[(0.566, 0.256, 16.0)], src="PV node: BQ25570 Voc sample 256 ms every 16 s, step 0.39 (indoor nominal) - 0.57 V (worst) "
                  "(v2/sim/ecg/results/sim07_v2_coupling.json H1_budget); harvesting runs in a session"),
    "INA_VS": dict(pulses=[], src="INA rail: INA_EN not switched in a session (P-2: no INA reads); static"),
    "INA_EN": dict(pulses=[], src="static in a session (P-2)"),
    "NTC": dict(pulses=[], src="P-2: no NTC_EN reading; V_O2 off with a healthy cell (Q18): static 0 V"),
    "PWR_CYC": dict(pulses=[], src="hard power-cycle one-shot: static low in a session"),
    "DISP_CTRL": dict(pulses=[], src="F-9: display powered down, static"),
    "AVDD_ECG": dict(pulses=[], src="DC (SIM-06)"), "XL1": dict(pulses=[], src="32 kHz, out of band"), "XL2": dict(pulses=[], src="32 kHz, out of band"),
    "SWDCLK": dict(pulses=[], src="no debugger: static"), "SWDIO": dict(pulses=[], src="static"), "NRESET": dict(pulses=[], src="static high"),
    "GND_K": dict(pulses=[], src="no head in a session (ECG locked while /PG low), Q20 off: static"),
    "TMP117_ISLAND": dict(pulses=[], src="floating island; P-2: no I2C, so the H3 path is silent"),
    # ---- E2
    "VIN_DC": dict(pulses=[(0.566, 0.256, 16.0), (0.020, 25e-3, 50e-3)], plate="plate_E2",
                   src="BQ25570 input: the same Voc sample; plus a bound for low-light hysteretic regulation ripple 20 mV square at 20 Hz ⚠"),
    "O2_OK": dict(pulses=[], plate="plate_E2", src="U20 output: V_O2 off (Q18 off with a healthy cell, no NTC_EN by P-2): static 0 V"),
    "O2_TH": dict(pulses=[], plate="plate_E2", src="ladder tap of V_O2: static 0 V in a session"),
}
FRONT = {"ECG_INN": "inn", "ECG_INP": "inp", "RLD_OUT": "rldout", "RLD_INV": "rldinv", "RLD_Z": "cz", "PGA2P": "pgp",
         "E1_MID": "m1", "E1_LINK": "e1", "E1_PAD": "e1"}          # E1's own nets: no effect (same node)
E2_FRONT = {"E3_MID": "m3", "E2_PAD": "e2", "E2_LINK": "e2"}


def net_caps(plate, bound):
    out = {}
    for net, ds in G["vias"].get(plate, {}).items():
        out.setdefault(net, dict(vias=0.0, tracks=0.0, n_vias=len(ds)))["vias"] = sum(c_via(d, bound) for d in ds)
    for net, dd in G["tracks_mm"].get(plate, {}).items():
        for lay, L in dd.items():
            if lay in C_TRK and not net.startswith(("E1_", "E2_")):
                out.setdefault(net, dict(vias=0.0, tracks=0.0, n_vias=0))["tracks"] += L * C_TRK[lay][0 if bound == "low" else 1]
    for v in out.values():
        v["total_pF"] = (v["vias"] + v["tracks"]) * 1e12; v["vias_pF"] = v["vias"] * 1e12; v["tracks_pF"] = v["tracks"] * 1e12
        del v["vias"], v["tracks"]
    return out


EL = {"in-vivo nominal": ("iv", (1, 1, 1), -60.0, 0.75), "in-vivo dry x2, E3 0.5 cm2": ("iv", (2, 2, 2), -60.0, 0.5),
      "ARCH 1M|1n (-50/+50 %)": ("arch", 1e6, 1e-9, -1), "ARCH 10M|1n (-50/+50 %)": ("arch", 10e6, 1e-9, -1)}


def cfg_el(name, extra=""):
    b = base(FINAL, None, Rin=V("ads_rin_loff"), **ENVS["typical"])
    e = EL[name]
    if e[0] == "iv":
        c = add_caps(b, CAPS); c["Re"] = Q.invivo_electrodes(e[1], e[2], e[3])
    else:
        c = mm(e[1], e[2], e[3], 0, b, CAPS)
    if extra:
        c["extra"] = (c.get("extra", "") + "\n" + extra).strip()
    return c


def artefact(H, spec):
    """in-band (0.5-40 Hz) pp of the input-referred response to a pulse train / single pulse / step (20 s window)"""
    w = 2j * np.pi * F_T; X = np.zeros_like(F_T, complex)
    for (amp, width, per) in spec.get("pulses", []):
        one = amp * (1 - np.exp(-w * width)) / w
        if per is None:
            X += one * np.exp(-w * 5.0)                                      # single event at t = 5 s
        elif per > 2.0:                                                      # slow train (Voc sample): events at 5 s + k per inside the kept window
            X += one * sum(np.exp(-w * (5.0 + kk * per)) for kk in range(int((20 - 5.0) / per) + 1))
        else:
            k = np.arange(0, int(20 / per)); ph = np.exp(-np.outer(w, k * per)).sum(axis=1) if len(k) < 2000 else None
            if ph is None:                                                   # dense train: harmonic lines only
                ph = np.where(np.abs((F_T * per) - np.round(F_T * per)) < 1e-6, 20 / per, 0)
            X += one * ph
    if spec.get("step"):
        X += spec["step"] / w * np.exp(-w * 10.0)
    Y = H * bp(F_T) * X
    sp = np.zeros(N_T, complex); sp[1:N_T // 2 + 1] = Y; sp[N_T // 2 + 1:] = np.conj(Y[:-1][::-1])
    y = np.fft.ifft(sp).real * N_T * DF
    y = y[N_T // 8:]                                                         # drop the first 2.5 s (filter start)
    return float(y.max() - y.min())


R = dict(source=dict(geometry="plate_geom_final.json (closed board v3/finish/solarband_v3f_final.kicad_pcb, plate_geom8.py)",
                     model="v3/sim/ecg sim07_v2_common (FINAL network, STRUCT 'V2-B rule: B.Cu + L5 void', chains 2 x 330 k)",
                     c_via_pF={f"{d:.2f}": (round(c_via(d, 'low') * 1e12, 4), round(c_via(d, 'high') * 1e12, 4)) for d in (0.25, 0.30, 0.35, 0.38, 0.40)},
                     c_track_pF_per_mm={k: (v[0] * 1e12, v[1] * 1e12) for k, v in C_TRK.items()}),
         activity={k: v["src"] for k, v in ACT.items()})
R["caps_E1"] = {b: net_caps("plate_E1", b) for b in ("low", "high")}
R["caps_E2"] = {b: net_caps("plate_E2", b) for b in ("low", "high")}
print("C per via (low/high pF):", R["source"]["c_via_pF"])

# A) aggressors on E1 and E2 (unit 1 pF transfer to the plate's landing node, scaled: linear)
art = {}
for en in EL:
    Hs = {pl: transfer(cfg_el(en), f"Vagg agg dg DC 0 AC 1\nCagg agg {node} 1e-12") for pl, node in (("plate_E1", "e1"), ("plate_E2", "e2"))}
    row = {}
    for net, spec in ACT.items():
        for pl in ("plate_E1", "plate_E2"):
            for b in ("low", "high"):
                c = R["caps_" + pl[-2:]][b].get(net, {}).get("total_pF", 0.0)
                v = artefact(Hs[pl], spec) * c * 1e6 if (c and (spec.get("pulses") or spec.get("step"))) else 0.0
                row.setdefault(net, {"low": 0.0, "high": 0.0})[b] += v
    row["sum_high"] = sum(v["high"] for k, v in row.items() if isinstance(v, dict))
    art[en] = row
    print(f"{en:28s} " + " ".join(f"{k} {v['high']:.4f}" for k, v in row.items() if isinstance(v, dict) and v['high'] > 1e-4) + f" | sum {row['sum_high']:.4f} uVpp", flush=True)
R["aggressor_artefact_uVpp"] = art

# B) front-end nets: cross capacitances into the network, M2 noise re-run (as g6_noise_mini.noise, lead-off 6 nA)
NF = V("ads_noise_500sps"); q = 1.602e-19


def noise(relist, extra, rch=330e3):
    cfg = add_caps(default_cfg(**FINAL, Rin=V("ads_rin_loff")), CAPS); cfg["Re"] = relist; cfg["extra"] = extra
    S.run(netlist(dict(cfg, vecg_ac=1.0), ".noise v(inp,inn) Vecg dec 40 0.5 40")); S.cmd("setplot noise1")
    f = S.vec("frequency").real; on = np.abs(S.vec("onoise_spectrum")); th = math.sqrt(np.trapezoid(on ** 2, f))
    sh = 0.0
    for (Rr, C) in (relist[0], relist[2]):
        z = abs(Rr / (1 + 2j * math.pi * f * Rr * C)); sh += np.trapezoid(2 * q * V("i_tvs_leak_typ") * z ** 2, f) + np.trapezoid(2 * q * 6e-9 * (z + 2 * rch) ** 2, f)
    ads = NF[4][0] * math.sqrt((40 - 0.5) / 131) * 1e-6
    return math.sqrt(th ** 2 + sh + ads ** 2) * 1e6 * 6.6


lines = []
for net, node in FRONT.items():
    c = R["caps_E1"]["high"].get(net, {}).get("total_pF", 0.0)
    if c and node != "e1":
        lines.append(f"Cx_{net} {node} e1 {c*1e-12:.4g}")
for net, node in E2_FRONT.items():
    c = R["caps_E2"]["high"].get(net, {}).get("total_pF", 0.0)
    if c and node != "e2":
        lines.append(f"Cx_{net} {node} e2 {c*1e-12:.4g}")
SETS = {"in-vivo nominal": Q.invivo_electrodes((1.0, 1.0, 1.0), -60.0, 0.75), "in-vivo worst of v2 (k2/0.5/2 ph-80 a3 0.5)": Q.invivo_electrodes((2.0, 0.5, 2.0), -80.0, 0.5),
        "ARCH 10M|1n": [(10e6, 1e-9)] * 3}
R["front_end_cross_caps"] = lines
R["noise_uVpp"] = {sn: dict(without=noise(rel, ""), with_caps=noise(rel, "\n".join(lines))) for sn, rel in SETS.items()}
for sn, v in R["noise_uVpp"].items():
    print(f"noise {sn}: {v['without']:.4f} -> {v['with_caps']:.4f} uVpp")
FLOOR = NF[4][0] * math.sqrt((40 - 0.5) / 131) * 6.6
worst = max(r["sum_high"] for r in art.values())
R["M2"] = dict(floor_uVpp=FLOOR, worst_aggressor_sum_uVpp=worst, total_uVpp=FLOOR + worst, limit_uVpp=10.0,
               verdict="PASS" if FLOOR + worst <= 10.0 else "FAIL", rule="floor (input short, display off F-9) + linear sum of the aggressor artefacts at the high C bound", flags=sorted(FIX))
H1 = transfer(cfg_el("ARCH 10M|1n (-50/+50 %)"), "Vagg agg dg DC 0 AC 1\nCagg agg e1 1e-12")
R["allowed_pF_alone_ARCH10M_E1"] = {net: ((10.0 - FLOOR) / (artefact(H1, s) * 1e6) if (s.get("pulses") or s.get("step")) else None) for net, s in ACT.items()}
R["runtime_s"] = time.time() - t0
tag = "_".join(sorted(FIX)) or "base"
(HERE / f"sim07_final_{tag}.json").write_text(json.dumps(R, indent=1))
print(json.dumps(R["M2"]), "\nallowed pF alone:", {k: (round(v, 3) if v else v) for k, v in R["allowed_pF_alone_ARCH10M_E1"].items()}, "\n%.0f s" % R["runtime_s"])
