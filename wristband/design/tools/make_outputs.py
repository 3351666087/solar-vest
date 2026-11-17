"""Collect the V3-F outputs into v3/design/: per variant BOM_<variant>.csv (JLC-placed, grouped by LCSC) and BOM_full_<variant>.csv
(every item incl. DNP, copper-only and off-PCBA items), parts.json (all variants; per part: footprint courtyard area, maximum
seated height with its source, board side, pins/nets), stock_report.md, netclasses.json, and the board_nets section of every
pinmap/<C>.yaml (per pad: datasheet pin name and net, baseline variant, with the other variants where they differ).
Inputs: out/<variant>/parts.json (SKiDL), data/jlc/<C>.json (tools/jlc_query.py, today; older caches read-only as fallback), lib/*.pretty, ../../layout/work/heights.json (v1, read-only).
usage: python make_outputs.py
"""
import csv, json, os, re, sys, datetime, yaml
HERE = os.path.dirname(os.path.abspath(__file__)); DESIGN = os.path.dirname(HERE); WB = os.path.dirname(os.path.dirname(DESIGN))
sys.path.insert(0, HERE)
from kisexp import parse, find, first
MAIN = ["v3f", "v3f_fldnp"]            # full outputs (BOM, stock report, pin maps, netclasses)
# [G1] option variants (levels 0 and 4, tools/run_all.sh builds them): parts.json, BOM and the area check only
OPTIONS = [v for v in ("v3f_o2m", "v3f_o2pack", "v3f_noled", "v3f_noled_o2pack", "v3f_nofl", "v3f_nomotor", "v3f_erm7", "v3f_erm6", "v3f_nofl_noled_nomotor")
           if os.path.exists(os.path.join(DESIGN, "out", v, "parts.json"))]
VARIANTS = MAIN + OPTIONS
BASE = "v3f"
VINFO = {v: json.load(open(os.path.join(DESIGN, "out", v, "variant.json"))) for v in VARIANTS}
BOARDS = 10                    # stock rule: flag when the orderable quantity is < 50 or < 5 x (qty per board x 10 boards)
# [FIX R-05] orderable quantity = min(stockCount, canPresaleNumber). JLC does not document canPresaleNumber; where it is far below
# stockCount the line is treated as short until the BOM tool (an account action) says otherwise.
P = {v: json.load(open(os.path.join(DESIGN, "out", v, "parts.json"))) for v in VARIANTS}

def jlc(c):
    for d in (os.path.join(DESIGN, "data", "jlc"), os.path.join(WB, "cache", "v2", "jlc"), os.path.join(WB, "cache", "jlc")):
        try:
            r = json.load(open(os.path.join(d, f"{c}.json")))
            x = [x for x in r["response"]["data"]["componentPageInfo"]["list"] if x["componentCode"] == c][0]
        except Exception:
            continue
        pr = x.get("componentPrices") or []
        def at(n):
            for p in pr:
                if p["startNumber"] <= n and (p["endNumber"] in (-1, None) or n <= p["endNumber"]): return p["productPrice"]
            return pr[-1]["productPrice"] if pr else None
        pre = x.get("canPresaleNumber"); st = x.get("stockCount") or 0
        return dict(lib="Basic" if x["componentLibraryType"] == "base" else ("Preferred" if x.get("preferredComponentFlag") else "Extended"),
                    stock=st, presale=pre, orderable=st if pre is None else max(min(st, pre), 0), hand=bool(x.get("assemblyComponentFlag")),
                    mpn=x.get("componentModelEn"), mfr=x.get("componentBrandEn"), pkg=x.get("componentSpecificationEn"),
                    p100=at(100), fetched=r["fetched_utc"], desc=(x.get("describe") or "")[:90], cache=os.path.relpath(d, WB))
    return None
def sortkey(ref): return (re.match(r"[A-Z]+", ref).group(0), int(re.sub(r"\D", "", ref) or 0), ref)

# ---------------- footprint courtyard area ----------------
def courtyard(fp):
    lib, name = fp.split(":")
    path = os.path.join(DESIGN, "lib", lib + ".pretty", name + ".kicad_mod")
    t = parse(open(path).read()); xs, ys = [], []
    for kind in ("fp_line", "fp_rect"):
        for g in find(t, kind):
            ly = first(g, "layer")
            if ly and "CrtYd" in ly[1]:
                for k in ("start", "end"):
                    q = first(g, k); xs.append(float(q[1])); ys.append(float(q[2]))
    if not xs: return None
    return round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3)

# ---------------- maximum seated height (mm): v1 table by LCSC + the V2 parts ----------------
H1 = json.load(open(os.path.join(WB, "layout", "work", "heights.json")))
V1P = json.load(open(os.path.join(WB, "design", "parts.json")))["main"]
HEIGHT = {}
for ref, h in H1.items():
    c = V1P[ref].get("lcsc_ref")
    if c: HEIGHT[c] = (h["h"], "v1 layout/work/heights.json (" + h.get("key", "") + ")", "V")
HEIGHT.update({   # (h_max, source, V = datasheet-verified / E = estimate)
 "C509405": (0.40, "nRF52832 PS v1.4 Table 132 p.541: A 0.351 / 0.375 / 0.399", "V"),
 "C4371025": (0.40, "TI YBJ (DSBGA) family: 0.35 mm max in the YBJ0006 drawing 4226653/A (cache/v2/ds_review/ti_mxbg457.pdf, read by the review); the YBJ0008 drawing "
              "of this part is not in the cached SBOSA81D PDF (it holds only the DDF drawing) -> 0.40 kept as an estimate", "E"),
 "C2760012": (1.25, "XB5358D0 REV0.4 p.11: A 0.95-1.25", "V"),
 "C727398": (0.60, "Vishay 66597 TDFN4 1.2 x 1.6 outline: 0.55 nom / 0.60 max (EasyEDA model H0.6); drawing not re-read", "E"),
 "C478155": (0.50, "Nexperia SOT883 description p.2: body 1.0 x 0.6 x 0.5 mm", "V"),
 "C253326": (0.60, "ROHM EMT6 outline: 0.5 typ / 0.6 max; drawing p.8 not re-read", "E"),
 "C130414": (0.70, "Nexperia SOD523: 0.58-0.7 (JEDEC SC-79); drawing not re-read", "E"),
 "C5603826": (0.70, "OSRAM CT DBLP31.12 v1.3 p.11: 0.6 +-0.1", "V"),
 "C125114": (0.70, "Lite-On LTST-S270KRKT p.2: 0.60 +-0.10 (side-looking, lying on the board)", "V"),
 "C598214": (0.90, "Kingbright KA-2810ASURSK p.1: thickness 0.8 mm, tolerance +-0.1 (right-angle LED lying on the board)", "V"),
 "C2826535": (1.50, "BAT WIRELESS BW0036BG drawing 681-0036B-2 (p.6): free height 1.40 +0.10 / -0.05 mm; working height 1.00 mm, limit 0.70 mm", "V"),
 "C144806": (0.40, "0402 thick-film resistor 0.35 +-0.05 (class value)", "E"),
 "C23345": (0.55, "0603 thick-film resistor 0.45 +-0.10 (class value)", "E"), "C22830": (0.55, "0603 thick-film resistor 0.45 +-0.10 (class value)", "E"),
 "C22775": (0.55, "0603 thick-film resistor 0.45 +-0.10 (class value)", "E"),
 "C398713": (0.50, "Seiko SC-16S p.1: 0.5 Max", "V"),
 "C2826523": (1.50, "BAT WIRELESS BW0025BG: free height 1.35 +-0.15 mm = 1.50 mm maximum, working height 0.90 mm (drawing p.6); not used after the review fix (R-04)", "V"),
 "C105226": (0.70, "Samsung CL05A226MQ5QUNC: T 0.5 +-0.2 mm (thickness code, Lens C); spec sheet table not re-read", "E"),
 "C23733": (0.60, "0402 MLCC 0.5 +-0.1 (class value)", "E"),
 "C1554": (0.55, "0402 C0G 0.5 +-0.05 (class value)", "E"),
 "C384960": (0.33, "Murata GRM033: 0.3 +-0.03", "E"), "C237514": (0.33, "Murata GJM033: 0.3 +-0.03", "E"),
 "C7393837": (0.33, "0201 MLCC 0.3 +-0.03 (class value)", "E"), "C76922": (0.33, "Murata GRM033: 0.3 +-0.03", "E"),
 "C98045": (0.33, "Murata LQP03TN: 0.3 +-0.03", "E"),
 "C295786": (0.26, "0201 thick-film resistor 0.23 +-0.03 (class value)", "E"), "C270364": (0.26, "0201 resistor (class value)", "E"),
 "C473048": (0.26, "0201 resistor (class value)", "E"), "C270346": (0.26, "0201 resistor (class value)", "E"), "C285010": (0.33, "0201 MLCC 0.3 +-0.03 (class value)", "E"),
})
for c in ("C25084", "C270612", "C25076", "C11702", "C423177", "C423179", "C477775", "C159047", "C26082"):   # C26082 10 M: DNP only in v1
    HEIGHT[c] = (0.40, "0402 thick-film resistor 0.35 +-0.05 (class value, as the v1 0402 resistors)", "E")
HEIGHT.update({   # [V3F] new parts (max seated height; V = read in the maker drawing today, E = class value)
 "C5208201": (0.80, "TI SLUSDJ8A p.31-32: WSON DSG0008A 0.8 mm max height", "V"),
 "C2867950": (0.40, "TI SBVS277C p.39: DQN0004A X2SON 0.4 mm max height", "V"),
 "C5187176": (0.55, "TI SCES937B p.36: RUT0012A UQFN 0.55 mm max height", "V"),
 "C5217869": (0.60, "TI SCES940A p.35: DRY0006A USON 0.6 mm max height", "V"),
 "C549313": (0.50, "Nexperia BAV70M p.7: SOT883 A 0.46-0.50", "V"),
 "C549275": (0.50, "Nexperia BAT54CM p.6: SOT883 A 0.46-0.50", "V"),
 "C20345399": (0.45, "TI SLVSH10C p.18-20: DPY0002A X1SON 0.45 mm max height", "V"),
 "C896422": (0.40, "onsemi NSR0240MX2 p.4: case 714AB A 0.34-0.37 (0.40 kept)", "V"),
 "C6736531": (1.10, "Nexperia PMEG10020AELR Fig. 16 p.9: CFP3 height 0.9-1.1 mm (max kept) [S2b]", "V"),
 "C324723": (1.00, "Hirose FH34 p.1 / p.6: 1.0 mm above the board (actuator closed) [S2a]", "V"),
 "C221907": (1.35, "C&K PTS840 p.2 (B-41) front view: 1.35 mm above the mounting face; actuator 0.5 mm stem", "V"),
 "C2876045": (0.40, "TI SLVSE13J p.53: DPW0005A X2SON 0.4 mm max", "V"),
 "C2863637": (1.10, "TI SLVSE13J p.59-61: DCK0005A SC70-5 1.1 mm max height [ECO3]", "V"),
 "C478207": (0.50, "Nexperia PMZ350UPE p.1: 1.0 x 0.6 x 0.48 mm; SOT883 A max 0.50", "V"),
 "C17913": (0.65, "1206 thick-film resistor 0.55 +-0.10 (class value; UNI-ROYAL sheet not read)", "E"),
 "C4109": (0.40, "0402 thick-film resistor 0.35 +-0.05 (class value)", "E"), "C43676": (0.40, "0402 thick-film resistor (class value)", "E"),
 "C1538": (0.55, "0402 MLCC 0.5 +-0.05 (class value)", "E"),
 # [G1 level 0] UNI-ROYAL thick-film datasheet V.9 (LCSC C473473, p.4): 0201 H 0.23 +-0.03, 0402 0.35 +-0.05, 0805 0.55 +-0.10; YAGEO RC_L V.12 p.4: RC0201 0.23 +-0.03 (read 2026-11-15)
 "C17445": (0.65, "UNI-ROYAL datasheet V.9 p.4: 0805 H 0.55 +-0.10", "V"),
 "C423797": (0.26, "UNI-ROYAL datasheet V.9 p.4: 0201 H 0.23 +-0.03", "V"), "C473458": (0.26, "UNI-ROYAL V.9 p.4: 0201 H 0.23 +-0.03", "V"),
 "C423582": (0.26, "UNI-ROYAL V.9 p.4: 0201 H 0.23 +-0.03", "V"), "C270345": (0.26, "UNI-ROYAL V.9 p.4: 0201 H 0.23 +-0.03", "V"),
 "C270358": (0.26, "UNI-ROYAL V.9 p.4: 0201 H 0.23 +-0.03", "V"), "C473560": (0.26, "UNI-ROYAL V.9 p.4: 0201 H 0.23 +-0.03", "V"),
 "C473473": (0.26, "UNI-ROYAL V.9 p.4: 0201 H 0.23 +-0.03", "V"), "C851635": (0.26, "YAGEO RC_L V.12 p.4: RC0201 0.23 +-0.03", "V"),
 "C413063": (0.40, "Panasonic ERJ2RK (1005): t 0.35 +-0.05", "V"),
 "C270356": (0.26, "0201 resistor (class value)", "E"), "C270366": (0.26, "0201 resistor (class value)", "E"), "C270365": (0.26, "0201 resistor (class value)", "E"), "C423439": (0.26, "0201 resistor (class value)", "E"),
 "C2691509": (0.26, "0201 resistor (class value)", "E"), "C473632": (0.26, "0201 resistor (class value)", "E"), # [S2b] ECO resistors (class values: UNI-ROYAL thick film 0201 0.23 +-0.03, 0402 0.35 +-0.05, 0603 0.45 +-0.10)
 "C423488": (0.26, "0201 resistor (class value)", "E"), "C166160": (0.26, "0201 resistor (class value) [F R-172]", "E"), "C45993": (0.40, "0402 thick-film resistor 0.35 +-0.05 (class value)", "E"),
 "C25822": (0.55, "0603 thick-film resistor 0.45 +-0.10 (class value)", "E"),
 # [S2c] lid antenna L1 + F-8 (datasheets read 2026-11-15)
 "C2826516": (3.90, "BAT WIRELESS BW0019BG drawing 681-0019B-2 (p.6): free height 3.80 +0.10/-0.05; working 3.00, limit 2.50 (closed unit: compressed to the glass, 2.445-2.545)", "V"),
 "C2826518": (3.10, "BAT WIRELESS BW0020AG-L3.5W1.5H3.0 (ECO2C.md, drawing read by eye): free height 3.00 (zone 3.10 max); working 2.50, limit 2.00 (closed unit: compressed to the glass, 2.445-2.545)", "V"),   # [S2d J-1]
 "C504101": (0.53, "JSCJ CJBA7002K p.4: A 0.47-0.53", "V"),
 "C6652901": (0.60, "Murata LQW15AN spec section 5 p.8: T 0.5 +-0.1", "V"), "C668465": (0.60, "Murata LQW15AN spec section 5 p.8: T 0.5 +-0.1", "V"),
 "C2048575": (0.60, "Murata LQW15AN spec section 5 p.8: T 0.5 +-0.1 [F]", "V"), "C471381": (0.60, "Murata LQW15AN spec section 5 p.8: T 0.5 +-0.1 [F]", "V"),
})
for c in ("C270613", "C25792"):               # [FIX] 3.3 M and 47 k: placed for the first time in V2-B after the review; keep a v1 height if one exists
    HEIGHT.setdefault(c, (0.40, "0402 thick-film resistor 0.35 +-0.05 (class value)", "E"))

# ---------------- parts.json ----------------
allparts = {}
for v in VARIANTS:
    for ref, p in P[v].items():
        cy = courtyard(p["footprint"])
        p["courtyard_mm"] = cy; p["courtyard_area_mm2"] = round(cy[0] * cy[1], 3) if cy else None
        c = p.get("lcsc_ref")
        if p["dnp"]:
            p["height_max_mm"], p["height_source"], p["height_status"] = 0.0, "DNP (pads only)", "verified"
        elif p["jlc_placed"]:
            h = HEIGHT.get(c)
            if h is None:                          # [V3F] class value for plain chip passives that v1 / v2 did not place (e.g. C17168 0 Ohm links FB1-FB6)
                fpn = p["footprint"]
                cls = {"R0402": (0.40, "0402 thick-film resistor 0.35 +-0.05 (class value)"), "C0402": (0.55, "0402 MLCC 0.5 +-0.05 (class value)"),
                       "R0201": (0.26, "0201 resistor (class value)"), "C0201": (0.33, "0201 MLCC (class value)")}
                key = next((k for k in cls if fpn.endswith("_" + k)), None)
                if key is None: raise SystemExit(f"no height for {ref} {c}")
                h = (cls[key][0], cls[key][1], "E")
            p["height_max_mm"], p["height_source"], p["height_status"] = h[0], h[1], ("verified" if h[2] == "V" else "estimate")
        else:
            p["height_max_mm"], p["height_source"], p["height_status"] = 0.0, "copper only", "verified"
        j = jlc(c) if c else None
        if j: p["jlc_lib"], p["jlc_stock"], p["jlc_fetched"], p["mpn"], p["manufacturer"] = j["lib"], j["stock"], j["fetched"], j["mpn"] or p["mpn"], j["mfr"] or p["manufacturer"]
        if c == "C2826535": p["height_note"] = ("tallest part on the board (1.50 mm maximum free height): must sit where the free height under the lid is 1.85 mm (REDESIGN 5.2) and under its "
                                               "mating tab; tab underside 1.00 mm above the land (allowed 0.70-1.30 mm over the tolerance chain)")
        if c == "C2826516": p["height_note"] = ("[S2c] J40 lid-antenna feed finger: 3.90 mm free (max) inside the AE1 pocket; in the closed unit compressed against the strip pad on the "
                                               "glass to 2.445-2.545 mm (BW0019BG: working 3.00, limit 2.50 -> see v3/stage2c/ECO2C.md)")
        if c == "C2826518": p["height_note"] = ("[S2d J-1] J40 lid-antenna feed finger BW0020AG: 3.10 mm free (zone max) inside the AE1 pocket; in the closed unit compressed against the "
                                               "strip pad on the glass to 2.445-2.545 mm, between its working height 2.50 and its limit 2.00 (v3/stage2c/ECO2C.md, LEAD_NOTES 2j J-1)")
        if c == "C221907": p["height_note"] = ("[V3F] 1.35 mm: above the 1.05 mm part budget of BASELINE 8; SW1 sits at the hand-end board edge under the ring / E3 rim, "
                                              "which needs >= 1.50 mm free height there (V3-G9); outside the panel footprint (low-part zone <= 0.70 mm)")
        if j: p["jlc_presale"], p["jlc_orderable"], p["jlc_hand_assembly_flag"] = j["presale"], j["orderable"], j["hand"]
def summary(v):
    pl = [p for p in P[v].values() if p["jlc_placed"]]
    sky = [p for p in pl if p["side"] == "F"]; skin = [p for p in pl if p["side"] == "B"]
    fixed = [p for p in P[v].values() if not p["jlc_placed"] and not p["dnp"] and p["kind"] not in ("nettie", "antenna") and p["side"] == "F"]
    dnp = [p for p in P[v].values() if p["dnp"]]
    return dict(parts=len(P[v]), jlc_placed=len(pl), jlc_placed_sky=len(sky), jlc_placed_skin=len(skin), dnp=len(dnp),
                courtyard_jlc_placed_mm2=round(sum(p["courtyard_area_mm2"] for p in pl), 1),
                courtyard_sky_placed_mm2=round(sum(p["courtyard_area_mm2"] for p in sky), 1),
                courtyard_skin_placed_mm2=round(sum(p["courtyard_area_mm2"] for p in skin), 1),
                courtyard_dnp_pads_mm2=round(sum(p["courtyard_area_mm2"] for p in dnp), 1),
                sky_side_fixed_copper_features_mm2=round(sum(p["courtyard_area_mm2"] for p in fixed), 1),
                tallest_mm=max(p["height_max_mm"] for p in pl), tallest_ref=max(pl, key=lambda p: p["height_max_mm"])["value"])
json.dump({"generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "note": "SolarBand V3-F schematic lane (v3/design). courtyard_mm = bounding box of F.CrtYd of the footprint actually used (lib/easyeda_rev.pretty: pads + body + 0.15 mm "
                   "for chips <= 0603, 0.25 mm otherwise; lib/solarband.pretty: drawn). height_max_mm = maximum seated height, height_status says verified or estimate. "
                   "side F = sky side (all ICs), B = skin face (D3, D4, PD1, plate-dot pads, G10 array).",
           "variants": {v: dict(summary=summary(v), switches=VINFO[v]["switches"], motor=VINFO[v]["motor"], parts=P[v]) for v in VARIANTS}},
          open(os.path.join(DESIGN, "parts.json"), "w"), indent=1, ensure_ascii=False)

# ---------------- BOM per variant ----------------
OFF_PCBA = [   # BASELINE 5.2 off-board and hand-fitted parts
 ("BT1", "protected pack: GEB301030-class 70 mAh cell (>= 66 mAh nominal, >= 60 mAh minimum) + PCM (XB5358D0 class, Iq <= 6 uA) + F1 (hold >= 0.4 A, opens <= 1 A) + NTC 10 k B 3950 K +-1 %, welded by the pack maker; capsule 38.4 x 11.9 x 4.5 mm on strap root A",
  "pack maker RFQ (GEB301030 class)", "root-A flex to J3 (BATT_P) / J4 (GND) / J5 (NTC) / J10 (GND); R130 and R140 are locked to this pack (BOM kit + EOL check of the label)"),
 ("LID1", "PV laminate: 4 IBC strips 27.7 x 2.30 mm in series from Y 21.0 mm, 0.50 mm glass, flex tail (PV+, PV-, backsheet ground)", "custom (lid RFQ)", "tail hand-soldered to J6"),
 ("WING1", "c-Si wing on strap root B: 4 sub-cells 2.7 x 31 mm in series, 3.35 cm2, no diode", "custom (lid RFQ)", "root-B flex to J7 (PV_W+) / J9 (GND)"),
 ("DISP1", "Sharp LS011B7DH03 1.08 inch memory LCD (+ custom front-light film <= 0.25 mm above the panel, LED on the film tail)", "Sharp samples (C18337240 stock 0)", "FPC stiffened end in the J13 ZIF, terminals up (top contact); film tail to J16"),
 ("M1", "ERM coin motor Vybronics VCLP0820B004L class, 8 x 2.1 mm, 3.0 V rated, 30 / 35 mA", "samples (not in the JLC library)", "in the 8.6 mm board cut-out on the floor film, wires to J17"),
 ("E1, E2", "titanium Gr2 electrode plates 0.25 mm, each on two silver-epoxy dots (E11/E12, E21/E22)", "custom", "floor laminate"),
 ("E3", "titanium Gr2 strip on the top rim, tab >= 3.4 x 2.2 mm onto spring finger J11", "custom", "insert in the ring"),
 ("K+, K-", "flush contact pins in the top rim (gold over a nickel-free layer, or 316L / Ti), non-standard pitch and recess, inner faces >= 3.4 x 2.2 mm centred on J15 / J18", "ring moulder RFQ", "insert-moulded"),
 ("HEAD1", "isolated USB-C magnetic head (accessory, UCC12050 reinforced for wearers): 5.0 V >= 4.85 V at 50 mA on the band contacts (D14 drop)", "own JLC PCBA (V3-G10)", "not part of this board"),
]
bom_summ = {}
for v in VARIANTS:
    main = P[v]; groups = {}
    for ref, p in main.items():
        if p["jlc_placed"]: groups.setdefault(p["lcsc"], []).append(ref)
    rows, flagged = [], []
    for c, refs in sorted(groups.items(), key=lambda kv: sortkey(sorted(kv[1], key=sortkey)[0])):
        refs = sorted(refs, key=sortkey); p = main[refs[0]]; j = jlc(c) or {}
        q = len(refs); need = q * BOARDS; risk = ""
        if not j: risk = "NO JLC RECORD"
        elif j["orderable"] < 50 or j["orderable"] < 5 * need:
            risk = f"LOW: orderable {j['orderable']} (stock {j['stock']}, canPresale {j['presale']}) < {'50' if j['orderable'] < 50 else f'5 x {need}'}"
        if j and j["hand"]: risk = (risk + "; " if risk else "") + "NOT SMT-PLACED at JLC (assemblyComponentFlag)"
        sides = sorted({main[r]["side"] for r in refs})
        rows.append(dict(Designator=",".join(refs), Comment=p["value"], Footprint=p["footprint"], LCSC=c, MPN=j.get("mpn") or p["mpn"],
                         Manufacturer=j.get("mfr") or p["manufacturer"], Qty=q, Qty_10_boards=need, Library=j.get("lib", "?"), Side="+".join("top" if s == "F" else "bottom" for s in sides),
                         Stock=j.get("stock", ""), Can_presale=j.get("presale", ""), Price_at_100_USD=j.get("p100", ""), Stock_risk=risk, JLC_queried_UTC=j.get("fetched", "")))
        if risk: flagged.append((c, refs, j, risk))
    with open(os.path.join(DESIGN, f"BOM_{v}.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    full = []
    for ref, p in sorted(main.items(), key=lambda kv: sortkey(kv[0])):
        cls = ("JLC-placed" if p["jlc_placed"] else "DNP (pads only, excluded from BOM/CPL)" if p["dnp"] else "copper only (no component)")
        full.append(dict(Ref=ref, Value=p["value"], LCSC=p["lcsc_ref"] or "", MPN=p["mpn"], Footprint=p["footprint"], Side="top (sky)" if p["side"] == "F" else "bottom (skin)",
                         Courtyard_mm2=p["courtyard_area_mm2"], Height_max_mm=p["height_max_mm"], Class=cls, Function=p["func"]))
    for ref, val, mpn, note in OFF_PCBA:
        if ref == "M1":                                   # [G1 level 4] the motor follows the variant switch SB_MOTOR
            m = VINFO[v]["motor"]
            if m["part"] == "none": continue
            val = f"ERM coin motor {m['part']}, dia {m['dia_mm']:g} x {m['thick_mm']:g} mm, 3.0 V class, <= {m['i_max_mA']} mA, {m['grms']:g} Grms (maker's page)"
            note = f"in the {m['cutout_mm']:g} mm board cut-out on the floor film, wires to J17"
        if ref == "DISP1": note = "[S2a] FPC folded 180 deg toward its rear 1.9 mm from the glass edge, stiffened end into the J13 ZIF terminals UP (top contact, contact n = terminal n); film tail to J16"
        full.append(dict(Ref=ref, Value=val, LCSC="", MPN=mpn, Footprint="-", Side="-", Courtyard_mm2="", Height_max_mm="", Class="off the PCBA (hand-assembled, not on LCSC)", Function=note))
    with open(os.path.join(DESIGN, f"BOM_full_{v}.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(full[0].keys())); w.writeheader(); w.writerows(full)
    bom_summ[v] = dict(rows=rows, flagged=flagged)

# ---------------- stock report ----------------
V1LCSC = {p.get("lcsc_ref") for p in V1P.values() if p.get("lcsc_ref")}
rows = bom_summ[BASE]["rows"]; allrows = {r["LCSC"]: (r, v) for v in reversed(VARIANTS) for r in bom_summ[v]["rows"]}     # the baseline wins
ts = [r["JLC_queried_UTC"] for r, _ in allrows.values() if r["JLC_queried_UTC"]]
L = [f"# JLC stock, library class and price - SolarBand V3-F main board\n",
     f"JLC parts API (`selectSmtComponentList`, public, no login), queried {min(ts)} to {max(ts)} UTC by `tools/jlc_query.py`; raw answers in "
     f"`data/jlc/<C>.json` (fields used; raw answers outside the project). Stock changes hourly. Rule: flag a line when the orderable quantity = min(stockCount, canPresaleNumber) is < 50 or < 5 x the quantity "
     f"for {BOARDS} boards, or when JLC marks the part as not SMT-placed (`assemblyComponentFlag`). `canPresaleNumber` is not documented by JLC (review R-05); only the BOM "
     f"tool, an account action that was not taken, settles what can really be ordered.\n",
     "| Variant | BOM lines | Placements | Basic | Preferred | Extended | Flagged |\n|---|---|---|---|---|---|---|"]
for v in VARIANTS:
    r = bom_summ[v]["rows"]
    L.append(f"| {v} | {len(r)} | {sum(x['Qty'] for x in r)} | {sum(1 for x in r if x['Library'] == 'Basic')} | {sum(1 for x in r if x['Library'] == 'Preferred')} | "
             f"{sum(1 for x in r if x['Library'] == 'Extended')} | {len(bom_summ[v]['flagged'])} |")
L.append("\n## Flagged lines (any variant)\n")
fl = {}
for v in VARIANTS:
    for c, refs, j, risk in bom_summ[v]["flagged"]:
        fl.setdefault(c, [refs, j, risk, []])[3].append(v)
fl = {c: (a, b, r_, "all" if len(vs) == len(VARIANTS) else (", ".join(vs) if len(vs) <= 3 else f"{len(vs)} of {len(VARIANTS)} variants")) for c, (a, b, r_, vs) in fl.items()}
if fl:
    L.append("| LCSC | Part | Refs | Qty/board | Stock | canPresale | Why | Variant |\n|---|---|---|---|---|---|---|---|")
    for c, (refs, j, risk, v) in fl.items(): L.append(f"| {c} | {j.get('mpn','?')} | {','.join(refs)} | {len(refs)} | {j.get('stock','?')} | {j.get('presale','?')} | {risk} | {v} |")
else: L.append("None: every line has an orderable quantity >= 50 and >= 5 x the 10-board quantity.")
L.append("\n## Parts not in the v1 BOM (V2-B and V3-F additions)\n\n| LCSC | MPN | Manufacturer | Package | Library | Stock | USD @100 | Refs (baseline or variant) | Queried UTC |\n|---|---|---|---|---|---|---|---|---|")
for c, (r, v) in sorted(allrows.items(), key=lambda kv: sortkey(kv[1][0]["Designator"].split(",")[0])):
    if c in V1LCSC: continue
    j = jlc(c) or {}
    L.append(f"| {c} | {r['MPN']} | {r['Manufacturer']} | {j.get('pkg','')} | {r['Library']} | {r['Stock']} | {r['Price_at_100_USD']} | {r['Designator']}{'' if v == BASE else ' (' + v + ')'} | {r['JLC_queried_UTC']} |")
L.append("\n## Tightest lines of the baseline (lowest orderable quantity / 10-board need)\n\n| LCSC | Part | Stock | canPresale | Need (10 boards) | Ratio | Library |\n|---|---|---|---|---|---|---|")
def _ord(r): return min(r["Stock"] or 0, r["Can_presale"] if isinstance(r["Can_presale"], int) else (r["Stock"] or 0))
for r in sorted(rows, key=lambda r: _ord(r) / r["Qty_10_boards"])[:12]:
    L.append(f"| {r['LCSC']} | {r['MPN']} | {r['Stock']} | {r['Can_presale']} | {r['Qty_10_boards']} | {max(_ord(r), 0) / r['Qty_10_boards']:.1f}x | {r['Library']} |")
OPT = {"C17913": "1206W4F120JT5E 12 Ohm 1206 250 mW: R130 until gate-1 level 0 (now C17445 0805)",
       "C441935": "ERJ-PA3F3303V 330 k 0603 anti-surge: R301-R306 until stage 2b; now 680 k C25822 (0603WAF6803T5E, 75 V working, 150 V overload; no anti-surge 680 k 0603 stocked at JLC 2026-11-15)",
       "C427255": "ERJPA2F3303X 330 k 0402 anti-surge: NOT used (50 V limiting / 100 V overload against SIM-08's 110 V peak)",
       "C2876046": "TLV7041DPWR open drain X2SON: would drive the Q14 gate without a FET; stock 0",
       "C702121": "TLV7021DPWR open drain X2SON, 5 uA: rejected (stock about 60, 5 uA load on the PV at the check)",
       "C319184": "GRM033R61A225ME47D 2.2 uF 10 V 0201: candidate for the LDO capacitors once its DC-bias curve is read (not used)",
       "C3682876": "BQ25170JDSGR (JEITA): stock fallback for U15 only with the written 45-55 C exception (usbc lane 4.2)",
       "C2876045": "TLV7031DPWR X2SON-5: U19 / U20 until ECO3 (2026-11-16); centre VEE pad cannot be escaped under JLC rules (v3/eco3/ECO3.md)",
       "C180352": "TLV3691IDCKR (0.9 V, 75 nA): rejected for the O-2 window: offset +-15 mV (25 C) / +-22 mV",
       "C2867149": "TLV7041DCKR SC-70-5 open drain: would replace Q17, larger; the X2SON TLV7041DPWR (C2876046) has stock 0",
       "C5244996": "SDM02M30CLP3-7B: second source for D17 / D19 (Diodes, DFN1006-3 common cathode)",
       "C240197": "WSB5546N-2 40 V Schottky DFN1006-2: second source for D14 (EasyEDA land exists)",
       "C5247957": "PMEG4002ELD: not used (no EasyEDA footprint, 404)",
       "C547294": "PMZB290UNE2YL SOT883B: higher-stock alternate for the 13 PMZ290UNE2YL (different land, needs its own review)"}
L.append("\n## Options, alternates and rejected parts (queried in the same run)\n\n| LCSC | MPN | Library | Stock | Note |\n|---|---|---|---|---|")
for c, note in OPT.items():
    j = jlc(c) or {}
    L.append(f"| {c} | {j.get('mpn','?')} | {j.get('lib','?')} | {j.get('stock','?')} | {note} |")
open(os.path.join(DESIGN, "stock_report.md"), "w").write("\n".join(L) + "\n")

# ---------------- pin maps: per pad datasheet pin name + net ----------------
for fn in sorted(os.listdir(os.path.join(DESIGN, "pinmap"))):
    if not fn.endswith(".yaml") or fn.endswith(".nets.yaml"): continue
    c = fn[:-5]; rows_ = {}
    for v in MAIN:
        for ref, p in P[v].items():
            if p.get("lcsc_ref") != c: continue
            for num, net in p["pins"].items():
                rows_.setdefault(ref, {}).setdefault(num, {})[v] = net
    out = {}
    for ref, pins in sorted(rows_.items(), key=lambda kv: sortkey(kv[0])):
        o = {}
        for num, byv in pins.items():
            name = next(P[v][ref]["pinnames"][num] for v in byv)
            base = byv.get(BASE, None) if BASE in byv else None
            e = {"pin": name, "net": (base if BASE in byv else next(iter(byv.values()))) or "not connected"}
            diff = {v: (n or "not connected") for v, n in byv.items() if (n or "not connected") != e["net"]}
            if BASE not in byv: e["only_in"] = sorted(byv)
            if diff: e["other_variants"] = diff
            o[str(num)] = e
        out[ref] = o
    path = os.path.join(DESIGN, "pinmap", fn); txt = open(path).read()
    txt = txt.split("\nboard_nets:")[0].rstrip("\n") + "\n"
    if out:
        txt += "board_nets:   # per reference and pad: datasheet pin name and net (baseline variant " + BASE + "; differences listed)\n"
        txt += "".join("  " + l + "\n" for l in yaml.dump(out, sort_keys=False, allow_unicode=True, width=160).splitlines())
    else:
        txt += "board_nets: {}   # this part is not used in any V3-F variant (v1 / V2-B only)\n"
    open(path, "w").write(txt)

# ---------------- netclasses ----------------
main = P[BASE]
NC = {
 "PWR_HIGH": dict(nets=["VSTOR", "VSTOR_SW", "VBAT_IC", "BATT_P", "BATT_P_A", "VIN_DC", "PV_NODE", "PV_SW", "PV_Q", "PV_W", "LBOOST", "LBUCK", "VLED", "VDD_1V8",
                        "VBUS_K", "VBUS", "MOTOR_N"],
    track_mm=0.30, clearance_mm=0.15, via_mm=[0.20, 0.40],
    why="BQ25570 boost CBC 230 mA / buck 185 mA; PV up to ~60 mA through Q14 and R130 (cold start 36-52 mW in R130, CALC_V3F 2); pack path BATT_P carries the U12 inrush ~0.3 A "
        "and the motor start <= 80 mA; VBUS 33 mA (U15); motor 30-80 mA on MOTOR_N / VBAT_IC (J17 + and D17 at VBAT_IC, next to C106). LBOOST / LBUCK loops as short as possible."),
 "GND": dict(nets=["GND", "GND_A1", "GND_A2", "GND_B"], track_mm=0.30, clearance_mm=0.10, via_mm=[0.20, 0.40],
    why="solid ground planes; B.Cu and L5 void under the electrode plates; GND_A1 / GND_A2 are the guard conductors between BATT_P and NTC in strap root A (through FB2 / FB4)."),
 "PWR_LOW": dict(nets=["AVDD_ECG", "INA_VS", "VDD_DIS", "DEC1", "DEC2", "DEC3", "DEC4", "DCC", "DCDC_MID", "VDD_DISP", "V_O2", "FL_A", "FL_K", "DISP_EN"],
    track_mm=0.20, clearance_mm=0.10, via_mm=[0.20, 0.40],
    why="nRF52832 decoupling / DC/DC nodes (Nordic reference layout); AVDD_ECG star from U3; VDD_DISP from U16 (<= 1 mA); V_O2 the O-2 supply (<= 25 uA); front light <= 8 mA."),
 "RF_50R": dict(nets=["RF_ANT", "RF_50R", "ANT_FEED"], impedance_ohm=50, structure="to be re-derived for the 6-layer 1.0 mm stack (SIM-12 re-run)",
    why="as V2-B; radiator geometry from V3-G3a."),
 "ECG_PAIR": dict(nets=["ECG_INP", "ECG_INN"], track_mm=0.15, clearance_mm=0.20, diff_pair=True, length_match_mm=0.5,
    why="R-ECG-1: symmetric inputs, >= 8 mm from L1 / L2, the motor (J17, Q12, D17) and the display SPI / EXTCOMIN lines."),
 "ECG_ELECTRODE": dict(nets=["E1_PAD", "E1_LINK", "E1_MID", "E2_PAD", "E2_LINK", "E2_MID", "E3_PAD", "E3_MID", "RLD_OUT", "RLD_INV", "RLD_Z"], track_mm=0.15, clearance_mm=0.30,
    why="IEC 61000-4-2 entry nets before the 330 k chain; no ground or pour on B.Cu / L5 facing the plates."),
 "MOHM_KEEPOUT": dict(nets=["VBAT_OV", "OK_PROG", "OK_HYST", "VOUT_SET", "VRDIV", "VREF_SAMP", "GND_PMIC", "BQ_EN", "EN_HOLD", "CYC_G", "CYC_A",
                            "O2_G", "O2_TC", "O2_TH", "VB_DET", "BTN", "BTN_SUP", "BTN_N"], track_mm=0.15, clearance_mm=0.30,
    no_copper_pour=True, min_leakage_ohm=1e10,
    why="R-PMIC-1 as v1, the V2-B hold nodes, and [V3F] O2_G (10 MOhm / 100 nF hold of Q14), the O-2 chain taps (732 k / 162 k / 52.3 k: 1 nA of leakage = 0.05 mV), "
        "VB_DET (1 MOhm divider: also the D12A wake source), the button nodes (100 k / 1 MOhm)."),
 "NTC_SENSE": dict(nets=["NTC", "NTC_A", "NTC_ADC", "O2_NC", "O2_OK", "O2_PV", "ISET", "ISET_RC", "VSET"], track_mm=0.15, clearance_mm=0.20,
    why="[V3F] pack NTC node shared by the BQ25170 TS (38 uA), the O-2 ladder (100 k) and the MCU AIN (1 M): route as a guarded analog trace from the root-A land (J5 / FB3) to U15, U19, U20, R116, R149, "
        "away from SPI, EXTCOMIN, motor and PWM lines; ISET / VSET of U15 short and quiet (ISET is the current-sense node)."),
 "ECG_LOCAL": dict(nets=["ECG_VREFP", "ECG_VCAP1", "ECG_VCAP2", "PGA1P", "PGA1N", "PGA2P", "PGA2N"], track_mm=0.15, clearance_mm=0.15, why="as v1 (SBAS502C Fig. 73)."),
 "XTAL": dict(nets=["XC1", "XC2", "XL1", "XL2"], track_mm=0.15, clearance_mm=0.20, why="short, symmetric, ground guard; no copper under the SC-16S body (Seiko remark)."),
 "PPG_ANALOG": dict(nets=["PD1_IN", "PD_GND", "PPG_VREF", "LED1_DRV", "LED2_DRV"], track_mm=0.15, clearance_mm=0.15,
    why="PD cathode node is a nA input crossing the board from the skin-face photodiode to the sky-side MAX86141: one via, guarded by PD_GND."),
 "DISPLAY": dict(nets=["D_SCLK", "D_SI", "D_SCS", "D_EXTCOMIN", "D_DISP"], track_mm=0.10, clearance_mm=0.10,
    why="[V3F] 3 V panel lines from U17 / U21 to the FPC land J13: short (edge rate <= 50 ns at the panel, LD-29Y03 p.22), >= 8 mm from the ECG inputs; EXTCOMIN 60 Hz "
        "is a coupling source for E3 (display lane 3.6)."),
 "SIGNAL": dict(nets="all others", track_mm=0.10, clearance_mm=0.10, via_mm=[0.20, 0.40], why="0.10 / 0.10 mm (0.09 only in the WLCSP fan-out); via-in-pad under WLCSP / DSBGA inner balls."),
}
rule_areas = [
 dict(name="PLATE_VOID", rules=["B.Cu and L5 void under the two electrode plates except the plate-dot pads and the TMP117 thermal island", "vias under the plates covered by mask and >= 1 mm from a dot opening",
        "no via of a PWR_HIGH net or of VDD_1V8 under a plate: only GND and nets behind >= 100 kOhm (review R-14)",
        "J8 (bare ENIG with VSTOR, VLED, VIN_DC, AVDD_ECG, VDD) and every other mask-free B.Cu feature >= 2 mm from the plate edges and from the dot openings (review R-14)",
        "[V3F] the 8.6 mm motor cut-out sits between E1 and E2 (planning centre X 20.0, Y 25.4 mm, BASELINE 5.1): the plate outlines and the cut-out are fixed together in V3-G9"],
      source="REDESIGN 5.5, 5.7; review R-14; BASELINE 5.1, 7"),
 dict(name="ELECTRODE_TEST_PADS", around=["TP1", "TP2", "TP3", "TP4", "TP5", "J11"], rules=["bare pads on the electrode nets ahead of the 2 x 330 kOhm: >= 1 mm to copper of any net above 0.5 V (review R-14)"], source="review R-14"),
 dict(name="ROOT_A_ENTRY", around=["J3", "J4", "J5", "J10", "FB1", "FB2", "FB3", "FB4"], rules=["[V3F] land order along the root wall BATT_P (J3) | GND (J4) | NTC (J5) | GND (J10): pads 1.0 x 4.0 mm at 1.5 mm pitch (gap 0.5 mm), span 5.5 mm inside X 4.5-10.5 mm (BASELINE 1, 4, 7)",
        "one 0402 link per conductor, next to its land (FB1-FB4); the strap tails are quarter-wave monopoles at 2.44 GHz (BASELINE 13.1)",
        "BATT_P_A to every other net >= 0.5 mm; no third net between the J3 and J4 lands (a root short is the cell short of BASELINE 13.2; F1 sits in the pack)"],
      source="BASELINE 4, 7, 13.1, 13.2"),
 dict(name="ROOT_B_ENTRY", around=["J7", "J9", "FB5", "FB6"], rules=["[V3F] wing tail PV_W+ (J7) | GND (J9) with FB5 / FB6 at the lands; PV_W joins PV_NODE before RSH1 so INA_PV measures lid + wing"], source="BASELINE 4"),
 dict(name="CONTACTS", around=["J15", "J18", "D13", "D14"], rules=["[V3F] J15 / J18 at the elbow-end corner under the rim pins (X 0.4-3.7, Y 20.2-31.6 mm; contact zone 15.7 mm from the antenna keep-out, BASELINE 1, 13.1)",
        "D13 next to J15 (one via at most between the land and the TVS), then D14, then C130 at U15 IN",
        "mating pin inner face >= 3.4 x 2.2 mm centred on each spring-finger land (rotation-neutral, BASELINE E-13); free height >= 1.60 mm at the fingers"],
      source="BASELINE 1, 13.1, 16; SLVSH10C layout guidelines"),
 dict(name="TMP117_ISLAND", around=["U10"], rules=["thermal-via island under U10 down to B.Cu under a plate; isolated copper (not on an electrode net)"], source="REDESIGN 5.7"),
 dict(name="VREF_SAMP_100G", around=["C104", "U1 pin 4"], rules=["VREF_SAMP >= 100 GOhm to every other node"], source="SIM-02 (v1)"),
 dict(name="PMIC_NO_POUR", around=["R101-R107", "R125", "R126", "C121", "C104", "NT1", "R170-R172", "R174", "C174"], rules=["no pours / planes under the divider, CREF, MOhm hold-node and O-2 chain footprints"], source="R-PMIC-1; CALC_V3F 3"),
 dict(name="WLCSP_LIGHT", around=["U6", "U8", "U4", "U5", "U19", "U20"], rules=["bare-die / X2SON packages under the opaque lid or the opaque mask of the window: no direct light (photo-currents in nA nodes)",
        "no line of sight from D10, from its light window, from the front-light film or from the SWD / lid-tail openings to U6, U8, U4, U5 (review R-06)"], source="REDESIGN S-9; review R-06"),
 dict(name="SC16S_NO_PATTERN", around=["X2"], rules=["no copper under the crystal body"], source="Seiko SC-16S p.1"),
 dict(name="ECG_NOISE_DISTANCE", rules=["L1, L2, Q12 / D17 / J17 (motor), Q11 / J16 (front-light PWM), U17 / U21 / J13 (display lines) >= 8 mm from the ADS1291 inputs and the electrode networks"], source="R-ECG-1; BASELINE 13.2"),
 dict(name="ANTENNA", rules=["keep-out and radiator geometry from V3-G3a; ERM can and magnet >= 10 mm (planned 20.9 mm), contact pins 15.7 mm, rib insert, front-light tail (BASELINE 13.1)"], source="V3-G3a"),
 dict(name="LOW_PART_ZONE", rules=["[V3F] under the display panel (board X 1-33, Y 6-20 mm): only parts with height_max_mm <= 0.70 (parts.json); tall parts (> 0.70 mm) outside it: "
        "U15 0.80, SW1 1.35, J11 / J15 / J18 1.50, D10 0.90, L1 / L2, the 0603 and 1206 parts (BASELINE 5.3, 7)"], source="BASELINE 5.3, 7, 8"),
 dict(name="MOTOR_CUTOUT", around=["J17"], rules=["[V3F] 8.6 mm board cut-out under the PV band, planning centre X 20.0, Y 25.4 mm; J17 at its edge; Q12 / D17 within 5 mm of J17 (loop of the 30-80 mA motor current)",
        "the narrow board strip beside the cut-out: routing and drop strength checked in V3-G1"], source="BASELINE 1, 5.1, 18 V3-G1"),
 dict(name="BUTTON", around=["SW1"], rules=["[V3F] SW1 at the hand-end board edge below E3, actuator toward the wall membrane (side actuated, C&K B-41); 1.35 mm tall: needs >= 1.50 mm free height at the edge (V3-G9)"], source="BASELINE 1, 16"),
 dict(name="EDGE_LED", around=["D10"], rules=["at the board edge facing the light window of the ring; light-tight pocket (review R-06)",
        "lands = Kingbright's recommended pattern (1.4 x 0.9 mm, gap 1.0 mm), which is what the JLC footprint of C598214 has"], source="REDESIGN decision 5 (b); review R-06"),
 dict(name="RLIM_1206", around=["R130"], rules=["[V3F] R130 1206 250 mW carries the cold-start clamp current: 36 mW at 1 sun 25 C, 52 mW at 1.2 sun -10 C (BASELINE 11.5): copper for heat spreading"], source="BASELINE 11.5"),
 dict(name="SPRING_TABS", around=["J11", "J15", "J18"], rules=["mating tab / pin >= 3.4 x 2.2 mm centred on the pad centre (contact at 0 and 180 deg)",
        "tab underside 1.00 mm above the land in the closed unit, 0.70-1.30 mm over the whole tolerance chain (review R-04)"], source="REDESIGN 5.8 item 6; BW0036BG drawing 681-0036B-2"),
]
fixed_features = [  # sky-side features without a net, for the placement lane (BASELINE 5.1, 7)
 dict(name="rib post feet", count=6, area_mm2_each=1.0, where="board Y 19.8-20.8 mm, X ~ 4 / 10 / 16 / 22 / 28 / 33 mm (pitch <= 6 mm)", source="BASELINE 5.1 (placement area -6.0 mm2)"),
 dict(name="motor cut-out", count=1, area_mm2_each=66.2, where="8.6 mm circle (+0.3 mm band), centre X 20.0, Y 25.4 mm", source="BASELINE 5.1 (placement area -66.2 mm2)"),
]
allnets = sorted({v for p in main.values() for v in p["pins"].values() if v})
assigned = {n for c in NC.values() if isinstance(c["nets"], list) for n in c["nets"]}
missing = [n for n in assigned if n not in allnets]
if missing: raise SystemExit(f"netclass nets not in the netlist: {missing}")
json.dump(dict(board="SolarBand V3-F main (baseline " + BASE + ")", generated=datetime.date.today().isoformat(),
               source="v3/decide/BASELINE.md 4, 7, 13 + REDESIGN_V2 5.8 layout row + ARCHITECTURE 5.2-5.5; RF and stack values wait for SIM-12 and V3-G3a",
               netclasses=NC, signal_nets=[n for n in allnets if n not in assigned], rule_areas=rule_areas, fixed_features_without_net=fixed_features),
          open(os.path.join(DESIGN, "netclasses.json"), "w"), indent=1, ensure_ascii=False)
for v in VARIANTS:
    s_ = summary(v); r = bom_summ[v]["rows"]
    print(f"{v}: BOM {len(r)} lines / {sum(x['Qty'] for x in r)} placements; flagged {len(bom_summ[v]['flagged'])}; courtyard placed {s_['courtyard_jlc_placed_mm2']} mm2 "
          f"(sky {s_['courtyard_sky_placed_mm2']}, skin {s_['courtyard_skin_placed_mm2']}); fixed sky pads {s_['sky_side_fixed_copper_features_mm2']} mm2; tallest {s_['tallest_mm']} mm")
