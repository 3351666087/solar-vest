#!/usr/bin/env python3
"""Collects the SIM-03 / SIM-05 results of this folder into power_results.json and writes the table of POWER.md (between the markers)."""
import os, json
H = os.path.dirname(os.path.abspath(__file__))
def J(p): return json.load(open(os.path.join(H, p)))
S5 = {m: J(f'sim05/sim05_{m}.json') for m in ('typ', 'bounds')}
O2 = {p: J(f'sim03/o2_{p}.json')[p] for p in ('window', 'matrix', 'dyn', 'coldstart')}
O2['vpor16'] = J('sim03/o2_vpor16.json'); MI = J('sim03/misc_results.json'); REF = J('sim03/o2_inhibit.json')
A, B = '41x32 strips 2.30 mm', '41x34 strips 2.80 mm'
eb = {c: S5['bounds'][c]['energy'] for c in (A, B)}; et = {c: S5['typ'][c]['energy'] for c in (A, B)}
def wk(e, w): return e['weeks_from_50pct'][w]['days_from_full_if_negative']
cs = O2['coldstart']
mx = max(v['iq14_max_uA'] for k, v in O2['matrix'].items() if not k.startswith('25'))
hb = O2['dyn']
rel = [v['release_after_last_pulse_s'] for k, v in hb.items() if k.startswith('heartbeat')]
hap_fw = [v['margin_to_VBAT_OK_fall_max_3p441_mV'] for k, v in MI['haptic'].items() if 'firmware rule' in k]
hap_ramp = [v['margin_to_VBAT_OK_fall_max_3p441_mV'] for k, v in MI['haptic'].items() if '30 ms PWM soft start' in k]
cb = MI['charge_bound_R12_plus_Q14']
q8 = [v['C_70'] for v in MI['q8_single_fault'].values()]; q8_66 = [v['C_66'] for v in MI['q8_single_fault'].values()]
ch = MI['vbat_ok_chatter']; steps = [v['step_mV'] for v in ch.values()]
sun = {c: S5['bounds'][c]['sun_cases'] for c in (A, B)}
edge = {c: S5['bounds'][c]['edge_shunt'] for c in (A, B)}
ROWS = [
 # SIM-03 / V3-G4
 ('G4-a', 'cold start, dead band off the wrist, wing 1/0.5/0.25/0.1/0 x lid, through the O-2 (MCU off)',
  'BASELINE 11.5: >= 21.4 uA at 200 lx; "off the wrist about 360 lx or the head"',
  f"200 lx: 0 uA at every ratio (V_O2 below the comparator POR). Light for 21.4 uA (2.30 / 2.80 mm): "
  + '; '.join(f"wing {w:g}: {cs[f'wing {w:g} x lid | strips 2.30 mm']['lux_for_21p4uA_through_O2']:.0f}/{cs[f'wing {w:g} x lid | strips 2.80 mm']['lux_for_21p4uA_through_O2']:.0f}" for w in (1, 0.5, 0.25, 0.1, 0))
  + f" lx (POR 1.50 V); POR 1.60 V: {O2['vpor16']['VPOR 1.60 V | wing 1 | strips 2.30 mm']['lux_for_21p4uA_through_O2']:.0f} / {O2['vpor16']['VPOR 1.60 V | wing 0 | strips 2.30 mm']['lux_for_21p4uA_through_O2']:.0f} lx (wing 1 / 0). Without the O-2: 155-358 lx", 'FAIL'),
 ('G4-c', 'VBAT_OK chatter', 'no VBAT_OK chatter (SIM-03c)',
  f"hysteresis 91 mV against the VSTOR step when PV charge stops: {min(steps):.0f}-{max(steps):.0f} mV; >= 91 mV only at 1.2 sun with a 0 C cell (5.25 ohm path), and only if the heartbeat is not running within the C174 hold after VBAT_OK rises ⚠", 'PARTIAL'),
 ('G4-e', 'PV_INH probe (MCU on, heartbeat, 1 sun)', 'probe as V3 4.3: INA_PV = Isc, no PV current to the cell, MPPT back',
  f"INA_PV/Isc {hb['PV_INH probe (MCU on, 1 sun, Q14 Vth 0.95)']['INA_PV_over_Isc']}; PV_SW {hb['PV_INH probe (MCU on, 1 sun, Q14 Vth 0.95)']['pvsw_during_probe_mV']:.0f} mV; Q14 <= {hb['PV_INH probe (MCU on, 1 sun, Q14 Vth 0.95)']['iq14_during_probe_uA']:.0f} uA (C101 back-flow); back to 90 % in {hb['PV_INH probe (MCU on, 1 sun, Q14 Vth 0.95)']['recovery_to_90pct_ms']:.0f} ms (next heartbeat)", 'PASS'),
 ('G4-g', 'EN, ship mode, wake pair (D12: VBUS and button)', 'ship wake by the button and the head',
  f"head 5.0 / 4.75 V: EN_HOLD 1.0 V after {MI['EN_ship_wake']['head VBUS 5.0 V']['t_to_EN_HOLD_1V_s']:.2f} / {MI['EN_ship_wake']['head VBUS 4.75 V (minimum at the band)']['t_to_EN_HOLD_1V_s']:.2f} s; button 0.30 s press at VBAT 4.1-2.8 V: {MI['EN_ship_wake']['button at VBAT 4.1 V (press 0.30 s)']['t_to_1V_s']:.2f}-{MI['EN_ship_wake']['button at VBAT 2.8 V (press 0.30 s)']['t_to_1V_s']:.3f} s; light wake 200 lx 13.9 s; D12 unbiased in ship mode", 'PASS'),
 ('G4-q8', 'Q8 interlock at plug-in, 1.2 sun', 'PV and USB never at once (BASELINE 11.5, 13.3)',
  f"Q14 current < 1 % {hb['Q8 | MCU on (heartbeat), 1.2 sun']['t_to_1pct_ms']} ms after VBUS (MCU on and off); Q8 carries the {hb['Q8 | MCU on (heartbeat), 1.2 sun']['i_shorted_PV_mA']:.0f} mA PV short", 'PASS'),
 ('G4-q8f', 'Q8 single fault', 'no state above 0.5 C for a cell above the protector trip',
  f"Q8 short: PV always shorted (no harvest, safe). Q8 open, MCU on: Q1 backup in 5 ms. Q8 open, MCU off (cell 3.0-3.40 V, VBAT_OK low): the O-2 approves and the PV ({min(v['pv_mA'] for v in MI['q8_single_fault'].values()):.1f}-{max(v['pv_mA'] for v in MI['q8_single_fault'].values()):.1f} mA) adds to USB 32.7 mA = {min(q8):.2f}-{max(q8):.2f} C (70 mAh), up to {max(q8_66):.2f} C (66 mAh), until VBAT_OK rises", 'FAIL'),
 ('G4-rlim', 'R_LIM 12 ohm + Q14 bound, 1.2 sun, strings -10 / -20 C, k 0.72, cell 3.0 V', '<= 0.5 C',
  f"2.30 mm {cb['strips 2.30 mm | 1.2 sun strings -10 C | k 0.72']['C_70']}/{cb['strips 2.30 mm | 1.2 sun strings -20 C | k 0.72']['C_70']} C; 2.80 mm {cb['strips 2.80 mm | 1.2 sun strings -10 C | k 0.72']['C_70']}/{cb['strips 2.80 mm | 1.2 sun strings -20 C | k 0.72']['C_70']} C (66 mAh: {cb['strips 2.80 mm | 1.2 sun strings -20 C | k 0.72']['C_66']}); MCU off the O-2 blocks < 0 C anyway", 'PASS'),
 ('G4-dd', 'deep-discharge currents (three-diode path), inside the O-2 window', "within the cell maker's written limit",
  f"cell 0 / 0.5 / 1.0 V: 2.30 mm {MI['deep_discharge']['strips 2.30 mm | 1.2 sun 0 C (O-2 window edge) | cell 0 V']['C_70']}/{MI['deep_discharge']['strips 2.30 mm | 1.2 sun 0 C (O-2 window edge) | cell 0.5 V']['C_70']}/{MI['deep_discharge']['strips 2.30 mm | 1.2 sun 0 C (O-2 window edge) | cell 1 V']['C_70']} C, 2.80 mm {MI['deep_discharge']['strips 2.80 mm | 1.2 sun 0 C (O-2 window edge) | cell 0 V']['C_70']}/{MI['deep_discharge']['strips 2.80 mm | 1.2 sun 0 C (O-2 window edge) | cell 0.5 V']['C_70']}/{MI['deep_discharge']['strips 2.80 mm | 1.2 sun 0 C (O-2 window edge) | cell 1 V']['C_70']} C (1.2 sun, 0 C strings); SPICE 0 V / 1.2 sun / 25 C: 0.72 C. Below 1.0 C (cell maximum); the written deep-discharge limit (RQ-03) is not in hand", 'PARTIAL'),
 ('G4-o2w', 'O-2 comparator window, every tolerance corner', 'no PV current outside 0-45 C, MCU off',
  "SPICE worst corners (600 lx / 0.1 / 1.2 sun): hot stop <= 43.75 C, cold stop >= 0.66 C. Every corner (python, same formulas): inside 0-45 C for V_O2 >= 1.45 V; 1.40 V: hot stop 45.23 C. In SPICE the O-2 decides at V_O2 1.50-1.56 V near its threshold light; the TLV7031 POR level is not published (1.6 V = minimum supply)", 'PARTIAL'),
 ('G4-o2s', 'O-2 supply from the PV node; cell 0 / 0.5 / 1.2 / 2.0 V and PCM tripped; -10 and +50 C; MCU off; 0.1 sun-1.2 sun and 1000 lx', 'no PV current into the cell outside 0-45 C in any battery state, MCU off',
  f"36 cases: Q14 current <= {mx * 1e3:.1f} nA (sub-threshold at VGSth 0.45 V). At 25 C the O-2 approves (e.g. 0.72 C into a 0 V cell)", 'PASS'),
 ('G4-q1', 'no oscillation when Q1 shorts the PV', 'no oscillation',
  f"Q1 static on: 0 O2_OK edges, Q14 {hb['MCU off, 1.2 sun | Q1 static on from 0.5 s']['iq14_max_after_0p6s_uA']} uA; Q1 at 10 Hz: the O-2 follows (2 edges per cycle), no self-oscillation", 'PASS'),
 ('G4-hb', 'heartbeat override (stage 1 D-1)', 'MCU in reset, halted and off at a healthy cell: no PV current',
  f"no heartbeat: 0 A; release after the last pulse {min(rel):.2f}-{max(rel):.2f} s (Q14 VGSth 0.95-0.45 V); first pulse: O2_HB {hb['heartbeat | Q14 Vth 0.45 | Q16 Vth 0.45']['o2hb_first_pulse_peak_V']} V, Q14 VGS only 0.87-1.35 V (C101 inrush), >= 2.3 V from the 2nd pulse; static CHG_DIS high: one hold, off at {hb['static CHG_DIS high from 0.05 s (MCU halted with the pin high)']['on_until_s']:.2f} s", 'PASS'),
 ('G4-q14', 'Q14 at VGSth max (0.95 V) during a cold start, 200-1000 lx, wing lit', 'cold start passes through Q14 where the O-2 approves',
  f"200 lx: 0 (no approval, see G4-a); 500 / 711 / 1000 lx: {cs['Q14 Vth 0.95 | 500 lx | wing 1']['i_avg_uA']:.0f} / {cs['Q14 Vth 0.95 | 711 lx | wing 1']['i_avg_uA']:.0f} / {cs['Q14 Vth 0.95 | 1000 lx | wing 1']['i_avg_uA']:.0f} uA average (VGSth 0.45 V: {cs['Q14 Vth 0.45 | 500 lx | wing 1']['i_avg_uA']:.0f} / {cs['Q14 Vth 0.45 | 711 lx | wing 1']['i_avg_uA']:.0f} / {cs['Q14 Vth 0.45 | 1000 lx | wing 1']['i_avg_uA']:.0f}) >= 21.4 uA; ms relaxation cycles at the POR edge", 'PASS'),
 ('G4-1v6', 'V_O2 down to 1.6 V (stage 1 D-15)', 'window inside 0-45 C down to 1.6 V',
  "1.6 V: cold stop 0.55-4.10 C, hot stop 34.58-44.31 C (re-run of calc). SPICE shows decisions below 1.6 V (1.50-1.56 V): see G4-o2w", 'PARTIAL'),
 ('G4-vbus', 'VBUS present with NTC_EN high (stage 1 D-4)', 'hot stop <= 45 C or the firmware rule',
  f"BQ25170 hot stop {REF['stage1']['D4_hot_stop_with_NTC_EN_high_C']['range'][0]}-{REF['stage1']['D4_hot_stop_with_NTC_EN_high_C']['range'][1]} C in hardware (calc ⚠); met only by the firmware rule (BASELINE 14 item 10); TS window with the O-2 path 0.84-5.19 / 38.56-44.64 C", 'PASS'),
 ('G4-dark', 'O-2 dark load', '<= 2.5 uW',
  "dark: V_O2 0 V, comparators unpowered; battery-side nets only drive gates (Q18 from VBAT_OK, D19B off): model 0 nW + NTC readings 0.023 uW. Gate leakage at 3.3 V is not published ⚠", 'PASS'),
 ('G4-hap', 'haptic droop at VBAT 3.60 V (paths 1.40 / 2.25 / 3.75 ohm), with PV support 0 / 0.1 / 0.45 sun', 'no brown-out at a motor start at VBAT >= 3.60 V (VBAT_OK falling max 3.441 V)',
  f"firmware rule of CALC_V3F 4.3: margin {min(hap_fw):.0f}-{max(hap_fw):.0f} mV, motor >= 2.66 V average (starts ⚠). A plain 30 ms ramp: {min(hap_ramp):.0f} mV at the 0 C path (PV support +9-37 mV)", 'PASS'),
 ('G4-rev', 'reversed head: -5 V and -5.5 V on the contacts (D14)', '-5 V harms nothing',
  f"VBUS >= {MI['reversed_head']['reversed head -5 V (stiff, 0.5 ohm)']['VBUS_min_V'] * 1e3:.0f} mV (U15 IN min -0.3 V); contact current {abs(MI['reversed_head']['reversed head -5 V (stiff, 0.5 ohm)']['contact_current_end_uA']):.2f} uA; D13 does not conduct", 'PASS'),
 ('G4-att', "head attach transient (inrush into C130)", 'not named in this task (head parked, LEAD_NOTES 2g)',
  'band side only: 3.0 A peak from a stiff 0.5 ohm source (the head limits it); no criterion run', 'NOT_RUN'),
 # SIM-05 / V3-G5 (with datasheet bounds; typical in brackets)
 ('G5-T1', 'T1 MON dark, worst stack, night blank / face always on', '>= 14 d on both conventions',
  f"{A}: {eb[A]['T1_worst_stack_d']} / {eb[A]['T1_worst_stack_always_on_face_d']} d; {B}: {eb[B]['T1_worst_stack_d']} / {eb[B]['T1_worst_stack_always_on_face_d']} d (typical stack {eb[A]['T1_dark_d']} / {eb[A]['T1_dark_always_on_face_d']} d)", 'PASS'),
 ('G5-T2', 'T2 ECO dark, conservative / V3 convention', '>= 60 d', f"{eb[A]['T2_ECO_d']:.0f} / {eb[A]['T2_ECO_V3_convention_d']:.0f} d (typ {et[A]['T2_ECO_d']:.0f} / {et[A]['T2_ECO_V3_convention_d']:.0f})", 'PASS'),
 ('G5-T3', 'T3 50 klx MON-neutral', '<= 20 min/day (range reported)',
  f"2.30 / 2.80 mm: {eb[A]['T3_min_day_045sun']} / {eb[B]['T3_min_day_045sun']} min; hot lid {sun[A]['hot lid 35 / 45 C (T3 range)']['T3_min']} / {sun[B]['hot lid 35 / 45 C (T3 range)']['T3_min']}; sleeve (wing 0.25) {sun[A]['sleeve: wing 0.25 x lid']['T3_min']} / {sun[B]['sleeve: wing 0.25 x lid']['T3_min']}; dark wing {sun[A]['dark wing: 0 x lid']['T3_min']} / {sun[B]['dark wing: 0 x lid']['T3_min']}; overcast {eb[A]['T3_overcast_min_day_01sun']:.0f} / {eb[B]['T3_overcast_min_day_01sun']:.0f}", 'PASS'),
 ('G5-T6', 'T6 SHELF (ship mode)', '>= 182.6 d', f"{eb[A]['T6_SHELF_d']:.0f} d ({eb[A]['T6_SHIP_d']:.0f} d); typ {et[A]['T6_SHELF_d']:.0f} ({et[A]['T6_SHIP_d']:.0f}) d", 'PASS'),
 ('G5-T7', 'T7 head charge 0 -> 85 %', '<= 3 h with the cold corner stated',
  f"{min(v for k, v in eb[A]['T7_h'].items() if 'VREG 4.10' in k)}-{max(v for k, v in eb[A]['T7_h'].items() if 'VREG 4.10' in k)} h; VREG -0.8 % {eb[A]['T7_h']['KISET 270, VREG 4.067 V (-0.8 %)']} h; cold corner (5-10 C cell) {eb[A]['T7_h']['KISET 270, VREG -0.8 %, cold 5-10 C cell (ohmic 1.5, RC x2.5)']} h (stated, > 3 h)", 'PASS'),
 ('G5-W', 'W2 / W7 days from full (BASELINE 11.4: 40.6 / 45.4 d)', 'within +-10 %',
  f"2.30 mm {wk(eb[A], 'W2_indoor_300lx')} / {wk(eb[A], 'W7_low_outdoor_office')} d ({(wk(eb[A], 'W2_indoor_300lx') / 40.6 - 1) * 100:+.1f} / {(wk(eb[A], 'W7_low_outdoor_office') / 45.4 - 1) * 100:+.1f} %); 2.80 mm {wk(eb[B], 'W2_indoor_300lx')} / {wk(eb[B], 'W7_low_outdoor_office')} d; typ 2.30 mm {wk(et[A], 'W2_indoor_300lx')} / {wk(et[A], 'W7_low_outdoor_office')} d", 'PASS'),
 ('G5-W17', 'weeks W1-W7 (days from full; + = energy-positive)', 'reported',
  ' '.join(f"{w[:2]} {wk(eb[A], w) if isinstance(wk(eb[A], w), float) else '+'}/{wk(eb[B], w) if isinstance(wk(eb[B], w), float) else '+'}" for w in eb[A]['weeks_from_50pct']), 'PASS'),
 ('G5-sl', 'sleeve (wing 0.25 x lid) and dark wing (0), weeks', 'reported',
  f"sleeve W2/W7 {S5['bounds'][A]['weeks_sleeve_wing_0p25']['W2_indoor_300lx']['days_from_full_if_negative']}/{S5['bounds'][A]['weeks_sleeve_wing_0p25']['W7_low_outdoor_office']['days_from_full_if_negative']} d; dark wing W2/W7 {S5['bounds'][A]['weeks_dark_wing']['W2_indoor_300lx']['days_from_full_if_negative']}/{S5['bounds'][A]['weeks_dark_wing']['W7_low_outdoor_office']['days_from_full_if_negative']} d, W1/W4/W6 turn slightly negative at 2.30 mm ({S5['bounds'][A]['weeks_dark_wing']['W1_office']['days_from_full_if_negative']}/{S5['bounds'][A]['weeks_dark_wing']['W4_sun_20min']['days_from_full_if_negative']}/{S5['bounds'][A]['weeks_dark_wing']['W6_campus']['days_from_full_if_negative']} d), W4 stays positive at 2.80 mm", 'PASS'),
 ('G5-dl', 'office downlights (desk 300 / 1000 lx)', 'reported',
  f"{S5['bounds'][A]['office_downlights']['desk_300lx_uW']} / {S5['bounds'][A]['office_downlights']['desk_1000lx_uW']} uW against 37.8 / 192.8 (2.30 mm); 2.80 mm {S5['bounds'][B]['office_downlights']['desk_300lx_uW']} / {S5['bounds'][B]['office_downlights']['desk_1000lx_uW']}", 'PASS'),
 ('G5-edge', 'edge-dominated shunt (lid Rsh x 0.485 at 2.30 mm, x 0.581 at 2.80 mm; wing x 0.567)', 'reported; W2 / W7 within +-10 %',
  f"300 lx {edge[A]['base']['desk_300lx_uW']} -> {edge[A]['edge-dominated shunt']['desk_300lx_uW']} uW; lap 150 lx {edge[A]['base']['lap_150lx_uW']} -> {edge[A]['edge-dominated shunt']['lap_150lx_uW']}; cold start 200 lx {edge[A]['base']['cold_start_uA_200lx']} -> {edge[A]['edge-dominated shunt']['cold_start_uA_200lx']} uA (< 21.4); W2/W7 {S5['bounds'][A]['weeks_edge_shunt']['W2_indoor_300lx']['days_from_full_if_negative']}/{S5['bounds'][A]['weeks_edge_shunt']['W7_low_outdoor_office']['days_from_full_if_negative']} d (2.80 mm {S5['bounds'][B]['weeks_edge_shunt']['W2_indoor_300lx']['days_from_full_if_negative']}/{S5['bounds'][B]['weeks_edge_shunt']['W7_low_outdoor_office']['days_from_full_if_negative']})", 'PASS'),
 ('G5-log', 'night-light counts replaced by logged wakes', 'when logs exist', 'no logged wakes exist yet', 'NOT_RUN'),
]
tab = ['| # | Case | Criterion (as written) | Result | Status |', '|---|---|---|---|---|'] + [f'| {r[0]} | {r[1]} | {r[2]} | {r[3]} | **{r[4]}** |' for r in ROWS]
md = open(os.path.join(H, 'POWER.md')).read()
a, b = md.index('<!-- TABLE -->'), md.index('<!-- /TABLE -->')
open(os.path.join(H, 'POWER.md'), 'w').write(md[:a] + '<!-- TABLE -->\n' + '\n'.join(tab) + '\n' + md[b:])
OUT = dict(meta=dict(date='2026-11-15', variant='v3f', gates=['V3-G4 (SIM-03)', 'V3-G5 (SIM-05)'], markers='every value is a model result (E) unless a datasheet line is quoted',
                     tools='ngspice (KiCad libngspice) testbenches sim03/o2_tb.py, sim03/sim03_misc.py; project energy model v3_energy via sim05/baseline_calc_v3f.py'),
           table=[dict(id=r[0], case=r[1], criterion=r[2], result=r[3], status=r[4]) for r in ROWS],
           counts={s: sum(r[4] == s for r in ROWS) for s in ('PASS', 'PARTIAL', 'FAIL', 'NOT_RUN')},
           sim05=dict(bounds={c: {k: v for k, v in S5['bounds'][c].items()} for c in (A, B)}, typ={c: S5['typ'][c]['energy'] for c in (A, B)}),
           sim03=dict(o2=O2, misc=MI, o2_calc_stage1=REF.get('stage1')))
json.dump(OUT, open(os.path.join(H, 'power_results.json'), 'w'), indent=1, ensure_ascii=False, default=float)
print(OUT['counts']); print('\n'.join(tab))
