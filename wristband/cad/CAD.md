# SolarBand V3-F: mechanical CAD and gate V3-G9

> **Gate-1 work (2026-11-14 / 15):** the model's base is now the **41 × 32 mm pod (board 38 × 29 mm)**; the 40 mm outline is dropped and its files are frozen in `v3/cad_s1/`. Lane-root `board_zones.json` and `band_contacts.json` are the 41 × 32 files. Where the text below says 40 mm, read it as the stage-1 record. See the last section, "Gate 1 options".
> **Status:** 2026-11-13, CAD lane (`v3/cad/`). Built from `v3/decide/BASELINE.md` (cited [B §n]). Nothing was ordered, quoted or uploaded.
> **Marks:** ✅ read today in a named source (URL and page in `ref/sources.md`) or produced by a tool run named here; ✅s search summary only; ⚠ estimate, model output or design choice of this lane (method named); ❓ unknown. P = project file.
> **Re-run** (about 3 min in all): see §14. Every number below comes from a JSON file in `out/` that the scripts write.
> **Naming:** the band harvests light; nothing here is wireless power transfer. People are named only by role.

---

## 0. 中文摘要

**结论：V3-G9 部分通过（PARTIAL）。** 三条通过标准里两条通过、一条部分通过：

| 通过标准（BASELINE §18） | 结果 |
|---|---|
| §9 的佩戴配合数字成立 | **通过** ✅（CAD 复算 130/140/165/200 mm 手腕：小壳远端离皮肤 4.50/4.50/4.51/4.55 mm，翼片 2.95/2.95/2.97/3.01 mm，与 BASELINE 一致；表带上没有任何部件高过表体顶面） |
| 光伏条保持 2.30 mm | **部分通过**：CAD 里四条 27.7 × 2.30 mm 都放得下（层压件边缘留 0.45 mm，第 4 条切掉一个小角、加宽 0.04 mm 补回，总面积 255.5 mm² ≥ 254.8）。但这是靠把屏往天线方向挪 0.3 mm 换来的：屏到天线禁区只剩 1.2 mm（最大实体 1.0 mm），低于 1.5 mm 的规则，要 V3-G3a（SIM-10/11）认可。若坚持 1.5 mm，横梁要外移 0.3 mm，光伏条变 2.235 mm（盖板硅面积 −2.9 %），§11 要重算 |
| 有合法的马达位置 | **通过** ✅：Ø8 马达在两块电极板之间有合法区域 X 17.55–22.45、Y 25.15–25.70 mm（2.3 mm²）；BASELINE 的规划位置 (20.0, 25.4) 合法。Y 方向总共只有 0.55 mm 余量 |

**这次 CAD 新发现、需要别的关卡处理的问题（按严重程度）：**

1. **屏的软排线吃掉主板面积（影响第一关 V3-G1）。** 夏普图纸 ✅：软排线从短边出来，长 13.63 ± 0.4 mm，弯折只能在离玻璃边 0.8–6.0 mm 处、内半径 ≥ 0.45 mm、不能往前偏光片方向弯。手端只有约 5 mm 空间，所以排线必须 180° 折回、压在屏下面的板面上，末端焊盘 J13 落在 X 约 24 mm。这条走廊 121 mm² 不能放器件（BASELINE 只算了 J13 的 15.1 mm²）。粗估第一关利用率：40 mm 表体 0.565 → 0.648（v1 口径 0.718）✗；41 mm 0.623（0.690）✗；41 mm 再去掉 LED 链、O-2 放进电池保护板：0.587（0.650，v1 口径仍 ✗）⚠。
2. **屏的公差。** 图纸 ✅：外形一般公差 ±0.2 mm，厚度 0.745 ± 0.11 mm（最大 0.855，BASELINE 按 0.80 算）。按 BASELINE 原位置（X 1–33、Y 6–20），最大实体的屏会压进肘端墙 0.2 mm、压到横梁不锈钢芯 0.2 mm。CAD 把屏挪到 X 1.3–33.3、Y 5.7–19.7 才放下。厚度取 0.855 时屏到前光膜的空气隙只剩 0.045 mm，5 bar 下窗玻璃碰膜的压力从 4.3 bar 降到约 1.9 bar（简支；固支约 6 bar）⚠；或者表体加厚 0.055 mm。
3. **按键（C&K PTS840）图纸已读 ✅**：确实是侧按式，但高 1.35 mm（BASELINE 假设 1.05）。只能放在手端、屏那半的 E3 托架下面（间隙 0.05 mm）。按键中心离皮肤只有 2.13 mm，左右手都没有东西挡住，但用指腹压比较别扭，要做实物样件验证（厂家做）⚠。
4. **窗玻璃的不锈钢框** BASELINE 质量表里没有：CAD 算出 0.53 g。表体 CAD 质量 9.80 g（BASELINE 典型 9.38、最大实体 9.73 g），佩戴质量约 19.6 g（BASELINE 19.3 / 21.0 g）⚠。
5. **磁吸编码：** 表上只有铁磁靶片、没有磁铁，所以 BASELINE §16 写的“反接时互相排斥”做不到；反接靠结构挡住：充电头反过来会压到窗玻璃 0.45 mm 的台阶，放不平，而且两根针粗细不同（Ø1.6 / Ø2.0）。
6. **心电电极板（先定的）：** E1 202 mm²、E2 242 mm²，按项目惯用的 14.9 mm 接触带算，接触面积 157 / 164 mm²，满足 G-7（≥ 150 mm²），余量很小；按手腕椭圆模型、地板压进皮肤 0.6 mm 算，130/140 mm 手腕的 E1 只有 144/148 mm² ✗ ⚠。

**佩戴检查（左右手都一样，因为表带转 180° 后横截面完全对称）：** 翼片在桡侧、小壳在尺侧；E3 和按键左手在手端、右手在肘端；充电触点左手在肘端、右手在手端，都在尺侧角上。
- **离皮肤的高度：** 小壳 4.50–4.55 mm 最厚；表体屏那半 4.30、光伏那半 3.85；翼片 2.95–3.01；表扣 2.5；快拆 2.0；表带 1.5 mm。小壳外表面比窗玻璃顶低 1.8–3.6 mm。
- **桌面和侧睡：** 打字（手掌朝下）时先碰桌面的是表扣；小壳只在手腕从“尺侧朝下”继续往“手背朝下”转的时候才先着地：130 mm 手腕从 84° 起、140 mm 从 90° 起、165 mm 从 103° 起、200 mm 从 118° 起。也就是小手腕尺侧朝下侧睡时小壳就是支点（比皮肤高出 2.8 / 1.9 mm）。这正是 V3-G7 的 30 N 压力和跌落工况。
- **手腕后伸：** 表体手端离腕关节线 15 mm（大约“戴在腕骨上方一指”）时，手背要后伸约 87° 才碰到表体（轴深 12–20 mm 时 77–100°），远超日常活动需要的 40°（J Hand Surg 1991 的研究 ✅s；人的最大后伸角今天没查到 ❓）；表体滑到腕骨上（距离 0–5 mm）时 36–53° 就碰到。41 mm 表体只差 1.5° 左右。左手碰到的是 E3 和按键（会误按，固件“按住 > 5 s 算卡住”的规则正好兜底）。
- **戴着时能接充电头：** 25 × 15 × 7 mm 的头放在触点所在的尺侧角上（左手在肘端，线朝肘部；右手在手端，后伸时手先碰到头），130–200 mm 手腕都不碰小壳（≥ 3.0 mm）、不碰皮肤（≥ 4.0 mm）。

**交给别的关卡：** 板面区域文件 `board_zones.json`（在本目录根下，即 40 mm 版；41 mm 版是 `out/board_zones_L41.json`，含禁区、限高区、马达孔、横梁小柱脚、弹片和入线焊盘、按键、触点、天线禁区、电极板），读取模块 `src/lgeom_v3f.py`；充电接口文件 `band_contacts.json` 给充电头那条线（`v3/head/head_interface.json` 今天还不存在，没法对比）。

---

## 1. V3-G9 criteria (BASELINE §18)

| Criterion as written | Status | Result |
|---|---|---|
| the §9 fit numbers hold | **PASS** | CAD reproduces §9 on 130/140/165/200 mm wrists (§8.2) ✅ `out/worn_checks_L40.json` |
| the PV strips keep 2.30 mm (else the lid PV loss is stated and §11 re-run) | **PARTIAL** | met in CAD with laminate edge margins ≥ 0.45 mm (lid RFQ ❓) and the panel moved 0.3 mm toward the antenna (rule 1.5 mm → 1.2 mm nominal, 1.0 mm max-material: V3-G3a must accept). Weaker criterion met: four 2.30 mm strips fit with no max-material interference. Without the panel shift: strips 2.235 mm, −2.9 % lid silicon, §11 not re-run here |
| a motor position exists | **PASS** | legal centres X 17.55–22.45, Y 25.15–25.70 mm; (20.0, 25.4) legal ✅ `out/motor_search_L40.json` |

Work items of V3-G9 (no separate criterion; status of the work):

| Item | Done | Main result |
|---|---|---|
| V3-F floor plate outlines first | yes | §3: E1 202.1, E2 241.7 mm²; G-7 met on the 14.9 mm strip convention only |
| motor cut-out between the plates, rib post feet, root-A lands | yes | §4 |
| either-wrist pose, 130/140/165/200 mm (E3, button, contacts, buckle, wing radial, capsule ulnar) | yes | §8.1 |
| 4.5 mm capsule: rounded far edge, glass top, desk and side-sleep contact | yes | §8.4 |
| two-glass top with the rib beside the panel (from the LD-29Y03 drawing) | yes, with findings | §5: BASELINE positions interfere at max material; FPC corridor 121 mm² |
| contacts' inner faces ≥ 3.4 × 2.2 mm and the head footprint | yes | §6 |
| front-light tail | yes | §5.4 |
| button plunger and membrane | yes | §7; PTS840 is 1.35 mm tall |
| wrist extension against the hand-end wall and the 40 (41) mm length, both wrists | yes | §8.5 |

**Gate verdict: PARTIAL.**

## 2. What was built

- `src/geom_v3f.py`: single-source geometry (like `mech/geom_v0.py`): frames, the max-material Z stack of [B §8], plan regions (shapely), parts, board zones, the wrist model. `V3F_POD_L=41` builds the 41 × 32 mm reserve (hand-end features +1 mm, board 38 × 29 mm).
- `src/model_v3f.py`: build123d model of the pod, 45 named solids; STEP and GLB; manifold3d pairwise interference and clearance checks; masses; renders (`src/zrender.py`, copied from `mech/`) and exact planar sections.
- `src/motor_search.py`, `src/worn_v3f.py` (wrist model, worn assembly STEP/GLB on a 165 mm wrist, checks), `src/exports_v3f.py` (board zones, band contacts), `src/lgeom_v3f.py` (loader), `src/mass_v3f.py`, `src/report_v3f.py`.

**Frames.** Case frame of [B §7]: X 0–40 along the forearm (0 = elbow end on a left wrist), Y 0–32 (0 = root B, antenna wall), Z = 0 at the floor's skin face; the mesa reaches Z −0.80. Board frame (V2-B lgeom convention, F.Cu = sky side): X_b = X − 1.5, Y_b = Y − 1.5. Worn frame: u across the wrist toward the ulnar side, v dorsal; the floor plane is tangent to the dorsal vertex (mesa pressed in, [B header]).

**Z levels (max material, [B §8])**: floor 0–0.25, carrier film –0.35, board –1.45, parts ≤ 2.50 (≤ 2.20 under the panel); PV column: bead 2.45–2.65, laminate 2.65–3.85; window column: support 2.35–2.45, panel 2.45–3.25, air gap –3.35, film (and the stainless frame) 3.35–3.60, window glass 3.60–4.30. Pod 4.65 / 5.10 mm with the mesa.

## 3. Floor plates, fixed first

Rules ⚠ (sources in `geom_v3f.py`): Ti Gr2 0.25 mm inlaid flush in the 0.25 mm PC film; inside the board outline (0.5 mm from the ring wall; bonded by silver-epoxy dots, B.Cu and L5 void above them [B §18 V3-G1]); ≥ 2 mm PC web to the optical cap and between the plates (P enclosure §4.4); ≥ 5 mm from the antenna keep-out (P V2-B metal rule); inner edges at X 12.5 / 27.5 over the full height (the straight continuation of the cap web), which leaves a PC-only corridor for the motor; Y 5.0–27.0 (the 14.9 mm contact strip ± 3.5 mm). The motor position played no part in drawing them.

| Plate | Area | In the 14.9 mm strip (P Lens D convention) | Wrist model, floor pressed 0.4 / 0.6 / 1.0 mm into the skin (130–200 mm) ⚠ |
|---|---|---|---|
| E1 (elbow end, antenna corner cut) | 202.1 mm² | **157.2 mm²** ✓ G-7 ≥ 150 | 118–145 ✗ / 144–167 (✗ on 130, 140) / 171–196 ✓ |
| E2 (hand end) | 241.7 mm² | **163.9 mm²** ✓ | 118–146 ✗ / 144–179 (✗ on 130, 140) / 186–231 ✓ |

G-7 holds on the project's convention with 5–9 % margin; the real contact strip on small wrists is narrower, so G-7 stays a bench item (manufacturer). Outlines: `out/board_zones_L40.json → skin_face`, plot `out/motor_search_L40.png`.

## 4. Motor position (V3-G9 item 2)

Grid search (0.05 × 0.025 mm) of the ERM centre, every constraint as a clearance (`src/motor_search.py`): cut-out (Ø8.6) inside the board with the 0.5 mm edge band; ≥ 0.3 mm to the six post-foot pads, the root-A lands (X 4.5–10.5), the K zone and the cap; motor body (Ø8.1 max ⚠) clear of the rib shelf (Y 21.0) by 0.1 mm, ≥ 1.0 mm from both plates, carrier-film cut-away ≥ 0.5 mm from the plates; ≥ 10 mm from the antenna keep-out [B §13.1].

| Board | Legal centres | Area |
|---|---|---|
| closed cut-out (BASELINE) | X 17.55–22.45, Y 25.15–25.70 | 2.3 mm² |
| cut-out opened to the far edge (option for V3-G1) | X 17.55–22.45, Y 25.15–26.85 | 8.0 mm² |

At the planning centre (20.0, 25.4) ✅: cut-out to the nearest post foot 0.54 mm (rule 0.3), to the edge band 0.30 mm, motor to the rib shelf 0.35 mm, to E1 / E2 3.45 mm, to the antenna keep-out 20.8 mm; motor top to the PV laminate 0.15 mm (the §8 motor-column margin). X is bounded by the plates, Y by the rib shelf (below) and the board's edge band (above). The closed cut-out leaves a **0.8 mm board strip** to the far edge that cannot carry routing; opening the cut-out to the edge removes that fragile strip at no area cost (V3-G1 decides). Same window at 41 mm. **The Ø8 ERM fits; decision 5 is not forced to the LED by geometry.**

## 5. The top: two glasses, the rib, the panel (from LD-29Y03)

### 5.1 Panel data read today ✅ (LD-29Y03 p.13, p.36, p.42)
Outline 32.00 × 14.00 mm, general tolerance ±0.2; thickness 0.745 ± 0.11 (0.23 / 0.15 / 0.25 / 0.115 layers); active area 25.28 × 10.744 mm centred 17.73 ± 0.15 from the FPC edge; FPC from the short edge, centred, 13.63 ± 0.4 mm long, end 9.47 mm wide with a 4.5 mm stiffener (0.3 mm); bend 0.8–6.0 mm from the glass edge, inner R ≥ 0.45, never toward the front polarizer, ≤ 3 bends; mass ≤ 0.73 g.

### 5.2 Fit of the panel between the walls, the rib and the rules

| Direction | BASELINE position | Max-material panel (±0.2) | CAD position (as built) |
|---|---|---|---|
| X (elbow wall at 1.0; E3 rule glass ≥ 4.0 mm from E3) | X 1.0–33.0 | into the wall by 0.2 mm; E3 rule −0.1 mm if E3 starts at 37.1 (display lane) | **X 1.3–33.3**: wall gap 0.07–0.10 mm; E3 rule 4.1 mm with E3's top part from X 37.6 (CAD E3: 2.4 mm on top + 1.0 mm wrap) and 5.1 mm at 41 mm. If E3 must start at 37.1, only the 41 mm pod passes |
| Y (rib insert at 20.0; panel ≥ 1.5 mm from the antenna keep-out) | Y 6.0–20.0 | into the rib insert by 0.2 mm | **Y 5.7–19.7**: rib gap 0.10 mm at max material; keep-out distance **1.2 mm (1.0 at max material) < 1.5 rule** → V3-G3a. Alternative: rib +0.3 mm, strips 2.235 mm (−2.9 % lid silicon) |
| Z (0.80 allowance) | 2.45–3.25 | 0.855 mm at the drawing maximum | air gap to the film 0.045 mm at max thickness (0.10 nominal); the 5-bar window contact falls from 4.3 to about 1.9 bar simply supported (6.2 clamped) ⚠, or the window column grows 0.055 mm |

### 5.3 Glasses, rib, frame (CAD design, ⚠ where BASELINE is silent)
- **Window glass** 0.70 mm: X 0.5–37.5, Y 0.5–20.45, R5.5 corners (a 0.40 mm PC bezel lip outside it, flush with the glass top). **Stainless frame** 0.25 mm rigidly bonded under the glass edge (BASELINE: "rigid bond to a stainless frame"): 267.6 mm², 0.53 g, cut away within 5.0 mm of the antenna keep-out, where the glass sits on a raised PC seat. The frame rests on the ring's window seat (Z 3.15, elastic bead 0.20), the rib insert, the K block and the E3 block.
- **PV laminate** 1.20 mm max: X 3.25–37.5, Y 20.55–31.5, 0.10 mm sealant joint to the window glass. **Strips** X 3.7–31.4, Y 21.00 / 23.57 / 26.14 / 28.71, 2.30 mm; the 4th strip's elbow corner would leave the laminate's rounded corner (R5.5), so it is chamfered to the 0.45 mm margin and made 0.04 mm wider: 63.71 / 63.71 / 63.71 / 64.40 mm² (sum 255.5 ≥ 254.8, so the series string is not current-limited by it). Laminate edge to silicon: rib side 0.45, far side 0.45–0.49, K side 0.45, hand end 6.1 mm. The laminate's K-side edge rests in a sealant joint (no seat: the J15 fingers need the space below).
- **Rib** (lid RFQ part): PC shelf Y 20.0–21.0, X 3.7–37.0, Z 2.15–2.45; stainless insert 0.5 × 0.7 mm, **X 3.7–34.0 (30.3 mm; BASELINE 33 mm, because the K block takes X 1–3.7)**; six stainless posts 0.6 × 0.6 mm at X 4/10/16/22/28/33, Y 20.0–20.6, standing on the post feet. The board under the rib allows parts ≤ 0.55 mm (new zone). Insert to the antenna keep-out 15.5 mm.
- **Hand-end E3 block**: the window-half shelf (underside Z 2.85) covers SW1; the PV-half shelf (underside Z 2.15) restricts the parts under it to 0.55 mm (new zone, 11.8 mm²).

### 5.4 Display FPC, front light
- **FPC** (13.63 mm ✅): out of the TFT-glass ledge at Z 2.82, 180° fold 1.2 mm from the glass edge (inner R 0.61 mm ≥ 0.45 ✅ rule), back under the panel on the board, stiffened end with the soldered J13 land at X 24.1–28.6. **FPC corridor X 23.7–35.4, Y 7.5–17.9: 121.4 mm² without parts** ⚠. The fold clears SW1 by 0.29 mm and the frame by 0.44 mm. First-order gate-1 effect (BASELINE 455.4 / 806.3 mm² less J13, the corridor, four support legs and the film tail): **0.648 (v1 0.718) at 40 mm, 0.623 (0.690) at 41 mm, 0.587 (0.650) at 41 mm with the LED chain removed and O-2 in the pack** ⚠ — a V3-G1 item. Ways to win area back: parts ≤ 0.30 mm under the FPC if the panel is raised 0.09 mm; a fold nearer 6.0 mm (only if SW1 leaves the FPC's Y band); a shorter FPC from Sharp ❓.
- **Front-light film** (≤ 0.25 mm incl. OCA, laminated under the window glass, BASELINE §8 order): AA + 0.8 mm, to X 33.6; **tail** X 33.6–33.9, Y 5.75–7.35 (0.1 mm beyond the max-material glass edge, beside the FPC), to J16 at X 33.9–35.5; 27.1 mm from the antenna keep-out.
- **Panel support** 0.10 mm frame under the panel's rear border on four PC legs Ø0.8 (board keep-outs Ø1.2: new, 4.5 mm²) ⚠.

## 6. Charging contacts (K corner) and the head footprint

| Item | CAD value (case frame) |
|---|---|
| pins | VBUS Ø1.6 at (2.0, 22.4); GND Ø2.0 at (2.2, 28.6); **pitch 6.20 mm** (non-standard ⚠: common pogo pitches avoided, no catalogue survey) |
| top faces | 0.30 mm below the rim top (Z 3.85) in Ø(d + 0.4) counterbores |
| inner faces | **3.4 × 2.2 mm centred on the J15 lands** (2.5, 22.0) and (2.6, 25.8), at Z 2.45 (finger working height 1.0 mm ⚠, BW0036BG datasheet not found ❓); the GND pin is a formed insert with a 2.6 mm leg; pins 0.40 mm apart at the closest point |
| magnet code | one ferritic disc Ø2.4 × 0.5 mm at (1.5, 25.2) under a 0.2 mm PC skin; off the pin axis, so a head turned about the pin midpoint misses it by 1.34 mm. **Ferritic targets cannot repel**, so [B §16] "a reversed head repels" is not achievable without a magnet in the band |
| keying | the window glass stands 0.45 mm above the K block along Y 20.45; a head footprint at Y 20.6–35.6 sits flat; turned 180° it would reach Y 15.4 and rest on the glass step, so it cannot seat; the pins are unequal |
| distance to the antenna keep-out | 17.1 mm (REDESIGN ≥ 11 ✅ P) |
| head worn (25 × 15 × 7 mm at X −2–23, Y 20.6–35.6 ⚠) | clears the capsule by ≥ 3.06 mm, the root-A hinge by ≥ 2.2 mm, the skin by ≥ 4.0 mm on 130–200 mm wrists; left wrist: over the forearm; right wrist: at the hand end (the hand meets it first in extension) |

Placement safety: J15 is class M only with the inner face as drawn (E-13): the CAD states it; the ring drawing must carry it.

## 7. Side button

- **C&K PTS840 GK SMTR LFS** ✅ (catalogue B-34/B-35 via RS): "Microminiature SMT Side Actuated"; body 3.5 × 2.9 mm, leads 4.7 mm, actuator 1.7 mm wide standing 0.65 mm proud, **height 1.35 mm** (BASELINE assumed 1.05 mm), 220 gf, travel 0.2 mm (+0.2/−0.1), 100,000 cycles. The side-versus-top question of [B §16] is closed: it is side actuated. Footprint 4.7 × 3.55 mm ≈ 16.7 mm² (BASELINE 17.0 ✓). Its 1.35 mm fits only under the window-half E3 shelf (0.05 mm clearance), not under the PV half.
- **Membrane** ⚠: TPE window 3.2 × 1.75 mm (Y 13.9–17.1, Z 1.0–2.75) in the hand-end wall, 0.40 mm thick, flush outside, inner nub Ø1.2 mm 0.05 mm from the actuator tip; 0.1 mm below the E3 wrap. At 5 bar the membrane sees 2.8 N > 2.16 N: held pressed, as the firmware's > 5 s "stuck" rule expects [B §14].
- **Reach**: on both wrists nothing covers it (the roots leave the long walls). Left wrist: faces the hand; right wrist: faces the elbow. The actuator centre is **2.13 mm above the skin**; a fingertip pad (R 7–9 mm ⚠) touching a vertical face contacts it at the height of its centre, so it must press into the skin or deform; a fingernail or the tip's edge works. Ergonomics not verified ❓: a physical mock-up (manufacturer).

## 8. Worn checks

**Wrist model** ✅ P (strap lane, read online on 2026-11-13): elliptical wrist, depth/width 0.68 (Coll. Antropol. 38 (2014) 219-226, Table 1 p.222), circumference by Ramanujan II; strap 1.5 mm leaving the bar 2.5 mm outside the long wall, 1.0 mm above the floor plane, straight to tangency; the pod floor tangent to the dorsal vertex with the mesa pressed in. Ported in `geom_v3f.wrist_geo` (it reproduces `baseline_calc.py` exactly).

### 8.1 Either wrist
On the right wrist the band is turned 180° about the vertical: x = 40 − X, u = Y − 16 with u toward the ulnar side on both arms. **The cross-section is identical on both wrists**, so every height and fit number holds for both. Wing (root B) radial, capsule (root A) ulnar on both. E3 and the button: hand end (left) / elbow end (right). Contacts: elbow-ulnar corner (left) / hand-ulnar corner (right). Buckle: volar midline on both (symmetric band, operated from either side). Renders: `out/render_worn_165_{left,right}*_L40.png`.

### 8.2 §9 fit numbers (CAD, BASELINE method; values for 130 / 140 / 165 / 200 mm)

| Quantity | CAD | BASELINE §9 |
|---|---|---|
| free span, tilt | 13.67 / 13.96 / 14.73 / 15.71 mm; 66.0 / 61.0 / 51.1 / 41.5° | 13.7 / 14.0 / 14.7 / 15.7; 66 / 61 / 51 / 42 |
| capsule thickness above the skin at its far end | 4.50 / 4.50 / 4.51 / 4.55 mm | – / 4.50 / 4.51 / 4.55 (130: 4.50) |
| capsule inner face to the skin at the far end (normal distance) | 0.003 / 0.003 / 0.017 / 0.054 mm | 0.002 / 0.00 / 0.03 / 0.07 (vertical distance) |
| overhang past the tangent point | 0.23 / 0 / 0 / 0 mm | 0.23 (130), none |
| capsule outer top below the PV top (3.85) | 3.15 / 2.78 / 2.05 / 1.37 mm | – / 2.78 / 2.05 / 1.37 |
| same below the window top (4.30) | 3.60 / 3.23 / 2.50 / 1.82 mm | – |
| wing root above the skin | 2.95 / 2.95 / 2.97 / 3.01 mm | 2.95–3.01 |
| capsule to the pod lug in section | 1.09 / 1.13 / 1.22 / 1.34 mm | – |

### 8.3 Highest point of every item when worn (thickness above the skin where it rests, [B header])
Capsule 4.50–4.55 (thickest); pod window half 4.30; pod PV half, E3 rim and K corner 3.85; wing 2.95–3.01; buckle 2.5 ⚠; quick release 2.0 ⚠; band 1.5 mm. Above the floor plane the pod top (4.30) is the highest point; no strap item rises above 2.48 mm (capsule on 200 mm). Profile prominence (largest distance from the skin, at the pod's top long edges): 7.5 / 7.3 / 6.9 / 6.5 mm for the pod and 7.7 / 7.6 / 7.2 / 6.9 mm for the capsule's near top edge.

### 8.4 Capsule on a desk and in side sleep (roll sweep, rigid flat support, `out/worn_roll_contact_L40.png`)

| Wrist | Capsule is the first contact for roll angles (0 = volar side down, 90 = ulnar side down, 180 = palm up) | At 90° (ulnar side down) |
|---|---|---|
| 130 mm | 84–154° (stands up to 7.7 mm out of the skin) | capsule, 2.84 mm |
| 140 mm | 90–157° | capsule, 1.86 mm |
| 165 mm | 103–162° | band |
| 200 mm | 118–168° | band |

Typing or mouse use (volar side down, ±15°): the buckle touches. The capsule's glass top lies flat on the support at 180° − tilt = 114 / 119 / 129 / 138.5°; before that the rounded far edge (R1.0 ⚠, so the glass top is 37.4 × 9.9 mm, not 10.9) touches first, after it the near (hinge-side) edge. So on small wrists side sleep on the ulnar edge loads the capsule, and on every wrist a forearm resting on its dorso-ulnar side does: the 30 N spread / thumb / probe and edge-drop cases of V3-G7 are real use cases.

### 8.5 Wrist extension against the hand end (2-D sagittal model ⚠)
Hand dorsum rotating about an axis at depth d below the dorsal skin at the joint line (capitate head ✅s; depth not found, d = 12 / 16 / 20 mm); the pod's distal top corner at its height above the skin (left: E3 rim 3.85 mm; right: window lip 4.30 mm) and g mm proximal of the joint line. Extension at first contact, d = 16 mm:

| g (pod end to the joint line) | 0 | 5 | 10 | 15 | 20 mm |
|---|---|---|---|---|---|
| left wrist (E3 end) | 36° | 53° | 71° | 87° | 101° |
| right wrist (elbow end turned to the hand) | 38° | 54° | 71° | 87° | 100° |

d = 12 / 20 mm shifts these by +4.5 / −3.3° at g = 0 and +13 / −10° at g = 15. The 41 mm pod (centred) loses 1.4–1.7°. The J Hand Surg 1991 functional-ROM study ✅s: most daily tasks need ≤ 40° of extension. With the band "a finger's width above the wrist bone" (Fitbit guidance ✅s, about 15–20 mm) contact needs 77–101°, far beyond the 40° functional range (the maximum active range was not read today ❓); a band that slides onto the wrist bone (g ≈ 0–5 mm) is met at 36–53°, and on the left wrist the hand then presses E3 and the button.

## 9. Interference and clearance (manifold3d)
45 solids; 141 overlapping pairs tested; **no interference above 0.001 mm³**; 70 designed contacts (seats, bonds, contacts at max material) with zero volume; manifold3d accepted every solid (three are unions touching along an edge, so trimesh does not call them watertight). Full table with rules: `out/interference_clearance_L40.md`. Below a rule: only the panel-to-antenna plan distance (1.2 / 1.0 mm against 1.5). Smallest designed clearances: SW1 to the E3 shelf 0.05, actuator to the nub 0.05, panel (max material) to the wall 0.07, to the rib 0.10, motor to the laminate 0.15, parts to the structure 0.15 mm.

## 10. Masses and volumes against BASELINE §10 (`out/mass_L40.json`; CAD volumes are max-material ⚠, handbook densities)

| Pod line | CAD g | BASELINE g |
|---|---|---|
| top: laminate, window glass, panel 0.73 (✅ max), support | 2.83 | 3.08 (2.83 + 0.25 window delta) |
| **stainless window frame** | **0.53** | not listed |
| PCBA (board from CAD + BASELINE's parts) | 3.32 | 3.32 |
| ring, lip, K and E3 blocks, lugs, Ø0.8 bar pins | 1.31 | 0.83 |
| floor film, plates, carrier film | 0.85 | 0.97 |
| E3 strip and tab; optical cap | 0.09; 0.10 | 0.15; 0.08 |
| pins, fingers, target | 0.10 | 0.10 |
| beads, potting, FPC, PSA | 0.08 | 0.28 |
| front-light film (+0.01 LED) | 0.12 | 0.05 |
| ERM net of the cut-out | 0.30 | 0.30 |
| button, membrane, wake parts; O-2 | 0.04; 0.01 | 0.10; 0.01 |
| rib insert + posts; rib PC | 0.10; 0.01 | 0.12; – |
| **Pod** | **9.80** (41 mm: 9.93) | 9.38 typ / 9.73 max |

The CAD pod is 0.42 g above BASELINE's typical value, mostly the frame and the solid lugs (both can be slimmed). Strap at 165 mm from CAD volumes: capsule shell 0.47 g (BASELINE 0.66), glass top net 0.19 (0.24), hinges 0.25, root ends 0.28, wing core 0.59 (0.81), wing laminate 1.39 (1.41) ⚠; with BASELINE's band, cell, PCM and quick release the strap is about 9.8 g and the **worn band about 19.6 g** (BASELINE 19.3 / 21.0 g) ⚠. Volumes: pod envelope 5.15 cm³ without the mesa (5.64 cm³ with mesa and lugs; 41 mm: 5.28 / 5.77); solid material 4.22 cm³; capsule 1.64 cm³ of parts in a 2.06 cm³ box.

## 11. Files for other lanes

- **`board_zones.json`** (lane root; = `out/board_zones_L40.json`, 41 mm reserve in `out/board_zones_L41.json`): board outline (R4.5), 29 zones with kind and `h_max` (max part height above the board top incl. solder), rect and polygon in board and case frames: low-part zone under the panel (0.75), rib strip (0.55), PV-half E3 shelf (0.55), FPC corridor (no parts), J13, J16, film tail, K zone with both J15 lands, J11, six post feet, four support legs, SW1, motor cut-out (centre, Ø8.6) and its 0.3 mm edge keep-out, J17 (suggested), antenna keep-out (all layers), root-A and root-B lands; skin face: E1, E2 (B.Cu + In4.Cu void), cap, carrier-film cut-away. `src/lgeom_v3f.py` exposes them in lgeom style (`BOARD_W`, `CORNER_R`, `OUTLINE`, `ZONES`, `height_limit_at(x, y)` …).
- **`band_contacts.json`** (lane root; = `out/band_contacts_L40.json`; identical at 41 mm): pins, pitch, faces, target, keying, K-corner outline, head footprint, worn positions. `v3/head/head_interface.json` did not exist at the end of this lane's work: no comparison was possible.

## 12. Deviations from BASELINE made by the CAD (each needs the owner's acceptance)

1. Panel at X 1.3–33.3, Y 5.7–19.7 (BASELINE X 1–33, Y 6–20): max-material fit; costs the 1.5 mm antenna rule (V3-G3a).
2. Rib insert X 3.7–34.0 (30.3 mm, BASELINE 33 mm); the K block supports the glass edge at X 1–3.7.
3. E3's top part from X 37.6 (2.4 mm on the rim + 1.0 mm wrap).
4. Window glass edge Y 20.45, laminate edge Y 20.55 (0.10 mm joint); 4th strip chamfered and +0.04 mm.
5. New parts not in BASELINE: stainless window frame (0.53 g), panel-support legs (4 board keep-outs), Ø0.8 bar pins.
6. Capsule far-edge radius R1.0 (glass top 37.4 × 9.9 mm, not 10.9).
7. J11 (E3 finger) at board (36.2, 8.0) under the window-half shelf.

## 13. Verified, estimated, unknown

- ✅ today: LS011B7DH03 outline, tolerances, thickness, FPC length and bend rules (LD-29Y03 p.13, 36, 42); PTS840 side actuation, size, height, force, travel (B-34/B-35); tool runs of this lane (all JSON in `out/`).
- ✅s: the J Hand Surg 1991 functional-ROM study (40° extension); the capitate as the flexion-extension axis; Fitbit's "a finger's width above your wrist bone"; Digi-Key "Side Actuated … Right Angle".
- ⚠: every CAD dimension BASELINE does not fix (frame, lip, beads, supports, K and E3 blocks, membrane, pins, target, lugs); the 0.45 mm laminate margins; the finger working height; the motor's 8.1 / 2.2 mm envelope; the axis depth; the fingertip model; masses (densities); the gate-1 estimate.
- ❓: BW0036BG datasheet (working height, tip position); a lid supplier's laminate edge margin; Sharp's outline tolerance beyond "general ±0.2"; the head's design (`head_interface.json`); whether SIM-10/11 accepts the panel 1.2 mm from the keep-out.

## 14. Files and re-run

| File | Content |
|---|---|
| `src/geom_v3f.py`, `src/model_v3f.py`, `src/motor_search.py`, `src/worn_v3f.py`, `src/exports_v3f.py`, `src/lgeom_v3f.py`, `src/mass_v3f.py`, `src/report_v3f.py`, `src/zrender.py` | scripts |
| `out/V3F_L40_pod.step`, `.glb` (and `_L41`) | pod assembly, 45 named, coloured solids |
| `out/V3F_L40_worn_165_left.step`, `.glb` (and `_L41`) | pod + roots (capsule with shell, glass, cell, PCM; wing with core, laminate, cells) + band + 165 mm wrist |
| `out/render_{top,bottom,iso,exploded,cut_rib_X20,cut_window_Y12p7}_L40.png`; `out/section_{X20_rib_motor,X16_post,Y12.7_window,Y22.4_contacts,Y15.5_button}_L40.png` | pod renders and planar sections (rib, window, motor, contacts, button) |
| `out/worn_sections_L40.png`, `worn_roll_contact_L40.png`, `worn_wrist_extension_L40.png`, `render_worn_165_*_L40.png` | worn cross-sections (incl. the capsule) on 4 wrists, roll contact, extension, worn renders on both wrists |
| `out/checks_pod_L40.json`, `interference_clearance_L40.md`, `worn_checks_L40.json`, `motor_search_L40.{json,png}`, `plate_contact_L40.json`, `mass_L40.json`, `checks_V3G9_L40.json` | checks; the last one holds the criteria |
| `board_zones.json`, `band_contacts.json` (lane root) and `out/*_L40.json`, `out/*_L41.json` | inputs for layout and the head lane |
| `ref/sources.md` | datasheet and literature notes |

Re-run (venv python, `-B`): `motor_search.py`, `model_v3f.py`, `exports_v3f.py`, `mass_v3f.py`, `worn_v3f.py`, `report_v3f.py`, in that order (`logs/run_L41.sh` does the same with `V3F_POD_L=41`).

## Stage 1 (2026-11-14): fixes after the CAD review (`v3/stage1/STAGE1.md`, `issue_log.json`)

Tags in the sources: `[S1 C-n]`. Run order: `logs/run_L.sh 40|41`. Both lengths exit 0 on every step:
- interference 0 of 157 / 156 pairs;
- void checks all clear;
- `test_lgeom_v3f` 14 / 14.

- **C-1 window support.** A GF-LCP rail on the antenna side carries the window: Y 5.0–5.4, X 1.1–33.7, section 0.40 × 0.855 mm, 9 posts ≤ 4.0 mm apart.
  - The frame (glass alone inside the antenna buffer) sits on structural bond lines on the rail and on the rib insert. The ring seat keeps its elastic seal bead.
  - The free span becomes 36.0 × 14.6 mm.
  - 5-bar check (`v3/stage1/calc/window_plate_s1.json`, ⚠): 4.05 bar simply supported, about 13 bar clamped. BASELINE's basis was 4.3 / 14 bar. The earlier CAD statements of 1.9 / 6.2 bar are withdrawn.
- **C-10 window column.** The column is 0.055 mm taller, so the air gap stays 0.10 mm at the 0.855 mm max-material panel. Window half 5.155 mm. The rib insert is 0.5 × 0.755 mm.
- **C-2 K corner.**
  - Strips at X 4.1–31.8; laminate from X 3.65; K top to X 3.55.
  - Pins VBUS (1.9, 21.9) and GND (1.9, 27.3): pitch 5.40 mm.
  - Walls at the largest counterbores are ≥ 0.325 mm; nothing overlaps the laminate.
  - The target at (1.5, 24.46) is now the attach point only.
- **C-8 fingers.** J15 land (2.5, 22.15) and J18 land (2.65, 26.2). The finger body clears the max-material panel by 0.10 mm in plan. The BW0036BG drawing is still missing.
- **C-4 / C-5 zones.** Zones are drawn from the `parts.json` courtyards:
  - SW1 4.04 × 6.54 mm, with pad 5 deleted;
  - root lands X 5.1–11.1;
  - J13, J16, J17, the fingers;
  - O-2 22.12 mm².
  - The FPC fold is now 1.0 mm from the glass edge: the SW1 courtyard clears it by 0.04 mm at 40 mm and 1.04 mm at 41 mm.
- **C-6.** D10 sits at the radial board edge. Its light goes up through a frame notch, inside the window bond. The lid flex tail runs to J6 at X 32.1–35.6.
- **C-7.** `height_limit_at()` uses zone priorities and has unit tests (`src/test_lgeom_v3f.py`).
- **C-9 E3-net metal to the panel (rule ≥ 4.0 mm).**
  - 40 mm: strip 4.1, tab 3.1, J11 finger 3.4 mm. The rule fails; this goes to SIM-07 as an input.
  - 41 mm: 5.1 / 4.1 / 4.4 mm.
- **C-12.** The head housing comes from `head_interface.json`, with a 1.0 × 0.8 mm rebate: 0.295 mm clearance over the glass. The cable direction text is corrected.
- **C-13.** Masses are compared with the max-material 9.73 g. Pod 9.83 g at 40 mm and 9.96 g at 41 mm. The PCBA line is copied from BASELINE.
- **C-14 / C-15 / C-18 / C-20.**
  - `src/plate_contact.py` added; the motor search is re-run.
  - The 5 mm rule is tested on a 5.01 mm, 128-segment buffer: 5.0099 mm.
  - One capsule radius constant; the plate dot pads are stated.
  - Voids are checked against solids.
- **Still open:**
  - C-3: gate 1 with the CAD features is 0.734 / 0.813 at 37 × 29 (`v3/stage1/checks/cross_check.json`).
  - C-9 at 40 mm.
  - C-16: the antenna type.
  - C-17: the wrist-model limits.
  - The BW0036BG drawing.

## Gate 1 options (2026-11-14 / 15): 41 × 32 base and levels 1 to 4 (`v3/g1/cad/CAD_OPTIONS.md`)

Tags in the sources: `[G1]`. Full notes, tables and the Chinese summary are in `v3/g1/cad/CAD_OPTIONS.md`. Every option has a zone file `out/options/board_zones_<TAG>.json` (same schema, with zone height limits) and a plan `out/options/plots/zones_<TAG>.png`.

- **Base.** `geom_v3f.py` defaults to 41 × 32 mm. Against `v3/cad_s1` (41 mm outputs) every stage-1 check is unchanged (`v3/g1/cad/base_vs_s1.json`):
  - interference 0 of 156 pairs; 7 voids clear; 61 clearance rows identical;
  - 42 zones identical; V3-G9 PASS / PARTIAL / PASS; pod 9.96 g; `test_lgeom_v3f` 14 / 14.
- **New inputs.** `V3F_POD_W` (32 / 33 / 34) and `V3F_OPT` (`fpc`, `fold`, `rin`, `raise`, `joint`, `motor`, `mx`, `my`, `notch`, `strips`). Run one option with `logs/run_L.sh <L> [W] [OPT] [fast]`, all of them with `logs/run_all_options.sh` (exit 0 on 2026-11-15 01:28 UTC).
- **Display FPC (level 1), LD-29Y03 p.36 and p.42 read again ✅.**
  - The FPC is 9.47 mm wide only for 5.63 mm from the glass edge, then a 5.5 mm tail. §5.4's corridor of 10.4 mm over the whole length was too large.
  - The stiffener is on the front face and the terminals on the rear face. After the only legal fold the terminals face the panel. **A J13 land under the stiffened end (§5.4, BASELINE §5.1) cannot be soldered.** Working joints: a bridge flex to a land beyond the FPC tip, or a top-contact ZIF (1.0 mm, panel +0.15 mm).
  - FPC + J13 without parts: 123.5 mm² (stage 1) → 104.9 mm² (as drawn, L1-A) → 95.6 mm² (fold at 1.9 mm, L1-A3; 0.14 mm to the SW1 courtyard).
  - Parts under the FPC: none of the netlist's classes at a panel raise of 0 to 0.15 mm (0.055–0.205 mm worst case; R0201 needs 0.31 mm).
  - A panel raise lifts the low zone: 0.75 → 0.80 / 0.85 / 0.90 mm; from +0.10 mm U10 and U15 fit under the panel. Window half 5.155 → 5.205 / 5.255 / 5.305 mm.
- **Wider pods (level 2).** The extra width is on the PV half.
  - 41 × 33: usable board +35.0 mm², lid silicon +10.8 %, +0.21 g; 130 mm wrist free span 13.93 mm, tilt 68.0°.
  - 41 × 34: +70.0 mm², +21.6 %, +0.43 g; 14.19 mm, 69.9°. The 0.50 mm PV glass reaches the parts at 4.15 bar simply supported ⚠.
  - V3-G9 pass 1 is FAIL as written at both (the §9 numbers change); the fit holds, 0 interference.
- **Longer pod (level 3).** 42 × 32: +28.0 mm², +0.20 g, wrist extension −1.4 to −1.5°.
- **Motor (level 4).** Other legal Ø8 positions +0.0 mm²; notch +4.2; Ø7 +13.7 (0.10 Grms, 53 / 85 mA); Ø6 does not fit in Z (0.25 mm into the laminate); no motor +71.6 mm².
- **Gate 1.** No CAD option alone passes with the stage-1 netlist (516.4 mm² with DNP lands and fiducials). Largest courtyard that fits at 0.62 on v1's measure ⚠: L1-A 400.2; L1-A3 405.4; L2-33A3 425.1; L2-34A3 444.7; L3-42A4 426.8; L23-42x33A3 441.3; L4-noneA3 454.5 mm². The real placement decides (V3-G1, not run in this lane).

