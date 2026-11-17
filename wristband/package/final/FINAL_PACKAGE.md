# SolarBand V3-F final production package (2026-11-16)


## Update 2026-11-16 19:50 UTC (R-172): R172 replaced; this block wins over the text below
- **R172 53.6k 0201 1 %: C423488 0201WMF5362TEE (stock 0) -> C166160 RALEC RTT015362FTH** (JLC API 19:41 UTC: 53.6 kΩ, 0201, ±1 %, ±200 ppm, stock 38 487, orderable 38 325). Other candidates the same day: C320952 10 882, C474764 3 016 orderable.
- EasyEDA footprint C166160_R0201 fetched with `tools/fetch_easyeda.py` (JSON API only, no 3D model): pads identical to C423488_R0201; the reviewed copies differ only in the name.
- Board copy `v3/final/board/solarband_v3f_final_rf.kicad_pcb`: only R172's footprint ID and Value text changed (backup `solarband_v3f_final_rf.pre_r172.kicad_pcb.bak`); DRC 0 errors / 0 unconnected (`drc_r172.json`, --refill-zones --severity-error).
- `STOCK=1 ./make_package.sh ../final/board/solarband_v3f_final_rf.kicad_pcb final` -> **exit 0**: GREEN 192, PREVIEW 15, RED 0; G7 207/207; G8 PASS; BOM 91 lines / 207 placements, fails 0, value diffs C203 only. CPL and all 17 Gerber/drill files identical to the 19:33 run (metadata lines excluded).
- Stock 19:44 UTC: no zero-stock line except **U15 C5208201 (orderable 0, B-1)**; U4/U5 C4371025 orderable 54 (B-1); C166160 38 325, C2048575 6 810, C471381 21 321.
- Previous package: `v3/package/backup_final_pre_r172_20261116/`.

## Update 2026-11-16 19:33 UTC (final lane, `v3/final/PROGRESS.md`): RF re-tune applied; this block wins over the text below
- BOM change from `v3/sim/rf/final/RF_FINAL.md`: **C215 9.0 nH C6652901 -> 7.6 nH LQW15AN7N6G80D C2048575**; **L204 6.2 nH C668465 -> 4.3 nH LQW15AN4N3B80D C471381**; C213 stays not fitted (bench-tune land). Applied in `v3/design` (catalog.py, mcu_rf.py + land/height/audit rows); run_all.sh rc 0, ERC 0 errors x 11, netlist cross-check 0 differences x 11.
- Board used: `v3/final/board/solarband_v3f_final_rf.kicad_pcb` = the closed board with **only** the two footprint IDs and Value texts of C215/L204 changed (pads, courtyards, copper unchanged: the old and new rev lands are both 0.41 x 0.66 at +-0.505). DRC 0 errors / 0 unconnected (--refill-zones, board rules incl. P-7). All 18 Gerber/drill files identical to the 19:15 run (metadata lines excluded); CPL identical.
- `STOCK=1 ./make_package.sh ../final/board/solarband_v3f_final_rf.kicad_pcb final` -> **exit 0**: GREEN 192, PREVIEW 15, YELLOW 0, RED 0, UNKNOWN 0; G7 207/207; G8 PASS; BOM 91 lines / 207 placements; value differences: C203 only (truncated text).
- Upload zip is now `upload/solarband_v3f_final_rf_gerbers_JLC.zip`. Stock 19:28 UTC: C2048575 6 846, C471381 21 380; R172 C423488 still 0, U15 C5208201 orderable 0, U4/U5 orderable 54 (unchanged).
- Previous package: `v3/package/backup_final_pre_rf_20261116/`.

## 中文摘要
- 板子 `v3/finish/solarband_v3f_final.kicad_pcb` 未被修改；`make_package.sh` 只在副本上加丝印标记（57/57），副本 DRC：0 错误、0 未连接（--refill-zones，板子自带 .kicad_dru，含 P-7 例外规则）。
- 贴片闸门：**GREEN 192，PREVIEW 15，YELLOW 0，RED 0，UNKNOWN 0**；G7 207/207 通过；G8 M1–M4 全部 PASS；退出码 0，upload 文件夹已生成。
- PREVIEW 15 行（付款前在 JLC 预览里人工看）：D3、D4、PD1（底面）；D9、D10、D11、D14、D16（极性件，独立代理复核过 pin map）；D12（C549313 用代理封装）；J11、J15、J18、J19、J40（单焊盘弹片，J40 340°）；SW1（按键方向）。
- 8 层、40 × 34 mm、Ø8.6 mm 电机开孔、508 过孔（220 个在焊盘内）都被工具正确处理；U19/U20 SC70（C2863637）GREEN（1F 类）。
- BOM：91 行 / 207 个贴片（顶面 204，底面 3）；Basic 7 / Extended 84；不贴 8、手工装 9、纯铜 27。板上 242 个封装：顶面 232，底面 10。
- 设计值与板值：R172 53.6k、R105 383k、Q20 CJBA7002K、J40 BW0020AG（C2826518）、C215 9.0 nH、L204 6.2 nH、C213 不贴，板与设计一致。唯一差异 C203 的 Value 文本被截断（缺尾字母 "D"），BOM 用设计值。
- **今天的库存问题（JLC 公开 API，19:11 UTC）**：R172 C423488 库存 **0**（订不到）；U15 BQ25170DSGR 可订 **0**（库存 128，canPresale −88）；U4/U5 INA236 可订 54（< 10 板需求 20 的 5 倍）。下单前必须先解决 R172 和 U15。
- 修过的东西：ECO3 重新生成 pin map 时把 P-6 的独立复核抹掉了，已用 `tools/pinmap_review_20261116.py` 重新写回（8 个文件，与 eco3 备份一致）；cplgate 加了别名 VEE/V- = GND；丝印工具给 Q5 加了回退位置；预览计数少算了表头；BOM 加了板值比对；加了可选的库存步骤（STOCK=1）。
- 结论：**PARTIAL**。文件齐全、闸门达标，但 R172 和 U15 今天订不到，P-3 的天线匹配重调和 8 层 1.0 mm 能否生产（P-5）也还没落实。

## Gate counts
GREEN 192, PREVIEW 15, YELLOW 0, RED 0, UNKNOWN 0; board-level RED 0. G7 closed loop 207/207. G8: M1 CPL mutations, M2 pad-number permutation, M3 wrong package and M4 turned board copy all PASS.
Before the fixes the first run gave GREEN 189, RED 11, PREVIEW 6, YELLOW 1. The causes were the lost pin-map reviews (8 RED), VEE vs GND on U19/U20 (2 RED), SW1 (1 RED, the review restores the second actuator source) and Q5 with no silk mark (YELLOW).

## Changes made (no board edit, no CPL edit)
| File | Change |
|---|---|
| v3/design/pinmap/{C5603826,C511402,C130414,C598214,C6736531,C896422,C549313,C221907}.yaml | P-6 review blocks rewritten by the existing script. The ECO3 run of write_pinmaps.py (14:12) had wiped them. Backup of the pre-fix state: `package/backup_final/pinmap/`. Still open: port the reviews into `pinmap_data*.py` |
| package/tools/cplgate.py | ALIAS gains VEE→GND and V-→GND (the negative-rail pin of single-supply comparators: TI "V-", EasyEDA "GND") |
| package/tools/add_silk_marks.py | Fallback for when nothing fits: a mark may enter a neighbour's courtyard margin but keeps ≥ 0.05 mm from that neighbour's body (its Fab hull). It was used once, for Q5 at (123.20, 99.53). DRC was not made worse |
| package/tools/bom_jlc.py | Checks the board Value against BOM_full and reports differences (`value_diffs`). The design value is used. This never fails the run |
| package/tools/stock_today.py (new), make_package.sh | Optional step 3b with STOCK=1 (read-only public API); the preview count no longer counts the table header |
Backups of the changed tools are in `package/backup_final/tools/`.

## Stock problems today (assembly/stock_today.md, 2026-11-16 19:11 UTC, 91/91 answered)
| Part | Refs | Orderable | Note |
|---|---|---|---|
| C423488 53.6k 0201 | R172 | 0 (stock 0) | Same value, 0201, 1 % parts in stock today: C166160 RTT015362FTH (38 k), C320952 (10.8 k), C474764 Yageo RC0201FR-0753K6L (3.0 k). Not applied: the design lane changes BOM_v3f |
| C5208201 BQ25170DSGR | U15 | 0 (stock 128, canPresale −88) | Charger: no drop-in substitute was searched. Needs a decision or JLC's BOM tool (an account action, not taken) |
| C4371025 INA236AIYBJR | U4, U5 | 54 | Enough for 10 boards (20) but below the 5× rule |
stock_report.md (older) also flagged C23733 and C5328762; today both are fine (199 695 and 138).

## Other open items
1. P-3: the antenna match (C213/C215/L204) is still the L-3 set (9.0 / 6.2 nH, C213 not fitted). The RF re-tune for the final feed distances was not run. The BOM uses the design values.
2. P-5: 8 layers at 1.0 mm is not confirmed by JLC ❓ (README_FAB says so).
3. ECO3 asks for an extra look at the U19/U20 pin-1 mark in the preview. The gate rates them GREEN (1F) and they are not a PREVIEW row.
4. 103 SMD footprints carry `attr through_hole` on the board, as they already did in the layout board. They are in the CPL (G7 207/207); this is cosmetic.
5. The 15 PREVIEW rows and `review/checklist.md` (62 rows) must be ticked in JLC's preview before any payment.

## Files (v3/package/final)
- `upload/`: Gerber zip, BOM_JLC.csv (91 lines), CPL_JLC.csv (207 rows), PREVIEW_CHECKS.md, manifest.sha256
- `fab/`: README_FAB.md, fab_info.json, drc.json, drill_maps/. `assembly/`: BOM_JLC, not-fitted, hand-fitted and copper-only lists, bom_check.json, stock_today.{md,json}
- `gate/`: cplgate_report.md, g7.json, mutation_report.json, overlays/. `review/`: placement_top.png, placement_bottom.png, checklist.md/.csv. `silk/`: silk_marks.md
- `summary.md`, `make_package.log`, `final_package.json`. Command: `STOCK=1 ./make_package.sh ../finish/solarband_v3f_final.kicad_pcb final` (exit 0)
