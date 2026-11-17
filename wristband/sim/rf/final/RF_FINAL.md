# RF_FINAL: lid antenna L1 on the closed board (L-1..L-5, P-3, A-2), 2026-11-16
中文摘要：
1. 在定稿板（v3/finish/solarband_v3f_final.kicad_pcb，未修改）上实测：C215.2 到馈点线长 0.648 mm（w 0.17，48.8 Ω ⚠）；L204.1 经 1.162 mm 支线（中心距，边到边 0.50）共 1.81 mm；
   **C213 不在 C215 旁边**：C213.1 到 C215.1 线长 6.09 mm，其中 3.04 mm 是 0.09 mm 窄线（约 74 Ω ⚠），芯片侧 0.90 mm 也是 0.09。
2. J40 在 (3.68, 1.43) 340°，比模型 (3.30, 1.55) 移了 **0.40 mm**（> 0.3 mm），所以跑了唯一一次粗网格 FDTD。结果**无效**：移动后的焊盘角离口袋边 X 5.0 的内层地只有 0.077 mm，
   0.25 mm 网格把它吸到地上，变成短路（Z ≈ 0.6 + 56j Ω）。改用 E→A 方向外推 + 焊盘角对地边缘电容 0.02 pF（0.01–0.05 ⚠）作为实板阻抗估计。没有剩余 FDTD 预算。
3. 现行器件（9.0 / 6.2 nH）在实板上：5.07 % / S11 −1.66 dB；预检的三元件 7.2/7.2/5.2 nH（假设 C213 在旁边）：9.62 % / −3.25 dB。两者都不再满足 S11。
4. **建议（2 元件，C213 仍不贴）：C215 = 7.6 nH LQW15AN7N6G80D（C2048575，库存 6 846），L204 = 4.3 nH LQW15AN4N3B80D（C471381，库存 21 380）**。
   人体 12.29 % / S11 −10.44 dB，自由空间 −11.0 dB，手放盖上 1.43 %，链路余量约 24.4 dB（手 15.1 dB）。三元件 8.4/7.2/4.1 nH 结果相同（12.28 % / −10.01），不更好，备选。
5. 公差（600 次）：≥1 % 100 %，≥5 % 100 %（机械全幅 94.5 %），S11 ≤ −10 dB 只有 19–20 %。gate 3a：PASS。ARCH §9：效率、自由空间 S11、链路 PASS；人体 S11 只在标称点勉强满足，**PARTIAL**，首批板仍需台架 S11 调谐（C213 焊盘留作调谐位）。
6. A-2：馈线 0.648 > 0.5 mm（已由重配吸收）；Y 3.0 边地过孔在 X 2.25–4.9 有 2.65 mm 空档（要求 ≤ 1.0），在 C215/L204 下面放不进过孔：记录为偏差 ⚠。
## Measured on the final board (`dump_rf.py` → `rf_dump.json`, `measure_rf.py` → `rf_geom_final.json`, `line_z.py` → `line_z.json`) ✅
| Item | Value |
|---|---|
| J40 | (3.68, 1.43) rot 340, land fully inside AE1 pad 1 copper; 0.40 mm from the modelled (3.30, 1.55) (LAYOUT N-5 move). Land 0.364 mm from the board edge ✅; land corner 0.077 mm (in plan) from the inner-layer GND at X 5.0, 0.15 mm from F.Cu GND |
| C215 / L204 / C213 | (3.04, 4.06) 270° / (4.20, 4.12) 90° / (8.175, 5.925) 180° DNP (C0402 land C1546) |
| Feed (ANT_FEED, F.Cu w 0.17, gap 0.151–0.157) | C215.2 → feed (2.75, 3.00): 0.648 mm; stub C215.2 → L204.1 1.162 mm (edge-to-edge 0.501); no via |
| RF_50R | L201.2 → C213.1 0.897 mm (w 0.09); C213.1 → C215.1 6.094 mm: w 0.09 3.037 mm (neck-down), w 0.15 2.346 mm, in-land 0.71 mm; no via |
| Line Z (8L estimate h 0.0764, εr 3.91 ⚠) | w0.17 48.8 Ω; w0.15 54–57 Ω; w0.09 70–79 Ω (gaps to other-net copper 0.11–0.29 mm, to GND fill 0.44–2.96 mm) |
| In1 under RF tracks | 99.0 % solid |
| Ground stitching | Y 3.0 row (Y 3.4, 0.4 mm back): X 0.75 / 1.25 / 1.75 / 2.25 / 4.90 / 5.40 → pitch 0.5 and **2.65** ❌; X 5.0 row (X 5.4): pitch 0.60–0.75 ✅. GND edges solid on 7 layers (F.Cu 83 % along Y 3.0: feed and lands). L204.2 via-in-pad ✅ |
| Pocket | no foreign copper on any layer; only the feed track notch X 2.75 Y 2.95–3.15 |
## The one coarse run (`lid_copy/`, copy of `../lid` scene + driver, feed "asbuilt", level c, gap 0.25; `lid_copy/runs/M_body_c.npz`, 460 s, rc 0)
Z = 0.57 + 56.5j Ω at 2.44 GHz against E_body_f 9.1 − 81.5j: the land snaps onto the X 5.0 ground edge on the 0.25 mm grid (a short). **Not used** (grid artefact, ⚠ no fine budget).
Used instead (`asbuilt_dz.py`): Z_asb = (Z_E + 0.40/1.13 (Z_E − Z_A)) ∥ C_edge 0.02 pF → ΔZ(2.44) = +0.5 + 8.4j Ω ⚠. Sensitivity (`sens_cedge.py`, 3-element net): C_edge 0 / 0.02 / 0.05 pF → S11 −11.4 / −10.0 / −8.1 dB, η 12.0–12.6 %.
## Re-tune (`rf_final.py` → `rf_final.json`; `two_el.py` → `two_el.json`; real chain above, HQ catalogue of post_lid, rule: S11 body ≤ −10 and free ≤ −6 dB, max body η)
| Net (C213 / C215 / L204) | Body as built η / S11 | Body as modelled (E) | Corner D | Hand | Free (est.) | MC s 0.6: ≥5 % / S11 ≤ −10 |
|---|---|---|---|---|---|---|
| In force: DNP / 9.0 / 6.2 nH | 5.07 % / −1.66 | 6.79 / −2.28 | 7.10 / −4.10 | 1.20 | 11.97 / −1.76 | 74.5 % / 0 % |
| Prechecks: 7.2 / 7.2 / 5.2 nH | 9.62 / −3.25 | 12.09 / −4.96 | 8.98 / −6.69 | 1.55 | 22.28 / −3.46 | 100 % / 0 % |
| **Proposed: DNP / 7.6 / 4.3 nH** | **12.29 / −10.44** | 9.78 / −6.97 | 4.59 / −2.70 | 1.43 | 39.5 / −11.04 | 100 % / 19 % |
| Alternative: 8.4 / 7.2 / 4.1 nH | 12.28 / −10.01 | 9.81 / −7.38 | 4.64 / −2.93 | 1.48 | 39.3 / −10.69 | 100 % / 20 % (full mech 94.5 % / 12 %) |
MC (600 builds): parts by tolerance code, lands ±30 %, returns ±50 %, line Z ±10 %, l_b / stub ±0.05 mm, l_a ±3 %, glass height and frame as post_lid (s_mech 0.6; 1.0 = full). Proposed: median 10.4 %, p5 7.7 %, ≥1 % 100 %.
Link (sim11_link rule, Nordic match IL 0.244 dB; check: 12.63 % → 24.55 dB): proposed ≈ 24.4 dB body, 22.4 dB at MC p5, 15.1 dB hand on the lid.
## Proposed BOM change (the lead applies it; `stock_rf.json`, JLC public parts API, 2026-11-16 19:1x UTC) ✅
| Ref | Now | Proposed | C-number | Stock today |
|---|---|---|---|---|
| C215 (series) | 9.0 nH LQW15AN9N0G80D C6652901 | **7.6 nH LQW15AN7N6G80D** (±2 %) | C2048575 | 6 846 |
| L204 (antenna-side shunt) | 6.2 nH LQW15AN6N2B80D C668465 | **4.3 nH LQW15AN4N3B80D** (±0.1 nH) | C471381 | 21 380 |
| C213 (chip-side shunt) | DNP | DNP (bench-tune land) | – | – |
Alternative if the bench prefers three parts: C213 8.4 nH LQW15AN8N4G80D C5788422 (8 457; C0402 land, not Murata's ⚠), C215 7.2 nH C2044544 (6 627), L204 4.1 nH C412281 (10 346). Same lands, no board change.
## Verdicts
| Criterion | Result | Verdict |
|---|---|---|
| Gate 3a: body total efficiency ≥ 1 %, link ≥ 13 dB | 12.29 %, ≈ 24.4 dB; hand 1.43 % / 15.1 dB; 100 % of MC builds ≥ 1 % | PASS |
| ARCH §9 total efficiency ≥ 5 % | 12.29 %; MC 100 % (94.5 % full mech); corner D 4.6 % ⚠ | PASS (nominal) |
| ARCH §9 S11 ≤ −10 dB on the body | −10.44 dB nominal; −7.0 dB if the feed move is ignored, −8.1 at C_edge 0.05; MC 19 % | PARTIAL |
| ARCH §9 free-space S11 ≤ −6 dB / SIM-11 ≥ 10 dB | −11.0 dB / 24.4 dB | PASS |
| A-2 layout (C215 ≤ 0.5 mm, C213 beside, stitching ≤ 1.0 mm) | 0.648 mm; C213 6.1 mm away; 2.65 mm stitch gap | PARTIAL (modelled; recorded) |
Open ⚠: real 8-layer stack (line Z); the as-built feed impedance rests on an extrapolation (bench S11 tune decides); LQW Q-f data (KQ 0.70).
