# Placement gate prepared for ruling P-6 (LEAD_NOTES §2o), 2026-11-16

## 中文摘要
- 结论：PARTIAL。闸门已能一条命令达到 P-6 状态；干跑板上贴片闸门 **GREEN 192 / PREVIEW 15 / YELLOW 0 / RED 0 / UNKNOWN 0**（之前 145 / 0 / 47 / 11 / 4）。唯一挡住下单的是布线：77 处未连接。
- 极性件 pin map 逐个对照厂家数据手册（页码见 §2），标 `reviewed: independent-agent 2026-11-16`。都与板子一致；修了 C130414 的页码和位号，给 C6736531、C896422 补了 reference_pin。
- D16：手册 p.1“1 = CATHODE”，p.4 底视图 1 脚焊盘有倒角；EasyEDA 符号和丝印点都在 pad 1。名字里的“-RD”不是方向标记（库里 9 个 -RD 封装，pad 1 在 -X 的 6 个、在 +X 的 3 个），闸门不再把它当投票。
- SW1：C&K B-41 顶视图写明执行器在 ESD 脚 5 的对面；EasyEDA 的 pad 5 在 +X，执行器丝印在 -X，两个来源一致。另外 EasyEDA 的“1-2”排就是厂家的“3-4”排，开关是 SPST，电气上没有影响。
- J40：EasyEDA C2826518 已取到，焊盘 2.10×1.50 与板上焊盘逐个相同。D12：EasyEDA 再次返回 404，改用标明为代理的 C549275 焊盘，D12 留在预览清单。
- 新工具 `tools/add_silk_marks.py`：在板子副本上给 57 个 IC 和极性件加 1 脚点或阴极条（线宽 0.15 mm），57 个全部放下，DRC 没有新增问题。新增 R4b 检查：每个板上标记与 JLC 自己封装上的标记都指向同一个焊盘，57/57 一致。
- `make_package.sh` 加了第 0 步（加丝印）；支持 8 层板（In5/In6，已在 8 层副本上测试）；新状态 PREVIEW 每行都带“在 JLC 预览里看什么”和对应的电测项目。
- 还要用户做的：在 JLC 预览中逐行核对 15 行 PREVIEW（账户操作）。另有几项要注意：D14 的 -Q 版手册没有找到 ❓；D3/D4 的焊盘视图没有标注是底视图 ⚠；EasyEDA 数据新鲜度（72 h）的检查还没做 ❓。

## 1. What changed (backups of every changed file: `backup_gateprep/`)
| File | Change |
|---|---|
| `preview_rules.yaml` (new) | Ruling P-6 written down. A row is allowed to become PREVIEW only for its own ref + C-number, and only when **all** of its red reasons match the entry; YELLOW is never moved. Each entry carries a `look` item. This is not a waiver (`waivers.yaml` stays empty). |
| `tools/cplgate.py` | New state PREVIEW (GREEN only with no preview item; shippable = GREEN + PREVIEW and no board RED). G3: a pin map marked `reviewed: independent-agent` with date, source and comparison is accepted, and the row becomes PREVIEW (the human check is its preview row). G5: the `-RD`/`-FD` token is recorded, not voted; the EasyEDA pin-1 dot now votes for cathode-referenced 2-pad parts; an actuator vote is added for mechanical parts (pin map `actuator.opposite_easyeda_pad`). G4: EasyEDA pads that `easyeda_rev_manifest.json` deletes with a datasheet reason become a note (SW1 pad 5, review D-9). G2: a labelled proxy footprint gives a `PROXY:` red reason. **R4b** (new): the board silk mark and JLC's footprint mark must sit at the same pad, otherwise RED. Writes `PREVIEW_CHECKS.md` (rows, look item, electrical test from `placement_proof.json`). |
| `tools/add_silk_marks.py` (new) | Adds marks as footprint graphics on F/B.SilkS: a cathode bar (2-pad polarised parts) or a dot (outer diameter 0.25 mm), line width 0.15 mm. Clearances: pad 0.15 mm, other silk 0.15 mm, via 0.10 mm, board edge 0.30 mm. The mark sits within 1.5 mm of the reference pad and nearer to it than to any other pad, outside other parts' courtyards. Parts with no legal spot are reported, never forced. Runs KiCad DRC before and after (all severities) and exits 1 if the board got worse. |
| `make_package.sh` | Step 0: silk marks on `OUT/board/<name>_silk.kicad_pcb`, and every later step uses that copy (`SILK=0` skips the step). The copper layer list is read from the board (6 or 8 layers). The upload set includes `PREVIEW_CHECKS.md`, and the final log line says "ORDERABLE after N JLC preview checks". |
| `tools/fab_info.py` | Layer count from the board; an 8-layer role table (P-5: GND In1, VDD_1V8 In4, signals F/In2/In3/In5/In6/B); the README carries the 8-layer thickness ❓ note. |
| `tools/mutate.py`, `summary.py`, `review_pics.py`, `render_gate.py` | Know PREVIEW. M1 skips the single-land rows (UNKNOWN or PREVIEW-by-P-6). Summary shows the PREVIEW count and list. |
| `tools/pinmap_review_20261116.py` (new, run once) | Wrote the reviews below into `v3/design/pinmap/*.yaml`. |
| `v3/design/pinmap/` | 8 files reviewed (below), plus `C2826518.yaml` (new, J40). |
| `v3/design/lib/` | `easyeda.pretty/C2826518_ANT-SMD_L3.5-W1.5.kicad_mod` + symbol (fetched); `easyeda.pretty/C549313_PROXY-C549275_…kicad_mod` (labelled copy with a `Proxy` property); `easyeda_index.json` entries for both. |

## 2. Pin-map review (independent, hostile; all URLs read 2026-11-16)
| C-number (refs) | Maker source, page | Result |
|---|---|---|
| C5603826 (D3, D4) | ams-OSRAM CT DBLP31.12 v1.3, look.ams-osram.com/m/7737569ee6f0cd0e/original/CT-DBLP31-12.pdf, p.11 pad view (leaders "anode" / "cathode"), p.12 | Agrees: pad 1 = anode (small land, left, small lands at the top). ⚠ The p.11 view is not labelled; it is read as a bottom view. EasyEDA symbol (pin 1 "+") and dot agree. |
| C511402 (PD1) | Vishay VEMD8080 Rev 1.1, vishay.com/docs/84565/vemd8080.pdf, p.4 "Pinning top view" | Agrees: pin 5 anode diagonal to pin 1. EasyEDA is the top view turned 180°, not mirrored. |
| C130414 (D9, D11) | Nexperia BAS521 (1 Jul 2023), Table 2 p.1: 1 K, 2 A. LCSC and Nexperia were not reachable online, so the project copy of the recorded URL was read (same sha256); online cross-check with BAS521B | Agrees. **Fixed:** outline p.6 → 5, footprint p.7 → 6; refs now name D11. |
| C598214 (D10) | Kingbright DSAK2457 V.7A, p.1 symbol: bar at terminal 1 | Agrees. The lens side is a preview item. |
| C6736531 (D14) | Nexperia PMEG10020AELR (1 Jan 2023), Table 2 p.1 (1 K; the bar marks the cathode), Fig. 16 p.9, Fig. 17 p.10 | Agrees for the type. ❓ This is the non-Q data sheet (URL productCode=C552793); no -Q data sheet was reachable. **Fixed:** reference K / pin 1 added. |
| C896422 (D16) | onsemi NSR0240MX2/D Rev 3, p.1 (1 CATHODE), p.4 case 714AB (chamfered pin-1 pad, pin-1 indicator) | Agrees; contradiction resolved (cathode = pad 1, EasyEDA +X). **Fixed:** reference K / pin 1 added. |
| C549313 (D12) | Nexperia BAV70M (1 Jul 2022), Table 2 p.2 | Agrees: 1 A1, 2 A2, 3 CC. The board land is the top view turned 90°, not mirrored. |
| C221907 (SW1) | C&K PTS840 B-41 (p.2) top view and layout | Agrees electrically. Pad numbering is swapped by row against the maker's (harmless, SPST). The actuator side has two sources. |
Every reviewed pin map was also compared with the KiCad pad numbers on the board (`easyeda_rev`, copper numbering unchanged), the EasyEDA footprint and symbol, and the netlist nets. No pin map was wrong in its pin identities.

## 3. Results on the dry-run board (`dryrun_p6/`, board sha256 6a20c2be… → silk copy 49bce14a…; ✅ this run)
| Item | Before (`dryrun/`) | After (`dryrun_p6/`) |
|---|---|---|
| Gate GREEN / PREVIEW / YELLOW / RED / UNKNOWN | 145 / – / 47 / 11 / 4 | **192 / 15 / 0 / 0 / 0**; board-level RED 0 |
| Silk marks | 0 | 57/57 placed, 0 not placed, DRC new violations: none; R4b 57/57 same pad as JLC's mark |
| G7 closed loop | 205/205 | 207/207 (D12 and J40 now have CPL rows) |
| G8 | PASS | PASS: M1 1212/1212, M2 49 caught + 8 exempt, M3 56/56, M4 7/7 |
| R4b negative test | – | Moving D16's bar to pad 2 on a board copy turns D16 RED ("board mark at pad 2, JLC mark at pad 1") ✅ |
| 8-layer copy (In5/In6 added) | not handled | 8 copper Gerbers (g1–g6), README "Layers 8", gate and G7/G8 unchanged ✅ |
| Orderable | NO | **NO: DRC 0 errors, 77 unconnected** (the only blocker) |

PREVIEW rows (look item and test: `dryrun_p6/gate/PREVIEW_CHECKS.md`): D3, D4, PD1 (bottom side, D_b); J11, J15, J18, J19, J40 (single-pad fingers; J40 at 340°); D12 (proxy land, no JLC data); SW1 (actuator); D9, D10, D11, D14, D16 (polarised; the human pin-map check moved to the preview).

## 4. Still open / blocks
1. Routing: 77 unconnected (grow / plan-B lane). Then: `./make_package.sh <routed>.kicad_pcb out_<rev>`.
2. The user: tick the 15 PREVIEW rows in JLC's preview before payment (an account action, not done here).
3. ❓ G2 freshness (EasyEDA fetch under 72 h, Classic ↔ Pro) is still not enforced by the gate (PACKAGE.md open item 7). Today's fetch covers only C2826518.
4. ❓ D14: the PMEG10020AELR-Q data sheet itself was not found. ⚠ D3/D4: the OSRAM pad view is unlabelled. Both rows are PREVIEW with an electrical test.
5. The pin-map YAMLs were edited directly. `v3/design/tools/write_pinmaps.py` would overwrite the reviews from `pinmap_data*.py`: port them before any regeneration.
6. Gerber names now carry `_silk` (the board copy's name). The zip name is unchanged.
7. Low stock as before (BQ25170 and C23733 show 0 orderable); JLC 8-layer at 1.0 mm ❓ (P-5).
