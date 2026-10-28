"""JLCPCB fabrication + assembly outputs for one board, all through kicad-cli.

usage: python3 fab.py <pmbh|libb>
writes out/<b>/fab/:
  <b>_gerbers.zip            Gerbers + Excellon drills (upload as "Gerber file")
  <b>_BOM_JLC.csv            Comment, Designator, Footprint, LCSC Part #   (JLC-assembled parts only)
  <b>_CPL_JLC.csv            Designator, Mid X, Mid Y, Layer, Rotation      (JLC rotation corrections applied)
  <b>_user_parts.csv         parts JLC does NOT place (supercaps, XIAO) — you add these
  <b>.step / <b>.glb         assembled 3D board for enclosure design
  <b>_schematic.pdf, drc.json, erc.json
"""
import csv, json, math, os, re, shutil, subprocess, sys, zipfile

B = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.expanduser("~/Applications/KiCad/KiCad/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
OUT = os.path.join(HERE, "out", B); FAB = os.path.join(OUT, "fab")
PCB, SCH = os.path.join(OUT, f"{B}.kicad_pcb"), os.path.join(OUT, f"{B}.kicad_sch")
parts = json.load(open(os.path.join(HERE, f"{B}_parts.json")))

def run(*a):
    r = subprocess.run([CLI, *a], capture_output=True, text=True)
    if r.returncode not in (0, 5):   # 5 = DRC/ERC found violations (reported separately)
        sys.exit(f"kicad-cli {' '.join(a[:3])} failed:\n{r.stdout}\n{r.stderr}")
    return r

# ---------- make the project self-contained: local hw library + project library tables + relative 3D paths ----------
shutil.rmtree(os.path.join(OUT, "lib"), ignore_errors=True)
shutil.copytree(os.path.join(HERE, "lib"), os.path.join(OUT, "lib"), ignore=shutil.ignore_patterns("*.bak", "*-bak"))
open(os.path.join(OUT, "fp-lib-table"), "w").write('(fp_lib_table\n  (version 7)\n  (lib (name "hw") (type "KiCad") (uri "${KIPRJMOD}/lib/hw.pretty") (options "") (descr "project parts"))\n)\n')
open(os.path.join(OUT, "sym-lib-table"), "w").write('(sym_lib_table\n  (version 7)\n  (lib (name "hw") (type "KiCad") (uri "${KIPRJMOD}/lib/hw.kicad_sym") (options "") (descr "project symbols"))\n)\n')
pcb_txt = open(PCB).read().replace(os.path.join(HERE, "lib", "hw.3dshapes"), "${KIPRJMOD}/lib/hw.3dshapes")
open(PCB, "w").write(pcb_txt)

shutil.rmtree(FAB, ignore_errors=True); os.makedirs(FAB)
GER = os.path.join(FAB, "gerber"); os.makedirs(GER)

# ---------- checks ----------
run("pcb", "drc", "--severity-all", "--format", "json", "-o", os.path.join(FAB, "drc.json"), PCB)
run("sch", "erc", "--severity-all", "--format", "json", "-o", os.path.join(FAB, "erc.json"), SCH)
drc = json.load(open(os.path.join(FAB, "drc.json")))
erc = json.load(open(os.path.join(FAB, "erc.json")))
def count(vs):
    c = {}
    for v in vs: c[f'{v["severity"]}:{v["type"]}'] = c.get(f'{v["severity"]}:{v["type"]}', 0) + 1
    return c
erc_v = [v for s in erc.get("sheets", []) for v in s.get("violations", [])]
print("DRC", count(drc["violations"]), "| unconnected", len(drc["unconnected_items"]), "| parity", len(drc.get("schematic_parity", [])))
print("ERC", count(erc_v))

# ---------- gerbers + drill ----------
LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
run("pcb", "export", "gerbers", "--output", GER + "/", "--layers", LAYERS, "--subtract-soldermask", PCB)
run("pcb", "export", "drill", "--output", GER + "/", "--format", "excellon", "--drill-origin", "absolute",
    "--excellon-units", "mm", "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2", PCB)
with zipfile.ZipFile(os.path.join(FAB, f"{B}_gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(GER)): z.write(os.path.join(GER, f), f)

# ---------- BOM ----------
def jlc_assembled(ref, p):
    return p["footprint"] and p.get("lcsc") and p.get("jlc") in ("base", "ext")
groups = {}
for ref, p in parts.items():
    if not jlc_assembled(ref, p): continue
    key = (p["value"], p["footprint"].split(":")[1], p["lcsc"])
    groups.setdefault(key, []).append(ref)
nat = lambda r: (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r) or 0))
with open(os.path.join(FAB, f"{B}_BOM_JLC.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "Qty", "JLC library"])
    for (val, fp, lcsc), refs in sorted(groups.items(), key=lambda kv: nat(sorted(kv[1], key=nat)[0])):
        jl = parts[refs[0]]["jlc"]
        w.writerow([val, ",".join(sorted(refs, key=nat)), fp, lcsc, len(refs), "Basic" if jl == "base" else "Extended"])
with open(os.path.join(FAB, f"{B}_user_parts.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["Designator", "Value", "Footprint", "Why not JLC", "Note"])
    for ref, p in sorted(parts.items(), key=lambda kv: nat(kv[0])):
        if p.get("jlc") == "user":
            note = {"SUPERCAP": "2.7 V 10 F, 10x25 mm radial; lay flat on the silk outline, + to the square pad, solder 2 joints each",
                    "XIAO": "buy the pre-soldered-header XIAO nRF52840 Sense; push into J4/J5 (USB-C toward board edge)"}[p["catkey"]]
            w.writerow([ref, p["value"], p["footprint"] or "plug-in module", "not stocked by JLC", note])

# ---------- CPL with JLC rotation corrections ----------
# community database used by both kicad-jlcpcb-tools (Bouni) and JLCKicadTools (matthewlai), fetched 2026-10-11
ROT_DB = [(r"^SOT-223", 180), (r"^SOT-23", -90), (r"^SOT-89", 180), (r"^TSOT-23", 180), (r"^SOT-353", 180), (r"^SOT-363", 180),
          (r"^SSOP-", 270), (r"^TSSOP-", 270), (r"^SOIC-", 270), (r"^VSSOP-10_", 270), (r"^JST_PH_S", 180)]
# NOTE CP_Elec: the community DB says +180, but the JLCPCB (jlc-smt.com) placement preview showed C15 reversed with it
# (2026-10-13). Domestic JLC needs 0 for CP_Elec_6.3x7.7, so no correction is applied.
# Per-part corrections win over the name rules. Pad-matched against each part's JLC/EasyEDA footprint (jlc_rotcheck.py)
# after JLC's original placement drawing (2026-10-13) showed the SOT-23 MOSFETs/BAT54S and the MSOP/SC-70 ICs 90° off, and the 2-pin
# JST PH (C295747) 180° reversed: its JLC footprint is drawn like KiCad's, unlike the 5-pin C265104.
LCSC_ROT = {"C15127": 180, "C20917": 180, "C47546": 180, "C49851": 270, "C2869734": 270, "C295747": 0, "C265104": 180,
            "C2897370": 270}
# JLC places THT parts by body centre; KiCad's anchor is pin 1. Footprint-local mm, rotated with the part.
LCSC_OFF = {"C2897370": (0.0, 7.62), "C474892": (1.75, 0.0)}
def correction(fp, lcsc=None):
    if lcsc in LCSC_ROT: return LCSC_ROT[lcsc]
    best = (0, 0)
    for pat, rot in ROT_DB:
        m = re.search(pat, fp)
        if m and len(m.group(0)) > best[0]: best = (len(m.group(0)), rot)
    return best[1]
pos_raw = os.path.join(FAB, "pos_raw.csv")
run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "--exclude-dnp", "-o", pos_raw, PCB)
rows = list(csv.DictReader(open(pos_raw)))
with open(os.path.join(FAB, f"{B}_CPL_JLC.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    n = 0
    for r in rows:
        ref = r["Ref"]; p = parts.get(ref)
        if not p or not jlc_assembled(ref, p): continue
        fp = p["footprint"].split(":")[1]
        rot = (float(r["Rot"]) + correction(fp, p["lcsc"])) % 360
        x, y = float(r["PosX"]), float(r["PosY"])
        if p["lcsc"] in LCSC_OFF:  # pos export is y-up, so the y-down local offset flips sign
            ox, oy = LCSC_OFF[p["lcsc"]]; t = math.radians(float(r["Rot"]))
            x += ox * math.cos(t) + oy * math.sin(t); y -= -ox * math.sin(t) + oy * math.cos(t)
        w.writerow([ref, f'{x:.4f}mm', f'{y:.4f}mm', "Top" if r["Side"] == "top" else "Bottom", f"{rot:g}"])
        n += 1
os.remove(pos_raw)
missing = [r for r, p in parts.items() if jlc_assembled(r, p) and r not in {x["Ref"] for x in rows}]
print(f"BOM lines {len(groups)}, CPL parts {n}", "| MISSING from pos:" if missing else "", missing or "")

# ---------- 3D + docs ----------
run("pcb", "export", "step", "--subst-models", "--force", "-o", os.path.join(FAB, f"{B}.step"), PCB)
run("pcb", "export", "glb", "--subst-models", "--force", "--include-tracks", "--include-pads", "--include-silkscreen",
    "--include-soldermask", "-o", os.path.join(FAB, f"{B}.glb"), PCB)
run("sch", "export", "pdf", "-o", os.path.join(FAB, f"{B}_schematic.pdf"), SCH)
for side, extra in (("top", []), ("bottom", []), ("iso", ["--rotate", "-35,0,25"])):
    run("pcb", "render", "--side", "top" if side == "iso" else side, "--width", "1800", "--height", "1300", "--quality", "high",
        *extra, "-o", os.path.join(FAB, f"{B}_render_{side}.png"), PCB)
print("fab outputs:", sorted(os.listdir(FAB)))
