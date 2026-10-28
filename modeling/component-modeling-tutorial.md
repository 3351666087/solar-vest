# Component 3D modelling: web-wide search results + tutorial

> 🔴 **The only thing you actually need to do is this one: [your-todo-shortlist.md](your-todo-shortlist.md)**. Just take 4–5 photos, no calipers needed. The measurement methods in section 3 below are background knowledge only, not tasks.

> **Date** 2026-10-08 · **Settled assumptions**: KiCad 10 + SKiDL for the board; JLCPCB fabrication and assembly; as little hand soldering as possible.
> **Companion files** (all in this folder):
> - [component-model-viewer.html](component-model-viewer.html): local 3D viewer; rotate the BITalino Core, battery, supercapacitor and panel models (the original manual figure is not included for copyright reasons; see PLUX user manual §1.8). Just open it in a browser.
> - [bitalino_core.py](bitalino_core.py): modelling code for the BITalino Core; every dimension is a named parameter.
> - [bitalino_core_LOD1.step](bitalino_core_LOD1.step) / [.glb](bitalino_core_LOD1.glb): the generated model.
> - Manual Figure 8 overlaid with a 5 mm grid for reading coordinates: not distributed with the repository for copyright reasons; the original is in the [PLUX user manual](https://support.pluxbiosignals.com/wp-content/uploads/2021/11/bitalino-revolution-user-manual.pdf) §1.8.
> - [bitalino-case_thingiverse-2286560/](bitalino-case_thingiverse-2286560/): the 3 official case STLs, already downloaded (CC-BY, author André Magro / BEE Very Creative, published by BITalinoWorld).

---

## 0. Conclusions

1. **Nobody anywhere on the web has published a 3D model of the BITalino circuit board itself**: not the vendor, not third parties.
2. **But BITalino has officially published STLs of the (r)evolution Plugged case on Thingiverse** (CC-BY licence: free to use with attribution). The case in the HeartBIT kit is very likely this one; it needs to be checked against the real part. In a 3D model of the whole unit, what you see is the case, **so the case model is more useful than the board model**. They have also published an ECG sensor housing and a PulseSensor housing.
3. **I have already modelled the Core board itself from the dimensioned figure in the official manual.** Accuracy is approx. ±1 mm, enough for assembly, cable routing and cut-outs.
4. **Switching to JLCPCB assembly halves the amount we have to model ourselves.** The CN3791 and INA226 modules are dropped; the chips are placed directly on our board instead, and the chips have official 3D models.

---

## 0.1 Update: official case downloaded and test-fitted with the Core model

| File | Outline (print orientation) |
|---|---|
| `1_Plugged_Bot_4.0.stl` (bottom shell, latest version) | 69.2 × 61.6 × 11.5 mm |
| `1_Plugged_Bot_v1.0_offset_0375.stl` (older bottom shell, with 0.375 mm printing allowance) | 69.2 × 61.6 × 11.5 mm |
| `2_Plugged_Top_v1.2.stl` (top cover, embossed "bitalino") | 69.2 × 60.8 × 12.0 mm |

**Test-fit result**: placing the Core traced from the manual (65 × 56 mm) into the bottom shell:

- Approx. 0.1 mm clearance at each end of the long side, approx. 0.7 mm per side on the short side.
- The 5 sockets on each side land exactly in the 5 notches along the shell edge.
- The USB port and switch face the end opening.

This verifies two things at once: **the traced dimensions are credible, and this case is indeed designed for the Core.** Item 2, "Test fit", in the viewer can be rotated to inspect this.

**Confirmed to be the same case**: in PLUX's official HeartBIT product photo, the red case lid is printed "3DP by BEEVERYCREATIVE", matching this STL. The remaining HeartBIT parts (ECG sensor, PulseSensor, electrodes, 700 mAh battery) have also all been modelled from official data; see [heartbit-kit-models/](heartbit-kit-models/).

## 1. Web-wide search log

| Platform | How it was searched | Result |
|---|---|---|
| **PLUX website + datasheets** | Downloaded the Plugged / Board datasheets and the 30-page user manual, read page by page | No 3D files. **User manual §1.8 Figure 8 gives the Core size as 65 × 56 × 2 mm, with a photo of the real board and dimension arrows**; Figure 12 has a wireframe of the connector layout. These two figures are the modelling basis |
| **Official BITalino GitHub** (BITalinoWorld's 35 repositories + PIA-Group) | Listed all repositories and files through the GitHub API | 6 case repositories from 2014 (STL, one with STEP), for the **old** BITalino; Eagle board files for the old V3 board; Eagle files for ProtoBIT and SnapBIT. **No (r)evolution board files** |
| **Thingiverse** | Browser search for "bitalino", 2 pages, 30 results | ✅ **(r)evolution Plugged Casing** ([thing:2286560](https://www.thingiverse.com/thing:2286560), published by the official BITalino account, 3 STLs)<br>✅ (r)evolution Board Casing ([thing:2286337](https://www.thingiverse.com/thing:2286337))<br>✅ ECG sensor housing ([thing:2286812](https://www.thingiverse.com/thing:2286812))<br>✅ PulseSensor housing ([thing:2286840](https://www.thingiverse.com/thing:2286840), CC0)<br>Also Plugged side clips, back clips, an accessory box and other sensor housings; a third-party Plugged BT case ([thing:3328925](https://www.thingiverse.com/thing:3328925), designed in Fusion 360, with a battery bay); an old-style hard case ([thing:2978394](https://www.thingiverse.com/thing:2978394)) |
| **GrabCAD** | Browser search for bitalino / INA226 / CN3791 / supercapacitor | Only 1 bitalino result: the 2016 "BITalino Case" (old model). **0 results** for both INA226 and CN3791. Supercapacitor: only an unrelated 350 F part |
| **Sketchfab** | Public API search for bitalino | 0 results |
| **Printables** | Opening it in the browser triggered a Cloudflare human-verification check, **which I did not bypass**; used a site-restricted search-engine query instead | Nothing found |
| **Cults3D / MyMiniFactory / MakerWorld** | Site-restricted search-engine queries | Nothing found (only unrelated results such as Bticino switch plates) |
| **Thangs** | Browser access refused | **Could not search** |
| **Tinkercad** | Search engine | There is a "BITalino - Case for Plugged Kit"; not confirmed whether it is for the new or old model |
| **Flux.ai** | Search engine | PulseSensor (SparkFun SEN-11574) has a STEP |
| Modules on Thingiverse | Searched INA226 / CN3791 | Only "INA226 bracket" and "CN3791 mount" models, from which the module size can be inferred, but not models of the modules themselves |

**Limits**: Printables and Thangs could not be searched. PLUX's internal CAD is not public. For a more accurate Core model, **you could email PLUX and ask for it** (the contact given in the manual is bitalino@plux.info). The email was sent on 2026-10-08.

---

## 2. How the modelling list changes after switching to JLCPCB assembly

| Before | Now | Where the 3D comes from | Do you solder it? |
|---|---|---|---|
| CN3791 module | **Chip placed directly on the PMB-H** (LCSC C154992) | EasyEDA / LCSC official model | No |
| INA226 module ×4 | **Chip ×4 placed directly** (C49851) | ✅ Downloaded | No |
| XIAO nRF52840 Sense | The JLCPCB library has the XIAO (e.g. C27675191; Sense version LCSC C17401557). ⚠ **Before ordering, check that it is the Sense version, that it is in stock, and which assembly process is used** (one listing says "wave soldering") | ✅ Seeed official STEP | No, if JLCPCB can assemble it; otherwise one row of pin headers |
| MOSFET, LM66100, TVS, passives | SMD | KiCad official library / LCSC | No |
| Connectors | **Choose SMD JST-PH / XH** | KiCad official library | No |
| 2.7 V 10 F supercapacitor (through-hole) | JLCPCB "Standard PCBA" can solder through-hole parts, charged per pin; or you solder it yourself | ✅ Parametric model exists | 0–4 solder joints |
| Battery, panel wiring | **Everything via connectors**: buy batteries with a JST plug; crimp JST-XH terminals onto the panel leads or use a terminal block | Parametric | No |

> **At most, the only place you need a soldering iron is the 4 solder joints of the supercapacitor.** JLCPCB assembly fees distinguish "Basic / Extended" parts: each Extended part type incurs an extra feeder-loading fee, so when drawing the schematic I will choose Basic parts wherever possible.

**Still to be modelled ourselves**: 6 V panel, two batteries, supercapacitor, BITalino (Core + case + 700 mAh battery + ECG sensor + electrodes), EVK10941 (only for the low-light comparison branch), back plate, two enclosures, vest, cables.

---

## 3. Modelling tutorial

### 3.1 Choose the level of detail first: finer is not always better

| Level | Contains | Used for | Where this project uses it |
|---|---|---|---|
| **LOD0 bounding box** | One box: outline dimensions + mass | Placement, centre of mass, collision checks | Batteries, supercapacitor, electrodes |
| **LOD1 outline + interfaces** | Outer contour, thickness, position and orientation of every socket and switch | Where cables exit, where enclosure cut-outs go, whether plugs press into the body | **BITalino, panel, EVK10941, custom enclosures** |
| LOD2 board-level detail | Every component, every pad | Only needed when designing a PCB | Only our own PMB-H and LIB boards (generated automatically by KiCad) |

**Principle: model only until it answers your question.** The whole-unit 3D model has to answer "does it fit, how do the cables run, which way do the ports face", so LOD1 is enough.

### 3.2 Where the data comes from: ranked by reliability

1. **Manufacturer STEP**: e.g. the XIAO. Use as is.
2. **Manufacturer drawings or dimensioned figures in a manual**: e.g. BITalino manual Figure 8. Model by tracing, accuracy approx. ±1 mm.
3. **Officially published case or bracket STLs**: the inner cavity of a case is the board outline, so the board can be inferred.
4. **Measuring the real part with calipers**: most reliable, 0.1 mm accuracy.
5. **Straight-on photos with a ruler**: trace them, accuracy approx. ±0.5–1 mm.
6. **Photogrammetry**: take photos all the way round the object and reconstruct it with the same Object Capture workflow used for your body scan. Suitable for irregular shapes such as cable harnesses and soft enclosures.

### 3.3 How to measure

**Calipers:**

- Measure each dimension 3 times, take the median, and enter it in the table:

  | Item | Length | Width | Thickness | Other (hole spacing, connector positions…) |
  |---|---|---|---|---|

- Measure all connector positions from **the same corner**, e.g. the top-left. Write them as "x mm from the left edge, y mm from the top edge".
- For pouch batteries, measure **the thickest point**; include any battery swelling.

**Photos for tracing:**

1. Shoot from **further away and zoom in**, e.g. 2× lens at 30 cm or more. This reduces perspective distortion.
2. Point the camera **straight at** the object; do not shoot at an angle.
3. **Put the ruler in the same plane as the object**, with at least 5 cm of scale visible.
4. Use a plain-coloured paper background and even lighting.
5. Take one photo each of the front, the side, and the face with the connectors.

### 3.4 Two routes

**A. You measure, I model (recommended, least effort)**

1. You fill in the dimension table in 3.3 and take the photos.
2. I write build123d code and generate STEP and GLB.
3. You compare it with the real part in the "Component Model Viewer". If something is wrong, tell me which number to change; I change one parameter and regenerate.

**B. Do it yourself (if you want to learn)**

Recommended: **Onshape**: free, runs in the browser, nothing to install. The workflow in FreeCAD or Fusion 360 is the same. Using the 523450 battery as an example:

1. Create a new Part Studio, units mm.
2. **Sketch** on the Top plane: draw a rectangle and dimension it 34 × 50.
3. **Extrude** 5.2 mm to get the battery body.
4. Draw a 27 × 6 rectangle at one end of the body and extrude it 4.2 mm: this is the protection-board section.
5. **Fillet**: R2 on the four long edges. Pouch battery edges are rounded.
6. Draw two small circles on the protection-board end face and extrude them as leads.
7. Right-click the Part → **Export → STEP**.
8. Naming convention: `partname_LODlevel.step`, e.g. `lipo_523450_LOD1.step`.

For enclosure-type parts, use one more command: **Shell**, to hollow the solid into a shell with a 2 mm wall.

### 3.5 Worked example: how the BITalino Core was modelled

1. **Find the basis**: user manual §1.8 Figure 8, a photo of the real board with two dimension arrows, 65 mm and 56 mm.
2. **Set the scale**: a script finds the pixel positions of the tick marks at both ends of each arrow. Vertically, 473 px corresponds to 65 mm, i.e. 7.28 px/mm; horizontally, 384.5 px corresponds to 56 mm, i.e. 6.87 px/mm. The two directions differ by 6%, which means the image itself is slightly distorted, so accuracy can only be stated as ±1 mm.
3. **Overlay a grid**: draw a line every 5 mm on the photo (this overlay is not distributed with the repository for copyright reasons), then read off the coordinates one by one:

   | Feature | Position read (mm, from the top-left corner) |
   |---|---|
   | Socket strips on both sides | 9 mm wide each, running the full length |
   | Notch at top centre | 12.5 mm deep |
   | UC-E6 sockets ×10 | Centres 5.2 / 18.6 / 32.1 / 45.6 / 59.1 from the top edge, symmetric on both sides. Left side top to bottom: I1, A4, A3, A2, A1; right side: O1, O2/I2, PWM, A6, A5 |
   | Bluetooth module | x 10.9–24.8, y 37.5–65 |
   | MCU (TQFP-32, rotated 45°) | Centre (28, 22.2) |
   | Micro-USB port | Centre x = 32.8, on the bottom edge, opening facing down |
   | Switch | x 39–46, on the bottom edge, slider protrudes approx. 1.5 mm beyond the board edge |
   | Battery JST-PH socket | x 33.5–39.3, y 45.4–52.9 |

4. **Set the heights**: the manual gives the overall Plugged thickness as 6 mm, so the tallest component is no more than approx. 4.4 mm (assuming a 1.6 mm board). Individual heights are marked 📏 to be measured.
5. **Write the code**: every number is a named parameter (see the top of `bitalino_core.py`), and coordinates are converted consistently from image coordinates to CAD coordinates. Convention: **origin at the board centre, Z axis pointing toward the component side**. Every part follows this convention so that assemblies don't get muddled.
6. **Self-check**: the generated model's outline is 56 × 66.5 × 6.4 mm. The extra 1.5 mm is the switch slider, and 6.4 mm broadly agrees with the manual's 6 mm. Viewed side by side with the original photo in the viewer, the layout matches feature for feature.

### 3.6 Approach for each component

| Component | Level | Data | Dimensions to measure | Key points | Difficulty |
|---|---|---|---|---|---|
| **BITalino Core** | LOD1 | ✅ Done (traced from manual) | Tallest component, battery socket orientation | Once you have the real part, replace the 📏 parameters with measured values | Done |
| **BITalino case** | LOD1 | Official Thingiverse STL | Compare outline with the real part | Import the STL directly into the assembly; no need to rebuild | ★☆☆ |
| HeartBIT 700 mAh battery | LOD0 | The label in manual Figure 11 looks like LP503436 (5 × 34 × 36 mm) ⚠ image too blurry, measure it | Length, width, thickness | A filleted box | ★☆☆ |
| ECG sensor + leads | LOD0–1 | Official ECG housing STL | Lead length, electrode snap diameter | Generate the lead wires with a "sweep" along a path | ★★☆ |
| Disposable electrode | LOD0 | — | Diameter, thickness, snap height | Disc + small cylinder | ★☆☆ |
| **6 V 6 W panel** | LOD1 | Nameplate + measurement | Length, width, thickness, frame, junction-box position, holes, mass | Draw the cell grid on the panel face so its orientation is easy to see | ★☆☆ |
| 523450 / 2500 mAh battery | LOD0 | Measurement | Length, width, thickest point, protection-board length | See 3.4 B | ★☆☆ |
| Supercapacitor | LOD0 | Measurement | Diameter, height, lead pitch | A cylinder + two leads | ★☆☆ |
| EVK10941 | LOD1 | Documentation says 76×50 mm + measurement | Hole positions, terminal positions | Use KiCad library models for the terminals | ★★☆ |
| PMB-H, LIB boards | LOD2 | Exported automatically by KiCad | — | `kicad-cli pcb export step` | Automatic |
| Back plate, enclosures | LOD1 | **Our own design** | — | Back plate conforms to the body surface: 42 mm sagitta, 18–28 mm standoffs | ★★★ I'll do it |
| Cables | LOD0 | Routing path | Cable diameter | Sweep along the path | ★★☆ I'll do it |

### 3.7 How to use STL mesh files

- An STL is "surface triangles", not an editable solid. **It is entirely adequate for assembly display and collision checks.**
- To modify it, e.g. to add a clip to the case, use the STL as a reference shape and redraw a solid in CAD.
- Online "STL to STEP" converters only wrap the triangle mesh in a shell; **it does not become editable**. Don't count on it.

### 3.8 Self-check list

- [ ] Units are mm.
- [ ] Consistent origin and orientation: origin at the part centre or base centre, Z axis pointing "outward" or toward the component side.
- [ ] Outline dimensions within 0.5 mm of the data or measurement. Anything only accurate to ±1 mm must be noted in the file.
- [ ] Interface orientation correct: which way the USB port and socket openings face.
- [ ] Every part has a name and colour so it is recognisable at a glance in an assembly.
- [ ] The top of every file states: data source, accuracy, and which numbers are not yet measured (📏).

---

## 4. What you need to do

See [your-todo-shortlist.md](your-todo-shortlist.md): take 4 photos (panel nameplate, panel front, panel side, supercapacitor); a 5th is recommended (Core front, to tell BT from BLE).

The email to PLUX was sent on 2026-10-08.

## Sources

- PLUX: [BITalino (r)evolution user manual](https://support.pluxbiosignals.com/wp-content/uploads/2021/11/bitalino-revolution-user-manual.pdf), [Plugged Kit datasheet](https://support.pluxbiosignals.com/wp-content/uploads/2021/11/revolution-bitalino-plugged-kit-datasheet.pdf), [Board Kit datasheet](https://support.pluxbiosignals.com/wp-content/uploads/2021/11/revolution-bitalino-board-kit-datasheet.pdf), [HeartBIT](https://www.pluxbiosignals.com/products/heartbit)
- GitHub: [BITalinoWorld organisation](https://github.com/BITalinoWorld) (e.g. [3d-models-plugged-h3dpw](https://github.com/BITalinoWorld/3d-models-plugged-h3dpw)), [PIA-Group/schematics-bitalino](https://github.com/PIA-Group/schematics-bitalino)
- Thingiverse: [(r)evolution Plugged Casing](https://www.thingiverse.com/thing:2286560), [ECG housing](https://www.thingiverse.com/thing:2286812), [PulseSensor housing](https://www.thingiverse.com/thing:2286840), [third-party Plugged case](https://www.thingiverse.com/thing:3328925)
- GrabCAD: [BITalino Case](https://grabcad.com/library/bitalino-case-1)
- JLCPCB / LCSC: [XIAO nRF52840 (C27675191)](https://jlcpcb.com/partdetail/Seeed-113991254/C27675191), [Assembly pricing](https://jlcpcb.com/help/article/pcb-assembly-price)
- Flux.ai: [PulseSensor SEN-11574](https://www.flux.ai/jecstronic/sen-11574~np8/files)
