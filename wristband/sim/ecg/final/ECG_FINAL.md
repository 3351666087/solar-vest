# ECG final: SIM-07 / plate re-check of the closed board (R-4, P-1, P-2, P-7, Q-3), 2026-11-17
中文摘要：
1. **M2 按现有规则（F-9 + P-2）：FAIL，最坏 613.8 µVpp**（底噪 3.99 + 耦合 609.8，ARCH 10M|1n；体内标称 188 µVpp）。主因不是 P-7 过孔，而是**极板上方 In5/In6 上的非禁用网络**在会话中仍在活动：
   IMU_INT1（E1 上 In6 12.95 mm + 1 过孔 ≈ 1.10 pF；P-2 停掉 I2C 后 FIFO 阈值中断无人清除，会话内出现一次 1.8 V 阶跃）558 µVpp；SPI_SCK（3 过孔 + In6 6.36 + In5 1.81 + In3 缺口 2.31 mm ≈ 0.85 pF）31.5；PPG_INT（In6 1.85 mm ≈ 0.15 pF）13.7；CS_FLASH 3.3；PV_SW（In4 缺口 0.12 mm 的 Voc 采样）1.7。
2. P-7 的 I2C_SDA 过孔 + In2 缺口 3.13 mm（0.19 pF）：P-2 成立时为 0；P-2 失效时 48 µVpp —— P-7 完全依赖 P-2 ✅（已知）。In4 缺口 6.86 mm 中只有 PV_SW（E1）和 VIN_DC（E2）在会话中有活动：1.69 / 0.0001 µVpp；其余（NTC、O2_TH、INA_EN、PWR_CYC、DISP_CTRL）会话中静止。In1 缺口 4.23 mm 在走线的另一侧（朝 F.Cu），不构成到极板的路径。
3. **最小修法 = 固件规则（不改板）**，把 P-2 扩成"会话内只读 ADS1291"：记录开始前 (a) 关 IMU 的 INT1（或 IMU 进入 power-down），(b) 暂停 PPG（无 PPG_INT、无 PPG SPI 读），(c) 会话内不写 flash（ECG 存 RAM / BLE 流，结束后再写）。三条都要：
   只做 a 55.8，a+c 32.5，a+b 29.4，**a+b+c：M2 = 3.99 + 2.24 = 6.23 µVpp ≤ 10，PASS**（体内最坏 5.30，标称 4.65）。
4. 改板替代（未做）：把 IMU_INT1、PPG_INT、SPI_SCK 移出 E1 上方的 In5/In6（改到 In2/In3 屏蔽层）要在已闭合的板上重新布线，风险和工期都大于固件规则，所以不建议；板子没有改动，DRC 不需重跑。
5. 患者直流电流、ESD 各行与最终布局无关或已满足：网络不变、过孔全部盖油且距点开口 ≥ 1.0 mm（DRC 0），D15–J18 courtyard 间距 0.693 mm ≤ 1 mm（J-3 ✅），各行结论不变（5c 仍为记录在案的残留）。

## Inputs ✅ (produced by named tool runs)
- Board `v3/finish/solarband_v3f_final.kicad_pcb` (not modified). Geometry: `plate_geom8.py` (copy of prechecks/plate_geom.py, 8-layer, plates = rule areas PLATE_E1/E2_AREA, In4 gap test = shield_check rule) -> `plate_geom_final.json`.
  Reproduces finish.json: E1 48 / E2 10 vias, I2C_SDA 1 via over E1, In4 gaps PV_SW 0.12, PWR_CYC 0.88, NTC 0.20, O2_TH 1.02, VIN_DC 0.32, I2C_SDA 3.13, INA_EN 1.05, DISP_CTRL 0.14 mm (sum 6.86).
- Model: `sim07_final.py` (copy of prechecks/sim07_vias.py): SIM-07 ngspice network (FINAL, 2 x 330 k), 0.5-40 Hz filter (ARCH 7.2), transfers into e1 and e2, four electrode sets, high C bound for the verdict.
  Fixed a defect of the copied artefact(): trains with period > 2 s (Voc sample) had their events inside the discarded first 2.5 s; now at 5 s + k*16 s.
- C estimates ⚠: via 0.026-0.059 pF (prechecks); In6 0.05-0.08, In5 0.02-0.04 pF/mm (8-layer stack of PLANB 2 ⚠); In2/In3 at an In4 gap 0.0045-0.045 pF/mm; F.Cu behind In1 GND: 0.

## Activity in an ECG session (F-9 display off, P-2 no I2C / NTC, motor/LED locked out, harvester and BLE running)
| Net (plate) | C high pF | In-session signal | ARCH 10M|1n µVpp |
|---|---|---|---|
| IMU_INT1 (E1) | 1.103 | one 1.8 V step (FIFO flag not cleared under P-2) ⚠ | 558.0 |
| SPI_SCK (E1) | 0.846 | PPG read 1 Hz 0.3 ms + flash pages ≈ 6 Hz 0.5 ms (0.9 V mean) ⚠; ADS reads 500 Hz out of band | 31.5 |
| PPG_INT (E1) | 0.148 | 1 Hz, low ≈ 1 ms ⚠ | 13.7 |
| CS_FLASH (E1) | 0.070 | ≈ 6 Hz page programs (ECG log 48 KB/session, ARCHITECTURE) ⚠ | 3.3 |
| PV_SW (E1, In4 gap) | 0.0056 | Voc sample 0.57 V, 256 ms / 16 s (v2 H1 worst) | 1.69 |
| SPI_MISO / DEC1 (E1) | 0.067 / 0.117 | 1 Hz reads + 16 mV data step / 20 mV radio steps ⚠ | 1.40 / 0.25 |
| VIN_DC (E2, In4 gap) | 0.0144 | Voc sample + 20 mV 20 Hz ripple bound ⚠ (E2 transfer is small) | 0.0001 |
| I2C_SDA (E1, P-7 via + gap) | 0.195 | static by P-2 (P-2 broken: 48.1) | 0 |
| static in a session | — | SWDIO 0.70, INA_VS 0.66, XL1/XL2, NRESET, SWDCLK, AVDD_ECG, island, INA_EN, PWR_CYC, NTC, DISP_CTRL; E2: O2_OK 0.39, O2_TH (V_O2 off, Q18) | 0 |
Front-end cross caps (ECG_INN/INP over E1, E2/E3 nets over E2): noise 26.98 -> 26.98 µVpp, no effect. ECG_DRDY: 500 Hz line, 0.0002.

## M2 (limit ≤ 10 µVpp; floor 3.99) — `sim07_final.py [flags]` -> `sim07_final_<flags>.json`
| Firmware set | nominal | dry x2 | ARCH 1M|1n | ARCH 10M|1n | M2 worst | Verdict |
|---|---|---|---|---|---|---|
| as ruled (F-9, P-2) | 184.0 | 364.1 | 123.8 | 609.8 | 613.8 | **FAIL** |
| + (a) IMU INT1 off | 12.1 | 24.0 | 12.5 | 51.8 | 55.8 | FAIL |
| + (a) + (c) no flash writes | 6.7 | 13.3 | 6.8 | 28.6 | 32.5 | FAIL |
| + (a) + (b) PPG paused | 6.0 | 11.9 | 6.0 | 25.4 | 29.4 | FAIL |
| **+ (a) + (b) + (c)** | 0.66 | 1.31 | 0.42 | 2.24 | **6.23** | **PASS** |
Low C bound, as ruled: still FAIL (IMU_INT1 alone 0.68 pF against 0.012 pF allowed).

## Proposed lead ruling (P-2 extended, firmware; needs the lead) and open items
- P-2b: before the recording starts (after the announcing vibration) the firmware disables the IMU INT1 routing (or puts the IMU in power-down), stops the PPG and its interrupt, and defers every flash write until the session ends; during the 30 s only the ADS1291 is read (DRDY + SPI) and BLE may stream. RAM: 30 s x 500 SPS x 3 B = 45 KB of the nRF52832's 64 KB ⚠ (or stream / pack to 2 B).
- Board left as closed; no DRC re-run needed. If the lead prefers a board fix: IMU_INT1 (In6) and PPG_INT (In6) off E1 removes 572 µVpp; SPI_SCK would still need (c).
- Patient DC current (rows 2a-2d) and ESD (5a-5f): no layout dependence beyond tented vias ≥ 1.0 mm from the dots (DRC 0) and J-3 (D15-J18 0.693 mm ✅, chk_final.json): unchanged; 5c stays a recorded residual.
