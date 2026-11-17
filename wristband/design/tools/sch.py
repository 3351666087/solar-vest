"""Readable KiCad 10 hierarchical schematic from the SKiDL part export (out/<board>/parts.json), in the spirit of
the vest's tools/cad/sch.py: one sheet per SKiDL block, symbols generated from the datasheet pin maps (pin names
exactly as in pinmap/<C>.yaml), every connected pin tagged with a global label (same name = same net), no-connect
flags on unconnected pins, PWR_FLAGs only on the supply nets listed (with reasons) in FLAGS.

usage: python sch.py <variant>      (variant folder under out/: v3f | v3f_fldnp)
"""
import json, os, re, sys, uuid, math
VTAG = sys.argv[1]                      # variant folder under out/: v3f | v3f_fldnp
BOARD = "main"
DESIGN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(DESIGN, "out", VTAG); KDIR = os.path.join(DESIGN, "kicad", VTAG); os.makedirs(KDIR, exist_ok=True)
parts = json.load(open(os.path.join(OUT, "parts.json")))
U = lambda: str(uuid.uuid4())
G = 2.54
def snap(v): return round(v / G) * G
PROJECT = "solarband_v3f" + VTAG[3:]    # v3f | v3f_fldnp
WLCSP = True

BLOCKS = [
 ("power", "POWER: BQ25570 harvester + 1.859 V buck, MOhm dividers, PV chain TVS / RSH1 / Q1 PV_INH, R_LIM R130 12 Ohm 0805 (after the O-2 switch), "
           "INA236 x2 on a gated rail, EN self-hold (ship mode) + power-cycle one-shot with VDD discharge, VSTOR switch, LED supply R117, AVDD_ECG LDO (EN via R123 / Q9)"),
 ("charger", "CHARGER: top-rim contacts J15 / J18, D13 ESD761, D14 reverse block, BQ25170 4.10 V / 30 mA, ISET RC, VB_DET -> Q8 PV short / Q9 ECG off, Q10 CHG_DIS, D12 BAV70M ship wake (VBUS, button)"),
 ("o2", "O-2: hardware PV-charge inhibit (pack NTC 0-45 C, MCU off, any cell state): Q14 series switch, Q16 heartbeat override, Q17 approval, Q18 supply gate, U19 / U20 TLV7031 window, ladder; NTC AIN"),
 ("hmi", "HMI: display TPS7A0230 3.0 V + TXU0104 + TXU0101 + ZIF J13 (FH34SRJ, top contact); front light Q11 / R160 / J16; ERM Q12 / D17 / J17; side button SW1 + Q13"),
 ("mcu_rf", "MCU_RF: nRF52832-CIAA WLCSP-50, Nordic CIAA DC/DC reference (PS v1.4 Fig.173), crystals, RF match, pi-net, printed-radiator feed; GPIO map of BASELINE 6"),
 ("ecg", "ECG: ADS1291, electrode networks (TVS + 2 x 330k), dot-loop links, C_CM/C_DIFF (SIM-07), RLD"),
 ("ppg", "PPG: MAX86141 + 2 x CT DBLP31.12 + VEMD8080 (data sheet typical application); LEDs and photodiode on the skin face"),
 ("sensors_storage", "SENSORS & STORAGE: LIS2DW12 (0x19), TMP117 (0x48), MX25R1635F, I2C pull-ups, skin-hot warning LED D10"),
 ("io", "IO: plate-dot pads, E3 spring finger, strap entry lands root A (BATT_P, GND, NTC, GND) / root B (PV_W+, GND) with links FB1-FB6, lid tail, G10 pogo array, SWD group, EOL-1 pads, fiducials"),
]
# Supply nets that are sourced by something outside the schematic (pack, PV lid / wing, head) or only through passive parts.
FLAGS = {"GND": "system ground: PV- (lid tail), pack - and wing - through FB2 / FB4 / FB6, contact - (J18)",
         "VIN_DC": "harvester input: sourced by the PV through RSH1, Q14 and R_LIM; no IC pin drives it",
         "VLED": "LED supply: fed from VSTOR_SW (U12 OUT) through R117 3.3 Ohm, i.e. only through a passive part",
         "BATT_P": "protected pack + (strap root A, pad J3 through FB1)",
         "VBUS": "head supply through the contacts (J15) and D14; no IC pin drives it",
         "V_O2": "O-2 supply: from PV_SW through Q18 and D19 or from NTC_EN through D19; no power-out pin",
         "O2_NC": "U20 supply = U19 output (chained AND of the O-2 window)",
         "PV_SW": "PV node after RSH1 (lid and wing); only passive parts and switches",
         "DISP_EN": "display power domain: GPIO P0.19 supplies VCCA of U17 / U21 (<= 2.5 uA each) and enables U16"}

# ---------------- symbols ----------------
def pin_sexpr(num, name, typ, x, y, ang, length=2.54, hide_name=False):
    nm = name if name else "~"
    return (f'(pin {typ} line (at {x:.2f} {y:.2f} {ang}) (length {length}) '
            f'(name {json.dumps(nm)} (effects (font (size 1.016 1.016)){" (hide yes)" if hide_name else ""})) '
            f'(number {json.dumps(num)} (effects (font (size 1.016 1.016)))))')
TYPEMAP = {"PASSIVE": "passive", "INPUT": "input", "OUTPUT": "output", "BIDIR": "bidirectional", "TRISTATE": "tri_state",
           "PWRIN": "power_in", "PWROUT": "power_out", "OPENCOLL": "open_collector", "NOCONNECT": "no_connect", "OPENEMIT": "open_emitter"}
def ktype(t): return TYPEMAP.get(t, "passive")

def make_symbol(key, p):
    """Return (lib_symbol_sexpr, [(num, x, y, ang)]) in symbol coordinates (y up)."""
    name = key; pins = sorted(p["pinnames"].items(), key=lambda kv: (len(kv[0]), kv[0]))
    kind = p["kind"]
    body, plist = [], []
    if kind in ("R", "C", "L", "nettie") or (len(pins) == 2 and kind not in ("pinmap",)):
        # horizontal 2-terminal: pin 1 left, pin 2 right
        if kind == "R": body.append('(rectangle (start -1.524 0.762) (end 1.524 -0.762) (stroke (width 0.254) (type default)) (fill (type none)))')
        elif kind == "C": body += ['(polyline (pts (xy -0.508 1.524) (xy -0.508 -1.524)) (stroke (width 0.3) (type default)) (fill (type none)))',
                                   '(polyline (pts (xy 0.508 1.524) (xy 0.508 -1.524)) (stroke (width 0.3) (type default)) (fill (type none)))']
        elif kind == "L": body += [f'(arc (start {-1.524 + i * 0.762:.3f} 0) (mid {-1.143 + i * 0.762:.3f} 0.381) (end {-0.762 + i * 0.762:.3f} 0) (stroke (width 0.254) (type default)) (fill (type none)))' for i in range(4)]
        else: body.append('(polyline (pts (xy -1.27 0) (xy 1.27 0)) (stroke (width 0.5) (type default)) (fill (type none)))')
        typ = [ktype(p["pintypes"][n]) for n, _ in pins]
        plist = [(pins[0][0], -3.81, 0, 0, pins[0][1], typ[0]), (pins[1][0], 3.81, 0, 180, pins[1][1], typ[1])]
        hide = kind != "pvcell"          # PV cells show their '+' / '-' pin names
    elif len(pins) == 1:
        body.append('(circle (center 0 0) (radius 0.762) (stroke (width 0.254) (type default)) (fill (type none)))')
        plist = [(pins[0][0], -3.81, 0, 0, pins[0][1], ktype(p["pintypes"][pins[0][0]]))]; hide = True
    elif len(pins) == 0:
        body.append('(circle (center 0 0) (radius 1.27) (stroke (width 0.254) (type default)) (fill (type none)))'); hide = True
    else:
        left_types = {"PWRIN", "INPUT"}
        L = [(n, nm) for n, nm in pins if p["pintypes"][n] in left_types]
        R = [(n, nm) for n, nm in pins if p["pintypes"][n] not in left_types]
        if abs(len(L) - len(R)) > 6:   # rebalance very lopsided parts
            allp = pins; half = (len(allp) + 1) // 2; L, R = allp[:half], allp[half:]
        rows = max(len(L), len(R)); h = (rows + 1) * G
        maxlen = max([len(nm) for _, nm in pins] + [4])
        w = snap(max(10.16, maxlen * 1.016 * 2 * 0.62 + 5.08)) + (G if snap(max(10.16, maxlen * 1.27 + 5.08)) / G % 2 else 0)
        w = max(w, 10.16)
        top = snap(h / 2)
        body.append(f'(rectangle (start {-w/2:.2f} {top:.2f}) (end {w/2:.2f} {top - h:.2f}) (stroke (width 0.254) (type default)) (fill (type background)))')
        for i, (n, nm) in enumerate(L):
            plist.append((n, -w / 2 - 2.54, top - G * (i + 1), 0, nm, ktype(p["pintypes"][n])))
        for i, (n, nm) in enumerate(R):
            plist.append((n, w / 2 + 2.54, top - G * (i + 1), 180, nm, ktype(p["pintypes"][n])))
        hide = False
    prefix = re.match(r"[A-Za-z]+", p["ref"]).group(0)
    xs = [x for _, x, _, _, _, _ in plist] + [0]; ys = [y for _, _, y, _, _, _ in plist] + [0]
    s = (f'(symbol "solarband:{name}" (pin_names (offset 0.508){" (hide yes)" if hide else ""}) (exclude_from_sim no) (in_bom yes) (on_board yes)\n'
         f'      (property "Reference" "{prefix}" (at 0 {max(ys) + 2.54:.2f} 0) (effects (font (size 1.27 1.27))))\n'
         f'      (property "Value" "{name}" (at 0 {min(ys) - 2.54:.2f} 0) (effects (font (size 1.27 1.27))))\n'
         f'      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
         f'      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
         f'      (symbol "{name}_0_1" {" ".join(body)})\n'
         f'      (symbol "{name}_1_1" {" ".join(pin_sexpr(n, nm, t, x, y, a) for n, x, y, a, nm, t in plist)}))')
    bb = (min(xs) - 1, min(ys) - 3, max(xs) + 1, max(ys) + 3)
    return s, [(n, x, y, a) for n, x, y, a, _, _ in plist], bb

symcache = {}
for ref, p in parts.items():
    p["ref"] = ref
    key = p["catkey"]
    if key not in symcache: symcache[key] = make_symbol(key, p)

def _kicad_power_flag():
    """PWR_FLAG copied verbatim from KiCad's own power library (avoids ERC lib_symbol_mismatch)."""
    t = open(os.path.expanduser("~/Applications/KiCad/KiCad/KiCad/KiCad.app/Contents/SharedSupport/symbols/power.kicad_sym")).read()
    i = t.find('(symbol "PWR_FLAG"'); d = 0
    for j in range(i, len(t)):
        if t[j] == "(": d += 1
        elif t[j] == ")":
            d -= 1
            if d == 0: break
    return t[i:j + 1].replace('(symbol "PWR_FLAG"', '(symbol "power:PWR_FLAG"', 1)
PWR_FLAG = _kicad_power_flag()

def prop(name, val, x, y, hide=False, size=1.27):
    return f'(property {json.dumps(name)} {json.dumps(str(val))} (at {x:.2f} {y:.2f} 0) (effects (font (size {size} {size})){" (hide yes)" if hide else ""}))'
def glabel(net, x, y, ang):
    just = "right" if ang == 180 else "left"
    if ang in (90, 270): just = "left" if ang == 90 else "right"
    return (f'  (global_label {json.dumps(net)} (shape passive) (at {x:.2f} {y:.2f} {ang}) (fields_autoplaced yes) '
            f'(effects (font (size 1.016 1.016)) (justify {just})) (uuid "{U()}") '
            f'{prop("Intersheetrefs", "${INTERSHEET_REFS}", x, y, True, 1.016)})')
def textn(t, x, y, size=2.0, bold=True):
    return (f'  (text {json.dumps(t)} (exclude_from_sim no) (at {x:.2f} {y:.2f} 0) (effects (font (size {size} {size}) '
            f'(thickness {size*0.15:.2f}){" bold" if bold else ""}) (justify left bottom)) (uuid "{U()}"))')

ROOT = U()
sheet_uuid = {b: U() for b, _ in BLOCKS}
def label_len(net): return 1.016 * 0.75 * len(net) + 3.5

def build_sheet(block, title, page):
    refs = [r for r, p in parts.items() if p["block"] == block]
    refs.sort(key=lambda r: ({"U": 0, "Q": 1, "D": 2, "X": 3, "PD": 2}.get(re.match(r"[A-Z]+", r).group(0), 5), re.match(r"[A-Z]+", r).group(0), int(re.sub(r"\D", "", r) or 0)))
    # ---- grouping: every IC/discrete heads a column; each passive joins the head it shares the most signal nets with ----
    COMMON = {"GND", "VDD_1V8", "GND_PMIC", "VSTOR", "AVDD_ECG", "VLED"}
    pfx = lambda r: re.match(r"[A-Z]+", r).group(0)
    heads = [r for r in refs if pfx(r) in ("U", "Q", "D", "X", "PD", "AE", "SC") or parts[r]["kind"] in ("testarray", "swd6", "lidtail")]
    if not heads: heads = refs[:1]
    groups = {h: [] for h in heads}
    def nets_of(r): return {v for v in parts[r]["pins"].values() if v}
    for r in refs:
        if r in groups: continue
        hint = [h for h in re.findall(r"\b([A-Z]{1,2}\d+)\b", parts[r].get("func", "")) if h in groups]
        if hint: groups[hint[0]].append(r); continue
        sig = nets_of(r) - COMMON
        best, score = None, 0
        for h in heads:
            sc = len(sig & nets_of(h)) * 2 + len((nets_of(r) & nets_of(h)) & COMMON) * 0
            if sc > score: best, score = h, sc
        if best is None:   # attach by any shared net, else to the first head
            best = max(heads, key=lambda h: len(nets_of(r) & nets_of(h)))
        groups[best].append(r)
    def size(r):
        p = parts[r]; s_, pl, (bx0, by0, bx1, by1) = symcache[p["catkey"]]
        labL = max([label_len(p["pins"][n] or "") for n, x_, y_, a_ in pl if a_ == 0] + [0])
        labR = max([label_len(p["pins"][n] or "") for n, x_, y_, a_ in pl if a_ == 180] + [0])
        val = 1.27 * 0.62 * len(str(p["value"])) + 2
        w = max((bx1 - bx0) + labL + labR + 4, val)
        h = (by1 - by0) + (8.0 if len(pl) <= 2 else 9)
        return w, h, labL, bx0, by1
    for paper, (PW, PH) in (("A3", (420, 297)), ("A2", (594, 420)), ("A1", (841, 594)), ("A0", (1189, 841))):
        x0, y0, xmax, ymax = 15.0, 34.0, PW - 15.0, PH - 45.0
        pos, x, band_y, band_h, ok = {}, x0, y0, 0.0, True
        for h in heads:
            members = [h] + groups[h]
            cols, col, colh = [], [], 0.0
            for r in members:
                w_, hh, *_ = size(r)
                if col and band_y + colh + hh > ymax and r != h:
                    cols.append(col); col, colh = [], 0.0
                col.append(r); colh += hh
            cols.append(col)
            gw = sum(max(size(r)[0] for r in c) + 4 for c in cols)
            if x + gw > xmax and x > x0:
                x = x0; band_y += band_h + 6; band_h = 0.0
            for c in cols:
                cw = max(size(r)[0] for r in c); yy = band_y
                for r in c:
                    w_, hh, labL, bx0, by1 = size(r)
                    pos[r] = (snap(x + labL - bx0 + 2), snap(yy + by1 + 3)); yy += hh
                band_h = max(band_h, yy - band_y); x += cw + 4
        if band_y + band_h <= ymax + 10: break
    items, syms = [], {}
    labels = ncs = 0
    for r in refs:
        p = parts[r]; key = p["catkey"]; s, pl, (bx0, by0, bx1, by1) = symcache[key]; syms[key] = s
        cx, cy = pos[r]
        props = [prop("Reference", r, cx, cy - by1 - 1.0), prop("Value", p["value"], cx, cy - by0 + 1.0),
                 prop("Footprint", p["footprint"], cx, cy, True), prop("Datasheet", "", cx, cy, True)]
        if p.get("lcsc"): props.append(prop("LCSC", p["lcsc"], cx, cy, True))
        if p.get("mpn"): props.append(prop("MPN", p["mpn"], cx, cy, True))
        if p.get("func"): props.append(prop("Function", p["func"], cx, cy, True))
        if p.get("jlc_lib"): props.append(prop("JLC_Library", p["jlc_lib"], cx, cy, True))
        copper_only = p["kind"] in ("pad1", "testarray", "fid", "nettie", "antenna", "lidtail", "swd6")
        in_bom = "no" if (copper_only or p.get("dnp")) else "yes"
        pin_entries = " ".join(f'(pin "{n}" (uuid "{U()}"))' for n, *_ in pl)
        items.append(f'  (symbol (lib_id "solarband:{key}") (at {cx:.2f} {cy:.2f} 0) (unit 1) (exclude_from_sim no) (in_bom {in_bom}) (on_board yes) (dnp {"yes" if p.get("dnp") else "no"})\n'
                     f'    (uuid "{U()}")\n    ' + "\n    ".join(props) + f'\n    {pin_entries}\n'
                     f'    (instances (project "{PROJECT}" (path "/{ROOT}/{sheet_uuid[block]}" (reference "{r}") (unit 1)))))')
        for n, px, py, ang in pl:
            X, Y = cx + px, cy - py
            net = p["pins"].get(n)
            if net is None or net.startswith("__") or net.startswith("NC"):
                items.append(f'  (no_connect (at {X:.2f} {Y:.2f}) (uuid "{U()}"))'); ncs += 1; continue
            items.append(glabel(net, X, Y, {0: 180, 180: 0, 90: 270, 270: 90}[ang])); labels += 1
    items.append(textn(title, 15, 22, 2.5))
    items.append(textn(f"V3-F variant {VTAG}. Generated from v3/design/src/main_board.py ({block}) by tools/sch.py - edit the Python, not this file. Pin names = datasheet (pinmap/<C>.yaml); footprints = EasyEDA footprint of the part's LCSC number (reviewed copy).", 15, 27, 1.4, False))
    lib = "\n    ".join(syms.values())
    s = (f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "10.0")\n  (uuid "{U()}")\n  (paper "{paper}")\n'
         f'  (title_block (title "SolarBand V3-F main board - {block}") (date "2026-11-13") (rev "V3-F {VTAG}") (company "SolarBand (sibling of SolarVest)") (comment 1 "Not ordered. Schematic V3-F per v3/decide/BASELINE.md; variant {VTAG}"))\n'
         f'  (lib_symbols\n    {lib}\n  )\n' + "\n".join(items) + "\n)\n")
    open(os.path.join(KDIR, f"{block}.kicad_sch"), "w").write(s)
    return dict(paper=paper, symbols=len(refs), labels=labels, nc=ncs)

stats = {}
for i, (b, t) in enumerate(BLOCKS):
    stats[b] = build_sheet(b, t, i + 2)
# ---------------- root sheet ----------------
items = []; x, y = 20.0, 40.0
for i, (b, t) in enumerate(BLOCKS):
    sx, sy = 20 + (i % 3) * 130, 45 + (i // 3) * 55
    items.append(f'  (sheet (at {sx:.2f} {sy:.2f}) (size 110 35) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced yes)\n'
                 f'    (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) (uuid "{sheet_uuid[b]}")\n'
                 f'    {prop("Sheetname", b, sx, sy - 0.7)}\n    {prop("Sheetfile", b + ".kicad_sch", sx, sy + 35.6)}\n'
                 f'    (instances (project "{PROJECT}" (path "/{ROOT}" (page "{i + 2}")))))')
    items.append(textn(t[:110], sx + 2, sy + 10, 1.2, False))
fy = 170.18
items.append(textn("PWR_FLAG on supply nets sourced outside the schematic:", 20, fy - 6, 1.6))
lib = [PWR_FLAG]
for i, (net, why) in enumerate(FLAGS.items()):
    if net not in {v for q in parts.values() for v in q['pins'].values() if v}: continue
    fx = 30.48; fyy = fy + i * 12.7
    items.append(f'  (symbol (lib_id "power:PWR_FLAG") (at {fx:.2f} {fyy:.2f} 0) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n'
                 f'    (uuid "{U()}")\n    {prop("Reference", f"#FLG0{i+1}", fx, fyy + 3, True)}\n    {prop("Value", "PWR_FLAG", fx, fyy - 4)}\n'
                 f'    {prop("Footprint", "", fx, fyy, True)}\n    {prop("Datasheet", "~", fx, fyy, True)}\n    (pin "1" (uuid "{U()}"))\n'
                 f'    (instances (project "{PROJECT}" (path "/{ROOT}" (reference "#FLG0{i+1}") (unit 1)))))')
    items.append(glabel(net, fx, fyy, 0))
    items.append(textn(f"{net}: {why}", fx + 30, fyy + 0.5, 1.2, False))
root = (f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "10.0")\n  (uuid "{ROOT}")\n  (paper "A3")\n'
        f'  (title_block (title "SolarBand V3-F main board") (date "2026-11-13") (rev "V3-F {VTAG}") (company "SolarBand (sibling of SolarVest)")'
        f' (comment 1 "Generated by design/tools/sch.py from the SKiDL source - not ordered") (comment 2 "Every JLC-placed part carries its LCSC number; footprints are EasyEDA-derived"))\n'
        f'  (lib_symbols\n    {chr(10).join(lib)}\n  )\n' + "\n".join(items) +
        f'\n  (sheet_instances (path "/" (page "1")))\n)\n')
open(os.path.join(KDIR, f"{PROJECT}.kicad_sch"), "w").write(root)
# minimal project file + footprint library table (layout will use them)
json.dump({"meta": {"filename": f"{PROJECT}.kicad_pro", "version": 3}, "schematic": {"drawing": {}}, "sheets": [[ROOT, "Root"]] + [[sheet_uuid[b], b] for b, _ in BLOCKS]},
          open(os.path.join(KDIR, f"{PROJECT}.kicad_pro"), "w"), indent=2)
open(os.path.join(KDIR, "solarband.kicad_sym"), "w").write(
    '(kicad_symbol_lib (version 20241209) (generator "solarband_sch") (generator_version "10.0")\n  '
    + "\n  ".join(v[0].replace('(symbol "solarband:', '(symbol "', 1) for v in symcache.values()) + "\n)\n")
open(os.path.join(KDIR, "sym-lib-table"), "w").write(
    '(sym_lib_table\n  (version 7)\n  (lib (name "solarband") (type "KiCad") (uri "${KIPRJMOD}/solarband.kicad_sym") (options "") (descr "generated by design/tools/sch.py from pinmap/*.yaml"))\n)\n')
open(os.path.join(KDIR, "fp-lib-table"), "w").write(
    '(fp_lib_table\n  (version 7)\n'
    '  (lib (name "easyeda") (type "KiCad") (uri "${KIPRJMOD}/../../lib/easyeda.pretty") (options "") (descr "EasyEDA-derived footprints, one per LCSC C-number (raw easyeda2kicad conversion, cplgate G4 reference)"))\n'
    '  (lib (name "easyeda_rev") (type "KiCad") (uri "${KIPRJMOD}/../../lib/easyeda_rev.pretty") (options "") (descr "reviewed copy used by the board: same copper, fixed paste/courtyard/holes/fields (tools/review_footprints.py)"))\n'
    '  (lib (name "solarband") (type "KiCad") (uri "${KIPRJMOD}/../../lib/solarband.pretty") (options "") (descr "copper-only pads, net ties, fiducials, printed-radiator placeholder"))\n)\n')
print(json.dumps(stats))
