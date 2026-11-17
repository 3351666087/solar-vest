# CALC_V3F - SolarBand V3-F main board: numbers behind the schematic

Lane V3-F MAIN-BOARD SCHEMATIC, 2026-11-13. Specification: `../decide/BASELINE.md` (V3-F). Every number comes from a script in this folder:

| Script | Output | Sections |
|---|---|---|
| `calc/v3f_calc.py` | `calc/v3f_calc.json` | 1, 2, 4–9 |
| `calc/o2_inhibit.py` | `calc/o2_inhibit.json` | 3 |
| `tools/area_check.py` | `area_check.json`, `area_check.md` | 10 |

Both calc scripts import the V3 PV model `../integrate/energy/v3_energy.py` read-only.

Marks:
- ✅ = a datasheet or drawing value I read today, with its document and page (URLs in `calc/v3f_calc.py` → `SRC`).
- ⚠ = computed from a model or from an estimate (stated).
- ❓ = not found.

Nothing here was measured or simulated in a project SIM. The V3-G gates of BASELINE §18 still have to run.

## 0. Summary (⚠ unless marked)

| Item | Result | Verdict |
|---|---|---|
| USB charge current, RISET 10 k | 26.7 / 30.0 / 33.3 mA (KISET ✅). 0.38–0.48 C on 70 mAh; 0.505 C max on 66 mAh | ≤ 0.5 C needs ≥ 66 mAh nominal (FS-1 lock kept) |
| VREG (36 k) | 4.10 V; 4.079–4.120 V at 25 °C, 4.067–4.133 V over temperature ✅ | – |
| TS window, NTC shared with O-2 and AIN | cold stop 0.84–5.19 °C; hot stop 38.56–44.64 °C at every corner | PASS (cold stop ≥ 0 °C, hot stop ≤ 45 °C) |
| Head voltage needed at the contacts (end of charge, D14 in series) | ≥ 4.75 V at 33 mA | new V3-G10 requirement: ≥ 4.85 V at 40 mA |
| R_LIM 12 Ω + Q14: PV bound, 1.2 sun, −10 / −20 °C | 0.382 / 0.400 C (lowest R; 2.50 mm strips) | ≤ 0.5 C ✓; Q14 only lowers the BASELINE bound (0.385 / 0.404 C) |
| Cold-start dissipation, R130 / Q14 | 36.6 / 52.7 mW; Q14 1.0–4.1 mW | 1206 250 mW ✓ |
| O-2 inhibit, MCU off | cold stop 0.84–3.97 °C, hot stop 34.9–43.3 °C at every corner; dark load 0 µW | PASS on the criteria. Residual: a flat band restarts only above about 711 lx. Area 20.6 mm² against a 12 mm² reserve |
| ERM start at VBAT 3.60 V, motor on VBAT_IC | VSTOR 3.507 V (typical path) / 3.450 V (maximum, 25 °C) / 3.350 V (0 °C cell). VBAT_OK falling max is 3.441 V | PASS at 25 °C. At 0 °C it needs the INA_BAT-limited soft start (≤ 42 mA → 2.39 V average, above the 2.3 V start voltage of the class) |
| Front light, R160 100 Ω | 4.1–16.8 mA peak over VSTOR_SW 3.31–4.28 V; 9.64 / 19.27 µW (typical / dark test) | 3 mA dim-room level reachable at every corner (220 Ω could not) |
| Display interface | VOH ≥ VDD − 0.1 V meets the panel's VIH ≥ VDD − 0.1 V (same rail) ✅; edges a few ns ⚠ | PASS (bench check of the power-up edge, V3-G10 (g)) |
| Wake | VBUS → EN_HOLD 1.0 V in 1.68 s; button 0.18–0.25 s; no D12 leakage in ship mode | PASS |
| Standby against BASELINE §11.1 | MON face on 255.1 µW, or 266.6 µW with three datasheet bounds; SHELF 35.7 / 37.9 µW; ship 22.3 / 26.0 µW | T6 SHELF 242 d and ship 353 d even with the bounds (≥ 182.6 d) |
| Board area, as built, 37 × 29 / 38 × 29 mm | 0.613 / 0.678 and 0.592 / 0.656 (project / v1); tall zone 0.523 / 0.579 at 37 × 29 | **FAIL on v1's measure at both sizes** (BASELINE planned 0.565 / 0.626 and 0.546 / 0.605). Passes at 38 × 29 only with reserves 1 + 3 (0.551 / 0.610) |

## 1. BQ25170 charger block (U15, `src/charger.py`)

Datasheet: TI SLUSDJ8A ✅.

### 1.1 Charge current, voltage and limits

| Quantity | Value | Source |
|---|---|---|
| ICHG = KISET / RISET, KISET 270 / 300 / 330 A·Ω, R140 10 k ±1 % | **26.73 / 30.00 / 33.33 mA** | p.6 ✅ |
| C-rate, 70 / 66 / 60 mAh (min / typ / max current) | 0.382–0.476 / 0.405–0.505 / 0.446–0.556 C | ⚠ |
| Precharge 20 % (between VBAT_SHORT and VBAT_LOWV 2.7–3.0 V) | 5.35–6.67 mA | p.7 ✅ |
| Trickle IBAT_SHORT below VBAT_SHORT 2.1–2.3 V, independent of RISET | 12 / 16 / 20 mA (0.17–0.29 C on 70 mAh) | p.7 ✅ |
| Termination 10 % | 3.0 mA nominal. Accuracy is given only at 600 Ω / 3 k / 30 k (±60 % at 30 k), so about ±60 % here | p.7 ✅ / ⚠ |
| VREG with R142 36 k | 4.10 V (Table 7-1); ±0.5 % at 25 °C, ±0.8 % over temperature → 4.067–4.133 V; recharge 75–125 mV below | p.14, p.6, p.7 ✅ |
| VSET resistor window | 35.6–36.4 k. Nearest table entries are 27 k (4.20 V) and 47 k (4.05 V); latched at power-up | p.14–15 ✅ |
| ISET RC (R141 2 k + C132 4.7 nF across R140), τ 9.4 µs | an RC "is recommended" below 50 mA. Values are from the 45 mA design of the sibling BQ25171-Q1 (SLUAAG9 Figure 5-1, p.4, read as an image) | p.14 ✅; applicability ⚠ |
| Abs. max IN / OVP | −0.3…30 V; OVP 6.60–6.90 V | p.4, p.6 ✅ |
| Charge-FET drop at 33 mA | ≤ 48 mV (RON ≤ 1.45 Ω) | p.7 ✅ |
| Dissipation in U15 | head 5.25 V, D14 0.40 V, cell 3.0 V, 33 mA: 62 mW. RθJA 75.2 °C/W (JEDEC) → +4.6 K | p.5 ✅ / ⚠ head |

### 1.2 Head voltage needed at the contacts

/PG and charging need VIN > VOUT + VSLEEPZ (95–175 mV) ✅ p.6, p.17. At the end of charge:

4.133 V (VREG max) + 0.175 V (VSLEEPZ max) + 0.436 V (D14 VF max at 33 mA, interpolated from NSR0240 p.2 ✅) + 7 mV (0.2 Ω of contacts ⚠) = **4.75 V**.

A 5.0 V −5 % head is exactly at this limit, so V3-G10 gets a new requirement: **≥ 4.85 V at the contacts at 40 mA**. Below that the charger sleeps near the end of charge and /PG goes high. That costs a few % of capacity and is not a hazard.

### 1.3 TS window (NTC shared with the O-2 ladder and the MCU AIN)

TS values ✅ p.7: ITS_BIAS 36.5–39.5 µA; VCOLD 0.99–1.09 V; VHOT 176–200 mV; VTS_ENZ 40–60 mV.

| Case | Cold stop | Hot stop |
|---|---|---|
| TS bias alone | 1.85–6.04 °C | 38.79–44.84 °C |
| With the O-2 path on the node (R116 + chain ‖ U19 supply = 586 kΩ, while VBUS is present) | 0.84–5.19 °C | 38.56–44.64 °C |

Corners: NTC ±1 % R25 and B, resistors ±1 %, TS bias and thresholds at their limits (`o2_inhibit.py` `ts_window`).

**PASS** at every corner (criterion: cold stop ≥ 0 °C, hot stop ≤ 45 °C).

CHG_DIS (Q10 on) pulls TS to 39.5 µA × 0.68 Ω = 27 µV, far below VTS_ENZ 40 mV, so charging is disabled ✅ p.7, PMZ290 p.6.

### 1.4 /PG and quiescent current

- **/PG** (R143 220 k to VDD_1V8):
  - Low while the head is attached: 8.45 µA.
  - High-level leakage ≤ 1 µA (3.3 V pull-up) ✅ p.7. No typical is published, so 1 µA is a bound. Even at the bound the high level is ≥ 1.64 V, above VIH 0.7 × VDD = 1.30 V ⚠.
- **IQ_OUT** (cell side, IN floating): 0.35 typ / 0.6 max µA at 25 °C, 0.8 µA below 105 °C ✅ p.6. Already in BASELINE §11.1.

## 2. R_LIM 12 Ω charge bound and cold start with Q14 in series (BASELINE §11.5)

Q14 (PMZ350UPE, O-2 series switch) sits in the PV path, so its RDS(on) adds to R130.

Q14 RDS(on): 0.33–0.45 Ω at −4.5 V, 0.42–0.645 Ω at −2.5 V, 0.52–0.94 Ω at −1.8 V ✅ PMZ350UPE p.6.

Model: `v3_energy.charge_point` / `series_i` ⚠. RSH1 1 Ω + series R; every string lit; k 0.72; cell 3.0 V (BASELINE convention).

| Case (70 mAh, C-rate; full 2.50 mm strips = upper bound for 2.30 mm) | 1.2 sun −10 °C | 1.2 sun −20 °C | 1 sun 25 °C |
|---|---|---|---|
| BASELINE reproduction, 12.0 Ω | 0.385 | 0.404 | 0.304 |
| Lowest R: R130 −1 % + Q14 0.33 Ω | 0.382 | 0.400 | 0.301 |
| Highest R: R130 +1 % + Q14 0.94 Ω | 0.368 | 0.386 | 0.292 |
| Lowest R, 2.30 mm strips | 0.377 | 0.394 | 0.297 |

Q14 only lowers the bound. **≤ 0.5 C ✓**. The 43 mAh BOM mix-up remains the reason R130 is locked to the pack (BASELINE §11.5).

Cold start, VIN_DC clamped at 0.6 V (SLUSBH2G p.18 ✅):

| Case | Current | R130 (+1 %) | Q14 |
|---|---|---|---|
| 1 sun, 25 °C | 55.0 mA | 36.6 mW | 1.0–2.8 mW |
| 1.2 sun, −10 °C | 66.0 mA | 52.7 mW | 1.4–4.1 mW |

R130 is a 1206 rated 250 mW ✓. Q14's few mW are well inside its package rating (the PMZ290 in the same SOT883 is rated 350 mW, p.3) ⚠.

Deep discharge: the three-diode path of BASELINE §11.5 still applies when Q14 is on. Q14 is on only inside the O-2 window (MCU off) or with VBAT_OK high. So the 0 V / 0.5 V / 1.0 V cases keep BASELINE's 0.07–0.89 C, and from now on only inside 0–45 °C.

## 3. O-2 hardware PV-charge inhibit (`src/o2.py`, `calc/o2_inhibit.py`)

### 3.1 Why a series switch instead of driving the Q1 gate

BASELINE §4 drew the O-2 output as an OR into the Q1 gate (Q1 shorts the PV). That route was rejected:
- When Q1 shorts the PV, the O-2's own PV supply collapses, so it oscillates.
- The NTC ladder would need power in every lit state.
- A default-on switch leaves windows with no protection during a deep discharge.

The circuit is fail-safe, default OFF:
- **Q14** (PMOS) sits in series between PV_SW and R130. R174 10 MΩ + C174 100 nF from gate to source keep it **off** unless O2_G is pulled low.
- **Q16** (gate = VBAT_OK) pulls O2_G low whenever the MCU runs. The firmware 0–45 °C governor (Q1 + the MCU's own NTC reading) is then in charge, and the O-2 is unpowered (**Q18** off).
- **With the MCU off** (VBAT_OK low), Q18 feeds V_O2 from PV_SW through D19A. U19 ("not cold") powers U20 ("not hot"), a chained AND; each TLV7031's power-on reset holds its output low.
- **Q17** pulls O2_G low only while the cell NTC is inside the window.

The decision is taken at the **open-circuit PV with Q14 off**, so it does not depend on the cell. The ladder (R116 100 k → NTC) and the reference chain (R170 732 k / R171 162 k / R172 52.3 k) hang on the same V_O2, so the decision is ratiometric.

### 3.2 Results

| Item | Value | Criterion (BASELINE §18 V3-G4) |
|---|---|---|
| Trip temperatures, every corner (NTC R25 and B ±1 %, resistors ±1 %, offset ±8 mV, hysteresis 2–17 mV ✅ SLVSE13J p.8, V_O2 1.91–2.76 V) | cold stop 0.84–3.97 °C, release 1.31–4.46 °C; hot stop 34.88–43.31 °C, release 32.87–40.55 °C; typical 2.45 / 38.41 °C | no PV current outside 0–45 °C with the MCU off: **PASS** (0.5 K margin rule) |
| Cell states 0 / 0.5 / 1.2 / 2.0 V, PCM tripped | same decision supply (open-circuit PV) | **PASS** |
| Supply | from the PV node (Q18 / D19A); never from VBAT alone | **PASS** |
| Dark load | 0 µW: PV_SW = 0 V; VBAT_OK only drives gates; NTC_EN readings average 0.8 nA | ≤ 2.5 µW: **PASS** |
| Load on the PV while deciding (MCU off) | 18.8 / 23.1 / 29.5 µA max at V_O2 1.6 / 2.0 / 2.6 V | ⚠ |
| Light needed to approve with the MCU off | **711 lx** (V_O2 ≥ 1.65 V with its own load). BASELINE cold start: 167 / 358 lx | residual; with the MCU on there is no effect (Q16) |
| No oscillation | Q1 can be on only with the MCU running (then Q16 holds and the O-2 is unpowered). Q8 collapses V_O2, the comparators go to reset, Q14 opens after the hold. The O-2 only ever opens Q14, which raises its own supply. Hysteresis 0.38 K (cold) / 1.64 K (hot) | **PASS** (by construction; SIM-03 to confirm) |
| Brown-out after approval (cold start or MPP below 1.6 V) | C174 holds Q14 on for 0.64–1.67 s, then a re-check within 0.3–1 ms; harvest duty ≥ 99 % | ⚠ |
| Timing | comparator power-up 200 µs; C170 charge 1.3 ms at 1000 lx; Q14 turn-on 40 µs; fault response ≤ 1.67 s | ✅ / ⚠ |
| MCU reading (NTC_EN → D19B → R116; AIN through R149 1 MΩ, C113 10 nF) | −0.47 K per 30 mV error of D19B's VF (firmware corrects it with the TMP117). With the MCU unpowered the AIN clamp leaks ≤ 0.2 µA (< 0.5 K) | ⚠ |
| Cost, MCU on | R174 draws PV_SW / 10 MΩ = 0.2 µA from the PV (0.4 µW of harvest) | ⚠ |
| Area (parts.json courtyards, 14 parts) | **20.6 mm²** against the 12.0 mm² reserve | over the reserve: the pack-PCM cut-off (BASELINE reserve 3) is the better route |

BASELINE's preferred alternative still stands: a pack PCM that opens its charge FET outside 0–45 °C down to a stated cell voltage. It removes all 14 parts (−20.6 mm²) and the 711 lx residual.

## 4. ERM drive (`src/hmi.py`: Q12, R162, R163, D17, J17)

### 4.1 Supply choice

Q12 is a low-side switch with gate resistor R162 1 k and pull-down R163 1 M; D17 (BAT54CM, both halves in parallel) is the flyback.

**The motor is on VBAT_IC as built (BASELINE §4 drew it on VSTOR).** On VSTOR the start current would also cross the BQ25570 PFET (0.95–1.50 Ω). That pulls VSTOR 0.07–0.10 V closer to VBAT_OK falling.

VBAT_OK falling is 3.192 / 3.312 / 3.441 V (min / nominal / max with IC accuracy) ✅ V2 CALC §1.

Source path (V2 `led_supply.py` ✅ / ⚠):

| Element | Value |
|---|---|
| Cell + PCM | 0.15 Ω (GEB statement via ENG_A, BASELINE §11.2) / 1.0 Ω (sister-cell limit) / 2.5 Ω at 0 °C ⚠ |
| R112 | 1.0 Ω |
| F1 + strap + FB links | 0.25 Ω ⚠ |
| PFET (VSTOR supply only) | 0.95 / 1.50 Ω |

### 4.2 Motor model and start at VBAT 3.60 V

Motor ✅ VCLP0820 page: 30 typ / 35 max mA at 3.0 V; rise ≤ 90 ms.

Start current 80 mA and starting voltage 2.3 V are taken from the CLP1020 class (p.4/13) ⚠ by analogy.

Model: R_coil 37.5 Ω; locked-rotor battery current = D² × V / R.

| VBAT 3.60 V, PWM to 3.0 V average | Path | Start: battery current / VSTOR | Margin to VBAT_OK max 3.441 V | Running VSTOR |
|---|---|---|---|---|
| VBAT_IC, typical | 1.40 Ω | 66.7 mA / 3.507 V | +66 mV | 3.559 V |
| VBAT_IC, maximum (25 °C) | 2.25 Ω | 66.7 mA / 3.450 V | +9 mV | 3.534 V |
| VBAT_IC, 0 °C cell | 3.75 Ω | 66.7 mA / 3.350 V | **−91 mV**: needs the soft-start limit 42 mA → duty 0.665 → 2.39 V average (≥ 2.3 V: starts) | 3.491 V |
| VSTOR, maximum (for comparison) | 3.75 Ω | 3.350 V | −91 mV | 3.491 V |
| VSTOR, 0 °C cell | 5.25 Ω | 3.250 V | −191 mV; the limit 30 mA gives only 2.02 V average (< 2.3 V: may not start) | 3.447 V (+6 mV) |

### 4.3 Hook for "VBAT ≥ 3.60 V" (BASELINE §14 item 6)

No extra part is needed. INA_BAT (U5 INA236, R112, bus = BATT_P) reads VBAT before the start and the battery current during the 30 ms ramp. The firmware ramps the duty while I_bat ≤ 40 mA and VBAT_IC − I × 1.0 Ω ≥ 3.50 V, then holds 3.0 V average. The motor never runs during ECG. "No brown-out at a motor start at VBAT ≥ 3.60 V" then holds at every corner of the table ⚠ (V3-G4 confirms with PV support).

### 4.4 Gate, flyback, ripple and ship mode

- **Gate:**
  - GPIO peak current 1.86 mA.
  - Gate charge at 1.86 V ≈ 0.19 nC ⚠ (Ciss 46 pF, QGD 0.2 nC at 10 V ✅ PMZ290 p.6).
  - Edge ≈ 0.22 µs; switching loss 1.3 mW at 40 kHz.
  - RDS(on) ≤ 0.68 Ω at 1.8 V ✅ → ≤ 54 mV at 80 mA.
- **Flyback:** VF ≤ 0.50 V at 30 mA ✅ BAT54CM p.4. Q12 VDS peak 4.78 V (20 V part); D17 2.9 mW average; IFRM 300 mA.
- **PWM ripple** on VBAT_IC (C106 22 µF × 0.40): ≤ 14 mV ⚠.
- **Ship mode:** VBAT_IC stays on the cell, because only the VSTOR–VBAT PFET opens (SLUSBH2G §7.4.1 p.18 ✅). So Q12's off-state leakage becomes a ship-mode load. The only published value is a bound, IDSS ≤ 1 µA at 20 V (no 4 V figure ❓): 3.7 µW (section 9).

## 5. Front light (`src/hmi.py`: R160, Q11, R161, J16)

Path: VSTOR_SW → R160 → film LED → Q11 (PWM). VF of the custom 1.08" film is not specified (2.6–2.9 V at 1–5 mA ⚠).

| R160 | Peak at VSTOR_SW 3.31 V, VF 2.9 V | Peak at 4.28 V, VF 2.6 V | 3 mA dim-room level possible |
|---|---|---|---|
| **100 Ω (as built, C270366, 485,571 orderable ✅ JLC 21:38 UTC)** | 4.07 mA | 16.8 mA (28 mW peak in the 0201, 50 mW rated) | yes |
| 120 Ω | 3.39 mA | 14.0 mA | yes |
| 150 Ω | 2.72 mA | 11.2 mA | no |
| 220 Ω (first value) | 1.85 mA | 7.6 mA | no |

- **Peak limit:** 16.8 mA is a pessimistic peak (VF rises with current), below the 25 mA absolute maximum of the 1.28" part ✅ AZ11049 p.2. The 1.08" film's own limit ❓.
- **Brightness:** PWM duty = target average / peak, corrected from VSTOR (INA_BAT). The VF spread stays: brightness ±30 % ⚠.
- **Energy** (battery-referred, I_avg × 3.7 V): 1.93 µW night + 7.71 µW dim room = **9.64 µW typical**; **19.27 µW** dark test. Same as BASELINE §11.1.

## 6. Display interface (U16 TPS7A0230, U17 TXU0104, U21 TXU0101, J13)

### 6.1 Panel requirements

LD-29Y03 ✅:
- VDD / VDDA 2.7–3.3 V (Table 6-1, spec p.18).
- **VIH ≥ VDD − 0.1 V and VIL ≤ VSS + 0.1 V** for SCLK, SI, SCS, DISP and EXTCOMIN.
- Edges ≤ 50 ns (spec p.22).
- DISP low ≥ 30 µs before VDD goes off (spec p.21).
- Power 15 / 50 µW in hold and 25 / 100 µW at a 1 Hz update (Table 6-4, spec p.24).

### 6.2 Translators (both powered and enabled by DISP_EN)

A side, VCCA = DISP_EN at 1.86 V (SCES937B p.8 ✅, interpolated to VCCA):
- VT+ max 1.30 V (at VCCA 1.90 V) → 0.46 V margin to a 1.80 V − 50 mV output.
- VT− min 0.40 V (at VCCA 1.80 V) → 0.35 V margin to a 50 mV low level.

B side, VCCB = VDD_DISP:
- VOH ≥ VCCB − 0.1 V and VOL ≤ 0.1 V at 0.1 mA (p.9 ✅).
- VCCB is the panel's own VDD, so these levels meet the panel's VIH / VIL at its µA input currents.

Edges: 100 Mbps for 1.65–1.95 → 3.0–3.6 V with 20 % of the pulse above 0.7 VCCO (p.10 ✅). That implies edges of a few ns, ≪ 50 ns ⚠ (inference).

**Why DISP has its own translator.** In V3-R, DISP was driven through an RC from the rail. That fails the edge limit, the power-off order and VIH ≤ VDD. So DISP moved to U21 on P0.18 (DISP_CTRL), the former debug UART_TX.

Supply current: ICCA + ICCB ≤ 2.5 / 3 / 6 µA per translator (25 / 85 / 125 °C) ✅ SCES937B p.9, SCES940A p.7. No typical is published ❓ (as V3_ARCH found for the TXU0104). U21 adds at most 9.25 µW while the face is on.

### 6.3 TPS7A0230 (U16)

TPS7A0230 ✅ SBVS277C p.6–7:
- **Output:** 3.0 V ±1.5 % (2.955–3.045 V), inside the panel's 2.7–3.3 V.
- **Headroom:** 0.147 V at VSTOR_SW = 3.192 V (lowest VBAT_OK falling). Dropout ≤ 310 mV at 200 mA, i.e. about 0.16 mV at 100 µA ⚠ scaled.
- **Currents:** IGND 25 / 46 nA (0.09 / 0.17 µW); ISHDN 3 / 10 nA (0.011 / 0.037 µW).
- **Enable:** VEN(HI) ≥ 1.1 V, IEN ≤ 10 nA.
- **Off and start:** 60 Ω output discharge when off; start-up 0.75–1.2 ms.

### 6.4 Power sequence (firmware)

On:
1. DISP_EN high.
2. Wait ≥ 1.2 ms.
3. Panel init with DISP_CTRL low.
4. DISP_CTRL high.

Off:
1. DISP_CTRL low.
2. Wait ≥ 30 µs.
3. DISP_EN low.

Both translators go high-Z while a supply is below 100 mV (p.1). So DISP is undriven during the first part of the VDD ramp ⚠: checked on the bench in G10 (g).

## 7. Wake paths, button and ship-mode leakage (D12 BAV70M, SW1, Q13)

The EN circuit is as V2 ✅ V2 CALC §4: Q4 holds EN low while EN_HOLD ≥ 1.0 V (strict); C121 4.7 µF; R126 3.3 MΩ to the PV node (≈ 0 V in the dark).

| Path | Source | EN_HOLD final / τ | Time to 1.0 V |
|---|---|---|---|
| Head: VBUS 5 V → R144 / R145 1 M / 1 M → VB_DET 2.5 V → D12A | 500 kΩ Thevenin | 1.78 V / 2.04 s | **1.68 s** |
| Button at VBAT 3.0 V: BTN = 0.909 × VBAT through R165 100 k / R167 1 M → D12B | 90.9 kΩ | 2.22 V / 0.42 s | **0.25 s** |
| Button at VBAT 3.7 V | 90.9 kΩ | 2.84 V / 0.42 s | 0.18 s |

D12's VF at a few µA is taken as 0.45 V ⚠ (≤ 715 mV at 1 mA ✅ BAV70M p.3).

- **Running:** EN_HOLD is already 1.27–1.46 V (D9), so BTN starts at EN_HOLD + VF and Q13 switches at once. BTN_N falls on P0.26 (SENSE).
- **Ship mode:** a press of ≥ 0.3 s wakes the band, then MCUboot holds PWR_HOLD. No pin of the MCU sees the VBAT level. R164 hangs on VDD_1V8, which is off in ship mode, so nothing back-feeds.
- **Press currents:** 3.7 µA (R165 + R167) and 1.86 µA (R164 through Q13).
  - The PTS840 is rated 50 mA / 12 V, contact ≤ 500 mΩ, bounce ≤ 10 ms ✅ p.1. 4 µA is a dry circuit: the contact finish is not stated ❓.
  - A stuck key or water pressure draws about 21 µW while held. In ship mode a held key wakes the band.
- **Leakage in ship mode:**
  - D12 has both anodes at 0 V (R145, R167) and the cathode at EN_HOLD = 0 V: no bias, no current.
  - Running: D12 is reverse-biased by about 1.3 V, IR ≤ 30 nA at 25 V per half ✅ BAV70M p.4.
  - R144 / R145 carry nothing with the head off (D14 blocks).

## 8. Contact ESD and reverse attach (J15, J18, D13, D14, C130)

Path: J15 (VBUS_K) → D13 ESD761 at the land → D14 NSR0240 (series Schottky, cathode toward U15) → VBUS → C130 1 µF at U15 IN. J18 is GND.

| Case | Result |
|---|---|
| +8 kV IEC 61000-4-2 contact (150 pF) | 1.2 µC into C130 (1 µF × 0.6 at 5 V ⚠): **+2.0 V** on IN against the 30 V absolute maximum (SLUSDJ8A p.4 ✅). D13 clamps 36.3 V at 1.8 A (8/20 µs), ±15 kV IEC (SLVSH10C p.4–5 ✅) |
| −8 kV | D14 is reverse-biased up to the ESD761 clamp (36.3 V at 1.8 A + the dynamic part at the IEC peak ❓) against its VR 40 V (NSR0240 p.1 ✅). The margin is small and not specified for ns pulses: **V3-G6 ESD test of the contacts**. Fallback: a 60 V Schottky in the same land |
| −5 V reversed head (V3-G4 item) | D14 blocks: U15 IN stays ≥ −0.3 V; ESD761 (VRWM ±24 V) does not conduct; current ≤ 0.55 µA at 25 V (NSR0240 p.2 ✅). **−5 V harms nothing** ⚠ (V3-G4 SIM confirms) |
| Head off | VBUS_K floats; D13 leaks ≤ 50 nA only with a voltage on it: 0 in use |

## 9. Standby against BASELINE §11.1 (battery-referred µW, 3.7 V)

| State | BASELINE §11.1 | As built, without the bound items | As built, with the datasheet bounds |
|---|---|---|---|
| MON, face on | 257.6 | **255.1** (the O-2 is no battery load: −2.5) | 266.6 |
| MON, dark (night blank) | 238.8 | 238.9 | 241.0 |
| ECO (conservative) | 93.9 | 93.9 | 96.1 |
| SHELF | 35.7 | 35.7 | 37.9 |
| Ship mode | 22.3 | 22.3 | 26.0 |

Bound items (no typical published, all "unverified - needs samples"):

| Item | Bound | Battery-referred | States |
|---|---|---|---|
| U21 ICCA + ICCB | 2.5 µA | 9.25 µW | face on |
| BQ25170 /PG leakage | 1 µA from VDD_1V8 | 2.19 µW | whenever VDD_1V8 is on |
| Q12 IDSS on VBAT_IC | 1 µA at 20 V | 3.7 µW | ship mode only, a path of the VBAT_IC supply |

Small computed items: U16 shutdown 0.037 µW; NTC readings 0.023 µW.

T6 at the bounds is SHELF 242 d and ship mode 353 d (BASELINE 257 / 411 d). **Both stay ≥ 182.6 d.**

## 10. Board area (`tools/area_check.py`, `area_check.md`)

### 10.1 Metric

The project metric (`v3_calc` `density()` / `area_config()`, `baseline_calc.area()`, reproduced in `area_check.py`):

placement = board − 0.5 mm edge band − antenna keep-out 15 − fixed features − motor cut-out 66.2 (Ø 8.6 + 0.3 mm band) − 6 rib post feet × 1.0

- utilisation = courtyard / placement. v1's measure is utilisation × 399.5 / 360.7. The limit is 0.62.
- Courtyard = JLC-placed sky-side F.CrtYd boxes plus the hand-soldered lands J13, J16 and J17.
- Fixed = 6 root lands + J6 + J12 + TP1–TP5 + the two V2 lid posts (12.3 ⚠): 102.1 mm² as built, against the plan's 96.5.
- Tall zone = placement − the panel zone 33 × 15 = 495 mm².

The script rebuilds BASELINE's 455.5 / 806.3 mm² from v2's parts.json and the BASELINE item lists (assert ±0.2 mm²).

### 10.2 Results

| Case | 37 × 29: total | 37 × 29: tall zone | 38 × 29: total | 38 × 29: tall zone |
|---|---|---|---|---|
| BASELINE §5.3 plan (rebuilt) | 0.565 / 0.626 | 0.471 / 0.522 | 0.546 / 0.605 | 0.432 / 0.479 |
| **V3-F as built** (490.5 mm²) | **0.613 / 0.678** | 0.523 / 0.579 | **0.592 / 0.656** | 0.479 / 0.531 |
| PCB incl. DNP lands and sky fiducials (516.1) | 0.645 / 0.714 | – | 0.623 / 0.690 | – |
| Reserve 1 (LED chain) | 0.596 / 0.660 | 0.498 / 0.552 | 0.576 / 0.638 | 0.456 / 0.505 |
| Reserve 3 (O-2 in the PCM) | 0.587 / 0.650 | 0.523 / 0.579 | 0.567 / 0.628 | 0.479 / 0.531 |
| Reserves 1 + 3 | 0.570 / 0.631 | 0.498 / 0.552 | **0.551 / 0.610 ✓** | 0.456 / 0.505 |
| Reserves 1 + 3 + SW1 on the C&K land (24.9 mm² ⚠) | 0.564 / 0.625 | 0.483 / 0.535 | 0.545 / 0.604 ✓ | 0.442 / 0.490 |

Board length (X, 29 mm wide) at which both measures pass, in total and in the tall zone:

| Case | Board length | Pod length |
|---|---|---|
| As built | 39.7 mm | ≈ 42.7 mm |
| Reserve 1 | 38.9 mm | |
| Reserve 3 | 38.4 mm | |
| SW1 C&K land | 39.4 mm | |
| Reserve 3 + SW1 C&K land | 38.1 mm | |
| **Reserves 1 + 3** | **37.6 mm** | |

### 10.3 Where the +35.0 mm² against BASELINE §5.3 come from

| Item | Change | Reason |
|---|---|---|
| SW1 | **+12.6** | EasyEDA land 4.53 × 6.54 mm against the 17.0 mm² assumption |
| O-2 | **+8.6** | 14 parts, 20.6 mm² against a 12.0 mm² reserve |
| Charger block | +5.0 | D14 reverse block, Q13 + R167 button level shifter, U15 land |
| J16 / J17 | +4.5 | drawn lands against 3.0 mm² each |
| Display | +2.3 | U21 + C1603 instead of the RC; U17 7.28 against 5.50; J13 −1.7 |
| Other (R123 and others) | +1.5 | – |
| Rounding | +0.4 | – |
| Fixed features | +5.7 more | root lands 6 × 6.75 against 6 × 6.0; J12 13.2 against 12.0 |

**Gate-1 verdict at planning level:**
- FAIL on v1's measure at 37 and at 38 mm. The project metric passes at both sizes; the tall zone passes everywhere.
- 41 mm alone no longer suffices: the 41 mm pod now needs reserves 1 + 3 as well.
- Otherwise the board must grow to 39.7 mm (pod ≈ 42.7 mm).

## Stage 1 additions (2026-11-14; `calc/o2_inhibit.json → stage1`, `calc/v3f_calc.json`)

All values in this section are ⚠ (model output) unless marked.

| Item | Value | Note |
|---|---|---|
| RISET 10.2 k (D-8) | 26.21 / 29.41 / 32.68 mA. C-rate: 0.374–0.467 C at 70 mAh, 0.397–0.495 C at 66 mAh, 0.437–0.545 C at 60 mAh | ≤ 0.5 C at ≥ 66 mAh nominal ✓ |
| O-2 heartbeat (D-1): Q16 gate peak | 1.11–1.20 V on the first edge (Miller); 1.49–1.57 V on later edges; > 1 V for 106–120 µs | Ciss 46 pF (E) |
| O-2 heartbeat: hold between 10 Hz pulses | Q14 \|VGS\| ≥ 88 % | |
| O-2 heartbeat: release after the last pulse | 0.64–1.67 s | |
| O-2 heartbeat: cost | about 1.0 µW for the MCU wake + 0.7 µW from the PV | only while the firmware wants PV charging |
| V_O2 down to 1.6 V (D-15) | cold stop 0.55–4.10 °C; hot stop 34.58–44.31 °C | inside 0–45 °C; margin 0.55 / 0.69 K |
| NTC_EN high with VBUS present (D-4) | BQ25170 hot stop moves to 46.34–53.58 °C | the firmware rule forbids this state |
| Cold start through Q14 at VGSth max (D-11) | Q14 needs \|VGS\| ≥ 0.854 V at 21.4 µA; the PV node is ≥ 1.85 V at 711 lx with the cold-start and O-2 load | nothing approves below 711 lx with the MCU off |
| G10 (h) front light (D-6) | 8.51–8.92 mA into a 330 Ω ±1 % jig load at 3.80 V; window 8.3–9.1 mA | |

---

## Gate 1, level 0 additions (2026-11-15; `calc/o2_dense.py` → `calc/o2_dense.json`; record in `../g1/dense/DENSE.md`)

All values are calculations ⚠ from the datasheet values quoted with their page; nothing was simulated.

- **Unchanged O-2 numbers:** `calc/o2_inhibit.py` was re-run today (exit 0); the result is identical to the stage-1 file (window 0.84–3.97 / 34.88–43.31 °C; 0.55–4.10 / 34.58–44.31 °C down to 1.6 V; approval light 711 lx).
- **R174 in 0201:** hold 0.64–1.67 s as before; 0.9 µW and ≤ 3 V against 50 mW and 25 V; a leak across the part shortens the hold (fail-safe).
- **R130 in 0805:** ≤ 52 mW (1.2 sun, −10 °C) = 42 % of 125 mW; 36 mW at 1 sun, 25 °C = 29 %.
- **R140 in 0201, 0.5 %, ±200 ppm/K:** ICHG max = 330 A·Ω / (10.2 kΩ × 0.995 × 0.993) = 32.75 mA = 0.496 C at 66 mAh.
- **FB1–FB6 in 0201:** rated 0.5 A against the 0.28–0.37 A U12 inrush; 1 A overload = the F1 opening limit.
- **O-2 option `SB_O2=merged`** (C175 1 nF, R175 100 kΩ in series from U20, R176 1 MΩ, R146 10 kΩ):
  - approval gate voltage 0.907 × V_O2: 1.45 V at 1.6 V (0.50 V above VGSth max);
  - heartbeat gate 1.72–1.82 V, ≥ 1.55 V at the end of a 10 µs pulse; undershoot −0.18 V;
  - approval edge into CHG_DIS: ≤ 0.27 V for about 10 µs with R146 10 kΩ (0.55 V for about 1 ms with 1 MΩ);
  - heartbeat current into the output clamp of the unpowered U20: about 5 µA peak, 0.5 nA average.
- **Pack PCM (ABLIC S-82D1A):** facts and coverage table in `o2_dense.json → pack_pcm_S82D1A`.
- **Area:** `area_check.md` (courtyard per option and per height class).
