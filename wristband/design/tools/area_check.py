"""Board-area check of the V3-F main board (task item 5; BASELINE 5.3, 18 V3-G1): courtyards of the built netlist per zone, on the project
metric and on v1's bounding-box measure, for 37 x 29 mm (40 mm pod) and 38 x 29 mm (41 mm pod), compared item by item with BASELINE 5.3.

Project metric (v3/decide/calc/v3_calc_copy.py density() + area_config(), baseline_calc.py area(); reproduced here, nothing imported):
  placement = board area (1056 mm2 at 37 x 29 with corner radii, +29 mm2 per extra mm of length) - 0.5 mm edge band (2 x (X + Y) x 0.5)
              - antenna keep-out 15 mm2 - fixed sky-side features - motor cut-out (pi d^2 / 4 + 0.3 pi d, d = 8.6 mm) - 6 rib post feet x 1.0 mm2
  utilisation = courtyard / placement; v1's measure = utilisation x 399.5 / 360.7 (gate-1 lane note, v2/gates/g1/PROGRESS.md); limit 0.62.
  courtyard = F.CrtYd boxes of the JLC-placed sky-side parts (parts.json) + the hand-soldered lands J13, J16, J17 (the baseline counts them as
  courtyard); fixed = root entry lands, lid-tail land J6, SWD group J12, EOL test pads TP1-TP5 and the two V2 lid posts (12.3 mm2, carried E).
  Fiducials and DNP lands are outside the metric (as in V2's 360.7 mm2); the 'PCB' rows add them (conservative: the lands exist in every build).
Zones (baseline_calc.py zone()): parts with height_max_mm > 0.70 may not sit under the panel (33 x 15 mm = 495 mm2 incl. 0.5 mm frame margin);
  tall-zone utilisation = tall courtyard / (placement - 495).
[G1, 2026-11-15] The board is 38 x 29 mm (pod 41 x 32, the lead's decision); every schematic option of v3/g1/dense is a row; courtyards are also
reported with the DNP lands and sky fiducials (PCB), per height class (<= 0.30, <= 0.45, <= 0.70, > 0.70 mm body height), and against the CAD keep-outs.
Reads (read-only): design/parts.json; v2/design/parts.json (dock_wlcsp and dock_wlcsp_p0201 courtyards); v3/decide/calc/baseline_calc.json and
  v3_calc_copy.json (the BASELINE numbers and its item lists). Writes: design/area_check.md, design/area_check.json.
usage: python area_check.py
"""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__)); DESIGN = os.path.dirname(HERE)
V3 = os.path.dirname(DESIGN); W = os.path.dirname(V3)
P = {v: x["parts"] for v, x in json.load(open(os.path.join(DESIGN, "parts.json")))["variants"].items()}
V2 = json.load(open(os.path.join(W, "v2", "design", "parts.json")))["variants"]
BC = json.load(open(os.path.join(V3, "decide", "calc", "baseline_calc.json")))
VC = json.load(open(os.path.join(V3, "decide", "calc", "v3_calc_copy.json")))

LIMIT = 0.62
V1 = 399.5 / 360.7
PANEL = 33.0 * 15.0
CUT_D = 8.6
CUT = math.pi * CUT_D ** 2 / 4.0 + 0.3 * math.pi * CUT_D          # 66.19 mm2 (baseline_calc.py area())
POSTS = 6 * 1.0
KEEPOUT = 15.0
LID_POSTS_V2 = 12.3                                                 # redesign/v2_calc.py FIX_DOCK item 'two lid posts' (E, no footprint)
HAND_LANDS = ("J13", "J16", "J17")                                  # counted as courtyard by the baseline (DISP_BLOCK J13, PARTS_NEW J16 / J17)
FIXED_REFS = ("J3", "J4", "J5", "J10", "J7", "J9", "J6", "J12", "TP1", "TP2", "TP3", "TP4", "TP5")

def board(xlen, ylen=29.0):
    area = 1056.0 + (xlen * ylen - 37.0 * 29.0)                     # corner radii as the 37 x 29 outline (1056 mm2)
    return area - 0.5 * 2 * (xlen + ylen)
def cutout(d): return 0.0 if d <= 0 else math.pi * d ** 2 / 4.0 + 0.3 * math.pi * d     # motor cut-out + 0.3 mm band (baseline_calc.py area())

def metric(cy, fixed, xlen, tall=None, ylen=29.0, cut=None, cad=0.0):
    """cut: motor cut-out area (default the 8.6 mm baseline); cad: CAD-only no-parts area (stage-1 cross-check: 132.0 mm2)"""
    pa = board(xlen, ylen) - KEEPOUT - fixed - (CUT if cut is None else cut) - POSTS - cad
    d = dict(board_mm=f"{xlen:g} x {ylen:g}", courtyard_mm2=round(cy, 1), fixed_mm2=round(fixed, 1), placement_mm2=round(pa, 1),
             utilisation=round(cy / pa, 3), utilisation_v1=round(cy / pa * V1, 3), pass_project=cy / pa <= LIMIT, pass_v1=cy / pa * V1 <= LIMIT)
    if tall is not None:
        za = (pa + cad) - PANEL                                     # tall zone: design convention (the CAD keep-outs lie almost entirely under the panel)
        d.update(tall_courtyard_mm2=round(tall, 1), tall_zone_mm2=round(za, 1), tall_zone_util=round(tall / za, 3),
                 tall_zone_util_v1=round(tall / za * V1, 3), low_courtyard_mm2=round(cy - tall, 1),
                 low_fill_of_panel_zone=round((cy - tall) / PANEL, 3))
    return d

# ---------------- the design as built ----------------
def items(v, pcb=False):
    """{ref: (courtyard, height, block, value)} of the metric's courtyard; pcb=True adds DNP lands and the sky fiducials"""
    out = {}
    for r, p in P[v].items():
        if p["side"] != "F": continue
        a = p.get("courtyard_area_mm2") or 0.0
        if (p["jlc_placed"] or r in HAND_LANDS) or (pcb and (p["dnp"] or p["kind"] == "fid")):
            out[r] = (a, p.get("height_max_mm") or 0.0, p["block"], p["value"])
    return out
def fixed_of(v):
    f = {r: P[v][r]["courtyard_area_mm2"] for r in FIXED_REFS}
    return f, sum(f.values()) + LID_POSTS_V2
def tall_of(it): return sum(a for a, h, _, _ in it.values() if h > 0.70)

# ---------------- BASELINE 5.3 rebuilt per ref (sanity check against baseline_calc.json) ----------------
def baseline_items():
    a = V2["dock_wlcsp"]["parts"]; b = V2["dock_wlcsp_p0201"]["parts"]
    keep0402 = {"R108", "R131"}                                       # baseline_calc P0201_KEEP_0402 (10 MOhm stays 0402)
    base = {}
    for r, p in a.items():
        if not (p.get("jlc_placed") and p["side"] == "F"): continue
        cy = p["courtyard_area_mm2"]
        if r not in keep0402 and b[r]["courtyard_area_mm2"] != cy: cy = b[r]["courtyard_area_mm2"]
        base[r] = (cy, p.get("height_max_mm") or 0.0, "v2:" + p["block"], p["value"])
    cfg = VC["board_area"]["configs"]["V3-R with USB on pod-top pads (D-4 b, no tab)"]
    for x in cfg["removed"]: base.pop(x["ref"], None)
    for x in cfg["added"]: base[x["ref"]] = (x["courtyard_mm2"], x["height_max_mm"] or 0.0, "v3r", x["part"][:60])
    for r in ("R144", "R145", "R146", "R149"):                        # baseline_calc P0201_V3_USB: 0402 1.50 -> 0201 (saving 0.79 each)
        c, h, blk, val = base[r]; base[r] = (round(c - 0.79, 2), 0.33, blk, val + " (0201)")
    for x in BC["baseline_V3F"]["area"]["added"]:
        if x["ref"] in ("0201", "D12 (old)"): continue                 # 0201 lump replaced by the per-ref values above; D12 replaced below
        base[x["ref"]] = (x["courtyard_mm2"], x.get("height_max_mm") or 0.0, "v3f", x["part"][:60])
    return base
BASE = baseline_items()
BASE_CY = sum(a for a, _, _, _ in BASE.values())
BASE_FIXED = VC["board_area"]["configs"]["V3-R with USB on pod-top pads (D-4 b, no tab)"]["fixed_features_mm2"]
ba = BC["baseline_V3F"]["area"]
sanity = dict(rebuilt_courtyard_mm2=round(BASE_CY, 1), baseline_calc_courtyard_mm2=ba["courtyard_mm2"],
              rebuilt_placement_mm2=metric(BASE_CY, BASE_FIXED, 37.0)["placement_mm2"], baseline_calc_placement_mm2=ba["placement_area_mm2"])
assert abs(sanity["rebuilt_courtyard_mm2"] - sanity["baseline_calc_courtyard_mm2"]) < 0.2, sanity
assert abs(sanity["rebuilt_placement_mm2"] - sanity["baseline_calc_placement_mm2"]) < 0.2, sanity

# ---------------- gate 1, level 0 and level 4 options (v3/g1/dense/DENSE.md) ----------------
S1 = {v: x["parts"] for v, x in json.load(open(os.path.join(V3, "design_s1", "parts.json")))["variants"].items()}   # frozen stage-1 state
VAR = json.load(open(os.path.join(DESIGN, "parts.json")))["variants"]
CAD_S1 = 132.0            # v3/stage1/checks/cross_check.json: CAD-only no-parts area at stage 1 (FPC corridor net of J13 110.0, lid tail 4.9, K zone 6.6, J11 1.2, rail feet 5.4, legs 3.1, film tail 0.7)
CLASSES = [("<= 0.30", 0.0, 0.30), ("<= 0.45", 0.30, 0.45), ("<= 0.70", 0.45, 0.70), ("> 0.70", 0.70, 99.0)]
LED = ("D10", "R507", "Q6", "R508")
O2_REFS = ("Q14", "R174", "C174", "Q16", "C175", "R176", "Q17", "R175", "Q18", "D19", "C170", "R170", "R171", "R172", "U19", "U20")

def collect(parts):
    """courtyard sums of one variant: placed sky parts per height class, hand lands, DNP lands, sky fiducials, fixed features"""
    d = dict(placed=0.0, hand=0.0, dnp=0.0, fid=0.0, fixed=0.0, n_placed=0, tall=0.0, cls={k: 0.0 for k, _, _ in CLASSES}, ncls={k: 0 for k, _, _ in CLASSES},
             o2=0.0, n_o2=0, sizes={})
    for r, p in parts.items():
        if p["side"] != "F": continue
        a = p.get("courtyard_area_mm2") or 0.0; h = p.get("height_max_mm") or 0.0
        if p["jlc_placed"]:
            d["placed"] += a; d["n_placed"] += 1
            k = next(k for k, lo, hi in CLASSES if lo < h <= hi or (lo == 0.0 and h <= hi))
            d["cls"][k] += a; d["ncls"][k] += 1
            if h > 0.70: d["tall"] += a
            if r in O2_REFS: d["o2"] += a; d["n_o2"] += 1
            m_ = __import__("re").search(r"_([RCL])(0201|0402|0603|0805|1206)(-RD)?$", p["footprint"])
            if m_: d["sizes"][m_.group(2)] = d["sizes"].get(m_.group(2), 0) + 1
        elif r in HAND_LANDS: d["hand"] += a
        elif p["dnp"]: d["dnp"] += a
        elif p["kind"] == "fid": d["fid"] += a
        elif r in FIXED_REFS: d["fixed"] += a
    d["fixed"] += LID_POSTS_V2
    d["courtyard"] = d["placed"] + d["hand"]                         # project convention (BASELINE 5.3: hand lands J13 / J16 / J17 count as courtyard)
    d["courtyard_pcb"] = d["courtyard"] + d["dnp"] + d["fid"]        # + DNP lands + sky fiducials
    return d

ROWS = [  # (id, label, parts dict, motor cut-out diameter, wearer cost)
 ("S1", "stage 1 as built (design_s1)", S1["v3f"], 8.6, "-"),
 ("L0", "LEVEL 0 = new baseline v3f: smaller passives, C&K land for SW1, trimmed lands, O-2 with R174 in 0201", P["v3f"], 8.6, "none"),
 ("L0-fldnp", "v3f_fldnp: level 0, front light DNP (research build, same PCB)", P["v3f_fldnp"], 8.6, "none (build option)"),
]
OPT_ROWS = [
 ("L0+o2m", "v3f_o2m", "level 0 option: O-2 with one gate FET (15 parts; two open points, calc/o2_dense.py)", "none"),
 ("L0+PCM", "v3f_o2pack", "level 0, O-2 in the pack PCM (reserve 3; needs the pack RFQ and a maker's answer for 1.5 V to VDL)", "none if the PCM covers every cell state; else no solar restart of a deeply discharged cell"),
 ("L4-led", "v3f_noled", "level 4: skin-hot LED chain removed (reserve 1; only the supervisor releases it)", "no warning light; vibration + screen + BLE carry the alert"),
 ("L4-led+PCM", "v3f_noled_o2pack", "reserves 1 + 3", "as the two rows above"),
 ("L4-fl", "v3f_nofl", "level 4: front light removed (driver and J16 land)", "no reading in the dark"),
 ("L4-motor", "v3f_nomotor", "level 4: motor block removed (no cut-out)", "no haptics: no silent alarm, no vibration alert (decision 5 (d) falls back to the LED)"),
 ("L4-erm7", "v3f_erm7", "level 4: smaller ERM Vybronics VC0720B088L dia 7 x 2.1 mm (7.6 mm cut-out)", "0.10 Grms against 0.25 Grms; 85 mA max against 35 mA"),
 ("L4-erm6", "v3f_erm6", "level 4: smaller ERM Vybronics VC0625B001L dia 6 x 2.5 mm (6.6 mm cut-out)", "0.30 Grms (50 g), 100 mA max; 0.4 mm thicker than the motor column allows"),
 ("L4-all", "v3f_nofl_noled_nomotor", "level 4: front light, LED chain and motor removed", "all three costs"),
]
for i_, v_, lab, cost in OPT_ROWS:
    if v_ in VAR: ROWS.append((i_, lab, VAR[v_]["parts"], VAR[v_]["motor"]["cutout_mm"], cost))

XL, YL = 38.0, 29.0
G1 = []
for i_, lab, parts, cut_d, cost in ROWS:
    c = collect(parts); cut = cutout(cut_d)
    def m(cy, cad=0.0, xl=XL, yl=YL): return metric(cy, c["fixed"], xl, c["tall"], ylen=yl, cut=cut, cad=cad)
    row = dict(id=i_, label=lab, wearer_cost=cost, placed_parts=c["n_placed"], courtyard_mm2=round(c["courtyard"], 1), courtyard_pcb_mm2=round(c["courtyard_pcb"], 1),
               placed_mm2=round(c["placed"], 1), hand_lands_mm2=round(c["hand"], 1), dnp_lands_mm2=round(c["dnp"], 1), sky_fiducials_mm2=round(c["fid"], 1),
               fixed_mm2=round(c["fixed"], 1), motor_cutout_mm2=round(cut, 1), tall_mm2=round(c["tall"], 1),
               by_height_mm2={k: round(v, 1) for k, v in c["cls"].items()}, by_height_n=c["ncls"], chip_sizes=dict(sorted(c["sizes"].items())),
               o2_mm2=round(c["o2"], 2), o2_parts=c["n_o2"],
               design_convention=m(c["courtyard"]), design_convention_pcb=m(c["courtyard_pcb"]),
               with_cad_s1=m(c["courtyard"], CAD_S1), with_cad_s1_pcb=m(c["courtyard_pcb"], CAD_S1))
    # the largest courtyard (PCB count) that passes both measures, and the board growth that would be needed with the stage-1 CAD keep-outs
    pa = row["with_cad_s1"]["placement_mm2"]
    row["room_at_0p62_v1_mm2"] = round(pa * LIMIT / V1, 1)
    row["short_by_mm2_pcb"] = round(c["courtyard_pcb"] - pa * LIMIT / V1, 1)
    need = None
    for k in range(0, 200):
        d_ = m(c["courtyard_pcb"], CAD_S1, xl=XL + 0.1 * k)
        if d_["pass_project"] and d_["pass_v1"]: need = round(XL + 0.1 * k, 1); break
    row["board_length_needed_pcb_mm"] = need
    needw = None
    for k in range(0, 200):
        d_ = m(c["courtyard_pcb"], CAD_S1, yl=YL + 0.1 * k)
        if d_["pass_project"] and d_["pass_v1"]: needw = round(YL + 0.1 * k, 1); break
    row["board_width_needed_pcb_mm"] = needw
    G1.append(row)
L0 = next(r for r in G1 if r["id"] == "L0"); S1R = next(r for r in G1 if r["id"] == "S1")

# ---------------- level 0 item by item against stage 1 ----------------
def cy_of(parts, r):
    p = parts.get(r)
    if p is None or p["side"] != "F": return None
    return p.get("courtyard_area_mm2") or 0.0
changes = []
for r in sorted(set(S1["v3f"]) | set(P["v3f"]), key=lambda r: (r.rstrip("0123456789"), int("0" + "".join(ch for ch in r if ch.isdigit())))):
    a = S1["v3f"].get(r); b = P["v3f"].get(r)
    if (a or b)["side"] != "F": continue
    ca = (a.get("courtyard_area_mm2") or 0.0) if a else 0.0; cb = (b.get("courtyard_area_mm2") or 0.0) if b else 0.0
    if a and b and a["footprint"] == b["footprint"] and a["lcsc_ref"] == b["lcsc_ref"] and abs(ca - cb) < 1e-6: continue
    kind = "fixed land" if r in FIXED_REFS else ("hand land" if r in HAND_LANDS else ("DNP land" if (b or a)["dnp"] else "placed"))
    changes.append(dict(ref=r, kind=kind, s1=(a["value"][:44] if a else "-"), s1_lcsc=(a.get("lcsc_ref") if a else None), s1_mm2=round(ca, 3),
                        l0=(b["value"][:44] if b else "removed"), l0_lcsc=(b.get("lcsc_ref") if b else None), l0_mm2=round(cb, 3), delta_mm2=round(cb - ca, 3),
                        jlc_lib=(b or {}).get("jlc_lib"), jlc_stock=(b or {}).get("jlc_stock"), jlc_orderable=(b or {}).get("jlc_orderable"), jlc_fetched=(b or {}).get("jlc_fetched")))
by_kind = {}
for x in changes: by_kind[x["kind"]] = round(by_kind.get(x["kind"], 0.0) + x["delta_mm2"], 2)

# ---------------- first-order combination with the CAD lane's options (v3/cad/out/options/options_table.json, if present) ----------------
COMBO = []
try:
    OT = json.load(open(os.path.join(V3, "cad", "out", "options", "options_table.json")))
    rows_ = OT["rows"] if isinstance(OT, dict) and "rows" in OT else OT
    for x in rows_:
        pa = x.get("placement_stage1_convention_mm2") or x.get("placement_mm2")
        if pa is None: continue
        COMBO.append(dict(cad_id=x.get("id"), tag=x.get("tag"), placement_s1_lands_mm2=pa))
except Exception as e:
    COMBO = [dict(error=f"CAD options table not readable: {e!r}")]

# ---------------- write ----------------
OUT = dict(generated_from="design/parts.json (all variants) + design_s1/parts.json (stage 1) + v3/decide/calc baseline_calc.json, v3_calc_copy.json; v2/design/parts.json",
           convention=__doc__.split("\n\n")[1], limit=LIMIT, v1_factor=round(V1, 4), panel_zone_mm2=PANEL, motor_cutout_mm2=round(CUT, 2),
           rib_posts_mm2=POSTS, antenna_keepout_mm2=KEEPOUT, cad_stage1_no_parts_mm2=CAD_S1, board_mm=[XL, YL], sanity_baseline_rebuilt=sanity,
           height_classes="body height_max_mm of parts.json (no solder): <= 0.30 (0201 resistors), <= 0.45 (0201 MLCC, X2SON, DSBGA, WLCSP, 0402 resistors, X1SON), <= 0.70 (panel zone limit), > 0.70 (tall zone)",
           gate1_rows=G1, level0_changes=dict(by_kind_mm2=by_kind, items=changes), cad_options=COMBO,
           tall_parts_built=sorted([dict(ref=r, h=p["height_max_mm"], mm2=p["courtyard_area_mm2"]) for r, p in P["v3f"].items()
                                    if p["side"] == "F" and p["jlc_placed"] and (p.get("height_max_mm") or 0) > 0.70], key=lambda x: -x["mm2"]))
json.dump(OUT, open(os.path.join(DESIGN, "area_check.json"), "w"), indent=1)

def f(x): return f"{x['utilisation']:.3f} / {x['utilisation_v1']:.3f}"
def ok(x): return ("PASS" if x["pass_project"] and x["pass_v1"] else ("project only" if x["pass_project"] else "FAIL"))
L = ["# V3-F board-area check (gate 1, levels 0 and 4)\n",
     "Generated by `tools/area_check.py` from `parts.json` (the built netlists) and `../design_s1/parts.json` (frozen stage 1). Planning metric, not a placement: "
     "V3-G1 (BASELINE 18) decides with a real placement. Courtyards are F.CrtYd boxes ✅ (parts.json); placement areas are planning values ⚠.\n",
     f"Board {XL:g} × {YL:g} mm (pod 41 × 32 mm). Convention (unchanged from stage 1, `v3/decide/calc`): placement = board − 0.5 mm edge band − antenna keep-out 15 − fixed features "
     "− motor cut-out (Ø + 0.3 mm band) − 6 rib post feet × 1.0; utilisation = courtyard / placement; v1's measure × 1.108; limit 0.62 on both. "
     f"'With CAD' subtracts the stage-1 CAD-only no-parts area {CAD_S1} mm² (FPC corridor 110.0 and six small zones, `v3/stage1/checks/cross_check.json`); the CAD lane's level-1 to level-3 options change that number. "
     "'PCB' adds the DNP lands and the two sky fiducials to the courtyard. Nothing is relaxed: both measures are shown for every row.\n",
     "## 1. Courtyard of each option (mm²)\n",
     "| Id | Option | Placed parts | Courtyard (project) | + DNP lands | + sky fiducials | Courtyard PCB | Fixed features | Motor cut-out | O-2 parts / mm² |",
     "|---|---|---|---|---|---|---|---|---|---|"]
for r in G1:
    L.append(f"| {r['id']} | {r['label']} | {r['placed_parts']} | {r['courtyard_mm2']} | {r['dnp_lands_mm2']} | {r['sky_fiducials_mm2']} | {r['courtyard_pcb_mm2']} | {r['fixed_mm2']} | {r['motor_cutout_mm2']} | {r['o2_parts']} / {r['o2_mm2']} |")
L += ["", "## 2. Courtyard per height class (placed sky-side parts, body height from parts.json, mm²; count in brackets)\n",
      "| Id | ≤ 0.30 mm | ≤ 0.45 mm | ≤ 0.70 mm | > 0.70 mm | Placed total | Hand lands J13 / J16 / J17 (0 mm) | Chip sizes placed (0201 / 0402 / 0603 / 0805 / 1206) |", "|---|---|---|---|---|---|---|---|"]
for r in G1:
    cz = r["chip_sizes"]
    L.append(f"| {r['id']} | " + " | ".join(f"{r['by_height_mm2'][k]} ({r['by_height_n'][k]})" for k, _, _ in CLASSES) + f" | {r['placed_mm2']} | {r['hand_lands_mm2']} | "
             + " / ".join(str(cz.get(k, 0)) for k in ("0201", "0402", "0603", "0805", "1206")) + " |")
L += ["", "## 3. Gate 1, first order (limit 0.62 on both measures)\n",
      "| Id | Placement, design convention | Project / v1 | Project / v1, PCB | Placement with CAD (stage 1) | Project / v1 | Project / v1, PCB | Verdict with CAD, PCB | PCB courtyard over the room at 0.62 (v1) | Board length / width that would pass (PCB, CAD stage 1) | Cost to the wearer |",
      "|---|---|---|---|---|---|---|---|---|---|---|"]
for r in G1:
    a, b, c_, d_ = r["design_convention"], r["design_convention_pcb"], r["with_cad_s1"], r["with_cad_s1_pcb"]
    L.append(f"| {r['id']} | {a['placement_mm2']} | {f(a)} | {f(b)} | {c_['placement_mm2']} | {f(c_)} | {f(d_)} | {ok(d_)} | {r['short_by_mm2_pcb']:+.1f} (room {r['room_at_0p62_v1_mm2']}) | "
             f"{r['board_length_needed_pcb_mm']} × 29 / 38 × {r['board_width_needed_pcb_mm']} | {r['wearer_cost']} |")
L += ["", f"Tall zone (parts > 0.70 mm outside the 495 mm² panel zone), level 0 with CAD: {L0['with_cad_s1']['tall_courtyard_mm2']} mm² on {L0['with_cad_s1']['tall_zone_mm2']} mm² = "
      f"{L0['with_cad_s1']['tall_zone_util']:.3f} / {L0['with_cad_s1']['tall_zone_util_v1']:.3f} (stage 1: {S1R['with_cad_s1']['tall_courtyard_mm2']} mm², {S1R['with_cad_s1']['tall_zone_util']:.3f} / {S1R['with_cad_s1']['tall_zone_util_v1']:.3f}).\n",
      "The board growth columns keep the stage-1 CAD keep-outs and the other dimension fixed; they are a measure of the remaining gap, not a proposal (levels 1 to 3 belong to the CAD lane).\n",
      f"## 4. Level 0 against stage 1, item by item: {L0['courtyard_mm2'] - S1R['courtyard_mm2']:+.1f} mm² of courtyard (project), {L0['courtyard_pcb_mm2'] - S1R['courtyard_pcb_mm2']:+.1f} mm² (PCB), "
      f"{L0['fixed_mm2'] - S1R['fixed_mm2']:+.1f} mm² of fixed features\n",
      "| Kind | Δ mm² |", "|---|---|"] + [f"| {k} | {v:+.2f} |" for k, v in by_kind.items()]
L += ["", "| Ref | Kind | Stage 1 | mm² | Level 0 | LCSC | mm² | Δ | JLC class | Stock / orderable | Queried UTC |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for x in changes:
    L.append(f"| {x['ref']} | {x['kind']} | {x['s1']} | {x['s1_mm2']} | {x['l0']} | {x['l0_lcsc'] or '-'} | {x['l0_mm2']} | {x['delta_mm2']:+.2f} | {x['jlc_lib'] or '-'} | "
             f"{x['jlc_stock'] if x['jlc_stock'] is not None else '-'} / {x['jlc_orderable'] if x['jlc_orderable'] is not None else '-'} | {x['jlc_fetched'] or '-'} |")
L += ["", "Tall parts of level 0 (> 0.70 mm): " + ", ".join(f"{x['ref']} {x['h']} mm {x['mm2']}" for x in OUT["tall_parts_built"]) + ".",
      "\nPlan sanity (BASELINE 5.3 rebuilt from `v2/design` + `v3/decide/calc`, unchanged): "
      f"{sanity['rebuilt_courtyard_mm2']} / {sanity['rebuilt_placement_mm2']} mm² against BASELINE's {sanity['baseline_calc_courtyard_mm2']} / {sanity['baseline_calc_placement_mm2']}."]
open(os.path.join(DESIGN, "area_check.md"), "w").write("\n".join(L) + "\n")
print(f"area_check: stage 1 {S1R['courtyard_mm2']} / PCB {S1R['courtyard_pcb_mm2']} mm2 -> level 0 {L0['courtyard_mm2']} / PCB {L0['courtyard_pcb_mm2']} mm2; "
      f"38x29 with CAD (stage-1 keep-outs): {f(L0['with_cad_s1'])}, PCB {f(L0['with_cad_s1_pcb'])} {ok(L0['with_cad_s1_pcb'])}")
for r in G1: print(f"   {r['id']:11s} courtyard {r['courtyard_mm2']:6.1f} PCB {r['courtyard_pcb_mm2']:6.1f} | " + " ".join(f"{k} {v}" for k, v in r["by_height_mm2"].items()) + f" | with CAD PCB {f(r['with_cad_s1_pcb'])}")
