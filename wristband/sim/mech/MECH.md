# V3-G7 / SIM-14 mechanical: calculation part (41 × 34 pod, stage 2a)

**中文摘要**
- **阶段 2b 复算（2026-11-15，`mech_s2b.py`）：门 V3-G7（计算部分）PARTIAL。** 7 项 PASS，2 项 PARTIAL：
  (2) 窗玻璃：不锈钢导轨段 14.0 / 5.89 bar PASS；天线 5 mm 缓冲区内（X < 11.5）导轨仍为 GF-LCP（金属规则），中跨保守估算 7.95 / 3.35 bar，最坏间隙不到 5 bar；该段导轨柱距改为 2 mm 时 14.0 / 5.89 bar。
  (6) 跌落：吊舱 CAD 质量升到 10.49 g 后护角需 0.34 mm，0.33 mm 在 30° 时差 0.005 mm；胶囊角按吊舱质量仍如前，台架决定。
- 其余：PV 层压板结构胶 32.5 / 27.0 bar；胶囊顶 0.50 为 8.63 bar；公差链全部 WC ≥ 0（W1 +0.08，W2 +0.02）。
- 以下为阶段 2a 原文（"before"）。
- 门 V3-G7（计算部分）结论：**FAIL**。9 项中 4 项 PASS、1 项 PARTIAL、4 项 FAIL。台架试验归制造商（见文末清单）。
- 安全系数：5 bar 工况按压力取 SF 1.5（最大实体间隙下接触压力 ≥ 7.5 bar），并且在第 5 项的最坏情况间隙下 ≥ 5.0 bar；30 N 工况按力取 SF 1.5（≥ 45 N）。
- 工况 1（PV 层压玻璃）：现状（0.50 mm、弹性胶条）2.31 bar，FAIL。弹性胶条在 5 bar 下压缩约 0.26 mm，是主要原因。**决定：必须用结构胶粘接**（环和肋两侧）；只加厚到 0.55 / 0.60 mm 不行，因为 PV 列最坏情况间隙是 0.00 mm。最小修改：粘接 + PV 座抬高 0.14 mm，玻璃保持 0.50（PV 半高 4.79 ≤ 5.305）→ 11.1 / 5.37 bar。
- 工况 2（窗玻璃 0.70）：3.63 bar，FAIL；W1 最坏间隙 −0.10 mm。主导项是 GF-LCP 导轨在柱间的下垂（5 bar 时 0.074 mm），不是粘接；0.80 mm 玻璃只有 4.39 bar。最小修改：导轨加不锈钢芯 + W1 链精密公差 + 窗座抬高 0.09 mm（窗半高 5.395）。
- 工况 3：30 N（铺开 / 15 mm 拇指 / 5 mm 探头）PASS（碰电芯需 180 / 87 / 45.5 N）；5 bar 4.42 bar，FAIL → 顶玻璃 0.50 mm（8.63 bar，胶囊 4.6 mm）。
- 工况 4：电机像一个刚性凸台，地膜只升 0.003–0.006 mm，PASS，不需要钛片；按键膜 2.8 N > 2.2 N，3.9 bar 以上按键被按住（BASELINE 固件规则已接受），PASS。
- 工况 5：W1（膜到面板）、W2（ZIF 到面板）最坏情况干涉，FAIL；其余链 PASS。P1 最坏情况余量正好 0.00。
- 工况 6：直边跌落时 PC 唇边先吸能；R6 角跌落时玻璃边会被碰到，PARTIAL → 角部护角凸起 0.33 mm。工况 7：铰链柔性板 PASS。
- 0.50 mm PV 玻璃在 5 bar 粘接状态下应力约 150 MPa：层压玻璃必须是化学强化玻璃（RFQ 写明）❓。

## 中文摘要（阶段 2d 复核，2026-11-15，43 × 34）
- 跨度变长（PV 36.5 × 12.5、窗口 39.0 × 15.3）：PV 32.2 / 21.4 bar、窗口 13.9 / 5.84 bar，均 PASS。导轨脚 X4 移到 3.5（K-5）后 GF-LCP 段最大柱距 2.5 mm：12.8 / 5.41 bar，挠度 0.010 mm，PASS。
- 公差链全部 WC 通过（P1 0.595：PV 半区零件 1.20；P2 0.665：电机站在膜上）。第 6 行仍 PARTIAL：吊舱变重，护角 0.34 在 30° 余量 −0.001（CAD 10.75 g）/ −0.012 mm（计算 11.26 g），需 0.35 mm。脚本 mech_s2d.py → mech_raw_s2d.json。

## 中文摘要（mini-ECO 复核，2026-11-15）
- F-4：天线缓冲区内 GF-LCP 导轨段柱距改 2 mm（X 2、4、6、8、10、12）：7.95 / 3.35 → 13.99 / 5.89 bar，第 2 行 PASS。
- F-5：护角 0.34 mm：吊舱质量下 R6 角余量 +0.004…+0.137 mm（原 −0.005），窗角不再被撞；胶囊角（吊舱质量）0.819 > 0.707 mm 不变，第 6 行仍 PARTIAL。
- V3-G7：PASS 8、PARTIAL 1（第 6 行）。脚本 mech_mini.py → mech_raw_mini.json；make_results_mini.py → mech_results.json "after_mini"。

## Method (all ⚠ model output unless marked)

- Geometry: `geom_v3f` (read-only) with `V3F_POD_W=34`, `V3F_OPT=fpc=dwg,fold=1.9,joint=zif,raise=0.15` (tag `L41W34_fold1p9_fpcdwg_jointzif_raise0p15`) ✅.
- Plates: Navier SS series (copied from `decide/calc`), extended to a centred patch load. Check: 28.7 × 12.6 / 0.50 / 0.15 gap gives 4.15 bar ✅ (LEAD_NOTES §2f); 36.0 × 14.6 / 0.70 / 0.10 gives 4.05 bar ✅ (stage 1).
- Real supports: a new strip FE across the short span (`mech_v3f.py`), with both glasses on one shared rib body. It includes the rib insert (now 0.5 × 0.905 after the raise) on posts every 6.0 mm, as a vertical spring (353 N/mm²) and a twist spring (408 N·mm/rad/mm); the LCP rail on posts every 4.0 mm (75 N/mm²); the bead or bond over each bearing width (elastic bead E 3 MPa ⚠, shape factor included: 53 N/mm³; epoxy 2.5 GPa); and the window frame bonded under the glass (composite section). The elastic part is scaled to 2-D with the Navier/strip ratio. For the verdicts the bonded seats get no rotation credit (`bond_pin`).
- Stack: `sim14_stack.chain()` (WC, RSS, MC uniform). Tolerances are the BASELINE §8 list values; the rest are marked in `mech_raw.json → stack.*.terms`.
- Drop: impact energy m g h (capsule 2.75 g / pod 10.21 g / whole band 20.39 g, CAD ✅). It goes into PC lip crush at a flow pressure of 100 MPa ⚠, for a straight edge (29 mm) or the R6 / R1 plan corner, and is compared with the glass-edge clearance `setback × sin θ` for θ = 30–75°.
- Hinge flex: tilts 43.9–69.9° on 130–200 mm wrists ✅ (worn json); hinge 2 mm long, moulded at the middle angle 56.9° ⚠. The 0.07 mm flex bends about its own axis (it is about 60× stiffer in tension than the TPU), with Cu 18 µm and its centre 0.010 mm off that axis ⚠.

## Verdicts (criteria as written in BASELINE §18 V3-G7; SF 1.5 stated here)

| # | Case | Criterion | Result (before, stage 2a) | Status before | Smallest fix (before) | After: stage-2b design | Status after | After mini-ECO | Mini | Stage 2d: 43 × 34 (`mech_s2d.py`) | 2d |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | PV laminate 0.50 at 5 bar, ring shelf + rib (insert, posts) + bond | ≥ 7.5 bar at the 0.15 max-material gap **and** ≥ 5.0 bar at the WC gap | elastic beads 2.31 / 0 bar; bonded 0.50: 5.75 / 0; 0.55: 7.20 / 0; 0.60: 8.84 / 0 (WC gap P1 = 0.00) | **FAIL** | structural bond on ring and rib, PV seat +0.14 mm, glass 0.50 (PV half 4.79): 11.1 / 5.37 bar. (0.55 + 0.11 → 4.81; 0.60 + 0.09 → 4.84) | structural bond, 0.50 strengthened glass, air 0.895: 32.5 / 27.0 bar; 157 MPa | **PASS** | unchanged | **PASS** | bonded 0.50, span 36.5 × 12.5: 32.2 / 21.4 bar, 160 MPa | **PASS** |
| 2 | Window 0.70 on its rigid bond (rail + rib), 5 bar | same, panel at 0.10 max-material gap | 3.63 / 0 bar; WC gap W1 −0.10; rail sag 0.074 mm, rib 0.022 mm; 0.80 glass 4.39 bar | **FAIL** | stainless core in the rail (0.4 × 0.855) + precision W1 tolerances + window seat +0.09 mm (window half 5.395): 13.2 / 5.6 bar | stainless section: 14.0 / 5.89 bar; GF-LCP section in the antenna buffer (X < 11.5, mid-span strip, conservative): 7.95 / 3.35 bar (posts 2 mm there: 14.0 / 5.89; 3 mm: 11.4 / 4.81) | **PARTIAL** | GF-LCP section with posts at 2 mm (X 2–12, F-4): 13.99 / 5.89 bar; stainless section 13.99 / 5.89 bar | **PASS** | span 39.0 × 15.3: 13.9 / 5.84 bar (stainless section); GF-LCP section with foot X4 at 3.5 (largest gap 2.5 mm): 12.8 / 5.41 bar, rail sag 0.010 mm at 5 bar (was 0.004) | **PASS** |
| 3a | Capsule top 0.40, 30 N spread / 15 mm thumb / 5 mm probe | cell not loaded at 1.5 × 30 N | 0.033 / 0.069 / 0.132 mm at 30 N vs 0.20 gap; contact at 180 / 87 / 45.5 N | PASS (probe margin 1.01) | – | top 0.50: 352 / 170 / 88.9 N | **PASS** | unchanged | **PASS** | unchanged (capsule not changed) | **PASS** |
| 3b | Capsule top 0.40 at 5 bar | ≥ 7.5 bar | 4.42 bar SS (270 MPa at 5 bar) | **FAIL** | top 0.50 mm strengthened glass: 8.63 bar, capsule 4.5 → 4.6 mm (t 0.477 needed) | top 0.50: 8.63 bar, 173 MPa; capsule 4.6 | **PASS** | unchanged | **PASS** | unchanged | **PASS** |
| 4a | Floor film over the Ø 8.6 cut-out, 5 bar (29 N) | motor not pushed into the lid | the motor is a boss: rise 0.003 (centred) – 0.006 mm (eccentric), film 16–26 MPa | PASS | – (Ti disc not needed; 0.77 mm was the film without the motor) | unchanged (rise 0.006 mm) | **PASS** | unchanged | **PASS** | motor now over E2 on the kept film: film rise as before (0.006 mm), Ti plate under it | **PASS** |
| 4b | Button membrane 3.2 × 1.75 | §13.4: held press goes to the firmware stuck rule | 2.8 N > 2.2 N; pressed above 3.93 bar | PASS | – | unchanged | **PASS** | unchanged | **PASS** | unchanged | **PASS** |
| 5 | Tolerance stack, both columns, ZIF, raised panel | no interference at WC | W1 film→panel −0.10 / RSS +0.09; W2 ZIF→panel −0.06 / +0.018; W3 0.07; W4 fold R_in 0.60 ≥ 0.45; P1 0.00; P2 0.04; P3 0.11 | **FAIL** | W1 as case 2; W2: support legs ±0.02 + FH34SRJ 1.0 confirmed as a maximum → WC +0.02 (else raise 0.15 → 0.21) | W1 +0.08 / W2 +0.02 / W3 0.07 / W4 0.60 / P1 0.745 / P2 0.785 / P3 0.855 WC | **PASS** | unchanged | **PASS** | W1 +0.08 / W2 +0.02 / W3 0.07 / W4 0.60 / P1 0.595 (PV-half parts 1.20, K-3) / P2 0.665 (motor on the film) / P3 0.855 WC | **PASS** |
| 6 | 1 m drop, window glass edge and capsule top | estimate: lip crushes before the glass edge is hit | window straight edge 0.19 < 0.35 mm (45°, pod mass); R6 corner 0.57 > 0.35: glass edge hit; capsule corner 0.48 < 0.71 (capsule mass), 0.81 > 0.71 (pod mass) | PARTIAL | PC corner bumpers 0.33 mm proud of the glass at the 4 window-half R6 corners (a setback would need 1.07 mm, beyond the ring seat) | bumpers 0.33: R6 corner margin −0.005 (30°) to +0.134 mm (75°) at the 10.49 g pod; 0.34 mm needed; capsule corner with the pod mass as before | **PARTIAL** | bumpers 0.34 (F-5): R6 corner margin +0.004 (30°) to +0.137 mm (75°) at the 10.49 g pod, window corners clear; whole band −0.165…+0.002 mm (information); capsule corner with the pod mass 0.819 > 0.707 mm (as before): bench decides | **PARTIAL** | bumpers 0.34: R6 corner margin −0.001 (30°) to +0.133 mm at the 10.75 g CAD pod, −0.012 at the 11.26 g calc pod (0.35 mm needed); capsule corner (pod mass) 0.827–0.843 > 0.707 mm | **PARTIAL** |
| 7 | Root-A flex at the bar hinge | no crack at 10⁵ cycles: R ≥ 100 t (IPC-2223, 1 layer dynamic) and Cu ≤ 0.30 % ⚠ | ±10° wear: R 11.5 ≥ 7.0 mm, Cu 0.17 %; fit offset ±13°: R 8.8 mm, 0.22 %; flat → 70°: 1.16 % (not cyclic) | PASS | – | unchanged | **PASS** | unchanged | **PASS** | unchanged (hinge geometry same) | **PASS** |

Gate (calculation part): **FAIL**. With the fixes of rows 1, 2, 3b and 5 every row passes, except row 6, which the bench decides.

## Notes the lead needs

- **Decision for case 1 (LEAD_NOTES §2f): bonded support, not thicker glass.** The elastic beads alone add 0.052 mm/bar. With bonded seats, 0.60 glass passes the max-material condition (8.84 bar) but not the WC one, because the P1 chain has 0.00 mm left at worst case. The seat raise is the cheapest lever, and the 0.50 glass is kept. The P3 rib bond line then varies 0.11–0.49 mm: the RFQ needs a gap-filling structural epoxy.
- Stress at 5 bar (SS strip, bonded): PV glass 0.50 at 150 MPa (0.60 at 109 MPa), window 0.70 at 97 MPa, capsule 0.40 at 270 MPa. The laminate glass must be chemically strengthened; BASELINE does not state its type ❓.
- Case 2: the "rigid bond" is not what limits the window. The LCP rail sags 0.074 mm between posts at 5 bar, because the 4.5 mm outer strip of glass loads it too. 0.80 glass is no fix (4.39 bar). Instead of the stainless core, rail posts at 2.0 mm pitch would also work ⚠ (not computed).
- Case 2 and W1 are coupled: the panel's own ±0.11 mm takes most of the 0.10 mm gap. Without a seat raise the WC condition can be met only by setting the gap at assembly (bond line as compensator, shim on the panel); that is not computed here.
- Case 4a assumes a flat, rigid motor base bonded centred on the film. The motor base itself carries the 5 bar through the PSA (can-face load ❓): bench item 11.
- The bead modulus (3 MPa) and the 100 MPa crush pressure are estimates. A stiffer bead does not change decision 1: even at 10× stiffness the elastic seat stays below 7.5 bar at 0.50 mm.

## Bench tests the manufacturer must still do (one line each)

1. 5-bar static water test (ISO 22810 method) on production units after the fixes, with pressure-indicating film under the PV laminate, window and capsule top: no contact marks.
2. Coupon test of the structural epoxy and the elastic bead: compression at 0.5 MPa line load and at bond lines of 0.11–0.49 mm.
3. Rib and rail sag between posts under the 5-bar line load (about 7.8 N/mm rib, 5.5 N/mm rail), measured.
4. First-article CMM of chains W1, W2, P1, P2 (seat heights, support legs, FH34SRJ height, panel thickness).
5. Capsule 30 N press: spread, 15 mm thumb, 5 mm probe; no glass-to-cell contact (pressure film), glass intact.
6. Capsule crush with a soft short: skin face ≤ 43 °C, no venting.
7. Steel-ball impact on the capsule top and on the window glass (ball and height set by the maker's standard).
8. 1 m drops on the window glass edge, the four R6 corners and the capsule edge; glass edges inspected; leak test after.
9. 10⁵ bend cycles at the bar hinge (±10° about the moulded angle, plus ±13° fit offsets) with conductor resistance logged; then pressure-decay leak test, also after a sweat soak.
10. Strap pull, including the quick release, to the strap-pull load.
11. Motor run test after a 1 h 5-bar soak (the base loaded through the floor film).
12. Button press life; membrane seal at 5 bar and the switch released after the pressure is removed.
13. End-of-line pressure-decay leak test of every joint (two glass bonds, rib and posts, ring–floor, E3, root slots, contact pins, membrane, capsule lid).
14. Display check after 5 bar: no press marks or Newton rings on the panel.

## Files

- Stage 2d: `mech_s2d.py` (copy of mech_mini.py on CAD option `L43W34_..._s2d1`) → `mech_raw_s2d.json` (CAD pod 10.75 g) and `mech_raw_s2d_11.26.json` (MECH_POD_G=11.26, calc pod); logs `logs/mech_s2d*.log`.

- Stage 2b: `mech_s2b.py` (copy of mech_v3f.py on the stage-2b geometry) → `mech_raw_s2b.json`; `make_results_s2b.py` adds `after_stage2b` to `mech_results.json` (stage-2a content kept as "before"); logs `logs/mech_s2b.log`, `logs/make_results_s2b.log`. Note: mech_v3f.py now imports the stage-2b geometry by default; its stage-2a outputs are kept in `mech_raw.json`.

- `v3/sim/mech/mech_v3f.py` → `mech_raw.json` (all numbers); `make_results.py` → `mech_results.json` (verdicts); logs in `logs/`.
- `copied/`: unchanged copies of `sim14_stack.py`, `sim14_layout.py` (not used: v0 layout), `window_plate_s1.py`, and the plate models from `decide/calc/baseline_calc.py`.
