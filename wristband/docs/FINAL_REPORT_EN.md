# SolarBand V3-F: final delivery report (2026-11-17)

> Marks: ✅ produced today by a named tool or read in a named file; ⚠ model estimate; ❓ unknown. Every number comes from simulation or calculation. **No physical test has been done.**

## 1. What the band is
SolarBand V3-F is a light-harvesting health band. PV strips on the lid and PV cells on a strap wing charge the battery while it is worn.
The pod carries ECG (two skin plates plus a third electrode on the lid), PPG (heart rate / SpO2), skin temperature, an IMU,
a 1.08" reflective display, Bluetooth LE and a vibration motor. The battery sits in a capsule at a strap root; cable charging goes
through the supplied isolated magnetic USB-C head.

## 2. Delivery state
- Board closed: 8 layers, board 40 × 34 mm, pod 43 × 37 mm, 242 parts, **0 unconnected, 0 DRC errors** ✅ (kicad-cli 10.0.7, --refill-zones).
- Delivery board `v3/final/board/solarband_v3f_final_rf.kicad_pcb`: the closed board `v3/finish/solarband_v3f_final.kicad_pcb` with only the
  footprint IDs and values of C215, L204 (antenna re-tune) and R172 (R-172) changed, same lands; every Gerber and drill file is identical to the run before ✅.
- JLC package `v3/package/final`: `make_package.sh` exit 0 ✅; placement gate GREEN 192, PREVIEW 15, YELLOW/RED/UNKNOWN 0; G7 207/207; G8 PASS;
  BOM 91 lines, 207 placements (run 2026-11-16 19:50 UTC).
- R172 is now **C166160 RALEC RTT015362FTH** (53.6 k, 0201, 1 %, 38 325 orderable ✅). Only U15 has 0 orderable; U4/U5 54 (purchase note B-1, section 9).

## 3. Key numbers against the market (⚠ model)
| Item | SolarBand V3-F | Market |
|---|---|---|
| Thickness (max material) | **5.395 mm**, flat top | thinnest product 8.3 mm, median 10.6 mm (35 % thinner) |
| Dark autonomy T1 | **38.4 d** (night blank); face always on 34.3 d; worst stack 21.9 d | band median 8 d (about 4.8×) |
| Indoor 300 lx (W2) / low outdoor office (W7) | 40.2 d / 43.9 d from full | – |
| Office, 20 min sun, campus day | energy-positive (no cable needed) | – |
| Daily light need at 0.45 sun | 12.9 min (overcast 57 min) | – |
| USB full charge T7 | 2.14 h (1.98–2.34) | – |
| Mass | pod 11.9 g, worn about 21.4 g | – |
| Length along the forearm | 43 mm | mainstream bands 22.5–24.9 mm (ours is longer) |
| PV silicon | lid 333.8 mm² + wing 158.1 mm² | – |
| Antenna | 12.3 % efficiency on the body, link margin 24.4 dB | – |
Sources: `v3/track2/calc/baseline_calc_t2.json`, `v3/track2/track2.json`, `v3/sim/rf/final/RF_FINAL.md`.

## 4. Verified by simulation (all ⚠ model output, not experiments)
| Item | Result | Verdict |
|---|---|---|
| Power and energy (SIM-03/05) | SIM-05 passes; SIM-03 gaps handled by rulings | PASS / recorded deviations |
| Thermal SIM-13, worst corner (low perfusion, wind × 0.6, prints α 0.20) | pod bottom 42.82 °C, motor at 5 % duty 42.88 °C ≤ 43 | PASS (0.12 K margin) |
| 5 bar water load | PV glass 0.60 (L-6): 22.4 / 14.9 bar at 169 MPa (0.50 would reach 228 MPa); window 17.3 / 7.3 bar; rail 14.63 / 6.16 bar | PASS (stress ⚠) |
| Drop, corner bumpers | 0.36 mm gave −0.006 mm at 30° with 11.87 g; RFQ now 0.37 mm (L-6), not re-simulated | PARTIAL until checked |
| Fit 130–200 mm, either wrist | all pass; wrist extension 38.8° < 40° | PASS / recorded cost |
| Antenna on the final board (real J40 position) | 12.29 %, S11 −10.44 dB, free space −11.04 dB, hand 1.43 % | PASS; only 19 % of builds reach S11 ≤ −10 dB |
| ECG noise M2 (≤ 10 µVpp) | **6.23 µVpp** under the firmware rules F-9, P-2 and P-2b (without P-2b: 613.8) | PASS (firmware requirements) |
| Patient DC current (criterion F-3) | normal 2.48 µA ≤ 10; worst single fault 25.39 µA ≤ 50 | PASS (fails the old < 10 µA figure) |
| ESD at the GND contact J18 (case 5c) | drain peaks 66–80 V for 0.2–0.7 ns against a 60 V part | recorded residual; maker's test decides |
| Schematic ERC / netlists | ERC 0 errors, 0 differences on 11 variants ✅ | PASS |
| Board DRC / placement gate | 0 / 0; GREEN 192 / PREVIEW 15 ✅ | PASS |

## 5. Not verified
- No prototype, no lab measurement, no wear trial, no water test.
- Antenna: the impedance at J40's final position is an estimate (the coarse FDTD run was unusable, no budget left); a bench S11 tune is needed.
- Stack-up: whether JLC builds 8 layers at 1.0 mm is not confirmed ❓ (1.2 mm adds 0.22 mm to the pod); line impedances are estimates.
- The IR-cut coating effect (about 40 %) is assumed; it needs a vendor value.
- No samples or RFQ answers yet for the pack, lid, capsule or motor.

## 6. Residual risks (all)
1. **ECG relies on firmware**: IMU_INT1, SPI_SCK and PPG_INT run over plate E1. M2 passes only with the firmware requirements F-9, P-2 and
   **P-2b (adopted)**: before recording, IMU INT1 off or IMU powered down, PPG and its interrupt paused, no flash writes (ECG in RAM or streamed over BLE).
   RAM: a 30 s session is about 45 KB of 64 KB (estimate); the firmware owner confirms.
2. Antenna S11 ≤ −10 dB in about 19 % of builds; J40 land corner 0.077 mm in plan from the inner ground (passes DRC, edge capacitance estimated); the Y 3.0 ground stitching has a 2.65 mm gap against a 1.0 mm rule.
3. ESD case 5c (J18 drain 6–20 V above rating for nanoseconds): the maker's IEC 61000-4-2 test decides.
4. Drop: bumpers 0.37 mm in the RFQ (L-6); capsule corner with the pod mass 0.82–0.84 > 0.707 mm (bench B8).
5. PV glass 0.60 mm in the RFQ (L-6; +0.15 g, top stays at 5.395 mm).
6. Thermal margin 0.12 K; the combined corner under the wing (low perfusion and wind) is 43.3–43.4 °C ⚠ (F-6: measure before any wear).
7. A dead band off the wrist needs about 330–690 lx to cold-start (target 200 lx; accepted deviation).
8. LQW15AN inductors are 0.60 mm at most; the clearance under the deeper rail is stated as 0.55 or 0.70 mm in different files: the CAD lane must re-check.
9. Wrist extension 38.8° < 40° (cost of the 43 mm pod).
10. P-7: one I2C via over E1; it relies wholly on firmware rule P-2 (+48 µVpp if P-2 fails).
11. Stock: U15 0 orderable, U4/U5 54 orderable (below the 5× rule); see B-1 in section 9. R172 solved (C166160).
12. The P-6 pin-map reviews live only in the YAML files; every `run_all.sh` wipes them (restored after the R-172 run).

## 7. Bench list for the manufacturer
1. 5-bar static water test (ISO 22810) with pressure film under the PV laminate, window and capsule top.
2. Coupons of the structural epoxy and elastic bead (0.5 MPa, bond lines 0.11–0.49 mm).
3. Rib and rail sag between posts, measured.
4. First-article CMM (seat heights, legs, FH34SRJ height as a maximum of 1.0 mm, panel thickness).
5. Capsule 30 N press; 6. capsule crush with a soft short (skin ≤ 43 °C, no venting); 7. steel-ball impact.
8. 1 m drops (window edge, four R6 corners, capsule edge; B8); 9. 10⁵ hinge bends plus leak test; 10. strap pull.
11. Motor run after a 5-bar soak; 12. button life and seal; 13. end-of-line leak test of every unit; 14. display after 5 bar.
15. Skin temperature under the wing (low perfusion with wind) before any wear (F-6).
16. Antenna bench S11 tune (the C213 land is kept free for it); J40 working height (L-5, ±0.10 mm).
17. Contact ESD (IEC 61000-4-2, J18/J15); leakage with each charger class; hi-pot of the heads.
18. ECG noise measured with the F-9 / P-2 / P-2b firmware; patient current measured.
19. Pack: ≥ 1.0 C charge rate, deep-discharge limit, fuse F1 fast-acting, clears ≥ 1.45 A within 0.5 s (E-7).
20. Power-on self test G10, LED/PD loop-back (D3/D4/PD1 polarity).

## 8. Items for the supervisor
1. **Worn charging rule:** cable charging stays off the wrist until the supervisor adopts the rule and the maker's leakage test passes; then only through reinforced heads.
2. **Skin-hot alert by vibration:** at most 5 % duty (mean ≤ 5.5 mW), or the motor's own heat exceeds the limit (T-4).
3. **Patient-current criterion F-3:** IEC 60601-1 structure, ≤ 10 µA normal and ≤ 50 µA single fault, replacing "< 10 µA in every case".
   The worst single fault, 25.39 µA, passes F-3 and fails the old figure.
4. **The P-7 exception:** at most two I2C vias over plate E1 (one used, 5.96 mm from a dot opening), valid only because there is no I2C traffic during ECG (P-2).

## 9. Purchases that wait for the user (none made)
1. Sharp LS011B7DH03 samples; custom 1.08" front-light film.
2. Pack RFQ and samples (≥ 66 mAh nominal, ≥ 1.0 C, UN 38.3 and IEC 62133-2 reports).
3. Lid RFQ (PV laminate on **0.60 mm** PV glass, window glass, stainless frame, **0.37 mm** corner bumpers, IR-cut coating, prints α ≤ 0.20, wing); capsule, strap-root and ring tooling (L-6).
4. ERM samples; isolated head prototypes and UCC12050.
5. **B-1:** BQ25170 (U15, 0 orderable) and INA236 (U4/U5, 54 orderable): the user chooses JLC consignment or a pre-order when ordering; the board does not change. Also lock MAX86141.
6. The JLC order (8-layer PCB + SMT), after confirming 8 layers at 1.0 mm.
Full list: `v3/decide/BASELINE.md` §19.

## 10. JLC package and preview checks before payment
- Upload set `v3/package/final/upload/`: `solarband_v3f_final_rf_gerbers_JLC.zip`, `BOM_JLC.csv`, `CPL_JLC.csv`, `PREVIEW_CHECKS.md`, `manifest.sha256`. The CPL comes from the gate; never edit it by hand.
- Before paying, tick the 15 PREVIEW rows in JLC's preview: D3, D4, PD1 (bottom); D9, D10, D11, D14, D16 (polarity); D12 (proxy land);
  J11, J15, J18, J19, J40 (single-pad spring fingers, J40 at 340°); SW1. Then the 62 rows of `review/checklist.md`, and the U19/U20 pin-1 mark (ECO3).
- Settle U15 and U4/U5 (B-1) first. To rebuild: `cd v3/package && STOCK=1 ./make_package.sh ../final/board/solarband_v3f_final_rf.kicad_pcb final`.

## 11. Where the files are
| Content | Path |
|---|---|
| This report, Chinese version, data | `v3/final/FINAL_REPORT_EN.md`, `FINAL_REPORT.md`, `final.json`, `PROGRESS.md` |
| Delivery board (KiCad) and DRC | `v3/final/board/solarband_v3f_final_rf.*`, `drc_r172.json` |
| Closed board as finished | `v3/finish/solarband_v3f_final.*`, `FINISH.md` |
| Board STEP and renders | `v3/final/img/solarband_v3f_final_board.step`, `board_top.png`, `board_bottom.png`, `board_iso.png` |
| Assembly renders and STEP | `v3/final/img/pod_iso.png`, `pod_top.png`, `pod_bottom.png`, `pod_exploded.png`, `pod_cut_window.png`, `worn_165_left*.png`, `pod_assembly.step`, `worn_165_left_assembly.step` |
| Production package | `v3/package/final/` (`FINAL_PACKAGE.md`, `upload/`, `review/`, `gate/`) |
| Specification | `v3/decide/BASELINE.md` (top block "Final (stage F)") |
| Schematic flow | `v3/design/` (`tools/run_all.sh`, `BOM_v3f.csv`) |
| Simulation results | `v3/sim/ecg/final/ECG_FINAL.md`, `v3/sim/rf/final/RF_FINAL.md`, `v3/sim/thermal/THERMAL.md`, `v3/sim/mech/MECH.md`, `v3/sim/power/POWER.md`, `v3/track2/TRACK2_CAD.md` |
| Rulings | `v3/LEAD_NOTES.md` |
