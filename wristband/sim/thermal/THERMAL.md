# V3-G2 (SIM-13 thermal), V3-F stage-2a pod 41 × 34

2026-11-15. All values ⚠ (model results; no measurements). Models: `pod3d_v3f.py` (3-D) and `strap2d_v3f.py` (2-D), run ✅ (logs in `logs/`).

## 中文摘要

- **阶段 2b 复算（2026-11-15，`s2b_final.py`）：按原文判定 V3-G2 全部 11 项 PASS。** 设计：吊舱顶面平 5.395 mm（层压板与窗口齐平，层压板下空气 0.895 mm）、窗座 +0.09、红外截止镀膜 40 %（假设值）、翼片硅到 s 8 mm、表带根部与表带 α 0.30、胶囊 4.6 mm / 玻璃顶 0.50、电机 ≤ 5 % 占空比、U10 过孔岛在 (6.05, 25.55)。吊舱最高 42.67 °C，比 V2-B 低 0.07–0.27 K；翼片列出工况最高 42.56 °C；胶囊下皮肤最高 42.59 °C。
- 遗留：印刷吸收率按 T-2 允许 0.25 时，在灌注 1e-3 + 风 ×0.6 的最坏角吊舱 43.18 °C、电机 43.26 °C（> 43）；印刷 ≤ 0.20 时 42.92 / 43.00 °C。翼片在 1e-3 + 风同时出现（未列工况）时 43.27–43.43 °C。
- **阶段 2d 快速复算（2026-11-15，`s2d_pod43.py`，43 × 34，电机在 E2 上方、膜保留）：1a、1b、4c、5 PASS。** 吊舱最高 42.53 °C（原 42.67），比 V2-B 低 0.16–0.34 K；电机 5 % 占空比最坏 42.59 °C（原 42.75）。印刷 0.25 在 1e-3 + 风角仍 > 43（43.09 / 43.15 °C），≤ 0.20 时 42.81 / 42.87 °C。其他行未变、未复算。
- 以下为阶段 2a 原文（"before"）。

- 按原文判定：V3-G2 **FAIL**。共 11 项：PASS 5（3a、3c、4a、4b、5），FAIL 6（1a、1b、1c、2、3b、4c）。
- 吊舱（1000 W/m²，35 °C，W-C，灌注 3e-3）按现设计皮肤最高 42.07–42.92 °C（显示屏 α 0.45–0.75），比 V2-B 的 41.17 °C 高 0.90–1.75 K；灌注 1e-3 加风速 ×0.6 时到 44.90 °C。原因：叠层太薄，层压板下只有 0.15 mm 空气。
- 最小修正 FIXP：PV 层压板抬高 0.655 mm，与窗口顶面平齐（吊舱最大厚度 5.305 mm 不变，LEAD f），再在窗口玻璃上加红外截止镀膜（显示屏吸热减少约 40 % ⚠）。修正后 α 0.75 时为 41.14 / 41.76 / 40.70 / 41.95 °C，在所有对应条件下都不高于 V2-B（余量只有 0.02–0.05 K），最高 42.73 °C ≤ 43。
- 遮罩窗口的过渡版（α 0.6）按现设计 43.27 °C，FAIL。PV 层压板抬高 0.655 mm、遮罩 α 降到 ≤ 0.35 后为 41.03–42.67 °C，PASS。
- 翼片（硬门槛）FAIL：165 mm 腕、灌注 3e-3 时四个子电池下皮肤 41.4 / 42.5 / 43.8 / 45.0 °C（140–200 mm 腕为 44.7–45.3 °C）。按门槛条件，能通过的最小措施是 (b)：从 s 9 mm 起外区做成浅色（α ≤ 0.30），三种腕围下 42.61–42.97 °C；(a) 在 s 8–10 mm 截短均不通过。若风速 ×0.6 和灌注 1e-3 也要通过：有源区截到 s 8 mm，再加浅色表带根部（α ≤ 0.30）。
- 电池舱：α 0.15 时电芯 40.9–44.2 °C（灌注 1e-3、h 5 时 45.7 °C，此时由热端截止停充），始终 ≤ 60 °C，PASS。舱下皮肤在灌注 1e-3、h 5 时 43.98 °C，FAIL，改用浅色表带后 41.27 °C。
- 低温：离腕时电芯就是气温（−20 °C）。O-2 冷端截止 0.84–3.97 °C、USB TS 1.85–6.04 °C，都在 0 °C 以上，所以不会在 0 °C 以下充电，PASS。
- 充电热（22 / 50 / 70 mW）在室内只让皮肤升高 0.17–0.57 K，PASS。电机 0.11 W 连续 257 s 估算 46.3 °C，FAIL；改为 ≤ 5 % 占空比后最坏 42.81 °C。
- TMP117（U10 在 E1 上方）带 4 × 4 mm 过孔岛时耦合误差 0.16–0.30 K，PASS；不加岛 1.11 K，所以过孔岛是布局要求。

## 1. Inputs and models

- Geometry: `v3/cad/src/geom_v3f.py` (POD_W 34, raise 0.15) and BASELINE §8 with S2-06. Window column 5.305 mm (glass 0.70, film 0.25, air 0.155, panel 0.80, support 0.10, low parts 0.75 + 0.15). PV column 4.65 mm (laminate 1.20 at 2.65–3.85, parts to 2.50). Strips 4 × 27.7 × 2.80 mm = 311.1 mm². Floor: 0.25 mm PC with Ti E1 212 / E2 264 mm², mesa 11 × 7 × 0.80, carrier 0.10, PCB 1.10. ERM Ø8 at (20.0, 25.4) on the floor film. No cell in the pod.
- U10 TMP117 at pod (5.53, 25.55) and U15 BQ25170 at (5.53, 22.55), both on the sky side. Source: placement `v3/g1/place/work/pl_S2W34A3_B_s13.json` (routing is still running, so these positions can change).
- 3-D model: the physics review's FV model (`review_fv3d_v2b.py`, a copy of `redesign/attack_physics/calc/fv3d_v2b.py`), with the same materials, boundary data and SIM-13 tissue R_eff. The V2-B rev-1 copy in `pod3d_v3f.py` reproduces **41.17 °C** ✅, so the V2-B comparison is model to model. The model reads 0.4–0.5 K low against SIM-13 (REDESIGN §5.7). Absolute values below are given without that bias.
- Absorptance: display 0.45–0.75 (under the front-light film, film 0.03). Window border and laminate print 0.15 (G-8), with 0.25 and 0.60 as sensitivities. Silicon 0.90. K and E3 tops 0.50.
- 2-D strap section (s, z): wing (TPU 1.20 + laminate 1.75, cells at 0.40 below the top, sub-cells as `worn_v3f.wing_parts`), capsule (PC 0.40 / cell 3.50 / air 0.20 / glass 0.40 with the print under it), lug, root, QR and band. The gap g(s) comes from the CAD wrist model (free span 14.46 / 15.22 / 16.24 mm on 140 / 165 / 200 mm wrists). Gap conductance 0.026/(g + 0.05) + 6 W/m²K, as the BASELINE 1-D bound. Tissue is 2-D Pennes, 37 °C at 30 mm depth. The sun is normal to every top face. Top h = h_conv + h_rad (h_conv 10, wind × 0.6 = 6).
- Strap and band absorptance 0.6 unless stated. In this bound a bare α 0.6 strap gives 42.6 °C skin at 3e-3 and 45.7 °C at 1e-3. Bare skin (1-D, no sweating) gives 43.8 °C.

## 2. Verdicts (criteria as written; skin values are the model's contact-skin maxima)

| # | Case | Criterion | Result (before, stage 2a) | Verdict before | Smallest fix → result (before) | After: stage-2b design | Verdict after | Stage 2d: 43 × 34, motor over E2 (`s2d_pod43.py`) |
|---|---|---|---|---|---|---|---|---|
| 1a | Pod, full sun, W-C, display 0.45–0.75, perfusion 1e-3 / 3e-3 / 6e-3, wind × 0.6 | skin ≤ 43 °C | 41.54–43.81 °C without wind; 43.33–44.90 °C with wind; dark prints 0.60: 44.73 °C | FAIL | FIXP → max 42.73 °C (print ≤ 0.25; print 0.60 still 45.07 °C) | 42.67 °C max (disp 0.75, 1e-3, wind); print 0.25 at that corner 43.18 °C, print 0.20 42.92 °C | **PASS** | 42.53 °C max (disp 0.75, 1e-3, wind); print 0.25 there 43.09 °C, print 0.20 42.81 °C → **PASS** (print ≤ 0.20 at that corner) |
| 1b | Same pod | not hotter than V2-B (41.17 °C at 3e-3; 41.81 / 40.72 / 41.99 at 1e-3 / 6e-3 / wind; 41.75 at print 0.25) | 42.07 / 42.50 / 42.92 °C (display 0.45 / 0.60 / 0.75): +0.90 to +1.75 K | FAIL | FIXP → 41.14 / 41.76 / 40.70 / 41.95 / 41.54 °C, all ≤ V2-B (margin 0.02–0.21 K) | 41.09 / 41.70 / 40.65 / 41.89 / 41.48 °C (w3 / w1 / w6 / wind / print 0.25), margins 0.07–0.27 K | **PASS** | 40.99 / 41.58 / 40.56 / 41.77 / 41.41 °C (w3 / w1 / w6 / wind / print 0.25) vs 41.17 / 41.81 / 40.72 / 41.99 / 41.75: margins 0.16–0.34 K → **PASS** |
| 1c | Interim build, masked window α 0.6 | ≤ 43 °C and ≤ V2-B | 43.27 (3e-3), 44.21 (1e-3), 44.30 (wind), 45.47 °C (1e-3 + wind) | FAIL | PV raise 0.655 + mask α ≤ 0.35 → 41.03 / 41.63 / 41.89 / 42.67 °C | mask 0.35: 40.16 / 40.68 / 40.87 / 41.53 °C | **PASS** | not re-run (window column unchanged; the longer glass only adds border) – stays PASS |
| 2 | c-Si wing on root B, per sub-cell, real gap (hard gate) | skin ≤ 43 °C | 165 mm, 3e-3: 41.43 / 42.48 / 43.78 / 44.97 °C (gaps 2.74 / 1.66 / 0.83 / 0.27 mm). 140 / 200 mm: 45.29 / 44.67 °C. 1e-3: 47.8–48.4 °C. 6e-3: 43.0–43.6 °C. Wind: 46.0 °C | FAIL | (b) light zone α ≤ 0.30 from s 9 mm → 42.97 / 42.81 / 42.61 °C (140 / 165 / 200 mm, 3e-3). (a) to s 8–10 fails (43.11–43.78 °C). For every case, (a) to s 8 + strap α ≤ 0.30 → 42.46 °C (1e-3); (a) to s 10 + strap α ≤ 0.30 → 42.2 °C (wind) | wing to s 8 + strap α 0.30: 40.66–40.79 (3e-3), 42.40–42.56 (1e-3), 39.8–39.9 (6e-3), 41.22–41.36 °C (wind); extra corner 1e-3 + wind 43.27–43.43 °C (not a listed case) | **PASS** | not re-run (strap unchanged) – stays PASS |
| 3a | Capsule cell, glass top, α 0.15 / 0.30, h 5–20 | cell ≤ 45 °C while PV can charge; ≤ 60 °C always | α 0.15: 40.91–44.21 °C (3e-3), 45.74 °C at 1e-3 and h 5. α 0.30: 43.30–47.67 °C, 49.42 °C at 1e-3. Max − mean 0.2–0.5 K | PASS | Above 45 °C charging is stopped (O-2 hot stop 34.88–43.31 °C, firmware 45 °C, TS ≤ 44.84 °C); max 49.42 ≤ 60 °C. Keep α ≤ 0.15 | glass 0.50, capsule 4.6: α 0.15 cell 39.95–43.56 °C; α 0.30 42.3–47.24 °C (hot stop above 45); max ≤ 60 | **PASS** | not re-run – stays PASS |
| 3b | Skin under the capsule | ≤ 43 °C | α 0.15: 39.93–41.80 °C (3e-3), **43.98 °C** at 1e-3 and h 5; α 0.30: 45.30 °C there | FAIL | strap root and band α ≤ 0.30 → 41.27 °C (α 0.15) / 42.59 °C (α 0.30) | α 0.15 max 41.27 °C, α 0.30 max 42.59 °C (1e-3, h 5, strap α 0.30) | **PASS** | not re-run – stays PASS |
| 3c | Cold: −10 / −20 °C air, h 20–30, sun 0 / 500 W/m², worn and off the wrist | no charging below 0 °C (O-2) | Worn 2-D: cell mean −0.2 to 13.7 °C (optimistic; the lens lumped value is −10 °C at −20 °C). Off the wrist: −20 / −10 °C, and −7.5 °C at −10 °C with sun | PASS | O-2 cold stop 0.84–3.97 °C, USB TS 1.85–6.04 °C, all > 0 °C at every corner | cell off the wrist −20 / −10 °C; O-2 / TS stop above 0 °C | **PASS** | not re-run – stays PASS |
| 4a | Charging BQ25170 22 / 50 / 70 mW, indoors 25 °C still air; sunny window 800 W/m², 30 °C | skin ≤ 43 °C | Indoors 32.12 / 32.35 / 32.52 °C (+0.17 / +0.40 / +0.57 K); window 42.70 °C at 70 mW | PASS | – | indoor 32.16 / 32.39 / 32.63 °C; window 41.33 °C | **PASS** | not re-run (charger U15 unchanged) – stays PASS |
| 4b | Charging 70 mW in full sun (display 0.75, 3e-3) | ≤ 43 °C; CHG_DIS at 41 °C skin | 44.16 °C steady without CHG_DIS; the sun alone gives 42.92 °C > 41 °C, so CHG_DIS stops charging first | PASS (by CHG_DIS) | FIXP gives 42.59 °C even without CHG_DIS | 42.53 °C without CHG_DIS | **PASS** | not re-run – stays PASS |
| 4c | Skin-hot motor event, 0.11 W for 257 s | ≤ 43 °C | Steady 47.23 °C. At 257 s, 0.775 of the steady rise (disc on tissue, ⚠) → **46.3 °C**. FIXP: 46.09 °C steady (≈ 45.0 °C at 257 s) | FAIL | Alert at ≤ 5 % duty (mean ≤ 5.5 mW) → 42.81 °C at the worst point (FIXP, display 0.75, 1e-3, wind); 10 % duty → 43.09 °C | 5 % duty worst 42.75 °C (print 0.15); 43.26 °C with print 0.25, 43.00 with 0.20 | **PASS** | motor at (35.75, 25.55) on the film over E2: 5 % duty worst 42.59 °C (1e-3, wind), 10 % 42.65, print 0.20 42.87, print 0.25 **43.15** °C; 5 % at 3e-3 41.04; continuous 0.11 W steady 42.84 °C → **PASS** (5 % duty, print ≤ 0.20) |
| 5 | TMP117 coupling on the new board | ≤ 0.5 K | With a 4 × 4 mm via island and filled contact to E1: +0.16 to +0.30 K vs the E1 face (all sun, indoor and charging runs; 70 mW charging: −0.01 K). Without the island: 1.11 K | PASS | The island is a layout requirement | island at (6.05, 25.55): +0.16 to +0.22 K | **PASS** | +0.16 to +0.19 K (island model as stage 2b) → **PASS** |

FIXP: the PV laminate is raised 0.655 mm, so its top is flush with the window top. The air under the laminate goes from 0.15 to 0.805 mm, the K and E3 tops follow, and the pod maximum stays 5.305 mm (LEAD f). The window glass gets an IR-cut (hot-mirror) coating that removes about 40 % of the display's absorbed heat ⚠ (assumed, not from a datasheet). Each part alone does not pass: the raise alone gives 42.25 °C and the IR coating alone 42.07 °C at display 0.75, 3e-3.

## 3. Notes for the lead

- Hot spot: in the as-designed pod the skin maximum sits at Y ≈ 22, X 18–20, under the ERM and the PV half. The 0.15 mm air gap under the laminate is the weak point. V2-B had 0.30 mm over the cell and 0.75 mm over the parts.
- Bias: with the review model's +0.45 K, FIXP's worst case without dark prints (42.73 °C) becomes about 43.2 °C. That is ⚠ margin against the absolute limit. The V2-B comparison is model to model and is not affected.
- The wing's outer two sub-cells sit 0.27–0.83 mm above the skin. In this bound an α 0.6 strap alone gives 42.6 °C (3e-3), 43.7 °C (wind) and 45.7 °C (1e-3). So the strap colour sets the floor: light roots and band (α ≤ 0.30) are needed for any wing or capsule case at 1e-3 or in wind.
- Charging below 0 °C: the cell reaches air temperature off the wrist. The O-2 and TS windows stop charging above 0 °C at every tolerance corner. The cell's −10 °C discharge limit is crossed off the wrist at −20 °C. That limit is not in V3-G2's criteria and is reported only.
- Not run (parked by LEAD g, or not named in this task): the head on the pod (90–296 mW, no-load), the single faults Q12 and Q19, the USB tab, and W-S harvesting.

## 4. Files

- Stage 2d: `s2d_pod43.py` (pod3d_v3f.pod() copied at run time with the 43 × 34 coordinates of CAD option `L43W34_..._s2d1`, motor (35.75, 25.55) on the film; check case reproduces 42.67 °C) → `out/pod3d_s2d.json` (log `logs/s2d_pod43.log`).

- Stage 2b: `s2b_final.py` → `out/pod3d_s2b.json`, `out/strap2d_s2b.json` (log `logs/s2b_final.log`); `make_thermal_s2b.py` adds `after_stage2b` to `thermal_results.json` (the stage-2a `cases` stay as "before"). `pod3d_v3f.py` / `strap2d_v3f.py` gained the parameters win_raise, u10, rail_ss / t_top, cap_t (defaults reproduce stage 2a: 42.92 °C and 45.0 °C re-checked); pre-edit copies in `logs/*.pre_s2b.*`.

- `v3/sim/thermal/THERMAL.md` (this file), `thermal_results.json` (all verdicts and numbers, from `make_thermal.py`)
- `pod3d_v3f.py` → `out/pod3d.json` (log `logs/pod3d.log`); `pod3d_extra.py` → `out/pod3d_extra.json`
- `strap2d_v3f.py` → `out/strap2d.json`; `strap2d_extra.py` → `out/strap2d_extra.json`
- Unchanged copies: `review_fv3d_v2b.py`, `sim13_fv3d.py`, `sim13_lumped.py`, `sim13_tissue2d.py`, `sim13_transient.py`, `materials.py`
