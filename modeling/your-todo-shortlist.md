# What you need to do: the shortest list

> **Date** 2026-10-08
> ✅ **All done as of 2026-10-08**: all photos received; the panel has no nameplate, so its electrical parameters are now derived from the cells instead. Results are in [../docs/v3.1-change-list.md](../docs/v3.1-change-list.md). **There is currently nothing you need to measure.**
>
> Original conclusion: no calipers, just 4 photos, with a 5th recommended.

## Rules

1. **Only collect data that I cannot get from any public source and that affects the design.** Anything available from official documents, part numbers or datasheets, you will never be asked to measure.
2. **You don't need to review the models once built.** When designing enclosures, cut-outs and the back plate, I leave at least 1 mm of clearance throughout; the modelling error (±1 mm) falls within that clearance and does not affect assembly.
3. **Photos instead of calipers.** Lay the item flat next to a **bank card** and photograph them together. A bank card has an international standard size of 85.60 × 53.98 mm; I detect it automatically and convert to the item's dimensions, with approx. ±1 mm accuracy, which is good enough.

## Photos to take

| # | What to photograph | Why it is essential | How to shoot it |
|---|---|---|---|
| 1 | **Nameplate on the back of the 6 V 6 W panel** | The fuse, TVS diode and MPPT set point all need P<sub>max</sub>, V<sub>mp</sub>, I<sub>mp</sub>, V<sub>oc</sub>, I<sub>sc</sub>; there is no other source | Straight on to the nameplate; the text just needs to be legible |
| 2 | **Panel front + bank card** | Back-plate and vest dimensions, mounting-hole positions | Lay the panel flat on the floor with the bank card against its edge on the same floor; hold the phone directly above the panel, use the 2× lens, and get the whole panel and card in frame |
| 3 | **Panel side + bank card** | Thickness and junction-box height, which set the standoff height | Lay the panel on its side or stand it up, put the bank card next to it, and shoot level from the side |
| 4 | **1 supercapacitor + bank card**, with the text on the sleeve legible | The part number printed on the sleeve leads to the datasheet; if it can't be found, the dimensions from the photo are used | Lay flat, shoot from above |
| 5 (strongly recommended) | **Open the red HeartBIT case and photograph the front of the Core board** | Tells at a glance whether it is **Bluetooth Classic (BT) or Bluetooth Low Energy (BLE)**: a long green module is BT, a small blue square is BLE. **This decides whether the phone app can run on an iPhone**: iPhone does not allow ordinary apps to use the Bluetooth Classic serial port, so the BT version is Android-only | The top cover is snap-fit; pry it open gently |

Just drag the photos into the chat to send them to me.

## What you don't need to do, and why

| Item | Where the data comes from |
|---|---|
| HeartBIT main unit (Core + case) | The case is the official STL, the same one printed "3DP by BEEVERYCREATIVE" in PLUX's product photo; the Core is modelled by tracing the official manual and test-fitted in the case with 0.1–0.7 mm clearance |
| HeartBIT ECG sensor, PulseSensor | Official housing STLs, plus PulseSensor official dimensions |
| Electrodes, HeartBIT 700 mAh battery | PLUX official specifications; battery model number confirmation requested from PLUX by email |
| XIAO nRF52840 Sense | Seeed official STEP |
| 523450 battery | The model number is the size: 5.2 × 34 × 50 mm |
| 2500 mAh battery, vest or chest strap | Not bought yet; when buying, I will choose models with a dimension table |
| EVK10941 | e-peas official documentation gives 76 × 50 mm, and it is only used in the low-light comparison branch |
| CN3791 module, INA226 module | No longer used now that JLCPCB assembles the chips directly |
| Your body | Scan data already exists |

## About "modelling from a picture"

**Yes, it works, with one condition: the photo must contain an object of known size, in the same plane as the object being measured and in the same shot.** When that holds, accuracy is roughly ±1 mm. That is how the BITalino Core was modelled, and when it was later test-fitted into the official case, the clearance on the long side was only 0.1 mm.

**The HeartBIT "family photo" on the PLUX website cannot be used for measurement.** Using the case as the scale reference, I measured a few other items of known size:

| Item | True size | Measured from the image | Error |
|---|---|---|---|
| USB-A metal plug width | 12.0 mm | 10 mm | −17% |
| PulseSensor diameter | 15.9 mm | 14.1 mm | −11% |

This shows it is a composite promotional image in which each item is scaled separately. So the image is used only to recognise shapes and confirm which case it is; all dimensions come from official data. That is also why photos 2–4 need to be **taken by you, with a bank card in the frame**.
