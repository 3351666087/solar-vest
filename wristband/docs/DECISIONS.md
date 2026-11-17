# SolarBand V3: final decisions (lead synthesis, fixed after verification)

> **Status:** 2026-11-13. Lead synthesis, revised the same day by the fix stage after two verification lenses (`verify/engineering.md` E-1 to E-14, `verify/experience.md` X-1 to X-13). Every issue was re-checked at its source; all 27 were confirmed. Each change, with its before → after, is in `CHANGELOG.md`. The pre-fix calculation is kept unchanged in `calc/pre_fix/`.
> **Where things were written:** `v3/decide/` only, plus the two pointer edits the task allowed (one line under `V3_ARCH.md` §12; a new §9 at the end of `V3_REPORT.md`). Nothing in `ARCHITECTURE.md`, `design/`, `sim/`, `redesign/`, `v2/` or the repository was changed. Nothing was bought, quoted, requested or uploaded. No account was used. No message was sent.
> **The instruction this implements (user, 2026-11-13, verbatim):** "需要我定的所有东西你来按最优解来定，我指的是真实的用户体验和市场需求"
> **Inputs:** `v3/V3_ARCH.md`, `v3/V3_REPORT.md`; the research lanes `decide/research/market/MARKET.md`, `ux/UX.md`, `eng_a/ENG_A.md`, `eng_b/ENG_B.md` (with their JSON and calc folders); the three judges (`decide/judges/{consumer,research,manufacturing}/NOTES.md`); the two lens returns (`decide/verify/`).
> **How decided:** the safety floor first (pass or fail, never traded). Then the judges where they agree. Where they disagree, the evidence in this order: real everyday experience, market demand, the user's thin/light/small preference, engineering risk and schedule. An extra change is adopted only if at least two judges support it, or the evidence is strong and the cost small. All four of the user's asks are answered: two as asked, two with a changed method (§6).
> **Numbers:** `calc/baseline_calc.py` → `calc/baseline_calc.json` (fix-stage run 2026-11-13, exit 0). The script still reproduces V3-R as published exactly (T1 21.6 d, worst stack 11.5 d, T3 12.5 min, W2 23.2 d, W7 26.9 d, 19.1 / 20.2 g, 0.486, 4.65 mm). All V3-F numbers are ⚠ model or planning values unless marked.
> **Conventions (fix stage):** "Highest point when worn" is each item's thickness above the skin where it rests: the pod with the PPG mesa pressed in; a strap item at the far end of its free span, where it rests on the skin. This is how V3 measured the USB-C tab (4.6 mm). T1 is given two ways: with the 30-min night blank (V3-F's display policy) and with the face always on (V3's convention).
> **Marks:** ✅ read in a named source (the lane file named keeps the URL, page and figure; "read again today" where the fix stage re-opened it); ✅s search summary only; ⚠ estimate or model output (method named); ❓ unknown.
> **Names:** the chosen configuration is **V3-F**. Its full specification is `BASELINE.md`. The band harvests light; nothing here is wireless power transfer.

---

## 0. 中文摘要（给用户）

### 0.1 结论

我按"真实使用 + 市场需求"把待你决定的事全部定了。结果叫 **V3-F**。两轮核查后改了几处（清单见 `CHANGELOG.md`），大方向不变：

- 表体目标 **40 × 32 mm**。按现在的估算，主板按 v1 的口径还超一点（0.626，限 0.62）。所以上盖和环体的询价先按 **41 × 32 mm** 准备；V3-G1 真能放下，再回到 40 mm。
- 电芯换成 **70 mAh**，仍放在表带根部 A 的白色小壳里，整包从电芯厂买。小壳顶面改用 0.40 mm 强化玻璃，30 N 按压碰不到电芯 ⚠。
- **屏保留**，第一版就设计好**前光**。前光膜在屏的上面，屏下面保留支撑。
- **表带上不再有 C 口充电片。** 改为表体顶面两个平齐触点，加一个随盒附带的**隔离 C 口磁吸充电头**。
- 加一个**密封侧键**和一个**小振动马达**。
- 产品目标 **5 ATM**（能游泳）。为此上盖两块玻璃之间加一根带不锈钢芯的横梁，用 6 根小柱撑在主板上；光伏条因此窄 8 % ⚠。5 bar 测试通过之前，只宣称 IP68 1.5 m。

你的四个要求：两个照做，两个改了做法。
1. **表带光伏：照做。** 仍是刚性晶硅翼片（柔性片弯不到手腕的半径，见 V3 报告）。
2. **不摘下来用：照做，有条件。** 靠光，戴着就能充。每天在晴天户外（约 5 万 lx）待 20 分钟以上、表面和翼片不被衣袖遮住，就不用插线；阴天约要 50 分钟；翼片被衣袖遮住时，晴天也要约 25 分钟 ⚠。只在室内的人约 41 天插一次线。在导师批准戴着充电的规则、厂家做完漏电流测试之前，插线时要摘下来（约 2 小时）。
3. **C 口应急充电：改了做法。** 手环本体不再有 C 口，要通过随附的隔离充电头（钥匙扣大小）才能用 C 线。没带充电头就不能插线，只能晒太阳：户外晴天约 10 分钟够用 1 天，阴天约 45 分钟 ⚠；屋里的灯光（200–1,000 lx）补不回每天的耗电 ⚠，只够让没电的手环重新开机。
4. **显示屏：有，夜里能看要等前光膜。** 夜里能看要等定制前光膜做出来；首批研究样机可能先不带前光。

主要数字（⚠ 估算）：
- 佩戴质量 19.3 g（最大实体 21.0 g），比 V3-R 的 19.1 g 重 0.2 g。
- 黑暗续航：夜里熄屏 38.4 天；按 V3 的口径（屏一直亮）34.3 天。V3-R 是 21.6 天。
- 最坏叠加：21.9 天（屏一直亮 18.7 天），都过 14 天目标；V3-R 是 11.5 天，不过。
- 只在室内（300 lx × 10 h）：满电 40.6 天后才需要补电（V3-R 23.2 天）。
- 戴着时离皮肤最远的是表带根部的电芯小壳，约 4.5 mm（表体屏那半 4.30 mm、光伏那半 3.85 mm）。V3-R 是 C 口充电片 4.6 mm、小壳 3.5 mm、表体 3.85 mm。所以"最高点"几乎没降；去掉充电片的好处在位置、防水和安全，不在高度。
- 表体厚度：光伏那半 4.65 mm，屏那半 5.10 mm（前光要在屏上面，屏下面还要支撑）。按已查证的上盖工艺，光伏那半是 5.12–5.42 mm。

### 0.2 逐项决定

**1. 电芯放哪（D-1 位置）**
- **选：** 表带根部 A 的白色小壳（同 V3-R），不放回表体。三位评审一致。
- **为什么：** 放回表体要么更长，要么更厚：
  - 43 mAh 放回表体，表体沿前臂方向 49–52 mm 长（V3-P）。
  - 再加按键和振动，约 53–58 mm（研究、制造两位评审估算 ⚠）。
  - 70 mAh 放回表体，要厚到 6.30 mm，或长到 55 mm ⚠（ENG_A §3.4）。
  - 沿前臂方向，主流手环表体只有 22.5–24.9 mm ✅（UX S31、S32；方向是推断 ⚠）。V3-F 的 40 mm 已经像手表；V3-P 的 49–52 mm 约为手环的两倍，手腕后弯时可能顶到手背 ⚠。
- **代价：** 小壳 38.4 × 11.9 × 4.5 mm。它是戴着时最厚的一块：离皮肤 4.50–4.55 mm ⚠。它在手腕尺侧上方，外表面比表体顶面低 1.4–2.8 mm ⚠。
- **风险：**
  - 小壳被挤压可能短路。对策：电芯旁的保险 F1、表带导线的排列顺序、强化玻璃顶面、挤压测试（V3-G7）。
  - 电芯本体 30 mm，加上 6 ± 1 mm 的极耳和 4 mm 的保护板，会超出小壳 37.4 mm 的内长 ✅/⚠。所以询价写明"电芯连焊点 ≤ 33.4 mm（焊前剪短极耳），保护板平放 ≤ 4 mm"；做不到时小壳加长到约 41 mm（最大实体 +0.1 g ⚠）。
  - 冬天户外小壳低于 0 °C 时，光充暂停。
  - "坏了"是前用户停用的第一原因（33.3 % ✅ MARKET §5）。所以小壳必须通过 V3-G2 和 V3-G7，不通过就退回 V3-P。

**2. 电芯大小和采购（D-1 容量）**
- **选：** 70 mAh 级电芯 GEB301030：3.0 × 10 × 30 mm，最小容量 70 mAh，最大充电 1.0 C ✅（规格书，ENG_A §3.2）。
  - 整包从电芯厂买：电芯 + 保护板 + 保险 + NTC，由厂家点焊，附 UN 38.3 和 IEC 62133-2 报告。
  - 限流电阻 R_LIM 从 22 Ω 改为 12 Ω，充电电流设定电阻从 18 kΩ 改为 10 kΩ。
  - 这两个阻值和电池包锁成一套料单，出厂时检查。锁定条件：标称 ≥ 66 mAh、最小 ≥ 60 mAh。原因：10 kΩ 时 C 口最大充电 33 mA，标称 60 mAh 的电芯会到 0.55 C，超过项目的 0.5 C 规则 ⚠。
  - 询价时优先问更薄的电芯：标称 ≥ 66 mAh、最小 ≥ 60 mAh、新电芯 ≤ 2.7 mm、宽 ≤ 10.5 mm。小壳可降到 4.2 mm，续航仍全部达标（黑暗 33.0 天、最坏 18.9 天、存放 224 天 ⚠）。没有现成型号 ❓。
- **为什么：**
  - 买家最看重续航（65 % ✅，YouGov 2022，MARKET §5），最常抱怨的也是续航（21.4 % ✅，JMIR 2025）。
  - 43 mAh 时最坏叠加只有 11.5 天，过不了 14 天目标；70 mAh 时 21.9 天（屏一直亮 18.7 天）⚠。
  - 对照手环 W-C 不采光。它在最坏叠加下也有 15.8 天 ⚠，够一个两周的研究周期。
- **代价：** 典型 +0.2 g；小壳从 3.5 mm 厚到 4.5 mm，成为戴着时最厚的一块；主板面积不变。
- **风险：**
  - 规格书写电芯"约 3 g" ❓。若属实，佩戴质量变成 20.9 g。
  - 目前只有一个货源 ❓，定型前要找第二货源。
  - 如果 12 Ω 被错配到 43 mAh 电芯上，充电倍率是 0.63–0.66 C ⚠，超过 0.5 C。所以要锁料单。

**3. 显示屏（D-2）**
- **选：** 保留夏普 LS011B7DH03（1.08 英寸反射屏）。
  - 第一版就把前光设计进去：定制前光膜（膜本身 0.05 mm ✅，连胶的总厚在询价里限 ≤ 0.25 mm）、LED 驱动、尾线焊盘。
  - 前光膜在屏的上面。两种做法：由夏普认可的合作厂贴在屏面上（Azumo 的 1.28 英寸成品就是这样 ✅）；或者贴在屏窗玻璃下面。我们自己不能往屏面上贴胶 ✅（夏普说明）。屏下面保留 V3-R 的支撑框。
  - 有光时屏常亮，30 分钟没光自动熄屏。
  - 按键，或在非睡眠时段抬腕，就亮屏；暗处前光亮 3 秒。睡眠时段要按住 ≥ 1 秒才亮屏和前光；短按只记录，不亮。
  - 手机通知首发不做。原因：少打扰、睡觉时不亮不振，这正是很多人选无屏手环的理由 ✅（UX S28）；研究模式也不需要。以后作为消费模式的可选项，默认关。
  - 研究模式只显示时间、日期、电量、"记录中"图标、充电提示和安全警告。
  - 研究样机可以先不装前光膜；上市版本必须带前光。
  - 所有版本只做一种上盖（一半光伏、一半屏窗）。拿到屏样品前，研究样机用同一个上盖，把屏窗遮住；遮挡层吸收率 ≤ 0.6，这种样机也进 SIM-13。
- **为什么：**
  - 消费者接受"带光的屏"，也接受"没有屏"。"不带光的反射屏"是市场试过又否定的组合：2014 年的 vívofit 因夜里看不见被批评 ✅；下一代加了背光 ✅s（搜索摘要）（MARKET §2.2、§9）。
  - 这块屏只透过 0.2 % 的光 ✅，夜里完全看不见。
  - 一位无屏手环的评测者希望有个简单的时钟 ✅（MARKET §7）。
  - 研究里两只手腕都戴 SolarBand。如果没屏，参与者整个研究期间都看不到时间。
- **代价：**
  - 屏那半表体 4.65 → 5.10 mm ⚠：前光 +0.25 mm，5 ATM 的屏窗玻璃 +0.20 mm。
  - 主板 +6.4 mm²；+0.05 g。
  - 前光这一步（硬件，屏仍一直亮）：黑暗续航 38.4 → 35.6 天 ⚠。
  - 夜间熄屏这一步（固件）：35.6 → 40.0 天 ⚠。两步合起来是 +1.6 天。
- **风险：** 货源要过两关：
  - 夏普样品：Digi-Key 不备货，最少 1,600 片，交期 28 周 ✅；立创库存 0 ✅。
  - 定制 1.08 英寸前光膜：目录里没有这个尺寸 ✅，开模费和起订量 ❓。贴在屏面上要靠夏普认可的合作厂 ✅（Azumo 是"Sharp Approved Value-Added Partner"）；贴在玻璃上时效果 ❓。

**4. 戴着插线充电（D-3：导师定，我只给建议）**
- **建议：**
  - 现在：一律摘下来充，直到厂家做完漏电流台架测试。
  - 目标规则："戴着时只能用随附的、加强隔离的充电头充电（UCC12050 一类，或两道独立的基本隔离），以后也可以用隔离夹式充电宝；手环本体没有 USB 插口；有 VBUS 时由硬件关闭心电；每次充电都打标记。"
  - 研究用的充电头如果用基本隔离的 UCC12040，就标"只能摘下来充"。发给受试者戴着用的充电头，一律用 UCC12050（立创无货，要寄售或从别的渠道买）。
  - 每个充电头出厂都做耐压（hi-pot）测试。
  - 手环的触点做成目录里的磁吸插头插不上（非标准间距、凹进去的触针、磁极编码）。CAD 证明之前，不说"只有随附的充电头能插上"。
  - 不采用"在电极前串大电阻"(c)，也不采用"只用充电宝"(a')。
- **为什么：**
  - 隔离做在充电头里。戴着充电时，流过人体的电流 ≤ 5 µA ⚠，限值是 100 µA ✅。
  - 基本隔离只算一道保护。它被击穿（单一故障）后，充电头就等于一根普通线：用 0.5 mA 级充电器时是 500 µA ⚠，正好卡在单一故障限值 500 µA 上，没有余量。加强隔离击穿一处后仍然隔离。
  - 有人用外形相同、不隔离的磁吸线戴着充电时，正常状态就有 250–500 µA ⚠，是限值的 2.5–5 倍。所以触点要做成插不上。
  - (c) 在手指碰到 E3 时，每路电极要 ≥ 3.45 MΩ。按 M2 的输入短路测法（在芯片管脚短路），这部分电阻噪声不计入 10 µVpp；但真实的心电底噪确实升高（6.2 → 15.6 µVpp ⚠），会影响"采能是否影响生理信号"的比较（ENG_A §5.2）。
  - (a') 做不到：佩戴者分不出手里的充电宝是不是在边充边放 ✅/⚠（V3_ARCH §3.5：直通充电宝有厂家说明 ✅，其余是分析 ⚠）。
  - 市面上没有产品戴着插线充电，只有 WHOOP 的滑扣充电宝能戴着充 ✅（MARKET §6.1）。
- **代价：** 手环本身 0 mm、0 g。充电时停心电；PPG、皮温和遥测照常。加强隔离芯片要寄售。
- **风险：**
  - 充电头的隔离电容 ❓；不充电时的空载电流（发热）❓。
  - 加强隔离的 UCC12050 立创库存 0 ✅。
  - 充电头放在表体上会发热 90–165 mW ⚠，要放进 SIM-13。
  - 剩下的误用风险：有人自制不隔离的充电头。

**5. 充电接口（D-4）**
- **选：** 去掉表带上的 C 口充电片。
  - 表体顶面肘侧角做两个平齐触点；表带里不再走 VBUS。
  - 随盒附一个隔离 C 口磁吸充电头：钥匙扣形，可单独买备用；研究套件每人两个。
  - 夹式充电宝以后作为配件。
- **为什么（这是你要的功能，所以把证据摆清楚）：**
  1. **位置，不是高度。** 充电片在手腕尺侧边缘（离表杆 23.5–35.5 mm），打字、侧睡时可能受压、会勾袖口（UX §5.3，几何推断 ⚠）。去掉后根部 A 在 16 mm 处结束，少一个弯折铰链。高度上没有好处：70 mAh 的小壳离皮肤约 4.5 mm，只比充电片的 4.6 mm 低 0.1 mm。
  2. **防水。** 开口的 C 口让防水最多到 1–1.5 m 级 ✅/⚠（ENG_A §6.2）。目前没查到能防 5 bar 的 C 口母座，所以 UX 通道给充电片定的"防水达到整机等级"这个条件做不到。15 款消费手环全部能游泳 ✅（MARKET §2.3）。触点方案能做到 5 ATM，但要靠上盖的支撑横梁（第 9 项）；5 bar 测试通过之前只宣称 IP68 1.5 m。
  3. **安全。** 只有"触点 + 加强隔离的配件"能让戴着充电在设计上就安全（见第 4 项）。
  4. **市场。** 23 款有线充电的产品，没有一款在机身上开 C 口，全部用专用触点或专用线 ✅（MARKET §6.1）。
  5. **更轻、更少故障点。** 轻 1.2 g；表带里少一根 VBUS 线，少一段弯折软板（"坏了"是停用的第一原因）。
  - **反面证据：** 2019 年华为手环 4 自带 USB 插头、不用线，评测者称赞 ✅；华为现在的手环 10 已改为磁吸充电 ✅。
  - **评审分数的复核：** 三位评审都把"充电片是最高点"当作理由之一，这一条不成立。把他们的体验分改一改（充电片 +2 分、触点 −2 分），触点方案仍然领先（7.03 对 6.50 ⚠）。
- **保留的：** C 口应急充电，但要通过充电头。充电头上就是 C 口：任何 C 线、充电器、充电宝、电脑、手机都能用；导师同意后，戴着也能充。
- **放弃的：** 什么都不带、直接把线插在手环上。没带充电头时只能晒太阳：户外晴天约 10 分钟够用 1 天，阴天约 45 分钟 ⚠；屋里的灯光（200–1,000 lx）补不回每天的耗电 ⚠，只够让没电的手环重新开机（约 170–360 lx ⚠）。所以只在室内的人要随身带充电头（研究套件每人两个）。
- **代价：** 要带充电头（约 25 × 15 × 7 mm、4–6 g ⚠）。主板 +12.6 mm²（两个弹片）。
- **风险：**
  - 充电头会丢。对策：钥匙扣、备用头、研究套件每人两个。
  - 触点镀层和镍释放 ❓。
  - 反插必须做到不可能：磁极方向加上大小不同的触点。V3-G4 和 V3-G6 查一次反插（−5 V）的后果，必要时加防反接器件。
  - 欧盟以后可能把手环纳入统一 C 口规定：2026-06-30 的报告把手环列为候选，但没有提案，也没有日期 ✅（MARKET §6.2）。真纳入时，改为"表体肘端加一个密封 C 口"。

**6. 交互**
- **选：** 一个密封侧键，加抬腕亮屏，加有条件的双击。
  - 侧键在手那一端的侧壁、E3 下方。用 C&K PTS840 侧按开关，隔着环体上一体成型的膜，不穿墙。
  - 抬腕亮屏只在消费模式、非睡眠时段有效。
  - 抬腕后 3 秒内双击才有效。不用电容触摸，不用常开的双击。
  - 按法：短按亮屏、翻页；双按标记事件；长按 2–5 秒开始心电或确认警报。
  - 按住超过 5 秒当作卡住（例如在水里被水压按住）：只记录，不执行，也不能确认安全警报。
  - 睡眠时段按住 ≥ 1 秒才亮屏和前光；短按只记录。
  - 按键也能把手环从运输模式唤醒。
- **为什么：**
  - Fitbit 因用户抱怨，在 Charge 6 上恢复了实体按键 ✅（UX S22）。
  - 只靠双击不可靠 ✅（MARKET §7）；触摸在水里失效 ✅（UX S54）。
  - 研究设备用按键标记事件（Empatica E4、ActiGraph LEAP ✅，ENG_B §3）。
- **代价：** 主板 +18.4 mm²，+0.1 g，0 µW；多一道静态密封。双击 0.67 µW，黑暗续航约 −0.1 天 ⚠。
- **风险：**
  - 开关的高度、焊盘和按动方向还没读到 ❓。JLC 写"Vertical"，Digi-Key 摘要写"侧按" ❓。现在用的 17.0 mm² 和 1.05 mm 都是假设。V3-G1 之前读原厂图纸；若是顶按，就换侧按的型号，重算面积和高度。
  - 5 bar 时膜上的力（约 4.5 N ⚠）大于开关的动作力 2.2 N ✅，开关会被一直按住：固件按"卡住"处理；V3-G7 查膜的密封。
  - 膜的寿命。

**7. 提醒（含给导师的决定 5 建议）**
- **选：** 加一个低电流扁平振动马达：Ø8 × 2.1 mm，≤ 35 mA，Vybronics VCLP0820B004L 类。
  - 装在光伏条下方主板的 Ø8.6 mm 开孔里，粘在底膜上；开孔下面的载膜剪掉，高度余量 0.15 mm ⚠。
  - 规划位置在两块心电电极板之间（X 20、Y 25.4 mm）。原规划位置（X 27）压在电极板上 ⚠。为此把根部 A 的入线焊盘挪到肘侧（X 4.5–10.5 mm）。现在 Y 方向没有余量，V3-G9 要把马达和横梁小柱一起排。排不下，Ø8 马达就放不进，决定 5 维持 LED。
  - VBAT ≥ 3.60 V 时才振；心电测量时不振。
  - 消费模式有静音振动闹钟，在每天 4.7 秒振动的预算内；每天振 15 秒时，黑暗续航约 36.4 天 ⚠。
- **给导师的建议（选项 (d)）：** 皮肤过热时：
  - 先振动，振法照文献：每 6 秒一组，组内 0.5 秒振、0.5 秒停，组间停 1 秒；一直到按键确认（按下再松开）或皮温降到 40 °C 以下，最多 10 分钟。每次约 7.9 mWh，占电池的 3.6 % ⚠。
  - 同时全屏警告；这个警告压过熄屏等所有关屏状态。
  - 同时发蓝牙标志。
  - 侧面 LED 先保留。去掉它要两个条件：导师书面同意 (d)；厂家用实际的马达隔着底膜测过振感和叫醒效果。
- **为什么：**
  - 振动不用看就能察觉。腕部振动闹钟（Feeltact）叫醒了健康受试者 94–100 % 的闹钟次数（18 人；按自述、起身、脑电分别是 94 %、99 %、100 %）✅（UX S38，今天重读）。18 人里 13 人每次都醒；患者组按自述只有 63–66 %。
  - 那项研究的振法比原来建议的"每分钟 3 × 0.5 秒、最多 5 次"多约 34 倍，而且没报告振动强度 ❓。所以振法照抄文献。
  - 44 °C 持续 3–4 小时会造成低温烫伤，睡着时很难察觉 ✅（UX S43）。
  - LED 恰恰在大太阳下最难看清，而过热报警正是这时触发；能否看见未验证 ❓。
  - 11 款产品确认有振动 ✅（MARKET §9）。
- **代价：** 主板 +8.4 mm² 元件，开孔占掉 66 mm² 的布局面积；+0.3 g；每天约 6 µW，黑暗续航约 −1.1 天（40.0 → 38.9 天 ⚠）。
- **风险：**
  - 隔着 0.25 mm 底膜，振感够不够 ❓（由厂家用样品测）。备选 Ø10 马达振感更强（≥ 0.75 G ✅），但开孔更大，按 v1 口径主板到 0.652 ⚠，而且两块电极板之间可能放不下 ❓。
  - 5 bar 时底膜会把马达往上推（无支撑时 0.77 mm ⚠，而余量只有 0.15 mm）。V3-G7 查；需要时马达下面的底膜换成 0.25 mm 钛片（+0.05 g ⚠）。
  - 马达离天线要 ≥ 10 mm；规划位置是 20.9 mm。

**8. 存放（T6）**
- **选：** 存放目标按普通待机计算：257 天 ✓（目标 ≥ 182.6 天）。
  - 出厂用运输模式（411 天）。空运时电量 ≤ 30 %，其他运输 30–50 %；库存超过 3 个月要补电。
  - 运输模式可用按键、充电头或光唤醒。开箱按一下键就开机。
- **代价：** 按键唤醒用的二极管和原来的 USB 唤醒二极管合成一颗 BAV70M（SOT-883）。这样反而省了 0.001 的主板利用率（0.565 对 0.566 ⚠）；0 g。
- **风险：** 普通待机天数依赖实测的保护板电流和自放电。

**9. 防水**
- **选：** 产品目标 5 ATM（ISO 22810，能游泳）。
  - 宣称：5 bar 测试在量产样机上通过之前，一律只宣称 IP68 1.5 m。温水淋浴可以；热水澡、桑拿、泡温泉不行；游泳时先摘下并记录。
  - 从第一版起就按 5 ATM 的结构做：上盖两块玻璃（光伏片，加 0.70 mm 屏窗玻璃），中间一根带不锈钢芯（0.5 × 0.7 mm）的横梁，用 6 根小柱撑在主板上（间距 ≤ 6 mm）。
  - 横梁只能放在屏的旁边，所以光伏片的边从 Y 20.2 挪到 Y 21.0 mm，四条光伏条从 2.5 mm 窄到 2.3 mm（−8 %）⚠。
  - 屏窗玻璃要刚性粘在不锈钢框上；只能弹性粘接时，玻璃要 0.80 mm（+0.10 mm）⚠。SIM-14 定。
  - 每台出厂做气密测试。
- **为什么：**
  - 15 款消费手环全部能游泳 ✅（MARKET §2.3）。
  - 参与者游泳后忘记戴回去，会丢数据 ✅（UX S46）。
  - 只有触点方案没有开口。
  - 核查发现：原来的横梁压在屏的边框上，最多 0.10 mm 深，旁边也没地方放支柱，等于没有支撑。两块玻璃约 0.3 bar 就会碰到下面 ⚠，离 5 bar 差 15 倍。现在的横梁和小柱让光伏玻璃到 7.7 bar、屏窗玻璃（刚性粘接）到约 14 bar 才碰到 ⚠。
- **代价：** 屏那半表体 +0.20 mm；横梁和小柱 +0.12 g，屏窗玻璃 +0.25 g；小柱在主板上占 6 mm²；光伏条窄 8 %：晴天要晒的时间 T3 10.9 → 11.2 分钟，只在室内 40.7 → 40.6 天，冬季办公 45.8 → 45.4 天 ⚠。
- **风险：**
  - 屏能承受多大压力 ❓。若夏普书面给出屏边框的承压值，横梁就能压在屏边框上，光伏条恢复 2.5 mm。
  - 33 mm 长的不锈钢芯接近 2.44 GHz 的四分之一波长，SIM-10/11 要查。
  - 小壳在 5 bar 下：玻璃顶面在 4.4 bar（简支）就碰到电芯，再往上由电芯承压，要电芯厂认可 ⚠。

**10. V3 默认项**
- **保留：**
  - R131 和 R108 用 10 MΩ。
  - 翼片不加二极管。说明书写明："没电的手环离手放置时，要接充电头，或拿到户外晒 10–45 分钟；屋里的灯只能让它重新开机（约 360 lx 以上），补不回一天的电。"
  - 屏的软排线直接焊接。
  - 翼片保持全长，直到 SIM-13 有结论。这是人体佩戴前的硬关卡：SIM-13 证明不了皮肤 ≤ 43 °C，就改用缩短的翼片（T3 最多 +2 分钟）。
- **改：**
  - 43 mAh 改为 70 mAh。
  - R_LIM 22 Ω → 12 Ω，RISET 18 kΩ → 10 kΩ，与标称 ≥ 66 mAh 的电池包锁定。
  - T6 改按普通待机计算。
  - "左手戴、翼片在桡侧"改为左右手都能戴。
- **加（安全底线）：** 用电芯的 NTC 做硬件光充禁止：0–45 °C 之外停止光充。单片机关着、电芯深度放电或保护板已断开时也要有效。
  - 比较器和 Q1 的驱动取电于光伏节点或 VSTOR（有光、能往电芯充电时它们一定有电），不能只靠电池。
  - NTC 节点上已有充电芯片的 TS 偏置和单片机的采样；光充禁止的分压只在有光、没有 VBUS 时接通，并在 V3-G4 重算 TS 窗口。
  - 首选做进电池保护板（要写明它在多低的电芯电压下仍有效）；否则在主板上预留 12 mm²。

**11. 另外三项改动（只采纳三项）**
1. **左右手都能戴。** 戴右手时把手环转 180°，屏幕翻转，翼片仍在桡侧。研究方案要求左右手交换 ✅（ARCHITECTURE §1.1）。0 g，0 mm²。
2. **外圈表带可换。** 两种长度，合计覆盖约 130–210 mm。130 mm 手腕已按模型算过：小壳只超出切点 0.2 mm，内面仍贴着皮肤 ⚠（V3-G9 用 CAD 再核）。两种长度的分界按国标腕围数据定 ❓。速干材料；根部免工具快拆。依据：14.9 % 的用户说戴着不合适，15.7 % 说会掉 ✅（MARKET §5）。约 +0.1 g。
3. **用白话显示能量。** 屏和 App 显示"按现在的光还能用几天"和"今天的光够不够"，用的是实测的采能，不是宣传数字。没电前至少 24 小时振动提醒（目标 3 天）。太阳能的说法写明条件："每天在晴天户外（约 5 万 lx）待 20 分钟以上、表面和翼片不被衣袖遮住，就不用充电；阴天约要 50 分钟；只在室内约 6 周补一次电（⚠ 估算）。"研究模式下隐藏这些信息。0 g，0 mm²。

（研究模式和"不丢数据"规则算在屏和充电两项里；整包买电池算在电芯一项里；振动闹钟算在提醒一项里。）

### 0.3 V3-F 与 V3-R 对比（⚠ 估算，标 ✅ 的除外）

| | V3-R | **V3-F** |
|---|---|---|
| 表体外形 | 40 × 32 mm | 目标 40 × 32 mm；询价先按 41 × 32 mm，V3-G1 定 |
| 表体厚度（最大实体，按上盖询价目标） | 4.65 mm | 光伏那半 4.65 mm，屏那半 5.10 mm |
| 按已查证的上盖工艺 | 5.12–5.42 mm | 5.12–5.42 mm（光伏那半决定） |
| 各项离皮肤的厚度（戴着） | C 口充电片 4.6；小壳 3.5；表体 3.85 mm | 小壳 4.5；表体屏那半 4.30、光伏那半 3.85 mm |
| 佩戴质量 典型 / 最大实体 | 19.1 / 20.2 g | 19.3 / 21.0 g（41 mm 时 19.5 / 21.2 g） |
| 主板利用率（项目口径 / v1 口径；限 0.62） | 0.486 / 0.538 | 0.565 / 0.626 ✗（41 mm 时 0.546 / 0.605） |
| 黑暗续航 T1（≥ 14 天）：夜里熄屏 / 屏一直亮 | – / 21.6 天（V3 的暗处策略 24.5） | 38.4 / 34.3 天 |
| 最坏叠加：夜里熄屏 / 屏一直亮 | – / 11.5 天 ✗（暗处策略 13.5 ✗） | 21.9 / 18.7 天 ✓ |
| 对照手环 W-C（只靠电池）典型 / 最坏 | 15.7 / 9.6 天 | 26.5 / 15.8 天 |
| 每天要晒几分钟 T3（≤ 20） | 12.5 分钟 | 11.2 分钟（翼片被遮住 24.5 ✗） |
| 只在室内，满电多少天补一次 | 23.2 天 | 40.6 天 |
| 冬季办公周 | 26.9 天 | 45.4 天 |
| 每天 ≥ 20 分钟晴天户外光 / 办公周 / 校园周 | 能量为正 | 能量为正 |
| 普通待机存放 T6（≥ 182.6 天） | 174 天 ✗ | 257 天 ✓ |
| C 口充 0 → 85 % | 2.0–2.5 h | 2.0–2.3 h（冷电芯 3.1 h，模型偏保守） |
| 充 10 分钟够用 | 1.8 天 | 3.0 天 |
| 只在室内时，每 30 天因插线充电摘下的时间 | 2.6–3.2 h | 1.4–1.7 h |
| 夜里看屏 | 看不见 | 能（前光膜做出来之后；按键或抬腕亮 3 秒） |
| 按键 / 振动 | 无 / 无 | 1 个密封侧键 / Ø8 振动马达 |
| 防水 | 1–1.5 m 级（受 C 口限制） | 产品目标 5 ATM；5 bar 测试通过前宣称 IP68 1.5 m |
| 戴着插线充电 | 不允许 | 导师同意且台架测试通过后，只能用随附的加强隔离充电头 |
| 没带充电器时 | 任何 C 线都能直接插 | 只能晒太阳：晴天约 10 分钟够用 1 天 |
| 表带里的导线 | VBUS、GND、NTC、GND、BATT_P | BATT_P、GND、NTC、GND |

对比市场：V3-F 比市面最薄的产品（8.3 mm ✅ MARKET §3）薄 35–39 %。黑暗续航约是在售手环中位数（8 天 ✅）的 4.8 倍（屏一直亮时 4.3 倍）；最坏叠加约 2.7 倍（2.3 倍）（⚠ 模型值对厂商标称值）。

### 0.4 交给导师的两件事（我只建议，不替导师定）
1. **戴着充电的规则（D-3）：** 建议见第 4 项。要点：只认加强隔离的充电头；基本隔离的研究用头只能摘下来充。
2. **决定 5，皮肤过热怎么提醒：** 建议 (d)：振动为主（振法照文献），同时全屏警告和蓝牙标志。导师书面同意 (d)、且厂家测过振感之后，才去掉侧面 LED。

### 0.5 等你决定的购买和账号操作（都不需要你做实验）
- 夏普 LS011B7DH03 样品（通过夏普的销售渠道）。
- 定制 1.08 英寸前光膜的询价（夏普认可的合作厂，例如 Azumo）。
- 电芯厂整包电池的询价和样品：电芯连焊点 ≤ 33.4 mm、标称 ≥ 66 mAh；同时问 ≤ 2.7 mm 的薄电芯。
- 上盖（光伏片 + 屏窗玻璃 + 带不锈钢芯的横梁）和翼片的询价。
- 小壳（强化玻璃顶面）和表带根部的模具询价。
- 带触点（非标准间距）和按键膜的环体的模具询价。
- 振动马达样品（Ø8，和备选的 Ø10），给厂家测振感。
- 隔离充电头打样；发给受试者的头用 UCC12050（立创无货，寄售或别的渠道）。
- 锁定 BQ25170 库存（立创 153–158 片，可订最多 4 片 ✅）。

台架测试（漏电流、充电头耐压、5 bar、挤压、弯折）由厂家做。清单见 `BASELINE.md` §19。

### 0.6 下一步
1. 先做不需要购买的关卡 V3-G1 至 V3-G10（`BASELINE.md` §18）。
2. V3-G1 定表体用 40 mm 还是 41 mm。按 v1 口径主板还超 0.006（0.626 > 0.62）。要靠三项之一解决：
   - 导师书面同意 (d)、厂家测过振感后去掉侧面 LED（0.548 / 0.607）；
   - 或表体加长到 41 mm（+0.2 g；0.546 / 0.605）；
   - 或电池保护板自带低温禁充（0.550 / 0.609）。
   - V3-G1 定之前，上盖和环体的询价按 41 mm 准备。
3. 新加的 V3-G10：隔离充电头的设计审查（隔离等级、爬电距离、反插、空载发热、出厂耐压）。
4. 再做正式布局、cplgate 和嘉立创生产文件包。

---

## 1. For the supervisor (recommendations only; the supervisor decides)

**1.1 Worn-charging rule (D-3).** All three judges and ENG_A agree. The fix stage tightened the head requirement (E-1).
- **Now:** rule (b). The band comes off for every cable charge. This lasts until the manufacturer's bench AC patient-leakage test passes with the isolated head.
- **Target:** replace ARCH §1.5 ("no wired connection while worn") with: *"While worn, the band may be charged only through a supplied head with reinforced isolation (UCC12050 class, or two independent basic barriers), later also through the isolated clip-on pack. The band has no USB receptacle. ECG is disabled in hardware while VBUS is present, and every charge interval is tagged."*
- **Heads:** research prototypes built with the basic-isolation UCC12040 are labelled "off the wrist only". Every head given to wearers uses the UCC12050. JLC has none in stock (presale only ✅ 18:25 UTC), so it is consigned or bought elsewhere.
- **Acceptance (manufacturer, bench):**
  - AC patient leakage ≤ 100 µA in normal condition and ≤ 500 µA in single fault ✅ (limits via the usbc lane and the requirements lens).
  - Test the head on a pass-through power bank, a laptop docked to an earthed monitor, Class II chargers of the 0.25 and 0.5 mA classes, and a Class I desktop.
  - Measure the barrier capacitance and the head's no-load input current.
  - A hi-pot test of every head at end of line.
- **Why:**
  - The intact head bounds patient current at 0.35–5.0 µA (barrier 3.5–50 pF, 264 V, 60 Hz) ⚠. A plain cable from a Class II charger gives 250 / 500 µA ⚠ (ENG_A §5.1).
  - The UCC12040 is basic isolation, 3 kVrms ✅ (ti.com/product/UCC12040, read again today). A basic barrier is one means of protection. Its single fault, a shorted barrier, turns the head into a plain cable: 250 / 500 µA ⚠ from 0.25 / 0.5 mA-class chargers. That is exactly the 500 µA single-fault limit, with no margin for a charger that does not meet its class. A reinforced barrier, or two independent basic ones, still isolates after one fault.
  - Option (c) needs ≥ 3.45 MΩ per electrode once a finger touches E3. Measured as M2 is defined (input shorted at the AFE pins), this resistor noise does not count against the 10 µVpp target. The real ECG floor still rises from 6.2 to 15.6 µVpp ⚠ (ENG_A §5.2). That damages the study's own question: whether harvesting degrades the biosignals.
  - Option (a') cannot be followed: pass-through power banks and docked laptops are mains-referenced, and the wearer cannot tell ✅/⚠ (V3_ARCH §3.5: the pass-through case from a maker's article ✅, the rest analysis ⚠).
  - The order of risk controls in ISO 14971 puts inherently safe design first ✅ (Johner Institute page via ENG_A §5.3).
- **Residual misuse risk:** a look-alike non-isolated magnetic cable on the contacts while worn gives 250–500 µA ⚠ in normal condition, 2.5–5 times the limit. Q9 (ECG off) does not remove this path, because the electrode TVS diodes go to ground ahead of the 330 kΩ chains ✅ P (V3_ARCH §3.5). Controls:
  - contacts that catalogue magnetic plugs cannot mate: a non-standard pitch, recessed pins, a coded magnet pattern (the prototype head's catalogue pogo plug C5126841 is used off the wrist only);
  - the label "use only the supplied head";
  - V3-G6 models both the shorted barrier of each head type and the look-alike cable.

**1.2 REDESIGN decision 5, how the wearer learns the skin is hot.** Recommend a new option **(d)**. All three judges, ENG_B and UX rank vibration first. The fix stage matched the pattern to the evidence (E-4).
- **Vibration first, in the pattern of the cited study:** repeating 6-s sequences of 0.5-s pulses and 0.5-s pauses, with a 1-s pause between sequences. It runs until a button press and release, or until the skin is below 40 °C, for at most 10 min. That is about 257 s of vibration, 7.9 mWh, 3.6 % of the cell ⚠.
- **Full-screen warning:** it overrides every display-off state (night blank, low battery, ECO), so a visual channel remains when the VBAT ≥ 3.60 V rule blocks the motor.
- **BLE flag:** always.
- **The side LED D10:** stays in the baseline until two things hold: (d) is accepted in writing, and the manufacturer has checked the felt strength and the arousal with the actual motor through the 0.25 mm floor (a sample test). Removing it then frees 14.2 mm² and P0.24 and is gate-1 reserve 1.
- **Evidence, with its limits:**
  - Wrist vibration alarms (Feeltact) produced arousal on 94 % (written time record), 99 % (trunk lift) and 100 % (EEG) of alarms in healthy subjects; 18 were analysed, and 13 of 18 responded on the written record to every alarm. Patient groups: 66 % and 63 % ✅ (UX S38, PMC7783873, read again today).
  - Its vibration intensity is not reported ❓. Its pattern gives about 34 times the vibration of the earlier proposal (3 × 0.5 s every 60 s, up to 5 times).
  - Low-temperature burns occur at 44 °C after 3–4 h and are hard to notice in sleep ✅ (UX S43).
  - The LED is weakest in full sun, when the alarm fires; its visibility at 50 klx is unverified ❓ (ENG_B §4.3).
  - A piezo has no place in the 2.2 mm ring and no sound port ⚠.
  - A BLE flag alone fails for a sleeping wearer.
  - If the Ø8 motor is felt too weakly, the Ø10 sister part is rated 0.75 G minimum ✅ (CLP1020 p.5/13 via ENG_B). It costs utilisation 0.588 / 0.652 ⚠, and its place between the ECG plates is unproven ❓.

**1.3 Protocol items for the study design (not decisions; for the supervisor's protocol).**
- Study mode on both bands; two heads per participant kit; no charging during a session.
  - The W-C band covers a 14-day session even in the worst stack: 15.8 d with the face always on ⚠.
- Water, the same rule as the product: warm showers yes; hot baths, saunas and hot springs no (Xiaomi and HUAWEI exclude hot showers and saunas ✅ UX S31, S32). For swimming, the band is removed and the removal logged, until the 5-bar test passes on production units.
- Worn cable charging only with reinforced (UCC12050) heads, after the rule of §1.1 and the bench test.

---

## 2. Method

- **Safety floor (pass/fail, never traded):**
  - IEC 60601-1 BF patient leakage (100 µA normal condition, 500 µA single fault).
  - Skin ≤ 43 °C (ARCH §1.5).
  - Cell charged only at 0–45 °C.
  - No cell short next to the skin.
  - A configuration that fails is not eligible, whatever its score.
- **Scores:** each judge scored the options 0–10 on experience E, market M, preference P and risk/schedule R (10 = least risk).
  - The lead score is the plain mean of the judges who scored an option.
  - Weighted total = 0.40 E + 0.25 M + 0.20 P + 0.15 R, in the task's order of criteria.
  - S is the strictest safety verdict any judge gave.
  - The scores are entered as data in `calc/baseline_calc.py` §12; the output is `calc/baseline_calc.json` → `decision_scores`.
- **Measurement conventions (added by the fix stage):**
  - Highest point when worn: each item's thickness above the skin where it rests (X-1). The capsule therefore counts at 4.50–4.55 mm, not by its height below the pod top.
  - T1 with the night blank (V3-F's policy) and with the face always on (V3's convention), side by side (E-8).
- **Disagreements** are decided on the evidence in the order of the criteria. Each dissent is recorded in §3 with the reason it was not followed.
- **The costs of each decision** are computed one step at a time from V3-R to V3-F (§4).
- **Verification:** two lenses re-checked this record. The fix stage re-checked every issue at its source, confirmed all 27, and checked whether any winner changes (none does; the D-4 check is in §3.5). Verdicts and changes: `CHANGELOG.md`.

---

## 3. Decision table

Format per item: options with S, mean E / M / P / R and the weighted total; the three judges' choices; evidence by file and section with marks; dissent.

### 3.1 D-1 Where the cell goes

| Option | S | E | M | P | R | Weighted |
|---|---|---|---|---|---|---|
| **Capsule on root A, V3-R pod 40 × 32 mm (chosen)** | COND: V3-G7 (crush, seal, bend), F1 at the cell, O-2 hardware inhibit | 8.33 | 8.00 | 8.67 | 5.33 | **7.87** |
| V3-P: 43 mAh in a 49–52 mm pod | PASS | 5.00 | 5.33 | 5.00 | 6.00 | 5.23 |
| V3-P with 70 mAh (6.30 mm thick or 55 mm long) | PASS | 5.50 | 5.50 | 3.00 | 6.00 | 5.08 |
| Stacked pod at 40 × 32 mm (7.45 mm, or T1 10.1 d) | PASS | 3.33 | 4.00 | 3.00 | 4.00 | 3.53 |
| Volar clasp module | COND | 2.50 | 2.50 | 5.00 | 3.50 | 3.15 |

- **Judges:** all three choose the capsule, with V3-P as the defined fallback if V3-G2 or V3-G7 fails.
  - Consumer adds a rounded far edge and the NTC hardware inhibit.
  - Research adds O-2 closed in hardware.
  - Manufacturing adds a stiff capsule top (so a 30 N press does not reach the cell) and RA copper logged through 10⁵ bends.
  - All of these are adopted. The stiff top is a 0.40 mm strengthened glass (§3.10; the glass-filled PC of the synthesis does not meet the criterion).
- **Evidence:**
  - V3-P length: 49.1 mm, about 52 mm on v1's measure ⚠ (V3_ARCH §4.5).
  - V3-P with the market-needed additions (key, motor): about 53–58 mm ⚠ (research and manufacturing judges, scaling at 28 mm² per mm).
  - 70 mAh in the pod: 6.30 mm or 55.1–55.2 mm ⚠ (ENG_A §3.4).
  - Mainstream bands take 22.5–24.9 mm along the forearm ✅ (UX S31, S32; the orientation is inferred ⚠). The market lane's 33.97–47 mm "length" runs around the wrist (Xiaomi 46.57 × 22.54 mm), so it does not bound the pod's 40 mm (X-5). V3-F's 40 mm is already 1.6–1.8 times a band, which is watch-like; V3-P would be about 2 times.
  - "It broke" is the top reason former users stopped (33.3 %) ✅ (MARKET §5, JMIR 2025).
  - Capsule fit: outer top 2.78 / 2.05 / 1.37 mm below the pod top on 140 / 165 / 200 mm wrists; thickness above the skin at its far end 4.50 / 4.51 / 4.55 mm, the thickest worn item ⚠ (`baseline_calc.json` → `worn_geometry`).
  - Capsule length: the GEB301030 body is ≤ 30.0 mm with 6.0 ± 1 mm tabs ✅ (ENG_A §3.2), so cell, tabs and a flat 4 mm PCM need 39–41 mm against 37.4 mm inside the shell ⚠. The pack RFQ asks for cell + tab joints ≤ 33.4 mm (tabs trimmed before welding); otherwise the capsule grows to about 41 mm (max-material +0.1 g ⚠).
- **Dissent:** none among the judges. The UX lane was neutral (decide on the gates); that rule is kept as the fallback trigger.

### 3.2 D-1 Cell size and supply

| Option | S | E | M | P | R | Weighted |
|---|---|---|---|---|---|---|
| **70 mAh GEB301030 class, bought as a protected pack (chosen)** | PASS | 9.00 | 9.00 | 8.00 | 6.33 | **8.40** |
| LP301230 class (12.5 mm wide, 13.9 mm capsule) | PASS | 7.67 | 8.00 | 7.00 | 6.00 | 7.37 |
| 43 mAh GMB201030 (V3 default) | PASS | 5.67 | 7.00 | 9.00 | 6.67 | 6.82 |

- **Judges:** all three choose 70 mAh, each with additions:
  - Consumer: qualify a second 301030-class source before the design freeze.
  - Research: R_LIM 12 Ω and RISET 10 kΩ only with a large enough cell (BOM interlock and EOL check); NTC C49247682; F1 chosen after its datasheet.
  - Manufacturing: buy a certified protected pack (UN 38.3 summary, IEC 62133-2 report, weighed samples); keep 43 mAh as the documented fallback because its UN 38.3 report is on file ✅ P.
  - All adopted. The fix stage set the interlock at ≥ 66 mAh nominal and ≥ 60 mAh minimum: RISET 10 kΩ gives 27–33 mA, which is 0.45–0.55 C for a 60 mAh-nominal cell and ≤ 0.50 C from 66 mAh ⚠ (FS-1).
- **Evidence:**
  - GEB301030 datasheet ✅ (ENG_A §3.2, URL in ENG_A §10): 70 mAh minimal, 3.0 / 3.5 mm, 1.0 C maximum charge, 0–45 °C charge.
  - T1 38.4 d (34.3 d with the face always on), worst stack 21.9 d (18.7 d), SHELF 257 d (all pass), RAW W-C 26.5 / 15.8 d ⚠ (`baseline_calc.json` → `baseline_V3F.energy`).
  - PV bound at 12 Ω: 0.385 / 0.404 C at −10 / −20 °C ⚠ (full-width strips: an upper bound for the 2.30 mm strips).
  - 12 Ω with a 43 mAh cell would give 0.63 / 0.66 C ⚠ (→ `charge_limits`).
  - Buyers rank battery first (65 %) and complain about it most (21.4 %) ✅ (MARKET §5).
  - Pack route: a UN 38.3 summary is needed to ship any unit ✅ P (redesign/defects.md E-28, via the manufacturing judge); cell tabs must be welded, never soldered ✅ (Markyn spec p.9–10, V3_ARCH §9); JLC/LCSC stock no LiPo cells ✅ (manufacturing judge's query).
  - Thin-cell preference for the RFQ (X-1): ≥ 66 mAh nominal, ≥ 60 mAh minimum, ≤ 2.7 mm new / 3.2 mm at end of life, ≤ 10.5 × 30 mm. It brings the capsule to 4.2 mm (4.20–4.25 mm above the skin) and still passes every target: T1 33.0 d, worst 18.9 d, SHELF 224 d ⚠. No such part has been found ❓.
- **Dissent:** none on the size.
  - The fallback order is set by the lead: (1) a second 70 mAh 10 × 30 mm source; (2) LP301230 class if the 140 mm wrist check passes (it runs 1.94 mm past the tangent point ⚠, ENG_A §3.3); (3) GMB201030 43 mAh with 22 Ω and 18 kΩ, which makes worst-stack T1 and SHELF fail again.

### 3.3 D-2 Display: panel, night light, behaviour, builds before samples

| Option | S | E | M | P | R | Weighted |
|---|---|---|---|---|---|---|
| **LS011B7DH03 + front light designed in, night blank, study mode (chosen)** | PASS | 8.33 | 8.00 | 7.33 | 4.00 | **7.40** |
| No display (V3-N) | PASS | 5.67 | 6.33 | 9.00 | 7.67 | 6.80 |
| LS013B7DH05 1.26" + film, glass-only top | PASS, but cold start 14.1 µA < 21.4 µA | 6.33 | 7.33 | 4.33 | 3.67 | 5.78 |
| LS011B7DH03 unlit (V3-R as published) | PASS | 5.67 | 3.67 | 8.33 | 5.67 | 5.70 |
| E-paper | FAIL: rated 0–50 °C against a 46–47 °C lid | 3.50 | 5.00 | 4.50 | 1.50 | 3.78 |

- **Judges:**
  - **All three:** keep the panel, design the front light in from the first layout, blank the face at night, add study mode.
  - **Fitting the film:** consumer: fit the custom film; research: fit it once qualified, research units may ship unlit; manufacturing: fitted when sourced, required for the consumer release.
  - **Build before panel samples:** consumer and research: a V3-N full-PV lid; manufacturing: one top design for every build, with the window masked.
- **Chosen:**
  - The front light is designed in, fitted when qualified, and required for the consumer release.
  - **One top design for every build.**
  - The front light sits above the panel (E-10). Either Sharp's approved partner laminates the film to the panel front, as on Azumo's 1.28" module ✅ (AZ_11049 p.1: "designed to laminate to the front of Sharp LS013B7DH03"; Azumo is a "Sharp Approved Value-Added Partner"), or the film is laminated under the window glass. The panel keeps V3-R's 0.10 mm support underneath. The film plus adhesive is limited to ≤ 0.25 mm in the RFQ.
  - No phone notifications at launch: fewer distractions and no light or buzzing in bed are the reasons people give for screenless bands ✅ (UX S28). Study mode does not need them. A later consumer option, off by default (X-9).
  - A silent vibration wake alarm in consumer mode (§3.7).
- **Evidence:**
  - The panel transmits 0.2 % ✅ (LD-29Y03 p.13 / p.33 via ENG_B §2.1).
  - The 2014 vívofit was criticised because its display could not be read in the dark ✅; a backlight came in the next model ✅s (search summary; MARKET §2.2, §9).
  - Every consumer reflective display checked has a light ✅/✅s (MARKET §9).
  - One reviewer of a screenless band asked for a basic clock ✅ (9to5Google via MARKET §7).
  - AMOLED always-on costs 60–65 % of battery life ✅ (UX S32, S48).
  - Larger panels drop the cold start to 14.1 µA ⚠ (ENG_B §2.2).
  - Supply: Digi-Key 1,600 at USD 8.008, 28 weeks ✅; LCSC 0 ✅; no 1.08" film in Azumo's list ✅ (ENG_B §2.4–2.5).
  - Cost in the waterfall (§4): the front light alone (hardware, face still always on) takes T1 38.4 → 35.6 d; the night blank (firmware) takes it to 40.0 d ⚠. The window half grows 4.65 → 4.90 mm with the film (→ 5.10 mm with the 5 ATM window glass).
- **Dissent (consumer, research: a V3-N lid for builds without the panel). Chosen against, because:**
  1. Real experience is the same: neither build has a display.
  2. At 70 mAh the energy difference is small and both stay far beyond the market's 7–14 d ⚠:
     - indoor-only W2: 45.1 d (masked window) vs 47.6 d (V3-N lid);
     - winter office W7: 52.5 vs 61.6 d.
  3. One lid halves the lid NRE and MOQ (custom PV panel makers quote MOQ 500–3,000 ✅, build lens B-06 via the manufacturing judge).
  4. One lid avoids V3-N's own thermal fix (+0.41 K over V2-B ⚠, V3_ARCH §7.1). The masked window gets a mask of α ≤ 0.6 and its own SIM-13 case (E-12).
  5. Research units then carry the same PV area as the product, so the harvest data transfer.
  - The consumer judge's fallback "same panel unlit, said plainly" stays valid for research units.

### 3.4 D-3 Worn-charging rule (recommendation for the supervisor)

| Option | S | E | M | P | R | Weighted |
|---|---|---|---|---|---|---|
| **(b) now; target: reinforced isolated head or pack only, ECG off with VBUS (recommended)** | PASS (by design with a reinforced barrier; bench test pending) | 8.33 | 8.00 | 9.00 | 6.33 | **8.08** |
| (b) for good | PASS | 6.00 | 7.33 | 9.00 | 9.00 | 7.38 |
| (a') power bank only | **FAIL**: cannot be enforced | 6.33 | 4.67 | 9.33 | 3.67 | not eligible |
| (c) ≥ 3.45 MΩ ahead of every clamp | COND: ECG noise above M2 at the electrodes | 6.00 | 6.00 | 6.00 | 3.00 | 5.55 |

- **Judges:** unanimous for the first row; (c) and (a') are rejected.
- **Fix stage (E-1):** the judges scored a head with "basic or reinforced" isolation. A basic barrier passes only up to its first fault (500 µA, exactly the limit). So the recommended rule now names reinforced isolation, and basic-isolation heads are off-the-wrist only. The row's S verdict holds only with that wording.
- **Evidence:** §1.1.
- **Dissent:** none. The UX lane's clip-on *light* pack (charging through the PV) is not taken. The judges scored it E 3–4, because it takes hours per fill at under 1 sun and heats the lid ⚠.

### 3.5 D-4 Charging connector

| Option | S | E | M | P | R | Weighted |
|---|---|---|---|---|---|---|
| **Two flush contacts + isolated USB-C head (chosen)** | PASS | 7.67 | 8.00 | 9.33 | 6.00 | **7.83** |
| Contacts + clip-on pack now | PASS | 8.00 | 7.00 | 9.50 | 4.50 | 7.53 |
| (a) USB-C tab on root A (V3 default) | COND (off the wrist only) | 6.00 | 6.00 | 6.00 | 4.00 | 5.70 |
| Tab and contacts | COND | 5.67 | 5.33 | 5.00 | 3.00 | 5.05 |
| Sealed receptacle in the pod end | COND | 4.33 | 5.67 | 6.00 | 3.33 | 4.85 |

- **Judges:** all three choose contacts + head, with the pack later.
  - Consumer: keyring head, spares, a pin-impedance check in the head before 5 V is applied.
  - Research: two heads per study kit; gold over a nickel-free layer (EN 1811).
  - Manufacturing: prefer two rectangular top glasses over one notched glass.
  - All adopted.
- **Re-check of the scores (X-1):** all three judges used the premise that the tab was the highest worn point. It is not: on the same measure the 70 mAh capsule stands 4.50–4.55 mm off the skin against the tab's 4.6 mm. With the contacts' E lowered by 2 points and the tab's raised by 2, the totals are 7.03 and 6.50 ⚠ (`decision_scores` → `d4_height_premise_sensitivity`). The choice stands. Under a strict experience-first order, "contacts + clip-on pack now" (E 8.00, scored by two judges) would lead; it stays a later accessory because its R is 4.50 and nothing in it is designed.
- **Evidence:**
  - Position: the tab sits at or just past the ulnar edge (s 23.5–35.5 mm), where desks, mattresses and cuffs press (UX §5.3, a geometric inference ⚠). Without it, root A ends at s 16 mm and the 9.6 mm flex hinge is gone.
  - Height: no gain. Capsule 4.50–4.55 mm, tab 4.6 mm, pod window half 4.30 mm ⚠ (§2 convention).
  - An open receptacle caps the band at catalogue IPX7–IPX8 (1–1.5 m) ✅/⚠ (ENG_A §6.2). No documented receptacle reaches 5 bar, so the UX lane's own condition for the tab ("receptacle sealed to the band's rating", UX §4.5) cannot be met. 15 of 15 consumer bands are swim-rated ✅ (MARKET §2.3). The contacts reach 5 ATM only with the supported rib of §3.9 (E-5), and are claimed at IP68 1.5 m until the 5-bar test.
  - 0 of 23 cable-charged products have a USB-C receptacle on the device ✅ (MARKET §6.1).
  - The EU directive does not cover wristbands today ✅. Wristbands are named as a candidate (30 Jun 2026), with no proposal or date ✅ (MARKET §6.2).
  - Contacts take VBUS and the flex hinge out of the strap and save 1.2 g ⚠ (§4, step 2).
  - Counter-evidence weighed: reviewers praised Huawei Band 4's built-in USB plug ✅ (Tech Advisor, 16 Dec 2019, https://www.techadvisor.com/article/720979/huawei-band-4-review.html, read by the consumer judge). Huawei's current Band 10 charges magnetically ✅ (MARKET §2.3).
  - Reviewers expect a small proprietary charger to be lost (S16) and list a new proprietary cable as a con (S12) ✅. Hence the keyring head, spares and two heads per study kit.
  - Without the head only daylight helps: about 10 min of sun, 22 min at 0.2 sun or 44 min overcast per day of use ⚠. Room light (200–1,000 lx: 18.8–192.8 µW) stays below the 238.8–257.6 µW load, so it only restarts a flat band (167–358 lx) ⚠ (`fix_stage_numbers` → `rescue_without_head`).
- **Dissent:**
  - **The UX lane chose the tab** (any cable, nothing to carry). Not followed:
    - it cannot meet the swim-rating norm (no 5-bar receptacle);
    - it makes worn charging depend on a rule instead of on the design;
    - it puts a rigid part at the ulnar edge 24/7 for a port used about once in 41 days.
    - What is given up is real: an indoor-only wearer who forgets the head has no indoor rescue.
  - **Path if the EU later covers wristbands.** Consumer: keep the V3 tab drawing. Manufacturing: the sealed pod-end receptacle. **Chosen: the pod-end receptacle**, because it keeps VBUS out of the strap (no VBUS–BATT_P short beside the skin) and adds no second flex hinge. Its cost (+0.46 mm boss, utilisation 0.587 on the V3-R base, lid strips −18 %) is paid only if the rule comes.

### 3.6 Interaction

| Option | S | E | M | P | R | Weighted |
|---|---|---|---|---|---|---|
| **Sealed side button + raise (consumer mode, sleep-locked) + gated double tap (chosen)** | PASS | 8.33 | 8.67 | 8.00 | 6.00 | **8.00** |
| E3 as a push key | COND (electrode isolation) | 8.33 | 7.67 | 9.00 | 3.33 | 7.55 |
| Raise-to-wake only (V3) | PASS | 4.00 | 3.33 | 10.00 | 9.00 | 5.78 |
| Capacitive touch | PASS | 3.67 | 5.33 | 8.33 | 4.33 | 5.12 |

- **Judges:** all three choose the button, raise-to-wake and the gated tap.
  - Consumer and research add a ship-wake path from the button. Manufacturing does not: it saves 9.3 mm² and one polar diode.
  - Research: in study mode the button is the only input while the face is blank.
  - Manufacturing: a membrane seal, so the wall seal stays static.
- **Chosen:** all of these, including the ship-wake path.
  - The lead merges the old VBUS wake diode D12 (BAS521, SOD-523, placement class P) and the button's wake diode into one **BAV70M,315** common-cathode pair, SOT-883 (C549313, 1,481 in stock ✅ JLC API 16:41 UTC).
  - The merged pair saves 0.001 of utilisation (0.565 with the path, 0.566 without it ⚠).
  - It removes a class-P part, pending `placement_proof.py`.
  - Fix-stage firmware rules: in the sleep window a press must last ≥ 1 s to wake the face and the light (X-10); a press held longer than 5 s is treated as stuck (for example, water pressure on the membrane at depth), logged and ignored, and it never acknowledges a safety alarm (E-12).
- **Evidence:**
  - Fitbit restored the button on Charge 6 ✅ (UX S22).
  - Double tap is unreliable ✅ (MARKET §7); touch fails in water ✅ (UX S54).
  - Event marking: Empatica E4 manual p.25 ✅ and LEAP 510(k) ✅ (ENG_B §3).
  - An always-on tap costs 18.6–193.6 µW ⚠, the gated tap 0.67 µW ⚠, about −0.1 d of T1 (LIS2DW12 Table 11 ✅).
  - At 5 bar a 3 × 3 mm membrane carries about 4.5 N ⚠ against the PTS840's 2.2 N operating force ✅ (JLC attributes 18:24 UTC).
- **Dissent:**
  - Manufacturing's "no ship-wake path": its two reasons (area, polar diode) are removed by the merged pair.
  - The UX lane's "E3 as a push key": kept as a study item for a later revision, because a moving seal on the ECG electrode is unproven (R 3–4 from all judges).
  - The UX lane's "drop raise-to-wake": not followed, because the front light makes a raise at night useful; raise-to-wake is locked in the sleep window instead.

### 3.7 Alerts and decision 5 (recommendation for the supervisor)

| Option | S | E | M | P | R | Weighted |
|---|---|---|---|---|---|---|
| **(d) Ø8 low-current ERM first + full-screen warning + BLE (LED kept until (d) is in writing and the felt strength is checked) (chosen hardware; recommended rule)** | PASS | 8.67 | 8.67 | 8.00 | 5.67 | **8.09** |
| LRA + driver | PASS, but does not fit the 2.40 mm column | 8.67 | 9.00 | 4.67 | 3.33 | 7.15 |
| (b) side LED only (V3 default) | COND: unseen in sun or sleep | 3.00 | 2.67 | 10.00 | 8.33 | 5.12 |
| (c) BLE flag only | **FAIL** for a sleeping wearer | 2.00 | 2.00 | 10.00 | 8.50 | not eligible |

- **Judges:** all three choose the Ø8 ERM and (d).
  - On the LED: consumer keeps it if gate 1 has room; research keeps it until (d) is accepted; manufacturing removes it now.
- **Chosen:**
  - The LED stays until the supervisor accepts (d) in writing and the manufacturer has checked the felt strength and arousal with the actual motor (E-4). The V3 rule (RQ-08) says the LED may go only with the supervisor's written decision.
  - The skin-hot pattern follows the cited study (§1.2).
  - A silent vibration wake alarm in consumer mode, inside the 4.7 s/day motor budget (X-9). Vibration alarms are standard in Fitbit Air, Helio Strap, Index, CIRQA and WHOOP ✅ (MARKET §2.2, §9); Polar Loop launched without a wake alarm and its reviewer noted it ✅ (UX S10).
  - The motor's planning position moves between the ECG plates (X 20, Y 25.4 mm) and the root-A entry lands move to the elbow end (X 4.5–10.5 mm), because the synthesis position (X 27) sat on plate E2 (E-11). It has no slack in Y between the rib posts and the board's edge band; V3-G9 places both together.
- **Evidence:**
  - VCLP0820B004L is Ø8 × 2.1 mm at 30 / 35 mA, 0.25 Grms ✅ (ENG_B §4.1).
  - The LRA C08-005 is 3.3 mm tall and draws 75 mA ✅.
  - A standard 100 mA ERM exceeds the ±81.92 mA INA_BAT range ⚠.
  - Market and sleep evidence: §1.2.
  - Cost of the motor at 70 mAh: about 6 µW a day, T1 40.0 → 38.9 d (−1.1 d; the linear estimate is −0.97 d) ⚠ (E-9).
  - Floor at 5 bar: the 0.25 mm PC film over the 8.6 mm cut-out would push the bonded motor up by 0.77 mm if unsupported, against 0.15 mm to the lid ⚠. A 0.25 mm Ti disc in the floor under the motor deflects 0.017 mm and adds 0.05 g ⚠; V3-G7 decides.
- **Dissent:**
  - Manufacturing (remove the LED now): deferred to the supervisor and to the felt-strength check; removal is the first gate-1 reserve.
  - The UX lane's LRA in the USB tab: not possible, because the tab is gone and an LRA is 3.3 mm tall.
  - Manufacturing's "motor also below 3.60 V while PV supplies it": made a V3-G4 check item, not a rule yet.

### 3.8 T6 storage

| Option | S | E | M | P | R | Weighted |
|---|---|---|---|---|---|---|
| **SHELF claim; ship mode for transport, woken by the button, the head or light (chosen)** | PASS | 8.67 | 7.67 | 9.00 | 6.67 | **8.19** |
| SHELF claim; ship mode woken by the head or light only | PASS | 8.00 | 7.00 | 9.00 | 8.00 | 7.95 |
| Ship-mode claim (V3 default) | PASS | 5.33 | 5.67 | 9.33 | 7.33 | 6.52 |

- **Judges:** all three claim T6 in SHELF.
- **Chosen:** wake by the button (consumer, research), plus manufacturing's shipping rule: ship at ≤ 30 % SoC by air (IATA PI 967 recommendation ✅ P, redesign/defects.md E-03), 30–50 % otherwise; recharge stock older than 3 months.
- **Numbers:** SHELF 257 d ✓ (276 d before the 2.5 µW O-2 inhibit) ⚠. Ship mode 411 d from full; at 30 % SoC about 123 d ⚠ (manufacturing judge).
- **Dissent:** manufacturing's "no button wake". Not followed; see §3.6.

### 3.9 Water rating

| Option | S | E | M | P | R | Weighted |
|---|---|---|---|---|---|---|
| **Product 5 ATM (ISO 22810); claim IP68 1.5 m until the 5-bar test; every unit leak-tested (chosen)** | PASS | 8.67 | 9.00 | 7.33 | 5.00 | **7.93** |
| 10 ATM | PASS | 8.50 | 8.00 | 5.00 | 2.50 | 6.78 |
| IP67 | PASS | 5.67 | 4.67 | 9.33 | 7.67 | 6.45 |

- **Judges:** all three choose 5 ATM for the product and IP68 1.5 m for the first builds.
  - Research: first builds "with the lid as drawn". Manufacturing: "design for 5 ATM now".
- **Chosen:** design for 5 ATM now, with a load path that the fix stage checked (E-5):
  - two glasses: the PV laminate (0.50 mm glass) and a 0.70 mm window glass on a rigid (structural) bond to a stainless frame;
  - between them a ring rib at Y 20.0–21.0 mm beside the panel (which ends at Y 20.0), with a 0.5 × 0.7 mm stainless insert and 6 posts to the board at a pitch of ≤ 6 mm;
  - the PV laminate edge therefore moves from Y 20.2 to Y 21.0, and the four strips narrow from 2.50 to 2.30 mm (lid silicon 2.77 → 2.55 cm², −8 %) ⚠;
  - claims: IP68 1.5 m until a 5-bar test passes on production units, then 5 ATM. Warm showers yes; hot baths, saunas, hot springs and diving no (X-12).
- **Why the synthesis top did not work (E-5, confirmed):** its web lay over the panel's inactive border (Y 19.6–20.1). There it could be no deeper than the 0.10 mm air gap, and only 0.1 mm of it lay beside the panel, so no post fitted. At 5 bar the web carries about 6.5 N/mm, 214 N over 33 mm; as a free 33 mm beam a 0.5 × 0.7 mm PC rib would deflect about 3,050 mm and a stainless one 36 mm (engineering lens, `verify_work/engineering/checks/check_mech.json`). Each glass was then in effect free at the web: it touches what lies below at 0.35 bar (PV glass) and 0.32 bar (window) ⚠ (Levy series, engineering lens, validated against Navier). 5 ATM failed by about 15 times; IP68 1.5 m held (0.05–0.06 mm of deflection at 0.15 bar).
- **Evidence (Navier plate with the supported rib, simply supported upper bound / clamped about ×3.2 ⚠, `baseline_calc.json` → `water_pressure`):**

| Element | Touches what lies below at | Passes 5 bar? |
|---|---|---|
| PV laminate glass 0.50 mm between the ring and the rib (28.7 × 10.6 mm) | 7.7 bar (24.8 clamped) | yes |
| 0.70 mm window glass over 33 × 14.5 mm | 4.3 bar simply supported, about 14 clamped | only with the rigid bond |
| 0.80 mm window glass (if the bond is elastic) | 6.5 bar simply supported | yes (+0.10 mm on the window half) |
| Stainless rib insert between posts 6 mm apart | 0.038 mm at 5 bar | yes (posts ≤ 6.4 mm apart for 0.05 mm) |
| V3's single lid glass over the window | 0.15 bar | no |

  - With an elastic bond (G-14), the window needs ≥ 0.73 mm for 5 bar, 0.84 mm for a 1.5 × margin ⚠. SIM-14 decides between the rigid bond and the 0.80 mm glass.
  - Market and research evidence: 15 of 15 consumer bands are swim-rated ✅ (MARKET §2.3); participants forgot to put watches back on after swimming ✅ (UX S46).
- **Dissent:** research (first builds with the lid as drawn). Not followed. One lid design avoids re-validating the lid and makes research data transfer to the product. The cost is 0.20 mm on the window half at the RFQ target, 8 % of the lid silicon, 6 mm² of post keep-outs and 0.12 g for the rib.
  - **Option 2 (cost recovery):** if Sharp states in writing a pressure limit for the panel border that the rib may bear on, the posts go and the strips return to 2.50 mm (T3 10.9 min, W2 40.7 d, utilisation 0.561 / 0.621 ⚠).
  - If SIM-14 shows the 33 mm stainless insert hurts the antenna (it is close to λ0/4 = 30.7 mm), it is grounded at the posts or split.

### 3.10 Remaining V3 defaults (V3_ARCH §12)

| Default | Decision | Judges |
|---|---|---|
| R131 / R108 at 10 MΩ | keep | all |
| No diode on the wing | keep; the manual says a flat band off the wrist needs the head or daylight (room light only restarts it above about 360 lx with the wing dark) ⚠ | all |
| Display FPC soldered on a keyed land | keep (hot-bar at the manufacturer) | all |
| Wing at full length until SIM-13 | keep, **as a hard gate before any human wear**; if SIM-13 cannot show skin ≤ 43 °C, ship the shortened wing (active area to s ≈ 8–10 mm; T3 up to +2 min ⚠) | research's wording, the others agree |
| 43 mAh | → 70 mAh (§3.2) | all |
| R_LIM 22 Ω, RISET 18 kΩ | → 12 Ω (C17913) and 10 kΩ (C25744), locked to a pack of ≥ 66 mAh nominal, ≥ 60 mAh minimum | all (threshold: fix stage, FS-1) |
| T6 in ship mode | → SHELF (§3.8) | all |
| Wing radial on a left-wrist band | → either wrist, turned 180° with a firmware flip | all (UX too) |

**Safety-floor additions (all three judges; detail added by the fix stage):**
- **O-2: a hardware PV-charge inhibit from the cell NTC** (V3_ARCH RQ-17). It must work with the MCU off and in every battery state, including a deeply discharged or PCM-tripped cell (E-2):
  - below about 1.2 V the PV drives 0.71–0.89 C into the cell through the BQ25570 body diodes ⚠, and the comparators need ≥ 1.6 V (TLV7031) or ≥ 0.9 V (TLV3691) ✅ (JLC listings), so they and the Q1 gate drive are supplied from the PV node or VSTOR, never from VBAT alone;
  - the O-2 ladder on the NTC node is biased only while PV is lit and VBUS is absent, so it does not shift the BQ25170 TS window (1.9–44.8 °C, computed with the TS bias alone) or the MCU reading;
  - preferred in the pack PCM as a charge-temperature cut-off, if the pack maker states the cell voltage down to which it works; otherwise 12 mm² on the board (comparator candidates TLV7031DCKR C2863637 / TLV7031DPWR C2876045 / TLV3691IDCKR C180352 ✅ JLC 16:40 UTC). Its circuit is designed in V3-G4.
- **The stiff capsule top (E-3):** 0.40 mm chemically strengthened glass with the white print underneath (protected, α ≤ 0.15 for life), set flush in the PC rim so no glass edge is exposed. Under 30 N it deflects 0.03 mm spread, 0.07 mm on a 15 mm thumb patch and 0.15 mm on a 5 mm probe, against the 0.20 mm gap at end of life ⚠. Glass-filled PC (0.35 / 0.69 / 1.72 mm) and 0.15 mm stainless (0.22 / 0.43 / 1.01 mm) fail. Net +0.24 g. Fallback if the glass fails V3-G7's drop and impact case: a 0.20 mm 316L lid (+0.50 g; it passes the spread and thumb loads but not a 5 mm probe, 0.43 mm).
- No VBUS in the strap.
- F1 in the pack.

---

## 4. Cost of each decision (V3-R → V3-F, one step at a time; all ⚠, `baseline_calc.json` → `waterfall_V3R_to_V3F`)

| Step | Pod mm (window half, RFQ lid) | Highest worn item, mm | Worn g typ / max | Util. / v1 measure | T1 d: night blank / face on | Worst d: night blank / face on | T3 min | W2 d | W7 d | SHELF d |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 V3-R as published | 4.65 | 4.6 (tab) | 19.1 / 20.2 | 0.486 / 0.538 | 21.6 / 21.6 | 11.5 / 11.5 | 12.5 | 23.2 | 26.9 | 174 |
| 1 70 mAh pack, R_LIM 12 Ω, RISET 10 kΩ | 4.65 | 4.6 (tab) | 19.3 / 20.7 | 0.486 / 0.538 | 38.4 / 38.4 | 19.9 / 19.9 | 10.1 | 41.3 | 47.6 | 276 |
| 2 contacts + isolated head, no tab | 4.65 | 4.55 (capsule) | 18.1 / 19.2 | 0.495 / 0.548 | 38.4 / 38.4 | 19.9 / 19.9 | 10.1 | 41.3 | 47.6 | 276 |
| 3a front light designed in (hardware; film above the panel; face still always on) | 4.90 | 4.55 | 18.2 / 19.3 | 0.502 / 0.557 | 35.6 / 35.6 | 19.1 / 19.1 | 10.5 | 39.6 | 45.3 | 276 |
| 3b night blank after 30 min without light (firmware) | 4.90 | 4.55 | 18.2 / 19.3 | 0.502 / 0.557 | 40.0 / 35.6 | 22.4 / 19.1 | 10.5 | 42.5 | 48.0 | 276 |
| 4 Ø8 ERM in a board cut-out | 4.90 | 4.55 | 18.5 / 19.6 | 0.554 / 0.613 | 38.9 / 34.7 | 22.1 / 18.8 | 10.8 | 41.3 | 46.5 | 276 |
| 5 side button (+ ship wake, BAV70M) + gated tap | 4.90 | 4.55 | 18.6 / 19.8 | 0.575 / 0.637 | 38.8 / 34.6 | 22.0 / 18.8 | 10.8 | 41.2 | 46.3 | 276 |
| 6 O-2 hardware inhibit reserved on the board | 4.90 | 4.55 | 18.6 / 19.8 | 0.590 / 0.653 | 38.4 / 34.3 | 21.9 / 18.7 | 10.9 | 40.7 | 45.8 | 257 |
| 7 5 ATM load path (two glasses, 0.70 mm window, stainless rib + 6 posts, strips 2.30 mm), glass capsule top, band quick release | 5.10 | 4.55 | 19.3 / 21.0 | 0.594 / 0.658 | 38.4 / 34.3 | 21.9 / 18.7 | 11.2 | 40.6 | 45.4 | 257 |
| 8 0201 passives where the project has the part = **V3-F** | **5.10** | **4.55** | **19.3 / 21.0** | **0.565 / 0.626 ✗** | **38.4 / 34.3** | **21.9 / 18.7** | **11.2** | **40.6** | **45.4** | **257** |

Notes:
- T1 "night blank" is the dark test with the 30-min night blank and the front light on every one of 100 raises a day. "Face on" is V3's convention, the face always on. Step 3b is a firmware policy, not hardware (E-8).
- Highest worn item: each item's thickness above the skin where it rests. The capsule is 4.50–4.55 mm on 140–200 mm wrists. The pod's window half is 4.30 mm at steps 7–8 (4.10 mm at steps 3a–6); the PV half is 3.85 mm, or 4.32–4.62 mm with the verified P121 lid build-up.
- W2 (indoor-only) and W7 (winter office) are days from full in the SIM-05-style weeks, with the face on only while lit.
- The pod is 5.12–5.42 mm with the verified P121 lid build-up, at every step (the PV column governs there).
- **Gate 1:** on REDESIGN's metric V3-F passes with 0.565 (limit 0.62). On v1's bounding-box measure it fails: 0.626 (455.4 / 806.3 × 1.108) ✗, by 0.006 (E-7). The ordered reserves (`variants`):
  1. LED chain removed, only once the supervisor accepts (d) in writing and the felt-strength check has passed: 0.548 / 0.607.
  2. Pod and board 1 mm longer (41 × 32 mm, +0.2 g): 0.546 / 0.605. The only reserve that needs nobody's answer.
  3. O-2 cut-off in the pack PCM, if the pack RFQ confirms one: 0.550 / 0.609.
  - V3-G1's legal placement decides. Until it passes both measures at 40 mm, the lid and ring RFQs are drawn at 41 × 32 mm.

---

## 5. Extra changes

| Change | Support | Adopted? | Cost |
|---|---|---|---|
| Either-wrist wear (turn 180°, flip the face, remap the IMU, record the wrist) | all three judges + UX | **yes (1 of 3)** | 0 g, 0 mm², firmware + V3-G9 CAD |
| Replaceable outer band in two lengths (together about 130–210 mm), quick-drying, tool-free quick release at the root ends | all three + UX | **yes (2 of 3)** | +0.1 g typ / +0.3 g max ⚠; a second band SKU. The 130 mm wrist was computed: the capsule ends 0.23 mm past the tangent point and still rests on the skin (gap 0.002 mm) ⚠ (X-13) |
| Plain energy status ("days left at your current light", "today's light against need", from the measured harvest), warning ≥ 24 h before empty (target 3 d), solar claim stated with its condition | consumer, manufacturing, UX | **yes (3 of 3)** | firmware and app only |
| Study mode with data integrity: researcher-locked, identical faces, logging; no record deleted before the gateway acknowledges it; old records reduced to summaries when the ring fills | research (extra); study mode in all three judges' D-2 | folded into D-2 and D-3 (firmware rule, strong evidence, zero cost: in the KOALAP study the watch stopped collecting data when its upload during charging failed ✅ JMIR mHealth 2020;8(1):e14368, UX S46) | 0 |
| Battery bought as a certified protected pack | manufacturing | folded into D-1 (strong evidence: UN 38.3 needed to ship ✅ P; weld-only tabs ✅; no LiPo at JLC ✅; small cost: 0 mm, about 0 g) | pack-maker NRE / MOQ ❓ |
| Silent vibration wake alarm (consumer mode) | market evidence (X-9) | folded into alerts (§3.7): existing motor, inside the 4.7 s/day budget | 0 |
| Clip-on isolated pack now | ENG_A option | no: later accessory (all judges) | – |
| E3 as a push key | UX | no: later revision study item | – |
| Clip-on light pack charging through the PV | UX idea | no (scored E 3–4, M 3) | – |
| LRA haptics | UX | no: does not fit 2.40 mm, clips INA_BAT | – |

---

## 6. The user's four asks: status

| Ask (2026-11-13) | Answer | How in V3-F | What changed against V3-R, in plain words |
|---|---|---|---|
| 1. Flexible PV on the strap | **kept as asked (rigid, as in V3)** | c-Si wing on root B's free span, 3.35 cm², no diode. It is rigid, because no flexible PV fits the wrist and the sun: a-Si is rated 25.4 / 76.2 mm bend radius against a 12–20 mm wrist ✅ (strap lane via V3_ARCH §1); flexible CIGS has no small-quantity route ❓ | the wing stays radial on either wrist; full length only after SIM-13 shows skin ≤ 43 °C |
| 2. Use it without taking it off | **kept, with conditions** | light charges while worn (isolated from the body). With ≥ 20 min a day of direct sun (about 50 klx) on an uncovered face and wing it never needs charging (W1, W4, W6 energy-positive, lowest SoC 0.49 ⚠). Overcast days need about 48 min; a sleeve over the wing needs about 25 min of sun ⚠. Indoors only: top up every 40.6 d ⚠, 1.4–1.7 h off the wrist per 30 d ⚠ | worn cable charging only through a reinforced head, once the supervisor agrees and the bench test passes |
| 3. Emergency charging through USB-C | **changed: through the head only** | any USB-C cable, charger, power bank, laptop or phone through the head; also worn, after the supervisor's rule | the band has no receptacle (reasons in §3.5: position, swim rating, safety by design, market practice). Without the head only daylight helps: about 10 min of sun or 45 min overcast per day of use; room light only restarts a flat band ⚠ |
| 4. A display | **kept; night reading conditional** | LS011B7DH03 with a front light above the panel; night blank; study mode | readable at night once the custom 1.08" film exists (V3-R was not readable at night); research units may ship unlit |

---

## 7. Risks that remain (in the order they could stop V3-F)

1. **Display supply, two steps.**
   - Sharp samples ✅ (1,600 MOQ, 28 weeks; storage ≤ 3 months).
   - A custom 1.08" film (NRE and MOQ ❓), laminated on the panel front by Sharp's approved partner, or on the window glass (optics ❓).
   - Fallback: the same lid and board without the panel, then the unlit panel.
2. **The 5 ATM load path (E-5).** The rib, its posts and the rigid window bond are planning designs ⚠; the panel's pressure tolerance is ❓; the 33 mm stainless insert near λ0/4 is an RF item. Until SIM-14 and the 5-bar test pass, the claim is IP68 1.5 m.
3. **The strap capsule.**
   - Crush with a soft short beside the skin, the seal, the shell and glass-top supplier ❓, no FPC overmoulder found ❓ (fallback: a potted slot), the white print at α ≤ 0.15 for life (under glass now).
   - It is the thickest worn item (4.5 mm); the thin-cell RFQ preference could make it 4.2 mm.
   - The cell's tab length must be trimmed (≤ 33.4 mm with the joints) or the capsule grows to about 41 mm.
   - Fallback: V3-P.
4. **Gate 1 and the board layout.** 0.565 on the project metric; 0.626 ✗ on v1's measure. The motor's planning position has no slack in Y between the rib posts and the board edge, and needs the root-A entry lands moved. Ordered reserves in §4; the RFQs are drawn at 41 × 32 mm until V3-G1 passes at 40 mm.
5. **The skin under the wing.** 44.2–45.4 °C under the outer sub-cells in the 1-D bound, against 43.8 °C for bare skin ⚠ (V3_ARCH §7.2). A hard gate before human wear; the shortened wing is pre-costed.
6. **The isolated head.** Reinforced isolator stock 0 ✅ (consigned); heat on the pod top (90–165 mW ⚠) and at no load ❓; barrier capacitance ❓; look-alike non-isolated cables (contacts made non-mateable); not designed yet (V3-G10).
7. **O-2 inhibit.** Not designed yet (V3-G4); its supply in a deeply discharged or tripped state, and its sharing of the NTC node, are now requirements. A PCM with a charge-temperature cut-off ❓.
8. **Haptics.** Felt strength through the 0.25 mm floor ❓ (the Ø10 fallback may not fit between the plates ❓); 0.15 mm height margin ⚠; the floor film over the cut-out at 5 bar ⚠.
9. **The 70 mAh cell.** Mass ("approx 3 g" ❓ → worn 20.9 g), a single source ❓, UN 38.3 for the pack ❓, T7 cold corner 3.1 h in a conservative model ⚠.
10. **Carried from V3.** The lid ≤ 1.20 mm, the shunt of narrow IBC pieces (F9; the 2.30 mm strips have slightly more cut edge per area), chip-antenna efficiency, the dark wing off the wrist (358 lx needed ⚠).

---

## 8. Files

| File | Content |
|---|---|
| `v3/decide/DECISIONS.md` | this file |
| `v3/decide/BASELINE.md` | full specification of V3-F for the next phase |
| `v3/decide/CHANGELOG.md` | the fix stage: every issue, its verdict, the change, before → after |
| `v3/decide/verify/engineering.md`, `verify/experience.md` | the two lens returns, saved verbatim |
| `v3/decide/verify/PROGRESS.md` | fix-stage progress, runs and integrity checks |
| `v3/decide/PROGRESS_SYNTH.md` | synthesis progress, run commands and exit codes |
| `v3/decide/calc/baseline_calc.py`, `baseline_calc.json`, `baseline_calc_run.log` | every number of BASELINE.md and the costs and scores here (fix-stage version) |
| `v3/decide/calc/pre_fix/` | the synthesis version of the script, its JSON and log, unchanged |
| `v3/decide/calc/v3_calc_copy.py`, `v3_calc_copy.json` | guarded copy of `v3/integrate/v3_calc.py` (three lines changed, marked DECIDE COPY) |
| `v3/decide/calc/pv_tables_R12.json`, `pv_tables_R12_w230.json`, `pv_tables_R12_w240.json`, `pv_tables_R22_w230.json` | PV posture tables of the V3-F PV set at R_LIM 12 Ω (full and narrowed strips) and at 22 Ω (narrowed, conservative check) |
| `v3/decide/calc/tools/jlc.py`, `calc/data/jlc_search.json` | JLC query tool (copy) and the fields read by the synthesis |
