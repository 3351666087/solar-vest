"""Reviewed copy of the EasyEDA-derived footprint library: lib/easyeda.pretty -> lib/easyeda_rev.pretty.

Why (Integrate stage 2026-11-12, design/review_mcu-rf-dfm.md findings 1, 2, 7, 9 and footprint_audit FLAG C2803242):
  * copper pads are not changed (pad numbers, positions, sizes, rotations stay exactly JLC's/EasyEDA's, so the cplgate
    G4 geometry match against the EasyEDA record is unaffected), with ONE exception since the V2-B review (finding R-12):
    the round lands of the two 0.4 mm BGA-class parts are set to 0.20 mm diameter (LAND_DIA below). Pad numbers, centres and
    count are untouched, so the pad pairing of G4 is the same; only the overlap grade changes. Reason: EasyEDA draws 0.17 mm
    (nRF52832-CIAA) and 0.149 mm (INA236 YBJ), below JLC's minimum BGA pad of 0.2 mm;
  * U6 C77540: the 4 unnumbered EP "via" holes that easyeda2kicad turned into plated, pasted, mask-opened PTH pads on
    BOTH sides are removed (EasyEDA tents them; layout places GND POFV vias in the EP instead);
  * exposed-pad paste is replaced by windowed apertures (paste-only pads) at the coverage TI's stencil examples give
    (BQ25570 81 % SLUSBH2G p.45, ADS1291 77 % SBAS502C p.82, TPS61099 88 % SLVSD88M p.30) or, for the nRF52832,
    EasyEDA's own 64 % window (cache/easyeda/C77540.json layer-5 region) split 3 x 3 for outgassing;
  * TMP117 C2803242 thermal pad (pad 7): paste removed (TI SNOSD82 p.35: best accuracy with the thermal pad unsoldered;
    the copper stays as the floating island coupled to E1, R-THERM-1);
  * F.CrtYd regenerated as the bounding box of pads + body + margin (0.15 mm for 2-terminal chips <= 0603, 0.25 mm
    otherwise) so KiCad's courtyard DRC enforces assembly spacing (SIM-15d);
  * the footprint-level property "LCSC Part" is stripped: the symbol's LCSC field is the only one (cplgate rule R1).
Every change is recorded in lib/easyeda_rev_manifest.json with the sha256 of the source and the output file.
usage: python review_footprints.py
"""
import hashlib, json, math, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); DESIGN = os.path.dirname(HERE)
SRC = os.path.join(DESIGN, "lib", "easyeda.pretty"); DST = os.path.join(DESIGN, "lib", "easyeda_rev.pretty")
os.makedirs(DST, exist_ok=True)

# EP paste plans: LCSC -> (EP pad number, grid n, target coverage, source)
EP_PASTE = {
    "C77540":   ("49", 3, 0.64, "EasyEDA C77540 paste region 3.04 mm square on the 3.80 mm land = 64 %, split 3 x 3"),
    "C506250":  ("21", 2, 0.81, "TI SLUSBH2G p.45 example stencil: 81 % printed solder coverage"),
    "C139059":  ("33", 2, 0.77, "TI SBAS502C p.82 example stencil: 77 % printed solder coverage"),
    "C2842395": ("7",  1, 0.88, "TI SLVSD88M p.30 example stencil: 88 % printed solder coverage"),
    "C5208201": ("9",  1, 0.87, "[V3F] TI SLUSDJ8A p.34 example stencil (DSG0008A): 87 % printed solder coverage under the package"),
}
NO_PASTE = {"C2803242": ("7", "TI TMP117 SNOSD82 p.35: thermal pad best left unsoldered (floating copper island to E1)")}
# [S1 D-9] pads deleted from the reviewed copy (with the body box used for the courtyard): C221907 pad 5 is the land of the ESD ground pin,
# which the GK part does not have (C&K PTS840 catalogue B-40/B-41: "PTS840 GK SMTR LFS" listed under "Without ground pin"); its F.Paste would
# print a solder deposit under the 1.35 mm body (tilt, solder ball). Body box = C&K body 2.9 x 3.5 plus the 0.65 mm actuator (EasyEDA silk).
DROP_PAD = {"C221907": ("5", "C&K PTS840 B-40/B-41: GK has no ground pin; EasyEDA pad 5 (ESD-pin land, F.Paste) deleted, review D-9")}
BODY_BOX = {"C221907": ((-2.56, -1.75), (0.98, 1.75), "C&K PTS840 B-41: body 2.9 x 3.5 mm + actuator 0.65 mm at -x (EasyEDA silk -2.56 .. 0.98)"),
            # [S2a] Hirose FH34 p.6: A 7.0 +-0.15 (max 7.15), depth 3.8 incl. the actuator; EasyEDA silk -2.15 .. +1.65 in y (lead / actuator side at -y).
            # The EasyEDA courtyard (y -1.21 .. 1.79) missed the lead row.
            "C324723": ((-3.575, -2.10), (3.575, 1.70), "Hirose FH34 p.6: body 7.15 (A max) x 3.8 mm, lead / actuator side at -y [S2a]"),
            # [S2b E-4] Nexperia PMEG10020AELR Fig. 16 (CFP3 / SOD123W): 3.7 max over the leads x 1.9 max body width
            "C6736531": ((-1.85, -0.95), (1.85, 0.95), "Nexperia PMEG10020AELR Fig. 16: 3.3-3.7 x 1.5-1.9 mm (max kept) [S2b]")}
# [G1 level 0, 2026-11-15] SW1 on the maker's land. C&K PTS840 datasheet p.2 (B-41) "RECOMMENDED PCB LAYOUT" (G leads): overall 5 +- 0.1 across the leads with a
# 2.2 +- 0.1 gap -> pads 1.40 long at centres +-1.80; 2.5 +- 0.1 along the actuation axis with a 0.4 +- 0.1 gap -> pads 1.05 wide at centres +-0.725 about the lead
# centre line. In the EasyEDA frame the actuation axis is x (actuator at -x) and the lead centre line is x = -0.47 (mid of EasyEDA's pad columns -1.22 / +0.28 and of
# the body -1.92 .. 0.98). Pad numbers, the origin (JLC's centroid) and the 0 deg orientation are unchanged; only the copper moves.
# [S2b E-4] D14 PMEG10020AELR (C6736531): EasyEDA draws 1.00 x 1.20 pads at +-1.65 (gap 2.30, outer 4.30). Nexperia Fig. 17 reflow footprint (SOD123W):
# solder lands 1.2 x 1.2 at centres 2.8 apart (gap 1.6, outer 4.0), paste 1.1, resist 1.4, occupied area 4.4 x 2.1. Terminals (Fig. 16): leads 0.75-1.05 wide,
# 0.3-0.6 long, 3.3-3.7 overall. Pad 1 (cathode, marking bar, Table 2) stays at -x as in EasyEDA (its silk bar is at -x); origin and 0 deg unchanged.
SET_PAD = {"C6736531": ({"1": (-1.40, 0.0, 1.20, 1.20), "2": (1.40, 0.0, 1.20, 1.20)},
                        "Nexperia PMEG10020AELR Fig. 17 reflow land: 2 pads 1.2 x 1.2 at +-1.40 (was EasyEDA 1.00 x 1.20 at +-1.65); numbers, origin, 0 deg unchanged [S2b]"),
           "C221907": ({"1": (-1.195, 1.80, 1.05, 1.40), "2": (-1.195, -1.80, 1.05, 1.40), "3": (0.255, 1.80, 1.05, 1.40), "4": (0.255, -1.80, 1.05, 1.40)},
                       "C&K PTS840 B-41 recommended PCB layout: 4 pads 1.05 x 1.40 at lead-line +-0.725 / +-1.80 (was EasyEDA 0.84 x 1.785 at +-0.75 / +-2.12); numbers, origin, 0 deg unchanged"),
           # [S2c] LQW15AN wire-wound 0402 (C215 9.0 nH, L204 6.2 nH): Murata JELF243A_0100H-01 section 12.1 land for reflow: a (gap) 0.6, b (outer) 1.42, c (width) 0.66
           # -> 2 pads 0.41 x 0.66 at +-0.505. EasyEDA: C6652901 0.50 x 0.648 at +-0.43 (gap 0.36), C668465 0.54 x 0.54 at +-0.42 (gap 0.30).
           "C6652901": ({"1": (-0.505, 0.0, 0.41, 0.66), "2": (0.505, 0.0, 0.41, 0.66)},
                        "Murata LQW15AN spec JELF243A 12.1 land: 2 pads 0.41 x 0.66 at +-0.505 (gap 0.60, outer 1.42) (was EasyEDA 0.50 x 0.648 at +-0.43); numbers, origin, 0 deg unchanged [S2c]"),
           "C668465": ({"1": (-0.505, 0.0, 0.41, 0.66), "2": (0.505, 0.0, 0.41, 0.66)},
                       "Murata LQW15AN spec JELF243A 12.1 land: 2 pads 0.41 x 0.66 at +-0.505 (gap 0.60, outer 1.42) (was EasyEDA 0.54 x 0.54 at +-0.42); numbers, origin, 0 deg unchanged [S2c]"),
           "C2048575": ({"1": (-0.505, 0.0, 0.41, 0.66), "2": (0.505, 0.0, 0.41, 0.66)},
                        "Murata LQW15AN spec JELF243A 12.1 land (same series): 2 pads 0.41 x 0.66 at +-0.505; numbers, origin, 0 deg unchanged [F]"),
           "C471381": ({"1": (-0.505, 0.0, 0.41, 0.66), "2": (0.505, 0.0, 0.41, 0.66)},
                       "Murata LQW15AN spec JELF243A 12.1 land (same series): 2 pads 0.41 x 0.66 at +-0.505; numbers, origin, 0 deg unchanged [F]")}
# [FIX R-12] land diameter of round BGA-class lands: LCSC -> (diameter mm, source). Centres and numbers are not touched.
LAND_DIA = {
    "C509405":  (0.20, "JLC capability page (BGA pad 0.2 mm minimum, 0.2-0.25 mm needs ENIG; read 2026-11-12, cache/v2/jlc_review/pages/pcb-capabilities.html); "
                       "nRF52832 PS v1.4 Table 132 p.541: ball b = 0.20 mm nominal. Gap between lands at 0.40 mm pitch: 0.20 mm (JLC SMD pad-to-pad >= 0.15 mm)"),
    "C4371025": (0.20, "JLC capability page (BGA pad 0.2 mm minimum); TI YBJ0006 drawing 4226653/A of the same YBJ family (cache/v2/ds_review/ti_mxbg457.pdf, as read "
                       "by the review): land 0.20 mm NSMD. The YBJ0008 drawing itself was not found"),
}
DROP_UNNAMED_PTH = {"C77540"}

pad_re = re.compile(r'^\s*\(pad\s+("?[^\s"]*"?)\s+(\w+)\s+(\w+)\s+\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)\s+\(size\s+([-\d.]+)\s+([-\d.]+)\)')
crt_re = re.compile(r'\(layer F\.CrtYd\)')
pt_re = re.compile(r'\((?:start|end|center)\s+([-\d.]+)\s+([-\d.]+)\)')

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

def pad_bbox(x, y, w, h, rot):
    a = math.radians(rot or 0.0); c, s = abs(math.cos(a)), abs(math.sin(a))
    hw, hh = (w * c + h * s) / 2, (w * s + h * c) / 2
    return x - hw, y - hh, x + hw, y + hh

manifest = {}
for fn in sorted(os.listdir(SRC)):
    if not fn.endswith(".kicad_mod"): continue
    lcsc = fn.split("_")[0]
    src = os.path.join(SRC, fn); lines = open(src).read().splitlines()
    out, changes, pads, body = [], [], [], []; land_changed = False; land_old = None
    is_chip = bool(re.match(r"C\d+_(C|R|L)0(201|402|603)(-RD)?\.kicad_mod$", fn))     # V2: 0201 parts and the L0201-RD drawing
    custom = None                                     # (x, y, rot, poly-width) while inside a custom pad's primitives
    for ln in lines:
        if custom is not None:                        # custom pad: primitives are relative to the pad anchor
            for m2 in re.finditer(r"\(xy\s+([-\d.]+)\s+([-\d.]+)\)", ln):
                cx0, cy0, crot, cw = custom
                a = math.radians(crot); px, py = float(m2.group(1)), float(m2.group(2))
                gx = cx0 + px * math.cos(a) - py * math.sin(a); gy = cy0 + px * math.sin(a) + py * math.cos(a)
                pads.append((gx - cw / 2, gy - cw / 2, gx + cw / 2, gy + cw / 2))
            if ln.strip() == ")" and out and out[-1].strip() == ")": custom = None
            out.append(ln); continue
        if '(property "LCSC Part"' in ln:
            changes.append("stripped footprint property 'LCSC Part' (symbol LCSC field is the single source, rule R1)"); continue
        if crt_re.search(ln):
            for m in pt_re.finditer(ln): body.append((float(m.group(1)), float(m.group(2))))
            continue                                  # regenerated below
        m = pad_re.match(ln)
        if m:
            num = m.group(1).strip('"'); typ = m.group(2)
            x, y, rot, w, h = float(m.group(4)), float(m.group(5)), float(m.group(6) or 0), float(m.group(7)), float(m.group(8))
            if lcsc in DROP_PAD and num == DROP_PAD[lcsc][0]:
                changes.append(f"COPPER: pad {num} deleted at ({x:.2f}, {y:.2f}) {w:.2f} x {h:.2f}; {DROP_PAD[lcsc][1]}")
                continue
            if lcsc in SET_PAD and num in SET_PAD[lcsc][0]:
                nx, ny, nw, nh = SET_PAD[lcsc][0][num]
                ln = re.sub(r"\(at\s+[-\d.]+\s+[-\d.]+(?:\s+[-\d.]+)?\)\s+\(size\s+[-\d.]+\s+[-\d.]+\)", f"(at {nx:.3f} {ny:.3f} 0.00) (size {nw:.3f} {nh:.3f})", ln, count=1)
                changes.append(f"COPPER: pad {num} ({x:.2f}, {y:.2f}) {w:.2f} x {h:.2f} -> ({nx:.3f}, {ny:.3f}) {nw:.2f} x {nh:.2f}; {SET_PAD[lcsc][1]}")
                x, y, rot, w, h = nx, ny, 0.0, nw, nh
            if lcsc in DROP_UNNAMED_PTH and num == "" and typ == "thru_hole":
                changes.append(f"removed unnumbered PTH pad at ({x:.2f}, {y:.2f}) with *.Paste/*.Mask (EasyEDA via, tented in the source)")
                continue
            if lcsc in LAND_DIA and typ == "smd" and m.group(3) == "circle":
                d_new, why = LAND_DIA[lcsc]
                if abs(w - d_new) > 1e-6 or abs(h - d_new) > 1e-6:
                    ln = ln.replace(f"(size {m.group(7)} {m.group(8)})", f"(size {d_new:.3f} {d_new:.3f})")
                    land_changed = True; land_old = w
                    w = h = d_new
            pads.append(pad_bbox(x, y, w, h, rot))
            if m.group(3) == "custom": custom = (x, y, rot, 0.1)
            if lcsc in EP_PASTE and num == EP_PASTE[lcsc][0]:
                epn, n, f, why = EP_PASTE[lcsc]
                ln = ln.replace("(layers F.Cu F.Paste F.Mask)", "(layers F.Cu F.Mask)")
                out.append(ln)
                if n == 1:
                    k = math.sqrt(f); sw, sh = w * k, h * k
                    out.append(f'\t(pad "" smd rect (at {x:.3f} {y:.3f} 0) (size {sw:.3f} {sh:.3f}) (layers F.Paste))')
                    cov = sw * sh / (w * h)
                else:
                    # n x n windows, 0.20 mm stencil webs between them, outer inset chosen to hit the coverage target
                    web = 0.20; k = math.sqrt(f); sw, sh = k * w / n, k * h / n
                    ex = (w - n * sw - (n - 1) * web) / 2; ey = (h - n * sh - (n - 1) * web) / 2
                    if ex < 0 or ey < 0:            # target not reachable with 0.20 mm webs: keep webs, shrink windows
                        ex, ey = max(ex, 0.0), max(ey, 0.0); sw = (w - (n - 1) * web) / n; sh = (h - (n - 1) * web) / n
                    for i in range(n):
                        for j in range(n):
                            cx = x - w / 2 + ex + sw / 2 + i * (sw + web); cy = y - h / 2 + ey + sh / 2 + j * (sh + web)
                            out.append(f'\t(pad "" smd rect (at {cx:.3f} {cy:.3f} 0) (size {sw:.3f} {sh:.3f}) (layers F.Paste))')
                    cov = n * n * sw * sh / (w * h)
                changes.append(f"EP pad {epn} {w:.2f} x {h:.2f}: full paste -> {n} x {n} window(s) {sw:.3f} x {sh:.3f} mm"
                               f"{' with 0.20 mm webs' if n > 1 else ''}, coverage {cov * 100:.0f} %; {why}")
                continue
            if lcsc in NO_PASTE and num == NO_PASTE[lcsc][0]:
                ln = ln.replace("(layers F.Cu F.Paste F.Mask)", "(layers F.Cu F.Mask)")
                changes.append(f"pad {num}: paste removed; {NO_PASTE[lcsc][1]}")
        out.append(ln)
    if land_changed:
        changes.append(f"COPPER: every round land {land_old:.3f} -> {LAND_DIA[lcsc][0]:.2f} mm diameter (centres, numbers and count unchanged; paste and mask follow the pad); {LAND_DIA[lcsc][1]}")
    # courtyard = pads + body (old courtyard outline) + margin, rounded outward to 0.01 mm
    if lcsc in BODY_BOX:
        body = [BODY_BOX[lcsc][0], BODY_BOX[lcsc][1]]; changes.append(f"courtyard body box {BODY_BOX[lcsc][2]}")
    xs = [b[0] for b in pads] + [b[2] for b in pads] + [p[0] for p in body]
    ys = [b[1] for b in pads] + [b[3] for b in pads] + [p[1] for p in body]
    mg = 0.15 if is_chip else 0.25
    x1, y1 = math.floor((min(xs) - mg) * 100) / 100, math.floor((min(ys) - mg) * 100) / 100
    x2, y2 = math.ceil((max(xs) + mg) * 100) / 100, math.ceil((max(ys) + mg) * 100) / 100
    old = (min(p[0] for p in body), min(p[1] for p in body), max(p[0] for p in body), max(p[1] for p in body)) if body else None
    crt = [f"\t(fp_line (start {a:.2f} {b:.2f}) (end {c:.2f} {d:.2f}) (layer F.CrtYd) (width 0.05))"
           for (a, b, c, d) in ((x1, y1, x2, y1), (x2, y1, x2, y2), (x2, y2, x1, y2), (x1, y2, x1, y1))]
    i_model = next((i for i, l in enumerate(out) if l.strip().startswith("(model")), len(out) - 1)
    out = out[:i_model] + crt + out[i_model:]
    changes.append(f"F.CrtYd {('%.2f x %.2f (body only)' % (old[2] - old[0], old[3] - old[1])) if old else 'none'} -> "
                   f"{x2 - x1:.2f} x {y2 - y1:.2f} mm (pads + body + {mg} mm)")
    dst = os.path.join(DST, fn)
    txt = "\n".join(out) + "\n"
    txt = txt.replace("(module easyeda2kicad:", "(module easyeda_rev:", 1)
    open(dst, "w").write(txt)
    manifest[fn] = dict(lcsc=lcsc, source_sha256=sha(src), reviewed_sha256=sha(dst), changes=changes)
# [V3F] SOT883 diode lands. EasyEDA's C549275 (BAT54CM) draws the two small lands 0.40 x 0.16 mm, narrower than the package terminals
# (b 0.22-0.30 mm, Nexperia BAT54CM p.6), and C549313 (BAV70M) has no EasyEDA footprint at all (API 404, 2026-11-13 20:41 UTC). Both get the
# pad set of C478155 (PMZ290UNE2YL, Nexperia SOT883, reviewed in v2: 0.45 x 0.25 / 0.45 x 0.70 mm at x +-0.35, y +-0.23), which has the same
# orientation as the C549275 record (pad 3 large at -x, pad 1 at +y, pad 2 at -y) and the same origin: JLC's centroid and 0 deg are unchanged.
def sot883_pads():
    t = open(os.path.join(DST, "C478155_DFN1006-3L_L1.0-W0.6-LS1.0-BR.kicad_mod")).read().splitlines()
    return [l for l in t if l.strip().startswith("(pad ") or "F.CrtYd" in l]      # pads and the courtyard that belongs to them
def put_pads(fn, why):
    path = os.path.join(DST, fn); t = open(path).read().splitlines(); new_pads = sot883_pads()
    out = [l for l in t if not l.strip().startswith("(pad ") and "F.CrtYd" not in l]
    i = next(i for i, l in enumerate(out) if l.strip().startswith("(model")) if any(l.strip().startswith("(model") for l in out) else len(out) - 1
    out = out[:i] + new_pads + out[i:]
    open(path, "w").write("\n".join(out) + "\n")
    manifest.setdefault(fn, dict(lcsc=fn.split("_")[0], changes=[]))["changes"].append("COPPER: " + why); manifest[fn]["reviewed_sha256"] = sha(path)
put_pads("C549275_DFN1006-3_L1.0-W0.6-P0.35-BR_BAT54CM.kicad_mod",
         "small lands 0.40 x 0.16 -> 0.45 x 0.25 mm and large land 0.40 x 0.60 -> 0.45 x 0.70 mm, centres x +-0.32 -> +-0.35, y +-0.18 -> +-0.23 (pad set of C478155, same "
         "Nexperia SOT883; EasyEDA's 0.16 mm lands are narrower than the 0.22-0.30 mm terminals, BAT54CM p.6); numbers and orientation unchanged")
DERIVED = {"C549313_SOT883_BAV70M_land_of_C549275.kicad_mod": ("C549275_DFN1006-3_L1.0-W0.6-P0.35-BR_BAT54CM.kicad_mod",
           "BAV70M,315 (C549313): EasyEDA API 404 'Component not found' (2026-11-13 20:41 UTC). Land = the reviewed C549275 copy (Nexperia SOT883 pad set of C478155), "
           "same pin positions (1, 2 small lands, 3 large land; BAV70M p.2, BAT54CM p.3). JLC's own 0 deg for C549313 is unknown: preview mandatory")}
for new, (donor, why) in DERIVED.items():
    t = open(os.path.join(DST, donor)).read()
    name_old = donor[:-len(".kicad_mod")]; name_new = new[:-len(".kicad_mod")]
    t = t.replace(name_old, name_new)
    open(os.path.join(DST, new), "w").write(t)
    manifest[new] = dict(lcsc=new.split("_")[0], source_sha256=sha(os.path.join(DST, donor)), reviewed_sha256=sha(os.path.join(DST, new)),
                         changes=[f"DERIVED from {donor}: {why}"])
json.dump(dict(generated_by="design/tools/review_footprints.py", rule="copper pads unchanged except the land diameter of C509405 and C4371025 (review R-12); see module docstring", footprints=manifest),
          open(os.path.join(DESIGN, "lib", "easyeda_rev_manifest.json"), "w"), indent=1)
print(f"{len(manifest)} footprints reviewed -> {DST}")
for fn, m in manifest.items():
    sig = [c for c in m["changes"] if not c.startswith(("stripped", "F.CrtYd"))]
    if sig: print(" ", fn, "|", "; ".join(sig))
