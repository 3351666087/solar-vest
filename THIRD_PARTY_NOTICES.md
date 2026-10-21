# Third-party notices

## 3D models

All three Thingiverse licences below were checked on their pages on 2026-10-21.

| Item | Source | License | Where used here |
|---|---|---|---|
| "BITalino (r)evolution Plugged Casing" by BEE Very Creative, published by BITalinoWorld: `1_Plugged_Bot_4.0.stl`, `1_Plugged_Bot_v1.0_offset_0375.stl`, `2_Plugged_Top_v1.2.stl` | https://www.thingiverse.com/thing:2286560 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Verbatim in `建模教程/BITalino官方外壳_Thingiverse2286560/`. Adapted (positioned, merged with the traced Core, mesh-compressed) in `建模教程/HeartBIT套件模型/*.glb`, `建模教程/元件模型查看器.html`, `制造文件/源码/SolarVest_Explorer_src/models/heartbit.mo.glb` and the built explorer (`models-boards.js`) |
| "BITalino Electrocardiography (ECG) Sensor Housing" by BEE Very Creative, published by BITalinoWorld: `ecg_sensor_bot.stl`, `ecg_top.stl` | https://www.thingiverse.com/thing:2286812 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Verbatim in `建模教程/HeartBIT套件模型/官方STL/`. Adapted (the two halves joined and positioned on the body) in `建模教程/HeartBIT套件模型/ecg_sensor.glb`, `heartbit_kit_all.glb`, `建模教程/元件模型查看器.html`, every assembly GLB in `制造文件/查看器/`, `制造文件/源码/SolarVest_Explorer_src/models/assembly.mo.glb` and the built explorer (`models-core.js`) |
| "PulseSensor Housing" by BITalinoWorld: `PulseSensor_Housing.stl`, `.scad` | https://www.thingiverse.com/thing:2286840 | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | `建模教程/HeartBIT套件模型/官方STL/` and the derived HeartBIT / assembly models |
| Seeed Studio XIAO nRF52840 STEP | Seeed Studio wiki | Vendor download; **not** included | `3D与PCB调研_验证样例/参数化模型/parts.py` expects it in `官方模型/` |
| Component 3D models on the PCBs | KiCad 10 standard libraries, plus this project's own build123d models (`hw.3dshapes`) | KiCad libraries: CC BY-SA 4.0 with the KiCad design exception | Embedded in the board STEP/GLB exports under `制造文件/PCB/` |

Changes made to the CC BY works: they were positioned in the project's body / enclosure frames, merged with other parts, re-meshed or mesh-compressed for the web viewers. The original designers do not endorse this project.

## Documentation and figures

The BITalino dimensions used in this project come from PLUX's *BITalino (r)evolution User Manual* (Fig. 8 Core 65 × 56 mm, Fig. 9 Board 65 × 108 mm) and data sheets. They are cited, not redistributed:

- User manual: https://support.pluxbiosignals.com/wp-content/uploads/2021/11/bitalino-revolution-user-manual.pdf
- Board Kit data sheet: https://support.pluxbiosignals.com/wp-content/uploads/2021/11/revolution-bitalino-board-kit-datasheet.pdf
- HeartBIT: https://www.pluxbiosignals.com/products/heartbit

## Software bundled in the web viewers

`制造文件/SolarVest_Explorer/app.js` and `制造文件/查看器/viewer.bundle.js` include three.js, three-mesh-bvh and the meshopt decoder. All three are MIT-licensed; the full texts are in the `THIRD_PARTY_LICENSES.txt` file next to each viewer.

## Tools

KiCad, SKiDL, build123d (OpenCascade), trimesh, manifold3d, ngspice, esbuild, glTF-Transform and openhtmltopdf are used as tools. None of their source code is redistributed here.
