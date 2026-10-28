"""Readable KiCad 10 schematic from the SKiDL part/net export: real library symbols, laid out per function block,
every pin tagged with a net label (same name = same net), NC flags on unused pins, PWR_FLAG on supply nets.

usage: python3 sch.py <pmbh|libb>
"""
import json, os, re, sys, uuid, math

B = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
SYMDIR = os.path.expanduser("~/Applications/KiCad/KiCad/KiCad/KiCad.app/Contents/SharedSupport/symbols")
sys.path.insert(0, HERE)
CAT = {}
exec(re.search(r"CAT = \{.*?\n\}", open(os.path.join(HERE, "hwcommon.py")).read(), re.S).group(0), {}, CAT)   # read the catalogue without SKiDL
CAT = CAT["CAT"]
parts = json.load(open(os.path.join(HERE, f"{B}_parts.json")))
U = lambda: str(uuid.uuid4())

# ---------------- s-expression helpers ----------------
def find_block(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(": depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0: return text[start:i + 1]
    raise ValueError
_libcache = {}
def lib_text(lib):
    if lib not in _libcache:
        path = os.path.join(HERE, "lib/hw.kicad_sym") if lib == "hw" else os.path.join(SYMDIR, lib + ".kicad_sym")
        _libcache[lib] = open(path).read()
    return _libcache[lib]
def get_symbol(lib, name):
    t = lib_text(lib); i = t.find(f'(symbol "{name}"')
    if i < 0: raise KeyError(f"{lib}:{name}")
    return find_block(t, i)
def children(blk):
    """Top-level child s-expressions of a block, as strings."""
    out, depth, start = [], 0, None
    for i, ch in enumerate(blk):
        if ch == "(":
            depth += 1
            if depth == 2: start = i
        elif ch == ")":
            if depth == 2: out.append(blk[start:i + 1])
            depth -= 1
    return out
def head(c): return re.match(r"\((\w+)", c).group(1)
def flatten(lib, name):
    """Return a lib_symbols entry named 'lib:name' with any (extends ...) resolved the way KiCad does it:
    the child's own properties/flags + the parent's units, graphics, pins and pin-name settings."""
    blk = get_symbol(lib, name)
    m = re.search(r'\(extends "([^"]+)"\)', blk)
    if not m:
        return blk.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)
    parent = flatten(lib, m.group(1))
    own = [c for c in children(blk) if head(c) != "extends"]
    have = {head(c) for c in own}
    inherited = []
    for c in children(parent):
        h = head(c)
        if h == "symbol":
            inherited.append(re.sub(rf'^\(symbol "{re.escape(m.group(1))}_', f'(symbol "{name}_', c))
        elif h != "property" and h not in have:
            inherited.append(c)
    return f'(symbol "{lib}:{name}" ' + " ".join(inherited[:0] + [c for c in inherited if head(c) != "symbol"] + own
                                              + [c for c in inherited if head(c) == "symbol"]) + ")"
def pins_of(flat):
    """[(number, name, x, y, angle)] from a flattened symbol (unit 1 / common units)."""
    out = []
    for m in re.finditer(r'\(pin (\w+) \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)[\s\S]*?\(name "([^"]*)"[\s\S]*?\(number "([^"]*)"', flat):
        out.append((m.group(6), m.group(5), float(m.group(2)), float(m.group(3)), int(m.group(4))))
    return out
def bbox(flat):
    xs, ys = [], []
    for x, y in re.findall(r'\((?:start|end|at|xy|center) ([-\d.]+) ([-\d.]+)', flat):
        xs.append(float(x)); ys.append(float(y))
    for _, _, x, y, _ in pins_of(flat): xs.append(x); ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else (-2.54, -2.54, 2.54, 2.54)

# ---------------- layout ----------------
BLOCKS = {
    "pmbh": [("input", "INPUT: fuse · reverse-polarity P-MOS · TVS"), ("pv_sense", "PANEL CURRENT (low side, auto-ranged)"),
             ("charger", "CN3791 MPPT CHARGER  V_MPPT = 6.40 V, I_CH = 1.2 A"), ("battery", "BATTERY · NTC"),
             ("load", "LOAD SWITCH → CHEST CABLE J6"), ("power", "3.3 V RAIL"), ("meter", "INA226 × 6  (I2C 0x40–0x45)"),
             ("mcu", "MCU: XIAO nRF52840 Sense (plug-in)"), ("test", "TEST POINTS"), ("mech", "MECHANICAL")],
    "libb": [("input", "INPUT FROM BACK UNIT"), ("oring", "IDEAL-DIODE OR-ING (LM66100 §9.2.3)"), ("holdup", "SUPERCAP HOLD-UP 2×10 F"),
             ("output", "OUTPUTS: BITalino battery · SYNC → I1"), ("test", "TEST POINTS"), ("mech", "MECHANICAL")],
}[B]
GRID = 2.54
def snap(v): return round(v / GRID) * GRID
SHEET = (420.0, 297.0) if B == "pmbh" else (297.0, 210.0)
cols = 4 if B == "pmbh" else 3
region_w = (SHEET[0] - 30) / cols
symbols_used, instances, labels, ncs, texts, flags = {}, [], [], [], [], []
def label_len(name): return 1.27 * 0.9 * len(name) + 2.54

cursor = {}
blocks_parts = {b: [r for r, p in parts.items() if p["block"] == b] for b, _ in BLOCKS}
# region heights proportional to content
rows_y = 25.0; col = 0; row_h = 0.0; region_x = 15.0
pos = {}
for bname, title in BLOCKS:
    refs = sorted(blocks_parts.get(bname, []), key=lambda r: (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r) or 0)))
    if not refs: continue
    # place the block's parts in a sub-grid
    x0, y0 = region_x, rows_y + 8
    x, y, line_h, block_h = x0, y0, 0.0, 0.0
    for ref in refs:
        p = parts[ref]; lib, sym = CAT[p["catkey"]][0], CAT[p["catkey"]][1]
        flat = flatten(lib, sym); symbols_used[f"{lib}:{sym}"] = flat
        bx0, by0, bx1, by1 = bbox(flat)
        maxlab = max([label_len(n) for n in p["pins"].values() if n] + [0])
        w = (bx1 - bx0) + 2 * maxlab + 5; h = (by1 - by0) + 10
        if x + w > region_x + region_w - 5 and x > x0:
            x = x0; y += line_h; line_h = 0
        cx = snap(x + maxlab + (-bx0)); cy = snap(y + by1 + 4)
        pos[ref] = (cx, cy, lib, sym, flat)
        x += w; line_h = max(line_h, h); block_h = max(block_h, y + line_h - y0)
    texts.append((title, region_x, rows_y + 3))
    row_h = max(row_h, block_h + 14)
    col += 1; region_x += region_w
    if col == cols: col = 0; region_x = 15.0; rows_y += row_h; row_h = 0.0

ROOT = U()
def prop(name, val, x, y, hide=False):
    return f'(property "{name}" {json.dumps(val)} (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)){" (hide yes)" if hide else ""}))'
supply = {"pmbh": ["GND", "VPV", "VSYS"], "libb": ["GND", "VLOAD"]}[B]
for ref, (cx, cy, lib, sym, flat) in pos.items():
    p = parts[ref]; bx0, by0, bx1, by1 = bbox(flat)
    pin_list = pins_of(flat)
    pin_entries = " ".join(f'(pin "{num}" (uuid "{U()}"))' for num, *_ in pin_list)
    props = [prop("Reference", ref, cx, cy - by1 - 1.5), prop("Value", p["value"], cx, cy - by0 + 1.5),
             prop("Footprint", p["footprint"], cx, cy, True), prop("Datasheet", "", cx, cy, True)]
    if p.get("lcsc"): props.append(prop("LCSC", p["lcsc"], cx, cy, True))
    if p.get("jlc") == "user": props.append(prop("Assembly", "user-installed (not JLC)", cx, cy, True))
    onboard = "no" if not p["footprint"] else "yes"
    instances.append(f'''  (symbol (lib_id "{lib}:{sym}") (at {cx:.2f} {cy:.2f} 0) (unit 1) (exclude_from_sim no) (in_bom {"no" if p.get("jlc") in (None,) and p["catkey"] in ("TP", "NETTIE", "HOLE") else "yes"}) (on_board {onboard}) (dnp no)
    (uuid "{U()}")
    {chr(10).join("    " + s for s in props)}
    {pin_entries}
    (instances (project "{B}" (path "/{ROOT}" (reference "{ref}") (unit 1)))))''')
    for num, name, px, py, ang in pin_list:
        X, Y = cx + px, cy - py
        net = p["pins"].get(num)
        if net is None or net.startswith("__NOCONNECT"):
            ncs.append((X, Y)); continue
        lab_ang = {0: 180, 180: 0, 90: 270, 270: 90}[ang]
        labels.append((net, X, Y, lab_ang))
# PWR_FLAGs on supply nets
pf = flatten("power", "PWR_FLAG"); symbols_used["power:PWR_FLAG"] = pf
fx, fy = SHEET[0] - 80, SHEET[1] - 55
for i, net in enumerate(supply):
    x, y = snap(fx + 22 * i), snap(fy)
    instances.append(f'''  (symbol (lib_id "power:PWR_FLAG") (at {x:.2f} {y:.2f} 0) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
    (uuid "{U()}")
    {prop("Reference", f"#FLG0{i+1}", x, y + 3, True)}
    {prop("Value", "PWR_FLAG", x, y - 3)}
    {prop("Footprint", "", x, y, True)}
    {prop("Datasheet", "", x, y, True)}
    (pin "1" (uuid "{U()}"))
    (instances (project "{B}" (path "/{ROOT}" (reference "#FLG0{i+1}") (unit 1)))))''')
    labels.append((net, x, y, 270))
texts.append(("PWR_FLAG: supplies sourced by connectors / battery", fx - 5, fy - 12))

def lab(net, x, y, ang):
    just = {0: "left bottom", 180: "right bottom", 90: "left bottom", 270: "right bottom"}[ang]
    return f'  (label {json.dumps(net)} (at {x:.2f} {y:.2f} {ang}) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {just})) (uuid "{U()}"))'
title = {"pmbh": "PMB-H back power & measurement board", "libb": "LIB chest interface board"}[B]
out = f'''(kicad_sch (version 20250114) (generator "eeschema") (generator_version "10.0")
  (uuid "{ROOT}")
  (paper "User" {SHEET[0]} {SHEET[1]})
  (title_block (title "{title}") (date "2026-10-11") (rev "A") (company "solar-harvesting wearable ECG")
    (comment 1 "Generated from SKiDL source ({B}.py) — edit the Python, not this file") (comment 2 "Every placed part carries an LCSC number for JLCPCB assembly"))
  (lib_symbols
{chr(10).join("    " + s for s in symbols_used.values())}
  )
{chr(10).join(lab(*l) for l in labels)}
{chr(10).join(f'  (no_connect (at {x:.2f} {y:.2f}) (uuid "{U()}"))' for x, y in ncs)}
{chr(10).join(f'  (text {json.dumps(t)} (exclude_from_sim no) (at {x:.2f} {y:.2f} 0) (effects (font (size 2.2 2.2) (thickness 0.35) bold) (justify left bottom)) (uuid "{U()}"))' for t, x, y in texts)}
{chr(10).join(instances)}
  (sheet_instances (path "/" (page "1")))
)
'''
os.makedirs(os.path.join(HERE, "out", B), exist_ok=True)
open(os.path.join(HERE, "out", B, f"{B}.kicad_sch"), "w").write(out)
print("written", len(pos), "symbols,", len(labels), "labels,", len(ncs), "NC")
