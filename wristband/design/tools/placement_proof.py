"""Placement proof table (review R-07, R-19; ARCHITECTURE 10.3 classes; REDESIGN 5.8 'how placement stays provable').
For every JLC-placed part that is not a plain R / C / L: the rotational symmetry of its pad set, computed from the footprint the board
uses (lib/easyeda_rev.pretty), whether a turned part would still connect the same nets (computed from the netlist), the proof class,
the evidence that decides the orientation, and the G10 item that catches a turned part on the delivered board.
Classes: 1F = the pad set has no rotational symmetry: pad geometry decides (cplgate G4).  2F / 4F = the copper fits at 180 deg (and 90 deg):
identity evidence is mandatory (pin map per C-number + an electrical test).  P = polar two-terminal part.  N = electrically neutral under
the silent turn (same nets on the pads that swap).  M = mechanically polar, electrically neutral (spring finger).
usage: python placement_proof.py  ->  placement_proof.md, placement_proof.json
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); DESIGN = os.path.dirname(HERE); sys.path.insert(0, HERE)
from kisexp import footprint_pads
VARIANTS = ["v3f", "v3f_fldnp"]
P = {v: json.load(open(os.path.join(DESIGN, "out", v, "parts.json"))) for v in VARIANTS}

def pads_of(fp):
    lib, name = fp.split(":")
    return [p for p in footprint_pads(os.path.join(DESIGN, "lib", lib + ".pretty", name + ".kicad_mod")) if p["num"] and "F.Cu" in (p["layers"] or [])]
def eff(p):
    r = abs(p["rot"]) % 180
    return (p["h"], p["w"]) if abs(r - 90) < 1 else (p["w"], p["h"])
def turn_map(pads, deg, tol=0.03):
    """Pad-number map {n: n'} if the pad set fits onto itself when turned by deg about the centre of its bounding box (within tol mm), else None."""
    xs = [p["x"] for p in pads]; ys = [p["y"] for p in pads]
    x0 = min(a - eff(p)[0] / 2 for a, p in zip(xs, pads)); x1 = max(a + eff(p)[0] / 2 for a, p in zip(xs, pads))
    y0 = min(a - eff(p)[1] / 2 for a, p in zip(ys, pads)); y1 = max(a + eff(p)[1] / 2 for a, p in zip(ys, pads))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; a = math.radians(deg); m = {}
    for p in pads:
        dx, dy = p["x"] - cx, p["y"] - cy
        qx, qy = cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a)
        w, h = eff(p)
        if deg in (90, 270): w, h = h, w
        hit = [q for q in pads if abs(q["x"] - qx) < tol and abs(q["y"] - qy) < tol and abs(eff(q)[0] - w) < tol and abs(eff(q)[1] - h) < tol]
        if len(hit) != 1: return None
        m[p["num"]] = hit[0]["num"]
    return m
# hand table: reference -> (evidence that decides, G10 / EOL item that catches a turned or wrong part, what a silent turn would do)
EVID = {
 "U1":  ("pad numbering + pin map identity (C506250.yaml) + corner token + silk pin-1 dot", "VBAT_OV / VBAT_OK threshold ramp, VDD_1V8 level", "no harvester, no 1.8 V rail"),
 "U3":  ("pin map identity; near-symmetric X2SON: human check of pin 1 in the JLC preview", "AVDD_ECG = 3.0 V with ECG_PWR_EN high", "no AVDD"),
 "U4":  ("A1 corner + ball map identity (C4371025.yaml)", "INA236 ID at 0x40; known-load reading", "VS ball open: no I2C answer (every pin stays <= 6 V)"),
 "U5":  ("A1 corner + ball map identity (C4371025.yaml)", "INA236 ID at 0x41; cell-voltage reading", "no I2C answer"),
 "U6":  ("WLCSP: pad set not symmetric (six empty positions) -> geometry; QFN-48: numbering + identity + corner token", "SWD IDCODE, flash of the test image", "no MCU"),
 "U7":  ("pad numbering + pin map identity (C139059.yaml) + corner token", "ADS1291 ID register, internal test signal", "no ECG AFE"),
 "U8":  ("A1 corner + ball map identity (C5328762.yaml)", "MAX86141 part ID; LED / PD loop-back", "no SPI answer"),
 "U9":  ("pin map identity (C189624.yaml)", "LIS2DW12 WHO_AM_I", "no I2C answer"),
 "U10": ("pin map identity (C2803242.yaml)", "TMP117 device ID", "no I2C answer"),
 "U11": ("pin map identity (C5687033.yaml)", "MX25R JEDEC ID", "no SPI answer"),
 "U12": ("pin map identity (C727398.yaml): TDFN4 fits at 180 deg", "VSTOR_SW = VSTOR after VBAT_OK; VLED level", "IN / OUT and GND / ON swapped: VSTOR_SW dead"),
 "U13": ("pin map identity (C727398.yaml)", "INA236 IDs answer only with INA_EN high", "INA_VS dead: INA IDs fail"),
 "U14": ("SOT-23-5: geometry decides; identity confirms (C2760012.yaml)", "protector function test from the bench supply at J3 / J4 (REDESIGN 5.5 step 1)", "-"),
 "Q1":  ("DFN1006-3: three unequal lands, geometry decides", "PV_INH probe: PV current with Q1 on", "-"),
 "Q2":  ("pin map is its own 180 deg image (E1 B1 C2 / E2 B2 C1) and both transistors have the same circuit class", "cradle detect: VCHG_N low and AVDD_EN low with C+ at 3.3 V", "none: Tr1 and Tr2 swap roles, both have 1 k / 10 k and an emitter on GND"),
 "Q4":  ("DFN1006-3: geometry decides", "G10 (a) hold test", "-"), "Q5": ("DFN1006-3: geometry decides", "G10 (c) power-cycle test", "-"),
 "Q6":  ("DFN1006-3: geometry decides", "G10 (b) warning LED test", "-"), "Q7": ("DFN1006-3: geometry decides", "G10 (c): VDD_1V8 below 0.3 V during the cycle", "-"),
 "D1":  ("polar: human-reviewed pin map (C130414.yaml, pin 1 = cathode)", "cradle test: PV-node rises with C+ powered; no current from the PV node back into C+", "cradle cannot charge; PV back-feeds the contact"),
 "D2":  ("bidirectional TVS (TPD1E10B06): electrically symmetric", "-", "none"), "D5": ("bidirectional TVS", "-", "none"), "D6": ("bidirectional TVS", "-", "none"),
 "D7":  ("bidirectional TVS", "-", "none"), "D8": ("bidirectional TVS", "-", "none"),
 "D3":  ("pad set is not its own 180 deg image (one large + two small lands): geometry decides the turn; anode = pad 1 rests on the pin map (human review)", "LED / PD loop-back: LED1 on -> photocurrent", "-"),
 "D4":  ("as D3", "LED / PD loop-back: LED2 on -> photocurrent", "-"),
 "PD1": ("polar, 4 x 2 lands fit at 180 deg: human-reviewed pin map (C511402.yaml) + electrical proof on every board", "LED / PD loop-back: each LED on -> photocurrent; both off -> dark", "anode on PD1_IN: no signal"),
 "D9":  ("polar: human-reviewed pin map (pin 1 = cathode)", "G10 (a): VIN_DC = 0 V, P0.27 high -> VDD_1V8 alive for >= 30 s; P0.27 low -> off within 60 s", "works whenever light or the jig feeds the PV node, switches off in the dark although the MCU holds P0.27: NOT caught without item (a)"),
 "D10": ("polar and right-angle: human-reviewed pin map + lens side checked in the JLC preview", "G10 (b): ALERT_LED on -> supply current rises by 6-26 mA and red light leaves the board edge", "no warning light: NOT caught without item (b)"),
 "D11": ("polar: human-reviewed pin map (pin 1 = cathode)", "G10 (c): PWR_CYC high -> VDD_1V8 below 0.3 V within 0.5 s and back above 1.7 V within 3 s", "the one-shot never triggers: NOT caught without item (c)"),
 "X1":  ("2016 4-pad crystal: numbers pair (1 / 3 crystal, 2 / 4 GND), any 180 deg turn is electrically the same", "HFXO start (radio test)", "none"),
 "X2":  ("non-polar 2-terminal crystal", "LFXO start", "none"),
 "J11": ("one land: the mating tab (>= 3.4 x 2.2 mm centred on the land centre) makes the turn irrelevant; 90 deg is caught by the land shape", "EOL-1: E3 contact resistance TP5 to the strip", "none by design of the tab"),
 "J1":  ("as J11", "EOL-1: C+ contact", "none by design of the pin's inner face"), "J2": ("as J11", "EOL-1: C- contact", "none"),
 # ---------------- V3-F (BASELINE 16 + this lane); G10 items (e)-(k) of BASELINE 16, jig feeds the root-A pads J3 / J4 from a bench supply ----------------
 "U15": ("WSON-8 + EP fits turned 180 deg: pin map identity (C5208201.yaml) + JLC preview of the pin-1 index before payment", "G10 (e): 5.0 V on the contacts (J15 / J18, through D14) -> /PG low < 1 s, 27-33 mA into a 3.8 V load on J3 / J4, AVDD_EN low with ECG_PWR_EN high, PV shorted (INA_PV = Isc under the jig lamp)", "IN on ISET / OUT on VSET etc.: no charge, /PG high: caught by (e)"),
 "U16": ("X2SON-4 fits turned 180 deg (as U3): pin map identity (C2867950.yaml) + preview of the pin-1 index", "G10 (g): VDD_DISP = 3.0 V +-1.5 % with DISP_EN high, < 0.1 V with DISP_EN low", "OUT and EN swapped with IN and GND: no display rail"),
 "U17": ("UQFN-12 land symmetric on both axes: pin map identity (C5187176.yaml) + preview of pin 1 against our CPL rotation (the body may carry no pin-1 mark)", "G10 (g): test pattern on the panel at a 20 mA supply limit; VDD_DISP current <= 1 mA", "turned 180 deg VCCB (3 V) would sit on the A4 pad (EXTCOMIN GPIO) and GND on OE: caught by (g) and the current limit"),
 "U21": ("USON-6 fits turned 180 deg: pin map identity (C5217869.yaml) + preview of pin 1", "G10 (g): DISP_CTRL high -> panel shows the pattern; DISP_CTRL low -> white screen", "VCCA on BY, VCCB on A: DISP never high (blank panel): caught by (g)"),
 "U19": ("[ECO3] SC70-5 C2863637, 3 + 2 leads: a 180 deg turn puts pins 1-3 on the 2-lead side (one lead on no land): geometry proves rotation; pin map identity (C2863637.yaml, numbering = TI); preview of the pin-1 mark for the mirror case", "G10 (k1)-(k2): MCU held in reset, PV lamp on. (k1) pack pads 3.70 V (VBAT_OK high): NTC pad J5 with 47 k / 10 k / 3.6 k -> VIN_DC stays 0 V in all three (no heartbeat). (k2) pads 3.0 V (VBAT_OK low): 47 k (about -1 C) -> 0 V; 10 k (25 C) -> VIN_DC rises; 3.6 k (about 51 C) -> 0 V; again with J3 at 0 V [S1 D-1: BASELINE 16 (k) restored]", "comparator turned: no approval -> no PV charging with the MCU off (fail-safe), caught by the 10 k step of (k)"),
 "U20": ("as U19", "G10 (k) as U19", "as U19"),
 "Q8":  ("DFN1006-3: three unequal lands, geometry decides", "G10 (e): INA_PV reads Isc while the head is attached", "-"),
 "Q9":  ("DFN1006-3: geometry decides", "G10 (e): AVDD_ECG off while VBUS with ECG_PWR_EN high", "-"),
 "Q10": ("DFN1006-3: geometry decides", "G10 (e): CHG_DIS high -> charge current to 0 within 2.1 s (TS duty cycle, SLUSDJ8A p.8)", "-"),
 "Q11": ("DFN1006-3: geometry decides", "G10 (h): FL_EN high -> 8.3-9.1 mA into a 330 Ohm +-1 % jig load on J16 at 3.80 V on the pack pads (R160 100 Ohm) [S1 D-6]", "-"),
 "Q12": ("DFN1006-3: geometry decides", "G10 (i): MOTOR_PWM at 3.8 V supply -> 25-40 mA through J17 (jig motor or 100 Ohm load), reversed D17 shows as overcurrent", "-"),
 "Q19": ("DFN1006-3: geometry decides", "G10 (i) + EOL: MOTOR_PWM low, 3.8 V on the pads: MOTOR_S (test via) < 0.1 V and J17- at VBAT through the jig load: a shorted Q12 shows as MOTOR_S = VBAT, a shorted Q19 as no drop across Q19 at 100 % PWM [S1 D-12]", "-"),
 "Q13": ("DFN1006-3: geometry decides", "G10 (j): SW1 pressed -> P0.26 low; released -> high", "-"),
 "Q14": ("DFN1006-3: geometry decides", "G10 (k): approval and block of the PV path (U19 row)", "-"),
 "Q16": ("DFN1006-3: geometry decides", "G10 (k3): test firmware runs the CHG_DIS heartbeat -> VIN_DC follows the PV regardless of the NTC; heartbeat stopped -> VIN_DC < 0.1 V within 2 s [S1 D-1]", "-"),
 "Q17": ("DFN1006-3: geometry decides", "G10 (k)", "-"), "Q18": ("DFN1006-3: geometry decides", "G10 (k): O-2 supply only with VBAT_OK low (V_O2 = 0 V with VBAT_OK high)", "-"),
 "D12": ("SOT883: three unequal lands -> geometry decides (1F); JLC's 0 deg of C549313 has no EasyEDA record: JLC preview of the cathode (large) land before payment", "G10 (f): ship mode in the dark, then 5 V on the contacts -> VDD_1V8 > 1.7 V within 20 s; again with the button pressed for 1 s", "-"),
 "D13": ("bidirectional ESD (ESD761): electrically symmetric", "-", "none"),
 "D14": ("[S2b] polar 2-pad SOD123W (Nexperia land): pin map C6736531.yaml (pad 1 = cathode = marking bar) + JLC preview of the cathode bar at -X", "G10 (e): a reversed D14 blocks the head: no /PG, no charge current", "no USB charging (caught by (e)); never a -5 V path into U15"),
 "D15": ("[mini-ECO F-1] bidirectional ESD (TPD1E10B06, as D18) on the GND contact: electrically symmetric", "-", "none"),
 "D16": ("[S2b] polar 2-pad: pin map C896422.yaml (pad 1 = cathode = VBUS) + JLC preview of the cathode mark", "G10 (e): a reversed D16 conducts VBUS to GND: no /PG, no charge current, head current at its limit", "no USB charging (caught by (e)); the head limits the current"),
 "D18": ("[S2b] bidirectional TVS (TPD1E10B06) on BTN: electrically symmetric", "-", "none"),
 "Q20": ("[S2c F-8] CJBA7002K (C504101) DFN1006-3: three unequal lands, geometry decides (1F); copper = the C478155 land turned 180 deg (JLC 0 deg of C504101 = C478155 + 180): "
         "the layout sets the rotation from this footprint, JLC preview of the large (drain) land toward J18 before payment",
         "G10 (e): charge current flows with the head (Q20 on; body diode alone would add about 0.7 V drop: VBUS >= 4.3 V check); EOL: J18 to GND >= 10 MOhm without a head", "-"),
 "J40": ("[S2c] one rectangular land 2.10 x 1.50 (part of AE1's FEED copper): a 180 deg turn fits the copper; the strip's contact pad on the glass covers the contact point at both "
         "turns (3.84, 1.36) / (2.76, 1.74) (LID_ANTENNA.md); JLC preview of rot 340 deg with the arm toward +X before payment",
         "G10 (m) new: lid closed, S11 at the U.FL-less test point / conducted RSSI at 1 m against a reference board; EOL: J40 to the strip pad <= 0.1 Ohm (lid on, 20 closings, bench list)",
         "turned 180 deg: still contacts the pad (by design); turned 90 deg: land does not fit"),
 "J19": ("[S2b] one land: spring finger under the window frame; the frame's flat underside makes the turn irrelevant (as J11)", "EOL-1: window frame to GND <= 1 Ohm (TP GND)", "none by design of the frame face"),
 "D17": ("SOT883: geometry decides (1F)", "G10 (i): reversed (impossible by geometry) would show as motor overcurrent", "-"),
 "D19": ("SOT883: geometry decides (1F)", "G10 (k): V_O2 follows the PV with VBAT_OK low", "-"),
 "SW1": ("4-pad land fits turned 180 deg, pairs {1,2} / {3,4} swap (electrically the same): actuator side only in the JLC preview (EasyEDA courtyard / 3D at -x)", "G10 (j): press -> P0.26 low; EOL: press test through the membrane", "actuator toward the board centre: the button cannot be pressed: caught by (j) only after casing -> preview mandatory"),
 "J13": ("[S2a] FH34SRJ land: 10 contact pads in one row + 2 retention-tab pads on the other side -> a 180 deg turn does not fit (1F, computed). JLC preview before payment: "
         "lead row / actuator toward -X (away from the fold), FPC entry facing the fold, contact 1 at +Y (pin-1 silk)",
         "G10 (g): panel inserted terminals UP, 20 mA supply limit: test pattern visible, VDD_DISP current <= 1 mA; a flipped FPC (bottom contact, 1<->10: VDD on EXTCOMIN, VSSA on SCLK) shows no pattern",
         "cannot be placed turned (pads do not match); an FPC flipped at assembly is caught by (g)"),
 "J15": ("one land: the rim pin's inner face >= 3.4 x 2.2 mm centred on the land makes the turn irrelevant (ring drawing, E-13)", "EOL-1: contact resistance of both pins; (l) head keying (four keys, no magnet repulsion)", "none by design of the pin face"),
 "J18": ("as J15", "as J15", "none"),
}
# parts whose two orientations are the same circuit by the nature of the part (the net names on the swapped pads differ, the function does not)
NEUTRAL = {"C48260": "bidirectional TVS (TPD1E10B06: one bidirectional channel, SLLSEB1 p.1)", "C398713": "two-terminal crystal, non-polar",
           "C20345399": "bidirectional ESD (ESD761: VBR +-25.5-35.5 V, SLVSH10C p.5)",
           "C718072": "four-pad crystal: 180 deg maps pad 1 <-> 3 (crystal) and 2 <-> 4 (ground)",
           "C253326": "dual NPN whose pin map is its own 180 deg image (E1 B1 C2 / E2 B2 C1): the two identical transistors swap places, each still has 1 k / 10 k and its emitter on GND"}
rows = {}
for v in VARIANTS:
    for ref, p in P[v].items():
        if not p["jlc_placed"] or p["kind"] in ("R", "C", "L"): continue
        pads = pads_of(p["footprint"]); nets = p["pins"]
        m180 = turn_map(pads, 180) if len(pads) > 1 else {pads[0]["num"]: pads[0]["num"]}
        m90 = turn_map(pads, 90) if len(pads) > 1 else None
        fits180 = m180 is not None; fits90 = m90 is not None
        near = None
        if not fits180 and len(pads) > 2:        # [V3F] near-symmetric land: a pad differs by <= 0.10 mm only -> geometry cannot decide (treated as 2F)
            m180n = turn_map(pads, 180, tol=0.10)
            if m180n is not None: near = m180n
        neutral180 = fits180 and all(nets.get(a) == nets.get(b) for a, b in m180.items())
        key = (ref, p["lcsc"], p["footprint"])
        if key in rows: rows[key]["variants"].append(v); continue
        ev = EVID.get(ref)
        if ev is None: raise SystemExit(f"placement_proof: no evidence row for {ref} ({p['value']})")
        if p["kind"] == "spring" or p["lcsc"] == "C221907": cls = "M"      # [V3F] SW1: actuator side is mechanical
        elif near is not None: cls = "2F"
        elif not fits180: cls = "1F"
        elif neutral180 or p["lcsc"] in NEUTRAL: cls = "N"
        elif len(pads) == 2: cls = "P"
        else: cls = "4F" if fits90 else "2F"
        rows[key] = dict(ref=ref, lcsc=p["lcsc"], value=p["value"], footprint=p["footprint"].split(":")[1], side="skin" if p["side"] == "B" else "sky", pads=len(pads),
                         copper_fits_at_180=fits180, copper_fits_at_90=fits90, near_symmetric_0p10=near is not None, same_nets_after_180=neutral180, neutral_by_part=NEUTRAL.get(p["lcsc"]), proof_class=cls, deciding_evidence=ev[0], g10_item=ev[1],
                         effect_of_silent_turn=ev[2] if (fits180 or near is not None) else "- (cannot be placed turned: the pads would not match)", variants=[v])
def sk(r):
    import re; m = re.match(r"([A-Z]+)(\d+)", r["ref"]); return (m.group(1), int(m.group(2)), r["lcsc"])
R = sorted(rows.values(), key=sk)
json.dump(dict(generated_by="tools/placement_proof.py", classes="1F geometry decides | 2F / 4F identity mandatory | P polar two-terminal | N neutral | M mechanically polar, electrically neutral", parts=R),
          open(os.path.join(DESIGN, "placement_proof.json"), "w"), indent=1, ensure_ascii=False)
cnt = {}
for r in R:
    if "v3f" in r["variants"]: cnt[r["proof_class"]] = cnt.get(r["proof_class"], 0) + 1
L = ["# SolarBand V3-F: how each rotation-sensitive placement is proven (BASELINE 16; v2 review R-07, R-19)\n",
     "Generated by `tools/placement_proof.py` from the footprints the board uses (`lib/easyeda_rev.pretty`) and the netlists of all variants. "
     "'Copper fits at 180 deg' is computed: the pad set, turned about the centre of its bounding box, lands on itself within 0.03 mm; 'within 0.10 mm' marks a near-symmetric land "
     "(one pad differs by <= 0.10 mm), which is treated as 2F because the geometry is too close to decide. "
     "'Same nets after 180 deg' is computed from the netlist. R, C and L are non-polar and not listed. Nothing here was run on hardware: G10 items are requirements for the test jig.\n",
     "Classes (ARCHITECTURE 10.3): **1F** pad geometry decides (cplgate G4); **2F / 4F** the copper fits turned, identity evidence (pin map + electrical test) is mandatory; "
     "**P** polar two-terminal part (human-reviewed pin map + electrical test); **N** a turned part connects the same nets; **M** mechanically polar, electrically neutral.\n",
     f"Baseline v3f: " + ", ".join(f"{k}: {v}" for k, v in sorted(cnt.items())) + ".\n",
     "| Ref | Part | Side | Pads | Copper fits at 180 / 90 deg | Same nets after 180 deg | Class | Deciding evidence | G10 / EOL item that catches it | Effect of a silent turn | Variants |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for r in R:
    vv = "all" if len(r["variants"]) == len(VARIANTS) else ", ".join(r["variants"])
    L.append(f"| {r['ref']} | {r['value']} ({r['lcsc']}) | {r['side']} | {r['pads']} | {'yes' if r['copper_fits_at_180'] else ('within 0.10 mm' if r['near_symmetric_0p10'] else 'no')} / {'yes' if r['copper_fits_at_90'] else 'no'} | "
             f"{'yes' if r['same_nets_after_180'] else 'no' if r['copper_fits_at_180'] else '-'} | {r['proof_class']} | {r['deciding_evidence']} | {r['g10_item']} | {r['effect_of_silent_turn']} | {vv} |")
L += ["\n## G10 items added by the review (ARCHITECTURE 10.5 list + these; jig feeds the cell pads from a bench supply, 3.8 V, 20 mA limit raised to 60 mA for item (b))\n",
      "| Item | Stimulus | Pass | Catches |", "|---|---|---|---|",
      "| (a) EN hold | VIN_DC = 0 V (no light, jig PV feed off), firmware drives P0.27 high, wait; then P0.27 low | VDD_1V8 alive for >= 30 s with P0.27 high; VDD_1V8 off within 60 s after P0.27 goes low; on again within 60 s after VIN_DC >= 2 V returns | D9 reversed, Q4, R125, R126, C121 |",
      "| (b) warning LED | ALERT_LED (P0.24) high for 0.5 s | supply current rises by 6-26 mA; red light at the board edge on the window side (photodiode or camera of the jig) | D10 reversed or turned, Q6, R507 |",
      "| (c) power-cycle | firmware drives P0.02 high | VDD_1V8 below 0.3 V within 0.5 s and above 1.7 V again within 3 s, in the dark (VIN_DC = 0 V) and with VIN_DC = 2 V; boot counter incremented | D11 reversed, Q5, Q7, R127, R128, C122, R129, R133 |",
      "| (d) protector | moved to the pack: incoming check of the pack PCM (over-discharge trip, current) | pack maker's values | (pack PCM) |",
      "| (e) charger | 5.0 V on J15 / J18 (through D14), 3.8 V / 60 mA source on J3 / J4 | /PG low < 1 s; 26-33 mA into the pack pads (R140 10.2 k, S1 D-8); AVDD_EN low with ECG_PWR_EN high; INA_PV = Isc under the jig lamp; CHG_DIS high -> 0 mA within 2.1 s | U15, D14, Q8, Q9, Q10, R140-R146 |",
      "| (f) ship wake | ship mode in the dark, then 5 V on the contacts; again: button pressed 1 s | VDD_1V8 > 1.7 V within 20 s in both cases | D12 (both halves), R144 / R145, R165, R167 |",
      "| (g) display | DISP_EN high, test pattern, DISP_CTRL high / low | VDD_DISP 3.0 V +-1.5 %; pattern visible at a 20 mA limit; white with DISP_CTRL low | U16, U17, U21, J13 placement and FPC insertion side (terminals up) |",
      "| (h) front light | FL_EN high (100 %), 330 Ohm +-1 % jig load on J16, pack pads at 3.80 V | 8.3-9.1 mA (R160 100 Ohm; VSTOR_SW 3.70-3.80 V); with a jig LED of stated VF 2.7 +-0.1 V instead: 8.8-12.1 mA [S1 D-6] | Q11, R160, J16 |",
      "| (i) motor | MOTOR_PWM 100 % for 0.2 s at 3.8 V; then MOTOR_PWM low | 25-40 mA (jig motor), no overcurrent; with the gate low MOTOR_S (test via) < 0.1 V [S1 D-12] | Q12, Q19, D17, R162, J17 |",
      "| (j) button | press SW1 (jig plunger at the edge) | P0.26 low while pressed | SW1 orientation, Q13, R164, R165 |",
      "| (k) O-2 | PV lamp on. (k1) MCU in reset, pack pads 3.70 V (VBAT_OK high), NTC pad J5 with 47 k / 10 k / 3.6 k. (k2) MCU in reset, pads 3.0 V (VBAT_OK low), 47 k / 10 k / 3.6 k; repeat with J3 at 0 V. (k3) test firmware with the CHG_DIS heartbeat on, then off | (k1) VIN_DC 0 / 0 / 0 V; (k2) 0 / > 1 V / 0 V; (k3) VIN_DC follows the PV, then < 0.1 V within 2 s [S1 D-1] | U19, U20, Q14, Q16-Q18, C175, R176, D19, ladder |",
      "| (l) contacts | head on the rim pins; reversed head; -5 V on the contacts | + pin charges; a reversed head cannot seat: (K1) the flat GND plunger does not enter the smaller VBUS counterbore, (K2) the housing step stands on the window glass (gap gauge), (K4) the head refuses by its pin check; the magnet only attaches (no repulsion: ferritic target); D14 blocks -5 V [S1 D-7] | J15, J18, D14 |",
      "\nEvery G10 failure blocks the unit and goes back into the G8 corpus (ARCHITECTURE 10.5)."]
open(os.path.join(DESIGN, "placement_proof.md"), "w").write("\n".join(L) + "\n")
print(f"placement_proof: {len(R)} rows; baseline classes {cnt}")
