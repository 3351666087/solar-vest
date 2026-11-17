# V3-F lead notes (2026-11-15)

Read this first. Where it differs from older files, this file wins.

> Public copy: the working-mode section (instructions to the design agents about effort and quota) and scheduling notes were removed. Paths such as `v3/...` refer to the private work tree; the published copies are mapped in `wristband/README.md`.

## 2. The baseline now

V3-F as in `v3/decide/BASELINE.md` (stage-1 edits S1-01..S1-26), plus these lead decisions of 2026-11-15:

| # | Decision | Reason |
|---|---|---|
| a | Pod **41 × 34 mm**, board **38 × 31 mm** | Real placements are legal at every size tried, but only 41 × 34 comes close to gate 1's utilisation criterion. The extra width costs the wearer +0.42 g and no comfort, and gives +21.6 % lid PV silicon. |
| b | Display FPC routing "A3": outline as drawn, one fold 1.9 mm from the glass edge, return run on the board. Zero-height features (DNP lands, fiducials, test pads) may sit under the FPC ("ufpc"). | Frees the most board inside the maker's rules. |
| c | **J13 is a ZIF connector** from the panel maker's Table 8-1 (terminals face up after the fold). The panel is raised 0.15 mm: window half 5.305 mm. No soldered land, no bridge flex. | The maker's own method: no custom part, no solder on the panel FPC, reworkable. |
| d | The netlist is the dense level-0 schematic in `v3/design` (variant `v3f`). O-2 stays as built (16 parts). The LED chain and the Ø8 motor stay. | Level 4 was not needed. |
| e | **Gate 1's real criterion:** a legal placement and a complete, DRC-clean routing of the whole board under JLC's rules. Both utilisation measures are reported, but they no longer stop the layout. | The 0.62 figure was a planning proxy from v1. The real layout is the test. |
| f | PV glass 0.50 mm gives 4.15 bar simply supported at 34 mm width. SIM-14 decides between the bonded support and 0.55–0.60 mm glass. The PV half may grow up to the window half without changing the pod's maximum thickness. | |
| g | **Parked, do not work on:** the isolated head (`v3/head`), the 40 mm pod, option levels 3 and 4, the supervisor's items (worn charging, skin-hot LED). | Economy. |

## 2b. Decisions after the power and energy simulations (`v3/sim/power/POWER.md`, 2026-11-15)

SIM-05 passes in every case. SIM-03: 22 PASS, 4 PARTIAL, 2 FAIL. The lead's rulings:

| Item | Ruling |
|---|---|
| R172 52.3 k → **53.6 k** (O-2 hot stop ≤ 45.0 °C down to a 1.30 V supply) | Adopt. Same footprint. |
| R105 294 k → **383 k** (VBAT_OK hysteresis 118 mV, no chatter) | Adopt. Same footprint. |
| Q8 single fault with the MCU off: PV + USB reach 0.71–0.83 C | Accepted as a single-fault case: it stays below the cell's 1.0 C maximum charge rate ✅ (pack data sheet). No part added. The pack RFQ must confirm ≥ 1.0 C. |
| Dead band off the wrist does not cold-start at 200 lx (the O-2 comparator is not yet powered); it needs 330–690 lx on the 41 × 34 lid | Accepted deviation from the "cold start at 200 lx" target: the O-2 safety inhibit comes first. Stated to the user as: a dead band restarts in daylight, in bright room light (≥ about 350–700 lx), or on the charging head. |
| Deep discharge: 0.84–0.89 C into a 0 V cell | No change; the pack RFQ asks for the maker's limit. |

The two resistor values are applied to `v3/design` by the production-package lane before the BOM is generated.

## 2c. Decisions after the thermal simulation (`v3/sim/thermal/THERMAL.md`, 2026-11-15)

SIM-13 fails as designed in 6 of 11 cases; a modelled fix exists for each. The lead adopts all of them (skin ≤ 43 °C is a safety floor):

| # | Change | Effect |
|---|---|---|
| T-1 | **PV laminate raised 0.655 mm, flush with the window top.** The pod top is flat at 5.305 mm; air under the laminate 0.805 mm. | Pod no hotter than V2-B (with T-2). Pod maximum thickness unchanged. |
| T-2 | **IR-cut coating on the window glass** (about 40 % of the display's absorbed heat removed; assumed, needs a vendor value). Window border and laminate prints absorptance ≤ 0.25. | With T-1: at most 42.73 °C. |
| T-3 | **Wing: active silicon ends at s 8 mm; strap roots and band are light (absorptance ≤ 0.30).** | Skin under the wing and the capsule ≤ 43 °C in every case, wind and low perfusion included. Costs about 40–45 % of the wing's silicon: re-run the energy numbers. |
| T-4 | Firmware: the skin-hot vibration alert runs at ≤ 5 % duty (mean ≤ 5.5 mW), not 257 s continuous. | Motor heat stays below the limit. |
| T-5 | Layout: a 4 × 4 mm thermal-via island under U10 (TMP117) with a filled contact to E1, no parts on it. | TMP117 coupling passes. |
| T-6 | Interim build with a masked window: mask absorptance ≤ 0.35. | Passes with T-1. |

## 2d. Decisions after the mechanical and ECG simulations (`v3/sim/mech/MECH.md`, `v3/sim/ecg/ECG.md`, 2026-11-15)

Both gates fail as designed; each failure has a modelled fix. The lead adopts these (design fix round "stage 2b"):

**Mechanical**

| # | Change |
|---|---|
| M-1 | PV laminate on a structural (rigid epoxy) bond on the ring and rib seats; its glass is chemically strengthened, 0.50 mm. The seat raise of 0.14 mm is covered by T-1 (flush top). |
| M-2 | Window rail gets a stainless core (0.4 × 0.855 mm); precision tolerances in the window column (seats and legs ±0.02, bond ±0.03 with spacer beads, film + OCA ±0.02); window seat raised 0.09 mm. **Pod top is flat at 5.395 mm** (PV laminate flush with it). |
| M-3 | Capsule top 0.50 mm strengthened glass; capsule 4.6 mm. |
| M-4 | Panel support legs ±0.02 mm; the FH34SRJ's 1.0 mm is confirmed as a maximum in the connector RFQ (otherwise the panel raise becomes 0.21 mm). |
| M-5 | PC corner bumpers 0.33 mm proud of the glass at the four window-half corners. |
| M-6 | Bench tests B1–B14 of MECH.md go to the manufacturer's list. |

**ECG, patient current, ESD**

| # | Change |
|---|---|
| E-1 | Ground the stainless window frame to board GND at the E3 end (a GND spring finger or a conductive dot on a GND pad). |
| E-2 | N-FET (PMZ290UNE2) in series with the GND charge contact J18, gate from VBUS_K (about 100 k, 1 M pull-down); an ESD761 on J18. |
| E-3 | ECG electrode chains 2 × 680 k instead of 2 × 330 k (same footprints); re-check the ECG noise. |
| E-4 | D14 becomes a Schottky with VR ≥ 100 V and VF ≤ 0.44 V at 33 mA in the same land; if no stocked part exists, the lane names the nearest real part and its land. |
| E-5 | VBUS negative clamp: a Schottky from GND (anode) to VBUS (cathode), unless the E-4 part's leakage keeps VBUS above −0.3 V at −5 V, 45 °C. |
| E-6 | TPD1E10B06 on BTN at SW1 and 10 k in series into the Q13 gate. |
| E-7 | Pack RFQ: fuse F1 fast-acting, clears ≥ 1.45 A within 0.5 s. |

The "barrier shorted" head cases stay as recorded (500 µA, no margin; reinforced heads only for wearers; the head is parked).

## 2e. Routing over the electrode plates (lead ruling after routing run r1, 2026-11-15)

Run r1: placement legal; 172 unconnected items in 71 nets. The blocker is the area over the two ECG plates (about 40 % of the board), where L3, L5 and B.Cu were closed and no signal via was allowed. Ruling:

| # | Rule |
|---|---|
| R-1 | The carrier film between the board and the floor is **two bonded polyimide layers, 2 × 0.05 mm** (same 0.10 mm). It is the double insulation between the board's bottom copper and the plates. Its only openings are the plate-contact dots. |
| R-2 | **Signal vias may sit over the plates** when all of this holds: tented and plugged on B.Cu; ≥ 1.0 mm from every plate-dot opening; the net is not in classes PWR_HIGH or VDD_1V8 (the written netclass rule); the net is not an "ECG-band" net, i.e. one that switches between 0.05 and 150 Hz (EXTCOMIN and the display COM, the O-2 heartbeat on CHG_DIS, LED, front-light and motor drives, BTN, slow enables). Inner layers L3 and L5 may carry such nets over the plates; B.Cu stays void over the plates except the via pads. |
| R-3 | The placement prefers plate-OK parts over the plates, so the via count there stays small. The layout reports the via count per net over each plate. |
| R-4 | After routing, SIM-07 is re-checked with those counts (about 0.033 pF per via pad through the film ⚠): the ECG target M2 ≤ 10 µVpp must still hold. |
| R-5 | The U10 (TMP117) island stays electrically isolated (board-only net, under solder mask); its thermal path to E1 is the film and a thermally conductive, electrically insulating bond. No copper touches a plate. |

## 2f. Rulings after the stage-2b fix round (`v3/stage2b/eco/ECO.md`, `v3/stage2b/cad/CAD2B.md`, 2026-11-15)

| # | Ruling |
|---|---|
| F-1 | D15 on the GND contact J18 becomes a **TPD1E10B06** (C48260, the part already used as D18), not an ESD761: the ESD761 lets Q20 avalanche. |
| F-2 | **E-3 is withdrawn.** The electrode chains go back to 2 × 330 k with the original anti-surge parts. Reason: 680 k pushes the ECG worst corner to 11.28 µVpp (limit 10), and JLC stocks no anti-surge 680 k. |
| F-3 | **Patient DC current criterion** follows IEC 60601-1's own structure: ≤ 10 µA in normal condition, ≤ 50 µA in single-fault condition. The older single figure "< 10 µA in every case" is replaced; this is flagged for the supervisor. Results are reported against both figures. |
| F-4 | Window rail inside the 5 mm antenna buffer (X 1.1–11.5 mm) stays GF-LCP but gets posts at 2 mm pitch; the zone file gains their feet. |
| F-5 | Corner bumpers 0.34 mm proud. Prints on the lid: absorptance ≤ 0.20. |
| F-6 | Wing stays at s 8 mm. The unlisted combined corner (perfusion 1e-3 with wind × 0.6: 43.3–43.4 °C ⚠) goes on the manufacturer's bench list as a measurement under the wing before any human wear. |
| F-7 | The J13 zone grows by 0.01 mm so its courtyard fits without a tolerance. |

## 2g. Rulings after the mini-ECO (`v3/stage2b/mini/MINI.md`, 2026-11-15)

| # | Ruling |
|---|---|
| F-8 | Q20 (the FET in series with the GND contact J18) becomes a **60 V N-FET in the same DFN1006-3 land** (JLC-stocked, for example a 2N7002-class part in SOT883; gate drive about 4.5 V; the drop at 34 mA must leave ≥ 4.745 V at the charger input). The ESD case at J18 is re-run with it. Applied by the production-package lane; the footprint does not change. |
| F-9 | **The display is powered down (DISP_EN low) during every ECG session.** The session is announced and closed by vibration before and after it; the image is restored afterwards. With this rule the panel's COM signal cannot reach the ECG; the remaining figure is the 3.99 µVpp floor. The criterion "M2 with the display running" no longer has a case. |
| F-10 | The capsule-corner drop case (0.819 mm crush against 0.707 mm allowance with the pod's mass behind it) stays PARTIAL and goes to bench test B8. |
| F-2 (corrected) | The chains stay 2 × 330 k because JLC stocks no anti-surge 680 k and the in-vivo noise is lower; the ECG worst corner does not depend on this value. |

## 2h. Antenna (lead ruling after `v3/sim/rf/RF.md`, 2026-11-15)

| # | Ruling |
|---|---|
| A-1 | The radiator is **PA_fill_booster** (`v3/sim/rf/export/AE1_PA_fill_booster.kicad_mod` and `.json`): placed at board (0,0), rotation 0, front; its rule area keeps the whole keep-out pocket free on all six layers. |
| A-2 | Layout: the antenna-side pad of the series element (C215 land) sits within 0.5 mm of line from the feed point at board (2.75, 3.00), with the chip-side shunt (C213 land) beside it. At 1.0 mm of line the efficiency halves. The ground edges at Y 3.0 (X 0.26–5.0) and X 5.0 (Y 0–3.0) are solid on all layers, stitched with GND vias at ≤ 1.0 mm pitch, 0.3–0.5 mm back from the edge. Radiator vias filled or tented; copper ≥ 0.30 mm from the board edge. |
| A-3 | Match: series 5.1 nH on the C215 land, shunt 1.1 nH on the C213 land, L204 not fitted. Both inductors are to be **high-Q parts (wire-wound or equivalent) in the same lands** where JLC stocks them; the production-package lane names the parts, recomputes the efficiency and the tolerance yield, and changes the schematic values. |
| A-4 | Result in force: 1.29 % total efficiency on the body and 14.5 dB link margin at nominal (gate 3a minimum: ≥ 1 %, ≥ 13 dB: met). Tolerance yield is PARTIAL (57 % of builds ≥ 1 % with multilayer inductors). ARCHITECTURE §9's older targets (≥ 5 %, S11 ≤ −10 dB on the body) are **not met** with a 5 × 3 mm keep-out; this is stated to the user as the weakest point of the design. First boards need a bench S11 tune (manufacturer). |
| A-5 | One FDTD run is left in the budget: the stainless strap-bar pins near the antenna corner. The production-package lane runs it with the final layout. |

## 2i. Antenna moves to the lid (lead ruling after `v3/sim/rf/lid/LID_ANTENNA.md`, 2026-11-15). This replaces rows A-1, A-3, A-4 and A-5 of §2h; row A-2 stays.

| # | Ruling |
|---|---|
| L-1 | The radiator is the **lid strip L1**: printed silver on the glass inner face (coordinates in `v3/sim/rf/lid/export/AE1_lid_L1.json`), fed by spring finger **J40** (BW0019BG, C2826516) at board (3.30, 1.55), rotation 340°. The stainless window frame is cut back to X 13.0 in the border band. |
| L-2 | Board: footprint `v3/sim/rf/lid/export/AE1_lid_L1.kicad_mod`. The keep-out pocket stays copper-free on all six layers except the feed leg and the spring land on F.Cu. No via, no B.Cu copper in the pocket. |
| L-3 | Match: C215 land = 9.0 nH LQW15AN9N0G80D (C6652901, series); L204 = 6.2 nH LQW15AN6N2B80D (C668465, antenna-side shunt, fitted); C213 not fitted. |
| L-4 | Result in force (model): 12.6 % total efficiency on the body, link margin 24.7 dB; every gate-3a minimum and every ARCHITECTURE §9 target passes at nominal; 100 % of tolerance builds reach ≥ 5 %. Only 10 % of builds reach S11 ≤ −10 dB: first boards need a bench tune. A hand on the lid gives 1.35 % and 15.0 dB (above the gate minimum, below the 5 % target). |
| L-5 | Board-to-glass height at the antenna corner: tolerance ±0.10 mm (the most sensitive dimension). The spring finger's working height must be confirmed from its drawing. |

## 2j. Rulings after ECO 2c (`v3/stage2c/ECO2C.md`, 2026-11-15)

| # | Ruling |
|---|---|
| J-1 | **J40 is BW0020AG-L3.5W1.5H3.0 (C2826518)**: free height 3.00 mm, working height 2.50 mm, limit 2.00 mm ✅ (drawing read by eye). Same land, position (3.30, 1.55) and rotation 340°; the J40 zone height is 3.10 mm. The BW0019BG is too tall for the 2.345–2.645 mm space. Applied to the BOM by the production-package lane. |
| J-2 | Q20 is CJBA7002K (C504101, 60 V). JLC's 0° for it is the old part's plus 180°: the large drain land faces J18. |
| J-3 | ESD at J18 (case 5c) stays a **recorded residual**: the drain peaks at 66–80 V for 0.2–0.7 ns (0.02–0.34 µJ) against a 60 V rating with no avalanche figure. Layout requirement: D15 within 1 mm of J18 with its own ground via. The manufacturer's ESD test on the contacts (IEC 61000-4-2) decides. No further part change. |
| J-4 | The layout change list of ECO2C.md is in force (AE1 lid footprint, J40, C215 and L204 on Murata's lands, C213 not fitted, Q20 rotation, zone `J40_land`). |

## 2k. Rulings after the layout attempt of 2026-11-15/16 (`v3/layout/LAYOUT.md`): the board does not route at 38 × 31 mm

Best board: 0 DRC errors, but 130 unconnected items in 79 nets, most of them in the 15 mm strip between the two plates, where the motor cut-out also sits. The lane estimates +100 mm² to close it. Rulings (stage 2d):

| # | Ruling |
|---|---|
| K-1 | **The motor cut-out moves out of the strip between the plates and sits over plate E2** (or E1 if E2 has no legal spot). The polyimide film stays under the motor (double insulation to the plate, R-1); the motor keeps ≥ 1.0 mm from every plate-dot opening and ≥ 10 mm from the antenna keep-out. The strip between the plates is then free for parts, vias and routing on every layer. |
| K-2 | **Pod 43 × 34 mm, board 40 × 31 mm.** The extra 2 mm goes into the strip between the plates; the plates keep their size. Cost to the wearer: about +0.4 g and about 3° less wrist extension ⚠. |
| K-3 | PV-half general part-height limit 1.20 mm (the flat lid gives the room); D14 (1.15 mm with solder) is then legal. |
| K-4 | The C1502–U16 decoupling distance limit is 5.0 mm (nano-power LDO output capacitor). |
| K-5 | Rail foot X4 moves by up to 0.5 mm so the antenna match parts reach the feed (re-check the rail sag). |
| K-6 | The U10 island follows R-5 (isolated, under solder mask); the CAD zone note is corrected. |
| K-7 | Layout method that worked best (keep it): via in pad on any pad (JLC fills and caps them on 6 layers), minimum via 0.15 / 0.25 mm, track and space 0.09 / 0.09 mm where needed, plane fan-out, one Freerouting stage, then the lane's own maze router (`v3/layout/tools/maze_finish.py`) after removing violating and dangling router copper. |

## 2l. Rulings after the 40 × 31 mm layout attempt (`v3/layout/LAYOUT.md`, 2026-11-16)

Best board: 0 DRC errors, 88 unconnected items in 53 nets (130 on 38 × 31). The lane's finding: 66 of the 87 failed pairs are walled in by router copper; more board area would not help; the finisher needs rip-up and reroute. Rulings (stage 2e):

| # | Ruling |
|---|---|
| N-1 | The outline stays 43 × 34 mm (board 40 × 31). No further growth. |
| N-2 | The maze finisher gets **rip-up and reroute** with a congestion cost (remove the router segments that wall in a failed pair, reroute both). |
| N-3 | **L4 may carry signals** where a channel needs it: VDD_1V8 becomes a routed bus with local pours instead of a full plane; every 1.8 V decoupling capacitor keeps a via or pour to it within 1 mm. L2 stays a full ground plane. |
| N-4 | The placer enforces J-2 (Q20's drain land faces J18) and J-3 (D15's courtyard within 1 mm of J18, own ground via). |
| N-5 | CAD: rail foot X6 moves by +0.7 mm so L204 sits beside C215 at the feed; the `J40_land` zone matches the footprint courtyard and the finger body stays inside the pocket; the J16 land and rail foot X35.3 no longer overlap; corner bumpers 0.35 mm. |
| N-6 | Lid prints: absorptance ≤ 0.20 is confirmed as the rule (0.25 fails the extreme thermal corner). Wrist extension is 38.8° at the 12 mm axis against the 40° target: recorded as the cost of the 43 mm pod. |

## 2m. After stage 2e (2026-11-16): 77 unconnected, the finisher is saturated; the user's direction

Best board (`v3/layout/kicad/solarband_v3f_main.*`): placement legal with 0 violations, 0 DRC errors, **77 unconnected items in 53 nets**; rip-up and reroute (`tools/maze_rrr.py`) stops falling at 77.

**The user's direction (2026-11-16):** no paid services and no outside dependence; rented CPU/GPU is the only acceptable spend; build our own "growing environment" for this board. Approved plan, step 1 first on the 10-core laptop:

| # | Ruling |
|---|---|
| G-1 | Folder `v3/grow`. Open-source software and our own code only. No pip or other downloads on this laptop: use what the project venv already has, or compile C with the system compiler. |
| G-2 | **Engine:** a whole-board negotiated-congestion router that starts from the placed, plane-fanned board (no Freerouting in the loop), with every rule of the layout lane built in, a compiled inner loop, and KiCad DRC as the referee. One command evaluates one candidate and writes a score. |
| G-3 | **Evolution:** a population of candidates (placement seed and local part moves, router weights, net order), parallel workers, selection and mutation, with routing congestion fed back into the placement. Resumable; results in a log. Success = 0 unconnected, 0 DRC errors, 0 placement violations. |
| G-4 | Validate on the laptop that the best score improves from generation to generation; then give the user a one-command bundle for a rented Linux machine and the size to rent. |
| G-5 | Open items carried, not blocking: the GF-LCP rail section's worst case (4.49 bar after foot X6 moved), bumpers 0.36 mm at the heavier pod, the antenna match distances (C215 0.65 mm, L204 1.67 mm of line) to be re-checked by the RF model once the layout closes. |

## 2n. Plan B and the package dry run (2026-11-16)

- The routing search is CPU-bound; it may run on a rented Linux machine (cores and memory stated with each bundle).

| # | Ruling |
|---|---|
| G-6 | **Plan B, evaluated in parallel with the search: an 8-layer board.** Same outline, placement and rules; two more signal layers. The evolution lane (or the lane after the engine) runs the engine with an 8-layer stack as soon as the engine exists and reports unconnected and DRC counts. The stack-up and rules for 8 layers come from `v3/planb/PLANB.md` when it exists. If 8 layers closes and 6 does not by Wednesday night, the deliverable is the 8-layer board. |
| G-7 | The production package (BOM, CPL from the placement gate, Gerbers, review images, checklist) is scripted now on the current board as a dry run (`v3/package`), so the final board needs one command. |

## 2o. Rulings after the package dry run and the pre-closure checks (`v3/package/PACKAGE.md`, `v3/prechecks/PRECHECKS.md`, `v3/planb/PLANB.md`, 2026-11-16)

| # | Ruling |
|---|---|
| P-1 | **Six more nets are plate-forbidden** (no via over a plate, no inner-layer track over a plate; F.Cu above the ground plane is allowed): NTC, NTC_ADC, I2C_SDA, I2C_SCL, O2_TC, O2_TH. Reason: on the 77-left board NTC and I2C couple 74–402 µVpp into the ECG (limit 10). Applies to the 6-layer and the 8-layer board; add them to `plate_forbidden_nets.json` and the DRC rule. |
| P-2 | Firmware rule as the second barrier: during an ECG session there is no I2C traffic and no NTC reading (the display is already off, F-9). |
| P-3 | Antenna match: all three lands (C213, C215, L204) stay fit-able. After the layout closes, the RF model re-tunes the three values for the real feed distances (the lid model gives 12.2 % and −10.05 dB with 7.2 / 7.2 / 5.2 nH at today's distances) and runs the tolerance yield. The layout still keeps C215 as close to the feed as it can. |
| P-4 | Window rail: the GF-LCP section in X 1.1–11.5 mm is 0.20 mm deeper (worst case 5.09 bar); parts under it ≤ 0.55 mm. Corner bumpers 0.36 mm. |
| P-5 | Plan B stack: 8 layers, GND on In1, VDD_1V8 full plane on In4, signals on F, In2, In3, In5, In6, B; through vias only; the antenna keep-out becomes `*.Cu`. Whether JLC makes 8 layers at 1.0 mm is not confirmed ❓ (1.2 mm would add 0.22 mm to the pod). |
| P-6 | **Placement gate, final state to reach:** every machine-checkable rule GREEN, and a short list of rows that wait for the JLC preview before any payment (bottom-side parts D3, D4, PD1; single-pad spring fingers; the parts whose mark the preview must confirm). For that: silkscreen pin-1 and polarity marks are added to the final board by a post-process step; the pin maps of the polarised parts are reviewed against their datasheets by an independent lane and marked `reviewed: independent-agent` with the date (the human check is the JLC preview row); EasyEDA footprint data for D12 and J40 may be fetched with `v3/design/tools/fetch_easyeda.py` (a public part-data query, not a file download into the project); D16 and SW1 get a second source from their datasheets. |

## 2p. Rulings after the first 8-layer evaluation (`v3/grow8/EVAL8.md`, 2026-11-16 evening)

Same placement, same 56 forbidden nets: 6 layers 75 unconnected, **8 layers 55**, 0 DRC errors on both. Eleven connections are blocked on both layer counts because the pad exits are closed by wide-class rules or fan-out copper; the rest is congestion around U7 (ADS1291), U1, U15, U17, U6; the six P-1 nets make up 12 of the 55. The 6-layer search on the laptop stayed at 62–64 over five generations and was stopped. Rulings:

| # | Ruling |
|---|---|
| Q-1 | **The baseline is now the 8-layer board** (stack of P-5). The tools live in `v3/grow8` (layer-count aware); `v3/grow` is frozen. |
| Q-2 | **Neck-down at pads:** within 1.5 mm of a pad it connects to, any net (the wide classes included: supplies, crystal, NTC classes) may use JLC's minimum track and clearance (0.09 / 0.09 mm). The largest current on this board is below 0.2 A, so a short 0.09 mm neck is acceptable ⚠. |
| Q-3 | **Forbidden nets may run on In2 and In3 over the plates** on the 8-layer board: those layers lie between the ground plane (In1) and the solid VDD_1V8 plane (In4), which shields them from the plates. Still no via of a forbidden net over a plate, and In5, In6 and B stay closed to them over the plates. In4 must be solid under such tracks (report its gaps). SIM-07 is re-checked on the final board. |
| Q-4 | **Escape first:** the fan-out must not close a neighbour's pad exit (via in pad where the pad allows it); the placement keeps an escape halo around the pad rings of U7, U1, U6, U15, U17 (only their own decoupling inside it), and the search may tune the halo. |
| Q-5 | **Track 2, in parallel, as insurance: a wider pod, 43 × 37 mm (board 40 × 34 mm)**, if the worn checks allow it (otherwise the widest that passes), with a placement that spreads the parts. The smaller board that closes first is delivered. |
| Q-6 | The search now runs on 8 layers with these rules; the rented machine is used as soon as the bundle (from `v3/grow8`) is ready. |

## 2q. Closing (2026-11-17)

Track 2e (pod 43 × 37, board 40 × 34, 8 layers, SC70 comparators) is the delivery board. The rented search reached 7–8 unconnected; local finishing (`v3/finish`) took the best board from 8 to 1 with 0 DRC errors and a legal placement.

| # | Ruling |
|---|---|
| P-7 | Fallback for the last connection only: I2C_SCL and I2C_SDA may have **at most two vias over plate E1 in total**, each ≥ 1.0 mm from a plate-dot opening, because firmware rule P-2 stops all I2C traffic during an ECG session. Written as a named exception in the board's DRC rules, with the count reported. All other plate rules stay. First choice remains moving U10 by up to 0.3 mm. |

## 2r. Final rulings (2026-11-17, after `v3/final/FINAL_REPORT.md`)

| # | Ruling |
|---|---|
| P-2b | **ECG session firmware rule, extended:** before recording starts the firmware turns off the IMU's INT1 (or powers the IMU down), pauses the PPG and its interrupt, and writes nothing to flash during the session (ECG kept in RAM or streamed over BLE, written afterwards). With F-9 and P-2 this gives M2 = 6.23 µVpp (limit 10). ECG sessions are short spot checks, so pausing the PPG for their length costs the wearer nothing. Board unchanged. |
| R-172 | R172 53.6 k 0201 (C423488, stock 0) is replaced by an in-stock part with the same value, size and tolerance class. |
| L-6 | Lid RFQ: PV glass 0.60 mm (0.50 mm reaches 228 MPa at 5 bar); corner bumpers 0.37 mm. |
| B-1 | BQ25170 (U15, orderable 0) and INA236 (U4/U5, 54 orderable): the user decides between JLC consignment and a pre-order when ordering; nothing changes on the board. |

## 3. Where things are

- Specification: `v3/decide/BASELINE.md`. Stage records: `v3/stage1/STAGE1.md`, `v3/g1/dense/DENSE.md`, `v3/g1/cad/CAD_OPTIONS.md` (options table: `options_summary.md`).
- Schematic flow: `v3/design` (`tools/run_all.sh`, `src/`, `parts.json`, `placement_proof.md`, `tools/area_check.py`). Frozen stage-1 state: `v3/design_s1`.
- CAD: `v3/cad` (`src/`, options through the `V3F_OPT` key=value list, zone files in `out/options/`). Frozen stage-1 state: `v3/cad_s1`.
- Placement and routing tools, already adapted to V3-F: `v3/g1/place/tools` (see `v3/g1/place/PROGRESS.md`; results table `work/g1_sets.md`). Legal placements exist for every option set. Freerouting trials t2–t4 left GND and supply pads unconnected (no plane or zone handling yet) and a few signals.
- Calculation: `v3/stage1/calc/baseline_calc_s1.py`.
- Simulations: `sim/` (v1 originals), `v2/sim/` (V2-B adaptations).
- Environments: `v3/g1/place/PROGRESS.md` (KiCad python, kicad-cli 10.0.7, Freerouting); Python `python3`.

## 4. Rules

- Write only inside the folders your task names. Never modify `ARCHITECTURE.md`, `design/`, `sim/`, `redesign/`, `v2/`, `layout/`, `mech/` (all under `wristband/`), or `/path/to/solar-vest`.
- No purchases, quotes, sample requests, log-ins, uploads or messages. Do not save downloaded files into the project.
- Marks: ✅ read today in a named source or produced by a named tool run; ⚠ estimate; ❓ unknown.
- Pass criteria as written. Never relax one silently: PASS, PARTIAL, FAIL or NOT_RUN.
- Placement safety: every polarised or rotation-ambiguous JLC-placed part needs a land that proves its rotation, or a JLC preview check before payment plus an electrical test.
- No personal names, school name or supervisor's name in any file ("the user", "the supervisor"). The band harvests light: never call it wireless power transfer.
- Do not name a file REPORT.md.
