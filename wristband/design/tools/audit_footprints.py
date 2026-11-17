"""Footprint audit: every JLC-placed LCSC part's EasyEDA footprint (lib/easyeda.pretty, converted 1:1 by easyeda2kicad)
against the datasheet land pattern / package drawing and the datasheet pin map (pinmap/<C>.yaml).

Automatic checks per part:
  * pad count and numbering vs the pin map (every datasheet pin number has exactly one pad; extra pads listed);
  * pin-1 / A1 location and numbering sense (counter-clockwise in the top view = not mirrored; BGA: A1 corner,
    rows and columns in top-view order);
  * EasyEDA symbol pin names vs the datasheet names (alias-normalised) -> identity agreement for cplgate G3;
  * measured land geometry (pitch, pad size, row centre distance, exposed pad) printed next to the datasheet values.
The verdict and the comparison values from the drawings are written by hand in REF below (page = cached PDF page).
Verdicts: PASS = matches the datasheet land within ~0.1 mm; PASS-NOTE = pin 1, numbering, pitch and rows correct, land
size differs but is solderable (noted, not changed); FLAG = something a human must decide before layout/order.
The EasyEDA footprints are NOT modified here: flagged items are reported, never silently fixed.
usage: python audit_footprints.py   -> design/footprint_audit.md
"""
import json, math, os, re, sys, yaml, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from kisexp import footprint_pads, symbol_pins
DESIGN = os.path.dirname(HERE)
IDX = json.load(open(os.path.join(DESIGN, "lib", "easyeda_index.json")))
PARTS = {}                                         # union over the build variants: ref (variant-tagged where it differs) -> part
for _v in ("v3f", "v3f_fldnp"):          # main variants; the gate-1 option variants use a subset of these parts (v3f_o2s1 adds C144806, C161418: audited in stage 1)
    for _r, _p in json.load(open(os.path.join(DESIGN, "out", _v, "parts.json"))).items():
        _k = _r if (_r not in PARTS or PARTS[_r]["lcsc_ref"] == _p["lcsc_ref"]) else f"{_r}[{_v}]"
        PARTS.setdefault(_k, _p)

# Datasheet land / package values (mm) and hand verdicts. ds = what the datasheet drawing gives.
REF = {
 "C506250": dict(ds="TI RGR0020A land example p.44: pad 0.24 x 0.60, pitch 0.50, pad-row centres 3.30, EP 2.05 x 2.05",
    verdict="PASS-NOTE", note="Pitch, EP 2.05 and pad inner edge (1.35) identical; EasyEDA pads 0.28 x 0.80 reach 0.2 mm further out (row centres 3.50). Pin 1 at the pin-1/pin-20 corner, CCW (drawn rotated 90 deg vs the TI view - JLC's own 0 deg)."),
 "C2842395": dict(ds="TI DRV0006A land example p.29: pad 0.30 x 0.45, pitch 0.65, rows 1.95, EP 1.00 x 1.60",
    verdict="PASS-NOTE", note="Same orientation as the TI view (pin 1 top-left, CCW); EP identical; oval pads 0.36 x 0.61 at rows 2.06 (inner edge 0.73 vs 0.75)."),
 "C3747031": dict(ds="TI DBV0005A land example p.46: pad 0.60 x 1.10, pitch 0.95, rows 2.60",
    verdict="PASS-NOTE", note="Pin 1/2/3 on one side, 4/5 opposite, CCW (rotated 90 deg). Pads 0.60 x 1.00 at rows 2.20: 0.2 mm further inboard than TI (outer edge 1.60 vs 1.85, still past the 1.45 mm lead tip)."),
 "C5443912": dict(ds="TI DDF0008A land example p.42: pad 0.45 x 1.05, pitch 0.65, rows 2.60",
    verdict="PASS-NOTE", note="Pins 1-4 / 5-8 CCW (rotated 180 deg vs TI). Pads 0.35 x 1.25 at rows 2.46 extend 0.17 mm further under the body (inner edge 0.60 vs 0.78); gap between pads 0.30."),
 "C77540": dict(ds="Nordic PS v1.4 Table 131 p.540: QFN48 6x6, e 0.40, b 0.20, L 0.35-0.45, exposed die pad D2/E2 4.50-4.70 (4.60 nom). No land pattern in the PS (Nordic reference layout not cached).",
    verdict="FLAG", note="(1) EP land 3.80 x 3.80 vs die pad 4.60 nom (0.4 mm smaller per side): solderable, but less ground/thermal contact than Nordic's layout - compare with Nordic's QFAA reference layout before layout. (2) The footprint carries 4 UNNUMBERED plated holes (0.30 drill, 0.61 pad, with paste) at +-0.5/+-0.5 inside the EP: in KiCad they get no net -> DRC 'shorting items' with EP pad 49 and solder wicking; layout must give them the GND net (or a reviewed copy must drop them). Pins 1-48 geometry, pin 1 corner and CCW numbering are correct; signal pads 0.20 x 0.67, pitch 0.40. Integrate 2026-11-12: (2) RESOLVED in lib/easyeda_rev.pretty (the 4 holes removed, EP paste 3 x 3 windows 64 %; GND POFV vias placed in the EP at layout); (1) stays OPEN for Phase B (compare with Nordic's QFAA reference layout)."),
 "C139059": dict(ds="TI RSM0032B land example p.81: pad 0.20 x 0.55, pitch 0.40, rows 3.85, EP 2.80 x 2.80",
    verdict="PASS-NOTE", note="Pin 1 corner and CCW numbering correct (rotated 90 deg). Oval pads 0.20 x 0.70 at rows 4.10 (inner edge 1.70 vs 1.65), EP 2.90 vs 2.80: EP-to-pad gap 0.25 as TI. EasyEDA SYMBOL pin names for pins 9-14 and 16 are corrupted ('32VREFP', '31VREFN', '30VCAP1', '29AVDD', '28AVSS', '27CLKSEL', '25START'): our schematic uses the datasheet names, but cplgate G3 must alias-strip the leading digits or it will report a name mismatch."),
 "C5328762": dict(ds="ADI 21-100134: 20 bumps 4 x 5, pitch 0.40, bump 0.27, body 2.048 x 1.848; land pattern per ADI AN1891 (not cached); ARCHITECTURE 5.3 intent 0.25 NSMD",
    verdict="PASS-NOTE", note="A1 top-left, rows A-D downward, columns 1-5 rightward = datasheet top view (not mirrored). Round lands 0.20 mm (vs the 0.25 mm NSMD intent in ARCHITECTURE 5.3): inside JLC's >= 0.20 BGA pad rule; confirm against AN1891 before layout."),
 "C189624": dict(ds="ST LGA-12 2.0x2.0x0.7 p.61: 12 terminals on a 4 x 4 perimeter, pitch 0.50, span 1.50, terminal ~0.25 x 0.275; land pattern only 'at www.st.com' (TN0018, not cached)",
    verdict="PASS-NOTE", note="Pin 1 corner and CCW order match Figure 2 (bottom view mirrored to top view, then rotated 90 deg). Rectangular lands 0.28 x 0.50 cover each terminal and extend 0.25 mm outward."),
 "C5220164": dict(ds="TI DQN0004A p.60-61: X2SON-4 1.0 x 1.0, pitch 0.65 (2X), leads 0.28 x 0.30, thermal pad 0.48 (diamond), pin-1 index top",
    verdict="PASS-NOTE", note="Pin 1 (OUT) top-left, 2 GND bottom-left, 3 EN bottom-right, 4 IN top-right = CCW top view as Fig. 4-3; leads drawn as custom polygons (0.36 x 0.22 each), EP 0.48 square at 45 deg as TI. EasyEDA symbol names OUT/GND/EN/IN/EP = datasheet. 4 equal leads on a 1 x 1 body: the copper set is near-symmetric, so pin-1 needs a human check in the JLC preview (pin map human_review)."),
 "C141606": dict(ds="Vishay SiP32431 p.3 Fig. 2 (SC-70-6 top view): 1 OUT, 2 GND, 3 ON/OFF | 4 IN, 5 GND, 6 N/C; pitch 0.65",
    verdict="PASS-NOTE", note="Pads 0.40 x 0.90 at rows 1.80, pitch 0.65; pin 1 at the silk-dot corner, numbering CCW (1-3 up the right side, 4-6 down the left; rotated 90 deg vs the datasheet view = JLC's own 0 deg). EasyEDA symbol names = datasheet. 6 pads in 2 x 3: 180 deg turn is geometrically silent (2F) -> G3 identity decides."),
 "C8661": dict(ds="Nexperia BAS21 p.7 SOT23 reflow footprint: land 0.60 x 0.70, pitch 1.90, rows 2.00",
    verdict="PASS-NOTE", note="A = 1, n.c. = 2 on the 2-lead side, K = 3 alone, as Table 2 p.2. Lands 1.07 x 0.60 at rows 2.48 (longer toe than Nexperia). EasyEDA symbol pins are named only '1/2/3' (no A/K): G3 cannot confirm the cathode by name -> polar pin map with human review (as BAS116 before)."),
 "C20526": dict(ds="onsemi MMBT3904 CASE 318 (SOT-23 STYLE 6): 1 base, 2 emitter, 3 collector; land 0.8 x 0.9, pitch 1.90, rows 2.0 (generic SOT-23)",
    verdict="PASS-NOTE", note="B = 1, E = 2 on the 2-lead side, C = 3 alone; EasyEDA symbol pins named B/E/C = datasheet. Lands 1.00 x 0.65 at rows 2.00. CJ's own drawing for C20526 was not downloadable (LCSC link blocked): pin map marked for human review."),
 "C2803242": dict(ds="TI DRV0006B example board layout p.41: pad 0.30 x 0.45, pitch 0.65, rows 1.95, NO thermal-pad land (p.35: thermal pad best left unsoldered)",
    verdict="PASS-NOTE", note="Pads 0.40 x 0.45 at rows 1.96, pin 1 / CCW correct. The EasyEDA footprint ADDS a 1.0 x 1.6 mm land (pad 7) with paste under the thermal pad, which TI's layout omits for best accuracy; soldered is allowed if floating or GND (datasheet). Schematic leaves pin 7 unconnected (floating island coupled to E1, R-THERM-1). RESOLVED (Integrate 2026-11-12): the board uses the reviewed copy lib/easyeda_rev.pretty with NO paste on pad 7 (copper unchanged), i.e. the thermal pad stays unsoldered as TI recommends."),
 "C5687033": dict(ds="Macronix p.81 USON-8 2x3x0.6: e 0.50, b 0.25, L 0.45, E 3.00, exposed strip D1 1.60 x E1 0.20",
    verdict="PASS", note="Pads 0.30 x 0.50 cover the 0.25 x 0.45 terminals; pad 9 = the 1.60 x 0.20 exposed strip (tied to GND per the package note). Pin 1 lower-left in the top view, CCW."),
 "C10488": dict(ds="Nexperia SOT23 reflow footprint (BAS116 p.7): land 0.60 x 0.70, pitch 1.90, rows 2.00 (Vishay doc 71196 package dims)",
    verdict="PASS-NOTE", note="G=1, S=2 on the 2-lead side, D=3 alone, not mirrored ('-BR' drawing, rotated 90 deg). Lands 0.60 x 1.00 at rows 2.30: longer toe (outer edge 1.65 vs 1.35), same inner edge."),
 "C48502": dict(ds="Nexperia SOT23 reflow footprint p.7: land 0.60 x 0.70, pitch 1.90, rows 2.00",
    verdict="PASS-NOTE", note="A=1, n.c.=2, K=3 as Table 2; geometry identical to C10488 (same EasyEDA SOT-23 drawing). Longer toe as above."),
 "C48260": dict(ds="TI DPY0002A land example p.20: pad 0.30 x 0.50, centres 0.70",
    verdict="PASS-NOTE", note="Bidirectional, electrically symmetric. EasyEDA lands 0.60 x 0.60 at centres 1.00 are about twice the TI area (gap 0.40 as TI); higher skew/tombstone risk on a 1.0 x 0.6 mm part - watch at the first article inspection."),
 "C965793": dict(ds="XINGLIGHT XL-1005UGC p.7: recommended land 0.30 x 0.55, centres 0.80 (gap 0.50); pin 1 = cathode",
    verdict="PASS-NOTE", note="EasyEDA symbol pin 1 = K, pin 2 = A = datasheet (cathode = pin 1). Lands 0.50 x 0.54 at centres 0.84 (gap 0.34 vs 0.50). Polarized: pin map needs 'reviewed: human' before the order."),
 "C511402": dict(ds="Vishay VEMD8080 p.4: 8 pads 0.54 x 0.55, x pitch 1.31/1.38/1.31, rows 2.38; pin 1 dot, pin 5 = anode",
    verdict="PASS", note="Pads 0.55 x 0.55 on exactly the datasheet grid. EasyEDA numbering = datasheet top view rotated 180 deg (pin 1 top-right, pin 5 bottom-left), not mirrored; symbol pin 5 = 'A', others 'C'. Polarized: human review required."),
 "C718072": dict(ds="YXC YSX211SL p.1 recommended land: 0.90 x 0.80, gaps 0.50 (x) / 0.30 (y); #1 lower-left, #2/#4 GND",
    verdict="PASS", note="Exact match (pads 0.90 x 0.80 at +-0.70/+-0.55), #1 lower-left, #3 upper-right, #2/#4 GND."),
 "C97604": dict(ds="SII SC-32S p.1 recommended pattern: 1.0 x 1.8, gap 1.5 (centres 2.5); 'no pattern under the crystal'",
    verdict="PASS-NOTE", note="Lands 0.85 x 1.70 at centres 2.30 (inner gap 1.45): slightly smaller. Non-polar. Layout: keep copper out from under the body (datasheet remark)."),
 "C2050114": dict(ds="TDK VLS201610CX-1 p.3 recommended land: 0.65 x 1.6, gap 0.70 (centres 1.35)",
    verdict="PASS-NOTE", note="Lands 1.00 x 1.72 at centres 1.66 (gap 0.66): 0.33 mm longer per end. Non-polar. Height 1.0 mm max (fits the 1.0 mm skin-side budget)."),
 "C434843": dict(ds="TDK VLS201610CX-1 p.3 (same family)", verdict="PASS-NOTE", note="Same EasyEDA drawing as C2050114."),
 "C2041554": dict(ds="TDK VLS201610CX-1 p.3 (same family)", verdict="PASS-NOTE", note="Same EasyEDA drawing as C2050114."),

 # ---------------- V2-B parts (datasheets in cache/v2/ds, renders in cache/v2/ds/png) ----------------
 "C509405": dict(ds="Nordic PS v1.4 Figure 3 (top view, p.15), Table 4, Table 132 / Figure 164 (p.541): 50 balls on an 8 x 7 grid, pitch 0.40, ball b = 0.20 nominal, positions B1, C1, D4, D5, E4, E5 empty; no land pattern in the PS (Nordic reference layout not cached)",
    verdict="PASS-NOTE", note="Ball names, positions and the six empty positions are identical to Figure 3: A1 top-left, columns 1-7 left to right, rows A-H downward (top view, not mirrored; render cache/v2/ds/png/nrf52832_ps_fig3_wlcsp_balls.png); pitch 0.40 x 0.40 exact; EasyEDA symbol names = Table 4 for all 50 balls. EasyEDA draws the lands 0.17 mm round, below JLC's minimum BGA pad of 0.20 mm (capability page re-read by the review 2026-11-12: 'BGA 0.2 mm; 0.2-0.25 mm BGA pad diameter requires ENIG'). REVIEW R-12, FIXED in the reviewed copy lib/easyeda_rev.pretty: every land 0.20 mm (= the nominal ball), centres and numbers unchanged, gap 0.20 mm; the board needs ENIG. Not compared with Nordic's CIAA reference layout (not cached): confirm before layout."),
 "C4371025": dict(ds="TI SBOSA81D Figure 5-1 (YBJ top view) and Table 5-1, p.3; body 0.745 x 1.508 mm (p.1). The YBJ0008 land-pattern drawing is NOT in the cached datasheet PDF (only the DDF package pages are); TI YBJ0006 drawing 4226653/A of the same family (cache/v2/ds_review/ti_mxbg457.pdf, read by the review): land 0.20 mm NSMD, ball 0.16-0.20 mm",
    verdict="PASS-NOTE", note="Ball map verified: EasyEDA = TI top view rotated 90 deg counter-clockwise, not mirrored (A1 ALERT / A2 IN+ on one short end, D1 SCL / D2 VS on the other); EasyEDA symbol names = Table 5-1 for all 8 balls; pitch 0.40. EasyEDA draws the lands 0.149 mm round, below JLC's 0.20 mm minimum BGA pad. REVIEW R-12, FIXED in the reviewed copy lib/easyeda_rev.pretty: every land 0.20 mm (TI's value for the YBJ family), centres and numbers unchanged. Not verified against the YBJ0008 drawing itself (not found): confirm before layout."),
 "C2760012": dict(ds="XySemi XB5358D0 REV0.4 p.11: SOT23-5, D 2.82-3.02, E 1.50-1.70, E1 2.65-2.95, e 0.95, e1 1.80-2.00, lead foot 0.30-0.60; no land pattern in the datasheet (TI DBV0005A example used for comparison: 0.60 x 1.10, pitch 0.95, rows 2.60)",
    verdict="PASS-NOTE", note="Pins 1-2-3 on one side, 4-5 on the other, counter-clockwise; EasyEDA symbol VT/GND/VDD/VM/VM = datasheet p.2. Lands 1.10 x 0.60 at rows 2.60, pitch 0.95 = the generic SOT-23-5 land; compared with the package dimensions, not with a vendor land drawing (none exists)."),
 "C727398": dict(ds="Vishay 'Recommended minimum pads for TDFN4 1.2 x 1.6' (doc 66558, p.14 of the cached sip32431.pdf): lands 0.30 x 0.55, pitch 0.50, centre pad 0.86 x 0.50, gaps 0.20, overall 2.0; pin configuration Fig. 3 p.3 (bottom view)",
    verdict="PASS", note="Exact match: lands 0.30 x 0.55 at +-0.25 / +-0.73, centre pad 0.86 x 0.50; pad numbers as Vishay's pattern (1, 2 on one side; 4, 3 on the other; 4 opposite 1). EasyEDA symbol 1 OUT, 2 GND, 3 IN, 4 ON/OFF, 5 GND = datasheet table. 2 x 2 lands: a 180 deg turn fits the copper -> identity by pin map + G10."),
 "C478155": dict(ds="Nexperia PMZ290UNE2 Fig. 19 reflow footprint SOT883 (p.12): lands 0.30 x 0.25 (2x) and 0.30 x 0.60, land pitch 0.70, occupied 1.3 x 0.9; pinning Table 2 p.2 (transparent top view: 1, 2 left, 3 right)",
    verdict="PASS-NOTE", note="EasyEDA = Nexperia top view rotated 180 deg, not mirrored (pin 1 G and pin 2 S keep their order). Pitch 0.70 exact; lands 0.45 x 0.25 (2x) and 0.45 x 0.70: 0.075 mm longer per end and 0.05 mm wider on the drain land than Nexperia's. Three asymmetric lands: geometry decides the rotation."),
 "C253326": dict(ds="ROHM EMX1 p.1 inner circuit; dimensions p.8 (image, not machine-readable; not compared number by number): EMT6 1.6 x 1.6 mm, pitch 0.5",
    verdict="PASS-NOTE", note="Pins 1-3 on one side, 6-4 on the other, counter-clockwise; EasyEDA symbol E1/B1/C2/E2/B2/C1 = datasheet. Lands 0.30 x 0.50, pitch 0.50, rows 1.60. Land size not compared with ROHM's drawing. The pin map is its own 180 deg image: rotation-neutral in this circuit."),
 "C130414": dict(ds="Nexperia BAS521 Fig. 10 reflow footprint SOD523 (p.6): lands 0.50 x 0.60 at centres 1.40, occupied 2.15 x 1.2; pinning Table 2 p.1: 1 = cathode",
    verdict="PASS-NOTE", note="Pad 1 = cathode ('C' in the EasyEDA symbol) = datasheet. Lands 0.60 x 0.36 at centres 1.30: 0.24 mm narrower across the body and 0.05 mm closer than Nexperia's; solderable (terminal 0.3 x 0.3). Polarized 2-terminal part: human review + electrical proof (EN hold works only one way round)."),
 "C5603826": dict(ds="ams-OSRAM CT DBLP31.12 v1.3 p.12 recommended solder pad E062.3010.218-01: lands 0.55 x 0.35 (2x, 0.34 apart) and 1.45 x 1.25, 0.25 between; p.11 pad view with anode / cathode",
    verdict="PASS", note="Exact match: lands 0.55 x 0.35 at (-0.44 / +0.45, -0.52) and 1.45 x 1.25 at (0, +0.53). Not its own 180 deg image. EasyEDA symbol: pad 1 '+', pad 2 '-', pad 3 unnamed; datasheet p.11 (pad view): anode = one small land, cathode = the other small land + the large land. Which small land is the anode rests on reading p.11 as a bottom view: human review, and the G10 LED/PD loop-back on every board."),
 "C125114": dict(ds="Lite-On LTST-S270KRKT p.8 suggested soldering pad: 1.10 x 1.10 (2x), gap 0.90 (not used after the review fix R-06)", verdict="PASS-NOTE", note="Not used any more."),
 "C598214": dict(ds="Kingbright KA-2810ASURSK p.1 recommended soldering pattern: lands 1.4 x 0.9 mm (2x), gap 1.0 mm, 0.5 mm of land beyond the body at each end; body 2.8 x 1.2 x 0.8 mm; polarity symbol: terminal 1 = cathode",
    verdict="PASS", note="Exact match: lands 1.40 x 0.90 at +-1.20 (gap 1.00) = Kingbright's pattern. EasyEDA symbol 1 = K, 2 = A = datasheet. Right-angle part with two equal lands: a 180 deg turn fits the copper, swaps the polarity AND turns the light away from the window; which side carries the lens in the EasyEDA 0 deg drawing (courtyard -0.82 ... +0.38 in y, lens outline on the -y side) was not proven against the tape drawing here -> human check in the JLC preview (lens toward the board edge) and the G10 item 'ALERT_LED on: current rises, red light at the board edge' on every board."),
 "C398713": dict(ds="Seiko SC-16S p.1 recommended soldering pattern: 0.5 x 1.0 (2x), gap 0.6, centres 1.1; 'no pattern under SC-16S'",
    verdict="PASS-NOTE", note="Lands 0.60 x 1.00 at centres 1.10 (gap 0.50): 0.05 mm wider per side than Seiko's. Non-polar."),
 "C2826523": dict(ds="BAT WIRELESS BW0025BG-L2.8W1.55H1.35: one solder pad 1.95 x 1.55 mm (not used after the review fix R-04)", verdict="PASS-NOTE", note="Not used any more (JLC: wave / manual soldering)."),
 "C2826535": dict(ds="BAT WIRELESS BW0036BG-L3.0W1.0H1.4 drawing 681-0036B-2 (p.6, render v2/design/fix/evidence/bw0036bg_p6.png): solder pad 2.30 x 1.00 mm (+-0.05), body 2.90 +-0.10 x 1.00 +-0.08, free height 1.40 +0.10/-0.05, working height 1.00, limit 0.70",
    verdict="PASS-NOTE", note="One rectangular land 2.40 x 1.20 mm against the maker's 2.30 x 1.00 mm solder area: 0.05 / 0.10 mm larger per side, solderable. EasyEDA body outline -1.95 ... +0.95 mm from the land centre (the folded end overhangs the land by 0.75 mm). 180 deg cannot be proven by pad geometry: the mating tab is specified >= 3.4 x 2.2 mm centred on the land centre so that the tip (0.6-0.8 mm from the centre) is under the tab at 0 and at 180 deg (REDESIGN 5.8 item 6); 90 deg is caught by the land shape. JLC part page 2026-11-12 23:00 UTC: SMT Assembly."),

 # ---------------- V3-F parts (datasheets read 2026-11-13; renders of the land drawings viewed in the session, not kept) ----------------
 "C5208201": dict(ds="TI SLUSDJ8A p.33 DSG0008A land example: 8 x 0.25 x 0.50 mm, pitch 0.50, pad-row centres (1.9), EP 0.9 x 1.6 (vias 0.2 optional)",
    verdict="PASS", note="EasyEDA pads 0.52 x 0.25 at x +-0.95 (row centres 1.90), pitch 0.50, EP 0.90 x 1.60: TI's land within 0.02 mm. Pin 1 top-left, 1-4 down the left, 5-8 up the right (CCW, not mirrored). "
    "EP paste of the reviewed copy: one window at 87 % (TI stencil p.34). The land fits turned 180 deg (2F): preview + G10 (e)."),
 "C2867950": dict(ds="TI SBVS277C p.40 DQN0004A land example: 4 corner pads 0.36 x 0.21 (chamfered), centres (0.86) x (0.65), centre pad 0.48 square at 45 deg",
    verdict="PASS", note="EasyEDA custom pads 1-4 at (+-0.42, +-0.33): 0.84 x 0.65 centre spacing (TI 0.86 x 0.65); centre pad 0.48 x 0.48 rotated 45 deg = TI. Pin 1 top-left, 2 bottom-left, 3 bottom-right, 4 top-right "
    "(TI Fig. 5-1). Same land as U3 (C5220164, v2). Fits turned 180 deg (2F): preview + G10 (g)."),
 "C5187176": dict(ds="TI SCES937B p.37 RUT0012A land example: 12 x 0.7 x 0.2 mm, pitch 0.4, column centres (1.4), pins 6 / 12 vertical with centres (1.7) apart; top view pins 1-5 down the left column",
    verdict="PASS-NOTE", note="EasyEDA = TI's land rotated 90 deg CCW (pins 1-5 along the bottom, 7-11 along the top, 6 right, 12 left; not mirrored): pads 0.69 x 0.20, pitch 0.40, row centres 1.40 = TI; "
    "pins 6 / 12 at x +-0.80 (TI +-0.85): 0.05 mm further in, inside the terminal length. Land symmetric on both axes: a 180 deg turn fits (2F, preview + G10 (g))."),
 "C5217869": dict(ds="TI SCES940A p.36 DRY0006A land example: 6 pads 0.3 x 0.2 at pitch 0.5, column centres (0.6); pad 1 longer (0.35) toward the centre",
    verdict="PASS", note="EasyEDA: pad 1 0.35 x 0.20 at x -0.28, pads 2-6 0.30 x 0.20 at x +-0.30, rows -0.5 / 0 / +0.5: TI's land including the longer pin-1 pad. 1-3 down the left, 4-6 up the right (CCW). "
    "The 0.05 mm longer pad 1 does not prevent a 180 deg fit (2F)."),
 "C549275": dict(ds="Nexperia SOT883 reflow footprint sot883_fr (BAV70M p.8, same package): solder lands 0.4 wide, small-land centres 0.45 apart, land rows 0.7 apart; package terminals b 0.22-0.30 (pins 1, 2), b1 0.55-0.62 (pin 3) (BAT54CM p.6)",
    verdict="FLAG", note="EasyEDA draws the small lands 0.40 x 0.16 mm, narrower than the 0.22-0.30 mm terminals. FIXED in the reviewed copy (lib/easyeda_rev.pretty): the pad set of C478155 (PMZ290UNE2YL, Nexperia SOT883, "
    "v2-reviewed: 0.45 x 0.25 / 0.45 x 0.70 mm at x +-0.35, y +-0.23) with the same numbers, orientation (pad 3 at -x) and origin, so JLC's centroid and 0 deg are those of the C549275 record. "
    "Three unequal lands: a turn does not fit (1F, placement_proof)."),
 "C549313": dict(ds="Nexperia BAV70M p.7-8: SOT883 outline and sot883_fr footprint (as C549275)",
    verdict="PASS-NOTE", note="No EasyEDA footprint exists for C549313 (API 404, 2026-11-13 20:41 UTC). The board uses the reviewed C549275 land (same Nexperia SOT883, pins 1 / 2 small lands, 3 large land, BAV70M p.2). "
    "Geometry proves the orientation (1F), but JLC's library 0 deg for C549313 cannot be compared with an EasyEDA record: the JLC preview of the cathode (large) land is mandatory, plus G10 (f)."),
 "C20345399": dict(ds="TI SLVSH10C p.19 DPY0002A land example: 2 pads 0.3 x 0.5 mm, centres (0.7)",
    verdict="PASS-NOTE", note="EasyEDA pads 0.60 x 0.60 at x +-0.50: same inner edge (0.20) as TI, outer edge 0.30 mm further out; symmetric, bidirectional part (class N). Solderable; larger fillet area."),
 "C896422": dict(ds="onsemi NSR0240MX2 p.4 case 714AB recommended footprint: 2 pads 0.47 x 0.60, outer span 1.20 (centres +-0.365); terminals e 0.65, L 0.20-0.30, b 0.45-0.55",
    verdict="PASS-NOTE", note="EasyEDA pads 0.30 x 0.55 at x +-0.33: smaller than onsemi's (0.47 x 0.60) but covering the terminal (|x| 0.20-0.45). Pad 1 = cathode at +x. 2-pad polar part: 180 deg fits (class P): "
    "preview of the cathode mark + G10 (e) (a reversed D14 blocks the head: no /PG, no current)."),
 "C6736531": dict(ds="Nexperia PMEG10020AELR (1 January 2023) Fig. 17 p.10 reflow footprint SOD123W: solder lands 1.2 x 1.2 at centres 2.8 (gap 1.6, outer 4.0), paste 1.1, "
    "resist 1.4, occupied 4.4 x 2.1; Fig. 16 p.9: leads 0.75-1.05 wide, 0.3-0.6 long, 3.3-3.7 overall, body 1.5-1.9 wide, 0.9-1.1 high; Table 2 p.2: pin 1 = cathode (marking bar)",
    verdict="PASS", note="[S2b E-4] EasyEDA C6736531 (SOD-123F_L2.8-W1.8-LS3.7) draws pads 1.00 x 1.20 at x +-1.65 (gap 2.30, outer 4.30): its inner edge 1.15 sits outside the shortest "
    "lead's inner end (1.05), so the land was replaced by Nexperia's (2 pads 1.2 x 1.2 at +-1.40) and checked pad by pad below (MAKER LAND). Pad 1 = cathode at -x, as EasyEDA's silk bar. "
    "2-pad polar part (class P): JLC preview of the cathode bar + G10 (e)."),
 "C324723": dict(ds="Hirose FH34 catalogue Oct. 2022 (Farnell 3932894.pdf, read 2026-11-15) p.8-9 recommended PCB mounting pattern, 10 pos: contact pads 0.3 +-0.05 x 0.8 +-0.05 at 0.5, "
    "B 4.5 (pad 1 .. 10 centres); retention-tab pads between E 6.1 and F 6.9 (0.4 wide, centres +-3.25), 0.8 long; 3.3 +-0.05 from the outer edge of the contact row to the "
    "outer edge of the tab pads (centres 2.5 apart); contact No.1 at the right end of the row seen from above with the row at the top (p.6, p.8); body A 7.0 +-0.15 x depth 3.8 x 1.0 (p.6)",
    verdict="PASS", note="[S2a] EasyEDA C324723 checked pad by pad against Hirose p.8-9: pads 1-10 0.30 x 0.80 at x +2.25 .. -2.25 step 0.5, y -1.25 (row outer edge -1.65); "
    "pads 11 / 12 0.40 x 0.80 at x -/+3.25, y +1.25 (outer edge +1.65): overall 3.30, E 6.10, F 6.90, B 4.50 as drawn; pad 1 at +x = contact No.1. "
    "Courtyard rebuilt from the body box (the EasyEDA courtyard missed the lead row). A 180 deg turn puts the 10-pad row on the 2 tab pads (class 1F)."),
 "C221907": dict(ds="C&K PTS840 datasheet p.2 (B-41) 'RECOMMENDED PCB LAYOUT', G leads (LCSC copy of C221907, re-read 2026-11-15): 5 +-0.1 over the pads across the leads, gap 2.2 +-0.1 "
    "-> pads 1.40 long at +-1.80; 2.5 +-0.1 along the actuation axis, gap 0.4 +-0.1 -> pads 1.05 wide at +-0.725 about the lead line; lead tips 4.7 apart, lead rows 1.5 +-0.1; "
    "body 3.5 x 2.9, actuator 1.7 x 0.65; ESD pad 5 (1.1 x 0.5) only on ESD versions",
    verdict="PASS", note="[G1 level 0] The reviewed copy now carries C&K's own land, checked pad by pad below (tools/review_footprints.py SET_PAD): pads 1.05 x 1.40 mm at "
    "x -1.195 / +0.255 (lead line x -0.47 +- 0.725), y +-1.80 in the EasyEDA frame (actuation axis = x, actuator at -x). Origin, 0 deg and pad numbers are EasyEDA's (JLC's centroid). "
    "Lead foot (1.75-2.35 mm from the centre line) lies fully on the pad (1.10-2.50): toe 0.15 mm, heel under the body 0.65 mm. The raw EasyEDA land was 0.84 x 1.785 at y +-2.12 (span 6.03 mm). "
    "EasyEDA numbers the C&K positions 4, 3, 2, 1: the joined pairs {1,2} and {3,4} coincide, so the switch connects the same two nets. Pad 5 stays deleted (GK has no pin 5, S1 D-9). "
    "Courtyard 4.04 x 5.50 mm = 22.2 mm2 (stage 1: 4.04 x 6.54 = 26.4). Mechanically polar (class M): the actuator must face the wall in the JLC preview."),
 "C2876045": dict(ds="TI SLVSE13J p.54 DPW0005A land example: 4 corner pads 0.42 x 0.22, column centres (0.78), row centres (0.48), centre pad 0.25 square at 45 deg; Fig. 4-4: 1 OUT top-left, 2 VCC bottom-left, "
    "3 VEE centre, 4 IN- bottom-right, 5 IN+ top-right",
    verdict="PASS-NOTE", note="Geometry = TI (pads at x +-0.39, y +-0.24, centre pad 0.25 at 45 deg). NUMBERING DIFFERS: EasyEDA pad 3 = bottom-right (TI pin 4 IN-), pad 4 = top-right (TI pin 5 IN+), pad 5 = centre (TI pin 3 VEE); "
    "its symbol names the pads OUT, VCC, IN-, IN+, VEE, i.e. the same function on the same position. pinmap/C2876045.yaml follows the PAD numbers with TI's functions mapped by position (both numbers in the text): "
    "the netlist puts VEE on the centre pad, IN- bottom-right, IN+ top-right."),
 "C2863637": dict(ds="TI SLVSE13J p.3 Fig. 4-1 / Table 4-1 (TLV70x1 North-West pinout, DBV/DCK): 1 OUT, 2 V-, 3 IN+, 4 IN-, 5 V+; p.60 DCK0005A land example: 5X 0.95 x 0.40, pitch 0.65, row centres 2.2 (pads at x +-1.10)",
    verdict="PASS", note="[ECO3] EasyEDA C2863637: 5 pads 0.90 x 0.40 at x +-1.10, y 0 / +-0.65 (TI 0.95 x 0.40: 0.05 mm shorter, same centres). Numbering = TI: 1 (1.10, 0.65) OUT, 2 (1.10, 0) V-, 3 (1.10, -0.65) IN+, 4 (-1.10, -0.65) IN-, 5 (-1.10, 0.65) V+; EasyEDA symbol names 1 OUT, 2 GND, 3 IN+, 4 IN-, 5 VCC (same functions, same numbers). Every pad has a free outer end (escape outward); side gaps 0.25 mm."),
 "C478207": dict(ds="Nexperia PMZ350UPE p.2 pinning, SOT883 (as PMZ290UNE2)",
    verdict="PASS-NOTE", note="Same land and numbering as C478155 (PMZ290UNE2YL, v2): pads 0.40 x 0.25 at (+0.35, +-0.23), 0.40 x 0.70 at (-0.35, 0); 1 G, 2 S, 3 D. Three unequal lands (1F)."),
 "C17913": dict(ds="1206 chip resistor (UNI-ROYAL 1206W4F120JT5E, 250 mW)", verdict="PASS", note="EasyEDA R1206 land 1.21 x 1.70 at +-1.48: standard IPC 1206 land; non-polar."),
 "C17445": dict(ds="0805 chip resistor (UNI-ROYAL 0805W8F120JT5E, 125 mW; datasheet V.9 p.4: 2.00 x 1.25 x 0.55 mm, terminations 0.40 +-0.20)", verdict="PASS",
    note="[G1 level 0] EasyEDA R0805 land (measured values in the table below): standard chip land for a 2.0 x 1.25 mm body; non-polar."),
 # [S2c] lid antenna L1 and F-8 (v3/stage2c/ECO2C.md); datasheets read 2026-11-15 from the LCSC copies, not kept in the project
 "C6652901": dict(ds="Murata LQW15AN_80 reference spec JELF243A_0100H-01 section 12.1 p.13: reflow land a (gap) 0.6, b (outer) 1.42, c (width) 0.66; body 1.0 x 0.6 x 0.5 (+-0.1), electrodes 0.2 +-0.1 (section 5 p.8)",
    verdict="PASS", note="[S2c] C215 9.0 nH LQW15AN9N0G80D. EasyEDA draws 0.50 x 0.648 at +-0.43 (gap 0.36, outer 1.36); the old C215 land (C2220990) was 0.50 x 0.54 at +-0.42 "
    "(gap 0.34, outer 1.34). Both have half Murata's gap. Replaced by Murata's land (0.41 x 0.66 at +-0.505) and checked pad by pad below (MAKER LAND). Non-polar."),
 "C668465": dict(ds="Murata LQW15AN_80 reference spec JELF243A_0100H-01 section 12.1 p.13 (same series as C6652901): a 0.6, b 1.42, c 0.66",
    verdict="PASS", note="[S2c] L204 6.2 nH LQW15AN6N2B80D. EasyEDA and the old L204 land (C521065) are both 0.54 x 0.54 at +-0.42 (gap 0.30, outer 1.38, width 0.54): "
    "gap 0.30 below Murata's 0.60, width 0.12 short. Replaced by Murata's land (0.41 x 0.66 at +-0.505), checked pad by pad below (MAKER LAND). Non-polar."),
 "C2048575": dict(ds="Murata LQW15AN_80 reference spec JELF243A_0100H-01 section 12.1 (same series as C6652901): a 0.6, b 1.42, c 0.66",
    verdict="PASS", note="[F] C215 7.6 nH LQW15AN7N6G80D (RF_FINAL re-tune). Same Murata land as C6652901 (0.41 x 0.66 at +-0.505), checked pad by pad below (MAKER LAND). Non-polar."),
 "C471381": dict(ds="Murata LQW15AN_80 reference spec JELF243A_0100H-01 section 12.1 (same series as C6652901): a 0.6, b 1.42, c 0.66",
    verdict="PASS", note="[F] L204 4.3 nH LQW15AN4N3B80D (RF_FINAL re-tune). Same Murata land as C668465 (0.41 x 0.66 at +-0.505), checked pad by pad below (MAKER LAND). Non-polar."),
 "C2826516": dict(ds="BAT WIRELESS BW0019BG-L3.5W1.5H3.8 datasheet April-14-2025-A01, drawing 681-0019B-2 (p.6, image read by eye): solder pad 2.10 x 1.50 (+-0.05), body 3.50 +-0.10 x 1.50 +-0.08; "
    "free height 3.80 +0.10/-0.05, normal working height 3.00, limit working height 2.50; force 60-80 gf (note 7); contact apex 0.90 +-0.15 from the pad end",
    verdict="PASS-NOTE", note="[S2c] J40. EasyEDA land 2.10 x 1.50 = the maker's solder pad exactly. The land is ALSO part of AE1's FEED copper (same net). HEIGHT: the board-to-glass "
    "distance 2.445-2.545 mm lies at / below the 2.50 limit height: see ECO2C.md (drop-in BW0020AG C2826518: same pad, working 2.50, limit 2.00)."),
 "C2826518": dict(ds="BAT WIRELESS BW0020AG-L3.5W1.5H3.0 drawing (read by eye in stage 2c, v3/stage2c/ECO2C.md 2): same solder pad and body as BW0019BG; free height 3.00, working 2.50, limit 2.00",
    verdict="PASS-NOTE", note="[S2d J-1] J40. No EasyEDA record fetched in stage 2d: the board keeps the reviewed C2826516 land (2.10 x 1.50 = the BW0019BG / BW0020AG solder pad), "
    "as LEAD_NOTES 2j J-1 rules (same land, position and rotation). Open: EasyEDA / JLC footprint check of C2826518 and the JLC preview (rot 340)."),
 "C504101": dict(ds="JSCJ CJBA7002K Rev 1.0 p.1 top view (D large; S, G small), p.4 X1-DFN1006-3 outline: D 1.00, E 0.60, b1 0.10-0.20, b2 0.45-0.55, L1 = L2 0.20-0.30, L3 0.40, e 0.35",
    verdict="PASS-NOTE", note="[S2c F-8] Q20. EasyEDA lands 0.45 x 0.25 (2x) at (-0.35, +-0.23) and 0.45 x 0.70 at (+0.35, 0) = the C478155 (PMZ290UNE2) land turned 180 deg, pad for pad "
    "(same G / S positions after the turn). Terminals (|x| 0.25-0.50, small |y| 0.10-0.25) lie inside the lands. JLC 0 deg of C504101 = C478155 + 180 deg."),
}
GENERIC = dict(verdict="PASS", note="Standard chip land (EasyEDA C0201/L0201/C0402/R0402/L0402/C0603/R0603/L0603 drawing), non-polar; body size matches the part's case code. Not compared with a vendor land drawing.")

def norm(s, two_pin=False):
    s = (s or "").upper().replace("~{", "").replace("}", "").replace("#", "").replace(" ", "").replace("–", "-")
    s = re.sub(r"^\d+(?=[A-Z])", "", s)          # tolerate EasyEDA's '32VREFP' corruption only for the alias check
    if s == "C" and not two_pin: return "C"      # 'C' = cathode only on 2-pin symbols (cplgate spec); on a BJT it is the collector
    return {"N.C.": "NC", "NC": "NC", "C": "K", "CATHODE": "K", "ANODE": "A", "EP": "EP", "POWERPAD": "EP", "THERMALPAD": "EP",
            "VSS": "VSS", "#1": "1", "#2": "2", "#3": "3", "#4": "4"}.get(s, s)

def tokens(title):
    t = re.findall(r"-(TL|TR|BL|BR)(?:-|$)", title); return t[0] if t else "-"

def perimeter_sense(pads, nums):
    """Signed area of the pad-centre polygon in pin order (y up). >0 = CCW top view (not mirrored)."""
    pts = [(p["x"], -p["y"]) for n in nums for p in pads if p["num"] == n]
    if len(pts) < 3: return None
    a = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    return a

def corner(p, pads):
    cx = sum(q["x"] for q in pads) / len(pads); cy = sum(q["y"] for q in pads) / len(pads)
    return ("top" if p["y"] < cy - 1e-6 else "bottom" if p["y"] > cy + 1e-6 else "mid") + "-" + ("left" if p["x"] < cx - 1e-6 else "right" if p["x"] > cx + 1e-6 else "mid")

def geom(pads, pm_nums):
    sig = [p for p in pads if p["num"] in pm_nums and max(p["w"], p["h"]) < 1.5]
    if len(sig) < 2: return ""
    def eff(p):
        w, h = (p["h"], p["w"]) if abs(p["rot"]) % 180 == 90 else (p["w"], p["h"]); return w, h
    sizes = sorted({tuple(round(v, 3) for v in sorted(eff(p))) for p in sig})
    xs = sorted({round(p["x"], 3) for p in sig}); ys = sorted({round(p["y"], 3) for p in sig})
    span = max(xs[-1] - xs[0], ys[-1] - ys[0])
    ep = [p for p in pads if max(p["w"], p["h"]) >= 0.9 and p not in sig and p["num"]]
    eps = ", EP " + " / ".join(f"{p['w']:.2f} x {p['h']:.2f} (#{p['num']})" for p in ep) if ep else ""
    return f"pads {' / '.join(f'{a:.2f} x {b:.2f}' for a, b in sizes)}; centre span {span:.2f}{eps}"

rows, lines = [], []
by_c = {}
for ref, p in PARTS.items():
    if p["lcsc"]: by_c.setdefault(p["lcsc"], []).append(ref)
for ref, p in PARTS.items():                      # DNP parts keep their pads: audit their footprints too
    if p["dnp"] and p["lcsc_ref"]: by_c.setdefault(p["lcsc_ref"], []).append(ref + "(DNP)")
counts = {"PASS": 0, "PASS-NOTE": 0, "FLAG": 0}
for c in sorted(by_c, key=lambda c: (c not in REF, c)):
    if c in IDX and "footprint" in IDX[c]:
        e = IDX[c]; fpfile = os.path.join(DESIGN, "lib", "easyeda.pretty", e["footprint"].split(":")[1] + ".kicad_mod")
        if "package_title" not in e: e = dict(e, package_title="PROXY of " + e.get("proxy_of", "?") + " (no EasyEDA record)")   # [ECO3] C549313 proxy entry (P-6) has no package_title
    else:                                      # [V3F] no EasyEDA record (C549313): audit the derived reviewed land
        fpn = [p for p in PARTS.values() if p["lcsc_ref"] == c][0]["footprint"].split(":")[1]
        e = dict(title="(no EasyEDA record)", footprint="easyeda_rev:" + fpn, package_title="SOT883 (derived)", symbol=None, model3d=None)
        fpfile = os.path.join(DESIGN, "lib", "easyeda_rev.pretty", fpn + ".kicad_mod")
    pads = footprint_pads(fpfile); numbered = [p for p in pads if p["num"]]
    sym = {s["num"]: s["name"] for s in (symbol_pins(os.path.join(DESIGN, "lib", "easyeda.kicad_sym"), e["symbol"]) or [])} if e["symbol"] else {}
    pmf = os.path.join(DESIGN, "pinmap", f"{c}.yaml")
    pm = yaml.safe_load(open(pmf)) if os.path.exists(pmf) else None
    checks = []
    if pm:
        pm_nums = [str(k) for k in pm["pins"]]
        pad_nums = [p["num"] for p in numbered]
        missing = [n for n in pm_nums if pad_nums.count(n) != 1]
        extra = sorted({n for n in pad_nums if n not in pm_nums})
        unnamed = len(pads) - len(numbered)
        checks.append("pads = pin map" if not missing and not extra else f"PAD MISMATCH missing {missing} extra {extra}")
        if unnamed: checks.append(f"{unnamed} UNNUMBERED pads")
        tp = len(pm_nums) == 2
        agree = [n for n in pm_nums if norm(sym.get(n), tp) == norm(pm["pins"][n]["name"], tp) or norm(sym.get(n), tp) in norm(pm["pins"][n]["name"], tp).split("/")]
        checks.append(f"symbol names agree {len(agree)}/{len(pm_nums)}")
        dis = [f"{n}: EasyEDA '{sym.get(n)}' vs DS '{pm['pins'][n]['name']}'" for n in pm_nums if n not in agree]
        p1 = [p for p in numbered if p["num"] in ("1", "A1")]
        if p1 and len(numbered) > 2: checks.append(f"pin {p1[0]['num']} at {corner(p1[0], numbered)}")
        perim = [n for n in pm_nums if re.fullmatch(r"\d+", n) and pm["pins"][n]["name"] not in ("PowerPAD", "PowerPad", "ThermalPad", "EP")]
        if c in ("C77540",): perim = [str(i) for i in range(1, 49)]
        if len(perim) >= 4 and c not in ("C511402", "C718072", "C5603826"):
            a = perimeter_sense(pads, perim); checks.append("numbering CCW (not mirrored)" if a and a > 0 else "numbering CW = MIRRORED")
        if c == "C5328762":
            g = {p["num"]: p for p in numbered}
            ok = g["A1"]["x"] < g["A5"]["x"] and g["A1"]["y"] < g["D1"]["y"]
            checks.append("A1 top-left, cols 1-5 left->right, rows A-D downward (top view, not mirrored)" if ok else "BGA ORIENTATION MISMATCH")
        if c == "C509405":
            g = {p["num"]: p for p in numbered}
            ok = g["A1"]["x"] < g["A7"]["x"] and g["A1"]["y"] < g["H1"]["y"] and not ({"B1", "C1", "D4", "D5", "E4", "E5"} & set(g))
            checks.append("A1 top-left, cols 1-7 left->right, rows A-H downward, B1/C1/D4/D5/E4/E5 empty (PS Figure 3 top view, not mirrored)" if ok else "WLCSP ORIENTATION MISMATCH")
        if c == "C4371025":
            g = {p["num"]: p for p in numbered}       # TI top view (A1 top-left, column 2 right) rotated 90 deg CCW: A1 bottom-left, A2 top-left, D1 bottom-right
            ok = g["A1"]["x"] < g["D1"]["x"] and g["A1"]["y"] > g["A2"]["y"] and abs(g["A1"]["x"] - g["A2"]["x"]) < 1e-6
            checks.append("ball map = TI Figure 5-1 top view rotated 90 deg CCW (not mirrored)" if ok else "DSBGA ORIENTATION MISMATCH")
        if c == "C511402":
            g = {p["num"]: p for p in numbered}
            ok = g["1"]["y"] == g["4"]["y"] and g["5"]["y"] == g["8"]["y"] and (g["1"]["x"] - g["4"]["x"]) * (g["8"]["x"] - g["5"]["x"]) > 0 and abs(g["1"]["x"] - g["5"]["x"]) > 3
            checks.append("pin 1 and pin 5 at opposite corners, rows 1-4 / 5-8 antiparallel (datasheet order, 180 deg)" if ok else "PD PIN ORDER MISMATCH")
        geo = geom(pads, set(pm_nums))
    else:
        dis, geo = [], geom(pads, {p["num"] for p in pads})
    r = REF.get(c, GENERIC); counts[r["verdict"]] += 1
    rows.append((c, e.get("title"), ", ".join(by_c[c]), e["package_title"], r["verdict"]))
    lines.append(f"### {c} {e.get('title')} - {', '.join(by_c[c])} - **{r['verdict']}**\n")
    lines.append(f"- EasyEDA footprint `{e['footprint']}` (package `{e['package_title']}`, corner token `{tokens(e['package_title'])}`), "
                 f"{len(pads)} pads; 3D `{e.get('model3d')}`")
    if pm: lines.append(f"- Datasheet: {pm['datasheet']['doc']}, pin table {pm['datasheet']['pin_table']}; pin 1: {pm['pin1_marker']}")
    if "ds" in r: lines.append(f"- Datasheet land/package: {r['ds']}")
    lines.append(f"- EasyEDA measured: {geo}")
    if checks: lines.append(f"- Automatic checks: {'; '.join(checks)}")
    if dis: lines.append(f"- Symbol name differences (informational, schematic uses datasheet names): {'; '.join(dis[:12])}{' ...' if len(dis) > 12 else ''}")
    lines.append(f"- Verdict: **{r['verdict']}** - {r['note']}\n")

hdr = f"""# SolarBand V3-F main board - EasyEDA footprint audit (both build variants)

Generated {datetime.date.today().isoformat()} by `v3/design/tools/audit_footprints.py` from `lib/easyeda.pretty` (easyeda2kicad output of the
EasyEDA records; V3-F raw records are kept outside the project) and `pinmap/<C>.yaml`. The board uses the reviewed copy
`lib/easyeda_rev.pretty` whose numbered copper pads are verified identical to these (last section), so KiCad's pad geometry
and 0 deg are JLC's own (ARCHITECTURE 10.1). Nothing below was edited to make it pass.

Verdicts: **PASS** = matches the datasheet land within ~0.1 mm; **PASS-NOTE** = pin 1, numbering, pitch and rows correct,
land size differs from the vendor drawing but is solderable (noted, not changed); **FLAG** = a human decision is needed
before layout / order.

Totals: {counts['PASS']} PASS, {counts['PASS-NOTE']} PASS-NOTE, {counts['FLAG']} FLAG (over {len(by_c)} distinct LCSC parts incl. DNP pads). [V3F] The FLAG is the raw EasyEDA land of C549275; the board uses the corrected copy (C478155 SOT883 pad set), see its entry and the reviewed-copy table.

V2-B: the parts that are new against v1 are C509405, C4371025, C2760012, C727398, C478155, C253326, C130414, C5603826, C598214,
C398713, C2826535 and the 0201 / 0402 / 0603 passives with new C-numbers; their datasheet land drawings were read on 2026-11-12 (renders in
`cache/v2/ds/png/` and `v2/design/fix/evidence/`). A footprint whose land could not be compared with a vendor drawing says so in its note;
FLAG = not usable as it is. After the independent review (R-04, R-06, R-12): spring finger C2826523 -> C2826535, warning LED C125114 -> C598214,
and the lands of the two 0.4 mm BGA-class parts are 0.20 mm in the reviewed copy (see the last section).

V3-F (2026-11-13): new parts C5208201, C2867950, C5187176, C5217869, C549313, C549275, C20345399, C896422, C221907, C2876045, C478207, C17913 and 0201 / 0402
passives. Their land drawings were read on 2026-11-13 from the maker datasheets (URL, page and sha256 in pinmap/<C>.yaml; renders viewed in the session, not kept).
Two findings: the EasyEDA numbering of TLV7031DPWR (C2876045) differs from TI's (mapped by position in the pin map), and the BAT54CM (C549275) small lands are too
narrow (copper replaced by the reviewed SOT883 pad set, the second permitted copper change); BAV70M (C549313) has no EasyEDA record (derived land, preview mandatory).

| LCSC | Part | Refs | EasyEDA package | Verdict |
|---|---|---|---|---|
""" + "\n".join(f"| {a} | {b} | {c_} | {d} | {v} |" for a, b, c_, d, v in rows) + "\n\n## Per-part detail\n\n"
# reviewed copy (tools/review_footprints.py): numbered copper pads must be identical to the raw conversion
rev_lines = ["\n## Reviewed copy used by the board (`lib/easyeda_rev.pretty`)\n",
             "Generated by `tools/review_footprints.py` (Integrate 2026-11-12; land diameter added by the V2-B review fix). Numbered copper pads are compared with the raw "
             "easyeda2kicad output below; only paste, unnumbered EP via holes (U6), courtyards and the duplicate `LCSC Part` "
             "field differ, plus the land DIAMETER of C509405 and C4371025 (0.17 / 0.149 -> 0.20 mm, review R-12: number, centre, rotation and shape of every pad are checked identical). "
             "Full change list: `lib/easyeda_rev_manifest.json`.\n", "| Footprint | Numbered copper pads | Changes |", "|---|---|---|"]
man = json.load(open(os.path.join(DESIGN, "lib", "easyeda_rev_manifest.json")))["footprints"]
bad = 0
COPPER_FIXED = {"C549275": "SOT883 pad set of C478155 (FLAG fixed)"}     # [V3F] permitted copper change: BAT54CM small lands (see its audit entry)
PADS_DROPPED = {}
# [G1 level 0] SW1 on the maker's land: the reviewed copy must equal C&K's recommended PCB layout pad by pad (numbers as EasyEDA, pad 5 deleted).
# Expected values = C&K PTS840 p.2 (B-41): pads 1.05 x 1.40 at lead line (x -0.47) +-0.725, y +-1.80.
MAKER_LAND = {"C6736531": ({"1": (-1.40, 0.0, 1.20, 1.20), "2": (1.40, 0.0, 1.20, 1.20)}, set(),
                           "Nexperia PMEG10020AELR Fig. 17 SOD123W reflow land (1.2 x 1.2 at 2.8 centres) [S2b E-4]"),
              "C324723": ({**{str(i): (round(2.75 - 0.5 * i, 3), -1.25, 0.30, 0.80) for i in range(1, 11)}, "11": (-3.25, 1.25, 0.40, 0.80), "12": (3.25, 1.25, 0.40, 0.80)}, set(),
                          "Hirose FH34 p.8-9 recommended pattern, 10 pos (B 4.5, E 6.1, F 6.9, 3.3 overall) [S2a]"),
              "C221907": ({"1": (-1.195, 1.80, 1.05, 1.40), "2": (-1.195, -1.80, 1.05, 1.40), "3": (0.255, 1.80, 1.05, 1.40), "4": (0.255, -1.80, 1.05, 1.40)}, {"5"},
                          "C&K PTS840 B-41 recommended PCB layout (4 pads 1.05 x 1.40 mm); pad 5 (ESD-pin land) deleted: GK has no pin 5 [S1 D-9]"),
              "C6652901": ({"1": (-0.505, 0.0, 0.41, 0.66), "2": (0.505, 0.0, 0.41, 0.66)}, set(), "Murata LQW15AN JELF243A 12.1 land (a 0.6, b 1.42, c 0.66) [S2c]"),
              "C668465": ({"1": (-0.505, 0.0, 0.41, 0.66), "2": (0.505, 0.0, 0.41, 0.66)}, set(), "Murata LQW15AN JELF243A 12.1 land (a 0.6, b 1.42, c 0.66) [S2c]"),
              "C2048575": ({"1": (-0.505, 0.0, 0.41, 0.66), "2": (0.505, 0.0, 0.41, 0.66)}, set(), "Murata LQW15AN JELF243A 12.1 land (a 0.6, b 1.42, c 0.66) [F]"),
              "C471381": ({"1": (-0.505, 0.0, 0.41, 0.66), "2": (0.505, 0.0, 0.41, 0.66)}, set(), "Murata LQW15AN JELF243A 12.1 land (a 0.6, b 1.42, c 0.66) [F]")}
for c in sorted(by_c):
    if c not in IDX or "footprint" not in IDX[c]:  # [V3F] derived land without an EasyEDA record (C549313: EasyEDA answers 404)
        fpn = [p for p in PARTS.values() if p["lcsc_ref"] == c][0]["footprint"].split(":")[1] + ".kicad_mod"
        ch = [x for x in man.get(fpn, {}).get("changes", []) if not x.startswith("stripped")]
        rev_lines.append(f"| {fpn} | derived (no EasyEDA record) | {'; '.join(ch)} |"); continue
    fpn = IDX[c]["footprint"].split(":")[1] + ".kicad_mod"
    a = sorted((p["num"], p["x"], p["y"], p["w"], p["h"], p["rot"], p["shape"]) for p in footprint_pads(os.path.join(DESIGN, "lib", "easyeda.pretty", fpn)) if p["num"])
    b = sorted((p["num"], p["x"], p["y"], p["w"], p["h"], p["rot"], p["shape"]) for p in footprint_pads(os.path.join(DESIGN, "lib", "easyeda_rev.pretty", fpn)) if p["num"])
    same = a == b
    LAND = {"C509405": 0.20, "C4371025": 0.20}          # review R-12: the only permitted copper difference is the land diameter of these two parts
    if not same and c in LAND:
        pos_same = [(q[0], q[1], q[2], q[5], q[6]) for q in a] == [(q[0], q[1], q[2], q[5], q[6]) for q in b]
        dia_ok = all(abs(q[3] - LAND[c]) < 1e-6 and abs(q[4] - LAND[c]) < 1e-6 for q in b)
        txt = f"numbers, centres, rotation and shape identical ({len(a)}); land diameter {a[0][3]:.3f} -> {LAND[c]:.2f} mm" if (pos_same and dia_ok) else "**DIFFERENT**"
        bad += not (pos_same and dia_ok)
    elif c in MAKER_LAND:
        exp, dropped, why = MAKER_LAND[c]
        nums_ok = sorted(q[0] for q in a if q[0] not in dropped) == sorted(q[0] for q in b) == sorted(exp)
        geo_ok = all(abs(q[1] - exp[q[0]][0]) < 1e-3 and abs(q[2] - exp[q[0]][1]) < 1e-3 and abs(q[3] - exp[q[0]][2]) < 1e-3 and abs(q[4] - exp[q[0]][3]) < 1e-3 for q in b) if nums_ok else False
        # side of each pad (sign of x about the lead line, sign of y) must be EasyEDA's: the numbering sense is unchanged
        xl = -0.47 if c == "C221907" else 0.0      # [S2c] lead line of SW1 only; 2-pad chip lands are split at x = 0
        side_ok = all((q[1] > xl) == (next(r for r in a if r[0] == q[0])[1] > xl) and (q[2] > 0) == (next(r for r in a if r[0] == q[0])[2] > 0) for q in b) if nums_ok else False
        txt = (f"MAKER LAND: pads {', '.join(q[0] for q in b)} = {why}; each pad on the same side as EasyEDA's (numbering unchanged)" if (nums_ok and geo_ok and side_ok) else "**DIFFERENT**")
        bad += not (nums_ok and geo_ok and side_ok)
    elif not same and c in PADS_DROPPED:
        a_keep = [q for q in a if q[0] not in PADS_DROPPED[c][0]]
        ok_ = a_keep == b
        txt = (f"pads {', '.join(q[0] for q in b)} identical; pad(s) {', '.join(sorted(PADS_DROPPED[c][0]))} deleted: {PADS_DROPPED[c][1]}" if ok_ else "**DIFFERENT**")
        bad += not ok_
    elif not same and c in COPPER_FIXED:
        txt = f"numbers identical ({len(a)}), copper replaced: {COPPER_FIXED[c]}"; bad += [q[0] for q in a] != [q[0] for q in b]
    else:
        txt = "identical (" + str(len(a)) + ")" if same else "**DIFFERENT**"; bad += not same
    ch = [x for x in man.get(fpn, {}).get("changes", []) if not x.startswith("stripped")]
    rev_lines.append(f"| {fpn} | {txt} | {'; '.join(ch)} |")
if bad: raise SystemExit(f"reviewed footprints changed copper for {bad} parts")
open(os.path.join(DESIGN, "footprint_audit.md"), "w").write(hdr + "\n".join(lines) + "\n".join(rev_lines) + "\n")
print(counts)
