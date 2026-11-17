"""V3-G6 / SIM-07 case 2: patient DC current for V3-F in normal condition and single faults, with the V3-F contacts:
the top-rim GND charge contact (J18, = board GND) touched by one finger while another finger is on E3, and the + contact
(J15 -> VBUS_K -> D14 -> VBUS -> R144 + R145 = 2 MOhm to GND) touched with no head attached.
Harness = sim07_v2_faults.py (same DC network: v3/design/src/ecg.py keeps TVS -> 330 k -> 330 k per electrode).
Finger on a contact: 'Rcm rf dg R' (wet 1 kOhm, dry 100 kOhm). The + contact: 2 MOhm (D14 forward drop ignored: conservative).
Seal single faults (V2-B class): an internal net reaches the skin / a plate / E3 through 1 kOhm of sweat.
Fix option modelled: the GND contact behind an N-FET that is off without the head (leakage bound 1 uA at 4.25 V -> 4.25 MOhm).
Criterion as written (BASELINE 18, V3-G6): < 10 uA patient DC in normal and single-fault condition (IEC SFC limit 50 uA, information).
Writes results/g6_patient_dc.json."""
import json, itertools, time
from sim07_v2_common import default_cfg, dc_point, V, HERE, FINAL, STRUCT, add_caps, S

t0 = time.time()
RE_WET = V("electrode_R_fault")
BASE = dict(FINAL, Re=[(RE_WET, 10e-9)] * 3, Rin=V("ads_rin_loff"), Iloff=6e-9 * 1.1, Itvs=[V("i_tvs_leak_max")] * 3, Ib=[V("ads_ib_fullT")] * 2)
CRIT, LIM = 10e-6, 50e-6
RES = []
HC = ([0, 0, 0], [0.3, -0.3, 0.0], [-0.3, 0.3, 0.0], [0.3, 0.0, -0.3], [-0.3, 0.0, 0.3], [0.3, 0.3, 0.3], [-0.3, -0.3, -0.3])
AFE = {"AFE on": dict(avdd=3.0), "AFE off": dict(avdd=1e-3, Iloff=0.0, Ib=[0.0, 0.0])}
GNDC = {"wet 1k": 1e3, "dry 100k": 100e3}


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


# normal condition
run("normal, no contact touched", "normal")
for (gn, rg), (an, akw) in itertools.product(GNDC.items(), AFE.items()):
    run(f"normal, finger on the GND contact ({gn}) [{an}]", "normal", rcm=rg, **akw)
    run(f"normal, finger on the GND contact ({gn}) + finger on the + contact (no head, 2 M) [{an}]", "normal", rcm=rg, rvb=2e6, **akw)
# ARCH single faults with the GND contact touched (wet)
pins = {"IN1P->AVDD": {"pin_high1": 1}, "IN1P->AVSS": {"pin_low1": 1}, "IN1N->AVDD": {"pin_high3": 1}, "IN1N->AVSS": {"pin_low3": 1},
        "RLDOUT->AVDD": {"rld_high": 1}, "RLDOUT->AVSS": {"rld_low": 1}}
shorts = {f"R{ab}{i} short": {f"short_{ab}{i}": 1} for i in (1, 2, 3) for ab in ("a", "b")}
for n, f in itertools.chain(pins.items(), shorts.items()):
    run(f"SFC {n}", "SFC", f)
    run(f"SFC {n} + finger on the GND contact (wet 1k)", "SFC+GND", f, rcm=1e3)
for i in (1, 2, 3):
    run(f"SFC TVS on E{i} shorted + finger on the GND contact (wet 1k)", "SFC+GND", {f"tvs_short{i}": 1}, rcm=1e3)
run("SFC LDO pass short AVDD 4.25 V + finger on the GND contact (wet 1k)", "SFC+GND", avdd=4.25, rcm=1e3)
run("SFC lead-off current mis-set 22 uA + finger on the GND contact (wet 1k)", "SFC+GND", Iloff=22e-6 * 1.1, rcm=1e3)
# seal single faults (internal net -> skin / plate / E3 through 1 kOhm sweat), with and without the GND-contact finger
SRC = {"VBAT / VSTOR 4.25 V": 4.25, "PV+ 3.17 V": 3.17, "VDD_DISP 3.05 V": 3.05, "VDD_1V8 1.91 V": 1.91}
SITE = {"skin under the pod": "lw", "plate E1": "e1", "E3 / finger": "rf"}
for (sn, vs), (tn, node) in itertools.product(SRC.items(), SITE.items()):
    for an, akw in AFE.items():
        run(f"seal: {sn} -> {tn} [{an}]", "seal", leak=(vs, node, 1e3), quiet=True, **akw)
        run(f"seal: {sn} -> {tn} + finger on the GND contact (wet 1k) [{an}]", "seal+GND", leak=(vs, node, 1e3), rcm=1e3, quiet=True, **akw)
        run(f"seal: {sn} -> {tn} + finger on the GND contact (dry 100k) [{an}]", "seal+GND", leak=(vs, node, 1e3), rcm=100e3, quiet=True, **akw)
        run(f"FIX (GND contact behind an off N-FET, <= 1 uA): {sn} -> {tn} + finger on the GND contact [{an}]", "fix", leak=(vs, node, 1e3), rcm=4.25e6, quiet=True, **akw)
for i in (1, 2, 3):
    run(f"FIX (GND-contact N-FET off): TVS on E{i} shorted + finger on the GND contact (wet 1k)", "fix", {f"tvs_short{i}": 1}, rcm=4.25e6)
for an, akw in AFE.items():
    run(f"FIX (GND-contact N-FET off) + chains 2 x 680 k: 4.25 V -> E3 / finger + finger on the GND contact [{an}]", "fix+680k", leak=(4.25, "rf", 1e3), rcm=4.25e6, Rprot=[(680e3, 680e3)] * 3, **akw)
    run(f"FIX (GND-contact N-FET off) + chains 2 x 680 k: 4.25 V -> skin under the pod + finger on the GND contact [{an}]", "fix+680k", leak=(4.25, "lw", 1e3), rcm=4.25e6, Rprot=[(680e3, 680e3)] * 3, **akw)
    run(f"chains 2 x 680 k: normal, finger on the GND contact wet 1k (no FET) [{an}]", "fix+680k", rcm=1e3, Rprot=[(680e3, 680e3)] * 3, **akw)
cls = sorted({r["cls"] for r in RES})
out = dict(results=RES, worst_by_class_uA={c: max(r["i_patient_uA"] for r in RES if r["cls"] == c) for c in cls},
           worst_case_by_class={c: max((r for r in RES if r["cls"] == c), key=lambda r: r["i_patient_uA"])["case"] for c in cls},
           crit_A=CRIT, sfc_limit_A=LIM, electrode_R=RE_WET, runtime_s=time.time() - t0)
(HERE / "results" / "g6_patient_dc.json").write_text(json.dumps(out, indent=1))
for c in cls: print(f"worst {c:10s} {out['worst_by_class_uA'][c]:10.3f} uA  {out['worst_case_by_class'][c]}")
print(f"done {time.time()-t0:.0f} s")
