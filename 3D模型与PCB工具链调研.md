# 3D 模型来源与 PCB 命令行工具链调研

> **日期** 2026-10-08 · **依据** 到货清单（CSV）+ 架构 v3（6 V / 6 W 刚性板）
> **标记** ✅ = 我在本机实际下载或运行过；🔎 = 只查到资料，没有实测；📏 = 需要你用卡尺或铭牌给一个尺寸

---

## 0. 结论

| 问题 | 结论 |
|---|---|
| 哪些能在网上直接找到 3D 模型？ | **所有芯片和连接器都能找到**，例如 CN3791、INA226、LM66100、LM74700、AO3401、YJL3404A、SS34、JST-PH/XH。**XIAO nRF52840 Sense 有 Seeed 官方 STEP** ✅。AEM10941 芯片有厂家 CAD ✅ |
| 哪些只能自己建？ | **所有"模块板"和"整件"都没有可靠的官方模型**：面板、电池、超级电容、CN3791 模块、INA226 模块、EVK10941、BITalino 和它的外壳、电极，以及背板、外壳、背心。它们形状简单，**给尺寸就能用代码建**，我已经在本机验证过这条路 ✅ |
| PCB 能不能用命令行平台开发？ | **能。** 推荐 **KiCad 10 + 代码描述电路 + Freerouting 自动布线 + kicad-cli 出全部文件**。除了"装 KiCad"和"把文件送去制板"这两步，其余都可以由我用命令行完成 |
| PCB 的 3D 能不能搞到？ | **能，而且是自动的。** `kicad-cli pcb export step/glb` 会把板子和板上所有器件的 3D 一起导出，器件模型来自上面两类 |

**需要你做的 4 件事**（第 9 节有细节）：

1. 装一次 KiCad 10（沙箱拦住了 brew，需要你在终端里跑）。
2. 告诉我实验室制板机的型号。
3. 用卡尺量几样东西（第 2 节列了清单）。
4. 选一条 PCB 工具链。

---

## 1. 逐件清单：3D 模型从哪来

### 1.1 已到货

| 物料 | 在系统里的作用 | 3D 来源 | 状态 |
|---|---|---|---|
| **6 V / 6 W 刚性太阳能板** | 主能源（背部） | 没有通用模型；外形差别大，必须按实物建 | 📏 铭牌和外形尺寸、厚度、接线盒位置、重量。参考：Voltaic/Adafruit 的 6 W 板是 220×175×5 mm、225 g |
| 395×460 mm 18 V 30 W 板 | 不采用（台架备用） | 不建 | — |
| **EVK10941**（AEM10941 评估板） | 低光对比支线 | 板子没有 3D；**AEM10941 芯片有厂家 CAD**（Altium 库 + Eagle 库 + 原理图片段）✅ 已下载。评估板尺寸 76×50 mm（e-peas/Mouser 资料），螺钉端子用 KiCad 官方库 | 可半自动建：板框 + 端子 + 芯片 |
| **523450 1000 mAh 锂电池** | 主储能 | 软包电池没有官方模型 | ✅ 已用代码建出（5.2×34×50 mm + 保护板），📏 量实物确认 |
| **YJL3404A** | **已确认是 N 沟道 MOSFET**：30 V、5.6 A、SOT-23（扬杰）。正好用作 P-MOS 栅极的电平转换管 | KiCad 官方 SOT-23 模型；LCSC 有同系列 YJL3404AQ（C2942683） | 🔎 |
| **2.7 V 10 F 超级电容 ×3** | 胸口单元掉电保持 | 径向电解电容外形，常见 10×30 或 12.5×20 mm | ✅ 已用代码建出，📏 量直径、高度、引脚距 |
| **BITalino ×2 + HeartBIT 套件** | 心电采集 / 参考仪器 | **官方没有 (r)evolution 的 3D**。PLUX 只给外形：(r)evolution Plugged 约 100×65×6 mm，3D 打印外壳 111×69×18 mm。**老版 BITalino V3 的 Eagle 板图和原理图是开源的** ✅（PIA-Group/schematics-bitalino），KiCad 能导入，但它不是你手上的 (r)evolution | **更新（同日）**：BITalino 官方在 Thingiverse 发布了 (r)evolution Plugged 外壳 STL；Core 板我已按手册图 8 建好 LOD1 模型。详见 [建模教程/元件建模教程.md](建模教程/元件建模教程.md) |
| HeartBIT 里的 ECG 传感器、PulseSensor、700 mAh 电池 | 套件自带 | 简单几何体 | 📏 |
| 一次性心电电极 | 贴胸前 | 圆片 + 按扣 | 📏 直径 |
| **TEUCER HP600 散热硅胶垫** | 面板与电子件之间的热界面（不能放在面板和皮肤之间） | 一张薄片 | 📏 厚度 |
| K 型表面热电偶 ×2 | 热安全测试 | 小探头，可简化成小方块 | 可选 |
| PH2.0 线、杜邦线、热缩管等耗材 | 接线 | 线缆按走线路径扫掠生成 | 不需要 |
| 焊台、万用表、测温仪、剥线钳、USB 检测仪、面包板、板材钳 | 工具 | 不进入整机模型 | 不需要 |

### 1.2 待采购（v3 §7）

| 物料 | 3D 来源 | 状态 |
|---|---|---|
| **XIAO nRF52840 Sense ×3** | **Seeed 官方 STEP** ✅ 已下载（8.8 MB 压缩包，`XIAO-nRF52840 v15.step`）。KiCad 符号和封装在 Seeed 官方 GitHub 库 ✅。⚠ 官方 STEP 是 Y 轴朝上，装配时要转 90°，我已在样例里处理 | 直接用 |
| **CN3791「6 V 版」模块 ×3** | 模块没有可靠模型。**CN3791 芯片**（LCSC C154992，SSOP-10）EasyEDA 有 3D | 板框按实测、芯片用真模型，📏 量模块。网上 9 V 版是 45×20×9.5 mm，6 V 版可能不同 |
| **INA226 模块 ×4** | 模块没有可靠模型。**INA226 芯片**（LCSC C49851）✅ 已下载 STEP | 同上，📏 |
| 1S 2500 mAh 锂电池 | 按型号尺寸建 | 📏 买到后量 |
| AO3401 / AO3400 | KiCad 官方 SOT-23；LCSC C15127 等 | 🔎 |
| LM66100（电池侧） | LCSC C2869734，SC-70-6 | 🔎 |
| SS34、SMAJ8.5A | KiCad 官方 SMA 封装 | 🔎 |
| LM74700 + N-MOS（Rev B） | LCSC C2941042，SOT-23-6 | 🔎 |
| PPTC / 保险丝、NTC | KiCad 官方库 | 🔎 |
| JST-XH / JST-PH 连接器 | KiCad 官方库；JST-XH 2P（LCSC C158012）✅ 已下载 | 直接用 |
| 参考电池片 ×2 | 小片，按尺寸建 | 📏 |
| 磁吸连接器（J6 防拉脱） | 选定型号后找厂家 CAD，大厂一般会提供 STEP | 型号未定 |
| ADS1292R / MAX86150 评估板 | 🔎 没查到可下载的 3D（TI/ADI 一般只给原理图和 Gerber）；按用户手册尺寸建包络 | 📏 |
| 背心、背板、支撑脚、两个外壳 | **自制件，必须自己设计**。可以把你的身体扫描当人台来贴合曲面（上次测得面板弓高 42 mm、支撑 18–28 mm） | 由我用代码建 |

### 1.3 已经替你实测的

| 验证项 | 结果 |
|---|---|
| Seeed 官方 XIAO STEP 下载 | ✅ 成功，已导入装配 |
| `easyeda2kicad` 按 LCSC 料号拉模型 | ✅ INA226（C49851）和 JST-XH（C158012）成功。其余料号的下载被沙箱网络截断（IncompleteRead），后来又被接口限流（403）。**工具本身是通的**，在你自己电脑上跑不会有这个问题 |
| e-peas AEM10941 CAD 包 | ✅ 下载成功：Altium 集成库、PcbLib、Eagle 库、原理图片段、BOM |
| 用代码建参数化模型 | ✅ 用 build123d 0.13 生成了电池、超容、面板、两种模块的 STEP |
| 官方模型和自建模型拼成装配体 | ✅ 「面板 + 电池 + CN3791 模块 + XIAO」装配体导出成 STEP 和 GLB（GLB 能直接放进网页 3D 查看器） |

样例文件在 [3D与PCB调研_验证样例/](3D与PCB调研_验证样例/)。`参数化模型/parts.py` 里每个尺寸都是一个具名参数，量到实物后改一个数就行。

---

## 2. 要自己建模的东西：请量这些尺寸

| 物料 | 需要的尺寸 |
|---|---|
| 6 V 6 W 面板 | 长、宽、厚；有没有边框；接线盒的位置和尺寸；安装孔；重量 |
| 523450 电池（以及以后的 2500 mAh） | 长、宽、厚；保护板那一截的长度；引线出口位置 |
| 超级电容 | 直径、高度、引脚距 |
| CN3791 模块、INA226 模块 | 板长、宽；最高元件的高度；孔位和端子位置（拍一张俯视照片加一把尺子就够） |
| EVK10941 | 核对 76×50 mm，端子朝向 |
| BITalino（带外壳） | 外壳长、宽、高；接口开孔位置 |
| 电极、参考电池片、散热垫 | 直径 / 长宽、厚度 |

> 不确定的尺寸我会先用资料值，并在模型里标出来；量到实物后再替换。

---

## 3. 要做哪几块 PCB

按 v3 的分体式拓扑（ADR-007），共 2 块，外加 1 块可选的小板：

| 板子 | 位置 | 功能 | 复杂度 |
|---|---|---|---|
| **PMB-H** | 背部 | 面板输入保护（保险丝、TVS、二极管）→ CN3791 模块；双电池切换；4 路 INA226（地址 0x40 面板、0x41 电池、0x42 负载、0x44 参考电池片）；XIAO Sense；Q0 充电开关（默认导通，防止冷启动死锁）；NTC；J6 线缆口 | 中等。**Rev A 做成"模块载板"**：CN3791、INA226、XIAO 都用成品模块插上去，板上只有连接器、MOSFET 和少量阻容 |
| **LIB** | 胸口 | 超容保持、负载开关、同步脉冲注入 BITalino I1、ESD、JST-PH 到 BITalino | 简单，约 25×20 mm |
| REF（可选） | 面板边框 | 参考电池片的取样电阻和接线 | 极简，也可以直接并进 PMB-H |

全部是 2 层板、低速信号，最细的器件是 SOT-23 和 0603 阻容，**实验室制板机和嘉立创都能做**。

---

## 4. 命令行 PCB 工具链：调研结果

| 工具 | 做什么 | 能不能全命令行 | 本机实测 | 要注意的地方 |
|---|---|---|---|---|
| **KiCad 10**（2026-03-20 发布）+ `kicad-cli` | 行业标准开源 EDA | **出图能全部命令行**：ERC、DRC、Gerber、钻孔、坐标、BOM，以及 **STEP / GLB / STL / VRML 3D 导出**、光线追踪渲染、jobset 批处理 | ❌ 本机没装 | `kicad-cli` **没有**「从网表更新 PCB」，也**没有**「导出 DSN / 自动布线」。这两步要用 KiCad 自带的 Python 接口：SWIG 接口在 10 里还能用，11 里会删掉；新的 IPC 接口用 `kicad-python` 0.8 |
| **SKiDL** 2.3 | 用 Python 写电路，生成网表和初始 PCB | ✅ | 未实测 | 完全离线、不用账号；自动生成的原理图排版一般 |
| **atopile** 0.15.9 | 声明式电路语言，自动选料，编译成 KiCad PCB | ✅ `ato build` | ✅ **编译通过，生成了 `.kicad_pcb`**；但**自动选料要登录**（`ato auth login`），新版要迁到 app.atopile.io | 要注册账号，**我不能替你注册** |
| **tscircuit** | 用 TypeScript/React 写电路；**自带自动布线**；导出 Gerber、BOM、贴片坐标、GLB/STEP、KiCad 文件；能按 JLCPCB 料号导入器件 | ✅ `tsci` | ❌ **本机装不上**：它要求 **Node 24**（本机是 22），而且依赖的图像库 sharp 在安装时要从 GitHub 下载二进制，被沙箱网络挡住了。在你自己电脑上装好 Node 24 应该能用，但还没实测 | 版本还是 0.x，迭代很快，用于开关电源功率板偏冒险；很适合 LIB 这种小板 |
| **Freerouting** v2.5.0（2026-10-05） | 自动布线器 | ✅ `java -jar freerouting.jar -de x.dsn -do x.ses`；还有 MCP 服务 | 未实测 | 本机 Java 是 17，不够的话用它自带运行时的 macOS 安装包 |
| **KiBot** 1.9 | 把所有输出（Gerber、3D、BOM、交互式 BOM、渲染图）写成一份配置，一条命令重建 | ✅ | 未实测 | 适合放进 GitHub Actions，每次提交自动出全套文件 |
| **easyeda2kicad** 1.0.1 / **JLC2KiCadLib** | 按 LCSC 料号下载符号、封装和 **STEP/WRL 3D** | ✅ | ✅ 已成功下载 | 接口偶尔限流 |
| **KiCad MCP 服务器**（如 mixelpixx/KiCAD-MCP-Server） | 把 KiCad 包成 100+ 个 AI 工具：放器件、布线、DRC、导出 | ✅ | 未实测 | 社区项目，质量参差；可以当备选，不是必需 |
| **build123d** 0.13 / CadQuery | 用 Python 写机械 3D：面板、外壳、背板 | ✅ | ✅ 已生成 STEP/GLB | — |
| 嘉立创 EDA、Flux.ai、Altium | 图形界面或浏览器工具 | ❌ 没有命令行 | — | 不适合由我驱动 |
| 嘉立创下单 API | 上传 Gerber、报价、下单 | 有 API，但**只开放给审核通过的企业客户** | — | 个人还是网页上传 Gerber，这一步你来点 |

---

## 5. 推荐流水线

```
电路描述（代码，Git 管理）
   │  SKiDL（离线）或 atopile（要账号）
   ▼
网表 + 初始 .kicad_pcb（器件全在板外，只有飞线）
   │  Python 放置脚本：机械约束（板框、孔、连接器朝向）写成坐标
   │  开关回路（CN3791 外围、分流电阻开尔文走线）手工 / 脚本精确布线
   ▼
Freerouting 自动布剩下的信号线（DSN → SES）
   ▼
kicad-cli：ERC / DRC 不过就回到上一步
   ▼
kicad-cli / KiBot 出全套：
   ├─ Gerber + 钻孔 → 实验室制板机 或 嘉立创
   ├─ BOM + 贴片坐标（如果走代工贴片）
   ├─ PDF 原理图、装配图（给副院长和实验室看）
   ├─ 渲染图 PNG（我用它自查布局）
   └─ STEP / GLB 3D（器件模型来自第 1 节）
   ▼
build123d 总装：面板 + 背板 + PMB-H 外壳 + 线缆 + LIB 外壳 + BITalino
   ▼
GLB → 现有的 3D 背心网页（替换掉现在的方块示意件）
```

**我能做和不能做的：**

- ✅ **我能做**：写电路代码；写放置和布线脚本；跑自动布线、ERC/DRC；导出全部制造文件和 3D；出渲染图自查；所有自建件的 3D 建模；总装和网页 3D。
- ❌ **要你做**：安装 KiCad；注册账号（如果选 atopile）；操作实验室制板机；嘉立创下单付款；焊接。
- ⚠ **会降低质量的地方**：自动布线不懂开关电源。所以 CN3791 的功率回路和分流电阻的开尔文走线**必须由脚本按规则精确布**，不能交给 Freerouting。出图后我会附渲染图，你或者实验室老师再用 KiCad 图形界面看一眼。

---

## 6. 制板：实验室机器 vs 嘉立创

| | 实验室制板机 | 嘉立创 |
|---|---|---|
| 输入 | 取决于机型：**数控雕刻机**要 Gerber 转 G 代码（pcb2gcode / FlatCAM，开源，本次未实测）；**曝光 / 激光**要镜像的 PDF 或 SVG（`kicad-cli pcb export pdf/svg` 直接出） | Gerber 压缩包，网页上传 |
| 能力 | 未知 ❓。没有过孔金属化、没有阻焊的话，规则要放宽（线宽、间距 ≥ 0.3 mm，过孔用铆钉） | 2 层 / 4 层、沉金、阻焊都有；可以代贴片 |
| 周期 | 当天 | 3–7 天 |
| 建议 | **Rev A 载板在实验室做**：都是大焊盘，改得快 | **Rev B 和 LIB 小板走嘉立创**：小板精度要求高，贴身用还需要阻焊和沉金防汗 |

> **需要你确认：实验室制板机的品牌和型号。** 一台雕刻机和一条曝光蚀刻线，设计规则完全不同，我要按机器能力定线宽、间距和过孔做法。

---

## 7. 汇总成整机 3D

1. 每个零件做成一个 STEP：官方模型（第 1 节 ✅）、自建模型（第 2 节）、PCB 导出（第 5 节）。
2. 用 build123d 按实测位置总装：面板上下沿 156.5 / 139.5 cm、支撑 18–28 mm、J6 走线路径。
3. 导出 GLB，替换现有 3D 背心网页里的方块示意件。

⚠ **人体模型**：可以用你的扫描或推断出的身体来贴合背板曲面，但那是你的身形数据。**发布到网页之前我会先问你**；默认用通用人台。

---

## 8. 这次调研顺带核实或更正的事

| 项目 | 以前 | 现在 | 来源 |
|---|---|---|---|
| AEM10941 输入上限 | ⚠「约 ≤ 5 V，来自记忆」 | ✅ **开路电压最高 5.0 V**，冷启动 3 µW / 380 mV。v3 局限第 5 条可以关闭 | e-peas 官网 |
| AEM10941 封装 | v1 写的是 QFN-40 | **QFN28 5×5 mm**（不影响结论：它仍然不能手焊） | e-peas 官网 |
| YJL3404A | ❓ 只知道是 MOSFET | **N 沟道，30 V / 5.6 A，SOT-23**，R<sub>DS(on)</sub> < 40 mΩ @ 4.5 V | 数据手册 |
| HeartBIT 套件 | 内容未核实 | Core BT/BLE、ECG 传感器（30 cm 导联）、PulseSensor、(r)evolution 外壳、**700 mAh 锂电池**、电极 25 片、USB 线、蓝牙适配器 | PLUX 官网 |
| 腋下高度 → J6 线长 | 117 / 83 cm | 102 / 64 cm（上次已更正），买 1.2 m 的结论不变 | 身体扫描 |

---

## 9. 下一步：需要你决定的

| # | 问题 | 我的建议 |
|---|---|---|
| 1 | 选哪条电路描述工具？ | **KiCad 10 + SKiDL**：完全离线、不用账号，产出的标准 KiCad 工程实验室和副院长都能用图形界面打开。tscircuit 要先装 Node 24，装好后我拿 LIB 小板试一下，好用再推广。atopile 只有你愿意注册账号才选 |
| 2 | 装 KiCad 10 | 在终端运行 `brew install --cask kicad`（沙箱不让我装）。装好后我先跑一遍 `kicad-cli version` 确认 |
| 3 | 实验室制板机型号 | 拍一张机器铭牌或型号的照片 |
| 4 | 第 2 节的尺寸 | 能量多少量多少，没量的我先用资料值并标出来 |

---

## 参考来源

- Seeed XIAO nRF52840 资料页（含 3D 模型、KiCad 工程）：https://wiki.seeedstudio.com/XIAO_BLE/
- Seeed 官方 KiCad 库：https://github.com/Seeed-Studio/OPL_Kicad_Library
- e-peas AEM10941（数据手册、EVK 手册、CAD 包）：https://e-peas.com/product/aem10941/
- PLUX HeartBIT：https://www.pluxbiosignals.com/products/heartbit
- PLUX (r)evolution 3D 打印外壳：https://pluxbiosignals.com/products/3d-printed-casing-for-revolution-board
- BITalino V3 开源板图：https://github.com/PIA-Group/schematics-bitalino
- LCSC：CN3791 C154992 https://www.lcsc.com/product-image/C154992.html ；INA226AIDGSR C49851 https://www.lcsc.com/product-image/C49851.html ；LM66100DCKR C2869734 https://fat.lcsc.com/product-image/C2869734.html ；LM74700QDBVRQ1 C2941042 https://fat.lcsc.com/product-detail/C2941042.html
- YJL3404AQ（JLCPCB C2942683）：https://jlcpcb.com/partdetail/3323357-YJL3404AQ/C2942683 ；YJL3404A 数据手册：https://static.chipdip.ru/lib/076/DOC013076228.pdf
- Adafruit 6 V 6 W 面板（尺寸参考）：https://www.adafruit.com/products/1525
- KiCad 10 发布：https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/
- kicad-cli 文档：https://docs.kicad.org/10.0/en/cli/cli.html
- KiCad Python / IPC 接口：https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/
- KiBot 3D 导出：https://kibot.readthedocs.io/en/latest/configuration/outputs/export_3d.html
- atopile：https://pypi.org/p/atopile
- tscircuit：https://github.com/tscircuit/tscircuit
- easyeda2kicad：https://github.com/uPesy/easyeda2kicad.py
- Freerouting：https://github.com/freerouting/freerouting
- KiCad MCP Server：https://github.com/MJP-Sys/kicad-mcp-server ，https://mcpservers.org/ja/servers/mixelpixx/kicad-mcp-server
- 嘉立创 API 说明：https://api.jlcpcb.com/help/article/jlcpcb-online-api-available-now
