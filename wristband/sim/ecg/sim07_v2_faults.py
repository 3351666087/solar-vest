"""SIM-07 / ARCH 1.5, 7.3 for V2-B: patient DC current in normal condition and under single faults.
Part 1 re-runs the v1 fault list (sim07_faults.py: normal, pin at a rail, one 330 kOhm shorted, TVS shorted, LDO pass short,
        'pin at rail + one resistor shorted') on the V2-B network. The DC network of the ECG chain is unchanged, so the numbers
        must equal v1; a difference would be a modelling error.
Part 2 adds the single faults that the bonded structure makes possible (REDESIGN 8.1 skin-safety row, review R-14):
        a seal fault lets sweat reach a node that is NOT behind the 2 x 330 kOhm, or a film defect ties a plate to board copper.
        Each case with the ECG front end powered (AVDD 3.0 V) and unpowered (AVDD 0 V: the input pins then clamp to the 0 V rail
        through their ESD diodes and become return paths), wet skin (1 kOhm electrodes, 1 kOhm leak path).
        Patient current = current that the leak source drives through the body (and the largest electrode current).
Criterion: ARCH 1.5 '< 10 uA normal and < 10 uA with any single resistor shorted (design target; the single-fault limit is 50 uA)'.
Writes results/sim07_v2_patient_current.json."""
import json, itertools, time
from sim07_v2_common import default_cfg, dc_point, V, HERE, FINAL, STRUCT, add_caps, S

t0 = time.time()
RE_WET = V("electrode_R_fault")
BASE = dict(FINAL, Re=[(RE_WET, 10e-9)] * 3, Rin=V("ads_rin_loff"), Iloff=6e-9 * 1.1, Itvs=[V("i_tvs_leak_max")] * 3, Ib=[V("ads_ib_fullT")] * 2)
CRIT, LIM = 10e-6, 50e-6
RES = []
HC = ([0, 0, 0], [0.3, -0.3, 0.0], [-0.3, 0.3, 0.0], [0.3, 0.0, -0.3], [-0.3, 0.0, 0.3], [0.3, 0.3, 0.3], [-0.3, -0.3, -0.3])


def run(name, cls, faults=None, avdd=None, leak=None, quiet=False, **kw):
    """leak = (volts, node, ohms): a source of that voltage (against device ground) reaches the node through that resistance"""
    cfg = add_caps(default_cfg(**dict(BASE, **kw)), STRUCT["V2-B rule: B.Cu + L5 void"])
    cfg["faults"] = faults or {}
    if avdd is not None: cfg["avdd"] = avdd
    if leak: cfg["extra"] = "Vleak vlk dg DC %g\nRleak vlk %s %g" % leak
    worst_e, worst_l = 0.0, 0.0
    for vhc in HC:
        cfg["Vhc"] = vhc
        o = dc_point(cfg)
        worst_e = max(worst_e, max(abs(i) for i in o["i"]))
        if leak: worst_l = max(worst_l, abs(float(S.vec("vleak#branch")[-1])))
    w = max(worst_e, worst_l)
    row = dict(case=name, cls=cls, i_patient_uA=w * 1e6, i_electrode_max_uA=worst_e * 1e6, i_leak_uA=worst_l * 1e6,
               pass_10uA=bool(w < CRIT), pass_50uA=bool(w < LIM))
    RES.append(row)
    if not quiet:
        print(f"{cls:14s} {name:86s} {w*1e6:7.3f} uA (electrode max {worst_e*1e6:6.3f}, leak {worst_l*1e6:6.3f}) {'< 10 uA' if w < CRIT else ('> 10 uA, < 50 uA' if w < LIM else '> 50 uA')}", flush=True)
    return w


# ---------------------------------------------------------------- part 1: the v1 list
run("normal (6 nA lead-off, TVS 100 nA each, bias 1 nA)", "normal")
pins = {"IN1P->AVDD": {"pin_high1": 1}, "IN1P->AVSS": {"pin_low1": 1}, "IN1N->AVDD": {"pin_high3": 1}, "IN1N->AVSS": {"pin_low3": 1},
        "RLDOUT->AVDD": {"rld_high": 1}, "RLDOUT->AVSS": {"rld_low": 1}}
shorts = {f"R{ab}{i} short": {f"short_{ab}{i}": 1} for i in (1, 2, 3) for ab in ("a", "b")}
for n, f in pins.items(): run(n, "SFC", f)
for n, f in shorts.items(): run(n, "SFC", f)
for i in (1, 2, 3): run(f"TVS on E{i} shorted (= plate tied to ground by a film defect)", "SFC", {f"tvs_short{i}": 1})
run("LDO pass short: AVDD = 4.25 V", "SFC", avdd=4.25)
wd = 0.0
for (pn, pf), (sn, sf) in itertools.product(pins.items(), shorts.items()):
    wd = max(wd, run(f"{pn} + {sn}", "ARCH-double", {**pf, **sf}, quiet=True))
print(f"ARCH 'pin at rail + one resistor shorted', worst of {len(pins)*len(shorts)}: {wd*1e6:.2f} uA", flush=True)
run("lead-off register mis-set 6 uA", "misconfig", Iloff=6e-6 * 1.1)
run("lead-off register mis-set 22 uA", "misconfig", Iloff=22e-6 * 1.1)

# ---------------------------------------------------------------- part 2: V2-B structure
SRC = {"VSTOR / VBAT / VLED 4.25 V": 4.25, "PV+ 3.17 V (Voc at -10 C)": 3.17, "AVDD_ECG 3.0 V": 3.0, "VDD_1V8 1.91 V": 1.91}
SITE = {"skin under the band (sweat past a seal: cap bond at the LED anode lands, floor film at J8, lid bead at the PV tail)": "lw",
        "plate E1 (film defect to a via / copper of that net)": "e1", "plate E2": "e2", "E3 strip / finger (lid edge, top rim)": "rf"}
AFE = {"AFE on": dict(avdd=3.0), "AFE off": dict(avdd=1e-3, Iloff=0.0, Ib=[0.0, 0.0])}
for (sn, vs), (tn, node), (an, akw) in itertools.product(SRC.items(), SITE.items(), AFE.items()):
    if sn.startswith("AVDD") and an == "AFE off": continue
    run(f"{sn} -> {tn[:44]} [{an}]", "V2B-seal", leak=(vs, node, 1e3), **akw)
# design-rule cases (netclasses.json PLATE_VOID: under a plate only GND and nets behind >= 100 kOhm)
for an, akw in AFE.items():
    run(f"4.25 V net behind 100 kOhm -> plate E1 [{an}]", "V2B-rule", leak=(4.25, "e1", 100e3 + 1e3), **akw)
    run(f"4.25 V net behind 100 kOhm -> skin [{an}]", "V2B-rule", leak=(4.25, "lw", 100e3 + 1e3), **akw)
# seal fault + one resistor shorted (double, information)
w2 = 0.0
for (sn_, sf), (an, akw) in itertools.product(shorts.items(), AFE.items()):
    w2 = max(w2, run(f"4.25 V -> skin + {sn_} [{an}]", "V2B-double", sf, leak=(4.25, "lw", 1e3), quiet=True, **akw))
print(f"seal fault (4.25 V to the skin) + one 330 kOhm shorted, worst: {w2*1e6:.2f} uA", flush=True)
# what series resistance per electrode would keep the 4.25 V seal fault below 10 uA with the AFE off
need = {}
for rp in (330e3, 470e3, 560e3, 680e3):
    need[f"2 x {rp/1e3:g}k"] = run(f"4.25 V -> skin, chains 2 x {rp/1e3:g} k [AFE off]", "V2B-option", leak=(4.25, "lw", 1e3), Rprot=[(rp, rp)] * 3, **AFE["AFE off"]) * 1e6
# contacts variant: C- (ground) in the top face touched by the other hand
for rc, rn in ((1e3, "wet 1 kOhm"), (100e3, "dry 100 kOhm")):
    for an, akw in AFE.items():
        cfg_extra = "Rcm rf dg %g" % rc
        run(f"CONTACTS: finger on C- ({rn}), no fault [{an}]", "contacts", extra=cfg_extra, **akw)
    for vs, sn in ((4.25, "4.25 V"), (3.17, "PV+ 3.17 V")):
        cfg = add_caps(default_cfg(**dict(BASE, **AFE["AFE off"])), STRUCT["V2-B rule: B.Cu + L5 void"])
        cfg["extra"] = "Vleak vlk dg DC %g\nRleak vlk lw 1k\nRcm rf dg %g" % (vs, rc)
        o = dc_point(cfg); il = abs(float(S.vec("vleak#branch")[-1]))
        RES.append(dict(case=f"CONTACTS: {sn} -> skin + finger on C- ({rn})", cls="contacts-seal", i_patient_uA=il * 1e6, i_electrode_max_uA=max(abs(i) for i in o["i"]) * 1e6,
                        i_leak_uA=il * 1e6, pass_10uA=bool(il < CRIT), pass_50uA=bool(il < LIM)))
        print(f"{'contacts-seal':14s} {'CONTACTS: ' + sn + ' -> skin + finger on C- (' + rn + ')':86s} {il*1e6:9.1f} uA", flush=True)
cls = sorted({r["cls"] for r in RES})
out = dict(results=RES, worst_by_class_uA={c: max(r["i_patient_uA"] for r in RES if r["cls"] == c) for c in cls},
           worst_case_by_class={c: max((r for r in RES if r["cls"] == c), key=lambda r: r["i_patient_uA"])["case"] for c in cls},
           arch_cases_pass=all(r["pass_10uA"] for r in RES if r["cls"] in ("normal", "SFC", "ARCH-double")),
           option_series_R_uA=need, crit_A=CRIT, single_fault_limit_A=LIM, electrode_R=RE_WET, runtime_s=time.time() - t0,
           hand_bound=dict(seal_fault_afe_off_uA=3 * (4.25 + 0.3 - 0.5) / 660e3 * 1e6, note="three chains of 660 kOhm to pins clamped 0.5 V above the 0 V rail, half-cell 0.3 V"))
(HERE / "results" / "sim07_v2_patient_current.json").write_text(json.dumps(out, indent=1))
print("worst by class (uA):", {k: round(v, 2) for k, v in out["worst_by_class_uA"].items()})
print(f"done {time.time()-t0:.0f} s")
