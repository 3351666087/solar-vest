# V3-F production package, dry run (ruling G-7), 2026-11-16

## 中文摘要
- 一条命令 `v3/package/make_package.sh BOARD OUTDIR` 生成全部生产文件；在当前板（77 处未布通）上跑通，用时约 11 秒，CPU 负担很小。
- Gerber + 钻孔：13 层 + PTH/NPTH，打包成 zip；板框 40.0 × 31.0 mm 闭合，含 Ø8.6 mm 电机开孔；466 个过孔，其中 212 个在焊盘内（树脂塞孔+电镀盖帽说明已写入制板 README）。
- DRC：0 错误，77 处未连接，所以判定**不可下单**（已知，最终板替换后重跑同一命令）。
- BOM：91 行 / 207 个贴片，逐行与 `v3/design/BOM_v3f.csv`、BOM_full 和板子核对 **PASS**；不贴 8、手工装 9、纯铜 27；Basic 7 / Extended 84；低库存 4 行。
- 贴片闸门（cplgate）：GREEN 145，YELLOW 47，RED 11，UNKNOWN 4，所以**不是 GREEN**，按规则不写上传文件夹。
- YELLOW 47 个都只有一个原因：板上没有丝印极性/1 脚标记（布局工具把丝印移到了 Fab 层）。
- RED 原因：8 个极性件的 pin map 还没有人工复核；3 个底面件没有底面 canary 校验；D12、J40 在 lib 里没有 EasyEDA 封装（J40 还是 340°）；D16 的 EasyEDA 数据自相矛盾；SW1 的 1 脚只有一个来源。
- UNKNOWN 4 个：J11/J15/J18/J19 单焊盘弹片，几何上无法区分 0° 和 180°。
- 独立闭环核对 G7：205/205 通过（CPL 位姿对 Gerber 铜和锡膏，按焊盘编号逐个比）。
- 变异测试 G8 全部 PASS：1206/1206 个 CPL 变异被抓到；48/48 个焊盘编号置换被抓到；54/54 个错封装被抓到；在板子副本上转 7 个件，旧 CPL 正好在这 7 个件上失败，新 CPL 全部通过。
- 需要用户或 lead 决定的事见“Open items”第 2–7 条。

## How to run
```
cd /path/to/SolarVest_work/wristband/v3/package
./make_package.sh ../layout/kicad/solarband_v3f_main.kicad_pcb dryrun     # exit 0 = orderable, 1 = not
```
Environment: `PY` (default: the project venv) and `KICAD_CLI` (default: kicad-cli 10.0.7). It works offline and reads `v3/design` (BOMs, netlist, `lib/easyeda.pretty`, `lib/easyeda.kicad_sym`, `easyeda_index.json`, `pinmap/`, `placement_proof.json`, `stock_report.md`). Waivers live in `waivers.yaml`; none are granted.

## Outputs (OUTDIR = `dryrun/`)
| Path | Content |
|---|---|
| `fab/<board>_gerbers_JLC.zip` | 6 copper layers, mask, paste, silk and Edge.Cuts as Protel-named files, plus PTH and NPTH Excellon (mm, decimal), all on the place origin. Drill maps are in `fab/drill_maps`, outside the zip. |
| `fab/README_FAB.md`, `fab_info.json`, `drc.json` | Order parameters: 6 layers, 1.0 mm, stack-up, ENIG, via-in-pad filled and capped, minimum via and track, outline with the cut-out, layer map, DRC. |
| `assembly/BOM_JLC.csv` | JLC upload format: Comment, Designator, Footprint, LCSC Part #. |
| `assembly/BOM_not_fitted.csv`, `BOM_hand_fitted.csv`, `BOM_copper_only.csv`, `bom_check.json` | The other part classes, and the line-by-line check. |
| `gate/cplgate_report.md`, `cpl_provenance.json` | The verdict for each part, with θ, rms, margin, symmetry order, votes, reasons and hashes. |
| `gate/candidate_NOT_FOR_UPLOAD/CPL_JLC.csv` | The CPL the gate derived. It goes to `upload/` only when every check passes. |
| `gate/g7.json`, `gate/mutation_report.json`, `gate/overlays/*.svg` + `index.html` | G7, G8, and the G9 review overlays (one per part, grouped by risk). |
| `review/placement_top.png`, `placement_bottom.png`, `checklist.md/.csv` | Placement-review pictures, and the order-time checklist with 62 rows. |
| `summary.md`, `summary.json`, `make_package.log` | Counts, verdicts and exit codes. |
| `upload/` (+ `manifest.sha256`) | Written only when the run is orderable. It is absent in this run. |

## Results on the dry-run board (sha256 6a20c2be4cc1…; all figures ✅ from this run's tools)
| Item | Verdict | Numbers |
|---|---|---|
| 1. Gerbers, drill, zip, fab README | PASS (output) / board FAIL | 15 files in the zip. Outline 40.0 × 31.0 mm, closed. Motor cut-out Ø8.6 mm centred at (34.25, 24.05). 466 vias, 212 of them in SMD pads. Minimum via 0.15 / 0.25 mm, minimum track 0.09 mm. **DRC 0 errors, 77 unconnected** → not fit to order (known). |
| 2. BOM | PASS | 91 lines, 207 placements. Each line agrees with BOM_v3f.csv, BOM_full_v3f.csv and the board (footprint, side, DNP). Not fitted 8, hand-fitted 9, copper-only 27. The §2b/§2f–2j ECO values are already in BOM_v3f.csv ✅: R172 53.6 k, R105 383 k, Q20 C504101, J40 C2826518, C215 C6652901, L204 C668465. |
| 3. CPL gate | FAIL (not GREEN) | 205 CPL rows of 207 (top 202, bottom 3). GREEN 145, YELLOW 47, RED 11, UNKNOWN 4. Board-level RED 0. G1: the parser matches the kicad-cli pos export for all 207 parts. Every θ = 0: each board land is its C-number's own EasyEDA land. |
| 3. G7 closed loop | PASS | 205/205. Each EasyEDA pad, placed at the CPL pose, overlaps the X2 Gerber flash of the same designator and pin by ≥ 50 %. The part centre is within 0.3 × the smallest pad. Paste is present. This includes the 3 bottom parts under convention D_b. |
| 3. G8 mutations | PASS | M1: 1206/1206 CPL mutations caught (±90/180/270, layer, 0.6 × pad shift in x and in y). M2: 48/48 pad-number permutations caught; 8 are exempt as allowed modulo-180 cases. M3: 54/54 wrong-package substitutions caught, 42 of them by geometry and 12 only by the G2 binding check. M4: U1 +90, U7 +180, D9 +180, Q20 +90, U21 +270, C101 +180 and J13 +180 turned on a board copy. The old CPL fails G7 on exactly these 7. The regenerated CPL passes. |
| 4. Review pictures + checklist | PASS (output) | 62 rows: RED 11, UNKNOWN 4, YELLOW 47, GREEN 0. Each row gives the class, gate verdict, CPL rotation, the mark and its direction in board view, the deciding evidence and the G10/EOL test. |
| 5. Summary | PASS (output) | Low stock: C23733 (C121, C209) orderable 0; INA236 C4371025 (U4, U5) 48; MAX86141 C5328762 (U8) 43; BQ25170 C5208201 (U15) 0. |

### Why the gate is not GREEN (part by part)
- **RED, pin map not human-reviewed (G3 makes this mandatory for polarised parts):** D3, D4, PD1, D9, D11, D10, D14 and D16. They use 6 yaml files: C5603826, C511402, C130414, C598214, C6736531 and C896422.
- **RED, bottom side without a canary (R3):** D3, D4 and PD1. The CPL rotation follows convention D_b (defined in `tools/g7_verify.py`), which is self-consistent in G7 but unverified at JLC ❓.
- **RED, no EasyEDA footprint in `v3/design/lib`, so nothing was fetched (R8/G2):** D12 C549313 (EasyEDA record 404 at design time) and J40 C2826518 (lib has only C2826516's land). J40 is also at 340° (R7).
- **RED, D16 C896422:** the EasyEDA data contradicts itself. The symbol says pad 1 = cathode, the pin map agrees, but the package token `-RD` puts the band at the other pad (pad 1 sits at +X). The JLC preview decides.
- **RED, SW1 C221907:** the copper is 2-fold symmetric and pin 1 has only one source (the silk dot). EasyEDA pad 5 (ESD pin) was deleted in review D-9. The actuator side needs a preview and a waiver.
- **UNKNOWN, J11, J15, J18 and J19 (C2826535, one land each):** geometry cannot tell 0° from 180°. The contact tip sits 0.6–0.8 mm off the pad centre, so the direction matters.
- **YELLOW ×47 (and also on most RED parts), R4:** no silk polarity or pin-1 mark within 1.5 mm of the reference pad. The cause is `v3/layout/tools/build_board.py` (around line 217), which moves all footprint silk to F.Fab/B.Fab. The Gerber silk layers carry no part marks, and G7 finds 0 of 205 JLC pin-1 marks over board silk.

## Open items (owner)
1. **Routing:** 77 unconnected items (grow / plan-B lane). When the routed board exists, run the same command on it.
2. **Silkscreen (layout lane or lead):** keep a pin-1 / cathode mark ≥ 0.15 mm wide, clear of copper, on every polarised part and IC. The alternative is a lead waiver of R4 for all 56 parts flagged. JLC follows the silk when silk and CPL disagree.
3. **User:** mark the 6 pin maps above `reviewed: human` after checking each against its datasheet figure.
4. **Lead / user, bottom parts D3, D4, PD1:** choose one. (a) A 4-part bottom canary through a JLC preview upload (an account action the user takes). (b) Hand-place these 3 parts. (c) Accept the parts with a preview check and a waiver.
5. **D12 and J40:** fetch the C549313 and C2826518 EasyEDA records with `v3/design/tools/fetch_easyeda.py` (a download, not done here). Otherwise use a JLC preview plus a waiver. J40 at 340° needs an R7 waiver.
6. **J11/J15/J18/J19, SW1, D16:** check in the JLC preview, then the user adds waivers to `waivers.yaml`.
7. **Before an order:** G2 freshness (an EasyEDA fetch under 72 h old, Classic ↔ Pro cross-check) is not done offline ❓. The fab items marked ⚠ need confirming in the order form: the stack-up choice, ENIG, copper weights, and JLC accepting the Protel names. The JLC capability figures come from the board's `.kicad_dru` (read 2026-11-12). Low stock: 4 lines; BQ25170 and C23733 show 0 orderable.
8. **Board files carry no LCSC field and no pin functions (R1 / R2):** the gate takes them from BOM_full and the netlist instead. Pad nets agree with the netlist, except U10.7 → TMP117_ISLAND, which is deliberate (R-5).

## Method notes
- The gate follows research/cpl-placement-gate.md §0 and §6. The research/cpl-gate-prototype (fit, symmetry) and v3/design/tools/kisexp.py are reused. There was no earlier `cplgate` or `jlcfootprint` implementation in the work tree; only the prototype and the design-lane audit tools exist.
- G7 is written independently. It has its own Gerber X2 reader (apertures, macros, regions, clear polarity) and its own EasyEDA reader (custom pads included), and it reads only the emitted files.
- Custom-shaped pads (17 on the board; X2SON and UDFN) use their primitive outlines in both modules.
