"""One-off: write the independent review (ruling P-6) into the pin maps. Replaces each file's `reviewed:` block and applies the
listed fixes. Backups: v3/package/backup_gateprep/pinmap/. Evidence pages: v3/package/GATEPREP.md §2."""
import os, re, sys, yaml
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "design", "pinmap")
BY = "independent-agent"; DATE = "2026-11-16"

R = {
 "C5603826": dict(result="agrees (with a caution)", source="ams-OSRAM CT DBLP31.12 data sheet Version 1.3 (2021-03-29), Chinese edition, "
   "https://look.ams-osram.com/m/7737569ee6f0cd0e/original/CT-DBLP31-12.pdf (sha256 0fb488c925064f17..., read online 2026-11-16)",
   pages="p.11 dimensional drawing, pad view: leader 'anode' to one small land, leaders 'cathode' to the other small land and the large land; p.12 internal circuit (+/-) and recommended pad (no polarity shown)",
   compared="EasyEDA C5603826: pad 1 small land (-0.44,-0.52), pad 2 small land (0.45,-0.52), pad 3 large (0,0.53), silk dot at (-0.90,-0.87) beside pad 1; symbol pin 1 '+', pin 2 '-'. "
   "Board land (easyeda_rev) has the same pad numbers and positions. Netlist D3.1/D4.1 = VLED (anode).",
   caution="p.11 does not label the pad view; read as a bottom view (third view of the first-angle sequence, mirrored left-right): anode = small land on the LEFT in the top view with the small lands at the top = pad 1. "
   "The EasyEDA symbol and dot are the second source. The LED/PD loop-back test (G10) decides; the JLC preview row covers the bottom-side placement."),
 "C511402": dict(result="agrees", source="Vishay VEMD8080 data sheet Rev. 1.1 (05-Sep-2023), doc 84565, https://www.vishay.com/docs/84565/vemd8080.pdf "
   "(sha256 9fc7401a0d6d420c..., identical to the pin map's LCSC copy, read online 2026-11-16)",
   pages="p.4 'Pinning top view': pins 1-4 one row, 8-5 the other row, pin 5 = anode at the corner diagonal to pin 1; 'Pin 1 marking' dot at the pin-1 corner; footprint 8 x 0.54 x 0.55, pitch 1.31/1.38/1.31, rows 2.38",
   compared="EasyEDA C511402: pad 1 (2.00,-1.19), pads 1-4 one row, pad 5 (-2.00,1.19) diagonal to pad 1; silk dots (2.40,-1.25) and (2.03,-2.03) beside pad 1: "
   "the data sheet top view turned 180 deg, not mirrored. Netlist PD1.5 = PD_GND, the other seven = PD1_IN."),
 "C130414": dict(result="agrees; two fixes", source="Nexperia BAS521 product data sheet (1 July 2023). The LCSC URL in this file returned only an HTML shell online on 2026-11-16 and "
   "nexperia.com answered 403, so the project copy of that URL was read (cache/v2/ds/bas521.pdf, sha256 f8ea1381ad99407f..., same hash as recorded here). "
   "Online cross-check: Nexperia BAS521B data sheet (same SOD523 family), https://cdn.components.ru/media/PDF/3910755.pdf, Table 2: 1 K, 2 A.",
   pages="Table 2 Pinning information p.1: pin 1 K cathode, pin 2 A anode; Fig. 9 package outline SOD523 p.5; Fig. 10 reflow footprint p.6",
   compared="EasyEDA C130414: pad 1 (-0.65,0) with the silk dot (-0.80,0.40) and the band side; symbol C = 1, A = 2. Netlist D9.1 = EN_HOLD, D11.1 = CYC_A (cathodes).",
   fixed="package_drawing_page 6 -> 5 and land_pattern_page 7 -> 6 (the 2023 edition); refs now name D11 (the board uses D9 and D11; the file named only D9 and the contacts-variant D1)."),
 "C598214": dict(result="agrees", source="Kingbright KA-2810ASURSK data sheet DSAK2457 Rev V.7A, "
   "https://datasheet.lcsc.com/datasheet/pdf/67b1a40883785436a496c98954203521.pdf?productCode=C598214 (sha256 f92f83f6297beecd..., same as recorded, read online 2026-11-16)",
   pages="p.1 package dimensions: diode symbol with the bar at terminal 1 (1 = cathode, 2 = anode); front view (into the lens) terminal 1 left",
   compared="EasyEDA C598214 (land 'KA-2810AVBS-D'): pad 1 (-1.20,0) with the silk dot (-1.40,0.38); symbol K = 1, A = 2. Netlist D10.1 = ALERT_K.",
   caution="right-angle LED: the lens side is not in the land data; the JLC preview row checks that the lens faces the board edge."),
 "C6736531": dict(result="agrees for the PMEG10020AELR type; the -Q data sheet itself was not found", source="Nexperia PMEG10020AELR product data sheet (1 January 2023), "
   "https://datasheet.lcsc.com/datasheet/pdf/d8079dbb0971066558fedc170d99edb4.pdf?productCode=C552793 (sha256 a9d827c3f1d22ddf..., same as recorded, read online 2026-11-16). "
   "This is the data sheet of C552793 (PMEG10020AELR, not -Q); no PMEG10020AELR-Q data sheet was reachable (nexperia.com 403) ?",
   pages="Table 2 p.1: pin 1 K cathode, pin 2 A anode, 'The marking bar indicates the cathode'; Fig. 16 outline CFP3 (SOD123W) p.9; Fig. 17 reflow footprint p.10",
   compared="EasyEDA C6736531: pad 1 (-1.65,0) with the silk dot (-1.85,0.85) and the band side (-X); symbol pins carry numbers only (no K/A). Netlist D14.1 = VBUS (cathode).",
   fixed="polarity gains reference K / reference_pin '1' (missing before, so the gate had no pin-map vote)."),
 "C896422": dict(result="agrees; the EasyEDA contradiction is resolved: cathode = pad 1", source="onsemi NSR0240MX2/D Rev. 3, "
   "https://datasheet.lcsc.com/datasheet/pdf/4b95626787cd7ec325d86dd9eff135e9.pdf?productCode=C896422 (sha256 053f0d99260675e0..., same as recorded, read online 2026-11-16)",
   pages="p.1 pin assignment: 1 CATHODE, 2 ANODE; p.4 case 714AB issue B: top view pin-1 indicator, bottom view pin-1 pad with a chamfered corner, footprint 2 x 0.47 x 0.60 at 1.20",
   compared="EasyEDA C896422: pad 1 (+0.33,0) with the silk dot (0.50,-0.30) beside it; symbol C = 1, A = 2. Netlist D16.1 = VBUS. The '-RD' package token is not a side marker: "
   "in the 9 '-RD' footprints of v3/design/lib/easyeda.pretty pad 1 sits at -X in 6 and at +X in 3, and the silk dot sits at pad 1 in all 9. cplgate no longer counts the token as a vote.",
   fixed="polarity gains reference K / reference_pin '1'."),
 "C549313": dict(result="agrees", source="Nexperia BAV70M product data sheet (1 July 2022), "
   "https://datasheet.lcsc.com/datasheet/pdf/57d454f2d24a7e90ce02c5218e178436.pdf?productCode=C549313 (sha256 489ea64bb38044e3..., same as recorded, read online 2026-11-16)",
   pages="Table 2 p.2: 1 A1, 2 A2, 3 CC; transparent top view: pin 3 alone on one side, pins 1 (left) and 2 (right) on the other",
   compared="Board land: pad 1 (0.35,0.23), pad 2 (0.35,-0.23), pad 3 (-0.35,0): the top view turned 90 deg, not mirrored. Proxy EasyEDA land C549275 has the same numbering. "
   "Netlist 1 VB_DET, 2 BTN, 3 EN_HOLD. EasyEDA has no record of C549313 (404 again 2026-11-16 06:31 UTC)."),
 "C221907": dict(result="agrees electrically; the pad numbering differs from the maker's, the actuator side has a second source", source="C&K PTS 840 catalogue pages B-40/B-41, "
   "https://datasheet.lcsc.com/datasheet/pdf/82b5c1248b369a64727907ed223b233b.pdf?productCode=C221907 (sha256 fbe3ca6f1fd6bafc..., same as recorded)",
   pages="B-41 (p.2) top view: leads 1, 2 on the edge of ESD pin 5, leads 3, 4 on the actuator edge, actuator 1.7 mm wide opposite pin 5; schematic 1-2 and 3-4 joined; recommended layout pad 5 beside the 1-2 row",
   compared="EasyEDA C221907: pads 1, 2 at x -1.22 (y +-2.12), pads 3, 4 at x +0.28, pad 5 (ESD) at x +1.22, silk actuator outline at x -1.92..-2.56. "
   "So EasyEDA's '1-2' row is the maker's '3-4' row: the joined pairs are the same physical leads (opposite ends of one row), only the row names swap; electrically neutral (SPST). "
   "Actuator side: maker = opposite pin 5; EasyEDA pad 5 at +X -> actuator at -X, the same side as EasyEDA's actuator silk: two sources agree (actuator at EasyEDA -X = board pads 1/2, BTN_SUP side).",
   fixed="polarity gains actuator: {opposite_easyeda_pad: '5'} so cplgate can count the maker-drawing vote."),
}

def block(c, r):
    out = ["reviewed:", f"  by: {BY}", f"  date: '{DATE}'", "  human_review_required: true",
           "  note: 'ruling P-6: reviewed by an independent agent; the human check is the JLC preview row of each reference (cplgate PREVIEW)'"]
    for k in ("result", "source", "pages", "compared", "caution", "fixed"):
        if k in r:
            out.append(f"  {k}: " + yaml.safe_dump(r[k], width=150, allow_unicode=True).strip().replace("\n", "\n    ").removesuffix("\n    ...").removesuffix("..."))
    out.append("  previous: agent (datasheet transcription), 2026-11-15")
    return "\n".join(out) + "\n"

for c, r in R.items():
    p = os.path.join(D, c + ".yaml"); t = open(p).read()
    t2 = re.sub(r"(?ms)^reviewed:\n.*?(?=^board_nets:)", lambda m: block(c, r), t)
    if c == "C130414":
        t2 = t2.replace("package_drawing_page: 6", "package_drawing_page: 5").replace("land_pattern_page: 7", "land_pattern_page: 6")
        t2 = t2.replace("refs: D9; D1 (CHARGE=contacts)", "refs: D9, D11; D1 (CHARGE=contacts)")
        t2 = t2.replace("doc: BAS521 product data sheet", "doc: BAS521 product data sheet (1 July 2023)")
    if c in ("C6736531", "C896422"):
        t2 = t2.replace("polarity:\n  kind: diode\n", "polarity:\n  kind: diode\n  reference: K\n  reference_pin: '1'\n", 1)
    if c == "C221907":
        t2 = t2.replace("polarity:\n  kind: mechanical\n", "polarity:\n  kind: mechanical\n  actuator:\n    opposite_easyeda_pad: '5'\n    source: 'C&K B-41 top view: actuator opposite ESD pin 5'\n", 1)
    y = yaml.safe_load(t2)
    assert y["reviewed"]["by"] == BY and y["lcsc"] == c, c
    open(p, "w").write(t2); print(c, "ok", y["polarity"] if isinstance(y["polarity"], dict) else y["polarity"])
