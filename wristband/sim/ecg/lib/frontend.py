"""ngspice netlist of the SolarBand ECG front end: body, 3 dry electrodes, TVS, 2 × 330 kΩ chains, C_CM/C_DIFF,
ADS1291 input model, PGA common-mode sense, RLD amplifier with REXT‖CEXT, RLDREF (internal or external filtered),
and the floating device (device ground 'dg' coupled to earth '0' and to the body only by capacitance).

Node map
  0 earth | mn mains | bc body core | lw left wrist (E1, E2) | rf right finger (E3) | dg device ground (AVSS)
  e1/e2/e3 electrode landing pads (TVS here) | m1/m2/m3 between the two 330 kΩ | inp/inn ADS1291 IN1P/IN1N pins
  rldn = network side of RLDOUT, rldout = amplifier side (REXT/CEXT connect here); loop broken between them when asked
  avdd ADS1291 AVDD | vmid internal AVDD/2 | rldref RLD amp non-inverting input | rldinv summing node
"""
import math
from params import P

V = lambda k: P[k]["value"]


def default_cfg(**kw):
    cfg = dict(
        Re=[(1e6, 10e-9)] * 3, Vhc=[0.0, 0.0, 0.0],
        Rprot=[(V("r_prot"), V("r_prot"))] * 3, Ctvs=[V("c_tvs")] * 3, Itvs=[0.0] * 3,
        Ccm=[10e-12, 10e-12], Cdiff=47e-12, Croute=[V("c_route")] * 2,
        Rin=V("ads_rin"), Ib=[0.0, 0.0], Iloff=0.0, gain=4,
        rext=1e6, cext=1.5e-9, a0=V("rld_a0"), gbw=V("rld_gbw"), pga_bw=V("pga_cm_bw"), rout=V("rld_rout"),
        rldref="int",                      # or ("ext", R_top, R_bot, C)
        cpw=V("c_mains_body")[0], cb=V("c_body_earth"), csup=V("c_dev_earth")[0], cdb=V("c_dev_body")[0],
        vmains_ac=0.0, vecg_ac=0.0, avdd=V("avdd"), avdd_ac=0.0, avdd_src=None,
        loopbreak=False, faults={}, esd_diodes=True, extra="")
    cfg.update(kw)
    return cfg


def netlist(cfg, analysis):
    c = cfg
    L = ["* SolarBand ECG front end", ".options rshunt=1e15 gmin=1e-15 reltol=1e-5 abstol=1e-16 vntol=1e-9"]
    # ---------------------------------------------------------------- environment and body
    L += [f"Vmains mn 0 DC 0 AC {c['vmains_ac']}",
          f"Cpw mn bc {c['cpw']}", f"Cb bc 0 {c['cb']}",
          f"Rbd1 bc lw {V('r_body') / 2}", f"Rbd3 bc rfx {V('r_body') / 2}",
          f"Vecg rfx rf DC 0 AC {c['vecg_ac']}",       # V(lw) - V(rf) = +Vecg  (Lead I, left-wrist band)
          f"Csup dg 0 {c['csup']}", "Rdg dg 0 1e13"]
    if c["cdb"] > 0:
        L.append(f"Cdb dg bc {c['cdb']}")
    body = {1: "lw", 2: "lw", 3: "rf"}
    tail = {1: "inp", 2: "rldn", 3: "inn"}
    F = c["faults"]
    for i in (1, 2, 3):
        R, Cc = c["Re"][i - 1]
        L += [f"Vhc{i} h{i} {body[i]} DC {c['Vhc'][i - 1]}",
              f"Re{i} h{i} e{i} {R}", f"Ce{i} h{i} e{i} {Cc}"]
        if F.get(f"tvs_short{i}"):
            L.append(f"Rtvs{i} e{i} dg 1e-3")
        else:
            L += [f"Ctvs{i} e{i} dg {c['Ctvs'][i - 1]}", f"Itvs{i} e{i} dg DC {c['Itvs'][i - 1]}"]
        ra, rb = c["Rprot"][i - 1]
        if F.get(f"short_a{i}"): ra = 1e-3
        if F.get(f"short_b{i}"): rb = 1e-3
        L += [f"Rpa{i} e{i} m{i} {ra}", f"Rpb{i} m{i} {tail[i]} {rb}"]
    # ---------------------------------------------------------------- board network at the pins
    L += [f"Ccm1 inp dg {c['Ccm'][0]}" if c["Ccm"][0] > 0 else "",
          f"Ccm3 inn dg {c['Ccm'][1]}" if c["Ccm"][1] > 0 else "",
          f"Cdiff inp inn {c['Cdiff']}" if c["Cdiff"] > 0 else "",
          f"Crt1 inp dg {c['Croute'][0]}", f"Crt3 inn dg {c['Croute'][1]}"]
    # ---------------------------------------------------------------- ADS1291
    if c["avdd_src"]:
        L.append(c["avdd_src"])                      # caller supplies the AVDD source line(s)
    else:
        L.append(f"Vavdd avdd dg DC {c['avdd']} AC {c['avdd_ac']}")
    L += ["Bmid vmid dg V = (V(avdd)-V(dg))/2",
          f"Cin1 inp dg {V('ads_cin')}", f"Cin3 inn dg {V('ads_cin')}",
          f"Ib1 dg inp DC {c['Ib'][0]}", f"Ib3 dg inn DC {c['Ib'][1]}"]
    # input impedance model (the datasheet gives only magnitudes: 1000 MΩ, 500 MΩ with the nA lead-off source on):
    #  'sym'  : Rin per pin to the internal AVDD/2 node (default)
    #  'asym' : 1000 MΩ per pin to AVDD/2 plus the lead-off source/sink output impedance 1000 MΩ referenced to AVDD
    #           on IN1P (source) and to AVSS on IN1N (sink) -> 500 MΩ per pin, but AVDD now reaches IN1P only
    #  'avss' : Rin per pin to AVSS (bound in which AVDD noise has no path through the input impedance)
    if c.get("rin_mode", "sym") == "asym":
        L += [f"Rin1 inp vmid {V('ads_rin')}", f"Rin3 inn vmid {V('ads_rin')}",
              f"Rlo1 inp avdd {V('ads_rin')}", f"Rlo3 inn dg {V('ads_rin')}"]
    elif c.get("rin_mode") == "avss":
        L += [f"Rin1 inp dg {c['Rin']}", f"Rin3 inn dg {c['Rin']}"]
    else:
        L += [f"Rin1 inp vmid {c['Rin']}", f"Rin3 inn vmid {c['Rin']}"]
    if c["Iloff"] > 0:   # DC lead-off: source into IN1P, sink from IN1N (FLIP1 = 0), with supply compliance
        L += [f"Blo1 avdd inp I = {c['Iloff']}*max(1-exp(-(V(avdd)-V(inp))/0.05),0)",
              f"Blo3 inn dg I = {c['Iloff']}*max(1-exp(-(V(inn)-V(dg))/0.05),0)"]
    if c["esd_diodes"]:
        L += [".model DESD D(IS=1e-15 N=1 RS=5)"]
        for n in ("inp", "inn", "rldout"):
            L += [f"Du_{n} {n} avdd DESD", f"Dd_{n} dg {n} DESD"]
    for i, pin in ((1, "inp"), (3, "inn")):
        if F.get(f"pin_high{i}"): L.append(f"Rf{i} {pin} avdd 1e-3")
        if F.get(f"pin_low{i}"): L.append(f"Rf{i} {pin} dg 1e-3")
    # PGA common-mode outputs (followers for CM) -> 400 kΩ summing resistors -> RLDINV
    tau = 1 / (2 * math.pi * 1e3 * c["pga_bw"])
    L += [f"Epgp pgpx dg inp dg 1", f"Rpgp pgpx pgp 1k", f"Cpgp pgp dg {tau}",
          f"Epgn pgnx dg inn dg 1", f"Rpgn pgnx pgn 1k", f"Cpgn pgn dg {tau}",
          f"Rs1 pgp rldinv {V('rld_sum_r')}", f"Rs3 pgn rldinv {V('rld_sum_r')}"]
    # RLD amplifier: single-pole VCVS, rail-limited output, output resistance
    cp = c["a0"] / (2 * math.pi * 1e3 * c["gbw"])
    # gain stage clamped just outside the rails (no unphysical wind-up), then the dominant pole, then the output
    stuck = bool(F.get("rld_high") or F.get("rld_low"))
    # with the output stuck (fault model) the amplifier core is disconnected; its open integrator is frozen at 0 so the
    # DC solver does not chase a railed internal node (that made one fault case stall for > 30 min in .tran)
    L += [("Ba n1x dg V = 0" if stuck else
           f"Ba n1x dg V = max(min({c['a0']}*(V(rldref)-V(rldinv)), V(avdd)-V(dg)+0.5), -0.5)"),
          "Rp n1x n1 1k", f"Cp n1 dg {cp}",
          "Bo oi dg V = min(max(V(n1)-V(dg), 0.02), V(avdd)-V(dg)-0.02)",
          f"Ro oi rldout {1e12 if (F.get('rld_high') or F.get('rld_low')) else c['rout']}"]
    # stuck RLD output: the amplifier is disconnected and its pin is tied to the rail (fault model)
    if F.get("rld_high"): L.append("Rfr rldout avdd 1e-3")
    if F.get("rld_low"): L.append("Rfr rldout dg 1e-3")
    if c["rext"]: L.append(f"Rext rldout rldinv {c['rext']}")
    if c["cext"] and c.get("rz"):     # lead zero: Rz in series with CEXT
        L += [f"Cext rldout cz {c['cext']}", f"Rz cz rldinv {c['rz']}"]
    elif c["cext"]:
        L.append(f"Cext rldout rldinv {c['cext']}")
    L.append("Vinj rldn rldout DC 0 AC 1" if c["loopbreak"] else "Vinj rldn rldout DC 0")
    if c["rldref"] == "int":
        L.append("Bref rldref dg V = (V(avdd)-V(dg))/2")
    else:                              # ('ext', R_top, R_bot, C): divider from AVDD + C to AVSS on RLDIN/RLDREF
        _, rt, rbot, cr = c["rldref"]
        L += [f"Rr1 avdd rldref {rt}", f"Rr2 rldref dg {rbot}", f"Cr rldref dg {cr}"]
    L.append(c["extra"])
    L += analysis.strip().splitlines()
    L.append(".end")
    return "\n".join(l for l in L if l)
