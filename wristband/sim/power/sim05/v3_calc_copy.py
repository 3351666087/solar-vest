#!/usr/bin/env python3
"""DECIDE-STAGE COPY of v3/integrate/v3_calc.py (2026-11-13, lead synthesis). Changed lines are marked DECIDE COPY:
the energy import path (read-only import of v3/integrate/energy/v3_energy.py), a guard that never rewrites the integrate
energy cache and never recomputes it, and the output file (calc/v3_calc_copy.json in v3/decide/). Everything else is unchanged.
SolarBand V3 integrate stage: reproducible calculation behind v3/V3_ARCH.md.

Run:  python3 -B /path/to/SolarVest_work/wristband/v3/integrate/v3_calc.py [--force]
      (--force recomputes the PV tables in energy/v3_energy.py, about 3 min; otherwise its cache is used if the inputs match)
Writes: v3/integrate/v3_calc.json (and nothing else). Reads read-only: v2/design/parts.json, the three lane JSON files,
        redesign/v2_calc.json (through the copy in energy/), wrist_light.json of the strap lane (through the copied strap_iv.py).
Markers in the JSON: 'V' = read in a source today or a project file (source named), 'E' = estimate / model output (method named),
        'U' = unknown. Nothing here is a SIM-xx run; every thermal, RF and energy number is a planning estimate.
The band harvests light. Nothing here is wireless power transfer.
V3 FIX STAGE (2026-11-13): every change against the integrate version is listed in v3/fix/CHANGELOG.md (issue ids P-, B-, RQ- of
the three verification lenses). Original kept as v3/fix/orig/v3_calc.py.orig.
"""
import sys, os, json, math, copy
import numpy as np
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
W = '/path/to/SolarVest_work/wristband'
sys.path.insert(0, '/path/to/SolarVest_work/wristband/v3/integrate/energy')   # DECIDE COPY: read-only import of the integrate energy model
import v3_energy as VE                  # noqa: E402  (imports only the copies in energy/)

FORCE = False   # DECIDE COPY: never recompute the PV tables here
OUT = {}

# ================================================================================================= 0. sources (read-only)
PARTS = json.load(open(os.path.join(W, 'v2', 'design', 'parts.json')))['variants']['dock_wlcsp']['parts']
STRAP = json.load(open(os.path.join(W, 'v3', 'lanes', 'strap_pv', 'strap_pv.json')))
USBC = json.load(open(os.path.join(W, 'v3', 'lanes', 'usbc', 'usbc.json')))
DISP = json.load(open(os.path.join(W, 'v3', 'lanes', 'display', 'display.json')))

# ================================================================================================= 1. configurations
CONFIGS = {
 'V2-B': dict(name='V2-B as designed (reference)', cell_where='pod', cell='GMB201030', top='LID4', pvset='LID4', display=False,
              usb=False, alert_led=True, pod_len=40.0, r_lim=22.0, wing=None, asbuilt=False),
 'V3-R': dict(name='V3-R recommended: cell capsule on strap root A, wing on root B, PV strips + display window on the pod, USB-C tab',
              cell_where='strap', cell='GMB201030', top='C1', pvset='LID2+WR31', pvset_other_wrist='LID2+WU31', display=True,
              usb=True, alert_led=True, pod_len=40.0, low_zone=True, r_lim=22.0, r130_1206=True, wing='one wide (root B)', pulldown_fix=True,
              strap_conductors=dict(root_A=['VBUS', 'GND', 'NTC', 'GND', 'BATT_P'], root_B=['PV_W+', 'GND'])),
 'V3-N': dict(name='V3-N no display: as V3-R with the full 4-strip PV lid', cell_where='strap', cell='GMB201030', top='LID4',
              pvset='LID4+WR31', pvset_other_wrist='LID4+WU31', display=False, usb=True, alert_led=True, pod_len=40.0, r_lim=22.0,
              r130_1206=True, wing='one wide (root B)', pulldown_fix=True,
              strap_conductors=dict(root_A=['VBUS', 'GND', 'NTC', 'GND', 'BATT_P'], root_B=['PV_W+', 'GND'])),
 'V3-P': dict(name='V3-P cell stays in the pod: V2-B pod lengthened for gate 1, wings on both roots, display, USB-C tab',
              cell_where='pod', cell='GMB201030', top='C1', pvset='LID2+W1x2', display=True, usb=True, alert_led=True,
              pod_len=None, r_lim=22.0, r130_1206=True, wing='W1 both roots', pulldown_fix=True,
              strap_conductors=dict(root_A=['PV_W+', 'GND', 'VBUS'], root_B=['PV_W+', 'GND'])),     # pod length solved in section 3
}
# fix stage: R_LIM 22 ohm everywhere (physics P-1: the -10 C Voc shift was +0.44 V on a base that is already the 25 C data-sheet
# Voc; with the data-sheet slope the bound stays below 0.5 C at 22 ohm even at -20 C); R130 in 1206 for every V3 configuration
# (cold-start dissipation); skin-hot LED chain kept (RQ-08, REDESIGN decision 5 belongs to the supervisor); every strap conductor,
# GND included, has its own entry pad and RF link (P-7, RQ-02 conductor order with GND guards between VBUS and BATT_P).
CONFIGS_NOTE = 'fix stage 2026-11-13: R_LIM 22 ohm 1206 (C17958) in every V3 configuration; LED chain kept; display FPC soldered (J13 ZIF only as an option)'

# ================================================================================================= 2. Z stacks (max-material)
def L(name, t, tag): return dict(name=name, t=t, tag=tag)
MESA = L('optical cap proud of the floor (PPG mesa)', 0.80, 'E REDESIGN 5.2 (LED 0.6+-0.1 V OSRAM p.11)')
FLOOR = L('floor: 0.25 PC film flush with 0.25 Ti Gr2 plates', 0.25, 'E REDESIGN 5.2')
FILM = L('carrier film, polyimide-carrier double-sided', 0.10, 'E REDESIGN 5.2')
PCB = L('main PCB 6-layer 1.0 mm + tolerance', 1.10, 'V JLC thickness list (REDESIGN 11)')
PARTS_H = L('parts + solder (BQ25570, ADS1291 package-locked at 1.00 mm)', 1.05, 'V parts.json heights + 0.05 solder')
LOWP = L('low parts only under the display: body <= 0.70 mm + 0.05 solder', 0.75, 'E V3 placement rule (gate 1 must prove it)')
CLR = L('clearance to the lid / cover', 0.15, 'E REDESIGN 5.2')
LID = L('PV lid: laminated IBC module (glass 0.50 / 0.20 / cells 0.165 / 0.15 / flex 0.12)', 1.20, 'E RFQ acceptance maximum, not a supplier figure (REDESIGN 5.2)')
WIN = [L('window glass of the lid (chemically strengthened, AR both faces, UV-cut)', 0.50, 'E display lane 4.2-4.3'),
       L('air gap (no adhesive allowed on the panel)', 0.10, 'V LS013B7DH03 p.2 (11); E 0.10 mm'),
       L('Sharp LS011B7DH03 panel 0.745 + 0.055 allowance', 0.80, 'V LD-29Y03 p.13 (0.745); E allowance'),
       L('panel support (frame on the lid posts)', 0.10, 'E display lane'),
       L('clearance panel to parts', 0.15, 'E display lane')]
CELLCOL = [L('gap lid to cell', 0.20, 'E REDESIGN 5.2'), L('cell GMB201030 bare, maximum incl. adhesive', 2.50, 'V sister spec p.4 (REDESIGN 5.2)'),
           L('PSA under the cell', 0.10, 'E'), L('support shim 0.15 glass-epoxy', 0.15, 'E')]

def col(layers):
    return dict(layers=layers, total=round(sum(l['t'] for l in layers), 2))
COLUMNS = {
 'PV lid over the board (V3-R, V3-N)': col([LID, CLR, PARTS_H, PCB, FILM, FLOOR, MESA]),
 'display window over the low-part zone (V3-R)': col(WIN + [LOWP, PCB, FILM, FLOOR, MESA]),
 'display window over full-height parts (V3-R fallback if gate 1 cannot keep the low zone)': col(WIN + [PARTS_H, PCB, FILM, FLOOR, MESA]),
 'cell column (V2-B, V3-P)': col([LID] + CELLCOL + [FILM, FLOOR, MESA]),
 'display window over the board strip, cell in the pod (V3-P)': col(WIN + [PARTS_H, PCB, FILM, FLOOR, MESA]),
}
# V3-P: under the C1 lid the cell column governs; the window over the board strip has 1.50 mm free below the glass
v3p_free = round(COLUMNS['cell column (V2-B, V3-P)']['total'] - 0.50 - (PARTS_H['t'] + PCB['t'] + FILM['t'] + FLOOR['t'] + MESA['t']), 2)
LID_P121 = 1.67   # E: lid at the only verified small-panel build-up (Voltaic P121 drawing, REDESIGN 5.2: 1.1 +- 0.3 above the substrate)
LID_P121_MAX = 1.97   # fix stage (build B-12): the same build-up at its upper tolerance (+0.3 mm)
J13_ZIF_SEATED = 1.10 + 0.05   # fix stage (build B-02): Panasonic Y5B height 1.00 +- 0.10 mm (ACCTB1E 201310-T p.3) + solder
STACK = {
 'V2-B': dict(governs='cell column', total=COLUMNS['cell column (V2-B, V3-P)']['total']),
 'V3-R': dict(governs='PV lid column = display window column over the low-part zone',
              total=max(COLUMNS['PV lid over the board (V3-R, V3-N)']['total'], COLUMNS['display window over the low-part zone (V3-R)']['total']),
              fallback_no_low_zone=COLUMNS['display window over full-height parts (V3-R fallback if gate 1 cannot keep the low zone)']['total']),
 'V3-N': dict(governs='PV lid column', total=COLUMNS['PV lid over the board (V3-R, V3-N)']['total']),
 'V3-P': dict(governs='cell column', total=COLUMNS['cell column (V2-B, V3-P)']['total'],
              window_free_below_glass_mm=v3p_free + 0.0, window_needs_mm=round(sum(l['t'] for l in WIN[1:]), 2)),
}
for k, s in STACK.items():   # lid at the verified build-up instead of the 1.20 mm RFQ target (nominal and upper tolerance)
    base_ = COLUMNS['PV lid over the board (V3-R, V3-N)']['total'] if k in ('V3-R', 'V3-N') else s['total']
    s['lid_at_P121_buildup'] = round(base_ - 1.20 + LID_P121, 2)
    s['lid_at_P121_upper_tolerance'] = round(base_ - 1.20 + LID_P121_MAX, 2)
    s['catalogue_lid_2p40'] = round((COLUMNS['PV lid over the board (V3-R, V3-N)']['total'] if k in ('V3-R', 'V3-N') else s['total']) - 1.20 + 2.40, 2)
# every-tolerance chain (v2_calc.py TOL_B), with the ring shortened by the lost cell column for the strap-cell configurations
TOL = [('ring floor top to lid seat', 0.05), ('lid bond line', 0.05), ('lid glass', 0.05), ('encapsulant front', 0.05), ('silicon', 0.04),
       ('encapsulant back', 0.05), ('flex backsheet', 0.03), ('cap height', 0.05), ('carrier film', 0.02)]
tol_wc = round(sum(t for _, t in TOL), 2); tol_rss = round(math.sqrt(sum(t * t for _, t in TOL)), 3)
for k, s in STACK.items():
    s['worst_case_all_tolerances'] = round(s['total'] + tol_wc, 2); s['rss'] = round(s['total'] + tol_rss, 2)
STACK['V3-R']['ring_floor_top_to_lid_seat_mm'] = round(STACK['V3-R']['total'] - MESA['t'] - FLOOR['t'] - LID['t'] - 0.20, 2)
# display FPC: soldered land by default (no connector height); the ZIF option sits outside the panel footprint under the PV lid
STACK['V3-R']['display_fpc'] = 'soldered FPC land (default, fix stage B-01/B-02): no connector height'
STACK['V3-R']['zif_option_total_mm'] = round(STACK['V3-R']['total'] + max(0.0, J13_ZIF_SEATED - PARTS_H['t']), 2)
STACK['V3-R']['zif_option_P121_upper_tolerance_mm'] = round(STACK['V3-R']['lid_at_P121_upper_tolerance'] + max(0.0, J13_ZIF_SEATED - PARTS_H['t']), 2)
STACK['V2-B']['ring_floor_top_to_lid_seat_mm'] = 2.85
# strap-root items (worn, beside the pod; they do not set the pod thickness)
ROOT_ITEMS = {
 'cell capsule on root A (free span)': dict(layers=[('top wall, PC with white print (alpha <= 0.15)', 0.40), ('swelling gap', 0.20),
                                              ('cell GMB201030 max incl. adhesive', 2.50), ('bottom wall, PC', 0.40)],
                                       outline_mm=(38.4, 11.9), tag='V cell 2.5 x 10.5 x 33 mm max incl. tabs (REDESIGN 8.2 gate 4); E walls; '
                                       'fix stage (build B-05): +4 mm PCM end along X for XB5358D0 (4.2 x 3.4 mm, 1.25 mm), R132, C123, the '
                                       'over-current element F1 and the welded tab joints (protector group 18.8 mm2 + F1); 0.40 mm walls are '
                                       'a thin-wall target below a mainstream moulder range (1.02-3.81 mm, REDESIGN 5.5): RFQ or film shell'),
 'cell capsule with the 70 mAh option (LP301230, 3.5 mm max, PCM)': dict(layers=[('top wall', 0.40), ('swelling gap', 0.20), ('LP301230 max', 3.50), ('bottom wall', 0.40)],
                                       outline_mm=(33.4, 13.9), tag='V ARCH 6.2 / v2_calc (3.50 mm, 12 x 30 mm); E walls'),
 'wing on root B (free span)': dict(layers=[('wing laminate on the documented route: FR-4 0.60 + ETFE/encapsulant/IBC build-up 1.10 (P121 '
                                            '1.1 +- 0.3) + PSA 0.05', 1.75), ('root core TPU or FKM', 1.20)],
                                    outline_mm=(35.0, 16.0), tag='E fix stage (build B-06): planning value until a quote shows a flex-backed '
                                    'laminate; the strap lane target (flex 0.11, 0.87 mm) is the RFQ goal (2.07 mm root)'),
 'wing on root B, RFQ target (flex-backed laminate, strap lane 5.1)': dict(layers=[('W1 laminate (ETFE / POE / IBC 0.205 / POE / flex 0.11 / PI 0.20 / PSA)', 0.87),
                                    ('root core TPU or FKM', 1.20)], outline_mm=(35.0, 16.0), tag='E strap lane 5.1; no supplier documents it (B-06)'),
 'USB-C tab on root A beyond the flex hinge (s 23.5-35.5 mm)': dict(layers=[('tab housing, potted, receptacle 3.16-3.46 mm shell', 4.6)], outline_mm=(13.0, 12.0),
                                    tag='E usbc lane 8 (tab 4.4-4.8 mm); fix stage (B-04): starts at s 23.5 so that the flex crossing the hinge '
                                    'between capsule and tab has >= 9.6 mm of free length'),
}
for v in ROOT_ITEMS.values(): v['thickness_mm'] = round(sum(t for _, t in v['layers']), 2)
# capsule on the free span of root A: where it sits against the wrist and the pod (strap-lane wrist geometry, wrist_light.json)
WL = json.load(open(os.path.join(W, 'v3', 'lanes', 'strap_pv', 'calc', 'wrist_light.json')))
def capsule_fit(case, t_caps=3.5, s0=2.0, s1=13.9, strap_t=1.5, pod_top_above_floor=3.85):
    """fix stage (RQ-06): the root hinges at the bar (compliant zone s 0-2 mm), so the capsule starts at s 2.0 (was 1.5)"""
    g = WL['cases'][case]['geometry']; a, b = g['a'], g['b']; t = math.radians(g['facet_tilt_deg'][0])
    P0 = (16.0 + 2.5, b + 1.0); d = (math.cos(t), -math.sin(t)); n = (math.sin(t), math.cos(t))
    def pt(sv, off): return (P0[0] + sv * d[0] + off * n[0], P0[1] + sv * d[1] + off * n[1])
    out_top = pt(s0, -strap_t / 2 + t_caps)           # inner face of the capsule = inner face of the strap; outer face t_caps above it
    inner_end = pt(min(s1, g['free_span_mm'] - 0.3), -strap_t / 2)
    skin_z = b * math.sqrt(max(0.0, 1 - (inner_end[0] / a) ** 2))
    return dict(wrist_mm=g['C'], free_span_mm=round(g['free_span_mm'], 1), tilt_deg=round(g['facet_tilt_deg'][0], 1),
                capsule_outer_top_below_pod_top_mm=round((b + pod_top_above_floor) - out_top[1], 2),
                capsule_inner_face_to_skin_at_far_end_mm=round(inner_end[1] - skin_z, 2),
                extra_bulk_over_a_1p5mm_strap_mm=round(t_caps - strap_t, 2))
CAPSULE_FIT = {c: capsule_fit(c) for c in ('C140_q0.68', 'C165_q0.68', 'C200_q0.68')}
WING_ROOT_FIT = {c: capsule_fit(c, t_caps=2.95, s0=2.0, s1=13.7) for c in ('C140_q0.68', 'C165_q0.68', 'C200_q0.68')}
# worn profile (RQ-05): height above the skin plane of each worn item, mm (pod floor on the skin, mesa pressed in = 3.85 mm body)
WORN_PROFILE = {'pod top, mesa pressed into the skin (body 4.65 - 0.80)': 3.85, 'pod top, mesa not pressed': 4.65,
                'USB-C tab on the skin-contact strap (V3-R/V3-N/V3-P)': 4.6,
                'capsule outer top below the pod top, 140 / 165 / 200 mm wrists': [CAPSULE_FIT[c]['capsule_outer_top_below_pod_top_mm'] for c in CAPSULE_FIT],
                'wing root (documented route 2.95 mm) outer top below the pod top': [WING_ROOT_FIT[c]['capsule_outer_top_below_pod_top_mm'] for c in WING_ROOT_FIT],
                'textile band': 1.5, 'V2-B pod top for comparison (mesa pressed in)': 4.50,
                'USB-C plug overmould (5.5-6.5 mm, usbc lane 2.4) on a receptacle axis 1.98-2.30 mm above the skin: reaches below the skin plane by': '0.45-1.27 mm (RQ-05)',
                'tab thickness that clears a 6.5 mm overmould with the shell centred': 6.5}
OUT['stacks'] = dict(columns=COLUMNS, configs=STACK, root_items=ROOT_ITEMS, tolerance=dict(worst_case_add=tol_wc, rss_add=tol_rss),
                     capsule_on_free_span=CAPSULE_FIT, wing_root_on_free_span=WING_ROOT_FIT, worn_profile_mm=WORN_PROFILE,
                     note='max-material sums, PPG mesa included (REDESIGN 5.2 convention); E unless a layer says V')

# ================================================================================================= 3. board area (gate 1)
def cy(ref): return PARTS[ref].get('courtyard_area_mm2') or 0.0
SKY = {r: p for r, p in PARTS.items() if p.get('jlc_placed') and p.get('side') == 'F'}
CY_BASE = round(sum(cy(r) for r in SKY), 1)                          # 360.7 mm2 (CALC.md 12)
def h(ref): return PARTS[ref].get('height_max_mm') or 0.0
REMOVE = {
 'protector to the root-A flex (cell leaves the pod)': ['U14', 'R132', 'C123'],
 'skin-hot LED chain (removed only if the supervisor accepts REDESIGN decision 5 (c) in writing; kept by default, RQ-08)': ['D10', 'R507', 'Q6', 'R508'],
}
USB_BLOCK = [  # usbc lane parts_pod_block (courtyards V parts.json class / E for the WSON-8); C-numbers V JLC API 2026-11-13 (lane)
 ('U15', 'TI BQ25170DSGR linear charger, WSON-8', 'C5208201', 6.76, 0.80), ('C130', '1 uF 25 V X5R 0402 (IN)', 'C52923', 1.41, 0.60),
 ('C131', '1 uF 25 V X5R 0402 (OUT at VBAT_IC)', 'C52923', 1.41, 0.60), ('R140', '18 k 1 % 0402 ISET', 'C25762', 1.50, 0.55),
 ('R141', '2 kOhm 1 % 0402 ISET RC, in series with C132, the pair across R140 (TI SLUAAG9 Sep 2021: R 2 kOhm, C 4.7 nF in parallel '
          'with R-ISET for ICHG < 50 mA, read 2026-11-13)', 'C4109', 1.50, 0.55), ('C132', '4.7 nF 50 V X7R 0402 ISET RC', 'C1538', 1.41, 0.55),
 ('R142', '36 k 1 % 0402 VSET = 4.10 V', 'C43676', 1.50, 0.55), ('R143', '220 k 0402 /PG pull-up', 'C25767', 1.50, 0.55),
 ('R144', '1 M 0402 VBUS divider top', 'C26083', 1.50, 0.55), ('R145', '1 M 0402 VBUS divider bottom', 'C26083', 1.50, 0.55),
 ('Q8', 'PMZ290UNE2YL: PV short while VBUS', 'C478155', 2.02, 0.50), ('Q9', 'PMZ290UNE2YL: AVDD_EN low (ECG interlock)', 'C478155', 2.02, 0.50),
 ('Q10', 'PMZ290UNE2YL: CHG_DIS pulls TS low', 'C478155', 2.02, 0.50), ('R146', '1 M 0402 Q10 gate pull-down', 'C26083', 1.50, 0.55),
 ('D12', 'BAS521 SOD-523: VBUS wakes ship mode', 'C130414', 3.12, 0.70), ('D13', 'TI ESD761DPYR on VBUS at the pod entry', 'C20345399', 2.35, 0.45),
 ('R149', '100 k 0402 AIN protection on the shared NTC node', 'C25741', 1.50, 0.55)]
DISP_BLOCK = [  # display lane area.parts (refs renumbered: lane U15 -> U16, U16 -> U17 to avoid the USB U15)
 ('U16', 'TI TPS7A0230PDQNR 3.0 V LDO, X2SON-4', 'C2867950', 2.75, 0.40), ('C1501', '1 uF 25 V 0402 LDO in', 'C52923', 1.41, 0.60),
 ('C1502', '1 uF 25 V 0402 LDO out = panel VDD', 'C52923', 1.41, 0.60), ('C1503', '100 nF 0201 panel VDDA', 'C7393837', 0.78, 0.33),
 ('C1504', '100 nF 0201 DISP delay', 'C7393837', 0.78, 0.33), ('R1501', '100 k 1 % 0201 DISP delay', 'C270364', 0.70, 0.33),
 ('U17', 'TI TXU0104RUTR translator, UQFN-12', 'C5187176', 5.50, 0.55), ('C1601', '100 nF 0201 VCCA', 'C7393837', 0.78, 0.33),
 ('C1602', '100 nF 0201 VCCB', 'C7393837', 0.78, 0.33),
 ('J13', 'soldered FPC land: 10 pads 0.3 x 1.6 mm at 0.5 mm pitch plus an asymmetric key pad, display FPC soldered at final assembly '
          '(fix stage B-01/B-02; not a JLC-placed part)', None, 15.1, 0.0)]
J13_ZIF_OPTION = ('J13', 'ZIF option: Panasonic AYF531035 (C425133) is top-and-bottom contact (Panasonic product page, read 2026-11-13), '
                  'so a flipped FPC still mates: needs a lid-frame key and the EOL test; 1.00 +- 0.10 mm', 'C425133', 36.75, 1.10)
RFCHOKE = [(f'FB{i}', '0402 series link on a strap conductor, GND included (P-7): 0 ohm C17168 (UNI-ROYAL 0402WGF0000TCE, Basic, '
           '15,711,350 in stock, JLC API 2026-11-13 10:26 UTC) by default; a ferrite bead or a common-mode choke if SIM-10/11 asks (part U)',
           'C17168', 1.45, 0.55) for i in range(1, 9)]
PAD_PER_CONDUCTOR_MM2 = 6.0    # fixed sky-side land per strap conductor (strap lane 8.1: +12 mm2 for two pads; build lens check value)
PULLDOWN_FIX = [dict(ref='R131', change='1 MOhm C26083 -> 10 MOhm C144806 (YAGEO AC0402FR-0710ML, 255,833 in stock, JLC API 2026-11-13 10:26 UTC)',
                     why='1.86 uA flows through the 1 MOhm pull-down whenever INA_EN is high (MON, RAW, ECO): 4.1 uW battery-referred'),
                dict(ref='R108', change='1 MOhm C26083 -> 10 MOhm C144806', why='same while PV_INH is high: continuous in the W-C band')]
ROOTA_FLEX = [  # JLC flex PCBA on root A (FPC assembly confirmed on the JLC PCBA capability page 2026-11-13)
 ('U14', 'XySemi XB5358D0 protector (moved from the main board)', 'C2760012', 14.28, 1.25), ('R132', '100 ohm 0603 (protector R1)', 'C22775', 3.09, 0.55),
 ('F1', 'over-current element in series with the cell, inside the capsule (RQ-02): fuse or fusing resistor, hold >= 0.4 A (U12 inrush '
        '0.28-0.37 A), opens <= 1 A; part not selected (U), datasheet to be read', None, None, None),
 ('C123', '100 nF 0402 (protector C1)', 'C1525', 1.41, 0.55), ('J14', 'USB-C 6P receptacle, sealed (candidate SHOU HAN 6PFS 2JCB0.8-H6.7 IPX8, drawing U)', 'C3020039', None, None),
 ('R150', '5.1 k 1 % 0402 Rd CC1', 'C25905', 1.50, 0.55), ('R151', '5.1 k 1 % 0402 Rd CC2', 'C25905', 1.50, 0.55),
 ('D14', 'ESD761DPYR VBUS at the receptacle', 'C20345399', 2.35, 0.45), ('D15', 'ESD761DPYR CC1', 'C20345399', 2.35, 0.45),
 ('D16', 'ESD761DPYR CC2', 'C20345399', 2.35, 0.45)]
FIX_DOCK = 24.0 + 13.2 + 20.0 + 12.0 + 12.3 + 5 * 3.24             # 97.7 mm2 (redesign/v2_calc.py FIX_DOCK)
def density(board_area, cutout, cut_perim, keepout, fixed, courtyard, board_xy=(37.0, 29.0), edge=0.5, cut_edge=0.3):
    """redesign/v2_calc.py density(), with the board outline as a parameter"""
    gross = board_area - cutout - edge * 2 * (board_xy[0] + board_xy[1]) - cut_edge * cut_perim
    place = gross - keepout - fixed
    return dict(placement_area_mm2=round(place, 1), courtyard_mm2=round(courtyard, 1), utilisation=round(courtyard / place, 3))
BOARD_AREA_37x29 = 1056.0      # mm2, 37 x 29 with corner radii (redesign/v2_calc.py)
V1_BBOX = 399.5 / 360.7        # gate-1 lane note (v2/gates/g1/PROGRESS.md): v1's bbox measure gives 399.5 mm2 for the same parts

def area_config(k, pod_len=40.0):
    c = CONFIGS[k] if isinstance(k, str) else k; removed = []; added = []
    if c['cell_where'] == 'strap': removed += REMOVE['protector to the root-A flex (cell leaves the pod)']
    if not c['alert_led']: removed += REMOVE['skin-hot LED chain (removed only if the supervisor accepts REDESIGN decision 5 (c) in writing; kept by default, RQ-08)']
    r_lim_ = c['r_lim']
    if c.get('r130_1206') or r_lim_ != 22.0:   # R130 in 1206 (250 mW): cold-start dissipation with more PV exceeds the 0603 rating (section 5)
        removed += ['R130']
        cn = {22.0: ('C17958', 'UNI-ROYAL 1206W4F220JT5E, Basic, 549,459 in stock, JLC API 2026-11-13 14:11 UTC'),
              24.0: ('C17963', 'UNI-ROYAL 1206W4F240JT5E'), 27.0: ('C17946', 'UNI-ROYAL 1206W4F270JT5E')}[r_lim_]
        added += [('R130', f"{r_lim_:g} ohm 1 % 1206 250 mW R_LIM ({cn[1]})", cn[0], 10.35, 0.65)]
    if c['usb']: added += USB_BLOCK
    if c['usb'] and not c.get('usb_tab', True):
        added += [('J15', 'D-4 (b): two flush magnetic pads on the pod top, spring fingers (usbc lane: +12.6 mm2, parts.json class)', None, 12.6, 1.0)]
    if c['display']: added += (DISP_BLOCK[:-1] + [J13_ZIF_OPTION]) if c.get('fpc') == 'zif' else DISP_BLOCK
    sc = c.get('strap_conductors', dict(root_A=[], root_B=[]))
    n_ch = len(sc['root_A']) + len(sc['root_B'])
    # one 0402 RF link per strap conductor crossing the pod entry, GND included (P-7)
    added += RFCHOKE[:n_ch]
    courtyard = CY_BASE - sum(cy(r) for r in removed) + sum(a[3] for a in added)
    if c['cell_where'] == 'strap':
        fixed = FIX_DOCK - 24.0 - 13.2 + PAD_PER_CONDUCTOR_MM2 * n_ch   # cell tab + NTC pads -> one 6 mm2 land per strap conductor
        cut, cutp = 0.0, 0.0
    else:
        fixed = FIX_DOCK + PAD_PER_CONDUCTOR_MM2 * n_ch
        cut, cutp = 11.0 * 34.0, 34 + 2 * 11.0
    bx = 37.0 + (pod_len - 40.0); area = BOARD_AREA_37x29 + (pod_len - 40.0) * 29.0
    d = density(area, cut, cutp, 15.0, fixed, courtyard, board_xy=(bx, 29.0))
    d.update(dict(strap_conductors=sc, removed=[dict(ref=r, part=PARTS[r]['value'], lcsc=PARTS[r].get('lcsc'), courtyard_mm2=cy(r)) for r in removed],
                  added=[dict(ref=a[0], part=a[1], lcsc=a[2], courtyard_mm2=a[3], height_max_mm=a[4]) for a in added],
                  fixed_features_mm2=round(fixed, 1), board_mm=(bx, 29.0), cut_out_mm2=cut,
                  gate1_pass=d['utilisation'] <= 0.62, utilisation_on_v1_bbox_measure=round(d['utilisation'] * V1_BBOX, 3)))
    return d
AREA = {k: area_config(k) for k in ('V2-B', 'V3-R', 'V3-N')}
AREA['V3-R with the ZIF option (J13 AYF531035 instead of the soldered FPC)'] = area_config(dict(CONFIGS['V3-R'], fpc='zif'))
AREA['V3-R without the skin-hot LED chain (only with REDESIGN decision 5 (c) in writing)'] = area_config(dict(CONFIGS['V3-R'], alert_led=False))
V3R_PADS = dict(CONFIGS['V3-R'], usb_tab=False, strap_conductors=dict(root_A=['BATT_P', 'GND', 'NTC', 'GND'], root_B=['PV_W+', 'GND']))
AREA['V3-R with USB on pod-top pads (D-4 b, no tab)'] = area_config(V3R_PADS)
# V3-P: lengthen the pod (and board) along X until utilisation <= 0.62 (gate 1); also with 0201 passives (-22.1 mm2, CALC.md 12)
def solve_len(k, extra_cy=0.0):
    for dl in [x * 0.1 for x in range(0, 400)]:
        d = area_config(k, 40.0 + dl)
        if (d['courtyard_mm2'] + extra_cy) / d['placement_area_mm2'] <= 0.62: return round(40.0 + dl, 1), d
    return None, None
LEN_P, AREA_P = solve_len('V3-P'); LEN_P0201, _ = solve_len('V3-P', extra_cy=-22.1)
CONFIGS['V3-P']['pod_len'] = LEN_P
AREA['V3-P'] = AREA_P; AREA['V3-P']['pod_length_needed_mm'] = LEN_P; AREA['V3-P']['pod_length_with_0201_passives_mm'] = LEN_P0201
AREA['V3-P at 40 mm (for comparison)'] = area_config('V3-P', 40.0)
# remedies for a pod-cell layout at 40 mm (each alone, mm2 of courtyard; CALC.md 12, display lane, usbc lane)
REMEDIES = {'generic passives in 0201 (CALC.md 12)': -22.1, 'display FPC soldered instead of the ZIF (display lane 3.4; V3-R default since the fix stage)': -21.7,
            'skin-hot LED chain removed (display lane 3.5; needs REDESIGN decision 5 (c) in writing)': -14.2, 'USB charger block moved into the USB tab (E)': -19.0}
# V3-R low-part zone under the display: parts with height_max <= 0.70 mm may sit under the panel (seated <= 0.75 mm)
def zone_check():
    d = AREA['V3-R']; rem = {x['ref'] for x in d['removed']}
    tall = sum(cy(r) for r in SKY if r not in rem and h(r) > 0.70) + sum(a['courtyard_mm2'] for a in d['added'] if (a['height_max_mm'] or 0) > 0.70)
    low = d['courtyard_mm2'] - tall
    disp_fp = 33.0 * 15.0          # display 32 x 14 mm + 0.5 mm frame margin (E)
    tall_area = d['placement_area_mm2'] - disp_fp
    tall_list = sorted([(r, PARTS[r]['value'][:28], h(r), cy(r)) for r in SKY if r not in rem and h(r) > 0.70], key=lambda x: -x[3])
    return dict(display_footprint_mm2=disp_fp, tall_courtyard_mm2=round(tall, 1), tall_zone_area_mm2=round(tall_area, 1),
                tall_zone_utilisation=round(tall / tall_area, 3), low_courtyard_mm2=round(low, 1), low_zone_utilisation=round(low / disp_fp, 3),
                tall_parts=[dict(ref=a, part=b, height_max_mm=c_, courtyard_mm2=e) for a, b, c_, e in tall_list] +
                           [dict(ref=a['ref'], part=a['part'][:40], height_max_mm=a['height_max_mm'], courtyard_mm2=a['courtyard_mm2'])
                            for a in d['added'] if (a['height_max_mm'] or 0) > 0.70],
                rule='under the 32 x 14 mm panel only parts <= 0.70 mm body height; decoupling capacitors of ICs placed under the panel '
                     'must be <= 0.70 mm (0402 1-22 uF are 0.60-0.70 mm in parts.json); 0603 MLCCs (0.90 mm), QFNs, inductors, TMP117, '
                     'BQ25170 and the ZIF go outside the panel footprint')
AREA['V3-R low-part zone'] = zone_check()
OUT['board_area'] = dict(baseline_sky_courtyard_mm2=CY_BASE, gate1_limit=0.62, configs=AREA, remedies_for_a_pod_cell_layout=REMEDIES,
                         value_changes_same_land=PULLDOWN_FIX,
                         root_a_flex_pcba=[dict(ref=a[0], part=a[1], lcsc=a[2]) for a in ROOTA_FLEX],
                         note='metric of redesign/v2_calc.py: courtyard / (board - cut-out - edge bands - keep-out 15 mm2 - fixed sky-side '
                              'features); courtyards are the parts.json F.CrtYd boxes; on v1 bbox measure every value is x1.108 (gate-1 lane note)')

# ================================================================================================= 4. masses (g) and volume
RHO = dict(pc=1.20e-3, film=1.30e-3, ti=4.51e-3, fr4=1.85e-3, board6_10=2.63e-3, tpu=1.20e-3, textile=0.55e-3)   # g/mm3; board g/mm2 (v2_calc)
PLATES = 12.5 * 18.5 + 13.0 * 22.5          # 523.8 mm2 Ti (v2_calc.py)
def case_area(lx): return lx * 32.0 - (4 - math.pi) * 6.0 ** 2
def perim(lx): return 2 * (lx + 32.0) - (8 - 2 * math.pi) * 6.0
def lid_mass(lx, kind):
    if kind == 'LID4': return 2.43 * (lx - 0.4 - 2.5) * 31.6 / (37.1 * 31.6)        # v2_calc lid_mass(0.50) = 2.43 g on 1143 mm2, scaled with length
    return 2.83 * (lx - 0.4 - 2.5) * 31.6 / (37.1 * 31.6)                            # display lane C1 top (half PV + window + panel + frame) 2.83 g
def pod_mass(k):
    c = CONFIGS[k] if isinstance(k, str) else k; lx = c['pod_len']; m = {}
    m['top (lid or C1 lid + display)'] = lid_mass(lx, 'LID4' if c['top'] == 'LID4' else 'C1')
    m['cell in the pod (GMB201030, 0.9-1.4 g)'] = 1.20 if c['cell_where'] == 'pod' else 0.0
    board = BOARD_AREA_37x29 + (lx - 40.0) * 29.0 - (374.0 if c['cell_where'] == 'pod' else 0.0)
    parts_g = 0.45 - (0.02 if c['cell_where'] == 'strap' else 0.0) - (0.03 if not c['alert_led'] else 0.0) + (0.05 if c['usb'] else 0.0) + (0.05 if c['display'] else 0.0) \
              + (0.01 if c.get('r130_1206') else 0.0)
    m['PCBA (6L 1.0 mm at 2.63 mg/mm2 + parts)'] = board * RHO['board6_10'] + parts_g
    ring_h = 3.05 if c['cell_where'] == 'pod' else 2.40
    bars = 2 * 22 * 2.0 * 3.0 * RHO['pc'] + 4 * 27 * RHO['pc']
    m['ring walls 1.0 mm + strap bars'] = perim(lx) * 1.0 * ring_h * RHO['pc'] + bars
    shim = 11 * 34 * 0.15 * RHO['fr4'] if c['cell_where'] == 'pod' else 0.0
    m['floor: PC film, Ti plates, carrier film, shim'] = (case_area(lx) - PLATES) * 0.25 * RHO['pc'] + PLATES * 0.25 * RHO['ti'] + case_area(lx) * 0.10 * RHO['film'] + shim
    m['E3 strip and tab'] = 0.15; m['optical cap'] = 0.08
    if c['usb'] and not c.get('usb_tab', True): m['USB pads on the pod top (2 spring fingers + magnets, usbc lane: +0.1 g)'] = 0.10
    m['adhesives, vent, posts, tails'] = 0.25 + (0.04 if c['cell_where'] == 'strap' or c['usb'] else 0.0) - (0.01 if c['cell_where'] == 'strap' else 0.0)
    m = {a: round(b, 3) for a, b in m.items()}; m['TOTAL'] = round(sum(m.values()), 2)
    return m
# strap roots after the fix stage (B-04, B-05, B-06, B-08, RQ-04, RQ-06), s = distance from the bar along the strap:
#   root A with the cell: bar hinge s 0-2 | capsule s 2.0-13.9 | flex hinge s 13.9-23.5 (>= 9.6 mm free flex) | USB tab s 23.5-35.5
#   root B with a wing: bar hinge s 0-2 | wing s 2-13.7 | root end s 16
ROOT_A_LEN, ROOT_B_LEN, BAND_W, BAND_T = 35.5, 16.0, 20.0, 1.5
WING_DOC_FACTOR = 1.407 / 0.745        # wing mass on the documented route (0.6 mm FR-4 + 1.1 mm build-up) / flex-backed target (build B-06)
def strap_mass(k, max_material=False):
    c = CONFIGS[k] if isinstance(k, str) else k
    band = 6.0 if max_material else 5.5
    m = {'textile hook-and-loop band (5-6 g, REDESIGN decision 4)': band}
    if c['cell_where'] == 'pod' and not c.get('wing') and not c['usb']: m['TOTAL'] = band; return m
    has_a = c['cell_where'] == 'strap' or c['usb'] or c.get('wing') == 'W1 both roots'
    tab = c['usb'] and c.get('usb_tab', True)      # D-4 (b): USB on two pod-top pads + adapter cable, no tab on the strap
    la = ROOT_A_LEN if tab else 16.0               # without the USB tab root A ends at s 16 (no flex hinge to a tab)
    hinge2 = 9.6 if tab else 2.1                   # flex hinge s 13.9-23.5 to the tab, or the root end s 13.9-16
    if has_a:
        m[f'root A: textile replaced ({la:g} x 20 x 1.5 mm)'] = round(-la * BAND_W * BAND_T * RHO['textile'], 3)
    if c['cell_where'] == 'strap':
        shell = (38.4 * 11.9 * 3.5 - 37.4 * 10.9 * 2.7) * RHO['pc']
        m['root A: capsule shell PC (outer 38.4 x 11.9 x 3.5, inner 37.4 x 10.9 x 2.7 mm, PCM end)'] = round(shell, 3)
        m['root A: cell GMB201030 (0.9-1.4 g)'] = 1.40 if max_material else 1.20
        m['root A: flex PCBA (protector, F1, Rd, ESD, receptacle excluded), NTC bead, welded tabs'] = 0.11
        m[f'root A: TPU in the bar hinge and the flex hinge (35 x (2.0 + {hinge2:g}) x 1.2 mm)'] = round(35 * (2.0 + hinge2) * 1.2 * RHO['tpu'], 3)
    elif has_a:
        m[f'root A: TPU core under the W1 wing and in the hinge (20 x (16 + {hinge2 if tab else 0:g}) x 1.2 mm)'] = round(20 * (16 + (hinge2 if tab else 0.0)) * 1.2 * RHO['tpu'], 3)
    if tab:
        m['root A: USB-C tab (receptacle, potting, housing; usbc lane 1.0-1.5 g)'] = 1.50 if max_material else 1.25
    if c.get('wing') == 'one wide (root B)':
        m['root B: textile replaced (16 x 20 x 1.5 mm)'] = round(-ROOT_B_LEN * BAND_W * BAND_T * RHO['textile'], 3)
        m['root B: TPU root core 35 x 16 x 1.2 mm (needed only because of the wing)'] = round(35 * 16 * 1.2 * RHO['tpu'], 3)
        m['root B: wing laminate 35 x 16 mm, documented route (flex-backed target 0.745 g)'] = round(0.426 * 5.6 / 3.2 * WING_DOC_FACTOR, 3)
    elif c.get('wing') == 'W1 both roots':
        m['root B: textile replaced (16 x 20 x 1.5 mm)'] = round(-ROOT_B_LEN * BAND_W * BAND_T * RHO['textile'], 3)
        m['root B: TPU core 20 x 16 x 1.2 mm'] = round(20 * 16 * 1.2 * RHO['tpu'], 3)
        m['W1 wing laminates, both roots, documented route (strap lane 0.85 g target)'] = round(0.85 * WING_DOC_FACTOR, 3)
    m['TOTAL'] = round(sum(v for a, v in m.items()), 2)
    return m
def pod_mass_max(k):
    """maximum material (build B-08): 6-layer board at 1.10 mm instead of 1.00 mm (+0.10 mm FR-4 over the board), cell 1.40 g in the pod"""
    c = CONFIGS[k] if isinstance(k, str) else k; m = pod_mass(c)
    board = BOARD_AREA_37x29 + (c['pod_len'] - 40.0) * 29.0 - (374.0 if c['cell_where'] == 'pod' else 0.0)
    extra = 0.10 * board * RHO['fr4'] + (0.20 if c['cell_where'] == 'pod' else 0.0)
    return round(m['TOTAL'] + extra, 2)
MASS = {}
for k in CONFIGS:
    pm, sm = pod_mass(k), strap_mass(k); smx = strap_mass(k, max_material=True); pmx = pod_mass_max(k)
    MASS[k] = dict(pod=pm, strap=sm, pod_g=pm['TOTAL'], strap_g=sm['TOTAL'], worn_g=round(pm['TOTAL'] + sm['TOTAL'], 1),
                   pod_g_max_material=pmx, strap_g_max_material=smx['TOTAL'], worn_g_max_material=round(pmx + smx['TOTAL'], 1),
                   max_material_note='board 1.10 mm, band 6.0 g, cell 1.40 g, USB tab 1.50 g (top of each range; build B-08)')
_pm, _sm = pod_mass(V3R_PADS), strap_mass(V3R_PADS)
MASS['V3-R with USB on pod-top pads (D-4 b, no tab)'] = dict(pod=_pm, strap=_sm, pod_g=_pm['TOTAL'], strap_g=_sm['TOTAL'], worn_g=round(_pm['TOTAL'] + _sm['TOTAL'], 1),
    pod_g_max_material=pod_mass_max(V3R_PADS), worn_g_max_material=round(pod_mass_max(V3R_PADS) + strap_mass(V3R_PADS, max_material=True)['TOTAL'], 1))
VOL = {}
for k in CONFIGS:
    lx = CONFIGS[k]['pod_len']; body = (STACK[k]['total'] - MESA['t'])
    v = dict(pod_body_cm3=round(case_area(lx) * body / 1000, 2), case_outline_mm=(lx, 32.0), worn_plan_pod_and_bars_mm=(lx, 37.0))
    if CONFIGS[k]['cell_where'] == 'strap':
        v['root A capsule cm3'] = round(38.4 * 11.9 * 3.5 / 1000, 2); v['USB tab cm3'] = round(13 * 12 * 4.6 / 1000, 2)
    elif k != 'V2-B':
        v['USB tab cm3'] = round(13 * 12 * 4.6 / 1000, 2)
    if CONFIGS[k].get('wing') == 'one wide (root B)': v['wing laminate cm3'] = round(35 * 16 * 1.75 / 1000, 2)
    elif CONFIGS[k].get('wing') == 'W1 both roots': v['wing laminate cm3'] = round(2 * 20 * 16 * 1.75 / 1000, 2)
    v['total_rigid_cm3'] = round(sum(x for a, x in v.items() if a.endswith('cm3')), 2)
    VOL[k] = v
OUT['mass_g'] = MASS; OUT['volume'] = VOL

# ================================================================================================= 5. energy
# DECIDE COPY: never rewrite the integrate cache. If the signature differs from the cached one, compute() would recompute and
# overwrite v3/integrate/energy/v3_energy_cache.json, so the cache path is redirected to this folder in that case.
import hashlib as _hl
_sig = _hl.sha1(json.dumps([VE.PVSETS, VE.TABLE_SETS, VE.LUX_GRID, VE.SUN_GRID, VE.R_LIM, VE.A_LID2, VE.VOC_TC, 'v6-fix'], sort_keys=True).encode()).hexdigest()
_sig_cache = json.load(open(VE.CACHE)).get('sig') if os.path.exists(VE.CACHE) else None
CACHE_REDIRECTED = _sig != _sig_cache
if CACHE_REDIRECTED: VE.CACHE = os.path.join(HERE, 'v3_energy_cache_copy.json')
EN = VE.compute(force=False, verbose=True)
def harv(setname, lab, r_lim=22.0): return EN['scen'][VE.tkey(setname, r_lim)][lab] * 1e-6     # W into the battery (3.8 V)
def targets(k, pvset=None, which='typ', gain=4, self_pm=None, display=None, cell=None, r_lim=None):
    c = CONFIGS[k] if isinstance(k, str) else k; pvset = pvset or c['pvset']; cell = cell or c['cell']; rl = r_lim or c['r_lim']
    if VE.tkey(pvset, rl) not in EN['scen']: rl = 22.0      # sets without a table at the config value: 22 ohm (stated in the key)
    cfg = dict(cell=cell, display=c['display'] if display is None else display, usb=c['usb'], asbuilt=c.get('asbuilt', True), which=which, gain=gain,
               pulldown_fix=c.get('pulldown_fix', False))
    tot, br = VE.loads(cfg)
    if self_pm is not None:       # cell retention at the family limit (REDESIGN 5.6: 15 %/month)
        cap = VE.CELLS[cell]['c_typ']; extra = (self_pm - 0.03) * cap * 1e-3 / 730.0 * 3.7
        tot = {m: v + extra for m, v in tot.items()}
    U = VE.usable_Wh(cell)
    d = lambda p: U / (p * 24)
    t = dict(loads_uW={m: round(v * 1e6, 1) for m, v in tot.items()}, usable_mWh=round(U * 1e3, 1))
    t['T1_MON_dark_d'] = round(d(tot['MON']), 1)
    if c['display'] if display is None else display:
        don = VE.DISP[which]['on']; doff = VE.DISP[which]['rtw']; pon = tot['MON']; poff = pon - don + doff
        t['T1_with_dark_policy_d'] = round(1 + (U - pon * 24) / (poff * 24), 1)        # always-on for 24 h, then raise-to-wake only
    t['RAW_WC_d'] = round(d(tot['RAW']), 1); t['T2_ECO_d'] = round(d(tot['ECO']), 0)
    t['T3_min_day_045sun'] = round(tot['MON'] * 24 / harv(pvset, 'walking sun 30 deg 0.45 sun', rl) * 60, 1)
    t['T3_overcast_min_day_01sun'] = round(tot['MON'] * 24 / harv(pvset, 'walking overcast 0.1 sun', rl) * 60, 0)
    t['T4_ECO_1000lx_10h'] = round(10 * harv(pvset, 'desk 1000 lx', rl) / (tot['ECO'] * 24), 2)
    net = tot['MON'] * 24 - 10 * harv(pvset, 'desk 300 lx', rl)
    t['T5_indoor_300lx_10h_days_from_full'] = round(U / net, 1) if net > 0 else 'energy-neutral'
    t['T5_fraction_of_MON_covered_pct'] = round(100 * 10 * harv(pvset, 'desk 300 lx', rl) / (tot['MON'] * 24), 1)
    t['pv_set'] = VE.tkey(pvset, rl)
    t['T6_SHELF_d'] = round(d(tot['SHELF']), 0); t['T6_SHIP_d'] = round(d(tot['SHIP']), 0)
    return t, br
TGT = {}
TGT['V2-B planning (REDESIGN convention, R_LIM 22)'] = targets('V2-B')[0]
TGT['V2-B as built (G-4, R131, R108 items added; R_LIM 22)'] = targets(dict(CONFIGS['V2-B'], asbuilt=True))[0]
TGT['V2-B as built with R131, R108 at 10 MOhm'] = targets(dict(CONFIGS['V2-B'], asbuilt=True, pulldown_fix=True))[0]
for k in ('V3-R', 'V3-N', 'V3-P'):
    TGT[k] = targets(k)[0]
    TGT[k + ' | maximum currents (protector 6 uA, USB 0.6 + 1 uA, display at panel maximum)'] = targets(k, which='max')[0]
    TGT[k + ' | worst stack (LED gain 1, maximum currents, retention limit)'] = targets(k, which='max', gain=1, self_pm=0.15)[0]
    if CONFIGS[k].get('pvset_other_wrist'):
        TGT[k + ' | worn on the other wrist (wing on the ulnar side)'] = targets(k, pvset=CONFIGS[k]['pvset_other_wrist'])[0]
TGT['V3-R | wing shortened or narrowed to about 55 % area (17 mm wide; thermal mitigation of P-5/RQ-07)'] = targets('V3-R', pvset='LID2+WR17')[0]
TGT['V3-N | R_LIM 24 ohm option (only if -20 C at 1.2 sun on every string must hold with 5 % margin)'] = targets('V3-N', r_lim=24.0)[0]
TGT['V3-R | without the display load (same PV set)'] = targets('V3-R', display=False)[0]
TGT['V3-R | 70 mAh LP301230 option (R_LIM 22)'] = targets('V3-R', cell='LP301230')[0]
# 70 mAh option: R_LIM can fall in proportion to the cell; take the smallest of 12/13/15 ohm whose -20 C bound (k 0.72) is <= 0.5 C
_cb70 = EN['charge_bound']['LID2+WR31 with the 70 mAh cell, R_LIM 12/13/15']
_r70 = min([r for r in (12.0, 13.0, 15.0) if _cb70[f'R{r:g} | 1.2 sun, strings at -20 C | k 0.72']['c_rate'] <= 0.5] or [15.0])
_p70 = VE.M.bq_point(VE.sources('LID2+WR31', 'walking|sun30', VE.M.g_si(sun=0.45)), r_lim=_r70, vbat=3.8)['p_bat_mW'] * 1e-3
_t70 = dict(TGT['V3-R | 70 mAh LP301230 option (R_LIM 22)'])
_t70['T3_min_day_045sun'] = round(_t70['loads_uW']['MON'] * 1e-6 * 24 / _p70 * 60, 1); _t70['pv_set'] = f'LID2+WR31@R{_r70:g} (T3 only; other harvest values at R22)'
_t70['harvest_045sun_mW'] = round(_p70 * 1e3, 2); _t70['r_lim_ohm'] = _r70
_t70['charge_bound_minus20C_k072'] = _cb70[f'R{_r70:g} | 1.2 sun, strings at -20 C | k 0.72']['c_rate']
TGT['V3-R | 70 mAh LP301230 option with R_LIM lowered for the larger cell'] = _t70
TGT['glass-top option: display, no PV on the pod, one wing (R_LIM 22)'] = targets('V3-R', pvset='WR31', r_lim=22.0)[0]
TGT['V2-B lid + lane W1 wings (strap lane check, R_LIM 22)'] = targets('V2-B', pvset='LID4+W1x2')[0]
_, BR = targets('V3-R')
LOADS_BREAKDOWN = {m: {a: round(b * 1e6, 2) for a, b in v.items()} for m, v in BR.items()}

# fix-stage sensitivities on T3 / T5 (P-2 dark wing, P-9 hot lid, edge-dominated shunt, office downlights)
def _t3(k, p_uW): return round(TGT[k]['loads_uW']['MON'] * 1e-6 * 24 / (p_uW * 1e-6) * 60, 1)
def _t5(k, h300_uW):
    net = TGT[k]['loads_uW']['MON'] * 1e-6 * 24 - 10 * h300_uW * 1e-6
    return round(VE.usable_Wh(CONFIGS[k]['cell']) / net, 1) if net > 0 else 'energy-neutral'
SENS = {}
for k in ('V3-R', 'V3-N', 'V3-P'):
    ps = CONFIGS[k]['pvset']; ws = EN['wing_light_study'][ps]; hl = EN['hot_lid_045sun'][ps]; se = EN['sensitivity'][ps]
    SENS[k] = dict(
        T3_min=dict(base=TGT[k]['T3_min_day_045sun'], lid_35C=_t3(k, hl['lid at 35 C (G x 1.0)']), lid_45C=_t3(k, hl['lid at 45 C (G x 1.0)']),
                    wing_dark_no_diode=_t3(k, ws['no diode | wing 0 x lid']['sun_045_uW']),
                    wing_dark_with_diode=_t3(k, ws['RB751 diode on PV_W+ | wing 0 x lid']['sun_045_uW'])),
        T5_days=dict(base=TGT[k]['T5_indoor_300lx_10h_days_from_full'],
                     wing_dark_no_diode=_t5(k, ws['no diode | wing 0 x lid']['desk_300lx_uW']),
                     wing_dark_with_diode=_t5(k, ws['RB751 diode on PV_W+ | wing 0 x lid']['desk_300lx_uW']),
                     edge_dominated_shunt=_t5(k, se['edge-dominated shunt']['desk_300lx_uW']),
                     office_downlights=_t5(k, se['office downlights']['desk_300lx_uW'])),
        cold_start=dict(need_uA=21.4, wing_lit_desk=EN['cold_start_uA'][ps], wing_dark_no_diode=ws['no diode | wing 0 x lid']['cold_start_uA_200lx'],
                        wing_dark_with_diode=ws['RB751 diode on PV_W+ | wing 0 x lid']['cold_start_uA_200lx'],
                        lux_needed_wing_dark_no_diode=ws['no diode | wing 0 x lid | lux for 21.4 uA'],
                        lux_needed_wing_dark_with_diode=ws['RB751 diode on PV_W+ | wing 0 x lid | lux for 21.4 uA'],
                        lux_needed_wing_lit=ws['no diode | wing 0.867 x lid | lux for 21.4 uA'],
                        edge_dominated_shunt_uA=se['edge-dominated shunt']['cold_start_uA_200lx']))
# USB-C charge 0 -> 85 % (T7), constant-current AND constant-voltage phase (physics P-11): port of v3/verify/physics/scripts/usb_t7.py
# (own equivalent-circuit model of the physics lens; BQ25170 SLUSDJ8A p.6-7: KISET 270/300/330, VREG +-0.5 % at 25 C, +-0.8 % over T,
# ITERM 10 %); path R112 1.000 + protector 0.045 + strap 0.1 ohm; generic LiCoO2 OCV (E); ohmic 0.75 ohm + two RC (E); MON load in parallel
_OCV_A = [(0.00, 3.00), (0.01, 3.20), (0.02, 3.30), (0.035, 3.40), (0.05, 3.46), (0.075, 3.53), (0.10, 3.59), (0.15, 3.65), (0.20, 3.69),
          (0.25, 3.72), (0.30, 3.745), (0.40, 3.785), (0.50, 3.825), (0.60, 3.87), (0.70, 3.93), (0.80, 4.00), (0.90, 4.08), (0.95, 4.13), (1.00, 4.19)]
def _ocv(s_): x, y = zip(*_OCV_A); return float(np.interp(s_, x, y))
def usb_charge_h(i_set, vreg, cap=43.0, r0=0.75, r1=0.6, t1=60.0, r2=0.8, t2=1500.0, r_path=1.15, i_load=63e-6, dt=2.0):
    xs = np.linspace(0, 0.2, 2001); s_ = float(xs[np.argmin([abs(_ocv(v) - 3.31) for v in xs])])
    v1 = v2 = q = t = 0.0; Q = cap * 3.6; target = 0.85 * cap * 3.6
    while q < target and t < 6 * 3600:
        icc = i_set - i_load
        if _ocv(s_) + v1 + v2 + icc * (r0 + r_path) <= vreg: ic = icc
        else: ic = max(min((vreg - _ocv(s_) - v1 - v2) / (r0 + r_path), icc), 0.0)
        v1 += dt * (ic * r1 - v1) / t1; v2 += dt * (ic * r2 - v2) / t2; s_ += ic * dt / Q; q += ic * dt; t += dt
        if ic + i_load < 0.1 * i_set: break
    return round(t / 3600, 2)
USB_T7 = {'constant-current phase only (integrate stage)': {f'{i:.2f} mA': round(0.85 * 43.0 / i, 2) for i in (18.52, 16.67, 14.85)},
          'CC + CV, fresh cell 25 C, VREG 4.10 V': {f'{i * 1e3:.2f} mA': usb_charge_h(i, 4.10) for i in (18.52e-3, 16.67e-3, 14.85e-3)},
          'CC + CV, 14.85 mA, VREG 4.067 V (-0.8 %)': usb_charge_h(14.85e-3, 4.067),
          'CC + CV, aged / 15 C cell (ohmic 1.0, RC x1.5), 14.85 mA, VREG 4.067 V': usb_charge_h(14.85e-3, 4.067, r0=1.0, r1=0.9, r2=1.2),
          'CC + CV, cold 5-10 C cell (ohmic 1.5, RC x2.5), 14.85 mA, VREG 4.067 V': usb_charge_h(14.85e-3, 4.067, r0=1.5, r1=1.5, r2=2.0),
          'note': 'E: equivalent-circuit model ported from the physics lens (usb_t7.py: 2.00 / 2.21 / 2.47 h fresh, 2.75 h at VREG -0.8 %, 3.04 h cold)'}
USB_T7_70 = {f'{i:.1f} mA': round(0.85 * 70.0 / i, 2) for i in (300 / 11.0 * 0.9, 300 / 11.0, 300 / 11.0 * 1.1)}   # RISET 11 k for the 70 mAh option (CC only)
TOPUP_10MIN_DAYS = round(16.67 * 10 / 60 / (TGT['V3-R']['loads_uW']['MON'] * 1e-3 / 3.7 * 24), 2)    # 2.78 mAh / daily MON charge
# SIM-05 weeks from 50 % SoC
WK = {}
for k in ('V2-B', 'V3-R', 'V3-N', 'V3-P'):
    c = CONFIGS[k]; cfg = dict(cell=c['cell'], display=False, usb=c['usb'], asbuilt=c.get('asbuilt', True), pulldown_fix=c.get('pulldown_fix', False))
    p_mon = VE.loads(cfg)[0]['MON']; U = VE.usable_Wh(c['cell']); T = EN['tables'][VE.tkey(c['pvset'], c['r_lim'])]
    don = VE.DISP['typ']['on'] if c['display'] else 0.0; doff = VE.DISP['typ']['rtw'] if c['display'] else 0.0
    for w in VE.WEEKS:
        r = VE.sim_week(VE.trace(w), T, p_mon, U, p_disp_on=don, p_disp_rtw=doff)
        WK[f'{k} | {w}'] = r
    if c.get('pvset_other_wrist'):
        for w in ('W1_office', 'W2_indoor_300lx', 'W6_campus', 'W7_low_outdoor_office'):
            WK[f'{k} (other wrist) | {w}'] = VE.sim_week(VE.trace(w), EN['tables'][VE.tkey(c['pvset_other_wrist'], c['r_lim'])], p_mon, U, p_disp_on=don, p_disp_rtw=doff)
# charge-current bound (hardware, every source): PV via R_LIM; USB via ISET; both at once is prevented by Q8
# fix stage: worst at -10 C (REDESIGN convention) and at -20 C, k 0.72, for each R_LIM; Voc from the data-sheet slope (P-1)
CB = {}
for s_, v in EN['charge_bound'].items():
    worst = {}
    for rl in sorted({kk.split(' | ')[0] for kk in v}):
        for tc in ('-10 C', '-20 C'):
            kk = f'{rl} | 1.2 sun, strings at {tc} | k 0.72'
            worst[f'{rl} | {tc}'] = dict(case=kk, **v[kk])
        nom = {kk: vv for kk, vv in v.items() if kk.startswith(rl + ' |') and kk.endswith('k 0.8') and '-20 C' not in kk}
        wn = max(nom, key=lambda kk: nom[kk]['c_rate']); worst[rl + ' nominal k 0.80'] = dict(case=wn, **nom[wn])
    CB[s_] = worst
OUT['energy'] = dict(r_lim_ohm=VE.R_LIM, si_area_cm2=EN['si_area_cm2'], check_lid_alone=EN['check_lid_alone'],
                     harvest_uW_into_battery=EN['scen'], targets=TGT, loads_breakdown_uW_V3R=LOADS_BREAKDOWN,
                     usb_t7_h_43mAh=USB_T7, usb_t7_h_70mAh_riset_11k=USB_T7_70, usb_10min_topup_days_of_MON_V3R=TOPUP_10MIN_DAYS,
                     weeks_from_50pct=WK, charge_bound=CB, cold_start_uA_at_0V70_200lx=EN['cold_start_uA'], dock=EN['dock'],
                     cold_start_dissipation_in_R_LIM=EN['cold_start_rlim_dissipation'],
                     wing_light_study=EN['wing_light_study'], deep_discharge=EN['deep_discharge'], hot_lid_045sun_uW=EN['hot_lid_045sun'],
                     sensitivity_points=EN['sensitivity'], sensitivities_T3_T5_cold_start=SENS,
                     voc_convention='fix stage (P-1): Voc shift = -6.96 mV/K x (T - 25 C) per 4-cell string on the 25 C base fit (KXOB25-03X4TF '
                                    'data sheet p.1): 0 C +0.174 V, -10 C +0.244 V, -20 C +0.313 V (was +0.37 / +0.44 V on the same base)',
                     r_lim_by_config={k: v['r_lim'] for k, v in CONFIGS.items()},
                     r_lim_parts=dict(R22_0603='C23345 22 ohm 0603 100 mW (netlist R130; V2-B only)',
                                      R22_1206='C17958 UNI-ROYAL 1206W4F220JT5E 22 ohm 1 % 250 mW, Basic, 549,459 in stock (JLC API 2026-11-13 14:11 UTC)',
                                      R24_1206='C17963 UNI-ROYAL 1206W4F240JT5E 24 ohm 1 % 250 mW (V3-N option), 20,141 in stock (JLC API 2026-11-13 10:18 UTC)',
                                      courtyard_1206_mm2='10.35 E (4.5 x 2.3 mm: land + 0.25 mm, parts.json rule)'),
                     cell_rating=dict(c_rate_max=0.5, note='GMB201030 0.5 C rapid = 21.5 mA, 0.2 C standard (REDESIGN 5.6, sister spec p.3)'),
                     usb_charge_c_rate=dict(typ=round(16.67 / 43, 3), max=round(18.52 / 43, 3)),
                     usb_deep_cell_c_rate='below 2.2 V on OUT the BQ25170 charges at 12 / 16 / 20 mA = 0.28-0.47 C (SLUSDJ8A p.7 via usbc lane)')

# ================================================================================================= 5b. feature waterfall
def thick(c):
    if c['cell_where'] == 'pod': return STACK['V2-B']['total']
    return STACK['V3-R']['total']          # 4.65: PV lid column = display window column over the low-part zone
_b = dict(CONFIGS['V2-B'])
STEPS = [
 ('0 V2-B as designed (REDESIGN planning loads, R_LIM 22)', dict(_b)),
 ('1 V2-B with the as-built loads of v2/design (G-4 EN hold, R131, R108)', dict(_b, asbuilt=True)),
 ('2 + R131 and R108 changed to 10 MOhm (V3 fix, C144806)', dict(_b, asbuilt=True, pulldown_fix=True)),
 ('3 cell moved to a white capsule on strap root A (V2-B lid kept)', dict(_b, asbuilt=True, pulldown_fix=True, cell_where='strap',
     strap_conductors=dict(root_A=['BATT_P', 'GND', 'NTC', 'GND'], root_B=[]))),
 ('4 + one c-Si wing on root B (root B core and textile booked here; R130 22 ohm in 1206)', dict(_b, asbuilt=True, pulldown_fix=True, cell_where='strap',
     pvset='LID4+WR31', wing='one wide (root B)', r_lim=22.0, r130_1206=True,
     strap_conductors=dict(root_A=['BATT_P', 'GND', 'NTC', 'GND'], root_B=['PV_W+', 'GND']))),
 ('5 + USB-C tab on root A and BQ25170 in the pod = V3-N', dict(CONFIGS['V3-N'])),
 ('6 + display LS011B7DH03 (C1 lid: 4 stacked strips, 48 % of the V2-B silicon; soldered FPC; skin-hot LED kept) = V3-R', dict(CONFIGS['V3-R'])),
]
WF = []
for lab, c in STEPS:
    t = targets(c)[0]; a = area_config(c); pm = pod_mass(c); sm = strap_mass(c)
    smx = strap_mass(c, max_material=True); pmx = pod_mass_max(c)
    WF.append(dict(step=lab, pod_thickness_mm=thick(c), pod_g=pm['TOTAL'], strap_g=sm['TOTAL'], worn_g=round(pm['TOTAL'] + sm['TOTAL'], 1),
                   worn_g_max_material=round(pmx + smx['TOTAL'], 1),
                   utilisation=a['utilisation'], T1_d=t['T1_MON_dark_d'], T1_policy_d=t.get('T1_with_dark_policy_d'), T3_min=t['T3_min_day_045sun'],
                   T5_d=t['T5_indoor_300lx_10h_days_from_full'], T6_ship_d=t['T6_SHIP_d'], T6_shelf_d=t['T6_SHELF_d'], T2_d=t['T2_ECO_d'],
                   pv_set=t['pv_set'], cold_start_uA=EN['cold_start_uA'].get(c['pvset'])))
OUT['feature_waterfall'] = WF

# ================================================================================================= 6. thermal (lumped, E)
TH = {}
# (a) pod top in full sun, W-C band, 35 C air, perfusion 3e-3: display-lane linearisation of the review 3-D model of V2-B (9.5 K/W)
K_LIN, Q0, T0 = 9.5, 0.604, 41.17
q_c1 = {a: DISP['heat'][f'C1, display alpha {a:.2f}']['absorbed_W'] for a in (0.45, 0.60, 0.75)}
TH['pod_top_linearised_on_V2B_geometry'] = {f'C1 top, display alpha {a}': round(T0 + K_LIN * (q - Q0), 2) for a, q in q_c1.items()}
TH['pod_top_linearised_on_V2B_geometry']['V2-B lid'] = T0
# (b) three-node lumped model (air - lid - skin - core), calibrated on the review numbers for V2-B (lid 48.53 C, skin 41.17 C, 0.604 W)
T_AIR, T_CORE, T_LID0 = 35.0, 37.0, 48.53
G_UP = 0.731 / (61.42 - 35.0)                          # W/K, lid to air (v2_calc.py G_UP from SIM-13 v1)
q_up0 = G_UP * (T_LID0 - T_AIR); q_dn0 = Q0 - q_up0
G_DN0 = q_dn0 / (T_LID0 - T0); G_T = q_dn0 / (T0 - T_CORE)
def g_gap(mm, area_mm2): return (0.026 / (mm * 1e-3) + 6.0) * area_mm2 * 1e-6     # still air + radiation, W/K
g_v2b = g_gap(0.80, 666.0) + g_gap(0.20, 374.0)        # lid to board strip 0.80 mm (0.65 spare + 0.15), lid to cell 0.20 mm
R_REST = 1.0 / G_DN0 - 1.0 / g_v2b
def solve(q, g_dn):
    # q = G_UP (Tl - Ta) + g_dn (Tl - Ts);  g_dn (Tl - Ts) = G_T (Ts - Tc)
    a11, a12, b1 = G_UP + g_dn, -g_dn, q + G_UP * T_AIR
    a21, a22, b2 = g_dn, -(g_dn + G_T), -G_T * T_CORE
    det = a11 * a22 - a12 * a21; tl = (b1 * a22 - a12 * b2) / det; ts = (a11 * b2 - a21 * b1) / det
    return round(tl, 2), round(ts, 2)
def g_dn(gaps):
    g = sum(g_gap(mm, a) for mm, a in gaps); return 1.0 / (1.0 / g + R_REST)
cal = solve(Q0, g_dn([(0.80, 666.0), (0.20, 374.0)]))
chk = solve(Q0, g_dn([(1.30, 666.0), (0.70, 374.0)]))      # review: lid gap +0.5 mm -> skin 40.23 C
TH['lumped_3node'] = dict(
    method='air - lid - skin - core network; G_up from SIM-13 v1 (v2_calc.py), G_down and tissue conductance fitted to the review 3-D '
           'numbers for V2-B (lid 48.53 C, skin 41.17 C, 0.604 W absorbed); lid-to-board gap as still air + radiation over 1040 mm2',
    G_up_W_per_K=round(G_UP, 4), G_down_V2B_W_per_K=round(G_DN0, 4), G_tissue_W_per_K=round(G_T, 4),
    check_V2B_calibration=cal, check_V2B_lid_gap_plus_0p5mm=dict(model=chk, review_3d_skin=40.23),
    V3N_full_lid_on_4p65mm_pod=solve(Q0, g_dn([(0.15, 1040.0)])),
    V3R_C1_top_alpha_0p60_on_4p65mm_pod=solve(q_c1[0.60], g_dn([(0.15, 1040.0)])),
    V3R_C1_top_alpha_0p75=solve(q_c1[0.75], g_dn([(0.15, 1040.0)])),
    V3P_C1_top_alpha_0p60_cell_in_pod=solve(q_c1[0.60], g_dn([(0.80, 666.0), (0.20, 374.0)])),
    note='(lid C, skin C); a trend estimate only: SIM-13 must run each geometry')
# (c) free-span elements in perpendicular full sun (1000 W/m2), 35 C air, h_top 10 + 6.3 W/m2K (strap lane), underside to skin at 36 C
def free_span(alpha, gap_mm=1.5, h_conv=10.0, eta_el=0.0):
    h_top = h_conv + 6.3; h_bot = 0.026 / (gap_mm * 1e-3) + 6.0
    t = (alpha * 1000.0 * (1 - eta_el) + h_top * 35.0 + h_bot * 36.0) / (h_top + h_bot)
    return round(t, 1), round(h_bot * (t - 36.0), 0)
TH['free_span_1D'] = {
    'black c-Si wing, W-C (no harvest), wedge 1.5 mm': free_span(0.90), 'black c-Si wing, wind h 20': free_span(0.90, h_conv=20.0),
    'black c-Si wing, wedge 3.0 mm (bar end)': free_span(0.90, gap_mm=3.0), 'white capsule alpha 0.15': free_span(0.15),
    'white capsule alpha 0.30 (aged / dirty)': free_span(0.30), 'cell under a black wing (rejected)': free_span(0.90),
    'columns': '(element temperature C, heat into the skin under the wedge W/m2); bare skin in sun with sweating suppressed is 43.9 C (strap lane 6)'}
TH['skin_under_strap_PV_1D_bound_strap_lane'] = dict(model=STRAP['heat']['model'], skin_C_perfusion_1e3_3e3_6e3=STRAP['heat']['skin_C_perfusion_1e3_3e3_6e3'],
                                                      conclusion=STRAP['heat']['conclusion'])
TH['usb_charging_usbc_lane_3D'] = dict(charger_mW=dict(typ=21.7, worst_fast=50.0, worst_trickle=70.0),
                                       skin_rise_K_indoors=dict(typ='0.19-0.27', worst_50mW='0.44-0.61', trickle_70mW='0.63-0.86'),
                                       skin_rise_K_sunny_window_WC='0.21-0.79', junction_rise_K_at_50mW=3.8,
                                       note='in V3-R the cell is in the root-A capsule, away from the charger (the charger heat no longer reaches the cell)')
# (d) fix stage (P-5, RQ-07): air gap under the free span per wing sub-cell and the 1-D skin temperature under it. Port of the physics
# lens's wing_thermal.py (geometry re-implemented from the strap lane's wrist_light.py; Pennes 1-D tissue; no sweating, no lateral
# spreading). Root = wing laminate on the documented route 1.75 mm (k 0.3 W/mK, E) + TPU core 1.20 mm (k 0.2, strap lane).
def _ellipse_axes(C, q=0.68):
    def per(a):
        b = q * a; hh = ((a - b) / (a + b)) ** 2
        return math.pi * (a + b) * (1 + 3 * hh / (10 + math.sqrt(4 - 3 * hh)))
    lo, hi = 1.0, C
    for _ in range(100):
        m = 0.5 * (lo + hi)
        if per(m) < C: lo = m
        else: hi = m
    a = 0.5 * (lo + hi); return a, q * a
def _free_span_geometry(C, ts=1.5):
    a, b = _ellipse_axes(C)
    def pt(t, off=0.0):
        n = np.array([math.sin(t) / a, math.cos(t) / b]); n /= np.linalg.norm(n)
        return np.array([a * math.sin(t), b * math.cos(t)]) + off * n, n
    P0 = np.array([16.0 + 2.5, b + 1.0])
    f = lambda t: float(np.dot(P0 - pt(t, ts / 2)[0], pt(t, ts / 2)[1]))
    lo, hi = 0.05, math.pi / 2 + 0.5
    for _ in range(80):
        m = 0.5 * (lo + hi)
        if f(lo) * f(m) <= 0: hi = m
        else: lo = m
    t0 = 0.5 * (lo + hi); q0, n0 = pt(t0, ts / 2); free = float(np.linalg.norm(P0 - q0))
    tg = np.linspace(0.0, math.pi, 40001); skin = np.stack([a * np.sin(tg), b * np.cos(tg)], 1)
    def gap(sv):
        pc = P0 + (q0 - P0) * (min(sv, free) / free)
        return float(np.min(np.linalg.norm(skin - pc, axis=1)) - ts / 2)
    return dict(free=free, tilt=math.degrees(math.acos(abs(n0[1]))), gap=gap)
def _h_tissue(w): return math.sqrt(0.37 * w * 4.0e6)
def skin_under(alpha, r_root, gap_mm, w=3e-3, G=1000.0, h_top=16.3, t_air=35.0, t_core=37.0):
    r = r_root + 1.0 / (0.026 / ((gap_mm + 0.05) * 1e-3) + 6.0); ht = _h_tissue(w)
    a11, a12, b1 = h_top + 1 / r, -1 / r, alpha * G + h_top * t_air
    a21, a22, b2 = -1 / r, 1 / r + ht, ht * t_core
    det = a11 * a22 - a12 * a21
    tt = (b1 * a22 - a12 * b2) / det; ts_ = (a11 * b2 - a21 * b1) / det
    return round(tt, 1), round(ts_, 1)
R_WING_DOC = 1.75e-3 / 0.3 + 1.20e-3 / 0.2
WING_SKIN = {}
for C in (140.0, 165.0, 200.0):
    g = _free_span_geometry(C); cells = {}
    for i in range(4):
        s0, s1 = 2 + 3 * i, 2 + 3 * i + 2.7
        gm = float(np.mean([g['gap'](x) for x in np.linspace(s0, s1, 7)]))
        cells[f'sub-cell {i + 1} (s {s0:g}-{s1:g})'] = dict(gap_mean_mm=round(gm, 2), **{f'skin_C_w{w:g}': skin_under(0.90, R_WING_DOC, gm, w=w)[1] for w in (1e-3, 3e-3, 6e-3)})
    WING_SKIN[f'{C:g} mm wrist'] = dict(free_span_mm=round(g['free'], 2), tilt_deg=round(g['tilt'], 1),
                                        gap_mm_at_s={f's {x:g}': round(g['gap'](x), 2) for x in (0.0, 2.0, 5.0, 8.0, 10.0, 11.0, 13.7)}, sub_cells=cells)
TH['wing_skin_per_sub_cell_1D'] = dict(model='port of verify/physics/scripts/wing_thermal.py; alpha 0.90, 1000 W/m2 normal, 35 C air, h 10 + 6.3, '
                                             'root 1.75 mm laminate + 1.20 mm core; E', wrists=WING_SKIN,
                                       bare_skin_alpha0p6_no_sweat_C={f'w{w:g}': round((0.6 * 1000 + 16.3 * 35 + _h_tissue(w) * 37) / (16.3 + _h_tissue(w)), 1) for w in (1e-3, 3e-3, 6e-3)},
                                       limit_C=43.0, reading='the outer two sub-cells sit within 1 mm of the skin on every wrist: SIM-13 case; '
                                       'mitigation: active wing only to s about 8-10 mm, or a light outer zone (alpha <= 0.3)')
TH['usb_tab_on_skin_1D'] = {f'alpha {al}': {f'skin_C_w{w:g}': skin_under(al, 4.6e-3 / 0.25, 0.0, w=w)[1] for w in (1e-3, 3e-3, 6e-3)} for al in (0.9, 0.3, 0.15)}
# capsule temperature over the strap lane's convection set and the wedge range (RQ-R2): the alpha <= 0.15 rule must hold over life
TH['capsule_grid_C'] = {f'alpha {al} | h_conv {hc} | gap {gp} mm': free_span(al, gap_mm=gp, h_conv=hc)[0]
                        for al in (0.15, 0.30) for hc in (5.0, 10.0, 20.0) for gp in (0.5, 1.5, 3.0)}
# winter (P-8): lumped worn-capsule estimate of the physics lens (verify/physics/evidence/thermal_check.json, quoted, E)
TH['winter_capsule_physics_lens'] = {'-10 C air, wind h 30, no sun, wedge 1.5 / 3.0 mm': '2.1 / -0.2 C', '-20 C air, wind h 40, no sun, wedge 3.0 mm': '-10.3 C',
                                     '-10 C air, h 30, 600 W/m2 sun, alpha 0.15, wedge 1.5 mm': '3.9 C', 'time constant': 'about 80 s (E)',
                                     'cell limits (Markyn 201021 p.4)': 'charge 0-45 C, < 0 C prohibited; discharge -10 to 60 C',
                                     'consequence': 'the 0 C PV inhibit (ARCH 4.4 rule 5) stops PV charging in cold outdoor time; with the MCU off '
                                                    'nothing stops the BQ25570 charging a sub-zero cell (O-2)'}
OUT['thermal'] = TH

# ================================================================================================= 7. RF numbers (E)
C0, F = 299.792458, 2.44
RF = dict(lambda0_mm=round(C0 / F, 1), half_wave_mm={f'eps_eff {e}': round(C0 / F / 2 / math.sqrt(e), 1) for e in (1, 3, 10, 20)},
          quarter_wave_mm={f'eps_eff {e}': round(C0 / F / 4 / math.sqrt(e), 1) for e in (1, 3, 10, 20)},
          strap_conductor_lengths_mm={'root A capsule tail (bar to capsule far end)': 14, 'root A USB tab feed (bar to receptacle)': 36,
                                      'root B wing tail and string (bar to s 14)': 14, 'wing string across the root (31 mm active)': 31,
                                      'display FPC (panel to land, fold)': 10, 'display panel long side': 32, 'cell foil (capsule)': 30},
          eps_eff_for_quarter_wave_resonance={f'{n} {L_} mm': round((C0 / F / 4 / L_) ** 2, 2) for n, L_ in
                                              (('root A capsule tail', 14), ('root B wing tail', 14), ('USB feed', 36), ('wing string', 31), ('cell foil', 30))},
          distances_mm={'display glass edge to the 5 x 3 mm antenna keep-out, in plan (fix stage: window Y 6.0-20.0; was 0.5 mm at Y 5.0, not the 2.5 mm '
                        'the display lane assumed with the keep-out top at Y 3.0)': 1.5,
                        'PV strips to the keep-out (REDESIGN 5.3)': 1.5,
                        'wing -X end to the keep-out corner (root B on the antenna side, wing X 6-34)': 4.5,
                        'root A capsule (cell foil) to the antenna corner: root A on the far long wall': 30.0},
          note='E (fix stage, physics P-7): every tail is tied to the board ground at the entry, so it acts as a monopole on the pod ground and '
               'resonates first at a QUARTER wave (30.7 mm in air at 2.44 GHz): the 14 mm tails at eps_eff about 4.8, the USB feed, the wing string '
               'and the cell foil already near eps_eff 1. SIM-10/11 must model each tail with its GND conductor. One 0402 RF link per conductor, '
               'GND included, is reserved at the entry lands (FB1-FB7 in V3-R); a common-mode choke if SIM-10/11 asks; SIM-08 checks the ESD return')
OUT['rf'] = RF

# ================================================================================================= 8. ASCII plan views (1 char = 1 mm in X, 1 line = 2 mm in Y)
def raster(lx, rects, title, ly=32.0, dy=1.0):
    """rects: (char, x0, x1, y0, y1) in mm, later entries overwrite earlier ones; outline drawn with R6 corners"""
    nx, ny = int(round(lx)), int(round(ly / dy))
    g = [[' '] * nx for _ in range(ny)]
    for (ch, x0, x1, y0, y1) in rects:
        for j in range(ny):
            yc = (j + 0.5) * dy
            if not (y0 <= yc <= y1): continue
            for i in range(nx):
                xc = i + 0.5
                if x0 <= xc <= x1: g[j][i] = ch
    rows = []
    for j in range(ny - 1, -1, -1):
        row = ''.join(g[j])
        rows.append('|' + row + '|')
    top = '+' + '-' * nx + '+'
    return [title, top] + rows + [top]
LEG = 'Legend (top view): P / p = PV strips (alternating letters show the strips), D = display window (panel 32 x 14 mm), E = E3 titanium strip ' \
      'on the top rim, A = antenna keep-out (board, seen through the lid), . = lid or cover glass outside the PV and the window. Y = 0 at the bottom ' \
      '(the antenna long wall, strap root B); Y = 32 at the top (strap root A). Board view: see its own title.'
def top_view(k):
    c = CONFIGS[k]; lx = c['pod_len']; r = [('.', 0.4, lx - 2.5, 0.4, 31.6)]
    if c['top'] == 'LID4':
        for i in range(4): r.append(('P' if i % 2 == 0 else 'p', 3.7, 31.4, 6.0 + i * 5.6, 6.0 + i * 5.6 + 5.2))
    else:     # fix stage (P-3, P-6): four 27.7 x 2.5 mm strips along X, stacked in Y from 20.2 mm (gaps 0.27 mm); panel Y 6.0-20.0
        for i in range(4):
            y0 = 20.2 + i * 2.77
            r.append(('P' if i % 2 == 0 else 'p', 3.7, 31.4, y0, y0 + 2.5))
        r.append(('D', 1.0, 33.0, 6.0, 20.0))
    r.append(('A', 1.5, 6.5, 1.5, 4.5)); r.append(('E', lx - 3.5, lx, 3.0, 29.0)); r.append(('c', 14.5, 25.5, 12.0, 19.0)) if False else None
    return raster(lx, r, f'{k} top face ({lx:.0f} x 32 mm case; lid set back 2.5 mm at the E3 end)')
def board_view(k):
    c = CONFIGS[k]; lx = c['pod_len']; r = [('.', 1.5, lx - 1.5, 1.5, 30.5)]
    if c['cell_where'] == 'pod': r.append(('C', 1.5, 35.5, 19.5, 30.5))
    if c['display'] and c['cell_where'] == 'strap': r.append(('l', 1.5, 33.5, 5.5, 20.5))
    r.append(('A', 1.5, 6.5, 1.5, 4.5))
    r.append(('c', 14.5, 25.5, 12.0, 19.0))
    if c['cell_where'] == 'strap': r.append(('a', 10.0, 18.0, 29.0, 30.5)); r.append(('b', 14.0, 20.0, 1.5, 3.0))
    else: r.append(('b', 14.0, 20.0, 1.5, 3.0)); r.append(('a', lx - 10.0, lx - 4.0, 29.0, 30.5))   # root A tail enters beyond the cell bay
    return raster(lx, r, f'{k} main board zones ({lx - 3:.0f} x 29 mm board): . = parts up to 1.05 mm, l = low-part zone under the display '
                         f'(<= 0.70 mm), C = cell cut-out, A = antenna keep-out, c = PPG cap / optics (skin face), a/b = root A / root B entry lands')
PLAN = {k: dict(top=top_view(k), board=board_view(k)) for k in ('V2-B', 'V3-R', 'V3-N', 'V3-P')}
STRAP_VIEW = [
 'Strap roots of V3-R, unrolled along s (distance from the strap bar, 1 char = 1 mm); widths along the forearm in brackets',
 'root A (far long wall, Y = 32):  bar|hinge|[ capsule: cell 43 mAh + PCM end (protector, F1) + NTC, white top ]|~ flex hinge ~|[ USB-C tab, mouth to -X ]|~~ textile band ~~',
 '                                 s: 0  2 ............................................... 13.9 ............. 23.5 .................... 35.5  (capsule 38.4 x 11.9 x 3.5 mm, tab 13 x 12 x 4.6 mm)',
 'root B (antenna long wall, Y = 0): bar|hinge|[ c-Si wing: 4 sub-cells 2.7 mm along s, 31 mm across ]|~~~~ textile band ~~~~',
 '                                 s: 0  2 ........................................ 13.7 16  (root 35 mm wide, active X 4.5-35.5 mm; laminate 1.75 mm planning, 0.87 mm RFQ target)',
 'Free span (flat when worn): 14.0 / 14.7 / 15.7 mm on 140 / 165 / 200 mm wrists, tilt 61 / 51 / 42 deg (strap lane 3.1).']
OUT['plan_views'] = dict(legend=LEG, configs=PLAN, strap_v3r=STRAP_VIEW, scale='1 character = 1 mm in X (along the forearm, elbow at the left), 1 line = 1 mm in Y')

# ================================================================================================= 8b. one summary row per configuration
SUMMARY = {}
for k in ('V2-B', 'V3-R', 'V3-N', 'V3-P'):
    t = TGT['V2-B planning (REDESIGN convention, R_LIM 22)'] if k == 'V2-B' else TGT[k]
    a = AREA[k]; ms = MASS[k]; st = STACK[k]; v = VOL[k]
    SUMMARY[k] = dict(name=CONFIGS[k]['name'], pod_thickness_mm=st['total'], pod_thickness_if_no_low_zone_mm=st.get('fallback_no_low_zone'),
                      pod_thickness_zif_option_mm=st.get('zif_option_total_mm'),
                      pod_thickness_lid_at_P121_mm=st['lid_at_P121_buildup'], pod_thickness_lid_at_P121_upper_tol_mm=st['lid_at_P121_upper_tolerance'],
                      worst_case_all_tol_mm=st['worst_case_all_tolerances'],
                      case_mm=f"{CONFIGS[k]['pod_len']:.1f} x 32", pod_g=ms['pod_g'], strap_g=ms['strap_g'], worn_g=ms['worn_g'],
                      pod_g_max_material=ms['pod_g_max_material'], worn_g_max_material=ms['worn_g_max_material'],
                      pod_body_cm3=v['pod_body_cm3'], rigid_total_cm3=v['total_rigid_cm3'], utilisation=a['utilisation'],
                      utilisation_v1_bbox=a['utilisation_on_v1_bbox_measure'], gate1=('pass' if a['gate1_pass'] else 'FAIL'),
                      si_area_cm2=EN['si_area_cm2'][CONFIGS[k]['pvset']], r_lim_ohm=CONFIGS[k]['r_lim'],
                      T1_d=t['T1_MON_dark_d'], T1_policy_d=t.get('T1_with_dark_policy_d'), RAW_d=t['RAW_WC_d'], T2_d=t['T2_ECO_d'],
                      T3_min=t['T3_min_day_045sun'], T4=t['T4_ECO_1000lx_10h'], T5_d=t['T5_indoor_300lx_10h_days_from_full'],
                      T6_shelf_d=t['T6_SHELF_d'], T6_ship_d=t['T6_SHIP_d'],
                      T7_h=((f"USB-C CC+CV {min(USB_T7['CC + CV, fresh cell 25 C, VREG 4.10 V'].values()):.2f}-"
                             f"{max(USB_T7['CC + CV, fresh cell 25 C, VREG 4.10 V'].values()):.2f} (fresh, 25 C); "
                             f"{USB_T7['CC + CV, 14.85 mA, VREG 4.067 V (-0.8 %)']:.2f} at VREG -0.8 %; "
                             f"{USB_T7['CC + CV, cold 5-10 C cell (ohmic 1.5, RC x2.5), 14.85 mA, VREG 4.067 V']:.2f} cold cell")
                            if CONFIGS[k]['usb'] else 'dock 3.38 (CALC.md 3)'),
                      charge_bound_C_minus10=(CB[CONFIGS[k]['pvset']][f"R{CONFIGS[k]['r_lim']:g} | -10 C"]['c_rate'] if CONFIGS[k]['pvset'] in CB else None),
                      charge_bound_C_minus20=(CB[CONFIGS[k]['pvset']][f"R{CONFIGS[k]['r_lim']:g} | -20 C"]['c_rate'] if CONFIGS[k]['pvset'] in CB else None),
                      cold_start_uA=EN['cold_start_uA'][CONFIGS[k]['pvset']],
                      office_week_W1=WK[f'{k} | W1_office']['days_from_full_if_negative'], campus_week_W6=WK[f'{k} | W6_campus']['days_from_full_if_negative'],
                      indoor_only_W2_days_from_full=WK[f'{k} | W2_indoor_300lx']['days_from_full_if_negative'],
                      winter_office_W7_days_from_full=WK[f'{k} | W7_low_outdoor_office']['days_from_full_if_negative'],
                      worst_stack_T1_d=(TGT[k + ' | worst stack (LED gain 1, maximum currents, retention limit)']['T1_MON_dark_d'] if k != 'V2-B' else 14.0),
                      max_currents_T2_d=(TGT[k + ' | maximum currents (protector 6 uA, USB 0.6 + 1 uA, display at panel maximum)']['T2_ECO_d'] if k != 'V2-B' else None))
OUT['summary'] = SUMMARY

# ================================================================================================= 9. write
OUT['meta'] = dict(date='2026-11-13', stage='V3 integrate + fix stage (v3/fix/CHANGELOG.md)', configs={k: v for k, v in CONFIGS.items()}, configs_note=CONFIGS_NOTE,
                   markers='V = read in a source or project file; E = estimate / model output; U = unknown',
                   reproduce='python3 -B v3/integrate/v3_calc.py [--force]',
                   energy_model='v3/integrate/energy/v3_energy.py on copies of sim/energy_budget.py, sim/power/common, redesign/energy_calc, '
                                'redesign/v2_calc.py and the strap-lane models; R_LIM 22 ohm; harvest into the battery at 3.8 V')
json.dump(OUT, open(os.path.join(HERE, 'v3_calc_copy.json'), 'w'), indent=1, default=float)   # DECIDE COPY: own folder

if __name__ == '__main__':
    print('stacks:', {k: (v['total'], v.get('fallback_no_low_zone'), v['lid_at_P121_buildup']) for k, v in STACK.items()})
    print('capsule fit:', CAPSULE_FIT)
    for k, v in AREA.items():
        if 'utilisation' in v: print(f'area {k:34s} cy {v["courtyard_mm2"]:6.1f} / place {v["placement_area_mm2"]:6.1f} = {v["utilisation"]:.3f} (v1 bbox {v["utilisation_on_v1_bbox_measure"]:.3f}) pass {v["gate1_pass"]}')
    print('V3-P pod length', LEN_P, 'mm; with 0201', LEN_P0201)
    print('low zone', {a: b for a, b in AREA['V3-R low-part zone'].items() if a not in ('tall_parts', 'rule')})
    print('mass', {k: (v['pod_g'], v['strap_g'], v['worn_g']) for k, v in MASS.items()})
    print('volume', VOL)
    for k, t in TGT.items(): print(f'{k}:', {a: b for a, b in t.items() if a != 'loads_uW'}, t['loads_uW'])
    print('USB T7', USB_T7, USB_T7_70, '10 min top-up days', TOPUP_10MIN_DAYS)
    for k, r in WK.items(): print(f'{k:42s} harv {r["harvest_mWh_day"]:7.2f} load {r["load_mWh_day"]:5.2f} minSoC {r["min_soc"]:.2f} end {r["end_soc"]:.2f} empty {r["days_to_empty_from_50pct"]}')
    for s_, v in CB.items(): print('charge bound', s_, {a: b['c_rate'] for a, b in v.items()})
    for k, v in SENS.items(): print('SENS', k, v)
    print('wing study V3-R', json.dumps(EN['wing_light_study']['LID2+WR31'], indent=0)[:2500])
    print('deep discharge', EN['deep_discharge'])
    print('hot lid', EN['hot_lid_045sun'])
    print('mass max', {k: (v['pod_g_max_material'], v['worn_g_max_material']) for k, v in MASS.items()})
    print('wing skin', json.dumps(TH['wing_skin_per_sub_cell_1D']['wrists'], indent=0)[:2500])
    print('usb tab', TH['usb_tab_on_skin_1D'])
    print('cold start', EN['cold_start_uA'])
    print('dock', EN['dock'])
    print('thermal', json.dumps(TH, indent=0)[:3000])
    print('RF', RF['half_wave_mm'])
    for w in WF: print('WF', w)
    for k, v in SUMMARY.items(): print('SUMMARY', k, v)
    for k, p in PLAN.items():
        print('\n'.join(p['top'])); print('\n'.join(p['board']))
