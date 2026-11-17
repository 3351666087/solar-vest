"""V3-G6 hand models (no SPICE): (3) AC patient leakage through the charging head while worn, VBUS lock-out;
(4) reversed head -5 V; (6) strap-root 1 Ohm short with the pack fuse F1 (thermal time to the 43 C skin limit).
Inputs: v3/head/HEAD.md 7.2-7.3 (barrier 4.84 pF, 10 pF bound; source = open-circuit voltage behind a capacitance sized to
its touch-current class, ENG_A 5.1 model; Class II output floats at about mains / 2), v3/design src/charger.py, CALC_V3F 8,
JLC C896422 (NSR0240: 550 nA at 25 V), C478155 (PMZ290UNE2: VGS(th) 0.95 V), v2 CALC 2 (XB5358D0: IOV1 2.5-4.1 A,
RSS(on) <= 54 mOhm; cell DC resistance <= 1 Ohm). Writes results/g6_calc.json."""
import json, math, pathlib
from scipy.special import erfc
from scipy.optimize import brentq
HERE = pathlib.Path(__file__).resolve().parent
W = 2 * math.pi * 60.0
OUT = {}
# ---------------- (3) AC patient leakage
VM = 264.0; VOC2 = VM / 2; MD = 1e3
def i_src(voc, i_class, cb):
    cs = i_class / (W * voc)
    zs = 1 / (1j * W * cs) + (1 / (1j * W * cb) if cb else 0) + MD
    return abs(voc / zs)
rows = []
for head, cb_typ in (("UCC12050 reinforced", 4.84e-12), ("UCC12040 basic", 4.84e-12)):
    for src, ic in (("Class II charger 0.25 mA class", 0.25e-3), ("Class II charger 0.5 mA class", 0.5e-3), ("pass-through power bank on a 0.5 mA charger", 0.5e-3)):
        nc = i_src(VOC2, ic, 10e-12); nct = i_src(VOC2, ic, cb_typ); sfc = i_src(VOC2, ic, None)
        rows.append(dict(head=head, source=src, NC_uA_10pF=nc * 1e6, NC_uA_typ=nct * 1e6, SFC_barrier_shorted_uA=sfc * 1e6,
                         NC_pass=nc <= 100e-6, SFC_pass_as_written=sfc <= 500e-6, SFC_margin_pct=(500e-6 - sfc) / 500e-6 * 100))
    rows.append(dict(head=head, source="mains on the applied part (IEC test, 264 V through the barrier)", NC_uA_10pF=VM * W * 10e-12 * 1e6))
OUT["ac_leakage"] = dict(rows=rows, misuse_non_isolated_cable_uA=[i_src(VOC2, 0.25e-3, None) * 1e6, i_src(VOC2, 0.5e-3, None) * 1e6],
                         note="band side adds nothing in series: the TVS D5-D7 clamp the electrode pads to GND ahead of the 330 k chains; "
                              "AVDD off (Q9) does not open that path")
# VBUS lock-out (Q9)
vth_max = 0.95
OUT["vbus_lockout"] = dict(vb_det_at_head_min_V=5.1 / 2, vbus_needed_for_lockout_V=2 * vth_max, q9_overdrive_V=5.1 / 2 - vth_max,
                           avdd_en_when_locked_uV=1.8 * 0.5 / 220e3 * 1e6,
                           gaps=["no lock-out while a head is on but not driving (pin check pending / failed) or reversed: VBUS = 0; leakage then = intact-barrier NC value"])
# ---------------- (4) reversed head
ir = {"25 C, 25 V spec max": 0.55e-6, "45 C (x2 per 10 K, estimate)": 0.55e-6 * 4}
OUT["reversed_head"] = dict(d13_conducts=False, d14_blocks=True, i_rev_uA={k: v * 1e6 for k, v in ir.items()},
                            vbus_unclamped_V={k: -v * 2e6 for k, v in ir.items()}, vbus_typ_20nA_V=-20e-9 * 2e6, u15_in_absmax_V=-0.3,
                            note="with max IR, -IR x 2 MOhm (R144 + R145) goes below -0.3 V until U15's IN diode conducts the uA (about -0.4 V): rating violated at uA level")
# ---------------- (6) root short with F1
k, rho_c = 0.20, 1.8e6; alpha = k / rho_c; r = 1.0e-3; dT = 43.0 - 34.0
cases = []
for rcell in (0.3, 1.0):
    for rf1 in (0.1, 0.5):
        rt = rcell + 0.054 + rf1 + 1.0
        for v in (4.2, 3.7):
            i = v / rt; p = i * i * 1.0
            x = brentq(lambda x: p / (4 * math.pi * k * r) * erfc(x) - dT, 1e-3, 10)
            t = r * r / (4 * alpha * x * x)
            cases.append(dict(r_cell=rcell, r_f1=rf1, v_cell=v, i_A=i, p_bridge_W=p, pcm_trips=bool(i >= 2.5), t_skin43_s=t))
OUT["root_short"] = dict(model="point source in moulding (k 0.20 W/m K, rho c 1.8 MJ/m3K) 1.0 mm from the skin face, skin 34 -> 43 C; heat spreading in the copper ignored (conservative)",
                         cases=cases, i_min_A=min(c["i_A"] for c in cases), t_min_s=min(c["t_skin43_s"] for c in cases),
                         requirement=f"F1 must clear {min(c['i_A'] for c in cases):.2f}-{max(c['i_A'] for c in cases):.2f} A within {min(c['t_skin43_s'] for c in cases):.2f} s; PCM IOV1 2.5 A min trips only in part of the cases")
(HERE / "results" / "g6_calc.json").write_text(json.dumps(OUT, indent=1))
print(json.dumps(OUT, indent=1)[:4000])
