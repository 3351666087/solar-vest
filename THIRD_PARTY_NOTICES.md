# Third-party notices

## 3D models

All three Thingiverse licences below were checked on their pages on 2026-10-21.

| Item | Source | License | Where used here |
|---|---|---|---|
| "BITalino (r)evolution Plugged Casing" by BEE Very Creative, published by BITalinoWorld: `1_Plugged_Bot_4.0.stl`, `1_Plugged_Bot_v1.0_offset_0375.stl`, `2_Plugged_Top_v1.2.stl` | https://www.thingiverse.com/thing:2286560 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Verbatim in `modeling/bitalino-case_thingiverse-2286560/`. Adapted (positioned, merged with the traced Core, mesh-compressed) in `modeling/heartbit-kit-models/*.glb`, `modeling/component-model-viewer.html`, `tools/cad/SolarVest_Explorer_src/models/heartbit.mo.glb` and the built explorer (`models-boards.js`) |
| "BITalino Electrocardiography (ECG) Sensor Housing" by BEE Very Creative, published by BITalinoWorld: `ecg_sensor_bot.stl`, `ecg_top.stl` | https://www.thingiverse.com/thing:2286812 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Verbatim in `modeling/heartbit-kit-models/official-stl/`. Adapted (the two halves joined and positioned on the body) in `modeling/heartbit-kit-models/ecg_sensor.glb`, `heartbit_kit_all.glb`, `modeling/component-model-viewer.html`, every assembly GLB in `viewer/`, `tools/cad/SolarVest_Explorer_src/models/assembly.mo.glb` and the built explorer (`models-core.js`) |
| "PulseSensor Housing" by BITalinoWorld: `PulseSensor_Housing.stl`, `.scad` | https://www.thingiverse.com/thing:2286840 | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | `modeling/heartbit-kit-models/official-stl/` and the derived HeartBIT / assembly models |
| Seeed Studio XIAO nRF52840 STEP | Seeed Studio wiki | Vendor download; **not** included | `research/toolchain-samples/parametric-models/parts.py` expects it as `xiao/*.step` (relative to the working directory) |
| Component 3D models on the PCBs | KiCad 10 standard libraries, plus this project's own build123d models (`hw.3dshapes`) | KiCad libraries: CC BY-SA 4.0 with the KiCad design exception | Embedded in the board STEP/GLB exports under `hardware/pcb/` |

Changes made to the CC BY works: they were positioned in the project's body / enclosure frames, merged with other parts, re-meshed or mesh-compressed for the web viewers. The original designers do not endorse this project.

## Documentation and figures

The BITalino dimensions used in this project come from PLUX's *BITalino (r)evolution User Manual* (Fig. 8 Core 65 × 56 mm, Fig. 9 Board 65 × 108 mm) and data sheets. They are cited, not redistributed:

- User manual: https://support.pluxbiosignals.com/wp-content/uploads/2021/11/bitalino-revolution-user-manual.pdf
- Board Kit data sheet: https://support.pluxbiosignals.com/wp-content/uploads/2021/11/revolution-bitalino-board-kit-datasheet.pdf
- HeartBIT: https://www.pluxbiosignals.com/products/heartbit

## Software bundled in the web viewers

`explorer/app.js` and `viewer/viewer.bundle.js` include three.js, three-mesh-bvh and the meshopt decoder. All three are MIT-licensed; the full texts are in the `THIRD_PARTY_LICENSES.txt` file next to each viewer.

## Tools

KiCad, SKiDL, build123d (OpenCascade), trimesh, manifold3d, ngspice, esbuild, glTF-Transform and openhtmltopdf are used as tools. None of their source code is redistributed here.

## SolarBand wristband (`wristband/`)

| Item | Source | License / terms | Where used here |
|---|---|---|---|
| Component footprints and symbols, one per LCSC part number | EasyEDA / LCSC public component library, converted to KiCad format with the open-source tool easyeda2kicad (the tool is not included) | Terms of the EasyEDA / LCSC library; no separate open license is stated by the library | Raw conversions in `wristband/design/lib/easyeda.pretty` and `easyeda.kicad_sym`; reviewed copies (paste, courtyard, holes and fields fixed by `design/tools/review_footprints.py`, copper unchanged) in `easyeda_rev.pretty` and in the routing bundle; placed on the board in `wristband/board/` and `wristband/package/final/board/` |
| EasyEDA 3D models (`easyeda.3dshapes`) | EasyEDA / LCSC | **Not** included; the footprints still name them, so KiCad shows no body for those parts | Board STEP exports in `wristband/cad/img/` embed the bodies that were available when they were exported |
| Part fields (stock, price, package, description) | JLCPCB public parts search, read 2026-11-13 to 11-16 | Facts quoted for the BOM; the raw API answers are not included | `wristband/design/parts.json`, `stock_report.md`, `wristband/package/final/assembly/stock_today.*` |
| Data-sheet figures | Manufacturers' data sheets (TI, Sharp, C&K, Vybronics and others), cited by document number, page and figure in the reports | Cited, not redistributed (no data-sheet PDFs or page texts are included) | Reports in `wristband/docs`, `design`, `cad/sources.md`, `sim/`; digitised curve points in `wristband/sim/ecg/refs/curves.json` |
| IEC 60601-1, IEC 61000-4-2, ISO 22810 | Standards | Cited by clause structure only | Pass criteria in the reports |

KiCad 10 (kicad-cli, pcbnew Python module), SKiDL, build123d (OpenCascade), ngspice, numpy, scipy, shapely and matplotlib are used as tools by the wristband scripts. Freerouting was tried in early stages and is not bundled. None of their source code is redistributed here. The routing path-finder (`wristband/routing/**/pf.c`) and all other scripts in `wristband/` are this project's own code.
