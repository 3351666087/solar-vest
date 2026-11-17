"""SIM-07 for V2-B, coupling paths that v1 did not have (REDESIGN 5.7, G-11; review R-15):
  H1  PV lid -> finger on E3 / on the lid, and PV conductor -> E3 strip: Voc sampling (256 ms every 16 s), PV_INH edges,
      light changes (shadow of the hand), with the PV-node steps from the lid diode model and R_LIM
  H2  cell pouch -> plates (plates extend under the cell ends): cell terminal steps at Voc samples, LED pulses, BLE bursts
  H3  floating TMP117 island under plate E1 (I2C activity)
  H4  switching ripple of the boost charger on the PV node: alias bound at k x 128 kHz
  H5  motion band: what electrode-impedance and capacitance changes turn into (estimates; not a substitute for the bench)
All transfers are AC runs of the SIM-07 ngspice network (lib/frontend.py, FINAL network) with the V2-B structure capacitances;
steps and pulses are evaluated through the 0.5-40 Hz filter of ARCH 7.2 (sim07_v2_common.step_response).
Writes results/sim07_v2_coupling.json.  Run time about 6 min."""
import json, math, time, itertools
import numpy as np
from sim07_v2_common import (S, ENVS, V, HERE, FINAL, STRUCT, base, mm, add_caps, transfer, step_response, netlist, F_T, bp, Q, key)

t0 = time.time()
P = Q.P; VV = lambda k: P[k]["value"]
CAPS = STRUCT["V2-B rule: B.Cu + L5 void"]
LID = json.loads((HERE / "results" / "lid_caps.json").read_text())
R = {"caps_pF": [c * 1e12 for c in CAPS], "criterion": "ARCH M2: input-referred <= 10 uVpp over 0.5-40 Hz with the harvester running; "
     "REDESIGN 5.7 uses the same 10 uVpp for one PV-step artefact. 'clean' level used here: <= 3 uVpp (below the 4.0 uVpp of the shorted input)"}

# ------------------------------------------------------------------ electrodes
def cfg_el(name):
    b = lambda: base(FINAL, None, Rin=V("ads_rin_loff"), **ENVS["typical"])
    if name.startswith("in-vivo"):
        k, ph, a3 = EL[name]
        c = add_caps(b(), CAPS); c["Re"] = Q.invivo_electrodes(k, ph, a3)
        return c
    Rr, C, s = EL[name]
    return mm(Rr, C, s, 0, b(), CAPS)

EL = {"in-vivo nominal (2.06 MOhm cm2, -60 deg, E3 0.75 cm2)": ((1, 1, 1), -60.0, 0.75),
      "in-vivo dry x2, E3 0.5 cm2": ((2, 2, 2), -60.0, 0.5),
      "in-vivo dry x2, resistive (-30 deg), E3 0.5 cm2": ((2, 2, 2), -30.0, 0.5),
      "in-vivo moist x0.5, E3 1.0 cm2": ((0.5, 0.5, 0.5), -60.0, 1.0),
      "in-vivo, E3 dry x2 on 0.5 cm2, plates x0.5": ((0.5, 0.5, 2), -60.0, 0.5),
      "ARCH 0.1M|100n (+50/-50 %)": (0.1e6, 100e-9, 1), "ARCH 1M|10n (+50/-50 %)": (1e6, 10e-9, 1), "ARCH 1M|10n (-50/+50 %)": (1e6, 10e-9, -1),
      "ARCH 1M|1n (-50/+50 %)": (1e6, 1e-9, -1), "ARCH 10M|1n (-50/+50 %)": (10e6, 1e-9, -1)}
R["electrodes"] = {n: [(round(r / 1e6, 3), round(c * 1e9, 3)) for r, c in cfg_el(n)["Re"]] for n in EL}

# ------------------------------------------------------------------ lid diode model: PV-node voltage and its steps
pm = VV("pv_model"); VT = pm["vt"]
def string_prm(dvoc=0.0):
    a = pm["a_strip_cm2"]; n = pm["n"]; ns = pm["ns"]
    return dict(ISC=pm["jsc"] * a * pm["k_opt"], NS=ns, n=n, RS=ns * pm["rs_a"] / a + pm["r_ic"], RSH=ns * pm["rsh_a"] / a,
                I0=pm["i0_per_cm2"] * a * math.exp(-dvoc / (ns * n * VT)))
def string_I(Vv, G, prm):
    a = prm["NS"] * prm["n"] * VT; Iph = prm["ISC"] * (1 + prm["RS"] / prm["RSH"]) * G
    lo, hi = -10.0, Iph + 1e-12
    for _ in range(200):
        mid = 0.5 * (lo + hi); x = (Vv + mid * prm["RS"]) / a
        f = Iph - prm["I0"] * (math.exp(min(x, 700)) - 1) - (Vv + mid * prm["RS"]) / prm["RSH"] - mid
        if f > 0: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi)
def voc(G, prm):
    lo, hi = 0.0, 6.0
    for _ in range(60):
        m = 0.5 * (lo + hi)
        if string_I(m, G, prm) > 0: lo = m
        else: hi = m
    return 0.5 * (lo + hi)
def pv_point(G, rlim, ratio=0.80, dvoc=0.0):
    prm = string_prm(dvoc); vo = voc(G, prm); vin = ratio * vo; rs = rlim + VV("rsh1")
    lo, hi = 0.0, max(string_I(vin, G, prm), 0.0)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if string_I(vin + mid * rs, G, prm) > mid: lo = mid
        else: hi = mid
    i = 0.5 * (lo + hi); vnode = vin + i * rs; isc = string_I(0.0, G, prm)
    return dict(G=G, voc=vo, vin=vin, i_mA=i * 1e3, v_pv_node=vnode, step_voc_sample=vo - vnode, isc_mA=isc * 1e3,
                step_pv_inh=vnode - isc * (VV("rsh1") + 0.4), v_inh=isc * (VV("rsh1") + 0.4))
LIGHT = {"200 lx (LED light)": 200 * pm["lux_to_sun"], "1000 lx (LED light)": 1000 * pm["lux_to_sun"], "0.1 sun (10 klx overcast)": 0.1,
         "0.45 sun (50 klx at the wrist)": 0.45, "1 sun, hot lid": 1.0}
PV = {}
print("PV node (lid model of REDESIGN 5.6, estimate): Voc, node voltage while harvesting, steps")
for rl in VV("r_lim") + (0.0,):
    for ln, G in LIGHT.items():
        for ratio in (0.80, 0.72, 0.88):
            o = pv_point(G, rl, ratio); PV[f"R_LIM {rl:g}|{ln}|k {ratio:.2f}"] = o
            if ratio == 0.80:
                print(f"  R_LIM {rl:4.0f} Ohm {ln:32s} Voc {o['voc']:.3f} V node {o['v_pv_node']:.3f} V I {o['i_mA']:7.3f} mA | Voc-sample step {o['step_voc_sample']*1e3:6.1f} mV"
                      f" | PV_INH step {o['step_pv_inh']:.3f} V (node {o['v_inh']*1e3:.1f} mV while inhibited)")
# light change: the hand that touches E3 shades the lid: node follows the new operating point
o1 = pv_point(0.45, 22.0); o2 = pv_point(0.045, 22.0); o3 = pv_point(1.0, 22.0); o4 = pv_point(0.5, 22.0)
PV["shade 0.45 -> 0.045 sun (W-S, harvesting)"] = dict(step=o1["v_pv_node"] - o2["v_pv_node"])
PV["shade 1 -> 0.5 sun (W-S, harvesting)"] = dict(step=o3["v_pv_node"] - o4["v_pv_node"])
PV["shade 1 -> 0.5 sun (W-C, PV_INH on)"] = dict(step=o3["v_inh"] - o4["v_inh"])
print("  light change x0.1 at 0.45 sun: node step %.0f mV (W-S); 1 -> 0.5 sun: %.0f mV (W-S), %.1f mV (W-C, inhibited)" %
      (PV["shade 0.45 -> 0.045 sun (W-S, harvesting)"]["step"] * 1e3, PV["shade 1 -> 0.5 sun (W-S, harvesting)"]["step"] * 1e3, PV["shade 1 -> 0.5 sun (W-C, PV_INH on)"]["step"] * 1e3))
R["pv_node"] = PV

# ------------------------------------------------------------------ H1 PV -> finger / E3
K_PV = 0.625          # fraction of the PV-node step on the silicon under the finger (four strips at 1/4 ... 4/4 of the node: mean 0.625; n-type bulk 0.375)
D = LID["design"]
GEOM = {   # name: (C_fin to the finger [F], C_pe3 to the E3 net [F])
    "fingertip on the strip only (8 mm tip radius)": (LID["finger_rows"][0]["finger_pF_15mm"] * 1e-12, 0.0, 0.0),
    "finger pad on the rest, 2 mm from the silicon": (D["finger_on_rest_only_pF"] * 1e-12, 0.0, 0.0),
    "finger pad to the silicon edge": (D["finger_at_silicon_edge_pF"] * 1e-12, 0.0, 0.0),
    "finger 5 mm over the silicon": (D["finger_5mm_over_silicon_pF"] * 1e-12, 0.0, 0.0),
    "finger 10 mm over the silicon": (D["finger_10mm_over_silicon_pF"] * 1e-12, 0.0, 0.0),
    "finger lying on the lid (15 x 27.7 mm on glass)": (LID["plate_pF_per_cm2_finger_over_silicon"] * 1.5 * 2.77 * 1e-12, 0.0, 0.0),
    "E3 strip with the finger on it (shielded, lid_caps: 0.0001 pF)": (0.0, LID["finger_rows"][0]["strip_pF"] * 1e-12, 0.0),
    "E3 strip, no finger (lid rev 1: 0.05 pF; not a recording state)": (0.0, D["strip_pF"] * 1e-12, 0.0),
    "E3 net 0.01 pF from PV+ copper (lid backsheet / PV_NODE on the board)": (0.0, 0.01e-12, 0.0),
    "E3 net 0.05 pF from PV+ copper": (0.0, 0.05e-12, 0.0),
    "E3 net 0.2 pF from PV+ copper": (0.0, 0.2e-12, 0.0),
    "E1 net 0.01 pF from PV+ copper": (0.0, 0.0, 0.01e-12),
    "E1 net 0.05 pF from PV+ copper (10 mm2 of E1 copper 1.85 mm under an unshielded backsheet)": (0.0, 0.0, 0.05e-12),
    "E1 net 0.2 pF from PV+ copper": (0.0, 0.0, 0.2e-12),
}
def h_pv(cfg, cfin, cpe3, cpe1=0.0):
    lines = "Vpv pvn dg DC 0 AC 1"
    if cfin > 0: lines += "\nCpf pvn rf %g" % cfin
    if cpe3 > 0: lines += "\nCpe3 pvn e3 %g" % cpe3
    if cpe1 > 0: lines += "\nCpe1 pvn e1 %g" % cpe1
    return transfer(cfg, lines)
T_SET = VV("bq_focv")["t_settle"]
H1 = {}
print("\nH1 PV node -> ECG differential input, in-band peak-to-peak per volt of PV-node change (uVpp/V): step | 256 ms pulse")
for gname, (cfin, cpe3, cpe1) in GEOM.items():
    H1[gname] = dict(C_fin_pF=cfin * 1e12, C_pe3_pF=cpe3 * 1e12, C_pe1_pF=cpe1 * 1e12, k_pv=K_PV if cfin else 1.0, per_electrode={})
    for en in EL:
        H = h_pv(cfg_el(en), cfin * K_PV, cpe3, cpe1)
        pk, pp, _ = step_response(H); pk2, pp2, _ = step_response(H, pulse=T_SET)
        H1[gname]["per_electrode"][en] = dict(step_pp_uV_per_V=pp * 1e6, pulse_pp_uV_per_V=pp2 * 1e6, h_10Hz=float(abs(H[np.argmin(abs(F_T - 10))])),
                                              h_128k=None)
    w = max(H1[gname]["per_electrode"].items(), key=lambda kv: kv[1]["pulse_pp_uV_per_V"])
    wi = max(((k, v) for k, v in H1[gname]["per_electrode"].items() if k.startswith("in-vivo")), key=lambda kv: kv[1]["pulse_pp_uV_per_V"])
    H1[gname]["worst"] = dict(electrode=w[0], **w[1]); H1[gname]["worst_invivo"] = dict(electrode=wi[0], **wi[1])
    nom = H1[gname]["per_electrode"]["in-vivo nominal (2.06 MOhm cm2, -60 deg, E3 0.75 cm2)"]
    print(f"  {gname[:66]:66s} C_fin {cfin*1e12:5.2f} C_pe3 {cpe3*1e12:6.4f} C_pe1 {cpe1*1e12:5.2f} pF | nominal {nom['step_pp_uV_per_V']:7.2f} | {nom['pulse_pp_uV_per_V']:7.2f}"
          f" | worst in-vivo {wi[1]['pulse_pp_uV_per_V']:7.2f} | worst ARCH {w[1]['pulse_pp_uV_per_V']:7.2f} ({w[0]})", flush=True)
R["H1_transfer"] = H1
# artefact table: events x geometry (nominal and worst in-vivo electrode, worst ARCH corner)
EVENTS = {}
for rl in (22.0, 18.0):
    for ln in LIGHT:
        o = PV[f"R_LIM {rl:g}|{ln}|k 0.80"]; ow = max((PV[f"R_LIM {rl:g}|{ln}|k {r:.2f}"] for r in (0.72, 0.80, 0.88)), key=lambda x: x["step_voc_sample"])
        EVENTS[f"Voc sample, R_LIM {rl:g}, {ln}"] = ("pulse", o["step_voc_sample"], ow["step_voc_sample"])
        EVENTS[f"PV_INH edge, R_LIM {rl:g}, {ln}"] = ("step", o["step_pv_inh"], max(o["step_pv_inh"], o["voc"] - o["v_inh"]))
EVENTS["hand shadow 0.45 -> 0.045 sun, W-S"] = ("step", PV["shade 0.45 -> 0.045 sun (W-S, harvesting)"]["step"],) * 1 + (PV["shade 0.45 -> 0.045 sun (W-S, harvesting)"]["step"],)
EVENTS["light 1 -> 0.5 sun, W-S"] = ("step", PV["shade 1 -> 0.5 sun (W-S, harvesting)"]["step"], PV["shade 1 -> 0.5 sun (W-S, harvesting)"]["step"])
EVENTS["light 1 -> 0.5 sun, W-C (PV_INH static)"] = ("step", PV["shade 1 -> 0.5 sun (W-C, PV_INH on)"]["step"], PV["shade 1 -> 0.5 sun (W-C, PV_INH on)"]["step"])
ART = {}
print("\nH1 artefacts (uVpp in 0.5-40 Hz): nominal in-vivo electrode / worst in-vivo / worst ARCH corner; nominal regulation (worst regulation tolerance)")
for ev, (kind, dv, dvw) in EVENTS.items():
    ART[ev] = dict(kind=kind, dV=dv, dV_worst=dvw, by_geometry={})
    for gname in GEOM:
        f = "pulse_pp_uV_per_V" if kind == "pulse" else "step_pp_uV_per_V"
        nom = H1[gname]["per_electrode"]["in-vivo nominal (2.06 MOhm cm2, -60 deg, E3 0.75 cm2)"][f]
        wi = max(v[f] for k, v in H1[gname]["per_electrode"].items() if k.startswith("in-vivo")); wa = max(v[f] for v in H1[gname]["per_electrode"].values())
        ART[ev]["by_geometry"][gname] = dict(nominal=nom * dv, worst_invivo=wi * dvw, worst_arch=wa * dvw)
for ev in ("Voc sample, R_LIM 22, 1000 lx (LED light)", "Voc sample, R_LIM 22, 0.45 sun (50 klx at the wrist)", "Voc sample, R_LIM 22, 1 sun, hot lid",
           "PV_INH edge, R_LIM 22, 1000 lx (LED light)", "PV_INH edge, R_LIM 22, 1 sun, hot lid", "hand shadow 0.45 -> 0.045 sun, W-S", "light 1 -> 0.5 sun, W-C (PV_INH static)"):
    print(f"  {ev}  (dV {ART[ev]['dV']*1e3:.0f} mV, worst {ART[ev]['dV_worst']*1e3:.0f} mV)")
    for gname, a in ART[ev]["by_geometry"].items():
        print(f"      {gname[:70]:70s} {a['nominal']:8.2f} / {a['worst_invivo']:8.2f} / {a['worst_arch']:8.2f}")
R["H1_artefacts"] = ART
# budgets: capacitance that keeps one Voc-sample artefact at 3 and 10 uVpp (worst in-vivo electrode, indoor 0.2 Voc step = worst Voc-sample case)
dv_ref = max(v[2] for k, v in EVENTS.items() if k.startswith("Voc sample, R_LIM 22"))
NOMK = "in-vivo nominal (2.06 MOhm cm2, -60 deg, E3 0.75 cm2)"
def sens(gname, cap_key):
    g = H1[gname]; c = g[cap_key]
    return dict(nominal=g["per_electrode"][NOMK]["pulse_pp_uV_per_V"] / c, worst_invivo=g["worst_invivo"]["pulse_pp_uV_per_V"] / c, worst_arch=g["worst"]["pulse_pp_uV_per_V"] / c,
                nominal_step=g["per_electrode"][NOMK]["step_pp_uV_per_V"] / c, worst_invivo_step=max(v["step_pp_uV_per_V"] for k, v in g["per_electrode"].items() if k.startswith("in-vivo")) / c)
SF = sens("finger lying on the lid (15 x 27.7 mm on glass)", "C_fin_pF"); SE3 = sens("E3 net 0.05 pF from PV+ copper", "C_pe3_pF"); SE1 = sens("E1 net 0.05 pF from PV+ copper (10 mm2 of E1 copper 1.85 mm under an unshielded backsheet)", "C_pe1_pF")
dv_nom = PV["R_LIM 22|1000 lx (LED light)|k 0.80"]["step_voc_sample"]
bud = lambda sv, dv, lim: lim / (sv * dv)
R["H1_budget"] = dict(dV_voc_sample_worst=dv_ref, dV_voc_sample_indoor_nominal=dv_nom, sens_uVpp_per_V_per_pF=dict(finger=SF, e3_net=SE3, e1_net=SE1),
                      c_max_pF={n: {"3uVpp_nominal": bud(sv["nominal"], dv_nom, 3), "10uVpp_nominal": bud(sv["nominal"], dv_nom, 10),
                                    "3uVpp_worst_invivo": bud(sv["worst_invivo"], dv_ref, 3), "10uVpp_worst_invivo": bud(sv["worst_invivo"], dv_ref, 10)}
                                for n, sv in (("finger", SF), ("e3_net", SE3), ("e1_net", SE1))})
print("\nH1 budgets for ONE Voc-sample artefact (256 ms pulse; indoor step %.0f mV nominal, %.0f mV at the regulation tolerance):" % (dv_nom * 1e3, dv_ref * 1e3))
for n, sv in (("finger -> silicon (x K_PV)", SF), ("E3 net <- PV+ copper", SE3), ("E1 net <- PV+ copper", SE1)):
    k = {"finger -> silicon (x K_PV)": "finger", "E3 net <- PV+ copper": "e3_net", "E1 net <- PV+ copper": "e1_net"}[n]; b = R["H1_budget"]["c_max_pF"][k]
    print("  %-28s %8.2f uVpp/V/pF nominal, %8.2f worst in-vivo, %8.2f worst ARCH | C <= %.4f pF (3 uVpp) / %.4f pF (10 uVpp) nominal; %.4f / %.4f pF worst in-vivo" %
          (n, sv["nominal"], sv["worst_invivo"], sv["worst_arch"], b["3uVpp_nominal"], b["10uVpp_nominal"], b["3uVpp_worst_invivo"], b["10uVpp_worst_invivo"]), flush=True)

# ------------------------------------------------------------------ H2 cell pouch -> plates
b1, b2 = VV("plate_under_cell_cm2"); cc = Q.C_CELL_PER_CM2
def h_cell(cfg, k1=1.0, k2=1.0):
    # the plate-to-cell capacitance is already in the structure capacitance to ground; here it is re-connected to the source
    c = dict(cfg); ct = list(c["Ctvs"]); ct[0] -= cc * b1 * 1e-12 * k1; ct[1] -= cc * b2 * 1e-12 * k2; c["Ctvs"] = ct
    return transfer(c, "Vcell cel dg DC 0 AC 1\nCc1 cel e1 %g\nCc2 cel e2 %g" % (cc * b1 * 1e-12 * k1, cc * b2 * 1e-12 * k2))
H2 = {"C_cell_plate_pF": [cc * b1, cc * b2], "per_electrode": {}}
i_led, t_led, f_led = 20e-3, 117.3e-6, 25.0
r_cell = VV("cell_v2")["r_dc"][1] + VV("r_prot_fet")[2]
CELL_EV = {"Voc sample, 4 mV (R-15 low)": ("pulse", 4e-3), "Voc sample, 12 mV (R-15 high)": ("pulse", 12e-3),
           "Voc sample, full sun 20 mA x 1.05 Ohm": ("pulse", 20e-3 * r_cell), "PV_INH edge in sun (charge current 20 mA off)": ("step", 20e-3 * r_cell)}
print("\nH2 cell pouch -> plates (E1 %.1f pF, E2 %.1f pF); pouch assumed to follow the cell + terminal (worst case)" % (cc * b1, cc * b2))
for en in EL:
    H = h_cell(cfg_el(en))
    pk, pp, _ = step_response(H); pk2, pp2, _ = step_response(H, pulse=T_SET)
    # periodic narrow pulses: fundamental and harmonics inside 0.5-40 Hz
    def periodic(amp, width, f0):
        tot = 0.0
        for kh in range(1, int(40 // f0) + 1):
            fk = kh * f0; a = 2 * amp * width * f0 * abs(np.interp(fk, F_T, abs(H))) * abs(bp(np.array([fk]))[0]); tot += a * a / 2
        return math.sqrt(tot)
    led = periodic(i_led * r_cell, t_led, f_led); ble = periodic(4.1e-3 * r_cell, 1.5e-3, 1 / 30e-3)
    H2["per_electrode"][en] = dict(step_pp_uV_per_V=pp * 1e6, pulse_pp_uV_per_V=pp2 * 1e6, led_25Hz_uVrms=led * 1e6, ble_33Hz_uVrms=ble * 1e6,
                                   events={k: (pp2 if kind == "pulse" else pp) * 1e6 * dv for k, (kind, dv) in CELL_EV.items()})
    e = H2["per_electrode"][en]["events"]
    print(f"  {en:52s} step {pp*1e6:8.1f} uVpp/V | Voc sample 4 / 12 / 21 mV: {e['Voc sample, 4 mV (R-15 low)']:.3f} / {e['Voc sample, 12 mV (R-15 high)']:.3f} / "
          f"{e['Voc sample, full sun 20 mA x 1.05 Ohm']:.3f} uVpp | LED 20 mA 25 sps {led*1e6:.4f} uVrms | BLE 33 Hz {ble*1e6:.4f} uVrms", flush=True)
R["H2_cell"] = H2

# ------------------------------------------------------------------ H3 floating TMP117 island
isl = {}
print("\nH3 floating TMP117 island under plate E1 (I2C read at 1 Hz: SCL / SDA mean level -0.9 V for about 100 us x 4 bytes)")
for a_mm2 in VV("tmp117_island_mm2"):
    c_pi = Q.CAP_PER_CM2["B.Cu copper (ground or pour) under the plate"] * a_mm2 / 100 * 1e-12
    cg = VV("c_island_to_gnd"); c_agg = 0.3e-12                      # SCL + SDA pins and tracks to the paddle / island: 0.2-0.4 pF (estimate)
    row = {}
    for en in ("in-vivo nominal (2.06 MOhm cm2, -60 deg, E3 0.75 cm2)", "in-vivo dry x2, E3 0.5 cm2", "ARCH 1M|1n (-50/+50 %)"):
        H = transfer(cfg_el(en), "Vi2c agg dg DC 0 AC 1\nCagg agg isl %g\nCig isl dg %g\nCpi isl e1 %g" % (c_agg, cg, c_pi))
        w = 2j * np.pi * F_T; width = 0.4e-3
        pk, pp, _ = step_response(H, pulse=width)
        row[en] = pp * 1e6 * 0.9
    isl[f"{a_mm2:g} mm2"] = dict(c_plate_island_pF=c_pi * 1e12, artefact_uVpp=row)
    print(f"  island {a_mm2:4.0f} mm2 (plate-island {c_pi*1e12:.1f} pF): " + ", ".join(f"{k.split(' (')[0]} {v:.3f} uVpp" for k, v in row.items()))
R["H3_island"] = isl

# ------------------------------------------------------------------ H4 switching ripple alias bound
print("\nH4 charger ripple on the PV node (estimate %g mVpp at 1-100 kHz): input-referred at k x 128 kHz (unattenuated alias if a harmonic lands within +-40 Hz)" % (VV("bq_ripple_vin")["v_pp"] * 1e3))
H4 = {}
for gname in ("finger pad to the silicon edge", "finger 10 mm over the silicon", "finger lying on the lid (15 x 27.7 mm on glass)", "E3 net 0.05 pF from PV+ copper"):
    cfin, cpe3, cpe1 = GEOM[gname]; row = {}
    for en in ("in-vivo nominal (2.06 MOhm cm2, -60 deg, E3 0.75 cm2)", "in-vivo dry x2, E3 0.5 cm2", "ARCH 10M|1n (-50/+50 %)"):
        c = dict(cfg_el(en), vmains_ac=0.0, vecg_ac=0.0, extra="Vpv pvn dg DC 0 AC 1" + ("\nCpf pvn rf %g" % (cfin * K_PV) if cfin else "") + ("\nCpe3 pvn e3 %g" % cpe3 if cpe3 else ""))
        S.run(netlist(c, ".ac dec 40 100 1e6")); f = S.vec("frequency").real; Hh = abs(S.vec("inp") - S.vec("inn"))
        vpp = VV("bq_ripple_vin")["v_pp"]
        # sawtooth-like ripple: harmonic m has amplitude vpp/(pi m); the worst alias is a harmonic at 128 kHz: m = 128k/f_sw
        out = {}
        for fsw in (4e3, 16e3, 40e3, 128e3):
            mh = round(128e3 / fsw); a = vpp / (math.pi * mh) * float(np.interp(128e3, f, Hh)); out[f"{fsw/1e3:g}k"] = a * 1e6 / math.sqrt(2)
        row[en] = dict(h_128k=float(np.interp(128e3, f, Hh)), h_10k=float(np.interp(1e4, f, Hh)), alias_uVrms=out)
    H4[gname] = row
    n = row["in-vivo nominal (2.06 MOhm cm2, -60 deg, E3 0.75 cm2)"]; w = row["in-vivo dry x2, E3 0.5 cm2"]
    print(f"  {gname:52s} |H(128 kHz)| {n['h_128k']:.2e} (dry x2: {w['h_128k']:.2e}) | alias uVrms for f_sw 4k/16k/40k/128k: " +
          " ".join(f"{v:.3f}" for v in n["alias_uVrms"].values()) + " (dry x2: " + " ".join(f"{v:.3f}" for v in w["alias_uVrms"].values()) + ")")
R["H4_ripple_alias"] = H4

# ------------------------------------------------------------------ H5 motion band (estimates)
print("\nH5 motion band (estimates)")
H5 = {}
el = Q.invivo_electrodes()
for lname, idc in (("lead-off off (bias 0.2 nA + TVS 1 nA typ)", 1.2e-9), ("lead-off 6 nA", 6e-9 + 1.2e-9), ("lead-off 22 nA", 22e-9 + 1.2e-9), ("lead-off 6 nA + TVS worst 30 nA", 36e-9)):
    row = {}
    for nm, (Rr, C) in zip(("E1", "E3"), (el[0], el[2])):
        row[nm] = dict(R_MOhm=Rr / 1e6, v_drop_mV=idc * Rr * 1e3, uV_per_pct_dR=idc * Rr * 0.01 * 1e6)
    H5[lname] = row
    print(f"  {lname:40s} DC drop E1 {row['E1']['v_drop_mV']:.2f} mV, E3 {row['E3']['v_drop_mV']:.2f} mV -> {row['E1']['uV_per_pct_dR']:.1f} / {row['E3']['uV_per_pct_dR']:.1f} uV per 1 % change of the electrode resistance")
# finger pressure changes C_fin under the DC bias of the PV node: charge injected into the body
c = cfg_el("in-vivo nominal (2.06 MOhm cm2, -60 deg, E3 0.75 cm2)")
Hq = transfer(c, "Iq dg rf DC 0 AC 1")           # V(dm) per ampere injected into the finger
i10 = np.argmin(abs(F_T - 5)); zt = abs(Hq[i10])
for dC, vpv in ((0.2e-12, 2.5), (1.0e-12, 2.5)):
    q = dC * vpv; i_pk = q * 2 * math.pi * 5          # sinusoidal 5 Hz change
    H5[f"finger pressure: dC {dC*1e12:g} pF at {vpv} V, 5 Hz"] = dict(q_pC=q * 1e12, dm_uVpk=i_pk * zt * 1e6)
    print(f"  finger pressure changes C_fin by {dC*1e12:g} pF at {vpv} V DC, 5 Hz: {q*1e12:.2f} pC -> {i_pk*zt*1e6:.3f} uV peak differential (transimpedance {zt/1e3:.1f} kOhm at 5 Hz)")
# plate-to-board capacitance under strap pressure: film strain 0.1 % at 1.5 V + half-cell
dq = CAPS[0] * 1e-3 * 1.8; H5["plate capacitance change 0.1 % at 1.8 V"] = dict(q_fC=dq * 1e15, dv_uV_on_10nF=dq / 10e-9 * 1e6)
print(f"  plate-to-board capacitance change 0.1 % at 1.8 V: {dq*1e15:.2f} fC -> {dq/10e-9*1e6:.4f} uV on a 10 nF electrode")
H5["half_cell"] = "a change of the electrode half-cell potential reaches the input 1:1 above 0.5 Hz (attenuation < 1 %, section A): not simulable, bench"
R["H5_motion"] = H5
(HERE / "results" / "sim07_v2_coupling.json").write_text(json.dumps(R, indent=1, default=float))
print(f"done {time.time()-t0:.0f} s")
