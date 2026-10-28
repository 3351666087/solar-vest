# Solar-Harvesting Self-Powered Wearable Health Monitoring System: Architecture v3.0

> **Version** v3.0 · **Date** 2026-09-23 · **Supersedes** v2.0 (30 W rigid-panel design)
> **Trigger for this change**: the supervisor dropped the 30 W large panel in favour of a **6 V / 6 W rigid solar panel**, and asked that we **keep the research goals from the original email**.
> **Sections of v2 that remain valid and are not repeated here**: software stack / data model / CI (v2 §8.4, v1 §9), soldering SOP (v1 §6, v2 §6), power-on checklist (v1 §6.9 + v2 §6.5), BITalino / HeartBIT verification (v1 §1.4), hard safety rules (v1 §11, v2 §10).

Confidence markers are unchanged: ✅ actionable now · ⚠ rule-of-thumb value, check the datasheet or measure before acting · ❓ to be confirmed · 🚨 blocking

---

# 0. Conclusions

## 0.1 In one sentence

> **The 6 V / 6 W panel is closer to the plan in the original email than the 30 W panel was**: its voltage falls right in the 5–6 V range the email suggested, and it can be mounted on the body, so the "self-powered solar-harvesting wearable" positioning holds again.
> The price is that **energy is back in the "tight" regime**: on a typical wearing day, **continuous** BITalino acquisition cannot be self-powered (EAR ≈ 0.43), but it **extends runtime by about 76%**; with the **intermittent measurement** the email asks for (duty cycle ≤ 30–43%), the system reaches energy balance.
> The **truly low-power BLE sensor** mentioned in the email (about 5 mW) has a 14–60× margin in every scenario with daylight, and **fails only under indoor artificial light alone**.
> This conclusion matches the supervisor's original judgement exactly — "solar can extend runtime, but it cannot be guaranteed up front to eliminate external charging" — and we can now state it in numbers.

## 0.2 Directional changes relative to v2

| Dimension | v2 (30 W) | **v3 (6 V / 6 W)** |
|---|---|---|
| Relationship to the original goals in the email | Panel cannot be worn on the body; positioning conflict | ✅ **Panel can be mounted on the body; positioning returns to the email's intent** |
| Continuous acquisition (BITalino) | Feasible, EAR 1.0–3.9 | ❌ Typical day EAR 0.43; **feasible only on a good day (EAR 1.26)** |
| Duty-cycle scheduling | Demoted to an energy-saving option | 🔴 **Becomes the main operating mode again** (typical-day cap 43%) |
| Low-power node (Phase 3) | Optional | 🔴 **Back to the core**: it is the direct implementation of "BLE, intermittent measurement, low-power sensors" from the email |
| Top technical risk | EMC (8 W switch-mode supply) | EMC downgraded to moderate (≈1.7 W when worn); **tight energy budget + wearability** become the main issue |
| 18 V safety isolation | Required | Dropped (open-circuit voltage about 7 V ⚠) |
| Rationale for dual batteries (ADR-006) | Noise isolation | **Becomes energy saving**: suspending charging during acquisition costs 13 percentage points of duty cycle; dual batteries recover them |
| EVK10941 | Removed from the main power path | ⚠ **Still cannot be connected directly** (open-circuit voltage about 7 V, still above its input limit of about 5 V); its value is actually higher on the low-light comparison branch |

## 0.3 Five things you can do today (no need to ask the supervisor)

1. **Photograph the nameplate on the back of the panel**: P<sub>max</sub>, V<sub>mp</sub>, I<sub>mp</sub>, V<sub>oc</sub>, I<sub>sc</sub>, outline dimensions, **weight**, and whether it has an aluminium frame. All the protection parts and MPPT set points in this document depend on these values.
2. Outdoors on a sunny day, measure V<sub>oc</sub> and I<sub>sc</sub> with a multimeter (I<sub>sc</sub> is about 1.1–1.2 A ⚠; use the 10 A range + 10 A jack).
3. **TC-01: measure the BITalino's power consumption.** It currently sits right on the decision boundary (see §2.5): a measured 120 mW and a measured 240 mW lead to two different designs.
4. Check whether any companion parts for the 30 W design have already been ordered (18 V CN3791, 0.02 Ω shunt resistors, SMAJ26A, 18 AWG wire, etc.) and handle them according to the difference list in §7.
5. Find a well-fitting vest or backpack and try out how a panel mounted on the back feels (weight, sway, whether it presses against the chair back when sitting).

---

# 1. Point-by-point comparison with the original research goals (the supervisor's first email)

The "intent of the email" below comes from your summary of the email.

| # | Intent of the email | Status with 6 V / 6 W | Notes |
|---|---|---|---|
| 1 | Positioning: **self-powered solar-harvesting wearable**, panel **mounted directly on the wearable**, not to be called wireless power transfer | ✅ **Holds** | The panel can be mounted on the back of a vest (§5.4). The naming conflict from v2 disappears; all WPT terminology remains banned |
| 2 | Architecture: panel → charge controller (MPPT optional) → 3.7 V Li-ion battery → regulator → wearable electronics | ✅ **Exact match** | Charge controller is the CN3791 (6 V version, with MPPT); the BITalino runs directly from the battery, and the low-power node uses the nRF52840's on-chip DC/DC |
| 3 | Panel: small and **flexible**, about **5–6 V, 0.5–2 W** | ⚠ **Partial deviation** | Voltage ✅ matches; but it is a **rigid panel**, and its power is **3×** the suggested upper limit. More headroom on energy, but heavier and stiffer to wear. **§3 turns this deviation into a research advantage**: uniform attenuation can emulate 0.5–2 W panels on the same panel |
| 4 | Load: prefer **low-power** health sensors with **BLE and intermittent measurement** | ⚠ **BITalino is not low-power**; ✅ **"intermittent measurement" is exactly what rescues it** | BITalino about 240 mW ⚠; with intermittent measurement (typical-day duty cycle ≤ 43%) it can reach energy balance; a truly low-power node (about 5 mW) is the direct implementation of this goal → Phase 3 is back to the core |
| 5 | Practical constraints to watch: lighting, panel area, clothing occlusion, shading from body movement, whether the panel can stay exposed | ✅ **All turned into experiments** | §6 designs a test case for each, and builds a "loss waterfall" that quantifies them stage by stage |
| 6 | Solar can **extend runtime**, but cannot be guaranteed up front to eliminate external charging | ✅ **Can be answered quantitatively** | Typical day +76% runtime, overcast/rainy day +41%, indoor only +1%, good day net-positive energy (§2.4) |
| 7 | Validation items (implementation suggestions, not acceptance criteria): voltage, current, temperature rise, supply stability under different lighting, runtime gain | ✅ **All kept** | Reuses the v2 measurement chain; shunt resistors re-selected for the new power level (§5.2) |

> **Conclusion: the original research goals can be kept in full, and the 6 V / 6 W panel is closer to the email's intent than the 30 W panel.** The only deviation that needs to be explained in the report is item 3 (rigid, 6 W).

---

# 2. Energy model v3

Same assumptions as v2 so the results can be compared directly: temperature coefficient −0.4 %/°C ⚠, harvesting-chain efficiency 85% ⚠, BITalino taken as 240 mW + MCU 2 mW ⚠ (**to be replaced by TC-01**), standby 0.2 mW.

## 2.1 Panel model

```
P = 6 W × (G / 1000) × [1 − 0.004 × (T_cell − 25)]

6 W is the rating under standard test conditions (STC), so panel area does not
enter the energy calculation; it only affects wearability (§5.4).
```

## 2.2 Instantaneous power per scenario (panel worn on the back)

| Scenario | Plane-of-array irradiance G ⚠ | Cell temperature | Panel output |
|---|---|---|---|
| Outdoors, sunny, worn (random orientation) | 300 W/m² | 45 °C | **1.66 W** |
| Outdoors, overcast, worn | 120 W/m² | 30 °C | **0.71 W** |
| Indoors right by a window < 0.5 m, panel facing the window | 150 W/m² | 30 °C | **0.88 W** |
| Indoors 2 m from a window | 35 W/m² | 25 °C | **0.21 W** |
| Indoors, artificial light only, 500 lux (low-irradiance efficiency taken as ×0.5 ⚠) | 1.5 W/m² | 25 °C | **4.5 mW** |

## 2.3 Four typical days

| Light profile of the day | Daily harvest | Average power | BITalino continuous EAR | BITalino duty-cycle cap (charge while acquiring) | Duty-cycle cap (charging suspended during acquisition) | **Low-power node EAR** |
|---|---|---|---|---|---|---|
| **Good day**: 2 h outdoors sunny + 6 h by a window | 7.31 Wh | 305 mW | ✅ **1.26** | 100% | 56% | 61 |
| **Typical day**: 1 h outdoors sunny + 6 h at 2 m from a window + 8 h artificial light | 2.51 Wh | 105 mW | ❌ 0.43 | **43%** | **30%** | **21** |
| **Overcast/rainy day**: 1 h outdoors overcast + 6 h at 2 m from a window + 8 h artificial light | 1.70 Wh | 71 mW | ❌ 0.29 | 29% | 23% | 14 |
| **Indoor only**: 10 h artificial light | 0.04 Wh | 1.6 mW | ❌ 0.01 | 1% | 1% | ❌ **0.3** |

How to read it:
- **43% duty cycle** ≈ 4.3 minutes of acquisition every 10 minutes; **30%** ≈ 3 minutes every 10 minutes. This is the "intermittent measurement" from the email.
- "Charging suspended during acquisition" is the cost of ADR-004 (turn the charger off during acquisition to keep switching noise out of the ECG): all light falling on the panel during an acquisition window is wasted. **On a typical day this costs 13 percentage points of duty cycle.** This is the new rationale for dual batteries (ADR-006) in v3 (§4).
- **Indoor artificial light alone is the scenario in which no load can be self-powered**, including the low-power node. The report should never say "charges automatically under indoor lighting".

## 2.4 Runtime extension ratio RES (the email's own words: solar can extend runtime)

BITalino **continuous** acquisition, with light vs. without light:

| Light on the day | 1000 mAh: no light → with light | 2500 mAh: no light → with light | **Runtime gain** |
|---|---|---|---|
| Good day | 15.3 h → never runs down | 38.2 h → never runs down | **Net-positive energy** |
| Typical day | 15.3 h → 26.9 h | 38.2 h → 67.3 h | **+76%** |
| Overcast/rainy day | 15.3 h → 21.6 h | 38.2 h → 54.1 h | **+41%** |
| Indoor only | 15.3 h → 15.4 h | 38.2 h → 38.5 h | **+1%** |

> This table can go straight into the report to the supervisor: it quantifies "extends runtime but does not guarantee freedom from charging" as four numbers.

## 2.5 🚨 TC-01 now sits right on the decision boundary

On a typical day, how the measured BITalino power maps to the design:

| Measured BITalino power | Continuous EAR | Duty-cycle cap | Implication |
|---|---|---|---|
| 60 mW | 1.69 | 100% | Continuous acquisition is self-powered; Phase 3 becomes a nice-to-have |
| 120 mW | 0.86 | 86% | Close to continuous; light scheduling is enough |
| 180 mW | 0.57 | 57% | Scheduling required |
| **240 mW (current estimate)** | **0.43** | **43%** | **An explicit intermittent-measurement scheme is required** |

The BT and BLE versions may differ considerably in power consumption. **Do TC-01 first; it is the single most influential unknown in all of v3.**

## 2.6 Battery: autonomy and charge-current matching

| Battery | Typical day · BITalino at 43% duty cycle | Low-power node | 0.5 C charge current | Match with the panel |
|---|---|---|---|---|
| 1000 mAh (on hand) | 1.5 days | 31 days | 0.50 A | Sufficient when worn (about 0.38 A); current-limited when the panel faces strong light directly (about 1.22 A) |
| 2000 mAh | 2.9 days | 62 days | 1.00 A | Roughly matched |
| **2500 mAh (recommended)** | **3.7 days** | 77 days | 1.25 A | ✅ **Absorbs the panel's 1.22 A peak exactly** |

**Recommendation: a single 2500 mAh cell as the main battery of the device under test (DUT)**; the existing 1000 mAh goes to the control unit. If TC-05 decides in favour of dual batteries, add another 2500 mAh cell (about 50 g more on the back).

---

# 3. Deviations from the email, and how to turn them into research assets

## 3.1 Deviation 1: 6 W is 3× the 0.5–2 W the email suggested

**Approach: attenuate uniformly with neutral-density mesh to emulate 0.5 / 1 / 2 / 3 W panels on the same panel.**
Uniform attenuation is equivalent to lower irradiance and scales the output proportionally, giving a "panel power ↔ self-powering capability" design curve (typical day):

| Equivalent panel power | Daily harvest | BITalino duty-cycle cap | Low-power node EAR |
|---|---|---|---|
| 0.5 W | 0.21 Wh | 3.5% | 1.7 |
| 1 W | 0.42 Wh | 7.1% | 3.5 |
| **2 W (upper limit suggested in the email)** | 0.84 Wh | 14% | 7.0 |
| 3 W | 1.25 Wh | 22% | 10.5 |
| **6 W (as delivered)** | 2.51 Wh | 43% | 21 |

> This curve directly addresses the "panel area" constraint in the email: **for a given load, how large a panel is enough?** That is a more generally useful result than reporting only "what a 6 W panel can do".
> ⚠ Note: the attenuation must be **uniform across the whole panel**. Partial shading creates hot spots, produces multiple peaks in the I-V curve, and can damage the panel (v2 §5.1.3). Also, after attenuation the panel voltage drops only slightly (logarithmically) and stays higher than that of a genuinely small panel; the report must state this approximation.

## 3.2 Deviation 2: rigid rather than flexible

A rigid panel cannot conform to the curved body surface, so it needs a **backplate-style mount** (§5.4). This brings two research benefits:
1. The panel normal is fixed, so a **reference cell** can be mounted in the panel plane together with an **orientation sensor**, separating "orientation" and "occlusion" from "panel efficiency" (§4 ADR-010).
2. A rigid panel is easy to make detachable, which makes it convenient to compare "the same panel in different wearing positions" (TC-20).

---

# 4. Architecture decision updates

| ADR | Content | v3 status |
|---|---|---|
| ADR-001 | The PMB owns the battery; the BITalino is only a load | ✅ Unchanged |
| ADR-002 | Dual charging paths | 🔄 Main path is the **CN3791 (6 V version)**; the EVK10941 still cannot be connected directly and is kept as a **low-light comparison branch** (with a small flexible cell) |
| ADR-003 | Role of the BITalino | 🔄 **Back to the v1 position**: the BITalino serves as the **reference instrument and intermittent-measurement demonstrator**; **the low-power node is the direct implementation of the email's goal**, and Phase 3 is brought forward to the core |
| ADR-004 | Charging suspended during acquisition (time-division multiplexing) | ✅ Kept, **but at an energy cost**: the typical-day duty-cycle cap drops from 43% to 30% |
| ADR-005 | Hardware sync pulse | ✅ Unchanged |
| ADR-006 | Alternating dual batteries | 🔄 **Rationale changed**: from "noise isolation" to "**don't waste the light that falls during acquisition windows**". Whether to build it is still decided by TC-05 |
| ADR-007 | Split architecture (back unit + chest unit) | 🔄 Kept, **with the rationale changed from 18 V safety to EMC + mechanics**: panel and charger on the back, ECG front end on the chest, separated by 20–30 cm of torso |
| ADR-008 | INA226 coulomb counting instead of MAX17048 | ✅ Unchanged |
| **ADR-009 (new)** | **Light-aware scheduling** | See below |
| **ADR-010 (new)** | **Plane-of-array irradiance + orientation logging** | See below |

### ADR-009: Light-aware scheduling (energy-neutral scheduling)

**Decision**: acquisition windows are not fixed; the MCU schedules them dynamically based on "current charging power + state of charge":
- **In strong light** (high charging power): prioritise charging, defer acquisition;
- **In weak light** (indoors, charging power close to 0): prioritise acquisition; suspending charging then loses almost no energy;
- **Constraints**: the maximum interval between two acquisitions must not exceed T<sub>max</sub> (set by clinical requirements, e.g. 15 minutes ❓), and the system degrades gracefully when the state of charge falls below a threshold.

**Rationale**: without dual-battery hardware it recovers most of the 13 percentage points lost to ADR-004. This kind of "energy-neutral operation" scheduling is a classic problem in energy-harvesting sensor networks, and **can in itself be a research contribution** (a literature search is recommended before writing the paper).

**Cost**: sampling instants are no longer uniform, so HRV analysis must treat the data as non-uniformly sampled; the scheduling-policy version must be recorded in the manifest.

### ADR-010: Plane-of-array irradiance + orientation logging

**Decision**:
1. Mount a calibrated reference cell next to the panel, **coplanar with the panel** (this is v2's P0-5, just in a different mounting position), to measure "the light actually reaching the panel";
2. Switch the telemetry MCU to the **XIAO nRF52840 Sense** (on-board 6-axis IMU ⚠ verify the part number), to record torso orientation and activity state.

**Rationale**: the constraints listed in the email (clothing occlusion, shading from body movement, whether the panel can stay exposed) are all problems of **the light in the panel plane**, not of the panel itself. Without measuring plane-of-array irradiance, these cannot be separated from panel efficiency.

**Loss waterfall** (every stage has a measurement point; it can go straight into the paper as a figure):

```
Available ambient light (reference cell, horizontal, nearby)
  └─ Orientation / body shading / clothing occlusion ──►  Plane-of-array incident light (coplanar reference cell + IMU)
        └─ Panel efficiency / temperature ──────────────►  Panel output (INA226 #1)
              └─ MPPT / charging efficiency ────────────►  Net battery gain (INA226 #2 coulomb integration)
                    └─ Load ────────────────────────────►  Acquisition time / runtime
```

---

# 5. Hardware changes

## 5.1 Input stage (v2 → v3)

| Ref. | v2 (18 V) | **v3 (6 V)** | Rationale |
|---|---|---|---|
| F1 | 2 A slow-blow, in the panel junction box | **1.5 A slow-blow or resettable fuse (PPTC)** ⚠ | I<sub>sc</sub> about 1.1–1.2 A ⚠; the fuse still sits at the panel end |
| TVS1 | SMAJ26A | **SMAJ8.5A** ⚠ | Rule unchanged: breakdown voltage > measured V<sub>oc</sub> × 1.15 (V<sub>oc</sub> about 7.2 V → need > 8.3 V) |
| D1 (reverse-polarity / reverse-current blocking) | SS54 | **Rev A: SS34; Rev B: LM74700 ideal-diode controller + N-MOS** ⚠ | 🔴 See the note below |
| C1 | 220 µF / 35 V | 220 µF / 16 V low-ESR (35 V parts already bought can be used as is) | — |
| L1 common-mode choke | Required | Optional (keep the ferrite ring) | Switched power drops to about 1/5 |
| Wiring | 18 AWG shielded silicone wire + XT30 | **22 AWG silicone wire + JST-XH or XT30** | Current about 1 A |
| 18 V isolation gap | ≥ 3 mm, safety requirement | **≥ 2 mm, for EMC only** | Open-circuit voltage about 7 V ⚠; no longer a safety issue |

🔴 **At 6 V the reverse-polarity / reverse-current diode becomes an efficiency problem**:
- A Schottky's drop of about 0.4 V is only 2% at 18 V, but **about 7%** at 6 V. The energy budget is already tight; this 7% cannot be ignored.
- Do not replace it with a P-MOS "reverse-polarity protection" circuit: that arrangement **does not block night-time reverse current**. The body diode of the CN3791's external P-MOS switch may bring the battery voltage back to VIN ⚠; once that voltage turns the P-MOS on, the battery discharges through the panel's dark current.
- **The LM66100 cannot be used on the panel side**: its input limit is about 5.5 V ⚠, below the panel's open-circuit voltage. It is only suitable on the battery side (Q3/Q4).
- Recommendation: use the SS34 in Rev A (many CN3791 modules already include an input diode; check the board first), and switch to an **LM74700-class ideal-diode controller + N-MOS** (input 3.2–65 V ⚠) in Rev B: about 0.1% loss, and it blocks reverse current.

## 5.2 Metering: shunt resistors re-selected for the new power level

| Position | v2 | **v3** | Full scale / resolution |
|---|---|---|---|
| RS1 (panel side) | 0.02 Ω | **0.05 Ω by default + 0.47 Ω "indoor range" pads (solder-bridge selectable)** | 0.05 Ω: about 1.6 A / 50 µA; 0.47 Ω: about 174 mA / about 5 µA |
| RS2 (battery side, bidirectional) | 0.02 Ω | **0.05 Ω** | Charging 1.25 A → 62.5 mV ✓; resolution 0.08% at 65 mA discharge |

**Why an "indoor range"**: indoors only, the panel current is below 1 mA. With 0.05 Ω that is only a dozen or so LSBs, and the INA226's offset voltage referred to current is on the order of a hundred µA ⚠, so the indoor data would be buried in noise. "Can it extend runtime indoors?" is exactly what the email cares about, so this range cannot be skipped. The Kelvin four-wire connection requirement is unchanged.

## 5.3 CN3791: configuration and two low-light traps

```
MPPT set point: V_MPPT = V_ref × (1 + R_top / R_bot)
   V_ref per the datasheet ⚠; target = measured V_mp (typically 0.76–0.8 × V_oc, about 5.5–5.8 V)
   → buy the "6 V solar panel version" module; if the 18 V version has already been bought,
     usually only the MPPT divider resistors need changing (some modules have a potentiometer) ⚠ also verify the module's minimum input voltage

Charge current: set R_cs for 1.0–1.25 A (2500 mAh); limit to 0.5 A when a 1000 mAh cell is connected
```

⚠ **Low-light trap 1: indicator LEDs.** Many cheap modules have two LEDs, CHRG / DONE, at 1–3 mA each. Indoors only, the panel produces less than 1 mA in total, so **the indicator LEDs would eat the entire harvest**. Remove or disconnect the LEDs.

⚠ **Low-light trap 2: quiescent current.** The CN3791's own operating current is unverified ⚠. If indoors it draws more than the panel produces, low-light operation should switch to the EVK10941 branch (with a small cell). **This is exactly why the AEM10941 comparison branch is kept**: CN3791 for strong light, AEM10941 for low light, and compare the two on "start-up threshold / low-light efficiency" (TC-18).

## 5.4 🔴 Wearable mounting (the new main issue in v3)

Panel dimensions and weight ❓ to be confirmed from the nameplate (common 6 V / 6 W rigid panels are about A5 size, 200–450 g ⚠, depending on the laminate and whether there is a frame).

| Position | Light | Relation to the ECG | Wearability | Verdict |
|---|---|---|---|---|
| **A Back (scapular area), backplate-style vest** | Random orientation when walking outdoors | ✅ Separated by the torso, far from the chest electrodes | Weight on the back; leans against the chair back when sitting ⚠ | ✅ **Recommended**; best fits "mounted directly on the wearable" |
| B Top of a backpack / shoulder strap | ✅ Close to horizontal, best light | ✅ Far away | More "carried" than "worn" | Can serve as a comparison position (TC-20) |
| C Chest | Average | ❌ Presses on the electrodes and leads; closest for EMC; heat risk near the heart region | — | ❌ Not used |
| D Arm / head | — | — | ❌ Size and weight rule it out | ❌ |

**Mount requirements**:
- Quick release (buckles / hook-and-loop / magnetic), to make position comparisons easy;
- **10–20 mm air gap + thermal insulation layer** between the back of the panel and the body (the back of the panel can reach 60–70 °C on a sunny day ⚠);
- 🚨 The TEUCER HP600 **thermal silicone pad still must not be placed on the body side** (v2 §1.2); it is only for heat conduction from "charger → enclosure";
- The coplanar reference cell is fixed next to the panel frame (ADR-010);
- The cable from the back unit (panel + PMB-H + battery) to the chest unit is about 0.4–0.6 m long, routed along the inside of the vest, with a magnetic connector to prevent pull-out.

## 5.5 Supercapacitors: the leakage problem is back

On an indoor-only day the average harvest is only **1.6 mW**, while the supercapacitor bank's leakage plus balancing loss is about **280 µW**, i.e. **17%**.
→ Change the balancing resistors back to **1 MΩ** (about 16 µW), and have the MCU **disconnect the supercapacitor bank** during prolonged low light (the approach from v1 §5.6 applies again).

---

# 6. Experiment plan: turning the constraints listed in the email into experiments

The existing TC-01…TC-19 (v1 §10, v2 §9) remain valid, with **TC-01 and TC-05 at the highest priority**. New additions:

| ID | Email item addressed | Purpose | Method | Output |
|---|---|---|---|---|
| **TC-03b** | Panel area | "Panel power ↔ self-powering capability" curve | Uniformly attenuate the whole panel with ND mesh to 0.5 / 1 / 2 / 3 / 6 W equivalent; calibrate with the coplanar reference cell | The **measured version** of the curve in §3.1 |
| **TC-20** | Available light | Wearing-position comparison | Same day, same route: back vs. top of backpack vs. horizontal reference | Daily harvest in Wh for each position |
| **TC-21** | **Clothing occlusion** | Fabric transmission loss | Thin cotton / shirt / jacket / backpack strap / long hair covering part of the panel; measure output for each | Transmission ratio per fabric; ⚠ partial shading causes hot spots, so keep exposures short and monitor temperature |
| **TC-22** | **Shading from body movement** | Effect of posture and activity | Sitting / standing / walking / turning; IMU logs orientation, coplanar reference cell logs incident light | "Orientation → incident light" relationship |
| **TC-23** | **Whether the panel can stay exposed** | Exposure ratio over a real day | Log a full day of wearing; compute the fraction of time with plane-of-array irradiance > 50 W/m² | Exposure ratio; provides measured grounding for the four day types in §2.3 |
| **TC-24** | **Runtime gain** | Measured RES | Same load, same schedule: panel covered vs. normal wearing (or Unit A vs. Unit B) | The **measured version** of the table in §2.4 |
| **TC-25** | Supply stability | Ripple at the load during charging | Oscilloscope on the BITalino supply pin, with the charger on / off | Ripple in mV<sub>pp</sub>; cross-checked against the TC-05 ECG noise results |

**Form of the final research deliverables**: a "loss waterfall" figure (ADR-010) + a "panel power ↔ self-powering capability" curve + an RES table + a set of "clothing / posture / position" coefficients. Together these fully answer every practical constraint raised in the email.

---

# 7. Procurement list differences (relative to v2)

> If the v2 list has already been handed to the supervisor or ordered, adjust it according to these tables.

## 7.1 Kept (unchanged)

| v2 No. | Item | Notes |
|---|---|---|
| P0-1 | 1S Li-ion battery **2500 mAh** with PCM | Quantity can drop from 4 to **2–3** (main + spare; add 1 if going dual-battery) |
| P0-3 | INA226 module ×4 | — |
| P0-5 | Irradiance reference (reference cell preferred) | **Buy 2 instead**: one coplanar with the panel, one horizontal as the ambient reference (ADR-010) |
| P0-7 | AO3401 / AO3400 | — |
| P0-8 | ECG electrodes, 500 pcs | — |
| P0-9 | LM66100 | **Battery side only** (Q3/Q4); not usable on the panel side |
| P0-10 | Thermal insulation material | 🔴 More important now: the panel sits against the body |
| P1-12 | Adjustable current-limited DC power supply | Don't buy if the Workspace has one |
| P1-14 | K-type thermocouple ×4 | — |
| P1-15 | Small flexible solar cell ×2 (< 5 V) | 🔴 **Upgraded to P0**: the low-light comparison branch (EVK10941) depends on it |
| P1-18/19/20/21 | NTC, magnetic connectors, PCB consumables, assembly consumables | — |

## 7.2 Modified

| v2 No. | v2 | **Change to** | Rationale |
|---|---|---|---|
| P0-2 | CN3791 module (18 V scenario) | **CN3791 "6 V solar panel version"** ×3 | MPPT set point about 5.5–5.8 V; if the 18 V version was already bought, try changing the divider resistors ⚠ |
| P0-4 | 0.02 Ω shunt ×20 | **0.05 Ω ×10 + 0.47 Ω ×10** | New range + indoor range (§5.2) |
| P0-6 | XIAO nRF52840 ×3 | **XIAO nRF52840 Sense ×3** ⚠ | On-board IMU for orientation logging (ADR-010) |
| P0-11 | 18 AWG shielded wire + XT30 + 2 A fuse | **22 AWG silicone wire + JST-XH + 1.5 A fuse / PPTC** | Current about 1 A |
| P1-17 | SMAJ26A, SS54, 220 µF/35 V | **SMAJ8.5A, SS34, 220 µF/16 V**; add **LM74700 + N-MOS** for Rev B ⚠ | §5.1 |
| P1-16 | 10 of each EMC part | Halve the quantities | Switched power drops to about 1/5 |
| P1-13 | 60–150 W electronic load | **≤ 30 W small electronic load**, or a home-made resistor box | The panel is only 6 W |

## 7.3 Cancelled

| Item | Rationale |
|---|---|
| Carrying / bracket structure for the 30 W panel (v2 P2-27) | Panel has been replaced |
| 18 V-specific SMAJ26A, SS54, 18 AWG shielded wire | Same as above |

## 7.4 New / upgraded

| Priority | Item | Qty | Rationale |
|---|---|---|---|
| **P0** | **Panel wearable mount**: adjustable vest or chest-and-back harness, rigid backplate (padded), quick-release buckles, standoff feet (to keep an air gap) | 1 set | Physical realisation of "mounted directly on the wearable" |
| **P1 (formerly P2-23)** | **ADS1292R or MAX86150 evaluation module** | 1 each | Phase 3 is back to the core; validate the low-power front end early |
| P1 | Fabric samples (thin cotton, shirt, jacket fabric) + backpack straps | Several | TC-21 clothing occlusion |
| P1 | Neutral-density mesh / ND filters, multiple grades | 1 set | TC-03b panel-power emulation (already listed in v2; confirm it is kept) |
| P2 | Second 6 V / 6 W panel of the same model | 1 | If two devices are to be worn at the same time, or for a "different positions at the same moment" comparison (TC-20) |

## 7.5 Items already delivered but idle

| Item | Suggested handling |
|---|---|
| 395×460 mm 18 V 30 W panel | ❓ Ask the supervisor whether to return or exchange it. If kept, it can serve as a bench "strong-light fallback source" for long full-load burn-in tests of the charger |
| 18 V CN3791 modules already purchased (if any) | First try changing the MPPT divider for use with the 6 V panel ⚠; if that fails, repurpose them for bench testing |

---

# 8. Phase plan adjustments

| Week | Content | Gate |
|---|---|---|
| W1 | Nameplate parameters, V<sub>oc</sub>/I<sub>sc</sub>, weight; **TC-01**; BITalino model and BT/BLE; send out the procurement difference list | Replace every ⚠ power figure with the TC-01 measurement and recompute §2 |
| W2 | Wearable mount prototype (back); repository / manifest; **ethics application submitted** | Purchases ordered; ethics application submitted |
| W3–4 | PMB-H Rev A (6 V input); firmware v0.1 (duty-cycle scheduling by default); TC-02 I-V, **TC-03b panel-power curve** | Power-on checklist fully passed |
| W5–6 | **TC-05 ECG noise comparison → decide the combination of ADR-004 / 006 / 009**; in parallel: low-power front-end selection (ADS1292R vs. MAX86150) | Decision point |
| W7–8 | TC-07 thermal safety phase 1 (off-body); TC-21 clothing, TC-22 posture (bench + short on-body sessions) | 🚨 No on-body wear until thermal safety phase 1 passes |
| W9–10 | Field wearing days: TC-20 position, TC-23 exposure ratio, **TC-24 runtime gain** | Telemetry data completeness > 99% |
| W11–14 | Low-power node prototyping and integration; Bland–Altman agreement analysis against the BITalino; **self-powered demonstration** (good day / typical day) | Low-power node typical-day EAR ≥ 5 |

---

# 9. Items needing the supervisor's confirmation (trimmed to 4)

| # | Question | Our recommendation |
|---|---|---|
| **Q1** | **Where is the panel mounted?** Back of a vest vs. top of a backpack | **Back of a vest**: far from the chest electrodes, and the best fit for "mounted directly on the wearable" in the email; top of a backpack as the comparison position |
| **Q2** | **Load strategy**: BITalino as the intermittent-measurement demonstrator + **low-power node developed in parallel** (requires buying ADS1292R / MAX86150 modules) | Recommend running both tracks in parallel: the BITalino provides early data and the reference standard, and the low-power node is the direct implementation of the email's goal of "BLE, intermittent measurement, low power" |
| **Q3** | What to do with the 30 W panel and the 18 V companion parts already purchased | Return them if possible; otherwise keep them for bench burn-in testing |
| **Q4** | Old questions still open: ethics approval route, whether to continue the thermoelectric comparison, Workspace instruments and PCB equipment capability | Same as v2 §12 |

> The panel plan has now changed twice; we recommend **confirming Q1 and Q2 in writing by email** this time before starting procurement and PCB work, to avoid rework.

---

# 10. Limitations

1. **BITalino power consumption is still an estimate**, and it now sits right on the decision boundary (§2.5). Until TC-01 is done, all duty-cycle numbers in §2 are order-of-magnitude only.
2. **Irradiance in the wearing scenarios (e.g. 300 W/m² outdoors) is an empirical estimate**; body orientation and clothing could shift it by 2–5×. This is exactly what TC-20 to TC-23 measure.
3. **The panel's nameplate parameters are unknown**: V<sub>oc</sub> and I<sub>sc</sub> determine the TVS, fuse and MPPT set point, so the selections in §5.1 must wait for nameplate confirmation.
4. **The CN3791's quiescent current and minimum input voltage are unverified**; they determine whether it can still operate indoors.
5. **The AEM10941's 5 V input limit comes from my memory** and has been marked ⚠ throughout; it must be confirmed against the datasheet before it goes on a board.
6. **Emulating a small panel by ND attenuation is an approximation**: power is equivalent, but the voltage remains higher than that of a genuinely small panel (§3.1); the report must state this.
