# POWER — V3-F（v3f 网表）SIM-03（V3-G4）与 SIM-05（V3-G5），2026-11-15

## 中文摘要
- 工具：ngspice（KiCad libngspice）搭建 O-2 实际电路（16 件）+ PV 前端 + BQ25570 输入行为模型的测试台；项目自身能量模型 v3_energy（SIM-05 口径）。所有数值为模型结果 ⚠。
- SIM-05 全部通过：最终负载（含数据手册上限项）下 T1 最坏堆叠 21.9 / 18.4 d，T2 98 d，T3 11.6 min（41×34 盖 10.9 min），T6 259 d，T7 1.98–2.34 h（冷角 3.15 h 已注明），W2 / W7 39.9 / 44.2 d（−1.7 / −2.6 %）。
- 41×34 盖（条宽 2.80 mm，硅 +21.6 %）：T3 −0.7 min，W2 +0.4 d，W7 +1.0 d；暗翼 T3 25.4 → 20.9 min；PV 充电上限 −20 °C 0.408 C（仍 ≤ 0.5 C）。
- O-2：窗外（−10 / +50 °C）在 0–2.0 V 电芯、PCM 跳闸、0.1–1.2 sun 共 36 种情况下 Q14 电流 ≤ 3.8 nA；Q1 短路不振荡；心跳停止后 0.87–1.57 s 释放；Q8 插入后 0.29 ms 切断。
- FAIL 1：Q8 单点开路且 MCU 未运行（电芯 3.0–3.40 V）时，O-2 放行 PV，PV + USB = 0.71–0.83 C（> 0.5 C）。最小改动：Q8 并联第二只 PMZ290UNE2（栅极 VB_DET）。
- FAIL 2：离腕死机冷启动，200 lx 在任何翼光比下都为 0 µA（O-2 供电低于比较器 POR）；需 350–800 lx（POR 1.6 V 时 460–1080 lx）。不加 O-2 时为 155–358 lx。最小改动：更新 BASELINE §11.5 的残余说明（或评估 0.9 V 起工作的 TLV3691，需重算窗口）。
- PARTIAL：O-2 在门槛光照下以 1.50–1.56 V 判决（低于 TLV7031 规定的 1.6 V），V_O2 1.40 V 时热停 45.23 °C。最小改动：R172 52.3 k → 53.6 k（低至 1.30 V 仍 ≤ 45.0 °C，标称热停 38.4 → 37.8 °C）。
- PARTIAL：VBAT_OK 回差 91 mV，在 1.2 sun、0 °C 电芯时会被 98–101 mV 的阶跃越过（固件未及时心跳时可能抖动）。最小改动：R105 294 k → 383 k（上升 3.430 V，回差 118 mV）。
- PARTIAL：深放电 0 V 电芯 0.84–0.89 C（< 1.0 C 最大值，但电芯厂书面限值 RQ-03 未到）。NOT_RUN：头部接入浪涌（头部已搁置）、记录唤醒次数（无日志）。

## Method (short)
- **O-2 testbench** `sim03/o2_tb.py`: the as-built netlist of `src/o2.py` (SB_O2=std) and the PV front end of `src/power.py`. Parts: R111, Q1/R108, Q8 with R144/R145, Q14/R174/C174, R130 12 Ω, C101, Q18, D19, C170, R116, R170–R172, U19/U20, Q16/C175/R176, Q17/R175, NTC 10 k B 3950.
  - PV node I–V: lid + wing from `v3_energy` (strips 2.30 or 2.80 mm, wing ratio and string temperature per case).
  - MOSFETs: EKV-type, VGSth at 250 µA = 0.45 / 0.70 / 0.95 V, 90 mV/decade, RDS(on) from PMZ350UPE / PMZ290UNE2 p.6.
  - TLV7031: VOS ±8 mV and hysteresis 2–17 mV (SLVSE13J p.8). The POR level is not published; it is taken as 1.50 V ⚠, with a 1.60 V sensitivity.
  - BQ25570 input: cold-start clamp at 0.6 V, MPPT at 0.8 Voc, or the three-diode deep-discharge path.
- **Cases** `sim03/o2_cases.py`:
  - window: temperature ramps at the worst corners;
  - matrix: 36 out-of-window cases;
  - dyn: heartbeat, probe, Q1, Q8, dark;
  - coldstart: bisection on light per wing ratio.
- **Other cases** `sim03/sim03_misc.py`:
  - ngspice: EN/wake, haptic (averaged PWM + motor model), reversed head;
  - `v3_energy` (Python): R_LIM bound, deep discharge, Q8 fault, chatter step ⚠.
- **SIM-05** `sim05/run_sim05.py` on the copy `sim05/baseline_calc_v3f.py`. `SIM05_MODE=baseline` reproduces BASELINE §11 exactly.
  - Final v3f loads (`design/calc/v3f_calc.json → standby`): the O-2 is no battery load; computed items included.
  - Mode `bounds` adds the datasheet-maximum items: U21 9.25 µW face on, /PG 2.19 µW, Q12 3.7 µW in ship mode. The table uses `bounds`; `typ` is in the JSON.
- The 41 × 34 column is the 41 × 34 lid with four 27.7 × 2.80 mm strips (311 mm²; `g1/cad/CAD_OPTIONS.md`). Same loads.

## Results
Strip widths: 2.30 mm = 41 × 32 lid; 2.80 mm = 41 × 34 lid. SIM-05 rows use the loads with the datasheet bounds.

<!-- TABLE -->
| # | Case | Criterion (as written) | Result | Status |
|---|---|---|---|---|
| G4-a | cold start, dead band off the wrist, wing 1/0.5/0.25/0.1/0 x lid, through the O-2 (MCU off) | BASELINE 11.5: >= 21.4 uA at 200 lx; "off the wrist about 360 lx or the head" | 200 lx: 0 uA at every ratio (V_O2 below the comparator POR). Light for 21.4 uA (2.30 / 2.80 mm): wing 1: 350/330; wing 0.5: 480/450; wing 0.25: 600/540; wing 0.1: 710/620; wing 0: 800/690 lx (POR 1.50 V); POR 1.60 V: 460 / 1080 lx (wing 1 / 0). Without the O-2: 155-358 lx | **FAIL** |
| G4-c | VBAT_OK chatter | no VBAT_OK chatter (SIM-03c) | hysteresis 91 mV against the VSTOR step when PV charge stops: 45-101 mV; >= 91 mV only at 1.2 sun with a 0 C cell (5.25 ohm path), and only if the heartbeat is not running within the C174 hold after VBAT_OK rises ⚠ | **PARTIAL** |
| G4-e | PV_INH probe (MCU on, heartbeat, 1 sun) | probe as V3 4.3: INA_PV = Isc, no PV current to the cell, MPPT back | INA_PV/Isc 1.0; PV_SW 26 mV; Q14 <= 15 uA (C101 back-flow); back to 90 % in 30 ms (next heartbeat) | **PASS** |
| G4-g | EN, ship mode, wake pair (D12: VBUS and button) | ship wake by the button and the head | head 5.0 / 4.75 V: EN_HOLD 1.0 V after 1.71 / 1.89 s; button 0.30 s press at VBAT 4.1-2.8 V: 0.16-0.293 s; light wake 200 lx 13.9 s; D12 unbiased in ship mode | **PASS** |
| G4-q8 | Q8 interlock at plug-in, 1.2 sun | PV and USB never at once (BASELINE 11.5, 13.3) | Q14 current < 1 % 0.29 ms after VBUS (MCU on and off); Q8 carries the 59 mA PV short | **PASS** |
| G4-q8f | Q8 single fault | no state above 0.5 C for a cell above the protector trip | Q8 short: PV always shorted (no harvest, safe). Q8 open, MCU on: Q1 backup in 5 ms. Q8 open, MCU off (cell 3.0-3.40 V, VBAT_OK low): the O-2 approves and the PV (16.8-21.8 mA) adds to USB 32.7 mA = 0.71-0.78 C (70 mAh), up to 0.83 C (66 mAh), until VBAT_OK rises | **FAIL** |
| G4-rlim | R_LIM 12 ohm + Q14 bound, 1.2 sun, strings -10 / -20 C, k 0.72, cell 3.0 V | <= 0.5 C | 2.30 mm 0.377/0.394 C; 2.80 mm 0.389/0.408 C (66 mAh: 0.433); MCU off the O-2 blocks < 0 C anyway | **PASS** |
| G4-dd | deep-discharge currents (three-diode path), inside the O-2 window | within the cell maker's written limit | cell 0 / 0.5 / 1.0 V: 2.30 mm 0.84/0.58/0.22 C, 2.80 mm 0.89/0.6/0.23 C (1.2 sun, 0 C strings); SPICE 0 V / 1.2 sun / 25 C: 0.72 C. Below 1.0 C (cell maximum); the written deep-discharge limit (RQ-03) is not in hand | **PARTIAL** |
| G4-o2w | O-2 comparator window, every tolerance corner | no PV current outside 0-45 C, MCU off | SPICE worst corners (600 lx / 0.1 / 1.2 sun): hot stop <= 43.75 C, cold stop >= 0.66 C. Every corner (python, same formulas): inside 0-45 C for V_O2 >= 1.45 V; 1.40 V: hot stop 45.23 C. In SPICE the O-2 decides at V_O2 1.50-1.56 V near its threshold light; the TLV7031 POR level is not published (1.6 V = minimum supply) | **PARTIAL** |
| G4-o2s | O-2 supply from the PV node; cell 0 / 0.5 / 1.2 / 2.0 V and PCM tripped; -10 and +50 C; MCU off; 0.1 sun-1.2 sun and 1000 lx | no PV current into the cell outside 0-45 C in any battery state, MCU off | 36 cases: Q14 current <= 3.8 nA (sub-threshold at VGSth 0.45 V). At 25 C the O-2 approves (e.g. 0.72 C into a 0 V cell) | **PASS** |
| G4-q1 | no oscillation when Q1 shorts the PV | no oscillation | Q1 static on: 0 O2_OK edges, Q14 -0.061 uA; Q1 at 10 Hz: the O-2 follows (2 edges per cycle), no self-oscillation | **PASS** |
| G4-hb | heartbeat override (stage 1 D-1) | MCU in reset, halted and off at a healthy cell: no PV current | no heartbeat: 0 A; release after the last pulse 0.87-1.57 s (Q14 VGSth 0.95-0.45 V); first pulse: O2_HB 1.464 V, Q14 VGS only 0.87-1.35 V (C101 inrush), >= 2.3 V from the 2nd pulse; static CHG_DIS high: one hold, off at 1.62 s | **PASS** |
| G4-q14 | Q14 at VGSth max (0.95 V) during a cold start, 200-1000 lx, wing lit | cold start passes through Q14 where the O-2 approves | 200 lx: 0 (no approval, see G4-a); 500 / 711 / 1000 lx: 56 / 95 / 147 uA average (VGSth 0.45 V: 75 / 115 / 168) >= 21.4 uA; ms relaxation cycles at the POR edge | **PASS** |
| G4-1v6 | V_O2 down to 1.6 V (stage 1 D-15) | window inside 0-45 C down to 1.6 V | 1.6 V: cold stop 0.55-4.10 C, hot stop 34.58-44.31 C (re-run of calc). SPICE shows decisions below 1.6 V (1.50-1.56 V): see G4-o2w | **PARTIAL** |
| G4-vbus | VBUS present with NTC_EN high (stage 1 D-4) | hot stop <= 45 C or the firmware rule | BQ25170 hot stop 46.34-53.58 C in hardware (calc ⚠); met only by the firmware rule (BASELINE 14 item 10); TS window with the O-2 path 0.84-5.19 / 38.56-44.64 C | **PASS** |
| G4-dark | O-2 dark load | <= 2.5 uW | dark: V_O2 0 V, comparators unpowered; battery-side nets only drive gates (Q18 from VBAT_OK, D19B off): model 0 nW + NTC readings 0.023 uW. Gate leakage at 3.3 V is not published ⚠ | **PASS** |
| G4-hap | haptic droop at VBAT 3.60 V (paths 1.40 / 2.25 / 3.75 ohm), with PV support 0 / 0.1 / 0.45 sun | no brown-out at a motor start at VBAT >= 3.60 V (VBAT_OK falling max 3.441 V) | firmware rule of CALC_V3F 4.3: margin 66-89 mV, motor >= 2.66 V average (starts ⚠). A plain 30 ms ramp: -64 mV at the 0 C path (PV support +9-37 mV) | **PASS** |
| G4-rev | reversed head: -5 V and -5.5 V on the contacts (D14) | -5 V harms nothing | VBUS >= -6 mV (U15 IN min -0.3 V); contact current 0.34 uA; D13 does not conduct | **PASS** |
| G4-att | head attach transient (inrush into C130) | not named in this task (head parked, LEAD_NOTES 2g) | band side only: 3.0 A peak from a stiff 0.5 ohm source (the head limits it); no criterion run | **NOT_RUN** |
| G5-T1 | T1 MON dark, worst stack, night blank / face always on | >= 14 d on both conventions | 41x32 strips 2.30 mm: 21.9 / 18.4 d; 41x34 strips 2.80 mm: 21.9 / 18.4 d (typical stack 38.5 / 33.2 d) | **PASS** |
| G5-T2 | T2 ECO dark, conservative / V3 convention | >= 60 d | 98 / 119 d (typ 100 / 122) | **PASS** |
| G5-T3 | T3 50 klx MON-neutral | <= 20 min/day (range reported) | 2.30 / 2.80 mm: 11.6 / 10.9 min; hot lid [11.4, 11.9] / [10.8, 11.3]; sleeve (wing 0.25) 18.9 / 16.5; dark wing 25.4 / 20.9; overcast 49 / 45 | **PASS** |
| G5-T6 | T6 SHELF (ship mode) | >= 182.6 d | 259 d (353 d); typ 276 (411) d | **PASS** |
| G5-T7 | T7 head charge 0 -> 85 % | <= 3 h with the cold corner stated | 1.98-2.34 h; VREG -0.8 % 2.71 h; cold corner (5-10 C cell) 3.15 h (stated, > 3 h) | **PASS** |
| G5-W | W2 / W7 days from full (BASELINE 11.4: 40.6 / 45.4 d) | within +-10 % | 2.30 mm 39.9 / 44.2 d (-1.7 / -2.6 %); 2.80 mm 40.3 / 45.2 d; typ 2.30 mm 41.1 / 45.9 d | **PASS** |
| G5-W17 | weeks W1-W7 (days from full; + = energy-positive) | reported | W1 +/+ W2 39.9/40.3 W3 55.6/58.6 W4 +/+ W5 40.1/40.1 W6 +/+ W7 44.2/45.2 | **PASS** |
| G5-sl | sleeve (wing 0.25 x lid) and dark wing (0), weeks | reported | sleeve W2/W7 38.4/39.9 d; dark wing W2/W7 37.9/38.7 d, W1/W4/W6 turn slightly negative at 2.30 mm (645.4/452.1/190.3 d), W4 stays positive at 2.80 mm | **PASS** |
| G5-dl | office downlights (desk 300 / 1000 lx) | reported | 33.7 / 176.6 uW against 37.8 / 192.8 (2.30 mm); 2.80 mm 38.0 / 197.0 | **PASS** |
| G5-edge | edge-dominated shunt (lid Rsh x 0.485 at 2.30 mm, x 0.581 at 2.80 mm; wing x 0.567) | reported; W2 / W7 within +-10 % | 300 lx 37.8 -> 24.8 uW; lap 150 lx 10.7 -> 3.9; cold start 200 lx 26.9 -> 21.1 uA (< 21.4); W2/W7 39.0/42.8 d (2.80 mm 39.4/43.8) | **PASS** |
| G5-log | night-light counts replaced by logged wakes | when logs exist | no logged wakes exist yet | **NOT_RUN** |
<!-- /TABLE -->

## Smallest fixes (not applied; design files untouched)
| # | Change | Effect (model ⚠) |
|---|---|---|
| G4-q8f | Second PMZ290UNE2 in parallel with Q8: drain PV_SW, gate VB_DET, source GND. One SOT883 part. | One open FET no longer defeats the PV short while VBUS is present: back to ≤ 0.47 C (USB alone). |
| G4-o2w, G4-1v6 | R172 52.3 k → 53.6 k (E96, 0201). | Hot stop ≤ 45.0 °C at every corner down to V_O2 1.30 V (as built: 1.45 V). Nominal 38.4 → 37.8 °C; cold stop ≥ 0.19 °C. Also ask TI for the TLV7031 POR level. |
| G4-c | R105 (ROK3) 294 k → 383 k. | VBAT_OK rising 3.403 → 3.430 V; hysteresis 118 mV, above the 101 mV worst step; a flat band boots 27 mV later. |
| G4-a | No part change proposed. Correct BASELINE §11.5: a dead band off the wrist needs 0.35–0.8 klx through the O-2 (0.46–1.1 klx if POR = 1.6 V), or the head. | — |
| G4-dd | Pack RFQ answer RQ-03 (the maker's limit for recharging a deep-discharged cell). | Needed only if that limit is < 0.9 C. |

## Notes
- **O-2 relaxation.** Near its approval light the O-2 relaxes on its own on a ms scale. V_O2 collapses after approval, U19/U20 go to POR, and C174 does not hold, because Q17 discharges it to the clamped PV_SW. The O-2 then re-approves. The average cold-start current is still 56–147 µA at 500–1000 lx with Q14 at VGSth max. This is not the Q1 case, which shows no oscillation.
- **First heartbeat pulse.** Its VGS is only 0.87–1.35 V, because the C101 inrush pulls PV_SW down. Harvest is full from the second pulse, 100 ms later.
- **Reversed head.** It is harmless. The correct +5 V attach into C130 from a stiff source peaks at 3.0 A; the head's current limit governs this, and it is not assessed here.

## Files
- `v3/sim/power/POWER.md`, `power_results.json` (table + all case data), `make_power.py`, `PROGRESS.md`
- SIM-03: `sim03/o2_tb.py`, `o2_cases.py`, `o2_vpor16.py`, `sim03_misc.py`, `o2_{window,matrix,dyn,coldstart,vpor16}.json`, `misc_results.json`, `o2_inhibit_ref.py` → `o2_inhibit.json` (stage-1 calc re-run)
- SIM-05: `sim05/run_sim05.py`, `baseline_calc_v3f.py`, `v3_calc_copy.py`, `sim05_{typ,bounds}.json`, `pv_tables_R12_w*.json`
- Logs: `logs/`
