# SCOUT - lid radiator vs board radiator (V3-F, coarse mesh, on the body), 2026-11-15

## 中文摘要
- 两次 FDTD（粗网格、手腕模型、场景与板载辐射体 PA_body_c 相同，仅辐射体换到盖板玻璃内表面，由弹簧指从板上馈点馈电）。✅
- L1（直条，长壁内侧 X 4.0–10.5、Y 1.5–2.0，开路端距接地不锈钢框 0.6 mm）：Z = 7.5 − 128.6j Ω，η_rad 16.9 %；
  多层电感网络 η_tot 8.8 %（板载同口径 1.36 %，+8.1 dB；对 1.26 % 的固定网络 +8.4 dB）；Q 60 电感 11.9 %（板载 2.16 %，+7.4 dB）。✅（粗网格 ⚠）
- L2（L1 + 第二弹簧接地的倒 F）：Z = 0.8 + 65j Ω，短路环太近馈点、R 过低，η_rad 16.3 % 但 η_tot 仅 5.4 %（+6.0 dB）；比 L1 差。✅
- 无谐振：2.0–2.9 GHz 内 L1 仍为容性（玻璃加载下 λ/4 约 18–24 mm，长壁只容 ~12 mm 路径），靠 π 网络匹配。
- 自由空间失谐（−10 MHz 类）：未跑（NOT_RUN）；仅体上结果。
- 结论：增益约 +7…8 dB，远大于粗/细网格差（2 %）和任何板上手段；值得做完整设计（自由空间、细网格、公差、手/袖子）。

## Set-up (✅ produced by the runs named)
Scene `../common/scene_v3f.py` unchanged (PV strips, grounded frame + E-1 finger, rib insert, stainless rail X 11.5-33.7, rim pins,
E3 strip, panel sheet, FPC, motor, plates, wing, capsule foil, strap tails); only the board radiator removed (`scene_lid.py`).
The 5 x 3 keep-out pocket stays copper-free FR-4. Port = the board runs' delta gap (case Y 4.25-4.5, X 4.0-4.5, z 1.0).
Feed: F.Cu leg X 4.0-4.5, Y 2.5-4.25 in the pocket -> spring finger 0.5 x 0.5 (land Y 2.5-3.0) z 1.0 -> 3.5 (glass inner face,
Z_case win0 3.545 snapped). Lid: jog X 4.0-4.5 Y 2.0-3.0, strip 0.5 wide Y 1.5-2.0, X 4.0-10.5.
L2 adds a lid bridge Y 2.75-3.25 to X 2.5, stub X 2.5-3.0 to Y 5.0 and a shorting spring X 2.5-3.0, Y 4.5-5.0 onto the Y 4.5 ground.
Mesh: v3f level c with the 0.25 mm zone widened to X 0-12 (3.65 M cells vs 3.53 M) ⚠ small mesh difference to PA_body_c.
Runs: `launch_lid.sh L1|L2 body` (604 / 599 s wall, decay 5e-5). Post: `post_lid.py` (board re-evaluated on the same basis).
Length choice L1: the glass-loaded quarter wave is ~18-24 mm (eps_eff ~1.6-2.8 ⚠), the long-wall border offers only X 4.0-10.5
before the grounded frame (X 11.1) and the stainless rail (X 11.5); path feed->open ~12 mm (leg 1.75 + spring 2.5 + lid 7.5).
So L1 is the maximum length, not a resonant one; the strip's end-coupling to the frame adds loading.
L2 reason: an inverted-F lets a metal short (Q > 200) cancel the arm's capacitance instead of the lossy chip inductors.

## Results (in band 2.40-2.48 GHz, minimum; l_b 0.5 mm; body-only ranking, no free run)
| run | Z @ 2.44 (ohm) | eta_rad 2.44 | eta_tot multilayer (net) | eta_tot Q 60 | gain vs board (ML / Q60) |
|---|---|---|---|---|---|
| board PA_body_c | 3.7 - 152j | 4.27 % | 1.36 % (A 1.0 nH, S 5.1 nH); 1.26 % fixed net | 2.16 % | 0 |
| L1 lid strip | 7.5 - 128.6j | 16.9 % | 8.81 % (A 1.5 nH, S 4.3 nH), RL 8.1 dB | 11.9 % | +8.1 / +7.4 dB |
| L2 lid IFA | 0.8 + 65.1j | 16.3 % | 5.40 % (A 2.9 pF, S 0.9 pF), RL 3.3 dB | 7.5 % | +6.0 / +5.4 dB |
eta_rad gain alone: +6.0 dB (L1). Network loss L1 2.1 dB vs board 4.1 dB. Detuning free -> body: NOT_RUN (no free run).

## What it would need
- Lid: printed silver (or LDS / FPC laminate) strip 0.5 x ~7 mm + jog on the window glass inner face in the frame cut-back border
  (X 4-10.5, Y 1.5-3.0), with a contact pad for the spring; the stainless frame's cut-back edge stays >= 0.6 mm from the open end
  (moving it further back, X >= 13, would allow a longer strip; the rail's stainless section stays from X 11.5).
- Board: the 5 x 3 keep-out stays copper-free (the strip needs no ground under its feed end); radiator copper replaced by a
  0.5 mm feed leg + spring land (~1.0 x 1.0 mm); pi-net (2 x 0402) at the feed as now. No added board area.
- Part: one SMT spring finger, 2.5 mm working height (~2.7 free), 0.5-1 mm footprint, e.g. a gold-plated contact class ⚠.
- Cost: +1 spring (~0.05-0.15 USD ⚠), lid print + contact pad (an extra step on the glass: decoration print class), assembly
  tolerance check at lid closing. Thickness: none (inside the 2.5 mm board-to-glass gap; parts zone stays below the spring).

## Risks
- Hand / sleeve over the lid: the radiator is now on the top face, 0.7 mm glass from a covering hand -> larger detuning and loss
  than the board radiator (not simulated). - Spring tolerance: contact force, travel +-0.3 mm, contact resistance (mOhm level is fine,
  intermittent contact is not); lid re-assembly wears the pad. - Feed inductance of the spring changes with height (~1 nH/mm ⚠).
- Coarse mesh only, no free run: the thin strip near the frame is mesh-sensitive; L2's tap position was not tuned.

## Recommendation
Worth a full design: free-space run (detuning, ARCH §9 check), fine mesh, spring height +-0.3 mm and frame-gap tolerance,
a hand-over-lid case. Base it on L1 (straight strip, open end); the IFA needs its tap/short re-placed before it competes.
