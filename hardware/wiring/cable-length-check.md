# Cable length check (every cable: length needed vs length available)

2026-10-12 · corresponds to [wiring-table.md](wiring-table.md) (W01–W15)

**How it was calculated**
- **Length needed**: measured in the 3D harness model along the actual route over the vest surface and inside the pods (`harness.json`).
- **Actual length** comes from three sources:
  1. The photos you sent (using a 13-inch MacBook Air as the ruler; method in §1);
  2. Official manufacturer pages (sources in §4);
  3. Typical specifications of equivalent items on Taobao. Category 3 is marked "check on arrival".
- **Acceptance criterion**: ready-made cables need at least 50 mm of slack, because breathing and bending stretch the route; cables that have to be cut get an extra 80 mm cutting allowance.

---

## 1. Original panel lead (measured from photos)

**Measurement method**
- Perspective-corrected using two known dimensions in the photo:
  - MacBook Air 13-inch body 304.1 × 215 mm;
  - Panel 261.8 × 171 mm.
- After correction, measured segment by segment along the cable centreline. Error on visible segments ≈ ±5 %.
- The coil (the wound-up bundle) is estimated as number of visible turns × turn length.

| Segment | Length |
|---|---|
| Junction box → panel edge | 99 mm |
| Panel edge → coil | 117 mm |
| Coil (≈ 3.8 m, visible part ≥ 2.0 m) | ≈ 3.8 m |
| Top of coil → waterproof connector | 129 mm |
| **Panel side total (junction box → waterproof connector)** | **≈ 4.2 m** |
| Waterproof connector body | 74 mm |
| Other side of connector → breakout | 410 mm |
| Bare cores after breakout | 69–83 mm |
| **Overall length** | **≈ 4.7–4.8 m** (consistent with the listed 5 m) |
| Outer diameter | 4.1 mm (2-core) |

**W01 only needs 221 mm** (cut length 350 mm).

### ⚠ Ask the vice dean before cutting: a cut cannot be undone

The panel belongs to the vice dean. There are two options, cut or don't cut:

| Option | How | Cost |
|---|---|---|
| **A. Cut (recommended, provided the vice dean agrees)** | Cut the panel side at 200 mm and solder it to the 100 mm tail left on the waterproof-connector side (2 solder joints + heat-shrink tubing). Cut the other side of the connector to 200 mm, strip it and connect to the J1 terminal. Keep the ≈ 3.8 m offcut for W04 (0.45 m) and W05 (0.6 m) | Irreversible. Return the remaining 2.7 m to the vice dean |
| **B. Don't cut** | Wind the 3.8 m coil into a Ø70 mm figure-eight and strap it to the side of the back pod with hook-and-loop tape. **Do not stuff it into the air gap under the panel** (that reaches 60–70 °C). Buy an extra 2 m of red/black 2-core wire (0.3 mm²) for W04 / W05 | ≈ 60 cm³ extra volume and ≈ 90 g on the back |

---

## 2. All cables compared

| Cable | Purpose | Needed (route) | Actual length available | Basis | Slack | Verdict |
|---|---|---|---|---|---|---|
| W01 | Panel → PMB-H J1 | 221 mm | 4.2 m + 0.41 m | Measured from photo | Ample | ✅ Handle per §1 |
| W02 | 2500 mAh battery → J2 | 50 mm | Battery's own PH2.0 lead, typically 50–100 mm | Taobao equivalents | ≥ 0 | ✅ (check on arrival; if too short, extend with a PH2 pre-wired lead) |
| W03 | NTC → J3 | 36 mm | Ready-made NTC with lead, typically ≥ 100 mm | Taobao equivalents | ≥ 64 mm | ✅ |
| W04 | REF1 reference cell → J7 | 344 mm | 0.45 m (panel-lead offcut) | §1 | 106 mm | ✅ |
| W05 | REF2 reference cell → J8 | 482 mm | 0.6 m (panel-lead offcut) | §1 | 118 mm | ✅ |
| **W06** | Back → chest, 5-core | **531 mm** | **0.7 m must be purchased** (if unavailable, buy 1 m and coil the excess in the channel) | Taobao PH2.0 5P double-ended straight-through cable | 169 mm | 🛒 **The 0.6 m in the original list is too short**; corrected |
| W07 | LIB → Core B battery socket | 59 mm | PH2.0 double-ended 10 cm | BOM | 41 mm | ✅ |
| W08 | LIB SYNC → Core B I1 | 53 mm | The 10 cm UC-E6 cable from the HeartBIT kit, one end cut off | PLUX kit documentation | 47 mm | ✅ |
| W09 | ECG sensor → Core B A2 | 147 mm | 30 cm UC-E6 sensor cable | HeartBIT kit | 153 mm | ✅ Coil the excess once inside the pocket |
| W10a/b/c | B's 3 leads (red/black/white) | 185 / 142 / 172 mm | 30 cm | Supplied with the HeartBIT ECG sensor | ≥ 115 mm | ✅ |
| **W11 + a/b/c** | C's 3-lead cable | **207 / 231 / 246 mm** (plug to electrode, including 83 mm inside the case) | **30 cm** | PLUX official: Board Kit BLE/BT includes a 30 cm 3-lead cable | ≥ 54 mm | ✅ (see note below) |
| W12 | 523450 → Board PWR | 118 mm | Own lead, typically 50–80 mm | Taobao equivalents | Possibly too short | ⚠ Check on arrival. If it is under 12 cm, extend it with a "PH2mm straight-pin pre-wired" lead, or simply use the 700 mAh battery supplied with the Board kit |
| W13 | PulseSensor → A3 | 512 mm | 61 cm (24 in) | PulseSensor official | 98 mm | ✅ |
| W14 / W15 | Thermocouples TC1 / TC2 → plug pouch | 592 / 597 mm | Surface thermocouples are typically 1 m | Taobao equivalents | ≈ 400 mm | ⚠ Check on arrival: a 0.5 m version is too short; swap for a 1 m one |

### What changed in this round of checks

1. **C-set leads**
   - The previous harness model placed the 3-lead cable's split point 30 mm above the cable hole, with the REF lead going up first and then folding back, giving 291 mm (only 9 mm slack on a 30 cm cable).
   - The three wires of the PLUX 3-lead cable actually **separate right at the plug**, so the split point was moved to the skin side of the cable hole.
   - Recalculated, the longest is 246 mm, with 54 mm slack. The electrode positions do not need to move.
2. **W06**: changed from 0.6 m to 0.7 m.
3. **Reference electrodes**: moved from the iliac crest to the lower ribs; the wiring table and wiring diagram have been updated accordingly. Reason: the iliac crest is more than 30 cm from the sensor, so the leads cannot reach.

---

## 3. The 3 cables that only need a glance on arrival (no measuring — check the product label or by eye)

| Cable | What to check | If it falls short |
|---|---|---|
| Board kit 3-lead cable | 30 cm or 10 cm (easy to tell by eye) | If 10 cm, buy PLUX SKU 810121413 (30 cm) |
| 523450 battery lead | At least 12 cm | Extend with a PH2 pre-wired lead, or switch to the 700 mAh battery supplied with the kit |
| Type-K thermocouple | At least 0.7 m | Swap for a 1 m version |

---

## 4. Sources

- PLUX: BITalino (r)evolution Board Kit BLE/BT product page; accessories include a 30 cm 3-lead cable, a 10 cm 2-lead cable and a 700 mAh LiPo — https://pluxbiosignals.com/products/bitalino-revolution-board-kit-ble-bt
- PLUX: 3-Lead Electrode Cable, available in 10 cm ± 0.5 cm and 30 cm ± 0.5 cm (SKU 810121411 / 810121413) — https://www.pluxbiosignals.com/products/3-lead-electrode-cable
- PLUX: BITalino (r)evolution Plugged Kit 2016 datasheet; the kit includes a 3-lead cable, a 2-lead cable and a UC-E6-to-UC-E6 sensor cable — https://cdn.robotshop.com/media/p/plu/rb-plu-103/pdf/classbit-sciences-teaching-kit-datasheet.pdf
- HeartBIT kit: ECG sensor leads 30 cm; one 10 cm and one 30 cm UC-E6 sensor cable (checked against the kit documentation in the previous round)
- Panel lead: the photos you sent (13-inch MacBook Air as scale reference)
