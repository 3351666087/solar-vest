# FINISH: hand-style finishing of rentres/b8/best -> CLOSED (2026-11-17)
中文摘要：
1. **已闭合**：v3/finish/solarband_v3f_final.kicad_pcb（附 .kicad_pro/.kicad_dru/.kicad_prl），未连接 0，DRC 错误 0
   （kicad-cli 10.0.7，--refill，用板子自己的 .kicad_dru），放置合法，关键对 0；242 个零件相对 b8 都没有移动。
2. b8 的 8 个未连接全部靠局部拆线重布完成（窗口拆线 + pfroute 8 层、Q-2 neck、Q-3 shield），除 P-7 外没有改动或放宽任何规则。
3. 最后一个 U10.6 I2C_SDA 用的是 lead 的新裁定 **P-7**：I2C_SCL/SDA 在 E1 上方合计最多 2 个过孔，且每个距点开口 ≥1.0 mm。
   .kicad_dru 里加了一条命名规则，R-2 规则只对这两个网、且只在 E1 上方豁免（E2 不豁免）。实际只用了 **1 个**过孔：I2C_SDA 在 (102.35,105.875)，
   距最近的点开口 5.96 mm。另一个过孔在 (107.03,101.78)，在 E1 外面。
4. 选项 A（U10 移 ±0.3 mm，合法、关键对 0）试过：分别剩 2 个和 4 个，不采用。
5. SIM-07 复核：极板上方过孔 E1 48 / E2 10（b8 为 42 / 10）；禁用类网络在极板上方过孔只有 1 个（I2C_SDA，P-7 允许）；
   In4 缺口 6.86 mm、In1 缺口 4.23 mm（b8 为 2.40 / 0.58，Q-3 要求报告）⚠。

## Files (v3/finish)
- `solarband_v3f_final.kicad_pcb/.kicad_pro/.kicad_dru/.kicad_prl` (= runs/w/q5), `drc_final.json`, `board_stats_final.json`,
  `shield_final.json`, `chk_final.json`, `placement_final.json` (= b8 placement, unchanged), `finish.json`
- `unconnected_b8.png` (the 8 of b8), `u10_surroundings_u7.png` (the board at 1 left, before P-7); earlier best: `solarband_v3f_best1.*`
- Tools (copies of eco3/tools_t2 + new): `rip.py`, `fin_try.sh`, `fin_apply.sh`, `corridor.py`, `pzpatch.py`, `drcwin.py`, `transplant.py`,
  `plot_pairs.py`. `pfroute.py` patches: (1) via hole >= 0.20 mm from net-tie copper (KiCad hole_clearance, the NT1/NT2 failure);
  (2) env PF_P7_NETS / PF_P7_ZONE: those nets may have vias over E1 only (and optionally only inside one rectangle).
  maze_finish `route` / maze_rrr are 6-layer only: not used.

## The 8 items of b8 (KiCad mm; board = x-100, 130-y) and how each closed
| # | Net | Ends | Closed in |
|---|---|---|---|
| 1 | GND | U1.15 via (119.65,106.78) - NT1.2 stub (120.70,107.25) | b2: pfroute with the net-tie via rule |
| 2 | GND | NT2.2 (123.43,110.58) - via (122.80,109.25) | t1: window rip |
| 3 | VDD_1V8 | U10.5 (103.57,105.95) - C504 (106.11,102.80), F.Cu only | v1: U10 window incl. GND |
| 4 | NTC | Q10.3 (125.08,112.58) - R149.1 (110.03,120.71) | n1: corridor rip |
| 5 | NTC | Q10.3 - R116.2 (129.19,123.83) | n1 |
| 6 | VBAT_OK | Q18.1 (120.58,120.05) - In2 stub | t1 |
| 7 | VBAT_OK | R129.1 (120.09,117.33) - In2 stub | b1: plain pfroute |
| 8 | PPG_INT | R401.1 (121.98,114.81) - stub (112.39,122.10) | p1: corridor rip (36 nets rerouted) |
The U10 knot (T-5: no via inside the island; VDD_1V8 / I2C / VBUS_K: no via over E1) then moved the last open pin between U10.2, U10.4,
D14 VBUS_K and U10.6 SDA (u1..u8, g1..g7). Path: b0 8 -> b1 7 -> b2 6 -> t1 4 -> p1 3 -> n1 1 -> ... -> u7 1 -> (P-7) q5 0.
Every intermediate board: 0 DRC errors; placement unchanged and legal.

## P-7 in the final .kicad_dru
- New rule "P-7 I2C via over plate E1 (exception, max 2, counted)" (comment cites the lead ruling of 2026-11-17).
- Rule "R-2 no via of a forbidden net over a plate": condition gains `!((NetName == I2C_SCL || I2C_SDA) && !intersectsArea(PLATE_E2_AREA))`.
- Dot keep-outs (DOT_E11/E12/E21/E22_NO_VIA) unchanged. The count of 2 at most is enforced by the router and checked by board_stats: I2C over E1 = 1 (SDA), 0 (SCL).

## SIM-07 re-check data (board_stats.py on the final board)
E1 48: GND 15, TMP117_ISLAND 4, ECG_INN 3, SPI_SCK 3, AVDD_ECG 2, ECG_INP 2, GND_K 2, NRESET 2, SWDCLK 2, XL1 2, and 1 each
CS_FLASH, DEC1, E1_LINK, E1_PAD, ECG_DRDY, I2C_SDA, IMU_INT1, INA_VS, SPI_MISO, SWDIO, XL2.
E2 10: GND 4, O2_OK 2, E2_LINK 1, E2_MID 1, E2_PAD 1, E3_MID 1.
Plate-forbidden nets: 1 via over a plate (I2C_SDA, E1, P-7), none over E2. Their track over the plates on In2/In3: 117.3 mm (b8 78.2).
In4 gap under them 6.86 mm, In1 gap 4.23 mm ⚠ (Q-3: In4 should be solid under such tracks; flagged for the SIM-07 lane).
Board: 508 vias (b8 486), track 2405.6 mm (b8 2122.3); 61 dangling-track / 1 dangling-via warnings (no errors).
