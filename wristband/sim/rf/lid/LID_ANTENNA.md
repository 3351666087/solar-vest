# V3-G3a: lid antenna L1 (V3-F stage 2b, pod 41 × 34), 2026-11-15

## 中文摘要
- 结论：**PARTIAL**。门 3a 最低要求和 ARCH §9 目标在标称值上全部满足；没过的是戴手、公差最坏角和弹簧图纸三项。
- 按实物做的模型（BW0019BG 弹簧，条带 X 5.125–12.375，窗框切到 X 13，表带销，细网格）在人体上的总效率是 **12.6 %**（板载方案 1.29 %，高 +9.9 dB）。S11 人体上 −10.3 dB，自由空间 −10.7 dB（估算）。链路裕量 **24.7 dB**。
- π 网络：C215 串联 **9.0 nH LQW15AN9N0G80D（C6652901，库存 5395）**，L204 天线侧并联 **6.2 nH LQW15AN6N2B80D（C668465，库存 8018）**，C213 不装。两颗都是 JLC 现货的绕线高 Q 件。
- 公差 Monte Carlo（600 次）：效率 P5 7.0 %，≥1 % 和 ≥5 % 的比例都是 100 %。但 S11 ≤ −10 dB 只有 10 % 能做到，所以首批板要上台架调 S11。
- 自由空间到人体几乎不失谐（0 MHz，网格 5 MHz）：条带在盖板上，离手腕远。
- 手压在盖板上时效率 1.35 %，链路 15.0 dB。门 3a 最低要求过了，ARCH 5 % 没过。
- 公差最坏角（条带下沉 0.25 mm，开口端间隙 0.375 mm，约为实际公差的 2 倍）：效率 4.1 %，链路 19.9 dB。说明效率对条带到板的高度很敏感，约 −24 Ω/0.25 mm。
- 弹簧：理想位置（X 4.0–4.5）放不下任何现货弹簧，所以改用 BW0019BG-L3.5W1.5H3.8（C2826516，库存 17846，镀金）。它在板坐标 (3.30, 1.55)、转 340°，触点在 (3.84, 1.36)。板到玻璃的距离是 2.445–2.545 mm。图纸 PDF 读不出来，工作高度还没有核实 ⚠。
- 窗框要改：长边边带（Y 0.5–5.65）在 X < 13.0 的部分去掉，原来到 X 11.4–11.5。显示屏、膜开口和导轨都不动。
- FDTD 用了 5 次，同时最多跑 2 次。

## 1. Geometry (case frame unless noted; board = case − 1.5)
| Item | Value | Source |
|---|---|---|
| Glass inner face | Z_case 3.895 (z 3.545 → grid 3.5) | geom_v3f stage 2b ✅ |
| Board top → glass inner face | 2.445 mm (1.10 max board, Z.pcb1 1.45) … 2.545 mm (1.0 board) | geom_v3f ✅ |
| Lid strip | 0.5 wide, Y 1.5–2.0, X 5.125–12.375 | this lane |
| Jog / contact pad | jog X 5.125–5.625, Y 2.0–2.375; pad X 3.875–5.875, Y 2.375–3.625 | covers the contact (5.34, 2.86) and its 180° image (4.26, 3.25) |
| Window frame | cut back for X < 13.0 in Y 0.5–5.65; open end to frame 0.625 mm | frame X 11.38 → 13.0 |
| Spring J40 | BW0019BG land 2.10 × 1.50, centre board (3.30, 1.55), rot 340°, body inside the pocket | EasyEDA footprint of C2826516 ✅ |
| Feed | F.Cu leg board X 2.5–3.0 from the feed point (2.75, 3.00) to the land; no via, no B.Cu | export/AE1_lid_L1.* |
| Strap-bar pins | Ø0.8 stainless pins, X 3–38, Y −1.5 / 35.5, Z_case 0.85 (model_v3f bar_*_ss) | in runs E, D, H |

Why the feed moved: a 0.5 × 0.5 spring at X 4.0–4.5 (scout, runs A/B) cannot be built. Pogo pins need a Ø2.3 land, and BW-class fingers are 3.5 mm
long. Inside the R4.5-cut pocket only BW0019BG at rot 340 fits with its whole body over copper-free FR-4. A body over solder-masked ground would add
about 2 pF ⚠. So runs E/D/H use the as-built feed. A/B (ideal feed) supply the free-space shift and stay as information.

## 2. FDTD runs (fine mesh: 0.125 mm zone X 0–13.5, Y 0–6, port gap 0.125; tooling copied from ../scout_lid and ../common)
| Run | Scene | Z @ 2.40 / 2.44 / 2.48 GHz (Ω) | η_rad 2.44 |
|---|---|---|---|
| A_body_f | ideal feed, body | 6.9−104.7j / 6.5−100.5j / 5.9−96.7j | 18.5 % |
| B_free_f | ideal feed, free | 5.1−106.1j / 5.6−100.0j / 6.8−96.0j | 70 % ⚠ (noisy: 56–95 %) |
| E_body_f | as built + pins, body | 12.7−83.6j / 9.1−81.5j / 6.1−77.8j | 19.9 % |
| D_body_f | E + strip −0.25 mm, frame X 12.75 | 9.1−108.3j / 6.8−105.8j / 4.9−102.4j | 16.8 % |
| H_body_f | E + hand on the lid (skin 1.5 + muscle 10.5) | 26.1−8.3j / 27.3−5.7j / 29.0−3.4j | 8.0 % |
Free space as built = B + (E − A) impedance shift ⚠ (no budget for a sixth run). All runs rc 0, decay 1e-4.

## 3. Match (real parts; ../matchlib chain: 50 Ω node, CPWG 3 mm, loaded empty lands, l_b 0.5 mm)
- **C215 (series) = 9.0 nH LQW15AN9N0G80D, C6652901**; **L204 (antenna-side shunt) = 6.2 nH LQW15AN6N2B80D, C668465**; **C213 = DNP**.
  All three lands stay 0402. Stock was read today from the JLC parts API (both Extended).
- Inductor model ⚠: Murata gives Q only as a minimum at 250 MHz. Read today: 1.3–1.5 nH 20, 2.4 nH 30, 4.3 nH 32, 6.2 nH 33. 9.0 nH is not read; the model
  uses 32. Q(f) = 0.7 · Q250 · √(f/250 MHz). SRF: 4.3 nH 9.6 GHz and 2.4 nH 15.5 GHz are read; the others are scaled. No S2P for LQW15AN in the library.
  Sensitivity: with KQ 0.5 instead of 0.7, η 12.1 %; with KQ 1.0, η 13.0 %.
- Rule: the highest in-band minimum body efficiency among the nets that meet both ARCH S11 criteria. The best net with no S11 rule is
  8.4 nH series / 7.1 nH shunt: 13.2 %, S11 −6.2 dB. The best LQG15HS multilayer net is 1.3 nH / 2.7 nH: 12.8 %, S11 −6.9 dB.
- In band, as built on the body: η_tot 12.6 / 16.7 / 18.7 % (2.40 / 2.44 / 2.48), network loss ≤ 1.04 dB, S11 ≤ −10.27 dB. Free (estimate): S11 ≤ −10.7 dB, η_tot ≥ 41 % ⚠.
- Detuning free → body: 0 MHz at the S11 minimum (2.44 GHz both).

## 4. Results against the criteria (as written)
| Case | Criterion | Result | Status |
|---|---|---|---|
| G3a min: η_tot body (as built, fine) | ≥ 1 % | 12.6 % | PASS |
| G3a min under tolerances (600 MC ¹) | ≥ 1 % | median 9.9 %, P5 7.0 %, yield 100 % | PASS |
| G3a min: link 2 m | ≥ 13 dB | 24.7 dB (P5 22.1 dB) | PASS |
| ARCH §9 η_tot body | ≥ 5 % | 12.6 %; MC yield ≥ 5 %: 100 % (86 % at the full modelled offset ²) | PASS |
| ARCH §9 S11 body | ≤ −10 dB | −10.27 dB nominal (MC: only 10 % ≤ −10 dB, median −6.4 dB) | PASS |
| ARCH §9 S11 free | ≤ −6 dB | −10.7 dB ⚠ (B + (E−A) estimate) | PASS |
| ARCH §9 SIM-11 margin | ≥ 10 dB | 24.7 dB | PASS |
| (c) hand on the lid vs G3a min | ≥ 1 %, ≥ 13 dB | 1.35 %, 15.0 dB (S11 −1.0 dB, η_rad 8 %) | PASS |
| (c) hand on the lid vs ARCH §9 | ≥ 5 % | 1.35 % | FAIL |
| (d) tolerance corner ² vs G3a min | ≥ 1 %, ≥ 13 dB | 4.1 %, 19.9 dB | PASS |
| (d) tolerance corner ² vs ARCH §9 | ≥ 5 %, S11 ≤ −10 dB | 4.1 %, −2.1 dB | FAIL |
| (e) strap-bar pins | ≥ 1 % (G3a min) | 12.6 % with the pins in; their isolated effect is not separated (E also carries the as-built feed) | PASS |
| Spring drawing read (task 3) | read | PDF not machine-readable; land read from the JLC/EasyEDA footprint; working height ❓ | PARTIAL |
¹ parts by tolerance code, lands ±30 %, shunt return ±50 %, l_b ±0.25 mm; mechanics t ∈ [0, 0.6] of the E→D offset, harmful side only (0.6 ≈ real
tolerance ±0.12 mm height, ±0.2 mm gap over the modelled 0.25 / 0.25 ⚠); strip print length ±0.1 mm as a frequency scaling ⚠.
² D models the strip 0.25 mm lower and the gap 0.375 mm, about twice the real tolerance. Height dominates: ΔX ≈ −24 Ω.

## 5. SIM-11 (lid/sim11_link.py, assumptions of ../RF.md: 2 m, 15 dB shadow, phone −5 dBi, 4 dBm / −96 dBm, SIM-09 match loss)
Margin 24.7 dB nominal; 22.1 dB at the efficiency P5; 19.9 dB at corner D; 15.0 dB with a hand on the lid. Range at 10 dB margin: 10.9 m (free-space slope).

## 6. What must change
**Schematic (v3/design):**
- AE1 → footprint `AE1_lid_L1`, value "lid strip L1 feed".
- New **J40** BW0019BG-L3.5W1.5H3.8 (C2826516) on ANT_FEED: one pad, class M, JLC rot 340°.
- **C215** → 9.0 nH LQW15AN9N0G80D (C6652901), an inductor on the 0402 "C" land.
- **L204** → 6.2 nH LQW15AN6N2B80D (C668465), fitted.
- **C213** stays DNP.
- The LEAD_NOTES A-3 values (5.1 nH on C215, 1.1 nH on C213) are withdrawn.

**Layout:**
- Place AE1 at board (0, 0), rot 0, front. Its rule area keeps the pocket free on all 6 layers; the only copper there is the FEED pad (leg + J40 land, F.Cu).
- Place J40 at board (3.30, 1.55), rot 340°. No other part, via or copper above or in the pocket.
- Keep a clear volume from the pocket to the glass for J40: free height 3.8 mm, compressed to 2.45–2.55 mm.
- A-2 stays, with L204 as the antenna-side shunt: the C215 antenna-side pad and the L204 pad within 0.5 mm of line from the feed point (2.75, 3.00).
  The ground edges are solid and stitched at ≤ 1.0 mm pitch.

**CAD (v3/cad):**
- frame_outline: subtract sbox(·, ·, 13.0, 5.65). Extend the antenna-corner PC seat (ant_seat) to X 13.0. Add the frame cut to the zone files.
- Lid print: silver strip + pad on the glass inner face as in §1. The pad gets a gold or ENIG-equivalent finish, or use an LDS carrier with the same outline. No IR-cut coating (T-2) and no
  decoration print over the pad. Strip and pad stay inside Y < 5.65, outside the display window.
- Lid-to-board registration ±0.3 mm in X/Y: the pad covers it.
- Glass inner face to board top 2.445–2.545 mm: check that this lies inside J40's working range once the drawing is read.
- The board-to-glass height is the most sensitive dimension: about −24 Ω of reactance per 0.25 mm. Tolerance target ±0.10 mm.
- Bench list: S11 tune on first boards. Contact resistance of J40 to the pad after 20 lid closings. Hand-on-lid link check.

## 7. Open items
1. BW0019BG drawing (working and limit height, contact force) not read. The PDF is image-only; it needs a manual read or a download approved by the user.
2. The LQW15AN Q–f curves are not read: Q is extrapolated from the 250 MHz minimum (⚠), and the 9.0 nH Q min is not read.
3. Free-space as built is an estimate (no sixth run). Free-space η_rad from B is noisy.
4. Pin effect is not isolated. S11 ≤ −10 dB is met only at nominal (10 % MC yield): a bench tune is needed.
5. Mechanical check of the glass corner without the frame to X 13 (support on the PC seat) belongs to the mechanics lane.

Files: `lid/scene_lid.py`, `run_lid.py`, `launch_lid.sh`, `post_lid.py`, `export_lid.py`, `sim11_link.py`; `runs/*_f.npz`; `results/post.json`,
`results/sim11_results.json`, `results/sim11_lid_p5.json`; `export/AE1_lid_L1.json`, `export/AE1_lid_L1.kicad_mod` (kicad-cli 10.0.7 fp upgrade rc 0);
`lid_results.json`.
