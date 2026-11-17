# G-6: first 8-layer evaluation with the grow engine (2026-11-16)

## 中文摘要
1. **8 层未闭合：最好 55 个未连接、0 个 DRC 错误**（a8，引擎 s2 权重，种子 1）；第二次 8 层（b8，权重 0.5/1.3/1.0 + 顺序扰动，种子 7）57 / 0。
2. **同条件 6 层（禁用网表含 P-1 六个网络）：75 / 0**（a6）。搜索线的 6 层 58 / 0 不含这六个网络；P-1 让 6 层多出 17 个未连接。8 层比 6 层少 20 个。
3. 两种层数都有同样 11 条“静态堵死”连接（焊盘出口被宽线规则或扇出铜封死），与层数无关：AVDD_ECG 0.8、BATT_P 11.3、GND 1.75/2.06、NTC 3.8/8.0、PV_SW 5.9、SPI_SCK 9.5、VBAT_IC 14.1、VDD_1V8 1.4/2.9 mm。
4. 其余是拥塞，集中在 U7（ADS1291 QFN-32）、U1（BQ25570）、U6（nRF52832 WLCSP）、U15/U17 周围；8 层最终迭代后已无重叠（over 0），失败来自合法化丢弃 24 条。
5. 极板上方禁用网络过孔 0 个（8 层、6 层都是）；DRC 的 R-2 两条规则已加入六个网络。
6. 运行：8 层单核一次 41 分钟（预处理 118 s，60 轮 2322 s，每轮 39 s；搜索线占 8 核时测得），内存峰值约 0.9 GB；6 层 38 分钟。
7. 闭合需要：①静态堵死 11 条——扇出修改、放置微调或主管裁定焊盘处缩颈；②P-1 宽松变体（8 层禁用网络可走 In2/In3，planb 已列，需裁定）——NTC/I2C/NTC_ADC 占 8 层剩余的 12 条；③进化线用 8 层（`"layers": 8`）做放置移动。

## 1. Results (kicad-cli 10.0.7 DRC on the final boards; placement violations 0 everywhere ✅)
| Run | Layers | Router (pres0 / mult / hist, order, seed) | Unconnected | DRC errors | Before strip | Route s | Total s |
|---|---|---|---|---|---|---|---|
| **a8** | 8 | 0.3 / 1.2 / 2.0, short, 1 (engine s2) | **55** | **0** | 53 / 2 | 2322 | 2466 |
| b8 | 8 | 0.5 / 1.3 / 1.0, short + jitter 3, 7 | 57 | 0 | 55 / 2 | 1746 | 1838 |
| **a6** | 6 | 0.3 / 1.2 / 2.0, short, 1 (engine s2) | **75** | **0** | 73 / 2 | 2125 | 2258 |
| ref grow e_s2 | 6 | same as a6, without the six P-1 nets | 58 | 0 | 55 / 2 | 880 | 895 |
All runs: placement of grow/work/b0 (w13b), 60 iterations, tlim 7200 s, forbidden list 56 nets (50 + P-1). Strip removed 2 hole_clearance tracks each run.
Grid 0.025 mm: 8L 12.2 M cells (6 signal layers), 6L 10.2 M. Timing taken with the search lane using 8 of 10 cores (load 11-17): about 3x the engine's quiet benchmark.
Peak memory (b8, whole evaluate process, ru_maxrss): 909 MB ✅. Router failures (connections): a8 11 unrouted + 24 dropped; a6 11 + 37.

## 2. Track per layer (mm) and vias
| Run | F | In2 | In3 | In4 / L4 | In5 | In6 / L5 | B | Total | Vias (new) |
|---|---|---|---|---|---|---|---|---|---|
| a8 | 487 | 259 | 313 | plane (0) | 227 | 247 | 199 | 1733 | 484 (267) |
| b8 | 544 | 240 | 299 | plane (0) | 222 | 250 | 239 | 1794 | 483 (266) |
| a6 | 510 | 401 | – | 224 (L4 signal) | – | 354 | 250 | 1739 | 484 (267) |

## 3. Vias over the plates per net (R-3), a8 (forbidden-net vias: 0 in a8, b8, a6)
- E1 (65): GND 24, TMP117_ISLAND 4, E1_PAD 3, ISET 2, CHG_PG_N 2, VSET 2, GND_K 2, RLD_OUT 2, ECG_INP 2, AVDD_ECG 2, DEC1 2, E1_MID 2, RLD_Z 2,
  SPI_SCK 2, RLD_INV 2, E1_LINK 2, PGA1P 2, ECG_GPIO2 1, RF_50R 1, PGA2P 1, XL2 1, SPI_MISO 1, INA_VS 1.
- E2 (9): GND 4, E2_LINK 2, E2_PAD 1, O2_NC 1, E2_MID 1. Quiet SPI nets 2 + 1 vias (budget about 6 each, planb). R-4 SIM-07 re-check still open.

## 4. Where the 55 (a8) are
- By net: NTC 4, AVDD_ECG 4, PV_SW 4, I2C_SCL 4, GND 3, SPI_SCK 3, SPI_MISO 3, I2C_SDA 2, VDD_1V8 2, VSTOR 2, VOUT_EN 2, VDD_DISP 2, NTC_ADC 2,
  ECG_INN 2, PV_NODE 2, others 1 each. P-1 nets (NTC, NTC_ADC, I2C_SCL, I2C_SDA) = 12.
- By part (pad ends): U7 ADS1291 13, U1 BQ25570 4, U15 BQ25170 3, U17 TXU0104 3, U6 nRF52832 2, U19, Q10, Q1, Q18, J13, U11, R126, R129, C113, R304 2 each.
- Dropped in legalisation (congestion): ALERT_LED, CS_ECG, DISP_CTRL, D_SCLK, D_SCS, E3_MID, ECG_DRDY, ECG_INN, I2C_SCL, I2C_SDA x2, NTC, NTC_ADC x2,
  PPG_INT, PV_NODE, PV_SW x2, RLD_INV, SPI_MISO x2, VBUS_K, VOUT_EN x2. Static (no legal exit, every layer count): the 11 in the summary.
- Board list: runs/a8/summary.json (unconnected_items with positions).

## 5. Verdict
- G-6 8-layer gate (0 unconnected, 0 DRC errors): **FAIL** (55 / 0). best8/ not written (the board did not close).
- 8 layers is better than 6 by 20 with the same rules; it cannot close the 11 static connections. With P-1 the 6-layer board loses 17.

## 6. How to run 8 layers (for the search lane)
- Board mode: `venv-python v3/grow8/tools/evaluate.py CAND.json OUTDIR` with `"board": ".../grow8/work/b8/v3f_g1_fan.kicad_pcb"` (8L fan board, 56-net list).
- Placement mode: add `"layers": 8` (6L build + fan-out, then tools/to8l.py) and `"forbidden_add": ["NTC","NTC_ADC","I2C_SDA","I2C_SCL","O2_TC","O2_TH"]`.
- The router follows the board's layer count; 6-layer boards run as before (6L path unchanged except the forbidden list). C core rebuilt (mask bits 64 / 128).

## 7. Open items
1. 11 static connections: fan-out change, placement moves, or a ruling on neck-down at pads (layer count does not help).
2. P-1 relaxed variant on 8L (forbidden nets on In2/In3 between the planes): not run, needs a lead ruling.
3. 8L stack-up block not written into the .kicad_pcb (thickness 1.0 mm only); JLC 8-layer 1.0 mm template still ❓.
4. In4 VDD_1V8 plane fragmentation and SIM-07 (R-4) with the plate via counts: not checked here.
