# V3-G3a: SIM-10 antenna, SIM-11 link (V3-F stage 2b, pod 41 × 34)

## 中文摘要
- 结论：**PARTIAL**。门 3a 最低要求在标称值上满足：人体上总效率 1.29 %（≥ 1 % ✅），2 m 链路裕量 14.5 dB（≥ 13 dB ✅）。
- 但余量很薄：按器件、焊盘和走线公差做 Monte Carlo，效率中位 1.05 %，P5 0.64 %，只有 57 % 达到 ≥ 1 %（PARTIAL）；P5 时链路裕量 11.5 dB。
- ARCH §9 目标未达到：效率 ≥ 5 % ❌，人体 S11 ≤ −10 dB ❌（−6.9 dB）；自由空间 S11 ≤ −6 dB ✅（−7.1 dB）；SIM-11 ≥ 10 dB ✅。
- 选定辐射体 PA：在 5 × 3 mm 禁布区（被 R4.5 板角切掉大半）里，F.Cu 和 B.Cu 铺满铜，两个过孔相连，作电容耦合“地板激励器”。真正辐射的是整块板地。
- π 网络：C213 焊盘装 1.1 nH LQG15HS1N1B02（芯片侧并联），C215 焊盘装 5.1 nH LQG15HS5N1B02（串联），L204 不装；π 网络到馈点的走线 0.5 mm。
- 自由空间到人体的失谐：−10 MHz（S11 最小点 2.44 → 2.43 GHz）。辐射效率：自由空间 28.9 %，人体 4.3 %（2.44 GHz）。
- 主要损耗在电感（网络损耗 4.4 dB）。估算：换成 Q≈60 的绕线电感，效率约 2.1 % ⚠，但没有 S2P 数据。
- 对布局的要求：AE1 放在板坐标 (0,0)、0°、正面；全部 6 层禁布；馈点板坐标 (2.75, 3.0)；π 网络必须紧贴馈点（现在 rf_geom 里的 8 mm 线必须取消）；两条地边缘用过孔缝合。
- 窗框 E-1 接地与否影响很小（−2 %）。
- 用了 5 次 FDTD（预算 6 次）。

## 1. Scene (common/scene_v3f.py, geometry read live from v3/cad/src/geom_v3f.py, option L41W34_fold1p9_fpcdwg_jointzif_raise0p15, stage 2b)
Board 38 × 31 as PEC ground (all layers merged; motor cut-out), FR-4 in the keep-out pocket; floor PC film + carrier; Ti plates E1/E2
(PEC, RF-tied as in V2-B); PPG mesa (PC); motor can Ø8 (PEC); flat two-glass lid top Z 5.395 (window glass 0.70 + film/OCA,
PV laminate glass 0.50 + encapsulant); PV strips (4 PEC sheets) + lid tail to J6; display panel as a PEC sheet + panel glass, FPC top run,
fold, return run on the board, J13 tie; stainless window frame (cut back 5 mm around the keep-out) grounded at the E3 end (E-1 finger);
rib insert (PEC, posts floating 0.25 mm above the board); stainless rail section X 11.5–33.7 (GF-LCP section and posts dielectric);
K-block pins on J15/J18; E3 strip + wrap + J11 finger; root-B tails (PV_W+ | GND) tied to the board at land B, into the c-Si wing
silicon (s 2.45–7.75, PEC); root-A tails tied at land A into the capsule cell foil (30 × 10, PEC); TPU roots, capsule and wing laminate
dielectrics; wrist phantom of V2-B (ellipse a 28 / b 22.4, skin 1.5 / fat 2.5 / muscle, Gabriel 2.44 GHz) for the body case.
Strap path: free span from the bar tangent to the wrist ellipse (model of geom_v3f.wrist_geo). Free space = same pod and roots, no tissue.
Port: delta gap at the Y 3.0 (board) ground edge on F.Cu, 50 Ω source; Z from gap V and Ampere loop; η_rad = flux in air / P_acc
(tooling from v2/gates/g3a, unchanged). Match: matchlib (Murata GJM1555 / LQG15HS S2P, lands 0.058 pF, CPWG loss) ≤ 2 parts.

## 2. Results

| Case | Criterion (as written) | Value | Status |
|---|---|---|---|
| Screening PA fill booster, body, coarse | — | Z 3.7 − 152j Ω, η_rad 4.3 %, η_tot 1.26 % | chosen |
| Screening PB shorted loop, body, coarse | — | Z 0.3 + 43.7j Ω, η_rad 13.6 %, η_tot 0.90 % (S11-ranked net) | rejected ¹ |
| G3a min: η_tot body (PA, fine) | ≥ 1 % | 1.29 % (2.40 / 2.44 / 2.48 GHz: 1.30 / 1.43 / 1.29 %) | PASS |
| G3a min under tolerances (400 MC) | ≥ 1 % | median 1.05 %, P5 0.64 %, yield 57 % | PARTIAL |
| G3a min: link margin, 2 m, 15 dB shadow, phone −5 dBi | ≥ 13 dB | 14.5 dB (11.5 dB at the efficiency P5) | PASS |
| ARCH §9 SIM-10 η_tot body | ≥ 5 % ⚠ | 1.29 % | FAIL |
| ARCH §9 SIM-10 S11 body, ≤ 2-part π-net | ≤ −10 dB | −6.9 dB | FAIL |
| ARCH §9 SIM-10 S11 free | ≤ −6 dB | −7.1 dB | PASS |
| ARCH §9 SIM-11 margin | ≥ 10 dB | 14.5 dB | PASS |
| Free space η_tot / η_rad (2.44 GHz) | — | 9.0 % / 28.9 % | info |
| Detuning free → body | — | −10 MHz (S11 minimum 2.44 → 2.43 GHz); Z shift +0.3 Ω, +1.3j Ω | info |
| Sensitivity: window frame floating (no E-1 finger), coarse body | — | η_tot 1.238 % vs 1.261 % nominal (−2 %) | info |
| Mesh: same π-net, coarse vs fine body | — | 1.26 % vs 1.29 % | info |

¹ PB: 0.3 Ω radiation resistance; the PEC model omits copper loss of the trace (≈ 0.1–0.2 Ω ⚠), which would take it below PA.

Sensitivity of the chosen net (fine body): series 4.7 nH → 0.71 %, 5.6 nH → 0.39 %; line π-net → feed 1.0 mm → 0.54 %, 2.0 mm → 0.14 %.
The element is very high-Q (|X|/R ≈ 45): every 0.5 mm of line and every 0.1 nH counts.
Estimate (hiq_estimate.py, ideal parts, no lands ⚠): Q_L 60 inductors (wire-wound class) → about 2.1 %; Q_L 20 → about 1.3 %.

## 3. Radiator and match (export/)
- `export/AE1_PA_fill_booster.json`: F.Cu and B.Cu polygons (board frame), vias (board (3.75, 1.50) and (2.00, 1.75), drill 0.2 / pad 0.4,
  net FEED), feed point board (2.75, 3.00) on F.Cu, copper-free region on all 6 layers (the keep-out ∩ board), layout rules.
- `export/AE1_PA_fill_booster.kicad_mod`: footprint (origin = board (0, 0); place AE1 at board (0, 0), rot 0, front = KiCad (100, 130));
  pads FEED (F.Cu custom, B.Cu custom, 2 thru vias) and GND (0.5 × 0.25 pad in the pour at board (3.5–4.0, 3.0–3.25));
  rule area "AE1_keepout" on all copper layers (no tracks, vias, pours, footprints). Parsed by kicad-cli 10.0.7 `fp upgrade` (exit 0).
- No short point: PA is an open (capacitive) element; the GND pin of AE1 is only the pour pad.
- π-net: C213 land = **1.1 nH LQG15HS1N1B02** (chip-side shunt), C215 land = **5.1 nH LQG15HS5N1B02** (series), L204 = **DNP**;
  line π-net → feed point 0.5 mm. The schematic's value and part change on C213 / C215 (inductors on "C" lands, 0402) is the schematic lane's.

## 4. What the layout must do
1. Drop in AE1_PA_fill_booster at board (0, 0); nothing else in the pocket on any layer.
2. Move the π-net to the feed point: the C215 antenna-side pad within 0.5 mm of board (2.75, 3.00) (the 8.0 mm CPWG of rf_geom.py / C-14 no longer applies);
   C213 next to it; L204 land kept (DNP) only if it costs no line length.
3. Ground edges Y 3.0 (X 0.26–5.0) and X 5.0 (Y 0–3.0) solid on all layers, stitched with GND vias at ≤ 1.0 mm, 0.3–0.5 mm back from the edge.
4. Copper to the routed edge ≥ 0.30 mm (as modelled). Radiator vias filled / tented.

## 5. Estimates and open items
- [E] materials (PC, LCP, TPU, panel glass, capsule), FR-4 tan δ 0.02; display as a PEC sheet; plates RF-tied to the board; PEC copper (no copper loss).
- Not modelled: the 0.8 mm stainless lug/hinge pins along X 3–38 (`LUG bar_d`, not in this task's list; 1–2 mm from the antenna corner — should be checked),
  the textile band beyond the roots, hand / sleeve variants, wing absent / wet strap.
- SIM-09 insertion loss 0.24 dB is the v1 QFN value (`sim/rf/sim09_match`); the WLCSP re-run value was not found ❓.
- The result is marginal: an RF bench check of AE1 + π-net on the first boards (S11 tune with the 4.7 / 5.1 / 5.6 nH and 1.0 / 1.1 / 1.2 nH set) is required.
- Options if more margin is wanted: wire-wound series inductor (needs a part with S2P data), a larger keep-out, or the nRF52840 respin (+4 dB TX, R4).
