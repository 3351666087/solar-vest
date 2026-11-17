"""V3-G6 / SIM-07 case 2: patient DC current for V3-F in normal condition and single faults, with the V3-F contacts:
the top-rim GND charge contact (J18, = board GND) touched by one finger while another finger is on E3, and the + contact
(J15 -> VBUS_K -> D14 -> VBUS -> R144 + R145 = 2 MOhm to GND) touched with no head attached.
Harness = sim07_v2_faults.py (same DC network: v3/design/src/ecg.py keeps TVS -> 330 k -> 330 k per electrode).
Finger on a contact: 'Rcm rf dg R' (wet 1 kOhm, dry 100 kOhm). The + contact: 2 MOhm (D14 forward drop ignored: conservative).
Seal single faults (V2-B class): an internal net reaches the skin / a plate / E3 through 1 kOhm of sweat.
Fix option modelled: the GND contact behind an N-FET that is off without the head (leakage bound 1 uA at 4.25 V -> 4.25 MOhm).
Criterion as written (BASELINE 18, V3-G6): < 10 uA patient DC in normal and single-fault condition (IEC SFC limit 50 uA, information).
Writes results/g6_patient_dc.json."""
# ===== mini-ECO copy (LEAD_NOTES 2f F-1/F-2/F-3): chains 2 x 330 k, J18 bound = Q20 IDSS 1 uA + D15 TPD1E10B06 100 nA. Writes results/mini/g6_patient_dc_mini.json.
# ===== Stage-2b ECO copy (g6_faults_eco.py; g6_faults.py and results/g6_patient_dc.json stay as "before") =====
# As built after the ECO (v3/design, 2026-11-15): chains 2 x 680 k (R301-R306), J18 behind Q20 PMZ290UNE2 (off without a head:
# IDSS <= 1 uA at 20 V, the only published bound -> 4.25 MOhm at 4.25 V; also run at IDSS 0.1 uA = 42.5 MOhm for the sensitivity),
# the + contact (no head) now sees R509 + R510 = 1.1 MOhm to GND in parallel with D14 -> 2 MOhm: 0.71 MOhm (diode drop ignored).
# A finger on J18 meets the body diode only when the skin is below board GND (no such source among the seal faults).
# Writes results/eco/g6_patient_dc_eco.json.
import json, itertools, time
from sim07_v2_common import default_cfg, dc_point, V, HERE, FINAL, STRUCT, add_caps, S

t0 = time.time()
RE_WET = V("electrode_R_fault")
R330 = [(330e3, 330e3)] * 3   # [mini-ECO F-2] back to 2 x 330 k anti-surge
BASE = dict(FINAL, Rprot=R330, Re=[(RE_WET, 10e-9)] * 3, Rin=V("ads_rin_loff"), Iloff=6e-9 * 1.1, Itvs=[V("i_tvs_leak_max")] * 3, Ib=[V("ads_ib_fullT")] * 2)
CRIT, LIM = 10e-6, 50e-6   # [mini-ECO F-3] normal <= 10 uA, single fault <= 50 uA (IEC 60601-1); both reported
RES = []
HC = ([0, 0, 0], [0.3, -0.3, 0.0], [-0.3, 0.3, 0.0], [0.3, 0.0, -0.3], [-0.3, 0.0, 0.3], [0.3, 0.3, 0.3], [-0.3, -0.3, -0.3])
AFE = {"AFE on": dict(avdd=3.0), "AFE off": dict(avdd=1e-3, Iloff=0.0, Ib=[0.0, 0.0])}
import os
R_GATE = float(os.environ.get("SB_RGATE", 1.1e6))     # R509 + R510 (as ruled: 100 k + 1 M)
I_D15 = V("i_tvs_leak_max")   # [mini-ECO F-1] D15 TPD1E10B06 100 nA max at 5 V (SLLSEB1G p5), in parallel with Q20 off
R_J18 = 4.25 / (1e-6 + I_D15); R_J18_LO = 4.25 / (0.1e-6 + I_D15); R_PLUS = 1 / (1 / R_GATE + 1 / 2e6)
GNDC = {"wet 1k (behind Q20 off, IDSS 1 uA bound)": R_J18, "IDSS 0.1 uA": R_J18_LO}


def run(name, cls, faults=None, avdd=None, leak=None, rcm=None, rvb=None, quiet=False, **kw):
    cfg = add_caps(default_cfg(**dict(BASE, **kw)), STRUCT["V2-B rule: B.Cu + L5 void"])
    cfg["faults"] = faults or {}
    if avdd is not None: cfg["avdd"] = avdd
    ex = []
    if leak: ex += ["Vleak vlk dg DC %g" % leak[0], "Rleak vlk %s %g" % (leak[1], leak[2])]
    if rcm: ex += ["Vcm rf cmx DC 0", "Rcm cmx dg %g" % rcm]
    if rvb: ex += ["Vvb rf vbx DC 0", "Rvb vbx dg %g" % rvb]
    cfg["extra"] = "\n".join(ex)
    we = wl = wc = 0.0
    for vhc in HC:
        cfg["Vhc"] = vhc
        o = dc_point(cfg)
        we = max(we, max(abs(i) for i in o["i"]))
        if leak: wl = max(wl, abs(float(S.vec("vleak#branch")[-1])))
        if rcm: wc = max(wc, abs(float(S.vec("vcm#branch")[-1])))
        if rvb: wc = max(wc, abs(float(S.vec("vvb#branch")[-1])))
    w = max(we, wl, wc)
    RES.append(dict(case=name, cls=cls, i_patient_uA=w * 1e6, i_electrode_max_uA=we * 1e6, i_leak_uA=wl * 1e6, i_contact_uA=wc * 1e6,
                    pass_10uA=bool(w < CRIT), pass_50uA=bool(w < LIM)))
    if not quiet:
        print(f"{cls:12s} {name:92s} {w*1e6:9.3f} uA {'< 10' if w < CRIT else ('10-50' if w < LIM else '> 50')}", flush=True)
    return w


# normal condition (ECO topology)
run("normal, no contact touched", "normal")
for (gn, rg), (an, akw) in itertools.product(GNDC.items(), AFE.items()):
    run(f"normal, finger on the GND contact ({gn}) [{an}]", "normal", rcm=rg, **akw)
    run(f"normal, finger on the GND contact ({gn}) + finger on the + contact (no head, 1.1 M || 2 M) [{an}]", "normal", rcm=rg, rvb=R_PLUS, **akw)
    run(f"normal, finger on the + contact only (no head, 1.1 M || 2 M) [{an}]", "normal", rvb=R_PLUS, **akw)
# ARCH single faults with the GND contact touched
pins = {"IN1P->AVDD": {"pin_high1": 1}, "IN1P->AVSS": {"pin_low1": 1}, "IN1N->AVDD": {"pin_high3": 1}, "IN1N->AVSS": {"pin_low3": 1},
        "RLDOUT->AVDD": {"rld_high": 1}, "RLDOUT->AVSS": {"rld_low": 1}}
shorts = {f"R{ab}{i} short": {f"short_{ab}{i}": 1} for i in (1, 2, 3) for ab in ("a", "b")}
for n, f in itertools.chain(pins.items(), shorts.items()):
    run(f"SFC {n}", "SFC", f)
    run(f"SFC {n} + finger on the GND contact (Q20 off)", "SFC+GND", f, rcm=R_J18)
    run(f"SFC {n} + finger on the + contact (no head)", "SFC+GND", f, rvb=R_PLUS)
for i in (1, 2, 3):
    run(f"SFC TVS on E{i} shorted + finger on the GND contact (Q20 off)", "SFC+GND", {f"tvs_short{i}": 1}, rcm=R_J18)
    run(f"SFC TVS on E{i} shorted + finger on the + contact (no head)", "SFC+GND", {f"tvs_short{i}": 1}, rvb=R_PLUS)
    run(f"SFC Q20 shorted (J18 = GND) + finger on the GND contact wet 1k, TVS on E{i} intact", "SFC+GND", rcm=1e3)
run("SFC LDO pass short AVDD 4.25 V + finger on the GND contact (Q20 off)", "SFC+GND", avdd=4.25, rcm=R_J18)
run("SFC lead-off current mis-set 22 uA + finger on the GND contact (Q20 off)", "SFC+GND", Iloff=22e-6 * 1.1, rcm=R_J18)
run("DOUBLE (information): Q20 shorted + LDO pass short AVDD 4.25 V, finger wet 1k on J18", "double (info)", avdd=4.25, rcm=1e3)
# seal single faults (internal net -> skin / plate / E3 through 1 kOhm sweat)
SRC = {"VBAT / VSTOR 4.25 V": 4.25, "PV+ 3.17 V": 3.17, "VDD_DISP 3.05 V": 3.05, "VDD_1V8 1.91 V": 1.91}
SITE = {"skin under the pod": "lw", "plate E1": "e1", "E3 / finger": "rf"}
for (sn, vs), (tn, node) in itertools.product(SRC.items(), SITE.items()):
    for an, akw in AFE.items():
        run(f"seal: {sn} -> {tn} [{an}]", "seal", leak=(vs, node, 1e3), quiet=True, **akw)
        run(f"seal: {sn} -> {tn} + finger on the GND contact (Q20 off, IDSS 1 uA bound) [{an}]", "seal+GND", leak=(vs, node, 1e3), rcm=R_J18, quiet=True, **akw)
        run(f"seal: {sn} -> {tn} + finger on the GND contact (Q20 off, IDSS 0.1 uA) [{an}]", "seal+GND IDSS0.1", leak=(vs, node, 1e3), rcm=R_J18_LO, quiet=True, **akw)
        run(f"seal: {sn} -> {tn} + finger on the + contact (no head) [{an}]", "seal+GND", leak=(vs, node, 1e3), rvb=R_PLUS, quiet=True, **akw)
cls = sorted({r["cls"] for r in RES})
out = dict(r_gate_ohm=R_GATE, r_plus_contact_ohm=R_PLUS, results=RES, worst_by_class_uA={c: max(r["i_patient_uA"] for r in RES if r["cls"] == c) for c in cls},
           worst_case_by_class={c: max((r for r in RES if r["cls"] == c), key=lambda r: r["i_patient_uA"])["case"] for c in cls},
           crit_A=CRIT, sfc_limit_A=LIM, electrode_R=RE_WET, runtime_s=time.time() - t0)
(HERE / "results" / "mini" / "g6_patient_dc_mini.json").write_text(json.dumps(out, indent=1))
for c in cls: print(f"worst {c:10s} {out['worst_by_class_uA'][c]:10.3f} uA  {out['worst_case_by_class'][c]}")
print(f"done {time.time()-t0:.0f} s")
