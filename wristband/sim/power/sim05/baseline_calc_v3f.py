# SIM-05 COPY (v3/sim/power/sim05/baseline_calc_v3f.py) of v3/stage1/calc/baseline_calc_s1.py, 2026-11-15. Changes tagged [SIM05]:
# W absolute; FINAL load mode (v3f netlist loads of v3/design/calc/v3f_calc.json -> standby: O-2 is no battery load, plus the computed
# items, plus the datasheet-bound items in mode 'bounds'); FINAL['mode'] = 'baseline' reproduces BASELINE 11.
# STAGE 1 COPY (v3/stage1/calc/baseline_calc_s1.py) of v3/decide/calc/baseline_calc.py (sha1 95d2a3b0e672fa386abd547f094eaea703e829c6).
# Changes, each tagged [S1 <id>]: RISET 10.2 k (D-8); window air gap 0.10 mm kept at the max-material panel -> window column +0.055 (C-10);
# rib insert 0.5 x 0.755 x 30.2 mm (C-10); window glass span 36.0 x 14.6 mm on the stage-1 rail and rib (C-1); stainless window frame 0.53 g
# and the GF-LCP rail 0.02 g from the CAD (C-13). Writes only into v3/stage1/calc (HERE). The decide originals are not touched.
#!/usr/bin/env python3
"""SolarBand V3 decide stage: every number of v3/decide/BASELINE.md and the costs in v3/decide/DECISIONS.md.

Lead synthesis 2026-11-13, revised the same day by the fix stage after two verification lenses
(v3/decide/verify/engineering.md E-1..E-14, v3/decide/verify/experience.md X-1..X-13; every change is listed in
v3/decide/CHANGELOG.md; the pre-fix script and its outputs are kept unchanged in calc/pre_fix/).

Configuration computed here: V3-F ("final"), the V3-R pod with the decisions of DECISIONS.md:
  70 mAh class cell (GEB301030) bought as a protected pack in the root-A capsule (4.5 mm, strengthened-glass top), R_LIM 12 ohm,
  RISET 10 kohm; two flush contacts in the top rim + isolated USB-C head (no strap tab, no VBUS in the strap);
  Sharp LS011B7DH03 with a designed-in front light (film laminated under the window glass, ABOVE the panel; panel on its V3-R
  support), night blank after 30 min without light, study mode;
  low-current coin ERM (8 mm) in a board cut-out between the ECG plates; one sealed side button with a ship-mode wake path (D12
  merged into a BAV70M pair); double tap gated to 3 s after a raise; hardware PV-charge inhibit from the cell NTC (O-2) reserved;
  5 ATM load path from the first build: two glasses on a ring rib with a stainless insert and 6 posts to the board beside the
  panel (PV strips narrowed to 2.30 mm, laminate edge at Y 21.0), 0.70 mm window glass on a rigid bond;
  0201 passives where the project has a part; skin-hot LED chain kept until the supervisor accepts decision 5 (d) in writing.

Run:   python3 -B /path/to/SolarVest_work/wristband/v3/decide/calc/baseline_calc.py
       (about 30 s with the cached tables; the first run builds the PV tables for the narrowed strips, about 1 min more)
Reads: calc/v3_calc_copy.py (DECIDE COPY of v3/integrate/v3_calc.py: it imports v3/integrate/energy/v3_energy.py read-only and reads
       its cache without rewriting it); v3/lanes/strap_pv/calc/wrist_light.json (read-only); lane figures that are not models
       (part data, judges' option scores) are entered below with their source.
Writes ONLY: calc/baseline_calc.json, calc/pv_tables_R12.json, calc/pv_tables_R*_w*.json, and (through the copy) calc/v3_calc_copy.json.
Markers in the JSON: 'V' read today in a named source or project file; 'E' estimate or model output (method named); 'U' unknown.
Nothing here is a SIM-xx run. The band harvests light; nothing here is wireless power transfer.
"""
import sys, os, json, math, copy, hashlib, time
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0]]                     # the copy must never see '--force'
sys.path.insert(0, HERE)
import numpy as np
T0 = time.time()
import v3_calc_copy as C                     # noqa: E402  (guarded copy; writes only calc/v3_calc_copy.json)
VE = C.VE; M = VE.M
W = '/path/to/SolarVest_work/wristband'   # [SIM05] absolute
OUT = dict(meta=dict(date='2026-11-13', stage='V3 decide: lead synthesis (baseline V3-F), revised by the fix stage',
                     cache_redirected=C.CACHE_REDIRECTED,
                     base='v3_calc_copy.py = v3/integrate/v3_calc.py with the import path, a cache guard and the output file changed',
                     fix_stage='changes against calc/pre_fix/baseline_calc.py are listed in v3/decide/CHANGELOG.md (issue ids E-n, X-n, FS-n)',
                     markers='V = read today in a named source or project file; E = estimate / model output (method named); U = unknown',
                     reproduce='python3 -B /path/to/SolarVest_work/wristband/v3/decide/calc/baseline_calc.py'))

# ===================================================================================================== 0. cells
# GEB301030: datasheet read by the eng_a lane (decide/research/eng_a/ENG_A.md 3.2, URL there): 70 mAh nominal and minimal,
# 3.0 mm max initial / 3.5 mm after cycle life, 10.0 x 30.0 mm max, tab length 6.0 +- 1 mm, max charge 1.0 C, charge 0..45 C,
# weight "approx 3 g" (U).
CELLX = {
 'GMB201030': dict(c_typ=43.0, c_min=38.7, t_max=2.5, g=(1.20, 1.40), i_prot=(2.8e-6, 6.0e-6), tag='V V3 baseline cell (Markyn sister spec via V3_ARCH)'),
 'GEB301030': dict(c_typ=70.0, c_min=70.0, t_max=3.5, g=(1.40, 1.80), i_prot=(2.8e-6, 6.0e-6),
                   tag='V eng_a lane datasheet reading; E mass 1.40 g typ (EEMB 70 mAh class) / 1.80 g max; E PCM XB5358D0 class (2.8 / 6.0 uA)'),
 'GEB301030 at 60 mAh': dict(c_typ=70.0, c_min=60.0, t_max=3.5, g=(1.40, 1.80), i_prot=(2.8e-6, 6.0e-6),
                   tag='E sensitivity: 60 mAh minimum (LP301230 class minimum) instead of the stated 70 mAh'),
 'thin cell (RFQ preference)': dict(c_typ=66.0, c_min=60.0, t_max=3.2, g=(1.26, 1.62), i_prot=(2.8e-6, 6.0e-6),
                   tag='E fix stage X-1(7): RFQ preference >= 60 mAh minimum and >= 66 mAh nominal (RISET 10 k stays <= 0.5 C), <= 2.7 mm '
                       'initial / 3.2 mm end of life, <= 10.5 x 30 mm; mass scaled by volume from GEB301030; no part identified (U)'),
}
for k, v in CELLX.items():
    if k not in VE.CELLS:      # adding keys after compute() does not touch the cache
        VE.CELLS[k] = dict(c_typ=v['c_typ'], c_min=v['c_min'], i_prot=v['i_prot'], t_max=v['t_max'], mass=v['g'][0], prot='pack PCM')
OUT['cells'] = CELLX

# ===================================================================================================== 1. new loads (W, battery-referred)
VB = 3.7; KV = VE.VDD / VE.ETA_BUCK
def light_W(events):   # (count per day, s each, LED mA) -> daily average W; LED current drawn from the cell at 3.7 V (eng_b lane method)
    return sum(n * s * i for n, s, i in events) * 1e-3 * VB / 86400.0
ERM_A = 30e-3                                         # V Vybronics VCLP0820B004L class 30 mA typ (35 mA max) via ENG_B 4.1
LOAD = dict(
    disp_on=VE.DISP['typ']['on'], disp_rtw=VE.DISP['typ']['rtw'], disp_on_max=VE.DISP['max']['on'], disp_rtw_max=VE.DISP['max']['rtw'],
    fl_typ=light_W([(10, 3, 1.5), (20, 3, 3.0)]),     # E eng_b: 10 night raises x 3 s at 1.5 mA + 20 dim-room raises x 3 s at 3 mA
    fl_dark=light_W([(100, 3, 1.5)]),                 # E eng_b T1 dark test: every one of 100 raises lit, 3 s at 1.5 mA
    erm=ERM_A * VB * 4.7 / 86400.0,                   # E eng_b: 4.7 s of motor a day at 30 mA (alarm 5 x 0.5 s, 5 notices x 0.4 s, 2 x 0.1 s)
    erm_heavy=ERM_A * VB * 15.0 / 86400.0,            # E eng_b heavy day 15 s
    tap=(90e-6 - 1.5e-6) * KV * 300.0 / 86400.0,      # E eng_b: LIS2DW12 400 Hz HP (90 uA, V Table 11) for 3 s after each of 100 raises
    o2=2.5e-6,                                        # E lead: two nano-power comparators (TLV7031 315 nA each, V JLC listing 16:40 UTC) at 3.7 V
                                                      #   = 2.3 uW, + 0.2 uW for an NTC divider; planning upper bound (E-2: the supply rail moves
                                                      #   to the PV node / VSTOR in V3-G4; the dark load must stay <= 2.5 uW)
)
def ret_extra(c_typ): return (0.15 - 0.03) * c_typ * 1e-3 / 730.0 * 3.7      # v3_calc targets(): retention at the 15 %/month family limit
OUT['new_loads_uW'] = {k: round(v * 1e6, 3) for k, v in LOAD.items()}
# E-4: skin-hot pattern that matches the cited study (S38, Feeltact, PMC7783873 read again today): successive 6-s sequences of 0.5-s
# vibrations and 0.5-s pauses, separated by 1-s pauses, for up to 10 min -> 3 s of vibration per 7 s
SKIN_HOT = dict(pattern='repeating 6-s sequences of 0.5-s pulses and 0.5-s pauses, 1-s pause between sequences, until a button press '
                        'and release or skin < 40 C, at most 10 min (V PMC7783873 pattern)',
                vib_s_per_event=round(600.0 / 7.0 * 3.0, 0), old_pattern_vib_s=7.5)
SKIN_HOT['mWh_per_event'] = round(SKIN_HOT['vib_s_per_event'] * ERM_A * VB / 3600.0 * 1e3, 2)
SKIN_HOT['ratio_to_old_pattern'] = round(SKIN_HOT['vib_s_per_event'] / SKIN_HOT['old_pattern_vib_s'], 0)

# ===================================================================================================== 2. PV tables (R_LIM and lid strip width)
PVSET = 'LID2+WR31'
STRIP_FULL = 2.50                                     # V3-R lid strips 27.7 x 2.50 mm, laminate edge Y 20.2
LAM_EDGE_Y = {2.50: 20.2, 2.40: 20.6, 2.30: 21.0}     # E-5 option 1: rib with a stainless insert beside the panel (panel ends Y 20.0)
def strips_for_edge(y_edge, y_top=31.0, gap=0.27):
    return round((y_top - y_edge - 3 * gap) / 4.0, 2)
class lid_strip:
    """temporarily narrows the lid strips in the energy model (A_LID2 is read at call time by v3_energy.lid())"""
    def __init__(self, w): self.w = w
    def __enter__(self): self.old = VE.A_LID2; VE.A_LID2 = 27.7 * self.w / 100.0
    def __exit__(self, *a): VE.A_LID2 = self.old
TAB12_PATH = os.path.join(HERE, 'pv_tables_R12.json')
_sig12 = hashlib.sha1(json.dumps([PVSET, 12.0, VE.LUX_GRID, VE.SUN_GRID, VE.A_LID2, VE.VOC_TC, 'decide-v1'], sort_keys=True).encode()).hexdigest()
TAB12 = None
if os.path.exists(TAB12_PATH):
    _c = json.load(open(TAB12_PATH))
    if _c.get('sig') == _sig12: TAB12 = _c['tables']
if TAB12 is None:
    TAB12 = {pk: VE.table(PVSET, pk, r_lim=12.0) for pk in VE.POST}
    json.dump(dict(sig=_sig12, set=PVSET, r_lim=12.0, tables=TAB12, note='E: v3_energy.table() at R_LIM 12 ohm (posture tables, W into the battery at 3.8 V)'),
              open(TAB12_PATH, 'w'), indent=1)
TABLES = {}
def tables_for(pvset, r_lim, w=STRIP_FULL):
    if pvset.startswith('LID4') or pvset.startswith('WR'): w = STRIP_FULL          # these sets do not use the 2.5 mm strips
    key = (pvset, float(r_lim), round(w, 2))
    if key in TABLES: return TABLES[key]
    if abs(w - STRIP_FULL) < 1e-9:
        T = TAB12 if (pvset == PVSET and r_lim == 12.0) else C.EN['tables'][VE.tkey(pvset, r_lim)]
    else:
        path = os.path.join(HERE, f'pv_tables_R{r_lim:g}_w{int(round(w * 100))}.json')
        sig = hashlib.sha1(json.dumps([pvset, r_lim, w, VE.LUX_GRID, VE.SUN_GRID, VE.VOC_TC, 'decide-fix-v1'], sort_keys=True).encode()).hexdigest()
        T = None
        if os.path.exists(path):
            c_ = json.load(open(path))
            if c_.get('sig') == sig: T = c_['tables']
        if T is None:
            with lid_strip(w): T = {pk: VE.table(pvset, pk, r_lim=r_lim) for pk in VE.POST}
            json.dump(dict(sig=sig, set=pvset, r_lim=r_lim, strip_w_mm=w, tables=T,
                           note='E fix stage (E-5 option 1): v3_energy.table() with the lid strips narrowed to this width'), open(path, 'w'), indent=1)
    TABLES[key] = T
    return T
POINTS = dict(sun045=('walk_sun', 0.45), ovc01=('walk_ovc', 0.1), lux300=('desk', 300.0), lux1000=('desk', 1000.0), lux200=('desk', 200.0), lap150=('lap', 150.0),
              sun1=('walk_sun', 1.0), sun02=('walk_ovc', 0.2), ovc003=('walk_ovc', 0.03))
def harv(pvset, r_lim, key, w=STRIP_FULL):
    pk, x = POINTS[key]; return VE.interp(tables_for(pvset, r_lim, w)[pk], x)       # W into the battery (3.8 V)
for args in ((PVSET, 12.0, 2.30), (PVSET, 12.0, 2.50), (PVSET, 22.0, 2.30), (PVSET, 22.0, 2.50), ('LID4+WR31', 22.0, 2.50), (PVSET, 12.0, 2.40)):
    tables_for(*args)
OUT['harvest_uW_into_battery'] = {f'{s}@R{r:g}' + ('' if abs(w - STRIP_FULL) < 1e-9 else f' strips {w:.2f} mm'): {k: round(harv(s, r, k, w) * 1e6, 1) for k in POINTS}
                                  for (s, r, w) in TABLES}

# ===================================================================================================== 3. configurations
V3F = dict(name='V3-F', cell='GEB301030', r_lim=12.0, riset_k=10.2, air_gap=0.155, s1_frame_rail=True,   # [S1 D-8, C-10, C-13]
           contacts=True, display=True, front_light=True, night_blank=True,
           erm=True, button=True, merge_d12=True, tap=True, o2='board', window_glass=0.70, under_panel=0.70, p0201=True, led=True,
           pod_len=40.0, pvset=PVSET, two_glass=True, capsule_top='glass', quick_release=True, panel_fitted=True, strip_w=2.30, web_posts=6,
           capsule_len=38.4)
V3R = dict(name='V3-R as published', cell='GMB201030', r_lim=22.0, riset_k=18.0, contacts=False, display=True, front_light=False, night_blank=False,
           erm=False, button=False, merge_d12=False, tap=False, o2=None, window_glass=0.50, under_panel=0.70, p0201=False, led=True,
           pod_len=40.0, pvset=PVSET, two_glass=False, capsule_top='pc', quick_release=False, panel_fitted=True, strip_w=2.50, web_posts=0,
           capsule_len=38.4)

# ---- new parts on the main board (courtyard mm2 E unless stated; heights mm) -------------------------------------------------------
R0201 = 0.70                                      # V parts.json 0201 resistor courtyard class (R1501 0.70)
PARTS_NEW = {
 'front_light': [('Q11', 'PMZ290UNE2YL NMOS, front-light LED switch on P0.10 (PWM)', 'C478155', 2.02, 0.50),
                 ('R160', 'LED current resistor 0201 (value and C-number chosen in V3-G1, about 150-560 ohm for 1.5-5 mA)', None, R0201, 0.33),
                 ('R161', 'Q11 gate pull-down 1 Mohm 0201', 'C295786', R0201, 0.33),
                 ('J16', 'front-light tail: 2 keyed asymmetric pads (hand-soldered at final assembly, like J13)', None, 3.0, 0.0)],
 'erm':         [('Q12', 'PMZ290UNE2YL NMOS, motor PWM on P0.04 (30 ms soft start)', 'C478155', 2.02, 0.50),
                 ('D17', 'flyback Schottky, common-cathode pair in DFN1006-3 (one half used): BAT54CM,315 C549275 or SDM02M30CLP3-7B C5244996',
                  'C549275', 2.02, 0.50),
                 ('R162', 'Q12 gate series resistor 0201 (value and C-number chosen in V3-G1)', None, R0201, 0.33),
                 ('R163', 'Q12 gate pull-down 1 Mohm 0201', 'C295786', R0201, 0.33),
                 ('J17', 'motor wire pads, 2 (motor hand-fitted in the board cut-out)', None, 3.0, 0.0)],
 'button':      [('SW1', 'C&K PTS840GKSMTRLFS SMD-5P 3.55 x 3.5 mm, behind a membrane moulded into the ring (courtyard and height '
                  'are assumptions until the C&K drawing is read: E-13)', 'C221907', 17.0, 1.05),
                 ('R164', 'level-safe input resistor from the button node to P0.26, 1 Mohm class, 0201 (topology in V3-G4)', 'C295786', R0201, 0.33),
                 ('R165', 'series resistor from VBAT to the button (active-high button feeding D12 half B and P0.26), 0201 (value in V3-G1)', None, R0201, 0.33)],
 'merge_d12':   [('D12', 'BAV70M,315 common-cathode switching pair, SOT-883: half A = VBUS wake (old D12), half B = button wake; '
                  'replaces BAS521 SOD-523 (C130414, 3.12 mm2, placement class P)', 'C549313', 2.02, 0.50)],
 'o2':          [('U18', 'O-2 hardware PV-charge inhibit: 2 comparators (TLV7031 1.6-6.5 V or TLV3691 0.9-6.5 V, V JLC listing), NTC ladder '
                  'biased only while PV is lit and VBUS is absent, OR into the Q1 gate; supplied from the PV node or VSTOR (never from VBAT '
                  'alone: E-2); reserve (circuit designed in V3-G4; moves to the pack PCM if the pack RFQ confirms a cut-off and the cell '
                  'voltage down to which it works); SC-70-5 options with a land that proves rotation: TLV7031DCKR C2863637, TLV3691IDCKR C180352',
                  'C2876045', 12.0, 0.40)],
}
D12_OLD_MM2 = 3.12                                # V v3_calc USB_BLOCK: D12 BAS521 SOD-523 courtyard
CUT_D = 8.6                                       # mm, board cut-out for the 8 mm coin motor (eng_b)
P0201_V2 = 22.13                                  # V CALC.md 12 / parts.json dock_wlcsp_p0201 vs dock_wlcsp (computed from parts.json)
P0201_KEEP_0402 = {'R108': 0.79, 'R131': 0.79}    # 10 Mohm stays in 0402 (C144806, V JLC 10:26 UTC); no 0201 part in the project library
P0201_R508 = 0.79                                 # part of the LED chain: its saving disappears when the chain is removed
P0201_V3_USB = {'R144': 0.79, 'R145': 0.79, 'R146': 0.79, 'R149': 0.79}   # 1 Mohm C295786 / 100 kohm C270364 0201 (project parts, P)
J15_MM2 = 12.6                                    # v3_calc: D-4 (b) two spring fingers (C2826535) on the board, parts.json class
POST_KO_MM2 = 1.0                                 # E E-5 option 1: keep-out per rib post on the board (0.6 mm post + 0.2 mm clearance)

def area(cfg):
    """main-board utilisation on REDESIGN's metric (v3_calc area_config) with the V3-F additions"""
    base_cfg = dict(C.CONFIGS['V3-R'], alert_led=cfg['led'])
    if cfg['contacts']:
        base_cfg.update(usb_tab=False, strap_conductors=dict(root_A=['BATT_P', 'GND', 'NTC', 'GND'], root_B=['PV_W+', 'GND']))
    d = C.area_config(base_cfg, cfg['pod_len'])
    cy, pa = d['courtyard_mm2'], d['placement_area_mm2']; items = []
    for key in ('front_light', 'erm', 'button', 'merge_d12'):
        if (key == 'front_light' and cfg['front_light']) or (key in ('erm',) and cfg['erm']) or (key == 'button' and cfg['button']) \
                or (key == 'merge_d12' and cfg['merge_d12']):
            for p in PARTS_NEW[key]: cy += p[3]; items.append(dict(ref=p[0], part=p[1], lcsc=p[2], courtyard_mm2=p[3], height_max_mm=p[4]))
    if cfg['merge_d12']: cy -= D12_OLD_MM2; items.append(dict(ref='D12 (old)', part='BAS521 removed (merged into the BAV70M pair)', lcsc='C130414', courtyard_mm2=-D12_OLD_MM2))
    if cfg['o2'] == 'board':
        for p in PARTS_NEW['o2']: cy += p[3]; items.append(dict(ref=p[0], part=p[1], lcsc=p[2], courtyard_mm2=p[3], height_max_mm=p[4]))
    if cfg['p0201']:
        s = P0201_V2 - sum(P0201_KEEP_0402.values()) - (0.0 if cfg['led'] else P0201_R508) + sum(P0201_V3_USB.values())
        cy -= s; items.append(dict(ref='0201', part='generic passives in 0201 (V2 p0201 variant less R108/R131; + R144-R146, R149)', courtyard_mm2=-round(s, 2)))
    if cfg['erm']:
        cd = cfg.get('motor_cut_d', CUT_D)
        pa -= math.pi * cd ** 2 / 4.0 + 0.3 * math.pi * cd
    if cfg.get('web_posts'):
        pa -= cfg['web_posts'] * POST_KO_MM2
    u = cy / pa
    return dict(courtyard_mm2=round(cy, 1), placement_area_mm2=round(pa, 1), utilisation=round(u, 3), utilisation_v1_bbox=round(u * C.V1_BBOX, 3),
                utilisation_exact=round(u, 4), utilisation_v1_exact=round(u * C.V1_BBOX, 4),
                gate1_pass=u <= 0.62, gate1_pass_v1_measure=u * C.V1_BBOX <= 0.62, base=dict(courtyard=d['courtyard_mm2'], placement=d['placement_area_mm2']),
                rib_post_keepout_mm2=cfg.get('web_posts', 0) * POST_KO_MM2, added=items)

# ---- stack-up -------------------------------------------------------------------------------------------------------------------
FL_NOM = round(0.96 - 0.741, 3)                   # E eng_b: Azumo 11049 drawing stack 0.96 mm over the 0.741 mm panel (+-0.20 general tolerance)
FL_MAX = 0.25                                     # E fix stage (E-10): RFQ maximum for the custom film + OCA, laminated to the window glass
TOLW = [('ring floor top to lid seat', 0.05), ('window bond line', 0.05), ('window glass', 0.05), ('cap height', 0.05), ('carrier film', 0.02)]
tolw_wc = round(sum(t for _, t in TOLW), 2); tolw_rss = round(math.sqrt(sum(t * t for _, t in TOLW)), 3)
def stack(cfg):
    pv = [('PV laminate (RFQ maximum; 0.50 mm glass)', 1.20), ('clearance', 0.15), ('parts + solder', 1.05), ('PCB 6-layer 1.0 + tol', 1.10),
          ('carrier film', 0.10), ('floor PC film + Ti plates', 0.25), ('PPG mesa', 0.80)]
    lowz = round(cfg['under_panel'] + 0.05, 2)
    win = [(f"window glass {cfg['window_glass']:.2f} mm (chemically strengthened, AR both faces, UV-cut)", cfg['window_glass'])]
    if cfg.get('fl_space', cfg['front_light']):
        win += [(f'front-light film + OCA, laminated to the underside of the window glass, ABOVE the panel (custom 1.08"; RFQ maximum '
                 f'{FL_MAX:.2f} mm; {FL_NOM:.2f} nominal from the 1.28" drawing); in unlit builds this space stays empty', FL_MAX)]
    win += [('air gap (no adhesive on the panel, V LS013B7DH03 p.2); S1 C-10: 0.10 kept at the 0.855 mm max-material panel', cfg.get('air_gap', 0.10)), ('LS011B7DH03 0.745 + 0.055 allowance', 0.80),
            ('panel support (frame on posts, as V3-R)', 0.10), ('clearance', 0.15),
            (f"low parts under the panel (body <= {cfg['under_panel']:.2f} mm + solder)", lowz),
            ('PCB 6-layer 1.0 + tol', 1.10), ('carrier film', 0.10), ('floor', 0.25), ('PPG mesa', 0.80)]
    tpv = round(sum(t for _, t in pv), 3); twin = round(sum(t for _, t in win), 3)   # [S1] 3 decimals (5.155)
    if not cfg['two_glass'] and cfg['window_glass'] > 0.50:   # one laminate: the thicker glass covers the PV half too
        tpv = round(tpv + cfg['window_glass'] - 0.50, 2)
    pod = round(max(tpv, twin), 3)
    wc = max(tpv + C.tol_wc, twin + tolw_wc); rss = max(tpv + C.tol_rss, twin + tolw_rss)
    return dict(pv_column=dict(layers=pv, total=tpv), window_column=dict(layers=win, total=twin), pod_max_material_mm=round(pod, 3),
                governs='window column' if twin > tpv else 'PV column',
                pod_at_P121_nominal_mm=round(max(tpv - 1.20 + C.LID_P121, twin), 2), pod_at_P121_upper_mm=round(max(tpv - 1.20 + C.LID_P121_MAX, twin), 2),
                worn_top_pv_half_mm=round(tpv - 0.80, 2), worn_top_window_half_mm=round(twin - 0.80, 2),
                worn_top_pv_half_P121_mm=(round(tpv - 1.20 + C.LID_P121 - 0.80, 2), round(tpv - 1.20 + C.LID_P121_MAX - 0.80, 2)),
                tolerance_lists=dict(pv_column=dict(items=C.TOL, wc=C.tol_wc, rss=C.tol_rss), window_column=dict(items=TOLW, wc=tolw_wc, rss=tolw_rss)),
                worst_case_all_tolerances_mm=round(wc, 2), rss_mm=round(rss, 2))

# ---- worn geometry: the strap lane's wrist ellipse (port of wrist_light.py; reproduces its 140 / 165 / 200 mm cases exactly) -------
POD_HALF_W, BAR_OUT, STRAP_T = 16.0, 2.5, 1.5
def ellipse_axes(Cw, q):
    def per(a):
        b = q * a; h = ((a - b) / (a + b)) ** 2
        return math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))
    lo, hi = 1.0, Cw
    for _ in range(100):
        m = 0.5 * (lo + hi)
        if per(m) < Cw: lo = m
        else: hi = m
    a = 0.5 * (lo + hi); return a, q * a
_GEO = {}
def wrist_geo(Cw, q=0.68, ts=STRAP_T):
    if (Cw, q) in _GEO: return _GEO[(Cw, q)]
    a, b = ellipse_axes(Cw, q)
    def pt(t, off=0.0):
        n = np.array([math.sin(t) / a, math.cos(t) / b]); n /= np.linalg.norm(n)
        return np.array([a * math.sin(t), b * math.cos(t)]) + off * n, n
    P0 = np.array([POD_HALF_W + BAR_OUT, b + 1.0])
    f = lambda t: float(np.dot(P0 - pt(t, ts / 2)[0], pt(t, ts / 2)[1]))
    lo, hi = 0.05, math.pi / 2 + 0.5
    for _ in range(80):
        m = 0.5 * (lo + hi)
        if f(lo) * f(m) <= 0: hi = m
        else: lo = m
    t0 = 0.5 * (lo + hi); q0, _n = pt(t0, ts / 2)
    free = float(np.linalg.norm(P0 - q0)); d = (q0 - P0) / free
    th = np.linspace(0.0, math.pi, 400001)
    g = dict(C=Cw, q=q, a=a, b=b, t0_deg=math.degrees(t0), free_span_mm=free, tilt_deg=math.degrees(math.atan2(-d[1], d[0])),
             ex=a * np.cos(th), ey=b * np.sin(th))
    _GEO[(Cw, q)] = g; return g
def item_on_free_span(Cw, t_item, s0=2.0, s1=13.9, ts=STRAP_T):
    """a rigid strap item from s0 to s1 (inner face on the strap's inner face): its thickness above the skin where it rests (far end),
    the inner-face gap there, the overhang past the tangent point, and the outer top against the pod top (V3_ARCH capsule_fit method)"""
    g = wrist_geo(Cw); a, b = g['a'], g['b']; t = math.radians(g['tilt_deg'])
    P0 = (POD_HALF_W + BAR_OUT, b + 1.0); d = (math.cos(t), -math.sin(t)); n = (math.sin(t), math.cos(t))
    def pt(sv, off): return (P0[0] + sv * d[0] + off * n[0], P0[1] + sv * d[1] + off * n[1])
    def dist(p): return float(np.min(np.hypot(p[0] - g['ex'], p[1] - g['ey'])))
    send = s1
    inner, outer = pt(send, -ts / 2), pt(send, -ts / 2 + t_item)
    return dict(wrist_mm=Cw, free_span_mm=round(g['free_span_mm'], 2), tilt_deg=round(g['tilt_deg'], 1),
                overhang_past_tangent_mm=round(max(0.0, s1 - g['free_span_mm']), 2),
                inner_face_gap_at_far_end_mm=round(dist(inner), 3), thickness_above_skin_at_far_end_mm=round(dist(outer), 2))
WRISTS = (140.0, 165.0, 200.0)
import functools
@functools.lru_cache(maxsize=None)
def standoff_max(t_item, s1=13.9): return round(max(item_on_free_span(c, t_item, s1=s1)['thickness_above_skin_at_far_end_mm'] for c in WRISTS), 2)
def standoff_range(t_item, s1=13.9):
    v = [item_on_free_span(c, t_item, s1=s1)['thickness_above_skin_at_far_end_mm'] for c in WRISTS]; return (min(v), max(v))

# ---- masses ---------------------------------------------------------------------------------------------------------------------
def shell_g(outline, t, wall=0.40):     # eng_a lane formula (pre-made PC shell, 0.5 mm side walls)
    lo, wo = outline; return round((lo * wo * t - (lo - 1.0) * (wo - 1.0) * (t - 2 * wall)) * C.RHO['pc'], 3)
MOTOR_G = 0.45                          # E eng_b: 8 x 2.1 mm coin ERM (scaled from 0.7 g for 8 x 3.4 mm, search summary)
RHO_GLASS, RHO_SS = 2.5e-3, 7.9e-3      # g/mm3 (E handbook values)
def capsule_top_net_g(kind, l=38.4, w=11.9):
    pc = l * w * 0.40 * C.RHO['pc']
    return round({'pc': 0.0, 'glass': l * w * 0.40 * RHO_GLASS - pc, 'steel': l * w * 0.20 * RHO_SS - pc}[kind], 3)
RIB_G = round((0.5 * 0.755 * 30.2 + 6 * 0.6 * 0.6 * 1.0) * RHO_SS, 3)   # [S1 C-10] insert 0.5 x 0.755 x 30.2 mm (CAD) + 6 posts 0.6 x 0.6 x 1.0 mm (CAD: board top to insert)
def mass(cfg):
    base_cfg = dict(C.CONFIGS['V3-R'], alert_led=cfg['led'])
    if cfg['contacts']: base_cfg.update(usb_tab=False, strap_conductors=dict(root_A=['BATT_P', 'GND', 'NTC', 'GND'], root_B=['PV_W+', 'GND']))
    base_cfg['pod_len'] = cfg['pod_len']
    pm = C.pod_mass(base_cfg); pmx = C.pod_mass_max(base_cfg)
    add = {}
    if cfg['front_light']: add['front-light film + LED (eng_b)'] = 0.05
    if cfg['erm']:
        cd = cfg.get('motor_cut_d', CUT_D); mg = MOTOR_G * ((cd - 0.6) / 8.0) ** 2
        add[f'ERM {cd - 0.6:g} x 2.1 mm {mg:.2f} g less the board removed by the {cd:g} mm cut-out'] = round(mg - math.pi * (cd / 2) ** 2 * C.RHO['board6_10'], 3)
    if cfg['button']: add['button, membrane, ship-wake parts (eng_b)'] = 0.10
    if cfg['o2'] == 'board': add['O-2 inhibit parts'] = 0.01
    if cfg.get('web_posts'): add['stainless rib insert 0.5 x 0.755 x 30.2 mm + 6 posts (5 ATM load path, E-5; S1 C-10)'] = RIB_G
    if cfg.get('s1_frame_rail'):   # [S1 C-1, C-13] from the CAD (v3/cad/out/mass_L40.json, max-material volumes x handbook densities, E)
        add['stainless window frame 0.25 mm (rigid bond; CAD 0.53 g)'] = 0.527
        add['GF-LCP window rail on 9 posts (CAD)'] = 0.022
    if cfg['window_glass'] > 0.50: add[f"window glass {cfg['window_glass']:.2f} instead of 0.50 mm over 33 x 15 mm at 2.5 g/cm3"] = round((cfg['window_glass'] - 0.50) * 33 * 15 * 2.5e-3, 3)
    pod_typ = round(pm['TOTAL'] + sum(add.values()), 2)
    pod_max = round(pmx + 1.25 * sum(v for k, v in add.items() if not k.startswith('window')) + sum(v for k, v in add.items() if k.startswith('window')), 2)
    sm = C.strap_mass(base_cfg)['TOTAL']; smx = C.strap_mass(base_cfg, max_material=True)['TOTAL']
    cell = cfg['cell']; t_caps = round(0.40 + 0.20 + CELLX[cell]['t_max'] + 0.40, 2); lcap = cfg.get('capsule_len', 38.4)
    d_shell = shell_g((lcap, 11.9), t_caps) - shell_g((38.4, 11.9), 3.5)
    sadd = {f'capsule shell at {t_caps} mm, {lcap:g} mm long (vs 3.5 mm, 38.4 mm)': round(d_shell, 3), 'cell mass change against GMB201030': round(CELLX[cell]['g'][0] - 1.20, 3)}
    saddx = dict(sadd); saddx['cell mass change against GMB201030'] = round(CELLX[cell]['g'][1] - 1.40, 3)
    top = cfg.get('capsule_top', 'pc')
    if top != 'pc':
        lab = 'stiff capsule top: ' + ('0.40 mm strengthened glass, white print underneath (max: 0.20 mm 316L fallback)' if top == 'glass' else '0.20 mm 316L lid')
        sadd[lab] = capsule_top_net_g(top, lcap); saddx[lab] = capsule_top_net_g('steel', lcap)
    if cfg['quick_release']: sadd['outer-band quick release at both root ends'] = 0.10; saddx['outer-band quick release at both root ends'] = 0.30
    strap_typ = round(sm + sum(sadd.values()), 2); strap_max = round(smx + sum(saddx.values()), 2)
    return dict(pod_g=pod_typ, pod_g_max=pod_max, strap_g=strap_typ, strap_g_max=strap_max, worn_g=round(pod_typ + strap_typ, 1),
                worn_g_max=round(pod_max + strap_max, 1), worn_g_2dp=round(pod_typ + strap_typ, 2), pod_breakdown=pm, pod_additions=add,
                strap_breakdown=C.strap_mass(base_cfg), strap_additions_typ=sadd, strap_additions_max=saddx, capsule_t_mm=t_caps)

def highest_worn(cfg, st, ms):
    """X-1: every worn item measured the same way, as its thickness above the skin where it rests (pod halves with the mesa pressed in;
    strap items at the far end of the free span, where they rest on the skin); the tab value is V3's (4.6 mm on the skin-contact strap)"""
    items = {'pod window half': st['worn_top_window_half_mm'], 'pod PV half': st['worn_top_pv_half_mm'],
             'cell capsule (root A)': standoff_max(ms['capsule_t_mm']), 'wing root (root B, documented route 2.95 mm)': standoff_max(2.95, s1=13.7)}
    if not cfg['contacts']: items['USB-C tab (root A, skin-contact strap)'] = 4.6
    top = max(items, key=items.get)
    return dict(items_mm=items, highest_item=top, highest_mm=items[top])

# ---- energy ---------------------------------------------------------------------------------------------------------------------
FINAL = dict(mode=os.environ.get('SIM05_MODE', 'bounds'))                                          # [SIM05] 'baseline' | 'typ' | 'bounds'
_FACE = ('MON_lit', 'MON_dark_always_on', 'MON_max_always_on', 'MON_worst_always_on', 'RAW_WC', 'RAW_WC_worst')
_DISPOFF = ('MON_dark', 'MON_max', 'MON_worst', 'ECO', 'ECO_V3_convention', 'SHELF')
def final_extra(k):
    """[SIM05] W added to load state k: v3f_calc.json standby additions (computed items always; bound items in mode 'bounds')"""
    e = 0.0; b = FINAL['mode'] == 'bounds'
    mon = k.startswith('MON') or k.startswith('RAW')
    if mon: e += 0.023e-6                                              # NTC readings by NTC_EN
    if k in _DISPOFF: e += 0.037e-6                                    # U16 shutdown while the display is off
    if b and (mon or k.startswith('ECO') or k == 'SHELF'): e += 2.187e-6   # BQ25170 /PG leakage bound (VDD_1V8 on)
    if b and k in _FACE: e += 9.25e-6                                  # U21 ICCA + ICCB bound, face on
    if b and k == 'SHIP': e += 3.7e-6                                  # Q12 IDSS bound on VBAT_IC
    if k == 'WEEK_always': e = 0.023e-6 + (2.187e-6 if b else 0.0)
    if k == 'WEEK_face_on': e = 9.25e-6 if b else 0.0
    return e
KISET = (270.0, 300.0, 330.0)            # V BQ25170 SLUSDJ8A p.6-7 via the usbc lane (KISET min / typ / max)
def energy(cfg, weeks=('W2_indoor_300lx', 'W7_low_outdoor_office')):
    cell = cfg['cell']; U = VE.usable_Wh(cell); c_typ = CELLX[cell]['c_typ']
    base = dict(cell=cell, display=False, usb=True, asbuilt=True, pulldown_fix=True, gain=4)
    LT = VE.loads(dict(base, which='typ'))[0]; LM = VE.loads(dict(base, which='max'))[0]; LW = VE.loads(dict(base, which='max', gain=1))[0]
    add = (LOAD['fl_typ'] if cfg['front_light'] else 0.0) + (LOAD['erm'] if cfg['erm'] else 0.0) + (LOAD['tap'] if cfg['tap'] else 0.0) \
          + (LOAD['o2'] if cfg['o2'] else 0.0)
    fl_dark_adj = (LOAD['fl_dark'] - LOAD['fl_typ']) if cfg['front_light'] else 0.0
    d_on = LOAD['disp_on'] if cfg['display'] else 0.0; d_rtw = LOAD['disp_rtw'] if cfg['display'] else 0.0
    d_on_x = LOAD['disp_on_max'] if cfg['display'] else 0.0; d_rtw_x = LOAD['disp_rtw_max'] if cfg['display'] else 0.0
    nb = cfg['night_blank']
    p = dict(
        MON_lit=LT['MON'] + d_on + add,                                              # face on (light), typical night light: T3, T5
        MON_dark=LT['MON'] + (d_rtw if nb else d_on) + add + fl_dark_adj,            # T1 dark test: night blank, light on every raise
        MON_dark_always_on=LT['MON'] + d_on + add + fl_dark_adj,                     # V3 convention: the face always on
        MON_max=LM['MON'] + (d_rtw_x if nb else d_on_x) + add + fl_dark_adj,
        MON_max_always_on=LM['MON'] + d_on_x + add + fl_dark_adj,
        MON_worst=LW['MON'] + ret_extra(c_typ) + (d_rtw_x if nb else d_on_x) + add + fl_dark_adj,
        MON_worst_always_on=LW['MON'] + ret_extra(c_typ) + d_on_x + add + fl_dark_adj,
        RAW_WC=LT['RAW'] + d_on + add,                                               # W-C band, face always on (V3 convention, conservative)
        RAW_WC_worst=VE.loads(dict(base, which='max', gain=1))[0]['RAW'] + ret_extra(c_typ) + d_on_x + add + fl_dark_adj,
        ECO=LT['ECO'] + d_rtw + add,                                                 # conservative: light, motor and tap kept in ECO
        ECO_V3_convention=LT['ECO'] + d_rtw + (LOAD['o2'] if cfg['o2'] else 0.0),    # V3 convention: display raise-to-wake only (+ O-2)
        SHELF=LT['SHELF'] + (3e-9 * VB if cfg['display'] else 0.0) + (LOAD['o2'] if cfg['o2'] else 0.0),
        SHIP=LT['SHIP'])
    if FINAL['mode'] != 'baseline':                                   # [SIM05] v3f netlist loads (v3f_calc.json standby)
        if cfg['o2']:
            for k_ in ('MON_lit', 'MON_dark', 'MON_dark_always_on', 'MON_max', 'MON_max_always_on', 'MON_worst', 'MON_worst_always_on',
                       'RAW_WC', 'RAW_WC_worst', 'ECO', 'ECO_V3_convention', 'SHELF'):
                p[k_] -= LOAD['o2']                                      # O-2 fed from the PV / unpowered: no battery load
        for k_ in p:
            p[k_] += final_extra(k_)
    rl = cfg['r_lim'] if cfg['r_lim'] in (12.0, 22.0) else 22.0; pv = cfg['pvset']; w = cfg.get('strip_w', STRIP_FULL)
    h = {k: harv(pv, rl, k, w) for k in POINTS}
    d = lambda x: U / (x * 24.0)
    t = dict(usable_mWh=round(U * 1e3, 1), loads_uW={k: round(v * 1e6, 1) for k, v in p.items() if v is not None},
             T1_dark_d=round(d(p['MON_dark']), 1), T1_dark_always_on_face_d=round(d(p['MON_dark_always_on']), 1),
             T1_max_currents_d=round(d(p['MON_max']), 1), T1_max_currents_always_on_face_d=round(d(p['MON_max_always_on']), 1),
             T1_worst_stack_d=round(d(p['MON_worst']), 1), T1_worst_stack_always_on_face_d=round(d(p['MON_worst_always_on']), 1),
             RAW_WC_d=round(d(p['RAW_WC']), 1), RAW_WC_worst_stack_d=round(d(p['RAW_WC_worst']), 1), T2_ECO_d=round(d(p['ECO']), 0),
             T3_min_day_045sun=round(p['MON_lit'] * 24 / h['sun045'] * 60, 1), T3_overcast_min_day_01sun=round(p['MON_lit'] * 24 / h['ovc01'] * 60, 0),
             T4_ECO_1000lx_10h=round(10 * h['lux1000'] / (p['ECO'] * 24), 2),
             T2_ECO_V3_convention_d=round(d(p['ECO_V3_convention']), 0), T4_ECO_V3_convention=round(10 * h['lux1000'] / (p['ECO_V3_convention'] * 24), 2),
             T6_SHELF_d=round(d(p['SHELF']), 0), T6_SHIP_d=round(d(p['SHIP']), 0), pv_table=f'{pv}@R{rl:g} strips {w:.2f} mm')
    if cfg['display'] and not nb:      # V3 dark policy: always on for 24 h without harvest, then raise-to-wake
        pon = p['MON_dark_always_on']; poff = pon - d_on + d_rtw
        t['T1_with_V3_dark_policy_d'] = round(1 + (U - pon * 24) / (poff * 24), 1)
    net = p['MON_lit'] * 24 - 10 * h['lux300']
    t['T5_indoor_300lx_10h_days_from_full'] = round(U / net, 1) if net > 0 else 'energy-neutral'
    t['T5_fraction_of_MON_covered_pct'] = round(100 * 10 * h['lux300'] / (p['MON_lit'] * 24), 1)
    # USB / head charging, CC + CV model of the physics lens (v3_calc usb_charge_h; it keeps the 43 mAh cell's resistances: conservative)
    rk = cfg['riset_k']; cap = c_typ
    t7 = {f'KISET {k:g}: {k / rk:.1f} mA, VREG 4.10 V': C.usb_charge_h(k / rk * 1e-3, 4.10, cap=cap) for k in KISET}
    t7['KISET 270, VREG 4.067 V (-0.8 %)'] = C.usb_charge_h(KISET[0] / rk * 1e-3, 4.067, cap=cap)
    t7['KISET 270, VREG -0.8 %, cold 5-10 C cell (ohmic 1.5, RC x2.5)'] = C.usb_charge_h(KISET[0] / rk * 1e-3, 4.067, cap=cap, r0=1.5, r1=1.5, r2=2.0)
    t['T7_h'] = t7; t['usb_c_rate_typ_max'] = (round(KISET[1] / rk / cap, 3), round(KISET[2] / rk / cap, 3))
    i_typ = KISET[1] / rk
    t['ten_min_topup_days_of_MON'] = round(i_typ * 10 / 60 / (p['MON_lit'] * 1e3 / 3.7 * 24), 2)
    # SIM-05 weeks from 50 % SoC (night blank = face blanks after 30 min without harvest)
    T = tables_for(pv, rl, w); pmon = LT['MON'] + add
    if FINAL['mode'] != 'baseline':                                   # [SIM05]
        pmon += final_extra('WEEK_always') - (LOAD['o2'] if cfg['o2'] else 0.0); d_on += final_extra('WEEK_face_on')
    wk = {}
    for wname in weeks:
        rr = VE.sim_week(VE.trace(wname), T, pmon, U, p_disp_on=d_on, p_disp_rtw=d_rtw, dark_policy_min=(30 if nb else 1440))
        wk[wname] = {k: rr[k] for k in ('harvest_mWh_day', 'load_mWh_day', 'min_soc', 'end_soc', 'days_to_empty_from_50pct', 'days_from_full_if_negative')}
    t['weeks_from_50pct'] = wk
    w2 = wk.get('W2_indoor_300lx', {}).get('days_from_full_if_negative')
    if isinstance(w2, (int, float)):
        lo, hi = min(t7[k] for k in t7 if 'VREG 4.10' in k), max(t7[k] for k in t7 if 'VREG 4.10' in k)
        t['off_wrist_hours_per_30d_indoor_only'] = (round(30 / w2 * lo, 2), round(30 / w2 * hi, 2))
    t['harvest_uW'] = {k: round(v * 1e6, 1) for k, v in h.items()}
    return t

def evaluate(cfg, weeks=('W2_indoor_300lx', 'W7_low_outdoor_office')):
    st = stack(cfg); ms = mass(cfg)
    return dict(config={k: v for k, v in cfg.items()}, stack=st, area=area(cfg), mass=ms, worn=highest_worn(cfg, st, ms), energy=energy(cfg, weeks))

# ===================================================================================================== 4. baseline and checks
ALLW = tuple(VE.WEEKS)
BASE = evaluate(V3F, weeks=ALLW)
CHECK_V3R = evaluate(V3R)
OUT['baseline_V3F'] = BASE
OUT['check_V3R_reproduced'] = dict(model=dict(T1=CHECK_V3R['energy']['T1_dark_d'], T1_dark_policy=CHECK_V3R['energy'].get('T1_with_V3_dark_policy_d'),
                                              T3=CHECK_V3R['energy']['T3_min_day_045sun'], T5=CHECK_V3R['energy']['T5_indoor_300lx_10h_days_from_full'],
                                              W2=CHECK_V3R['energy']['weeks_from_50pct']['W2_indoor_300lx']['days_from_full_if_negative'],
                                              W7=CHECK_V3R['energy']['weeks_from_50pct']['W7_low_outdoor_office']['days_from_full_if_negative'],
                                              worst=CHECK_V3R['energy']['T1_worst_stack_d'], util=CHECK_V3R['area']['utilisation'],
                                              worn=CHECK_V3R['mass']['worn_g'], worn_max=CHECK_V3R['mass']['worn_g_max'], pod=CHECK_V3R['stack']['pod_max_material_mm']),
                                   published=dict(T1=21.6, T1_dark_policy=24.5, T3=12.5, T5=23.2, W2=23.2, W7=26.9, worst=11.5, util=0.486, worn=19.1, worn_max=20.2, pod=4.65),
                                   V3R_worn_items_mm=CHECK_V3R['worn']['items_mm'])

# ===================================================================================================== 5. waterfall V3-R -> V3-F (one decision at a time)
STEPS = []
c = dict(V3R); STEPS.append(('0 V3-R as published (43 mAh, USB-C tab, unlit always-on display)', dict(c)))
c.update(cell='GEB301030', r_lim=12.0, riset_k=10.2); STEPS.append(('1 D-1: 70 mAh pack in the capsule (4.5 mm), R_LIM 12 ohm, RISET 10.2 kohm (S1 D-8)', dict(c)))
c.update(contacts=True); STEPS.append(('2 D-4: two flush contacts + isolated USB-C head; no strap tab', dict(c)))
c.update(front_light=True); STEPS.append(('3a D-2 hardware: front light designed in (film above the panel, Q11 driver; face still always on)', dict(c)))
c.update(night_blank=True); STEPS.append(('3b D-2 firmware: night blank after 30 min without light', dict(c)))
c.update(erm=True); STEPS.append(('4 alerts: 8 mm low-current ERM in a board cut-out', dict(c)))
c.update(button=True, merge_d12=True, tap=True); STEPS.append(('5 input: sealed side button (+ ship wake via a BAV70M pair) + gated double tap', dict(c)))
c.update(o2='board'); STEPS.append(('6 safety floor: hardware PV-charge inhibit (O-2) reserved on the board', dict(c)))
c.update(window_glass=0.70, two_glass=True, web_posts=6, strip_w=2.30, capsule_top='glass', quick_release=True)
STEPS.append(('7 5 ATM load path (two glasses, 0.70 mm window on a rigid bond, stainless rib + 6 posts, PV strips 2.30 mm), glass capsule top, band quick release', dict(c)))
c.update(p0201=True); STEPS.append(('8 0201 passives where the project has the part = V3-F', dict(c)))
WF = []
for lab, cfg in STEPS:
    ev = BASE if lab.startswith('8') else evaluate(cfg)
    e = ev['energy']; wk = e['weeks_from_50pct']
    WF.append(dict(step=lab, pod_mm=ev['stack']['pod_max_material_mm'], pod_window_half_mm=ev['stack']['window_column']['total'],
                   highest_worn_mm=ev['worn']['highest_mm'], highest_item=ev['worn']['highest_item'],
                   worn_g=ev['mass']['worn_g'], worn_g_max=ev['mass']['worn_g_max'], utilisation=ev['area']['utilisation'], util_v1=ev['area']['utilisation_v1_bbox'],
                   T1_d=e['T1_dark_d'], T1_face_always_on_d=e['T1_dark_always_on_face_d'], T1_worst_d=e['T1_worst_stack_d'],
                   T1_worst_face_always_on_d=e['T1_worst_stack_always_on_face_d'], T3_min=e['T3_min_day_045sun'],
                   W2_d=wk['W2_indoor_300lx']['days_from_full_if_negative'], W7_d=wk['W7_low_outdoor_office']['days_from_full_if_negative'],
                   SHELF_d=e['T6_SHELF_d'], RAW_WC_d=e['RAW_WC_d']))
OUT['waterfall_V3R_to_V3F'] = WF

# ===================================================================================================== 6. variants and sensitivities
VAR = {}
def short(ev):
    e = ev['energy']; wk = e['weeks_from_50pct']
    return dict(pod_mm=ev['stack']['pod_max_material_mm'], highest_worn_mm=ev['worn']['highest_mm'], worn_g=ev['mass']['worn_g'], worn_g_max=ev['mass']['worn_g_max'],
                utilisation=ev['area']['utilisation'], util_v1=ev['area']['utilisation_v1_bbox'], gate1_v1_pass=ev['area']['gate1_pass_v1_measure'],
                T1_d=e['T1_dark_d'], T1_face_always_on_d=e['T1_dark_always_on_face_d'], T1_worst_d=e['T1_worst_stack_d'], T3_min=e['T3_min_day_045sun'],
                T5_d=e['T5_indoor_300lx_10h_days_from_full'],
                W2_d=wk.get('W2_indoor_300lx', {}).get('days_from_full_if_negative'), W7_d=wk.get('W7_low_outdoor_office', {}).get('days_from_full_if_negative'),
                SHELF_d=e['T6_SHELF_d'], RAW_WC_d=e['RAW_WC_d'])
VAR['gate-1 reserve (1): LED chain removed (only with decision 5 (d) in writing and the felt-strength check)'] = short(evaluate(dict(V3F, led=False)))
VAR['gate-1 reserve (2): pod and board 1 mm longer (41 x 32 mm)'] = short(evaluate(dict(V3F, pod_len=41.0)))
VAR['gate-1 reserve (3): O-2 cut-off in the pack PCM instead of the board'] = short(evaluate(dict(V3F, o2='pcm')))
VAR['(1) + (3)'] = short(evaluate(dict(V3F, led=False, o2='pcm')))
VAR['button without a ship-wake path (manufacturing judge)'] = short(evaluate(dict(V3F, merge_d12=False)))
VAR['parts <= 0.58 mm under the panel (window column -0.12 mm)'] = short(evaluate(dict(V3F, under_panel=0.58)))
VAR['one laminate with a corner notch, 0.70 mm glass over the whole top (rib and posts kept)'] = short(evaluate(dict(V3F, two_glass=False)))
VAR['E-5 option 2: no posts, full 2.50 mm strips (needs Sharp\'s written limit for a rib bearing on the panel border)'] = short(evaluate(dict(V3F, web_posts=0, strip_w=2.50)))
VAR['E-5 option 1 at its optimistic end: laminate edge Y 20.6, strips 2.40 mm'] = short(evaluate(dict(V3F, strip_w=2.40)))
VAR['window glass 0.80 mm (elastic bond instead of a rigid one)'] = short(evaluate(dict(V3F, window_glass=0.80)))
VAR['capsule top 0.20 mm 316L instead of strengthened glass (fallback if the glass fails the drop case)'] = short(evaluate(dict(V3F, capsule_top='steel')))
VAR['capsule 41 mm long (E-14 fallback if the pack cannot keep cell + tabs <= 33.4 mm)'] = short(evaluate(dict(V3F, capsule_len=41.0)))
VAR['thin cell (RFQ preference: >= 60 mAh minimum, >= 66 mAh nominal, <= 2.7 / 3.2 mm)'] = short(evaluate(dict(V3F, cell='thin cell (RFQ preference)')))
VAR['cell at its 60 mAh sensitivity'] = short(evaluate(dict(V3F, cell='GEB301030 at 60 mAh')))
VAR['ERM fallback: 10 mm coin (CLP1020 class, 0.75 G min) in a 10.6 mm cut-out (E-4; mass scaled by area, E)'] = short(evaluate(dict(V3F, motor_cut_d=10.6)))
_h = dict(V3F); LOAD_SAVE = LOAD['erm']; LOAD['erm'] = LOAD['erm_heavy']; VAR['heavy motor day (15 s) instead of 4.7 s'] = short(evaluate(_h)); LOAD['erm'] = LOAD_SAVE
VAR['harvest tables at R_LIM 22 ohm instead of 12 ohm (conservative check)'] = short(evaluate(dict(V3F, r_lim=22.0)))
# interim research build before panel samples: same lid, window glass masked, display and front light not fitted
NP = dict(V3F, display=False, front_light=False, panel_fitted=False, fl_space=True)
_np = evaluate(NP); _np['area'] = BASE['area']          # same board: display and light parts are populate-optional (footprints kept)
VAR['interim build without the panel (same lid, masked window)'] = short(_np)
VAR['for comparison: V3-N full-PV lid with the same 70 mAh set, no display (22 ohm tables; its own thermal fix needed)'] = short(evaluate(dict(NP, pvset='LID4+WR31', r_lim=22.0, web_posts=0, strip_w=2.50)))
with lid_strip(V3F['strip_w']):
    _hl = VE.hot_lid_points(PVSET, r_lim=12.0)
    _wd = VE.harvest_point(PVSET, 'walking|sun30', M.g_si(sun=0.45), 12.0, wing_ratio=0.0)
    _wd_ovc = VE.harvest_point(PVSET, 'walking|overcast', M.g_si(sun=0.1), 12.0, wing_ratio=0.0)
_plit = BASE['energy']['loads_uW']['MON_lit'] * 1e-6
VAR['T3 sensitivities at R_LIM 12 ohm, strips 2.30 mm (min/day)'] = dict(
    convention=round(_plit * 24 / (_hl['convention (G x 0.92, 25 C Voc)'] * 1e-6) * 60, 1),
    lid_35C=round(_plit * 24 / (_hl['lid at 35 C (G x 1.0)'] * 1e-6) * 60, 1), lid_45C=round(_plit * 24 / (_hl['lid at 45 C (G x 1.0)'] * 1e-6) * 60, 1),
    wing_dark_no_diode=round(_plit * 24 / (_wd * 1e-6) * 60, 1), overcast_wing_dark=round(_plit * 24 / (_wd_ovc * 1e-6) * 60, 0),
    harvest_uW=dict(_hl, wing_dark=round(_wd, 0), overcast_wing_dark=round(_wd_ovc, 0)))
VAR['cell mass at the datasheet value "approx 3 g" (U)'] = dict(worn_g=round(BASE['mass']['worn_g_2dp'] + 3.0 - CELLX['GEB301030']['g'][0], 1),
                                                          worn_g_max=round(BASE['mass']['worn_g_max'] + 3.0 - CELLX['GEB301030']['g'][1], 1))
OUT['variants'] = VAR
OUT['parts'] = dict(new_main_board={k: [dict(ref=p[0], part=p[1], lcsc=p[2], courtyard_mm2=p[3], height_max_mm=p[4]) for p in v] for k, v in PARTS_NEW.items()},
                    v3r_usb_block=[dict(ref=a[0], part=a[1], lcsc=a[2], courtyard_mm2=a[3], height_max_mm=a[4]) for a in C.USB_BLOCK],
                    v3r_display_block=[dict(ref=a[0], part=a[1], lcsc=a[2], courtyard_mm2=a[3], height_max_mm=a[4]) for a in C.DISP_BLOCK],
                    j15_contacts_mm2=J15_MM2, p0201_saving_mm2=round(P0201_V2 - sum(P0201_KEEP_0402.values()) + sum(P0201_V3_USB.values()), 2),
                    jlc_queries='V JLC public parts API 2026-11-13: lead 16:40-16:48 UTC (calc/data/jlc_search.json); eng_a 15:26-15:51 UTC; eng_b 15:34-15:53 UTC; '
                                'engineering lens 18:23-18:25 UTC (verify_work/engineering/data_run2/)',
                    head_accessory=dict(isolator_research=('UCC12040DVER', 'C5216535', 744, 'BASIC isolation, 3 kVrms, 500 mW, 60 % peak, > 8 mm creepage and '
                                                           'clearance (V ti.com/product/UCC12040, read again 2026-11-13); OFF THE WRIST ONLY (E-1)'),
                                        isolator_wearer=('UCC12050', 'C2868010 / C504571', 0, 'REINFORCED, 5 kVrms (V JLC listing); JLC stock 0, presale only '
                                                         '(V 18:25 UTC): consigned for every head given to wearers (E-1)'),
                                        pogo_male_prototype=('Xinyangze YZR0158-20050-03025-01', 'C5126841', 80, 'catalogue 3P magnetic pogo male, 2.5 mm '
                                                             'pitch class (V JLC listing): prototypes off the wrist only; the product head uses a custom '
                                                             'pitch and magnet code (E-1)'),
                                        no_load_input_current='U: not on the TI product page (read again today); a V3-G10 item',
                                        size_mm=(25, 15, 7), mass_g=(4, 6), dissipation_on_pod_mW=(90, 165), note='E eng_a: head not designed'))

# ---- low-part zone under the panel (V3-G1 input) ------------------------------------------------------------------------------
def zone(cfg, limit=0.70):
    rem = {x['ref'] for x in C.area_config(dict(C.CONFIGS['V3-R'], alert_led=cfg['led'], usb_tab=False,
                                                strap_conductors=dict(root_A=['BATT_P', 'GND', 'NTC', 'GND'], root_B=['PV_W+', 'GND'])))['removed']}
    tall = sum(C.cy(r) for r in C.SKY if r not in rem and C.h(r) > limit)
    tall_v3 = sum(a[3] for a in C.USB_BLOCK + C.DISP_BLOCK[:-1] if (a[4] or 0) > limit) + 10.35 * (0.65 > limit) + J15_MM2   # R130 1206 0.65 mm; J15 1.4 mm
    tall_new = sum(p[3] for k in ('front_light', 'erm', 'button', 'merge_d12', 'o2') for p in PARTS_NEW[k] if p[4] > limit)
    tall_tot = tall + tall_v3 + tall_new
    ev = area(cfg); zone_area = ev['placement_area_mm2'] - 33.0 * 15.0
    return dict(limit_mm=limit, tall_courtyard_mm2=round(tall_tot, 1), tall_zone_area_mm2=round(zone_area, 1), tall_zone_utilisation=round(tall_tot / zone_area, 3),
                tall_zone_utilisation_v1=round(tall_tot / zone_area * C.V1_BBOX, 3))
OUT['low_part_zone'] = {'parts <= 0.70 mm under the panel (baseline)': zone(V3F, 0.70), 'parts <= 0.58 mm under the panel (option)': zone(V3F, 0.58)}

# ===================================================================================================== 7. charge limits, cold start, deep discharge
CB70 = C.EN['charge_bound']['LID2+WR31 with the 70 mAh cell, R_LIM 12/13/15']
CBX = {k: v['c_rate'] for k, v in CB70.items() if k.startswith('R12 |')}
OUT['charge_limits'] = dict(
    pv_bound_R12_70mAh=CBX,
    pv_bound_R12_minus10_minus20_k072=(CB70['R12 | 1.2 sun, strings at -10 C | k 0.72']['c_rate'], CB70['R12 | 1.2 sun, strings at -20 C | k 0.72']['c_rate']),
    bom_mixup_R12_with_43mAh_cell=(round(CB70['R12 | 1.2 sun, strings at -10 C | k 0.72']['c_rate'] * 70 / 43, 3),
                                   round(CB70['R12 | 1.2 sun, strings at -20 C | k 0.72']['c_rate'] * 70 / 43, 3)),
    pv_bound_R12_with_66mAh_nominal=(round(CB70['R12 | 1.2 sun, strings at -10 C | k 0.72']['c_rate'] * 70 / 66, 3),
                                     round(CB70['R12 | 1.2 sun, strings at -20 C | k 0.72']['c_rate'] * 70 / 66, 3)),
    usb_c_rate_by_nominal_mAh={f'{n} mAh': (round(KISET[1] / 10.2 / n, 3), round(KISET[2] / (10.2 * 0.99) / n, 3)) for n in (60, 66, 70)},   # [S1 D-8] max incl. R140 -1 %
    deep_discharge_R12_70mAh=VE.deep_discharge(PVSET, r_lim=12.0, cap_mAh=70.0),
    cold_start_dissipation_R12=VE.cold_start_rlim(PVSET, r_lims=(12.0,)),
    usb_c_rate=BASE['energy']['usb_c_rate_typ_max'], cell_max_charge_C=1.0, project_rule_C=0.5,
    note='E: PV bound = every string at 1.2 sun, k 0.72, cell 3.0 V (V3 convention), computed with the full 2.50 mm strips: an upper bound for '
         'the 2.30 mm strips; the 43 mAh row shows why R130 = 12 ohm is locked to the pack; RISET 10.2 k keeps <= 0.5 C at >= 66 mAh nominal with KISET max and R140 -1 % (S1 D-8)')
WS = C.EN['wing_light_study'][PVSET]
with lid_strip(V3F['strip_w']):
    _cs = dict(wing_lit_uA=round(VE.cs_at(PVSET, 200) * 1e6, 1), wing_quarter_uA=round(VE.cs_at(PVSET, 200, 0.25) * 1e6, 1),
               wing_dark_uA=round(VE.cs_at(PVSET, 200, 0.0) * 1e6, 1),
               lux_needed=dict(wing_lit=VE.lux_for_cold_start(PVSET, 0.867), wing_quarter=VE.lux_for_cold_start(PVSET, 0.25), wing_dark=VE.lux_for_cold_start(PVSET, 0.0)))
OUT['cold_start'] = dict(need_uA=21.4, V3F_strips_2p30=_cs,
                         V3R_full_strips=dict(wing_lit_uA=C.EN['cold_start_uA'][PVSET], wing_dark_uA=WS['no diode | wing 0 x lid']['cold_start_uA_200lx'],
                                              lux_needed=dict(wing_lit=WS['no diode | wing 0.867 x lid | lux for 21.4 uA'], wing_quarter=WS['no diode | wing 0.25 x lid | lux for 21.4 uA'],
                                                              wing_dark=WS['no diode | wing 0 x lid | lux for 21.4 uA'])),
                         note='E: cs_at() / lux_for_cold_start() of v3_energy with the lid strips at 2.30 mm; R_LIM does not change the cold-start current (node at 0.70 V)')

# ===================================================================================================== 8. water pressure, rib, capsule top (eng_a lane and engineering-lens methods, copied)
def navier(a, b, t, E, nu, q=1.0, terms=79):
    D = E * t ** 3 / (12 * (1 - nu ** 2)); w = 0.0; mx = 0.0; my = 0.0
    for m in range(1, terms + 1, 2):
        for n in range(1, terms + 1, 2):
            s = (-1) ** ((m + n) // 2 - 1); den = m * n * (m * m / a ** 2 + n * n / b ** 2) ** 2
            w += s / den; mx += s * (m * m / a ** 2 + nu * n * n / b ** 2) / den; my += s * (nu * m * m / a ** 2 + n * n / b ** 2) / den
    w *= 16 * q / (math.pi ** 6 * D); mx *= 16 * q / math.pi ** 4; my *= 16 * q / math.pi ** 4
    return w, 6 * max(mx, my) / t ** 2
def levy_free_edge(a, b, t, E, nu, q=1.0, terms=61):
    """engineering lens check_mech.py (validated there against Navier): plate simply supported on three edges, FREE on the fourth (y = b);
    deflection at (a/2, b) in mm for q in MPa"""
    D = E * t ** 3 / (12 * (1 - nu ** 2)); w = 0.0; x = a / 2; y = b
    for m in range(1, terms + 1, 2):
        al = m * math.pi / a; wp = 4 * q * a ** 4 / (D * math.pi ** 5 * m ** 5)
        def g(yy):
            e0 = math.exp(-al * yy); s = b - yy; eb = math.exp(-al * s)
            g1 = [e0, -al * e0, al ** 2 * e0, -al ** 3 * e0]
            g2 = [al * yy * e0, al * e0 * (1 - al * yy), -al ** 2 * e0 * (2 - al * yy), al ** 3 * e0 * (3 - al * yy)]
            g3 = [eb, al * eb, al ** 2 * eb, al ** 3 * eb]
            g4 = [al * s * eb, -al * eb * (1 - al * s), -al ** 2 * eb * (2 - al * s), -al ** 3 * eb * (3 - al * s)]
            return [[g1[k], g2[k], g3[k], g4[k]] for k in range(4)]
        G0, Gb = g(0.0), g(b)
        rows = [G0[0], G0[2]]; rhs = [-wp, 0.0]
        rows.append([Gb[2][i] - nu * al ** 2 * Gb[0][i] for i in range(4)]); rhs.append(nu * al ** 2 * wp)
        rows.append([Gb[3][i] - (2 - nu) * al ** 2 * Gb[1][i] for i in range(4)]); rhs.append(0.0)
        cc = np.linalg.solve(np.array(rows), np.array(rhs)); Gy = g(y)
        w += (wp + sum(cc[i] * Gy[0][i] for i in range(4))) * math.sin(m * math.pi * x / a)
    return w
GLS = dict(E=70e3, nu=0.22)
SPAN_PV = round(31.6 - LAM_EDGE_Y[V3F['strip_w']], 1)          # PV laminate glass span across the forearm: rib edge to the ring at Y 31.6
PR = {}
for lab, a, b, t, E, nu, gap in (
        (f'PV laminate glass 0.50 mm, 28.7 x {SPAN_PV} mm between the ring and the supported rib, to the parts (0.15 mm)', 28.7, SPAN_PV, 0.50, 70e3, 0.22, 0.15),
        ('window glass 0.70 mm, 36.0 x 14.6 mm on the stage-1 rail and rib (S1 C-1), to the film / panel (0.10 mm air gap at the max-material panel)', 36.0, 14.6, 0.70, 70e3, 0.22, 0.10),
        ('window glass 0.80 mm (elastic-bond alternative), same span', 36.0, 14.6, 0.80, 70e3, 0.22, 0.10),
        ('window glass 0.50 mm (V3 thickness), same span', 36.0, 14.6, 0.50, 70e3, 0.22, 0.10),
        ('window glass 0.70 mm on the stage-0 CAD supports (36 x 19 mm, review C-1), 0.045 mm gap at the max-material panel', 36.0, 19.0, 0.70, 70e3, 0.22, 0.045),
        ('V3 single lid glass 0.50 mm over 37 x 31 mm, to the panel (0.10 mm)', 37.0, 31.0, 0.50, 70e3, 0.22, 0.10),
        ('capsule top 0.40 mm PC over 37.4 x 10.9 mm, to the cell (0.20 mm)', 37.4, 10.9, 0.40, 2.3e3, 0.37, 0.20),
        ('capsule top 0.40 mm strengthened glass over the same span (V3-F)', 37.4, 10.9, 0.40, 70e3, 0.22, 0.20),
        ('capsule top 0.20 mm 316L over the same span (fallback)', 37.4, 10.9, 0.20, 193e3, 0.29, 0.20)):
    w1, s1 = navier(a, b, t, E, nu, q=0.1)
    pc = gap / w1
    PR[lab] = dict(contact_bar_SS=round(pc, 2), contact_bar_clamped_about=round(pc / 0.31, 1), stress_MPa_at_5bar_SS=round(s1 * 5.0, 0),
                   passes_5bar_SS=pc >= 5.0, passes_5bar_clamped=pc / 0.31 >= 5.0)
FREE = {}
for lab, a, b, t, gap in (('PV laminate glass 0.50 mm, 28.7 x 11.5 mm, rib edge free (pre-fix two-glass top, no rib support)', 28.7, 11.5, 0.50, 0.15),
                          ('window glass 0.70 mm, 33.0 x 14.5 mm, rib edge free (pre-fix two-glass top, no rib support)', 33.0, 14.5, 0.70, 0.10)):
    wf = levy_free_edge(a, b, t, **GLS, q=1.0)
    FREE[lab] = dict(edge_deflection_mm_per_bar=round(wf * 0.1, 3), contact_bar=round(gap / (wf * 0.1), 2), deflection_at_IP68_1p5m_mm=round(wf * 0.015, 3))
W5 = 0.5 * (SPAN_PV / 2 + 14.6 / 2)                               # N/mm on the rib at 5 bar (half of each glass span; S1 C-1 window span 14.6)
def beam_ss(wl, L, E, bw, h): return 5 * wl * L ** 4 / (384 * E * bw * h ** 3 / 12)
RIB = dict(line_load_N_per_mm_5bar=round(W5, 2), total_N_5bar_over_33mm=round(W5 * 33, 0),
           PC_rib_0p5x0p7_free_33mm_mm=round(beam_ss(W5, 33.0, 2.3e3, 0.5, 0.7), 0), steel_rib_0p5x0p7_free_33mm_mm=round(beam_ss(W5, 33.0, 193e3, 0.5, 0.7), 1),
           steel_rib_0p5x0p7_between_posts_6mm_mm=round(beam_ss(W5, 6.0, 193e3, 0.5, 0.7), 3),
           post_pitch_for_0p05mm_steel_mm=round((0.05 * 384 * 193e3 * 0.5 * 0.7 ** 3 / 12 / (5 * W5)) ** 0.25, 1),
           geometry='panel ends Y 20.0; rib Y 20.0-21.0 with a 0.5 x 0.7 mm stainless insert; 6 posts to the board (pitch <= 6 mm); window glass edge on '
                    'the rib Y 20.0-20.5, PV laminate edge Y 21.0',
           note='E: pre-fix web over the panel border (Y 19.6-20.1) could be no deeper than the 0.10 mm air gap and had no post room (engineering lens E-5)')
WIN_T = {}
_w70 = navier(36.0, 14.6, 0.70, **GLS, q=0.1)[0]   # [S1 C-1]
for pbar in (5.0, 6.0, 7.5):
    WIN_T[f'{pbar:g} bar'] = round(0.70 * (_w70 * pbar / 0.10) ** (1 / 3), 3)
FLOOR = dict(force_on_motor_N_5bar=round(0.5 * math.pi * 4.3 ** 2, 1),
             PC_film_0p25_clamped_deflection_mm=round(0.5 * 4.3 ** 4 / (64 * (2.3e3 * 0.25 ** 3 / (12 * (1 - 0.37 ** 2)))), 2),
             Ti_disc_0p25_clamped_deflection_mm=round(0.5 * 4.3 ** 4 / (64 * (105e3 * 0.25 ** 3 / (12 * (1 - 0.34 ** 2)))), 3),
             Ti_disc_extra_g=round(math.pi * 4.3 ** 2 * 0.25 * (C.RHO['ti'] - C.RHO['pc']), 3), motor_top_to_lid_mm=0.15,
             button_membrane_3x3mm_force_N_5bar=round(0.5 * 9.0, 1), PTS840_operating_force_N=2.2,
             note='E clamped circular plate; V PTS840 2.2 N (JLC attributes 18:24 UTC); membrane size assumed (E-12)')
OUT['water_pressure'] = dict(cases=PR, rib_edge_free_without_support=FREE, rib=RIB, window_glass_t_needed_SS_mm=WIN_T, floor_and_button_5bar=FLOOR,
                             method='E: thin-plate Navier series, simply supported (upper bound); clamped about 0.31 x the deflection; Levy series for a free '
                                    'edge (engineering lens, validated); glass E 70 GPa, PC 2.3 GPa, 316L 193 GPa; 1 bar = 10.2 m')
def capsule_press(E, nu, t, aa=37.4, bb=10.9, F=30.0):
    w_uni = navier(aa, bb, t, E, nu, q=F / (aa * bb))[0]
    c_, d_ = 15.0, bb; Dp = E * t ** 3 / (12 * (1 - nu ** 2)); w = 0.0; q = F / (c_ * d_)
    for m in range(1, 199, 2):
        for n in range(1, 199, 2):
            qmn = 16 * q / (math.pi ** 2 * m * n) * math.sin(m * math.pi / 2) * math.sin(n * math.pi / 2) * math.sin(m * math.pi * c_ / (2 * aa)) * math.sin(n * math.pi * d_ / (2 * bb))
            w += qmn / (Dp * math.pi ** 4 * (m * m / aa ** 2 + n * n / bb ** 2) ** 2) * math.sin(m * math.pi / 2) * math.sin(n * math.pi / 2)
    return dict(uniform_SS_mm=round(w_uni, 3), thumb_15mm_SS_mm=round(w, 3), point_SS_mm=round(0.1851 * F * bb ** 2 / (E * t ** 3), 3))
CAPTOP = {lab: capsule_press(E, nu, t) for lab, E, nu, t in (('PC 0.40 mm (V3)', 2.3e3, 0.37, 0.40), ('glass-filled PC 0.40 mm, E 6 GPa (pre-fix typical)', 6.0e3, 0.37, 0.40),
                                                           ('316L 0.15 mm', 193e3, 0.29, 0.15), ('316L 0.20 mm (fallback)', 193e3, 0.29, 0.20),
                                                           ('strengthened glass 0.40 mm (V3-F)', 70e3, 0.22, 0.40))}
for v in CAPTOP.values(): v['all_three_below_0p20_gap'] = max(v['uniform_SS_mm'], v['thumb_15mm_SS_mm'], v['point_SS_mm']) < 0.20
OUT['capsule_top_30N'] = dict(gap_end_of_life_mm=0.20, load_cases='30 N spread over the top; 30 N on a 15 mm thumb patch; 30 N on a 5 mm probe (Roark point, SS)',
                              cases=CAPTOP, mass_net_g=dict(glass=capsule_top_net_g('glass'), steel_0p20=capsule_top_net_g('steel')),
                              note='E: engineering-lens method (simply supported edges, as a bonded lid); V3-G7 defines the load case')

# ===================================================================================================== 9. worn geometry, thermal, RF, D-3 numbers
CAPS = {c: C.capsule_fit(c, t_caps=BASE['mass']['capsule_t_mm'], s0=2.0, s1=13.9) for c in ('C140_q0.68', 'C165_q0.68', 'C200_q0.68')}
OUT['worn_geometry'] = dict(capsule_fit=CAPS, wing_root_fit=C.WING_ROOT_FIT, capsule_outline_mm=(V3F['capsule_len'], 11.9, BASE['mass']['capsule_t_mm']),
                            convention='X-1: every worn item as its thickness above the skin where it rests; pod halves with the mesa pressed in; '
                                       'strap items at the far end of the free span (where they rest on the skin)',
                            thickness_above_skin_mm={f'{t:g} mm capsule': {f'{int(c)} mm wrist': item_on_free_span(c, t)['thickness_above_skin_at_far_end_mm'] for c in WRISTS}
                                                     for t in (3.5, 4.2, 4.5)},
                            wing_root_2p95_above_skin_mm={f'{int(c)} mm wrist': item_on_free_span(c, 2.95, s1=13.7)['thickness_above_skin_at_far_end_mm'] for c in WRISTS},
                            wrist_130mm=dict(capsule_4p5=item_on_free_span(130.0, 4.5), wing_root=item_on_free_span(130.0, 2.95, s1=13.7),
                                             geometry={k: round(v, 3) for k, v in wrist_geo(130.0).items() if not isinstance(v, np.ndarray)},
                                             note='E X-13: the strap lane ellipse (q 0.68) at 130 mm; the capsule ends 0.2 mm past the tangent point'),
                            highest_worn_V3F=BASE['worn'], highest_worn_V3R=CHECK_V3R['worn'],
                            root_A_end_s_mm=16.0, root_A_note='no USB tab: root A ends at s 16 mm; one hinge zone (bar, s 0-2 mm)')
TH = C.TH
OUT['thermal'] = dict(pod_top_V3R_C1_alpha060_075=(TH['lumped_3node']['V3R_C1_top_alpha_0p60_on_4p65mm_pod'], TH['lumped_3node']['V3R_C1_top_alpha_0p75']),
                      capsule_grid_C=TH['capsule_grid_C'], wing_skin_165=TH['wing_skin_per_sub_cell_1D']['wrists']['165 mm wrist']['sub_cells'],
                      bare_skin=TH['wing_skin_per_sub_cell_1D']['bare_skin_alpha0p6_no_sweat_C'], winter_capsule=TH['winter_capsule_physics_lens'],
                      head_on_pod_mW=(90, 165), head_no_load_mW='U (UCC12040 no-load input current not published on the TI page): V3-G10 and V3-G2',
                      charger_loss_mW=dict(typ=round((5.0 - 3.7) * 30.0, 1), worst_5V0_2V8=round((5.0 - 2.8) * 33.0, 1)),
                      erm_W_for_seconds=round(ERM_A * VB, 3), front_light_mW=round(5e-3 * 3.0 * 1e3, 1),
                      note='E: lumped / 1-D planning numbers (V3_ARCH 7); SIM-13 replaces all of them')
def dist_rect(r1, r2):
    dx = max(r2[0] - r1[1], r1[0] - r2[1], 0.0); dy = max(r2[2] - r1[3], r1[2] - r2[3], 0.0); return round(math.hypot(dx, dy), 1)
KEEPOUT = (1.5, 6.5, 1.5, 4.5)
MOTOR_C = (20.0, 25.4)            # E-11: between the ECG plates (E1 ends near X 14, E2 starts near X 26), above the rib posts, below the board edge band (no slack in Y)
LAND_A = (4.5, 10.5, 29.0, 30.5)  # E-11: root-A entry lands moved toward the elbow end, clear of the motor cut-out
OUT['rf'] = dict(quarter_wave_mm=C.RF['quarter_wave_mm'], strap_tails=dict(root_A=['BATT_P', 'GND', 'NTC', 'GND'], root_B=['PV_W+', 'GND'], links='FB1-FB6'),
                 distances_mm={'contacts (X 0.4-3.7, Y 20.2-31.6) to the antenna keep-out': dist_rect((0.4, 3.7, 20.2, 31.6), KEEPOUT),
                               f'motor can (8 mm, planning centre X {MOTOR_C[0]:g}, Y {MOTOR_C[1]:g}) to the keep-out': round(math.hypot(MOTOR_C[0] - 6.5, MOTOR_C[1] - 4.5) - 4.0, 1),
                               'button (hand-end wall, Y 13.5-17.5) to the keep-out': dist_rect((38.5, 40.0, 13.5, 17.5), KEEPOUT),
                               'front-light LED tail (X 33-37 beside the panel) to the keep-out': dist_rect((33.0, 37.0, 6.0, 20.0), KEEPOUT),
                               'stainless rib insert (X 1-34, Y 20.0-20.5) to the keep-out': dist_rect((1.0, 34.0, 20.0, 20.5), KEEPOUT),
                               'display window to the keep-out (V3-R)': 1.5},
                 rib_length_vs_quarter_wave='the 33 mm stainless insert is close to lambda0/4 (30.7 mm): SIM-10/11 checks it grounded at the posts and floating',
                 removed='USB-C shell and its 36 mm VBUS/GND feed (a primary suspect of V3-R) are gone',
                 note='E: motor and button rule >= 10 mm from the antenna (eng_b); SIM-10/11 decides; 0.70 mm glass now lies over the antenna corner')
def i_patient_uA(V, f, I_touch=None, C_iso=None, R_par=0.0):     # eng_a lane model (copied)
    X = 0.0
    if I_touch: X += V / I_touch
    if C_iso: X += 1.0 / (2 * math.pi * f * C_iso)
    return round(V / math.hypot(X, R_par + 1.0e3) * 1e6, 1)
OUT['d3_patient_current_uA'] = dict(
    isolated_head_normal_condition={f'C_iso {c * 1e12:g} pF, 264 V 60 Hz': round(2 * math.pi * 60 * c * 264 * 1e6, 2) for c in (3.5e-12, 10e-12, 50e-12)},
    plain_cable_class_II={'0.25 mA class': i_patient_uA(115.0, 50.0, 0.25e-3), '0.5 mA class': i_patient_uA(115.0, 50.0, 0.5e-3)},
    single_fault_basic_barrier_shorted={'0.25 mA class': i_patient_uA(115.0, 50.0, 0.25e-3), '0.5 mA class': i_patient_uA(115.0, 50.0, 0.5e-3),
                                        'note': 'E-1: a basic (UCC12040) barrier shorted = a plain cable: at the 500 uA SFC limit with a compliant 0.5 mA charger'},
    look_alike_non_isolated_cable_worn_normal_condition={'0.25 mA class': i_patient_uA(115.0, 50.0, 0.25e-3), '0.5 mA class': i_patient_uA(115.0, 50.0, 0.5e-3),
                                                         'note': 'E-1: 2.5-5 x the 100 uA NC limit; excluded by contacts that catalogue magnetic plugs cannot mate'},
    reinforced_head_single_fault='a reinforced barrier (UCC12050) or two independent basic barriers keep the head isolating after one fault',
    limits='100 uA normal condition, 500 uA single fault (BF; Delta note p.3 via the usbc lane and the requirements lens)',
    d3c_needs_MOhm_per_electrode_with_E3_touched=3.45, note='E: eng_a lane model')

# ===================================================================================================== 10. GPIO budget
OUT['gpio'] = [
 dict(pin='P0.04', dock_wlcsp='ECG_START', V3R='ECG_START', V3F='MOTOR_PWM (Q12)', basis='ADS1291 started by the START opcode with the START pin held low by R316 (V ADS1291 p.44, p.48 via eng_b)'),
 dict(pin='P0.09', dock_wlcsp='spare', V3R='CHG_DIS', V3F='CHG_DIS (Q10 pulls TS low at 41 C skin)', basis='NFC pad, UICR NFCPINS'),
 dict(pin='P0.10', dock_wlcsp='spare', V3R='spare', V3F='FL_EN (Q11, PWM)', basis='NFC pad, UICR NFCPINS; 2-10 uA between the pads only while their levels differ (display lane)'),
 dict(pin='P0.17', dock_wlcsp='spare', V3R='EXTCOMIN', V3F='EXTCOMIN', basis='RTC -> PPI -> GPIOTE'),
 dict(pin='P0.19', dock_wlcsp='spare', V3R='DISP_EN', V3F='DISP_EN', basis='also VCCA and OE of U17'),
 dict(pin='P0.20', dock_wlcsp='spare', V3R='USB /PG', V3F='/PG (head attached)', basis='GPIO SENSE wakes System OFF'),
 dict(pin='P0.24', dock_wlcsp='ALERT_LED', V3R='ALERT_LED', V3F='ALERT_LED (freed if decision 5 (d) is accepted in writing)', basis='near-radio pin, static'),
 dict(pin='P0.26', dock_wlcsp='IMU_INT2', V3R='IMU_INT2', V3F='BUTTON (SENSE wake)', basis='LIS2DW12 FIFO threshold routed to INT1 (CTRL4 INT1_FTH; V via eng_b)'),
 dict(pin='P0.29', dock_wlcsp='spare', V3R='DISP_SCS', V3F='DISP_SCS', basis='display lane'),
]
OUT['gpio_left'] = 'none (P0.24 if the LED chain goes)'

# ===================================================================================================== 11. plan views (1 char = 1 mm in X, 1 line = 1 mm in Y)
def top_v3f(lx=40.0, w=V3F['strip_w']):
    y0s = LAM_EDGE_Y[w]
    r = [('.', 0.4, lx - 2.5, 0.4, 31.6)]
    for i in range(4):
        y0 = y0s + i * (w + 0.27); r.append(('P' if i % 2 == 0 else 'p', 3.7, 31.4, y0, y0 + w))
    r.append(('D', 1.0, 33.0, 6.0, 20.0)); r.append(('W', 1.0, 34.0, 20.0, y0s)); r.append(('K', 0.4, 3.7, 20.2, 31.6))
    r.append(('A', 1.5, 6.5, 1.5, 4.5)); r.append(('E', lx - 3.5, lx, 3.0, 29.0)); r.append(('B', lx - 1.0, lx, 13.5, 17.5))
    return C.raster(lx, r, f'V3-F top face ({lx:.0f} x 32 mm case; lid set back 2.5 mm at the E3 end; two glasses on a supported rib: '
                           f'window glass to Y 20.5, rib Y 20.0-{y0s:.1f}, PV laminate from Y {y0s:.1f})')
def board_v3f(lx=40.0):
    r = [('.', 1.5, lx - 1.5, 1.5, 30.5), ('l', 1.5, 33.5, 5.5, 20.5), ('A', 1.5, 6.5, 1.5, 4.5), ('c', 14.5, 25.5, 12.0, 19.0),
         ('a', LAND_A[0], LAND_A[1], LAND_A[2], LAND_A[3]), ('b', 14.0, 20.0, 1.5, 3.0),
         ('M', MOTOR_C[0] - 4.3, MOTOR_C[0] + 4.3, MOTOR_C[1] - 4.3, MOTOR_C[1] + 4.3),
         ('K', 1.5, 3.5, 21.0, 30.5), ('S', lx - 4.5, lx - 1.5, 13.5, 17.5)]
    for xp in (4.0, 10.0, 16.0, 22.0, 28.0, 33.0): r.append(('o', xp - 0.5, xp + 0.5, 19.8, 20.8))
    return C.raster(lx, r, f'V3-F main board zones ({lx - 3:.0f} x 29 mm board): . parts <= 1.05 mm, l low-part zone under the panel (<= 0.70 mm), '
                           'A antenna keep-out, c PPG cap / optics (skin face), a/b root-A/root-B entry lands, M motor cut-out 8.6 mm (planning position '
                           'between the ECG plates), o rib posts, K contact spring fingers, S side button')
OUT['plan_views'] = dict(top=top_v3f(), board=board_v3f(),
                         legend='P/p PV strips 27.7 x 2.30 mm (4 in series, from Y 21.0); D display window over the panel (X 1-33, Y 6-20); W rib with a stainless '
                                'insert and posts (Y 20.0-21.0); K two contact pins in the ring rim; A antenna keep-out seen through the lid; E E3 strip on '
                                'the top rim; B side button in the hand-end wall (below E3); . lid outside PV and window. Y = 0 = root B (antenna long '
                                'wall), Y = 32 = root A. Elbow at the left on a left wrist; on the right wrist the band is turned 180 degrees and the '
                                'face is flipped in firmware.')

# ===================================================================================================== 12. decision scores (judges' option scores, entered as data)
# Source: the three judges' structured returns (relayed in the synthesis task; notes in decide/judges/<judge>/NOTES.md).
# Each option: {judge: (E, M, P, R)}; S = strictest safety verdict among the judges. Lead score = mean of the judges who scored it;
# weighted total = 0.40 E + 0.25 M + 0.20 P + 0.15 R (criteria order of the task: experience, market, preference, risk).
J = {
 'D-1 place': {
   'capsule on root A (V3-R pod)': dict(S='COND (V3-G7, F1, O-2 inhibit)', consumer=(8, 7, 9, 5), research=(9, 9, 8, 6), manufacturing=(8, 8, 9, 5)),
   'V3-P: 43 mAh in a 49-52 mm pod': dict(S='PASS', consumer=(5, 5, 4, 7), research=(4, 5, 5, 5), manufacturing=(6, 6, 6, 6)),
   'V3-P with 70 mAh (6.30 mm or 55 mm)': dict(S='PASS', consumer=(6, 6, 3, 7), research=(5, 5, 3, 5)),
   'stacked pod 40 x 32': dict(S='PASS', consumer=(3, 4, 3, 4), research=(3, 4, 3, 3), manufacturing=(4, 4, 3, 5)),
   'volar clasp module': dict(S='COND', consumer=(2, 2, 5, 3), manufacturing=(3, 3, 5, 4))},
 'D-1 size': {
   '70 mAh GEB301030 class (protected pack)': dict(S='PASS', consumer=(9, 9, 8, 7), research=(9, 9, 8, 6), manufacturing=(9, 9, 8, 6)),
   '43 mAh GMB201030 (V3 default)': dict(S='PASS', consumer=(6, 7, 9, 6), research=(5, 7, 9, 6), manufacturing=(6, 7, 9, 8)),
   'LP301230 class (13.9 mm capsule)': dict(S='PASS', consumer=(7, 8, 7, 6), research=(8, 8, 7, 6), manufacturing=(8, 8, 7, 6))},
 'D-2 display': {
   'LS011B7DH03 + front light designed in, night blank': dict(S='PASS', consumer=(8, 8, 8, 4), research=(8, 8, 7, 4), manufacturing=(9, 8, 7, 4)),
   'LS011B7DH03 unlit (V3-R as published)': dict(S='PASS', consumer=(5, 3, 9, 6), research=(6, 4, 8, 5), manufacturing=(6, 4, 8, 6)),
   'no display (V3-N)': dict(S='PASS', consumer=(6, 6, 9, 8), research=(6, 7, 9, 8), manufacturing=(5, 6, 9, 7)),
   'LS013B7DH05 1.26" + film, glass-only top': dict(S='PASS (cold start fails)', consumer=(6, 7, 5, 4), research=(5, 7, 4, 4), manufacturing=(8, 8, 4, 3)),
   'e-paper': dict(S='FAIL (0-50 C rating)', consumer=(4, 5, 5, 2), research=(3, 5, 4, 1))},
 'D-3 worn charging (supervisor)': {
   '(b) now; target: isolated head or pack only, ECG off with VBUS': dict(S='PASS', consumer=(8, 8, 9, 7), research=(9, 8, 9, 6), manufacturing=(8, 8, 9, 6)),
   '(b) for good': dict(S='PASS', consumer=(6, 7, 8, 9), research=(6, 8, 10, 9), manufacturing=(6, 7, 9, 9)),
   '(c) >= 3.45 Mohm ahead of every clamp': dict(S='COND (ECG noise above M2)', consumer=(7, 6, 6, 3), research=(4, 6, 6, 3), manufacturing=(7, 6, 6, 3)),
   "(a') power bank only": dict(S='FAIL (cannot be enforced)', consumer=(6, 5, 9, 2), research=(6, 4, 10, 2), manufacturing=(7, 5, 9, 7))},
 'D-4 connector': {
   'two flush contacts + isolated USB-C head': dict(S='PASS', consumer=(8, 8, 10, 6), research=(8, 8, 9, 6), manufacturing=(7, 8, 9, 6)),
   '(a) USB-C tab on root A': dict(S='COND (off the wrist only)', consumer=(6, 6, 6, 5), research=(6, 6, 6, 4), manufacturing=(6, 6, 6, 3)),
   'tab and contacts': dict(S='COND', consumer=(5, 5, 5, 4), research=(6, 5, 5, 3), manufacturing=(6, 6, 5, 2)),
   'sealed receptacle in the pod end': dict(S='COND', consumer=(4, 5, 6, 4), research=(4, 6, 6, 3), manufacturing=(5, 6, 6, 3)),
   'contacts + clip-on pack now': dict(S='PASS', consumer=(8, 7, 10, 5), manufacturing=(8, 7, 9, 4))},
 'interaction': {
   'sealed side button + raise (sleep-locked) + gated tap': dict(S='PASS', consumer=(9, 9, 8, 6), research=(8, 9, 8, 6), manufacturing=(8, 8, 8, 6)),
   'raise-to-wake only (V3)': dict(S='PASS', consumer=(3, 3, 10, 9), research=(4, 3, 10, 9), manufacturing=(5, 4, 10, 9)),
   'E3 as a push key': dict(S='COND (electrode isolation)', consumer=(9, 9, 9, 4), research=(8, 7, 9, 3), manufacturing=(8, 7, 9, 3)),
   'capacitive touch': dict(S='PASS', consumer=(3, 5, 9, 4), research=(4, 6, 8, 5), manufacturing=(4, 5, 8, 4))},
 'alerts / decision 5 (supervisor)': {
   '(d) 8 mm ERM first + full-screen warning + BLE (+ LED until (d) is in writing)': dict(S='PASS', consumer=(8, 8, 8, 6), research=(9, 9, 8, 6), manufacturing=(9, 9, 8, 5)),
   '(b) side LED only (V3 default)': dict(S='COND (unseen in sun or sleep)', consumer=(3, 2, 10, 8), research=(3, 3, 10, 9), manufacturing=(3, 3, 10, 8)),
   'LRA + driver': dict(S='PASS (does not fit 2.40 mm)', consumer=(9, 9, 4, 3), research=(8, 9, 5, 3), manufacturing=(9, 9, 5, 4)),
   '(c) BLE flag only': dict(S='FAIL', consumer=(2, 2, 10, 8), research=(2, 2, 10, 9))},
 'T6 storage': {
   'SHELF claim; ship mode for transport, woken by button, head or light': dict(S='PASS', consumer=(9, 8, 9, 7), research=(9, 8, 10, 7), manufacturing=(8, 7, 8, 6)),
   'SHELF claim; ship mode woken by head or light only': dict(S='PASS', manufacturing=(8, 7, 9, 8)),
   'ship-mode claim (V3 default)': dict(S='PASS', consumer=(5, 5, 9, 7), research=(5, 6, 10, 8), manufacturing=(6, 6, 9, 7))},
 'water': {
   'product 5 ATM, first builds IP68 1.5 m, every unit leak-tested': dict(S='PASS', consumer=(9, 9, 8, 5), research=(8, 9, 7, 5), manufacturing=(9, 9, 7, 5)),
   'IP67': dict(S='PASS', consumer=(5, 4, 10, 8), research=(6, 5, 9, 7), manufacturing=(6, 5, 9, 8)),
   '10 ATM': dict(S='PASS', consumer=(9, 9, 6, 3), research=(8, 7, 4, 2))},
}
W8 = (0.40, 0.25, 0.20, 0.15)
SC = {}
for item, opts in J.items():
    SC[item] = {}
    for opt, d in opts.items():
        js = [v for k, v in d.items() if k != 'S']
        mean = [round(sum(x[i] for x in js) / len(js), 2) for i in range(4)]
        SC[item][opt] = dict(S=d['S'], judges={k: v for k, v in d.items() if k != 'S'}, mean_EMPR=mean,
                             weighted=round(sum(W8[i] * mean[i] for i in range(4)), 2))
def wsum(m): return round(sum(W8[i] * m[i] for i in range(4)), 2)
_ct = SC['D-4 connector']['two flush contacts + isolated USB-C head']['mean_EMPR']; _tb = SC['D-4 connector']['(a) USB-C tab on root A']['mean_EMPR']
D4S = {'contacts as scored': wsum(_ct), 'contacts with E - 1 (height premise removed)': wsum([_ct[0] - 1] + _ct[1:]),
       'contacts with E - 2': wsum([_ct[0] - 2] + _ct[1:]),
       'tab as scored': wsum(_tb), 'tab with E + 1': wsum([_tb[0] + 1] + _tb[1:]), 'tab with E + 2': wsum([_tb[0] + 2] + _tb[1:])}
D4S['winner_unchanged_at_contacts_E-2_tab_E+2'] = D4S['contacts with E - 2'] > D4S['tab with E + 2']
OUT['decision_scores'] = dict(weights='0.40 E + 0.25 M + 0.20 P + 0.15 R', items=SC,
                              d4_height_premise_sensitivity=dict(values=D4S, note='X-1(6): all three judges scored D-4 with the premise that the tab '
                                                                                  'was the highest worn point; the lead does not re-score for them'))

# ===================================================================================================== 13. market position numbers (lane figures, V there)
ST = BASE['stack']; EB_ = BASE['energy']
OUT['market_position'] = dict(thinnest_product_mm=8.3, median_mm=10.6, band_battery_median_d=8,
                              V3F_thinner_than_thinnest_pct=(round(100 * (1 - ST['pod_max_material_mm'] / 8.3), 0), round(100 * (1 - ST['pod_at_P121_upper_mm'] / 8.3), 0)),
                              T1_over_band_median=dict(night_blank=round(EB_['T1_dark_d'] / 8, 1), face_always_on=round(EB_['T1_dark_always_on_face_d'] / 8, 1),
                                                       worst_night_blank=round(EB_['T1_worst_stack_d'] / 8, 1), worst_face_always_on=round(EB_['T1_worst_stack_always_on_face_d'] / 8, 1)),
                              pod_length_along_forearm=dict(V3F_mm=40.0, V3P_mm=(49.1, 52.0), mainstream_bands_mm=(22.54, 24.86),
                                                            note='V Xiaomi Band 10 / HUAWEI Band 10 spec pages via UX S31, S32 (orientation inferred, E); '
                                                                 'the market lane\'s 33.97-47 mm "length" runs around the wrist (X-5)'),
                              note='V market lane (MARKET.md 3; Fitbit Air 8.3 mm, median of 15 bands and research devices 10.6 mm, band battery median 8 d)')

# ===================================================================================================== 14. fix-stage numbers quoted in the documents
U_ = EB_['usable_mWh']; P_ = EB_['loads_uW']['MON_dark']
dT1_per_uW = -U_ / (24 * (P_ * 1e-3) ** 2) * 1e-3
WFd = {w['step'].split(' ')[0]: w for w in WF}
day_mWh = P_ * 24 / 1000.0
H = EB_['harvest_uW']
def minutes_for_a_day(h_uW, load_uW=0.0):
    net = h_uW - load_uW
    return round(day_mWh / (net / 1000.0) * 60.0, 0) if net > 0 else None
OUT['fix_stage_numbers'] = dict(
    dT1_per_uW_d=round(dT1_per_uW, 4),
    erm=dict(load_uW=round(LOAD['erm'] * 1e6, 2), linear_d=round(dT1_per_uW * LOAD['erm'] * 1e6, 2), waterfall=(WFd['3b']['T1_d'], WFd['4']['T1_d'])),
    tap=dict(load_uW=round(LOAD['tap'] * 1e6, 2), linear_d=round(dT1_per_uW * LOAD['tap'] * 1e6, 2), waterfall_button_and_tap=(WFd['4']['T1_d'], WFd['5']['T1_d'])),
    ship_wake_merge_utilisation=dict(with_path=BASE['area']['utilisation'], without_path=VAR['button without a ship-wake path (manufacturing judge)']['utilisation']),
    skin_hot_event=dict(SKIN_HOT, share_of_usable_pct=round(100 * SKIN_HOT['mWh_per_event'] / U_, 1), days_of_MON=round(SKIN_HOT['mWh_per_event'] / day_mWh, 2)),
    rescue_without_head=dict(one_day_of_MON_mWh=round(day_mWh, 2),
                             minutes_per_day_of_use={'sun 0.45 (about 50 klx)': minutes_for_a_day(H['sun045']), 'bright overcast 0.2 sun': minutes_for_a_day(H['sun02']),
                                                     'overcast 0.1 sun': minutes_for_a_day(H['ovc01']),
                                                     'dull daylight 0.03 sun (outdoor-posture proxy, E)': minutes_for_a_day(H['ovc003'])},
                             indoor_uW={'200 lx': H['lux200'], '300 lx': H['lux300'], '1000 lx': H['lux1000']}, MON_load_uW=(P_, EB_['loads_uW']['MON_lit']),
                             hours_per_day_of_use_resting_in_SHELF={k: (round(day_mWh / ((H[kk] - EB_['loads_uW']['SHELF']) / 1000.0), 0) if H[kk] > EB_['loads_uW']['SHELF'] else None)
                                                                    for k, kk in (('300 lx', 'lux300'), ('1000 lx', 'lux1000'))},
                             cold_start_lux=_cs['lux_needed'],
                             note='E: worn MON load against the harvest tables (R_LIM 12 ohm, strips 2.30 mm); room light restarts a flat band but never pays for a day of use'),
    solar_claim=dict(T3_sun_045_wing_lit_min=EB_['T3_min_day_045sun'], T3_overcast_min=EB_['T3_overcast_min_day_01sun'],
                     T3_wing_dark_min=VAR['T3 sensitivities at R_LIM 12 ohm, strips 2.30 mm (min/day)']['wing_dark_no_diode'],
                     W4_definition='20 min a day at 0.45 sun on lid and wing, nothing else (v2/sim/power/sim05/energy_budget_v2.py)',
                     W4=EB_['weeks_from_50pct']['W4_sun_20min']),
    T1_conventions=dict(night_blank=(EB_['T1_dark_d'], EB_['T1_worst_stack_d'], EB_['T1_max_currents_d']),
                        face_always_on_V3=(EB_['T1_dark_always_on_face_d'], EB_['T1_worst_stack_always_on_face_d'], EB_['T1_max_currents_always_on_face_d']),
                        V3R=(CHECK_V3R['energy']['T1_dark_d'], CHECK_V3R['energy']['T1_worst_stack_d'], CHECK_V3R['energy']['T1_max_currents_d'])),
    gate1=dict(util_exact=BASE['area']['utilisation_exact'], v1_exact=BASE['area']['utilisation_v1_exact'], v1_pass=BASE['area']['gate1_pass_v1_measure']),
    window_column_layers=BASE['stack']['window_column']['layers'],
    motor_column=dict(floor_top_to_lid_mm=2.40, carrier_film_cut_under_motor=True, psa=0.05, motor_max_mm=2.20, margin_mm=round(2.40 - 0.05 - 2.20, 2),
                      margin_if_on_carrier_film_mm=round(2.40 - 0.10 - 0.05 - 2.20, 2), source='V CLP1020 sister part 2.1 +- 0.1 mm via ENG_B notes'),
    capsule_length=dict(inside_mm=round(38.4 - 1.0, 1), GEB_body_mm=30.0, GEB_tab_mm=(5.0, 7.0), PCM_end_mm=4.0,
                        needed_with_full_tabs_mm=(39.0, 41.0), rfq_rule='cell + tab joints <= 33.4 mm, PCM flat <= 4 mm (tabs trimmed before welding)'),
)

OUT['meta']['runtime_s'] = round(time.time() - T0, 1)
json.dump(OUT, open(os.path.join(HERE, 'baseline_calc_v3f_' + FINAL['mode'] + '.json'), 'w'), indent=1, default=float, ensure_ascii=False)

if __name__ == '__main__' and os.environ.get('SIM05_PRINT'):
    b = BASE
    print('runtime', OUT['meta']['runtime_s'], 's; cache redirected', C.CACHE_REDIRECTED)
    print('CHECK V3-R', OUT['check_V3R_reproduced'])
    print('STACK', {k: v for k, v in b['stack'].items() if k not in ('pv_column', 'window_column', 'tolerance_lists')}, b['stack']['pv_column']['total'], b['stack']['window_column']['total'])
    print('WORN', b['worn'])
    print('AREA', {k: v for k, v in b['area'].items() if k != 'added'})
    print('MASS', {k: v for k, v in b['mass'].items() if k in ('pod_g', 'pod_g_max', 'strap_g', 'strap_g_max', 'worn_g', 'worn_g_max', 'worn_g_2dp', 'capsule_t_mm')})
    print('MASS ADD', b['mass']['pod_additions'], b['mass']['strap_additions_typ'], b['mass']['strap_additions_max'])
    e = b['energy']; print('ENERGY', {k: v for k, v in e.items() if k not in ('weeks_from_50pct', 'T7_h')})
    print('T7', e['T7_h']); [print('  WEEK', w, v) for w, v in e['weeks_from_50pct'].items()]
    for w in WF: print('WF', w)
    for k, v in VAR.items(): print('VAR', k, v)
    print('ZONE', OUT['low_part_zone'])
    print('CHARGE', {k: v for k, v in OUT['charge_limits'].items() if k != 'pv_bound_R12_70mAh'})
    print('COLD', OUT['cold_start'])
    for k, v in PR.items(): print('PRESS', k, v)
    print('FREE', FREE); print('RIB', RIB); print('WIN_T', WIN_T); print('FLOOR', FLOOR)
    print('CAPTOP', CAPTOP)
    print('CAPS', CAPS)
    print('WORN GEO', {k: v for k, v in OUT['worn_geometry'].items() if k in ('thickness_above_skin_mm', 'wing_root_2p95_above_skin_mm', 'wrist_130mm')})
    print('RF', OUT['rf']['distances_mm'])
    print('D3', OUT['d3_patient_current_uA'])
    for it, opts in SC.items():
        for o, d in opts.items(): print('SCORE', it, '|', o, d['mean_EMPR'], d['weighted'], d['S'])
    print('D4 SENS', D4S)
    print('MARKET', OUT['market_position'])
    print('FIX', json.dumps(OUT['fix_stage_numbers'], default=float))
    print('\n'.join(OUT['plan_views']['top'])); print('\n'.join(OUT['plan_views']['board']))
