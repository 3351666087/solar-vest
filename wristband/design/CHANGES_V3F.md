# CHANGES_V3F - V2-B `dock_wlcsp` → V3-F main board (lane V3-F MAIN-BOARD SCHEMATIC)

2026-11-13. This folder is a copy of `../../v2/design`; the V2-B documents and calc scripts are frozen in `v2_ref/`.

The schematic follows `../decide/BASELINE.md`: §3 block diagram, §4 power tree, §5 parts, §6 GPIO, §13.3 interlocks, §14 firmware hooks and §16 placement safety.

Nothing was bought, quoted, uploaded or sent. No account was used.

Downloads (datasheets, raw EasyEDA / JLC answers) stay outside the project. Only extracted facts and my own reviewed footprints are kept here.

- Numbers: `CALC_V3F.md`.
- The complete mechanical change list (refs and nets): `diff_v2.md`.
- How to continue: `PROGRESS.md`.

## 0. 中文摘要

### 已完成

- 已按 BASELINE §5.1 把 V2-B `dock_wlcsp` 改成 V3-F 主板。
- 做了两个变体：`v3f`（基线）和 `v3f_fldnp`（前光不贴，研究版；同一块 PCB）。
- 每个变体都跑完了全流程：
  - KiCad ERC 0 个错误（4 个警告都已说明）。
  - 原理图网表和 SKiDL 网表交叉核对：0 处差异。
  - 已生成 PDF、BOM（含 LCSC 号和今天的 JLC 库存）、BOM_full、parts.json（courtyard 和最大高度）。
  - 45 个引脚表，逐焊盘复核过的封装。
  - 封装审核：65 PASS / 22 PASS-NOTE / 1 FLAG。这个 FLAG 是 BAT54CM 的原始 EasyEDA 焊盘，复核版里已改正。
  - 贴片方向证明表、引脚预算、网络类别。

### 主要结论

1. **O-2 硬件温控断充：** 设计和计算都完成。
   - 断开方式：PV 串联 PMOS，默认断开。
   - 判定：在 PV 开路电压下判定，所以与电芯状态无关。
   - 结果：MCU 关机、电芯 0/0.5/1.2/2.0 V、保护板跳开时都满足 0–45 °C；黑暗负载 0 µW；不会振荡。
   - 代价一：占 20.6 mm²，超出 12 mm² 预留。
   - 代价二：MCU 关机时，约 711 lx 以上才放行充电。
   - 更好的路线仍是在电池包保护板里做断充（BASELINE 储备 3）。
2. **马达供电改到 VBAT_IC：** 启动电流不经过 BQ25570 的 PFET，25 °C 时 3.60 V 启动不掉电。0 °C 时需要靠 INA_BAT 限流软启动（≤ 42 mA）。
3. **DISP 改用 TXU0101，接 P0.18：** BASELINE 原来用 RC 驱动，不满足屏的边沿、掉电顺序和电平要求。代价是调试 UART 没了。
4. **反接保护：** 加 D14 肖特基，−5 V 无害。代价是充电头在触点处需要 ≥ 4.85 V。
5. **面积：** 按实际元件算，37×29 为 0.613（项目口径）/ 0.678（v1 口径），38×29 为 0.592 / 0.656。v1 口径两种尺寸都不通过，比 BASELINE 计划多 35 mm²。
   - 41 mm 壳体必须同时拿掉 LED 链并把 O-2 移到电池包，才能通过（0.551 / 0.610）。
   - 否则主板要加长到 39.7 mm。
6. **BQ25170：** JLC 今天可订数量为 0（库存 152），需要锁货或自供。

## 1. Result

| Variant | Parts / JLC-placed | Named nets | ERC | Netlist cross-check | Note |
|---|---|---|---|---|---|
| `v3f` (baseline: front light fitted) | 230 / 194 | 141 | 0 errors, 4 warnings | 0 differences (141 nets) | `SB_FL=fit` |
| `v3f_fldnp` (front light DNP: Q11, R160, R161) | 230 / 191 | 141 | 0 errors, 4 warnings | 0 differences | same PCB |

ERC warnings, all "bidirectional to power output", checked:

| Warning | Origin | Status |
|---|---|---|
| U7 pins 31 and 32 (IN3P/N) on AVDD | V2 | intended |
| U9 SA0 on VDD_1V8 | V2 | intended |
| U6 P0.19 (DISP_EN) on its PWR_FLAG | new | intended: the GPIO is the rail of U17 / U21 VCCA (≤ 3 µA), CALC_V3F §6 |

Flow: `tools/run_all.sh` (both variants).
- Per variant: `out/<v>/`, `kicad/<v>/`, `erc/`, `pdf/`, `netlist/`, `BOM_<v>.csv`, `BOM_full_<v>.csv`.
- Shared outputs: `parts.json`, `stock_report.md`, `pin_budget.md`, `netclasses.json`, `footprint_audit.md`, `placement_proof.md` / `.json`, `area_check.md` / `.json`, `diff_v2.md` / `.json`.
- JLC stock was queried 2026-11-13 21:18–21:38 UTC, 89 C-numbers, all found, none rate-limited.

## 2. Changes, one row each

Abbreviations: B = BASELINE section, D = datasheet (pages in CALC_V3F and `tools/pinmap_data_v3.py`). "Re-run" names the SIM or gate that has to repeat (BASELINE §18).

| # | Change | Source | What it invalidates | Re-run |
|---|---|---|---|---|
| 1 | U14 / R132 / C123 (protector) removed: the cell, PCM and F1 are in the pack | B 5.1, 5.2 | V2 protector analysis on the board | V3-G6 root short |
| 2 | Entry lands: root A J3 BATT_P_A, J4 GND_A1, J5 NTC_A, J10 GND_A2; root B J7 PV_W, J9 GND_B. Each 1.0 × 4.0 mm at 1.5 mm pitch (span 5.5 mm inside X 4.5–10.5). **Not 6 mm² per pad**: 1.5 mm wide pads would need 7.5 mm | B 1, 4, 5.1 | fixed area 40.5 instead of 36.0 mm² | V3-G1 |
| 3 | FB1–FB6: one 0 Ω 0402 (C17168) per strap conductor, GND included | B 4, 13.1 | – | V3-G3a |
| 4 | R130 12 Ω 1 % 1206 250 mW (C17913), now in series with Q14 | B 5.1, 11.5 | V2 R_LIM tables | V3-G4 |
| 5 | R131, R108 → 10 MΩ (C144806) | B 5.1 | – | – |
| 6 | Generic passives → 0201 (V2 p0201 set except R108 / R131) | B 5.1 | – | – |
| 7 | BQ25170 block U15, fed from two top-rim spring fingers J15 (VBUS_K) and J18 (GND, BW0036BG C2826535):<br>• D13 ESD761 at the land; **D14 NSR0240 reverse-blocking Schottky** (new)<br>• C130 / C131 1 µF<br>• R140 RISET 10 k (C25744); R141 2 k + C132 4.7 nF ISET RC; R142 36 k (VSET 4.10 V); R143 220 k /PG pull-up to VDD_1V8 (P0.20)<br>• R144 / R145 VB_DET divider; Q8 (PV short), Q9 (AVDD_EN low), Q10 (CHG_DIS pulls TS low, R146) | B 4, 5.1; D SLUSDJ8A, SLUAAG9 | head requirement ≥ 4.85 V at the contacts (CALC 1.2) | V3-G4 (attach transient, −5 V), V3-G6 ESD, V3-G10 |
| 8 | **R123 220 k** between ECG_PWR_EN (P0.22) and AVDD_EN (U3 EN), so Q9 can hold AVDD off while VBUS is present without shorting a GPIO (new part) | B 13.3 ECG interlock | V2 U3 EN wiring | V3-G6 interlock |
| 9 | **D12 BAV70M** (C549313): half A VBUS wake, half B button wake into EN_HOLD. EasyEDA has no record: land derived from the reviewed SOT883 set | B 5.1, 13.3 | V2 EN analysis gains two inputs | V3-G4 (g) |
| 10 | Display:<br>• U16 TPS7A0230 3.0 V (EN = DISP_EN) and U17 TXU0104 (VCCA = OE = DISP_EN)<br>• **U21 TXU0101** for DISP on **P0.18 DISP_CTRL** (was UART_TX), with C1603<br>• the display lane's RC delay C1504 / R1501 is not used<br>• J13 keyed FPC land (10 pads + key) | B 5.1, 6; D LD-29Y03 p.17, 21, 22; SCES937B / SCES940A | debug UART removed (logs over SWD / RTT) | V3-G6 (VDD_DISP, panel COM), G10 (g) |
| 11 | Front light: R160 **100 Ω 0201** (C270366), Q11 (FL_EN P0.10), R161, tail J16. DNP in `v3f_fldnp` | B 5.1, 11.1 | – | V3-G1 values done |
| 12 | ERM:<br>• **supply VBAT_IC** (not VSTOR), J17 + = VBAT_IC<br>• Q12 low side (MOTOR_PWM P0.04), R162 **1 kΩ 0201** (C270365), R163 1 M<br>• flyback D17 BAT54CM (both halves) to VBAT_IC<br>• motor off-board on J17 in the 8.6 mm cut-out | B 4, 5.1, 14 item 6 | B 4 tree; ship-mode leakage path (CALC 9) | V3-G4 haptic droop, V3-G7 |
| 13 | Sealed side button SW1 C&K PTS840GK (C221907): drawing read, **side actuated ✅**, 1.35 mm tall.<br>• R165 **100 k 0201** (C270364) from VBAT_IC<br>• R167 1 M<br>• **Q13 level shifter** to BTN_N (P0.26, R164 1 M pull-up to VDD_1V8) | B 5.1, 14 item 5; D PTS840 B-40–B-42 | area (+12.6 mm²), height budget at the hand-end edge | V3-G1, V3-G9, V3-G4 (g) |
| 14 | **O-2 inhibit** (14 parts):<br>• Q14 series PMOS with R174 / C174<br>• Q16 (VBAT_OK override), Q17 (approval), R175<br>• Q18 + D19 (supply from PV_SW only with VBAT_OK low; NTC_EN path), C170<br>• ladder R116 100 k (moved from the V2 NTC bias) + chain R170 732 k / R171 162 k / R172 52.3 k<br>• U19 / U20 TLV7031 chained AND<br>The MCU AIN path is R149 **1 MΩ** (not 100 k) with C113 at the pin | B 4, 13.2, 18 V3-G4; D SLVSE13J, PMZ350UPE, BAT54CM | B 4 "OR into Q1"; TS window and MCU reading recomputed (CALC 1.3, 3); area 20.6 mm² | V3-G4 O-2 SIM |
| 15 | D10 skin-hot LED chain kept | B 5.1 | – | – |
| 16 | GPIO:<br>• P0.04 MOTOR_PWM, P0.09 CHG_DIS, P0.10 FL_EN, P0.17 EXTCOMIN<br>• **P0.18 DISP_CTRL**<br>• P0.19 DISP_EN, P0.20 CHG_PG_N, P0.26 BTN_N, P0.29 DISP_SCS<br>• U9 INT2 not connected<br>No spare pin | B 6 | J8 / J12 pad 6 now DISP_CTRL | firmware lane |
| 17 | Netclasses and rule areas:<br>• new: ROOT_A_ENTRY, ROOT_B_ENTRY, CONTACTS, LOW_PART_ZONE, MOTOR_CUTOUT, BUTTON, RLIM_1206, MOHM_KEEPOUT (O-2 nodes), DISPLAY<br>• fixed features: 6 rib post feet, 8.6 mm cut-out | B 1, 5.1, 7, 13 | – | V3-G1 |

## 3. New parts

Stock is from the JLC parts API, 2026-11-13 21:18–21:38 UTC. Orderable = min(stock, canPresale). Footprint: "audit" = `footprint_audit.md`, checked pad by pad.

| Ref | Role | MPN | LCSC | Stock / orderable | Class | Footprint |
|---|---|---|---|---|---|---|
| U15 | linear charger 30 mA | BQ25170DSGR | C5208201 | 152 / **0** | 2F | PASS |
| U16 | 3.0 V panel LDO | TPS7A0230PDQNR | C2867950 | 419 / 393 | 2F | PASS |
| U17 | 4-bit translator | TXU0104RUTR | C5187176 | 2,708 / 2,555 | 2F | PASS-NOTE |
| U21 | DISP translator | TXU0101DRYR | C5217869 | 672 / 645 | 2F (near-symmetric land: pad 1 only 0.05 mm longer) | PASS |
| U19, U20 | O-2 comparators | TLV7031DPWR | C2876045 | 3,923 / 3,740 | 2F | PASS-NOTE (EasyEDA pad numbers differ from TI's, mapped by position) |
| Q14, Q18 | O-2 series switch / supply gate | PMZ350UPEYL | C478207 | 21,177 / 21,124 | 1F | PASS-NOTE |
| Q8–Q13, Q16, Q17 | NMOS switches | PMZ290UNE2YL | C478155 | 1,271 / 714 (13 per board: 54 boards) | 1F | PASS-NOTE |
| D12 | wake pair | BAV70M,315 | C549313 | 1,481 / 1,481 | 1F | PASS-NOTE (derived land; JLC 0° unknown → preview) |
| D17, D19 | flyback / O-2 OR | BAT54CM,315 | C549275 | 7,036 / 7,018 | 1F | FLAG in the raw EasyEDA land; **fixed** in the reviewed copy (C478155 SOT883 pad set) |
| D13 | contact ESD | ESD761DPYR | C20345399 | 24,306 / 23,924 | N | PASS-NOTE |
| D14 | reverse block | NSR0240MX2T5G | C896422 | 604 / 604 | P | PASS-NOTE |
| SW1 | side button | PTS840GKSMTRLFS | C221907 | 9,807 / 9,783 | M | PASS-NOTE |
| J15, J18 | contact fingers | BW0036BG-L3.0W1.0H1.4 | C2826535 | 6,372 / 6,363 | M | PASS-NOTE |
| R130 | R_LIM 12 Ω 1206 | 1206W4F120JT5E | C17913 | 99,038 / 57,577 | – | PASS |
| R160 | front-light R | 0201WMF1000TEE | C270366 | 579,767 / 485,571 | – | PASS |
| R162 | gate R | 0201WMF1001TEE | C270365 | 1,938,880 / 1,479,899 | – | PASS |
| R170 / R171 / R172 | O-2 chain | 0201WMF7323TEE / 1623TEE / 5232TEE | C423439 / C2691509 / C473632 | 12,195 / 14,900 / 17,919 orderable | – | PASS |
| R174 | Q14 gate hold | AC0402FR-0710ML | C144806 | 255,821 / 249,319 | – | PASS |
| FB1–FB6 | strap links | 0402WGF0000TCE | C17168 | 15.8 M | – | PASS |

Copper-only footprints were drawn for J3–J5, J7, J9, J10 (root lands), J13 (FPC land), J16 and J17. They are not JLC-placed.

Other new passives are standard C-numbers already in the V2 library (C52923, C7393837, C295786, C270364, C25744, C4109, C1538, C43676, C25767).

## 4. Where this lane deviates from BASELINE or adds to it

| BASELINE | As built | Why |
|---|---|---|
| §4 / §5.1: O-2 = U18 + ladder "OR into the Q1 gate", 12 mm² reserve | series PMOS, default OFF, VBAT_OK override; 14 parts, 20.6 mm² | an OR into Q1 collapses the O-2 supply and oscillates; default-on leaves deep-discharge windows open (CALC 3.1) |
| §14 item 8: "Room light only restarts it" | with the MCU off a flat band restarts only above about 711 lx | O-2 approval needs V_O2 ≥ 1.65 V; manual text to be rewritten |
| §4: ERM on VSTOR | on VBAT_IC | start droop: VSTOR misses VBAT_OK falling by up to 191 mV at 0 °C on VSTOR (CALC 4) |
| §5.1: DISP from the rail through an RC (C1504, R1501) | U21 TXU0101 on P0.18 | panel edge, power-off order, VIH ≤ VDD (LD-29Y03); debug UART_TX removed |
| §4: "a reverse-blocking element if needed" | D14 NSR0240 fitted | −5 V attach (V3-G4 criterion); cost 0.44 V |
| §5.1: R149 100 k AIN protection | 1 MΩ (C295786), C113 at the pin | the O-2 runs with the MCU unpowered: limits AIN clamp current to ≤ 0.2 µA |
| §4: "level-safe path with R164" | Q13 + R167; R164 = BTN_N pull-up | VBAT never reaches a pin; no back-feed in ship mode |
| §5.1: R160 / R162 / R165 values to V3-G1 | 100 Ω / 1 kΩ / 100 kΩ | CALC 4, 5, 7 |
| §5.1: 6 mm² per root land | 1.0 × 4.0 mm (4 mm² copper, 6.75 mm² courtyard) | four lands in X 4.5–10.5 at ≥ 0.5 mm gaps |
| §5.1: SW1 17.0 mm², 1.05 mm (assumed) | 29.6 mm² (EasyEDA land), 1.35 mm (C&K B-41) | drawing read; side actuated ✅ |
| (none) | R123 220 k | Q9 interlock without a GPIO short |
| §5.1: J15 "2 spring fingers" | J15 (VBUS_K) + J18 (GND) | one ref per finger for the CPL |
| §5.3: 0.565 / 0.626 (37 mm), 0.546 / 0.605 (41 mm) | 0.613 / 0.678 and 0.592 / 0.656 | +35.0 mm² courtyard, +5.7 mm² fixed (CALC 10) |

## 5. Pass criteria (lane level; BASELINE §18 rows as written; nothing relaxed)

| Criterion | Result | Status |
|---|---|---|
| Every BASELINE §5.1 change applied | all applied; deviations listed in §4 | PASS |
| Variants via `src/common.py` (baseline + front-light DNP) | v3f, v3f_fldnp | PASS |
| ERC 0 errors per variant | 0 / 0 (4 explained warnings) | PASS |
| Schematic netlist = SKiDL netlist | 0 differences, both variants | PASS |
| BOM with LCSC + today's stock, BOM_full, parts.json with courtyards and heights | done; 3 lines flagged in the stock rule | PASS |
| Every part orderable at JLC for 10 boards today | BQ25170 orderable 0 | FAIL (lock or consign; user action) |
| Pin maps + reviewed footprints pad by pad + audit | 45 pin maps; 88 C-numbers: 65 PASS, 22 PASS-NOTE, 1 FLAG fixed in the reviewed copy | PASS |
| Placement proof (§16): every rotation-sensitive part has a class, evidence and a G10 item | 54 rows: 1F 21, 2F 16, 4F 2, P 4, N 7, M 4 | PASS |
| Placement safety before payment: JLC preview of every 2F part and of C549313's 0° | not done (needs the JLC account) | NOT_RUN |
| O-2: no PV current outside 0–45 °C, MCU off, cell 0 / 0.5 / 1.2 / 2.0 V and PCM tripped | cold stop ≥ 0.84 °C, hot stop ≤ 43.31 °C at every corner | PASS (calc; SIM-03 NOT_RUN) |
| O-2 dark load ≤ 2.5 µW | 0 µW | PASS |
| O-2 within the 12 mm² reserve | 20.6 mm² | FAIL (better route: pack PCM, reserve 3) |
| TS window with the shared NTC: cold ≥ 0 °C, hot ≤ 45 °C at every corner | 0.84–5.19 / 38.56–44.64 °C | PASS |
| USB charge ≤ 0.5 C | 70 mAh: ≤ 0.476 C; 66 mAh nominal at KISET max and R140 −1 %: 0.505 C | PARTIAL (option R140 10.2 k → 0.495 C, or ≥ 67 mAh) |
| PV bound ≤ 0.5 C with R_LIM 12 Ω (+Q14) | ≤ 0.400 C | PASS |
| No brown-out at a motor start at VBAT ≥ 3.60 V | 25 °C: +9 mV minimum margin; 0 °C: only with the INA_BAT-limited soft start | PARTIAL (calc; SIM-03 NOT_RUN) |
| −5 V on the contacts harms nothing | D14 blocks (≤ 0.55 µA) | PASS (design; SIM NOT_RUN) |
| Ship wake by the button and the head | 0.18–0.25 s / 1.68 s to the strict Q4 threshold | PASS (calc) |
| T6 SHELF ≥ 182.6 d with the as-built loads | 242 d (at bounds) | PASS (planning) |
| Board area ≤ 0.62 on both measures, total and per zone, 37 × 29 | 0.613 / **0.678**; tall zone 0.523 / 0.579 | FAIL |
| Same, 38 × 29 (41 mm reserve) | 0.592 / **0.656** | FAIL |
| Same, 38 × 29 with reserves 1 + 3 | 0.551 / 0.610 | PASS (needs the supervisor's written decision 5 (d) + felt check, and the pack RFQ) |
| V3-G1 placement, V3-G4 SIM-03, V3-G6, V3-G8 cplgate | not in this lane | NOT_RUN |

## 6. Unverified - needs samples (nothing was bought)

- **BQ25170:**
  - /PG high-level leakage: only a 1 µA bound is published.
  - ISET RC values come from the BQ25171-Q1 note (SLUAAG9).
  - Termination accuracy at 10 k.
- **TXU0101 / TXU0104:** typical supply current (only the 2.5 µA maximum is published). DISP during the first part of the VDD ramp (outputs high-Z below 100 mV).
- **Q12:** IDSS at 4 V (ship-mode path; bound 1 µA at 20 V).
- **ERM VCLP0820:** start current and starting voltage (taken from the CLP1020 class). Felt strength.
- **Custom 1.08" front-light film:** VF and absolute maximum current.
- **D14 under −8 kV contact ESD:** reverse stress near its 40 V. Fallback: a 60 V Schottky in the same land.
- **SW1:** contact finish for a 4 µA dry circuit; press through the membrane.
- **O-2:** comparator offset and hysteresis spread on real parts; Q14 gate-hold leakage (IGSS at 2 V not specified).
- **Pack:** cell + PCM resistance at 0 °C (2.5 Ω assumed).

## 7. Actions that wait for the user (not done)

1. **BQ25170 C5208201:** JLC shows 152 in stock and 0 orderable today. Lock parts or consign before an order.
2. **JLC BOM-tool previews before any payment:**
   - pin 1 of U15, U16, U17, U19, U20, U21 (and the V2 2F parts);
   - the 0° orientation of D12 C549313, which has no EasyEDA record;
   - SW1's actuator side.
3. **Decision on the area reserves:**
   - (1) LED chain: the supervisor's written acceptance of decision 5 (d), plus the felt-strength check with motor samples;
   - (3) O-2 in the pack PCM: ask in the pack RFQ;
   - or accept a 39.7 mm board (pod about 42.7 mm).
4. **Head (V3-G10):** output ≥ 4.85 V at the contacts at 40 mA.

## Stage 1 (2026-11-14): changes after the design review (`v3/stage1/STAGE1.md`, `issue_log.json`)

- **D-1 O-2 override.**
  - Q16's gate moves from VBAT_OK to O2_HB. O2_HB is a software heartbeat on CHG_DIS, coupled through C175 (220 pF C0G, GRM0335C1H221JA01D, C161418) with R176 (1 MΩ) to ground.
  - Without a heartbeat there is no override. A healthy band whose MCU is not running therefore does not harvest. With VBAT_OK low (buck and MCU off), the window comparators decide.
  - The O-2 now has 16 parts and a 22.1 mm² courtyard.
- **D-8 RISET.** R140 becomes 10.2 kΩ 1 % 0402 (0402WGF1022TCE, C11660). The charge current is 26.2 / 29.4 / 32.7 mA, ≤ 0.495 C at 66 mAh.
- **D-9 SW1 land.** Pad 5 (the ESD-pin land with paste) is deleted. The courtyard is 4.04 × 6.54 mm. Pin 5 is removed from the pin map, and the audit allows the documented deletion.
- **D-12 motor.** Q19 (PMZ290UNE2) sits in series with Q12 and shares its gate. A new net, MOTOR_S, joins the two FETs; EOL probes it.
- **D-6, D-7, D-8 G10 items.** (e) 26–33 mA; (h) 8.3–9.1 mA into a 330 Ω jig load; (i) MOTOR_S check; (k1)–(k3) with the heartbeat; (l) four keys, no repulsion.
- **D-16.** The comments say that VBUS_K floats behind D14.
- **Tools.** `tools/run_all.sh` prints the exit code of every step 4 tool. The first stage-1 run showed `audit_footprints.py` failing silently with exit code 1.
- **Stock.** Refreshed on 2026-11-14 20:52–20:57 UTC (`stock_report.md`).

---

## Gate 1, level 0 and level 4 (2026-11-15; full record in `../g1/dense/DENSE.md`; the stage-1 state is frozen in `../design_s1/`)

中文：为第一关把主板做密。基线 `v3f` 里 48 个位号换了更小的料或焊盘，SW1 换成 C&K 原厂焊盘；网络不变。第 4 级（去功能）只做成开关，不进基线。

**Level 0, built into the baseline `v3f`** (same 233 references and 143 nets as stage 1; J13 lost its net-less key pad):
- 28 placed parts 0402 → 0201, 4 parts 0603 → 0402, R130 1206 → 0805 (C17445, ≤ 52 mW = 42 %), 7 DNP lands one size smaller. List with C-numbers, ratings and today's stock: DENSE.md §2.2 and `area_check.md` §4.
- Kept at size, with the reason: DENSE.md §2.3 (R301–R306 stay 0603: SIM-08 110 V against the 100 V overload rating of the 0402 anti-surge part).
- SW1: the reviewed footprint carries C&K's recommended land (4 pads 1.05 × 1.40 mm; origin, 0° and pad numbers as EasyEDA), courtyard 22.2 mm². `tools/review_footprints.py` (`SET_PAD`), checked pad by pad in `tools/audit_footprints.py` (`MAKER_LAND`).
- Lands (`tools/gen_footprints.py`): strap entry 1.0 × 2.5 mm, lid tail 3 × 1.0 × 2.0 mm at 1.5 mm, J13 = bridge-flex land 10 × 0.30 × 1.20 mm without a key pad. Tail assumptions: DENSE.md §3.2.
- O-2: circuit unchanged; R174 in 0201 (21.3 mm², 16 parts).

**Switches in `src/common.py`** (tags built from them; `tools/run_all.sh` builds nine option variants beside `v3f` and `v3f_fldnp`):
- `SB_O2 = std | merged | pack`; `SB_MOTOR = erm8 | erm7 | erm6 | none`; `SB_FL = fit | dnp | none`; `SB_LED = fit | none`.
- `merged` (one O-2 gate FET, 19.3 mm²) has two open points and is not the baseline: `calc/o2_dense.py`, DENSE.md §4.2.

**Tools changed:** `run_all.sh` (variant loop, `--main`), `make_outputs.py` (option variants, heights of the new parts, motor line), `area_check.py` (rewritten: 38 × 29 mm, every option, DNP lands and fiducials, height classes, item list against stage 1), `review_footprints.py`, `gen_footprints.py`, `audit_footprints.py`, `placement_proof.py`, `sch.py` (sheet titles).

**Re-run (run 2, exit 0):** ERC 0 errors and 4 warnings in all 11 variants; netlist cross-check 0 differences; audit 67 PASS / 21 PASS-NOTE / 1 FLAG; placement proof 55 rows (classes as stage 1); courtyard 451.7 mm² (project) / 471.5 mm² (with DNP lands and fiducials); fixed lands 80.0 mm². Gate 1 first order with the stage-1 CAD keep-outs at 38 × 29: 0.628 / 0.696 (PCB count 0.656 / 0.726): still FAIL; levels 1–3 and a real placement decide.
