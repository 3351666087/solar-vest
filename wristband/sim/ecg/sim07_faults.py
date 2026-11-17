"""SIM-07 / ARCH §7.3: patient DC current in normal condition and under faults, ngspice DC with the full front end
(final design), the RLD amplifier active and free to rail, wet-skin electrodes (1 kΩ, worst case) and body 300 Ω.

Patient current = largest DC current through any electrode (E1, E2, E3), from the half-cell source branch currents.
Criteria (ARCH §1.5 / SIM-07): < 10 µA normal; < 10 µA with a pin at its rail; < 10 µA with a pin at its rail AND one
330 kΩ shorted. Extra (informational): LDO pass-device short (AVDD = VBAT up to 4.25 V), TVS short, lead-off
register mis-set to 6/22 µA, TVS short combined with a pin at a rail or with a resistor short (double faults, beyond the
ARCH criterion), and the ARCH hand bound (return through 0 Ω).
Writes results/sim07_patient_current.json.
"""
import json, itertools, time
from sim07_common import default_cfg, dc_point, V, HERE, FINAL

t0 = time.time()
RE_WET = V("electrode_R_fault")
BASE = dict(FINAL, Re=[(RE_WET, 10e-9)] * 3, Rin=V("ads_rin_loff"), Iloff=6e-9 * 1.1,
            Itvs=[V("i_tvs_leak_max")] * 3, Ib=[V("ads_ib_fullT")] * 2)
CRIT = 10e-6
RES = []


def run(name, cls, faults=None, avdd=None, **kw):
    cfg = default_cfg(**dict(BASE, **kw))
    cfg["faults"] = faults or {}
    if avdd: cfg["avdd"] = avdd
    worst = 0.0
    for vhc in ([0, 0, 0], [0.3, -0.3, 0.0], [-0.3, 0.3, 0.0], [0.3, 0.0, -0.3], [-0.3, 0.0, 0.3]):
        cfg["Vhc"] = vhc
        o = dc_point(cfg)
        worst = max(worst, max(abs(i) for i in o["i"]))
    row = dict(case=name, cls=cls, i_patient_uA=worst * 1e6, pass_=worst < CRIT if cls in ("normal", "SFC", "ARCH-double") else None)
    RES.append(row)
    print(f"{cls:12s} {name:48s} {worst*1e6:7.3f} µA {'PASS' if worst < CRIT else 'over 10 µA'}", flush=True)
    return worst


run("normal (6 nA lead-off, TVS 100 nA, bias 1 nA)", "normal")
run("lead-off register mis-set 6 µA", "misconfig", Iloff=6e-6 * 1.1)
run("lead-off register mis-set 22 µA", "misconfig", Iloff=22e-6 * 1.1)
pins = {"IN1P->AVDD": {"pin_high1": 1}, "IN1P->AVSS": {"pin_low1": 1}, "IN1N->AVDD": {"pin_high3": 1},
        "IN1N->AVSS": {"pin_low3": 1}, "RLDOUT->AVDD": {"rld_high": 1}, "RLDOUT->AVSS": {"rld_low": 1}}
shorts = {f"R{ab}{i} short": {f"short_{ab}{i}": 1} for i in (1, 2, 3) for ab in ("a", "b")}
for n, f in pins.items():
    run(n, "SFC", f)
for n, f in shorts.items():
    run(n, "SFC", f)
for i in (1, 2, 3):
    run(f"TVS on E{i} shorted", "SFC", {f"tvs_short{i}": 1})
run("LDO pass short: AVDD = 4.25 V", "SFC", avdd=4.25)
worst_double = 0.0
for (pn, pf), (sn, sf) in itertools.product(pins.items(), shorts.items()):
    worst_double = max(worst_double, run(f"{pn} + {sn}", "ARCH-double", {**pf, **sf}))
print(f"ARCH 'pin at rail + one resistor shorted', worst of {len(pins)*len(shorts)}: {worst_double*1e6:.2f} µA")
for (pn, pf), (sn, sf) in itertools.product(pins.items(), shorts.items()):
    run(f"AVDD 4.25 V + {pn} + {sn}", "triple(info)", {**pf, **sf}, avdd=4.25)
for (pn, pf), i in itertools.product(pins.items(), (1, 2, 3)):
    run(f"{pn} + TVS E{i} shorted", "double(info)", {**pf, f"tvs_short{i}": 1})
worst_tvs_r = 0.0
for i, (sn, sf) in itertools.product((1, 2, 3), shorts.items()):
    worst_tvs_r = max(worst_tvs_r, run(f"TVS E{i} shorted + {sn}", "double(info)", {f"tvs_short{i}": 1, **sf}))
print(f"double fault 'TVS short + one resistor shorted', worst of {3*len(shorts)}: {worst_tvs_r*1e6:.2f} µA")
hand = dict(pin_at_rail=V("avdd") / (2 * V("r_prot")), pin_at_rail_plus_short=V("avdd") / V("r_prot"),
            with_halfcells_0p6V=dict(pin_at_rail=(V("avdd") + 0.6) / (2 * V("r_prot")),
                                     pin_at_rail_plus_short=(V("avdd") + 0.6) / V("r_prot")),
            note="ARCH §7.3 hand bound: return path of 0 Ω (needs a second fault such as a TVS short)")
out = dict(results=RES, worst_arch_double_uA=worst_double * 1e6, worst_tvs_plus_R_short_uA=worst_tvs_r * 1e6,
           worst_by_class_uA={c: max(r["i_patient_uA"] for r in RES if r["cls"] == c) for c in sorted({r["cls"] for r in RES})},
           all_arch_cases_pass=all(r["pass_"] for r in RES if r["pass_"] is not None),
           design={k: (list(v) if isinstance(v, tuple) else v) for k, v in FINAL.items()},
           hand_bound_A=hand, electrode_R=RE_WET,
           crit_A=CRIT, runtime_s=time.time() - t0)
(HERE / "results" / "sim07_patient_current.json").write_text(json.dumps(out, indent=1))
print(f"done {time.time()-t0:.0f} s")
