"""Shared SKiDL helpers for the SolarBand boards (V3-F main board, v3/design; copied from v2/design and adapted).

* Part templates are built from the datasheet pin maps (pinmap/<C>.yaml): pin numbers and names exactly as in the
  datasheet; footprints are the EasyEDA footprint of the part's own LCSC number (lib/easyeda_index.json).
* mk() instantiates a part with LCSC / MPN / function fields; pin() looks a pin up by exact number or exact
  datasheet name (never by regex), so a typo fails loudly instead of matching the wrong pin.
* export_parts() writes parts.json, the single hand-off to the schematic generator, BOM, netclasses and layout.
"""
import json, os, re, sys, yaml
from skidl import Part, Pin, Net, SKIDL, TEMPLATE, ERC, generate_netlist, set_default_tool, KICAD9
import skidl

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(DESIGN))          # .../wristband (v2/design is two levels below it)
JLC_CACHES = [os.path.join(DESIGN, "data", "jlc"), os.path.join(ROOT, "cache", "v2", "jlc"), os.path.join(ROOT, "cache", "jlc")]   # V3-F answers of today first (tools/jlc_query.py), older caches read-only

# ---------------- build variants (V3-F, v3/decide/BASELINE.md; the outline is a layout matter, not a schematic variant) ----------------
#   SB_FL    = fit | dnp | none   front-light driver: fitted (baseline) | DNP research build (Q11, R160, R161 not placed, lands kept) |
#                                 [G1 level 4] none = driver and the J16 tail land removed from the board (P0.10 not connected)
#   SB_LED   = fit | none         [G1 level 4] skin-hot LED chain D10 / R507 / Q6 / R508: fitted (baseline; only the supervisor releases it) | removed
#   SB_MOTOR = erm8 | erm7 | erm6 | none   [G1 level 4] vibration motor: Vybronics VCLP0820B004L dia 8 x 2.1 mm in an 8.6 mm cut-out (baseline) |
#                                 VC0720B088L dia 7 x 2.1 mm (7.6 mm cut-out) | VC0625B001L dia 6 x 2.5 mm (6.6 mm cut-out; 0.4 mm taller) | motor block removed
#   SB_O2    = std | merged | pack   O-2 inhibit: the stage-1 circuit with R174 in 0201 (baseline, 16 parts) | [G1 level 0 option] one gate FET
#                                 (15 parts, R146 10 k; two open points, calc/o2_dense.py) | no O-2 on the board (cut-off in the pack PCM: only with a
#                                 pack RFQ answer, BASELINE 5.3 reserve 3)
# The V2-B switches are fixed for V3-F: RADIO = wlcsp (nRF52832-CIAA), ANT = board (printed-radiator feed, gate 3a), PASSIVES = 0201 for the generic
# passives, INA = ybj (DSBGA). [G1 level 0, v3/g1/dense/DENSE.md] R_LIM = 12 Ohm 0805 (C17445); every passive at the smallest case its rating allows.
VARIANT = dict(FL=os.environ.get("SB_FL", "fit"), LED=os.environ.get("SB_LED", "fit"), MOTOR=os.environ.get("SB_MOTOR", "erm8"),
               O2=os.environ.get("SB_O2", "std"), RADIO="wlcsp", ANT="board", PASSIVES="0201", INA="ybj", RLIM="12")
assert VARIANT["FL"] in ("fit", "dnp", "none") and VARIANT["LED"] in ("fit", "none"), VARIANT
assert VARIANT["MOTOR"] in ("erm8", "erm7", "erm6", "none") and VARIANT["O2"] in ("std", "merged", "pack"), VARIANT
VTAG = ("v3f" + {"fit": "", "dnp": "_fldnp", "none": "_nofl"}[VARIANT["FL"]] + ("" if VARIANT["LED"] == "fit" else "_noled")
        + {"erm8": "", "erm7": "_erm7", "erm6": "_erm6", "none": "_nomotor"}[VARIANT["MOTOR"]] + {"std": "", "merged": "_o2m", "pack": "_o2pack"}[VARIANT["O2"]])
FL_DNP = VARIANT["FL"] == "dnp"; FL_NONE = VARIANT["FL"] == "none"; LED_NONE = VARIANT["LED"] == "none"; MOTOR_NONE = VARIANT["MOTOR"] == "none"
O2 = VARIANT["O2"]
# motor data for the BOM and the area check: part, body diameter, thickness, board cut-out diameter (body + 0.6 mm), current, vibration; sources in DENSE.md section 6
MOTORS = {"erm8": dict(part="Vybronics VCLP0820B004L", dia_mm=8.0, thick_mm=2.1, cutout_mm=8.6, i_max_mA=35, grms=0.25),
          "erm7": dict(part="Vybronics VC0720B088L", dia_mm=7.0, thick_mm=2.1, cutout_mm=7.6, i_max_mA=85, grms=0.10),
          "erm6": dict(part="Vybronics VC0625B001L", dia_mm=6.0, thick_mm=2.5, cutout_mm=6.6, i_max_mA=100, grms=0.30),
          "none": dict(part="none", dia_mm=0.0, thick_mm=0.0, cutout_mm=0.0, i_max_mA=0, grms=0.0)}
MOTOR = MOTORS[VARIANT["MOTOR"]]
# nets that do not exist in a variant (their MCU ports are left unconnected, mcu_rf.py; main_board.py skips them in the 2-pin check)
ABSENT_NETS = set()
if FL_NONE: ABSENT_NETS |= {"FL_EN", "FL_A", "FL_K"}
if LED_NONE: ABSENT_NETS |= {"ALERT_LED", "ALERT_A", "ALERT_K"}
if MOTOR_NONE: ABSENT_NETS |= {"MOTOR_PWM", "MOTOR_G", "MOTOR_N", "MOTOR_S"}
if O2 == "pack": ABSENT_NETS |= {"O2_G", "O2_OK", "O2_NC", "O2_PV", "V_O2", "O2_TC", "O2_TH", "O2_HB", "PV_Q"}
# 0201 set: the v2 p0201 references plus the new V3-F generic passives, which are entered directly with their 0201 keys in the block files.
# [G1 level 0] R108 / R131 (10 MOhm) are 0201 now as well: leakage across a pull-down only strengthens it (DENSE.md section 2).
P0201_KEYS = {"R1M": "R1M_0201", "R100k": "R100k_0201", "R10k": "R10k_0201", "R4k7": "R4k7_0201", "C100n": "C100n_0201", "C10n": "C10n_0201"}
P0201_REFS = set("""R116 R124 R127 R128 R508 R311 R312 R313 R314 R315 R316 R401 R402 R501 R503 R504 R505 R506
C107 C108 C314 C401 C405 C501 C504 C505 C113 C120 C103 C308 C312""".split())
CONTACTS = False; WLCSP = True; ANT_LID = False           # kept for the unchanged v2 block code
INA_KEY = "INA236_YBJ"; RLIM_KEY = "R12R_0805"
sys.path.insert(0, HERE)
from catalog import CAT

NC = skidl.NC if hasattr(skidl, "NC") else __import__("builtins").NC   # SKiDL exposes NC as a builtin
PINMAP_DIR = os.path.join(DESIGN, "pinmap")
EE_INDEX = json.load(open(os.path.join(DESIGN, "lib", "easyeda_index.json")))
TYPES = {"input": Pin.types.INPUT, "output": Pin.types.OUTPUT, "bidirectional": Pin.types.BIDIR, "tri_state": Pin.types.TRISTATE,
         "passive": Pin.types.PASSIVE, "power_in": Pin.types.PWRIN, "power_out": Pin.types.PWROUT,
         "open_collector": Pin.types.OPENCOLL, "no_connect": Pin.types.NOCONNECT}
try:
    from skidl import KICAD10
    set_default_tool(KICAD10)
except ImportError:
    set_default_tool(KICAD9)

def footprint_of(key):
    c = CAT[key]
    if c.get("fp"): return c["fp"]
    e = EE_INDEX.get(c["lcsc"], {})
    if "footprint" not in e:
        raise SystemExit(f"no EasyEDA footprint for {key} {c['lcsc']}: {e.get('error')}")
    # the board uses the reviewed copy (tools/review_footprints.py): identical copper, fixed paste/courtyard/holes/fields
    return e["footprint"].replace("easyeda:", "easyeda_rev:", 1)

def load_pinmap(lcsc):
    return yaml.safe_load(open(os.path.join(PINMAP_DIR, f"{lcsc}.yaml")))

_templates = {}
def template(key):
    if key in _templates: return _templates[key]
    c = CAT[key]; kind = c["kind"]
    if kind == "pinmap":
        pm = load_pinmap(c["lcsc"])
        pins = [Pin(num=str(n), name=p["name"], func=TYPES[p["type"]]) for n, p in pm["pins"].items()]
        prefix = {"C10488": "Q", "C20526": "Q", "C48502": "D", "C8661": "D", "C48260": "D", "C965793": "D", "C511402": "PD", "C718072": "X", "C97604": "X",
                  "C478155": "Q", "C253326": "Q", "C130414": "D", "C5603826": "D", "C125114": "D", "C598214": "D", "C398713": "X",
                  "C478207": "Q", "C549313": "D", "C549275": "D", "C20345399": "D", "C896422": "D", "C221907": "SW", "C324723": "J", "C6736531": "D", "C504101": "Q"}.get(c["lcsc"], "U")
        name = re.sub(r"[^A-Za-z0-9_.+-]", "_", pm["mpn"])
    elif kind in ("R", "C", "L"):
        pins = [Pin(num="1", name="~", func=Pin.types.PASSIVE), Pin(num="2", name="~", func=Pin.types.PASSIVE)]
        prefix, name = kind, kind
    elif kind == "pad1":
        pins = [Pin(num="1", name="~", func=Pin.types.PASSIVE)]; prefix, name = "J", "PAD"
    elif kind == "spring":            # JLC-placed spring finger, one pad (rotation-neutral mating tab, REDESIGN 5.8 item 6)
        pins = [Pin(num="1", name="~", func=Pin.types.PASSIVE)]; prefix, name = "J", "SPRING"
    elif kind == "lidtail":
        pins = [Pin(num=str(i), name=n, func=Pin.types.PASSIVE) for i, n in enumerate(["PV+", "PV-", "BS_GND"], 1)]
        prefix, name = "J", "LID_TAIL"
    elif kind == "fpc10":          # [V3F] J13 soldered display FPC land: 10 pins in the LS011B7DH03 order + an asymmetric key pad (no net)
        names = ["SCLK", "SI", "SCS", "EXTCOMIN", "DISP", "VDDA", "VDD", "EXTMODE", "VSS", "VSSA"]
        pins = [Pin(num=str(i), name=n, func=Pin.types.PASSIVE) for i, n in enumerate(names, 1)]
        pins.append(Pin(num="11", name="KEY", func=Pin.types.NOCONNECT)); prefix, name = "J", "FPC_LS011B7DH03"
    elif kind == "fpc10b":         # [G1 L0] J13 land for the display bridge flex: 10 pads, LS011B7DH03 terminal order, no key pad (keyed by the flex outline)
        names = ["SCLK", "SI", "SCS", "EXTCOMIN", "DISP", "VDDA", "VDD", "EXTMODE", "VSS", "VSSA"]
        pins = [Pin(num=str(i), name=n, func=Pin.types.PASSIVE) for i, n in enumerate(names, 1)]; prefix, name = "J", "FPC_BRIDGE_10P"
    elif kind == "tail2":          # [V3F] J16 front-light tail, J17 motor wires: 2 hand-soldered pads
        pins = [Pin(num="1", name="+", func=Pin.types.PASSIVE), Pin(num="2", name="-", func=Pin.types.PASSIVE)]; prefix, name = "J", "TAIL2"
    elif kind == "swd6":
        pins = [Pin(num=str(i), name=n, func=Pin.types.PASSIVE) for i, n in
                enumerate(["VDD", "GND", "SWDIO", "SWDCLK", "nRESET", "DISP_CTRL"], 1)]
        prefix, name = "J", "SWD_2x3"
    elif kind == "testarray":
        pins = [Pin(num=str(i), name=n, func=Pin.types.PASSIVE) for i, n in
                enumerate(["VDD", "GND", "SWDIO", "SWDCLK", "nRESET", "DISP_CTRL", "VSTOR", "VIN_DC", "VLED", "AVDD_ECG"], 1)]
        prefix, name = "J", "TEST_2x5"
    elif kind == "fid":
        pins = []; prefix, name = "FID", "FIDUCIAL"
    elif kind == "nettie":
        pins = [Pin(num="1", name="~", func=Pin.types.PASSIVE), Pin(num="2", name="~", func=Pin.types.PASSIVE)]; prefix, name = "NT", "NetTie_2"
    elif kind == "antenna":
        pins = [Pin(num="1", name="FEED", func=Pin.types.PASSIVE), Pin(num="2", name="GND", func=Pin.types.PASSIVE)]; prefix, name = "AE", "ANT_IFA"
    elif kind == "pvcell":
        pins = [Pin(num="1", name="+", func=Pin.types.PWROUT), Pin(num="2", name="-", func=Pin.types.PASSIVE)]; prefix, name = "SC", c["value"]
    elif kind == "jumper":
        pins = [Pin(num="1", name="~", func=Pin.types.PASSIVE), Pin(num="2", name="~", func=Pin.types.PASSIVE)]; prefix, name = "JP", "SolderJumper"
    else:
        raise ValueError(kind)
    t = Part(tool=SKIDL, name=name, ref_prefix=prefix, dest=TEMPLATE, footprint=footprint_of(key), pins=pins)
    _templates[key] = t
    return t

def jlc_record(lcsc):
    """Exact-match record from the cached JLC parts API answer (tools/jlc_query.py), or None."""
    if not lcsc: return None
    p = next((q for q in (os.path.join(d, f"{lcsc}.json") for d in JLC_CACHES) if os.path.exists(q)), None)
    try:
        r = json.load(open(p))
        if r.get("http") != 200: r = json.load(open(os.path.join(JLC_CACHES[2], f"{lcsc}.json")))
        x = [x for x in r["response"]["data"]["componentPageInfo"]["list"] if x["componentCode"] == lcsc][0]
        return dict(lib="Basic" if x["componentLibraryType"] == "base" else ("Preferred" if x.get("preferredComponentFlag") else "Extended"),
                    stock=x.get("stockCount"), mpn=x.get("componentModelEn"), mfr=x.get("componentBrandEn"),
                    pkg=x.get("componentSpecificationEn"), fetched=r.get("fetched_utc"), prices=x.get("componentPrices"))
    except Exception:
        return None

def mk(key, ref, block, func="", value=None, dnp=False, note="", side="F"):
    """side: 'F' = sky side (F.Cu, every JLC-placed part except the PPG optics), 'B' = skin face (B.Cu)."""
    if VARIANT["PASSIVES"] == "0201" and ref in P0201_REFS and key in P0201_KEYS: key = P0201_KEYS[key]
    c = CAT[key]
    p = template(key)(ref=ref, tag=ref)
    p.value = value or c["value"]
    p.block, p.catkey, p.func, p.dnp, p.note, p.side = block, key, func, dnp, note, side
    p.lcsc = c.get("lcsc")
    if p.lcsc: p.fields["LCSC"] = p.lcsc
    p.fields["Function"] = func
    if dnp: p.fields["DNP"] = "DNP"
    return p

def pin(part, ident):
    """Exact pin look-up: int -> pin number, str -> datasheet name (must be unique) or pin number."""
    if isinstance(ident, int):
        hits = [p for p in part.pins if str(p.num) == str(ident)]
    else:
        hits = [p for p in part.pins if p.name == ident] or [p for p in part.pins if str(p.num) == ident]
    if len(hits) != 1:
        raise KeyError(f"{part.ref}: pin {ident!r} matched {len(hits)} pins")
    return hits[0]

def wire(part, mapping):
    """mapping: {pin number (int) or datasheet name (str): Net or NC}."""
    for ident, net in mapping.items():
        p = pin(part, ident)
        p += net
    return part

def two(p, a, b):
    """Connect a 2-terminal part: pin 1 to a, pin 2 to b."""
    pin(p, 1).__iadd__(a); pin(p, 2).__iadd__(b)
    return p

def check_all_pins_assigned(circuit):
    """Fail if any pin of any part was left without a net or an explicit NC (catches forgotten pins)."""
    bad = [f"{p.ref}.{q.num}({q.name})" for p in circuit.parts for q in p.pins if q.net is None]
    if bad:
        raise SystemExit("unassigned pins: " + ", ".join(bad))

def export_parts(circuit, path):
    rows = {}
    for p in circuit.parts:
        c = CAT[p.catkey]
        pm = load_pinmap(c["lcsc"]) if c["kind"] == "pinmap" else None
        j = jlc_record(c.get("lcsc"))
        nets, names, types = {}, {}, {}
        for q in p.pins:
            n = q.net.name if q.net is not None else None
            nets[str(q.num)] = None if (n is None or n.startswith("__NOCONNECT")) else n
            names[str(q.num)] = q.name
            types[str(q.num)] = getattr(q.func, "name", str(q.func))
        rows[p.ref] = dict(
            value=p.value, footprint=p.footprint, lcsc=None if p.dnp else c.get("lcsc"), lcsc_ref=c.get("lcsc"),
            jlc_lib=(j or {}).get("lib"), jlc_stock=(j or {}).get("stock"), jlc_fetched=(j or {}).get("fetched"),
            mpn=(pm or {}).get("mpn") or (j or {}).get("mpn") or "", manufacturer=(pm or {}).get("manufacturer") or (j or {}).get("mfr") or "",
            kind=c["kind"], catkey=p.catkey, block=p.block, func=p.func, dnp=p.dnp, note=p.note, side=getattr(p, "side", "F"),
            jlc_placed=bool(c.get("lcsc")) and not p.dnp,
            pins=nets, pinnames=names, pintypes=types)
    json.dump(dict(sorted(rows.items(), key=lambda kv: (re.match(r"[A-Z]+", kv[0]).group(0), int(re.sub(r"\D", "", kv[0]) or 0)))),
              open(path, "w"), indent=1, ensure_ascii=False)
    # [G1] variant record for tools/make_outputs.py and tools/area_check.py (motor cut-out, switches)
    json.dump(dict(tag=VTAG, switches={k: VARIANT[k] for k in ("FL", "LED", "MOTOR", "O2")}, motor=MOTOR, absent_nets=sorted(ABSENT_NETS)),
              open(os.path.join(os.path.dirname(path), "variant.json"), "w"), indent=1)
    return rows
