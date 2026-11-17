# grow8: rulings Q-1..Q-4, Q-6 — 8-layer engine upgrade, search and rented-machine bundle (2026-11-16)

## 中文摘要
1. **8 层未闭合，最好 33 个未连接、0 个 DRC 错误、放置合法**（runs/w4：Q-2+Q-3+Q-4 规则，权重 pres0 0.6 / hist 5.0）。best8/ 未写。
2. 逐步（同一放置 w13b，单核 60 轮）：**55 → Q-2 缩颈 44 → +Q-3 屏蔽层 41 → +Q-4 扇出 34 → 权重调整 33**；DRC 错误始终 0，极板上方禁用网络过孔始终 0。
3. Q-2：路由器与 KiCad DRC 两边都已实现（每个网络一个 NECK 规则区 = 自身焊盘外扩 1.5 mm；区外的 0.09 mm 宽网络走线 DRC 报错，已用 kicad-cli 验证）。
4. 静态堵死：EVAL8 列出的 11 条中 9 条被缩颈打开（U7 的 VDD_1V8/AVDD_ECG/SPI_SCK、Q10 的 NTC、U4/U5 中心球 PV_SW/BATT_P）；VBAT_IC 14.06 是拥塞不是静态。
5. **剩下 2 条静态堵死：U19.5、U20.5（TLV7031 X2SON 中心 VEE 焊盘，GND）**：四周焊盘间隙 0.16/0.26 mm < 0.09 线 + 2×0.09 间距 = 0.27；盘中孔 0.25 只剩 0.03 间距。任何权重、扇出都打不开 → 需主管裁定（换封装，如 SC70-5，或其他）。
6. Q-3：In2/In3 上禁用网络在极板上方 117 mm；**In4 平面在这些走线下有 4.35 mm 缺口**（其他网络过孔的反焊盘），In1 0.71 mm（shield.json 有位置）。
7. Q-4：扇出加“出口保护”（不占邻盘最后出口）和 0.09 缩颈扇出（7 个焊盘获得过孔）；放置移动加逃逸晕圈项（U7/U1/U6/U15/U17，晕圈为可变基因 0.4–1.4 mm）。单独清晕圈的放置（q5）为 41，晕圈只作为搜索项。
8. 搜索：evolve.py 已搬到 grow8（8 层规则、晕圈基因、可续跑、results.jsonl）；本机验证 种群 5 × 2 代（6 轮路由）从打包树端到端跑通，续跑跳过已完成的 10 个评估。
9. 租机包：v3/grow8/bundle（中文三步说明）。建议租 **64 物理核 / 128 GB / 100 GB 盘，10 小时**，POP 62、GENS 14。

## 1. Step results (kicad-cli 10.0.7 DRC on the final boards; placement violations 0 and forbidden-net plate vias 0 everywhere ✅)
| Step | Run | Rules / change | Unconnected | DRC err | Router fail (unrouted + dropped) | Total s |
|---|---|---|---|---|---|---|
| 0 | EVAL8 a8 | 8L baseline (b8 board, s2 weights) | 55 | 0 | 11 + 24 | 2466 |
| 1 | q2 | + Q-2 neck-down 1.5 mm | **44** | 0 | 5 + 15 | 1330 |
| 2 | q3 | + Q-3 In2 / In3 shielded | **41** | 0 | 5 + 13 | 1324 |
| 3 | q4 | + Q-4 fan-out (placement mode, exit guard, neck fan-out) | **34** | 0 | 4 + 9 | 1546 |
| 3h | q5 | q4 + halo-cleaned placement (NT1, X2 moved; halo 0.8) | 41 | 0 | 7 + 14 | 1556 |
| 4 | **w4** | q4, router pres0 0.6 / hist_inc 5.0 | **33** | **0** | 4 + 13 | 845 |
| – | w2b | q4, pres0 0.5 / hist 3.5 | 36 | 0 | 3 + 14 | 788 |
| – | q3L / q6 / w1-w3 | legalisation support check (now off) / + 100 it, jitter | 40 / 41 / 44, 38, 47 | 0 | | |
- pl_old (placement mode, Q-4 off): fan board 356 / 0 = b8 ✅ (placement mode reproduces the EVAL8 board). Q-4 fan board: 349 / 0.
- Step 3 changes the board itself (7 more plane pads fanned), so steps 1-2 (board mode) and 3-4 (placement mode) differ in input too.
- Timing: 60 iterations 12-13 s each with the laptop quiet (w4: 845 s total), 20-25 s each under load 8-9 (q2-q4). Peak RSS 1.3-1.5 GB.

## 2. w4 board (runs/w4/final.kicad_pcb)
- Unconnected by net: NTC 4, GND 3, VSTOR 2, I2C_SDA 2, I2C_SCL 2, AVDD_ECG 2, SPI_SCK 2, SPI_MISO 2, VBUS 2, PV_SW 2, PD_GND 2, others 1.
  Pad ends by part: U7 4, U20 3, U6 2, U11 2, J8 2, R149 2. Static: GND U19.5 / U20.5 only (runs/diag/d4.out).
- 462 vias; plate vias E1 52 / E2 12; neck-down track 597 mm in total (0.09 mm segments of wide nets near their pads, all DRC-clean).
- Q-3: forbidden-net track on In2 / In3 over the plates 117.3 mm; In4 gaps under it 4.35 mm, In1 0.71 mm (runs/w4/shield.json; q4 4.26 mm:
  PV_NODE 0.99, VBUS 1.57, VBAT_IC 0.75, VOUT_EN 0.59, I2C_SCL 0.19, NTC 0.17).

## 3. What closed the eleven exits (exitdiag.py on the 8L fan board, without and with neck-down; runs/diag d0 / d1 / d4)
| Connection | Pad | Closed by (no neck) | After Q-2 / Q-4 |
|---|---|---|---|
| VDD_1V8 1.43 | U7.23 | 0.3 mm class track cannot pass U7.22 / U7.24 (gap 0.2) + GND fan-out stub of U7.24 (0.21 mm) | open |
| VDD_1V8 2.92 | U7.14 | GND fan-out stub and via of U7.13 (0.18 / 0.20 mm) | open; neck fan-out via |
| NTC 3.84, 8.03 | Q10.3 | NTC_SENSE 0.20 clearance to Q10.1 / Q10.2, C111, C175 pads | open |
| GND 1.75 | U20.5 | X2SON centre VEE pad enclosed by 4 pads (0.16 / 0.26 mm gaps), no via in pad (0.03 mm clearance) | **still closed** |
| GND 2.06 | U19.5 | same as U20.5 | **still closed** |
| AVDD_ECG 0.8 | U7.29 | ECG class width / clearance between U7.28 / U7.30 | open |
| PV_SW 5.88 | U4.B2 | DSBGA centre ball: GND fan-out via of the neighbour ball (0.175 mm) | open |
| BATT_P 11.32 | U5.B2 | same as U4.B2 (GND via 0.175 mm) | open |
| SPI_SCK 9.5 | U7.20 | VDD_1V8 fan-out via + stub (0.22 / 0.30 mm), pads 19 / 21 | open |
| VBAT_IC 14.06 | – | not static (congestion) | congestion |

## 4. Engine changes (v3/grow8 only; v3/grow untouched)
- `tools/neck_areas.py` (new): NECK_k_AREA rule areas (one per piece, same name) + DRU rules "Q-2 neck clearance" (0.09 for a < 0.095 mm track
  enclosed by its net's area) and "Q-2 neck only at pads" (such a track of a wide net outside its area is disallowed; WLCSP courtyards exempt).
- `tools/maze_finish.py dump`: pad list with copper polygons. `tools/pfroute.py`: `neck` (radius from own pad copper, default off, evaluate
  passes 1.4), `shield` (layers open to forbidden nets over plates), neck legality 0.09 / 0.09 to all copper, per-step width output, neck_mm.
- `src/pf.c`: neck mask per net window; a step is narrow iff one end is in the zone; narrow nodes use class 0 occupancy and halo 0.095; path
  elements split at neck changes. Legalisation support check written but off (`-DLEGAL_SUPPORT=1`): it made q6 41 against q4 34.
- `tools/forb_dru.py shield()`, `tools/shield_check.py` (new), `tools/exitdiag.py` (new), `tools/halo_clean.py` (new).
- `tools/fanout_planes.py`: exit guard (reject a via / via-in-pad / stub that takes the last neck-track or via-in-pad exit of a neighbouring
  pad of another net; 1 rejection on this placement) and neck fan-out (0.09 stub, via <= 1.4 mm); FANOUT_OPTS to switch them off.
- `tools/evaluate.py`: keys `neck`, `shield`, `fanout`; score `shield`, `neck_mm`; fix: the .kicad_dru was truncated before being read.
- `tools/evolve.py`: RULES8 per candidate, halo gene + intrusion term (own decoupling = capacitors sharing a non-GND net with the nearest halo
  IC), base / seed from grow8, `--rules`, `--base-eval`, `--timeout`, wider pres0 / hist_inc ranges (w4 sat at the old hist bound 5.0).

## 5. Search validation (laptop, runs/val5_laptop; run from a bundle tree in the scratchpad)
- pop 5, gens 2, workers 1, 6 router iterations: gen 0 best 72 (median 80), gen 1 best 73 (median 78); every row legal, 0 DRC errors.
  Resume: the same command again logged 10, re-ran nothing. Only placement moves are rare (0-1 of 1-4 requested pass the legality and
  halo checks), as in the stopped 6-layer lane.

## 6. Bundle (v3/grow8/bundle, README.md in Chinese: three steps)
- Seed `tree/.../grow8/work/seed8` = runs/w4 (33 / 0). install.sh fetches only: apt build-essential python3-venv python3-pip
  software-properties-common tmux; KiCad 10.0.x from ppa:kicad/kicad-10.0-releases; PyPI numpy 2.5.4 scipy 1.18.1 shapely 2.2.0
  matplotlib 3.11.2 (Python 3.10 / 22.04: numpy 2.2.6 scipy 1.15.3 shapely 2.1.1 matplotlib 3.10.3, untested ⚠). C core built there with
  `cc -O3 -shared -fPIC` (no -march=native).
- Run: `bash run.sh` (WORKERS = physical cores - 2, at most one per 2 GB; POP = WORKERS; GENS 14; resume = same command);
  results: `bash run.sh pack` = one tar to ~/results_rent8.tgz.
- Rent: 64 physical cores, 128 GB, 100 GB disk, 10 h (868 evaluations at 15-40 min each ⚠ server-core factor, about 25-40 min per
  generation; GENS 14 about 6-9 h).

## 7. Verdict and open items
- Q-2 / Q-3 / Q-4 implemented: PASS. Q-6 search + bundle: PASS (local end-to-end). G-6 8-layer gate (0 / 0): **FAIL (33 / 0)**.
1. U19 / U20 (TLV7031, X2SON) centre VEE pad cannot be escaped under JLC rules: 2 unconnected on every board; needs a ruling (package).
2. In4 not solid under the shielded forbidden tracks: 4.35 mm of gaps (antipads); a ruling or a router rule (keep other-net vias out of the
   In4 strip under those tracks) is needed; SIM-07 (R-4) re-check on the final board still open.
3. RF_50R / ANT nets may neck too (ruling "any net"): the RF lane should check the feed (neck_mm in routes.json stats per net).
4. KiCad 10 PPA on 22.04 ❓; x86 core speed vs the laptop ⚠ (rent advice assumes 1.0-1.5x slower).
5. Placement-move success rate is low; the search mostly tunes router weights (w4-type changes gave -1..-8).
