# V3-G6: SIM-06 / SIM-07 / SIM-08 for V3-F (2026-11-15)

## 中文摘要（mini-ECO 复核，2026-11-15：D15 = TPD1E10B06，电极链回到 2 × 330 k）
- 结果：PASS 15、PARTIAL 6、FAIL 1（5c）。按旧的单一“< 10 µA”标准则为 14 / 6 / 2（2d）。
- 病人直流（按 F-3）：正常 2.64 µA ≤ 10；单一故障最大 25.39 µA（密封失效 + J15 手指）≤ 50，PASS；超过旧的 10 µA。
- 屏干扰：体内 ≤ 7.26 µVpp PASS；ARCH 10M|1n 角 11.26 µVpp（680 k 时 11.28），仍 > 10，PARTIAL：换回 330 k 对这个角几乎没有作用。体内噪声标称 14.36 → 11.99 µVpp（信息）。
- J18 ESD：TPD1E10B06 下 Q20 VDS 37.1 V（+8 kV）/ 56.5 V（+15 kV 空气），超 20 V 1.9 / 23.1 ns，雪崩 0.25 / 0.84 µJ（ESD761 为 15.8–26.8 µJ）。PMZ290UNE2 无雪崩额定值，按原文 FAIL。

## 中文摘要（stage 2b ECO 复核，2026-11-15）
- 按 ECO 实际零件重跑：PASS 14、PARTIAL 6、FAIL 2（原为 11 / 4 / 7）。
- 钢框接地 + 2 × 680 k：屏干扰体内 ≤ 3.28 µVpp，合计 ≤ 7.27 µVpp；ARCH 10M|1n 角 11.28 µVpp 仍超 10。体内噪声标称 11.99 → 14.36 µVpp（信息）。
- 病人直流：正常 1.66 µA，单一故障 ≤ 2.85 µA，TVS 短路 2.53 µA，均 PASS。密封失效 + J18 手指 10.55 µA（Q20 IDSS 只有 1 µA 上限），+ J15 手指 15.83 µA（新发现：D14→R144/R145 与 R509/R510 通路），FAIL。
- 反接头：Q20 挡住，VBUS ≥ −0.08 V；Q20 短路时有 D16 钳位 −0.09 V，PASS ⚠。
- ESD：D14 100 V 反压 ≤ 68.2 V，PASS；按键 Q13 栅 −6.2 / +2.1 V，PASS ⚠。J18 上的 ESD761 钳位 25–46 V 高于 Q20 的 20 V，Q20 雪崩，FAIL（TPD1E10B06 只超 1.9 ns）。

## 中文摘要（首次运行）
1. 结果：22 项里 PASS 11 项，PARTIAL 4 项，FAIL 7 项。每项都按 BASELINE §18 原文判定。
2. **屏的 COM 干扰 ECG（FAIL）**：窗口玻璃下的不锈钢框在网表里没有接地，处于浮空状态。它把屏的 COM（3 V、30 Hz 方波）耦合到 E3 网络，耦合电容 0.06–0.30 pF。干扰在标称电极下为 46–217 µVpp，体内最坏情况 138–647 µVpp，目标 10 µVpp。手指本身的耦合可以忽略。网表和 CAD 里都没有"接地遮光印刷"。
3. **修法**：钢框接 GND（E3 端加一个弹片或导电胶点）。改后 0.7–1.1 µVpp（标称），体内最坏 3.3 µVpp，加上 3.99 µVpp 底噪，合计 ≤ 7.3 µVpp，PASS。这一改动同时解决屏盖板的 ESD 问题（5f）。
4. VDD_DISP 对 ECG 的影响为 0.0001 µVpp，表带导线 ≤ 0.023 µVpp，都 PASS。马达和前光的禁用只靠固件规则。
5. **病人直流电流**：正常情况下（包括手指按在 GND 触点上）为 4.85 µA，PASS。ARCH 单一故障加 GND 手指最高 9.77 µA，PASS，余量只有 2 %。
6. **FAIL**：TVS 短路，同时手指按在 GND 触点上，电流 130–152 µA；密封失效，同时手指按在 GND 触点上，电流 2.1 mA。修法：在 GND 触点 J18 上串一个 N-FET，只在充电头供电时导通，改后 ≤ 5.3 µA。
7. 密封失效本身（不碰 GND 触点）为 19.1 µA，是 V2-B 遗留问题；要压到 < 10 µA，还需要把限流电阻改成 2 × 680 kΩ。
8. **充电头漏电（模型）**：正常情况 0.50 µA，PASS。隔离击穿时，两种头都正好 500 µA，等于限值，零余量，判 PARTIAL。非隔离仿冒线的漏电为 250–500 µA，作为残余风险写明。Q9 的硬件 ECG 禁用 PASS。
9. **反接头 −5 V（PARTIAL）**：D14 能挡住反压。但按 D14 漏电的最大值，VBUS 会被拉到 −0.3 ~ −0.4 V，超过 U15 −0.3 V 的绝对最大值。修法：VBUS 对 GND 加一个 Schottky 钳位。
10. **ESD**：
    - + 触点 +8 kV、+15 kV：PASS。
    - **−8 kV（FAIL）**：D14 反压 63.7 V，−15 kV 时 97 V，都超过它 40 V 的额定值。修法：换成 ≥ 100 V 的 Schottky，零件未找到。
    - **按键（FAIL ⚠）**：如果放电击穿膜片，Q13 栅极会到 −118 V。修法：TVS 加 10 kΩ。
    - 表带根部：PASS ⚠。
11. **根部 1 Ω 短路（PARTIAL）**：短路电流 1.45–2.89 A，0.5–0.69 s 后皮肤表面到 43 °C。F1 必须在 0.5 s 内切断 ≥ 1.45 A。F1 型号未知，要写进电池包 RFQ。

## Inputs (read today)
- Netlist v3/design variant v3f: `src/ecg.py` (TVS → 330 k → 330 k per electrode, unchanged from V2-B), `src/charger.py` (J15 → VBUS_K → D13 ESD761 → D14 NSR0240 → VBUS, C130, R144/R145 1 M + 1 M, Q8/Q9), `src/hmi.py` (U16 VDD_DISP, J13, SW1/Q13/D12B/R165/R167), `src/power.py` (U3 EN via R123).
  - CALC_V3F §6 (panel 15/50 µW hold, VDD_DISP 2.955–3.045 V) and §8 (contact ESD).
  - pin_budget / V3_ARCH: EXTCOMIN 60 Hz, COM "about 3 V at 30 Hz".
- Geometry, all for the 41 mm pod:
  - CAD.md C-9: E3 strip / tab / J11 at 5.1 / 4.1 / 4.4 mm from the panel glass.
  - CAD.md §5: window 0.70 mm on a 0.25 mm stainless frame under the glass edge; panel 0.80 mm; air 0.10 mm.
  - LEAD_NOTES decision c: panel raised 0.15 mm.
  - STAGE2A: the FPC is 0.49 mm from the frame.
- Head interface (HEAD.md §7.2–7.3, read only): barrier 4.84 pF, 10 pF bound; source model of ENG_A §5.1.
- ESD761 (TI product page, today): VRWM 24 V, VBR ≥ 25.5 V, clamp 36.3 V typ, RDYN 0.53 typ, 1.1 pF.
- NSR0240 (JLC C896422): 40 V, 550 nA at 25 V. PMZ290UNE2 (C478155): VGS(th) 0.95 V, Ciss 46 pF.
- XB5358D0 (v2 CALC §2): IOV1 2.5–4.1 A, RSS 54 mΩ max.
- Electrode, network and noise models: the v2/sim/ecg lane, copied unchanged (FINAL network, V2-B plate capacitances ⚠, in-vivo Ti electrode model). Input-short floor 3.99 µVpp (`sim07_v2.json`).

## Methods (scripts in this folder; logs/, results/)
- `g6_com_caps.py`: 2-D finite-difference capacitance from the panel to the finger and to the E3 net. Three frame cases (floating, grounded, none), finger patch edge from +5.1 mm to −5 mm. Mesh check h 0.05 / 0.025 mm: finger term 2 %, E3 term 12 %.
- `g6_display.py`: SPICE AC transfer of COM through those capacitances.
  - COM waveform: 3.045 Vpp square at 30 / 35 / 60 Hz, steady state through the 0.5–40 Hz filter, plus sinc3 aliases at an assumed 500 SPS.
  - Electrodes: four in-vivo cases and two ARCH corners. Also run with a second finger on the GND contact.
  - SIM-06 supply chain: panel load → VSTOR_SW → TPS7A2030 PSRR → AVDD → network and ADS1291 PSRR.
  - Strap conductors into the skin.
- `g6_faults.py`: DC operating points with the harness of sim07_v2_faults.py, 7 half-cell sets. Adds the finger on J18 (wet 1 k / dry 100 k), the + contact with no head (2 MΩ), single faults, seal faults, and the fix variants.
- `g6_calc.py`: hand models for the head leakage, the Q9 lock-out, the reversed head and the root short. The root short uses a point heat source in the moulding, 1 mm from the skin face, 34 → 43 °C.
- `g6_esd.py`: generator and TVS from sim08_esd.py, executed unchanged.
  - ESD761 modelled without snap-back; the RDYN ×1.5 corner is assumed. D14 modelled first without breakdown, then with BV 44 V.
  - Button case: membrane puncture into the BTN node.

## Verdicts (criteria as written, BASELINE §18 V3-G6)

| # | Case | Criterion | Before (as built 2026-11-15) | Before | After ECO stage 2b (real parts) | After | After mini-ECO (D15 TPD1E10B06, 2 × 330 k) | Mini | After stage 2c (Q20 CJBA7002K 60 V, F-8) | 2c |
|---|---|---|---|---|---|---|---|---|---|---|
| 1a | VDD_DISP / VSTOR_SW → AVDD (SIM-06) | M2 10 µVpp, display running | 0.0001 µVpp | PASS | 0.0001 µVpp (unchanged) | PASS | unchanged | PASS | unchanged | PASS |
| 1b | panel COM → E3 net / finger, frame floating as built | M2 10 µVpp (floor 3.99 → 6.0 µVpp for the display) | C(COM–E3) 0.064–0.30 pF; 46–217 µVpp nominal, 138–647 µVpp worst in-vivo | **FAIL** | frame grounded (J19) + 2 × 680 k: 0.70–1.10 µVpp nominal, ≤ 3.28 µVpp in-vivo → ≤ 7.27 µVpp with the 3.99 floor; ARCH 10M\|1n corner 7.29 → 11.28 µVpp | PARTIAL | 2 x 330 k, frame grounded: 0.70-1.10 µVpp nominal, <= 3.27 µVpp in-vivo -> <= 7.26 µVpp with the 3.99 floor (PASS); ARCH 10M\|1n corner 7.27 -> 11.26 µVpp > 10 (680 k gave 11.28: the chain value hardly moves this corner) | PARTIAL | unchanged | PARTIAL |
| 1c | second finger on the GND contact during ECG | M2 | artefact changes < 2 %, same as 1b | **FAIL** | Q20 off: the second finger sees ≥ 4.25 MΩ, so the case reduces to 1b (not re-run separately) | PARTIAL | Q20 off + D15 TPD1E10B06: the second finger sees >= 3.86 MOhm (IDSS 1 µA + 100 nA bound), reduces to 1b | PARTIAL | Q20 CJBA7002K off + D15: the second finger sees >= 21.3 MOhm (IDSS 0.1 µA + D15 0.1 µA bound), reduces to 1b | PARTIAL |
| 1d | strap conductors (NTC step, BATT_P motion) | M2 | ≤ 0.023 µVpp | PASS | unchanged | PASS | unchanged | PASS | unchanged | PASS |
| 1e | motor and front light locked out | locked out | firmware rules (BASELINE §14, §13.2), no hardware interlock | PASS | unchanged | PASS | unchanged | PASS | unchanged | PASS |
| 2a | DC normal, incl. GND contact and + contact (no head) | < 10 µA | 4.85 µA | PASS | 1.66 µA (finger on J18 behind Q20 + finger on J15) | PASS | 2.64 µA <= 10 µA normal (finger on J18 behind Q20 + finger on J15, 2 x 330 k) | PASS | 2.48 µA <= 10 µA (finger on J18 behind Q20 + finger on J15); J18 finger alone 0.28 µA | PASS |
| 2b | ARCH single faults + finger on GND contact | < 10 µA | 9.77 µA (2.3 % margin) | PASS | 2.85 µA (TVS on E1 shorted + finger on J15); 0.62 µA with the J18 finger | PASS | 3.44 µA (IN1P->AVDD + finger on J15); 2.93 µA with the J18 finger; <= 10 and <= 50 µA | PASS | 3.44 µA (IN1P->AVDD + finger on J15, unchanged); 2.79 µA with the J18 finger; <= 10 and <= 50 µA | PASS |
| 2c | TVS shorted + finger on GND contact | < 10 µA | 130–152 µA | **FAIL** | 2.53 µA (J18 finger); Q20 itself shorted + J18 wet: 2.31 µA | PASS | TVS on E1 shorted: 5.31 µA (J18 finger), 5.63 µA (J15 finger); Q20 shorted + J18 wet 4.85 µA; <= 10 and <= 50 µA | PASS | TVS on E1 shorted: 5.31 µA (J18 finger), 5.63 µA (J15 finger); Q20 shorted + J18 wet 4.85 µA (unchanged) | PASS |
| 2d | seal fault: net → skin / plate / E3 | < 10 µA | 19.1 µA alone (V2-B, < 50 µA IEC); 2.13 mA with the GND finger | **FAIL** | seal alone 9.49 µA; + J18 finger 10.55 µA (IDSS 1 µA bound; 9.59 at 0.1 µA); **+ J15 finger 15.83 µA** (new case: D14 → R144/R145 2 M ∥ R509/R510 1.1 M) | **FAIL** | single fault: seal alone 19.12 µA; + J18 finger 20.25 µA (19.32 at IDSS 0.1 µA); + J15 finger 25.39 µA: <= 50 µA SFC (F-3) PASS; > 10 µA (old single figure) FAIL | PASS (F-3) / **FAIL** (< 10 µA) | seal alone 19.12 µA; + J18 finger 19.32 µA (19.23 at IDSS 10 nA); + J15 finger 25.39 µA (unchanged): <= 50 µA SFC PASS; > 10 µA FAIL | PASS (F-3) / **FAIL** (< 10 uA) |
| 3a | AC leakage through the head, NC, both heads | ≤ 100 µA | 0.50 µA (10 pF); 1.0 µA mains on the AP | PASS | unchanged (not re-run) | PASS | unchanged | PASS | unchanged | PASS |
| 3b | barrier shorted, UCC12050 reinforced | ≤ 500 µA SFC | 250 / 500.0 µA (0.25 / 0.5 mA source class), 0.0 % margin | PARTIAL | unchanged | PARTIAL | unchanged | PARTIAL | unchanged | PARTIAL |
| 3c | barrier shorted, UCC12040 basic | ≤ 500 µA SFC | 250 / 500.0 µA, equals the limit | PARTIAL | unchanged | PARTIAL | unchanged | PARTIAL | unchanged | PARTIAL |
| 3d | non-isolated look-alike cable, worn | stated as residual | 250–500 µA NC: residual risk, mitigated only by non-mateable contacts | PASS | unchanged | PASS | unchanged | PASS | unchanged | PASS |
| 3e | ECG lock-out while VBUS (Q9) | hardware | locks out from VBUS ≥ 1.9 V; 1.6 V overdrive at 5.1 V; none with a head on but not driving | PASS | unchanged | PASS | unchanged | PASS | unchanged | PASS |
| 4 | reversed head −5 V | band safe | D14 blocks, ≤ 0.55 µA; VBUS −0.04 V typ, −0.3…−0.4 V at D14 max IR vs −0.3 V U15 abs max | PARTIAL | Q20 blocks: ≤ 1.05 µA, D14 ≤ 1.2 V reverse, VBUS ≥ −0.08 V; Q20 shorted: −0.08 / −0.36 V (PMEG10020AELR typ / scaled max) without D16, −0.09 V with D16 | PASS ⚠ | Q20 blocks: <= 1.10 µA (IDSS 1 µA + D15 100 nA), D14 <= 1.21 V reverse, VBUS >= -0.087 V; Q20 shorted unchanged (D16 -0.09 V) | PASS ⚠ | Q20 blocks: <= 0.20 µA (IDSS 0.1 µA + D15 0.1 µA), D14 <= 0.22 V reverse, VBUS >= -0.016 V; Q20 shorted unchanged (D16 -0.09 V) | PASS ⚠ |
| 5a | + contact +8 kV contact / +15 kV air | ratings | D13 5.8 / 17.3 A; VBUS 2.1 / 3.5 V | PASS | ESD761 2.2–2.8 A (+8 kV), 13 A (+15 kV); VBUS 2.1 / 3.7 V; Q20 gate ≤ 0.85 V | PASS | unchanged | PASS | unchanged | PASS |
| 5b | + contact −8 kV / −15 kV, D14 40 V | ratings | D14 reverse 63.7 V (68.7 corner) for 1.7–42 ns; 97 V at −15 kV | **FAIL** | D14 PMEG10020AELR (100 V): reverse 61.9–67.4 V (−8 kV), 68.2 V (−15 kV); VBUS ≥ −0.11 V; Q20 gate ≥ −5.8 V | PASS | unchanged | PASS | unchanged | PASS |
| 5c | GND contact J18 | ratings | direct to the plane (not simulated) | PASS | D15 ESD761 holds GND_K at 25–46 V: Q20 VDS > 20 V for the whole discharge, avalanche 8.8–14.7 A (no rating). With a TPD1E10B06 instead: > 20 V for 1.9 ns, 0.25 µJ | **FAIL** | D15 TPD1E10B06 (as built): Q20 VDS 37.1 V (+8 kV contact) / 56.5 V (+15 kV air) > 20 V for 1.9 / 23.1 ns, avalanche 6.6 / 16.3 A pk, 0.25 / 0.84 µJ (PMZ290UNE2: no avalanche rating); negative polarity -9.2 / -12.9 V body diode, OK. ESD761 was 15.8-26.8 µJ for the whole discharge | **FAIL** | Q20 CJBA7002K (60 V), D15 TPD1E10B06: VDS peak 65.9 / 80.0 V (+8 kV contact / +15 kV air; avalanche modelled at 60 V min breakdown), 74.6 / 88.8 V at 70 V; > 60 V for 0.22 / 0.70 ns, avalanche 3.0 / 10.0 A pk, 0.021 / 0.34 µJ (no avalanche rating); > 20 V for 1.8 / 20 ns no longer stresses it; VGS <= 10.7 V (rating 20 V); negative -9.2 / -12.9 V body diode. Improved from PMZ290UNE2 (0.25 / 0.84 µJ) but the written rating criterion is still exceeded for < 1 ns | **FAIL** |
| 5d | button SW1 (puncture to the floating cover) | ratings | membrane + air hold about 9–13 kV ⚠ < 15 kV; Q13 gate −118 / +18 V | **FAIL** ⚠ | D18 TPD1E10B06 + R511 10 k: Q13 gate −5.9 / +1.5 V (±8 kV), −6.2 / +2.1 V (±15 kV) | PASS ⚠ | unchanged | PASS ⚠ | unchanged | PASS ⚠ |
| 5e | strap-root entries | no conductor reached | ≥ 20 kV through two layers, ≥ 1 mm ⚠ | PASS | unchanged | PASS | unchanged | PASS | unchanged | PASS |
| 5f | display cover ±15 kV air | discharge kept off the panel | floating frame about 1.1 mm from the surface, 0.49 mm from the panel FPC ⚠ | **FAIL** ⚠ | frame grounded through J19 (not simulated; position open in frame_gnd.json) | PARTIAL ⚠ | unchanged | PARTIAL ⚠ | unchanged | PARTIAL ⚠ |
| 6 | root 1 Ω short with F1 | F1 opens before the skin limit | 1.45–2.89 A; 43 °C at the skin face after 0.50–0.69 s; PCM trips in 2 of 8 corners; F1 ❓ | PARTIAL | unchanged (pack RFQ, E-7) | PARTIAL | unchanged | PARTIAL | unchanged | PARTIAL |

The "Before" columns are the lane's first run (fix suggestions now applied: see `v3/stage2b/eco/ECO.md`). "After": `g6_eco_noise.py`, `g6_faults_eco.py`, `g6_calc_eco.py`, `g6_esd_eco.py` (results/eco/, logs/eco/). After the ECO: PASS 14, PARTIAL 6, FAIL 2 (2d, 5c). "After mini-ECO" (LEAD_NOTES 2f F-1..F-3): `g6_calc_mini.py`, `g6_esd_mini.py`, `g6_faults_mini.py`, `g6_noise_mini.py` (results/mini/, logs/mini/); rows 2a-2d judged against F-3 (≤ 10 µA normal, ≤ 50 µA single fault), 2d also against the old single figure. After the mini-ECO: PASS 15, PARTIAL 6, FAIL 1 (5c); with the old < 10 µA figure: 14 / 6 / 2 (2d).

Stage 2c (F-8, 2026-11-15): `g6_esd_s2c.py`, `g6_faults_s2c.py`, `g6_calc_s2c.py` -> results/s2c/; pre-2c copies in logs/s2c/. Q20 = CJBA7002K (C504101): VDS 60 V, IDSS <= 100 nA at 60 V.

## Notes
- 1b sensitivity at the worst electrode: about 4,800 µVpp per pF on the E3 net and only 0.54 µVpp per pF on the finger.
  - Budget for the E3 net: ≤ 0.0013 pF (ARCH corner), about 0.008 pF nominal. A floating metal near both the COM and the E3 wrap cannot meet it.
  - The frame position and its distance to the E3 wrap are CAD ⚠ values. The COM is taken to the glass edge (the TFT ledge is ignored, conservative).
- 2c / 2d: the GND contact is a second, low-impedance return to the patient. Every single fault that puts a DC source or a galvanic couple on the body then closes the circuit.
- The J18 FET leaves the charge path unchanged:
  - The body diode starts conduction. The gate then follows VBUS_K through about 100 k, with a 1 M pull-down.
  - At 40 mA the drop is about 15 mV.
  - The head's pin check sees a diode. The head lane must confirm that this is acceptable.
- 3b / 3c: the band adds no series impedance, because D5–D7 clamp the pads to GND ahead of the 330 k chains. The result therefore equals the source's touch-current class.
- 5b: the −8 kV stress is the ESD761 clamp at 29 A (about 43 V) plus about 20 V of L·di/dt in 1.9 nH. A 60 V Schottky is not enough.
- 6: the moulding is treated as a point-source model, with no spreading in the copper (conservative). The cell resistance is taken as 0.3–1.0 Ω.
- Not run: the PV lid coupling (outside this task); E1–E3 ESD (network unchanged, v1/v2 SIM-08 hold); the ECG signal quality with the GND contact touched. With the contact wet the body is pulled towards GND; this is information only, there is no criterion for it.

## Files
- `ECG.md`, `ecg_results.json` (all numbers and verdicts), `verdicts.json`, `PROGRESS.md`.
- Scripts: `g6_com_caps.py`, `g6_display.py`, `g6_faults.py`, `g6_calc.py`, `g6_esd.py`, `g6_summary.py`.
- Copies (unchanged): `lib/`, `refs/`, `sim06*`, `sim07*`, `sim08_esd.py`.
- Results: `results/com_caps.json`, `g6_display.json`, `g6_patient_dc.json`, `g6_calc.json`, `g6_esd.json`. Logs: `logs/g6_*.log`.
- Stage-2b ECO: `g6_eco_noise.py`, `g6_faults_eco.py` (SB_RGATE = R509 + R510), `g6_calc_eco.py`, `g6_esd_eco.py`, `g6_summary.py`; results in `results/eco/`, logs and the pre-ECO copies of ECG.md / ecg_results.json / verdicts.json in `logs/eco/`.
