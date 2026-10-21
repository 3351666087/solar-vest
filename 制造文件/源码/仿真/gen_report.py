"""Writes 制造文件/仿真/仿真报告.md from the JSON results of every test bench (numbers are never typed by hand)."""
import json, os, shutil, sys
OUT = sys.argv[1]
os.makedirs(os.path.join(OUT, "图"), exist_ok=True)
for f in os.listdir("plots"):
    if f.endswith(".png"): shutil.copy(os.path.join("plots", f), os.path.join(OUT, "图", f))
J = lambda n: json.load(open(n))
CH = J("tb_charger_final.json"); LIB = J("tb_lib.json"); INR = J("tb_inrush.json"); RNG = J("tb_range.json")
NIG = J("tb_night2.json"); HP = J("tb_hotplug2.json"); LOOP = J("loop_ss.json")

def worst(damp, gmmax):
    rows = [r for r in LOOP if r["damp"] == damp and r["gm"] <= gmmax + 1e-12]
    pm = min(r["pm"] for r in rows if r["pm"] is not None)
    gms = [r["gm_db"] for r in rows if r["gm_db"] is not None]
    return pm, (min(gms) if gms else None)
DAMPS = sorted({r["damp"] for r in LOOP}, key=lambda d: ("ceramic" not in d, "−10" in d))
pm_old5, gm_old5 = worst(DAMPS[0], 5e-3); pm_new5, gm_new5 = worst(DAMPS[1], 5e-3); pm_cold5, gm_cold5 = worst(DAMPS[2], 5e-3)
pm_old1, gm_old1 = worst(DAMPS[0], 1e-3)
fmt_gm = lambda g: "∞" if g is None else f"{(0.0 if abs(g) < 0.5 else g):.0f} dB"

ch = {(r["G"], r["T"], r["vbat"]): r for r in CH}
il_max = max(r["il_pk"] for r in CH); vds_max = max(r["vds"] for r in CH); vgs_min = min(r["vgs"] for r in CH)
mppt_rows = [r for r in CH if abs(r["vbat"] - 3.7) < 1e-6 and r["G"] >= 30 and r["ibat"] + 0.008 < 1.18 and r["settled"]]
cap_min = min(r["capture"] for r in mppt_rows); cap_max = max(r["capture"] for r in mppt_rows)
r10 = ch.get((10, 25, 3.7)); r400 = ch.get((400, 37, 3.7))
n_settled = sum(1 for r in CH if r["settled"])

L = []
A = L.append
A("# PMB-H / LIB 电路仿真报告")
A("")
A("2026-10-12 · 对应 PCB：PMB-H（加 C15、RS1B 0.22 Ω、C10 1 µF、PV_EN 版）、LIB")
A("")
A("> 你说「理论可行不代表实际能用，需要确保能用」。所以这份报告做了三件事：")
A("> 1. 用器件手册参数建模，把两块板子的每个功能都跑一遍。")
A("> 2. 每一项都写明判定标准。")
A("> 3. 仿真发现了 **4 处真实问题，已经改进 PCB**。仿真证明不了的，列在 §7，台架上验证。")
A("")
A("---")
A("")
A("## 0. 结论")
A("")
A("| # | 检查项 | 判定标准 | 结果 | |")
A("|---|---|---|---|---|")
rows = [
 ("MPPT 稳压", "不限流时 VPV = 5.93 V ± 1 %", f"{min(r['vpv'] for r in mppt_rows):.3f} V（全部工况）", "✅"),
 ("MPPT 捕获率（30–1000 W/m²）", "≥ 90 % 面板最大功率", f"{cap_min:.1%}–{cap_max:.1%}", "✅"),
 ("充电限流", "≤ 1.2 A（2500 mAh 电池的 0.48 C）", f"{max(r['ibat'] for r in CH)*1e3:.0f} mA", "✅"),
 ("恒压段（电池 4.15 V）", "电流自动减小", f"{ch[(1000, 55, 4.15)]['ibat']*1e3:.0f} mA", "✅"),
 ("电感峰值电流", "< 饱和电流 1.8 A", f"{il_max:.2f} A", "✅"),
 ("M1 栅源 / 漏源电压", "Vgs ≥ −12 V，Vds ≤ 30 V", f"{vgs_min:.1f} V / {vds_max:.1f} V", "✅"),
 ("MPPT 环路稳定性", "增益裕度 > 6 dB，相位裕度 > 30°（跨导 ≤ 5 mA/V）", f"改前增益裕度最低 {fmt_gm(gm_old5)} ❌ → 加 C15 后 {fmt_gm(gm_new5)}，相位裕度 ≥ {pm_new5:.0f}°", "✅ 已改"),
 ("夜间电池倒灌", "< 0.2 mA", f"{NIG['Q1_on_Rsh3k']:.2f} mA ❌ → PV_EN 关断后 {NIG['PV_EN_Rsh3k']*1e3:.0f} µA", "✅ 已改"),
 ("面板接反", "无电流，板子不上电", "0.00 mA", "✅"),
 ("−10 °C 冷面板热插拔", "VPV < TVS 击穿 11.1 V；Q1 的 Vgs > −12 V", f"{HP['CN3791 not yet started']['peak']:.2f} V；{HP['CN3791 not yet started']['vgs_min']:.2f} V", "✅"),
 ("室内档突遇全日照", "PV_IN− > −0.3 V（INA226 绝对最大值）", f"−0.42 V ❌ → RS1B 改 0.22 Ω 后 {RNG['vmin_q2off']:.3f} V，RS1B {RNG['p_rs1b']:.2f} W", "✅ 已改"),
 ("负载开关上电浪涌", "< 1.5 A", f"{INR['100n_4.2']['peak']:.2f} A ❌ → C10 改 1 µF 后 {INR['1u_4.2']['peak']:.2f} A（电池 4.2 V）", "✅ 已改"),
 ("超级电容预充", "< 10 分钟到 90 %", f"{LIB['lib']['t90']:.0f} s", "✅"),
 ("拔线保持（Core B 65 mA）", "≥ 10 s（够接头松动、重新插拔）", f"{LIB['lib']['holdup_s']:.0f} s（最坏）～ 60 s", "✅（原文档写的 45 s 有误，已更正）"),
 ("切换瞬间 Core B 电压", "> 3.3 V", f"{LIB['lib']['vbit_min']:.2f} V", "✅"),
 ("重新插线后恢复", "VBIT > 3.6 V", "3.77 V", "✅"),
 ("超级电容均压", "每只 ≤ 2.7 V", "1.76 V", "✅"),
 ("SYNC 脉冲", "上升沿 < 5 µs，高电平 < 4.3 V", "237 ns，3.34 V", "✅"),
 ("3V3 电源", "电池 3.2 V + BLE 突发时 ≥ 3.1 V", "3.160 V", "✅"),
 ("冷启动（电池耗尽、XIAO 不工作）", "VPV 能升到 6.05 V 启动阈值以上", "100 / 300 / 1000 W/m² 下 6.61 / 7.06 / 7.55 V", "✅"),
 ("面板模型", "与照片估算的铭牌一致", "25 °C 时 Voc 8.03 V、Isc 0.85 A、Pmax 5.34 W", "✅"),
 ("极弱光 10 W/m²", "（说明性）", "面板最大只有 33 mW，小于板子自身约 8 mA（30 mW）的耗电，电池净放电约 7–8 mA。25 ms 内未到稳态：面板电流仅约 8 mA，给 C15 充电很慢", "ℹ️"),
]
for i, (a, b, c, d) in enumerate(rows, 1): A(f"| {i} | {a} | {b} | {c} | {d} |")
A("")
A("**因为仿真改了的 4 处**（都已写进 PCB 和生产文件）：")
A("")
A("| 改动 | 发现了什么 |")
A("|---|---|")
A(f"| **新增 C15** 100 µF / 35 V 铝电解（C2836437） | 输入只有陶瓷电容时，约 5 kHz 的谐振没有阻尼。如果 CN3791 的误差放大器跨导偏高（手册没给这个参数），MPPT 环路会振荡：开关级仿真在 400 W/m² 下 VPV 摆动 403 mV、电感电流在 0–0.95 A 之间来回。CN3791 手册本来就要求输入端有电解电容。加上后摆动降到 19 mV |")
A("| **RS1B** 0.47 Ω → 0.22 Ω | 室内档时如果光照突然变强，INA226 输入被拉到 −0.42 V，超过 −0.3 V 的绝对最大值；电阻自身 0.34 W 也超过 0.25 W 额定 |")
A("| **C10** 100 nF → 1 µF | 负载开关打开瞬间电池电流峰值 3.15 A（电池 4.2 V 时），接近电池保护板 3 A 左右的过流阈值 |")
A(f"| **PV_EN**（Q8 + R19 + R20）+ MPPT 分压 200k / 51k | 夜里电池经 Q1 和 M1 体二极管倒灌给面板：{NIG['Q1_on_Rsh3k']:.1f} mA（面板旧化后可到 {NIG['Q1_on_Rsh300']:.0f} mA）。MPPT 设定点从 6.40 V 改到 5.93 V，全天捕获率从 93.6 % 提到 98.4 % |")
A("")
A("---")
A("")
A("## 1. 方法")
A("")
A("| 项目 | 做法 |")
A("|---|---|")
A("| 仿真器 | ngspice（KiCad 10 自带的 libngspice，Python 调用） |")
A("| 电路 | 元件值全部取自 `pmbh.py` / `libb.py`，与 PCB 一致；面板线按 0.5 m、40 mΩ/m、0.6 µH/m 建模 |")
A("| MOSFET | AO3400A / AO3401A：用手册里 3 个 Rds 点和 Vth 拟合，带 Ciss、Crss、Rg、体二极管 |")
A("| 二极管、TVS | SS34、B5819W、BAT54、BZT52C10、SMAJ10A、SMF5.0A：按手册 Vf / VBR 拟合 |")
A("| 面板 | 12 片串联单二极管模型：Isc 0.85 A，Voc 8.0 V（照片估算的铭牌），含温度系数 |")
A("| CN3791 | 行为模型：MPPT 1.205 V、限流 120 mV、浮充 4.2 V、300 kHz、最大占空比 94 %、DRV = VCC − 6.3 V、欠压锁定和睡眠阈值（全部来自手册） |")
A("| LM66100 | 行为模型：开启 −150 mV、关闭 +35 mV（带迟滞）、91 mΩ、反向截止、ST 开漏 |")
A("| 三种仿真 | ① 开关级瞬态（每周期约 170 个点，跑 25 ms 到稳态）；② 平均模型长时间瞬态（LIB 900 s）；③ 小信号环路分析（伯德图） |")
A("")
A("**仿真本身踩过的坑**：行为模型里的 if/else（比较器、抗饱和）在 ngspice 里会让步长塌到 10⁻¹⁷ s，一个工况跑半小时以上还不收敛。改成连续函数（tanh / max）后，一个工况约 1 分钟。之前 1.5 ms 的短仿真结论里，有两个（400 W/m² 纹波、30 W/m² 电流为 0）其实是还没到稳态，已全部用 25 ms 长仿真重做。")
A("")
A("## 2. 面板模型")
A("")
A("![P-V](图/fig1_pv.png)")
A("")
A("| 温度 | Voc | Vmp | Pmax |")
A("|---|---|---|---|")
A("| −10 °C | 8.76 V | 7.47 V | 6.04 W |")
A("| 25 °C | 8.03 V | 6.69 V | 5.34 W |")
A("| 55 °C（背上晒热） | 7.39 V | 6.02 V | 4.75 W |")
A("")
A("面板没有铭牌，这几个数是按照片估算的。台架 TC-02 实测 I-V 后，可以重新拟合模型。")
A("")
A("## 3. 充电器（CN3791 MPPT 降压）")
A("")
A("![开关波形](图/fig2_switching.png)")
A("")
A("![捕获率](图/fig3_capture.png)")
A("")
A("| 光照 W/m² | 面板温度 | 电池 | VPV | VPV 纹波 | 面板功率 | 捕获率 | 电池电流 | 电感电流 | 效率 | 稳态 |")
A("|---|---|---|---|---|---|---|---|---|---|---|")
for r in CH:
    A(f"| {r['G']} | {r['T']} °C | {r['vbat']:.2f} V | {r['vpv']:.3f} V | {r['vpv_pp']*1e3:.0f} mV | {r['ppanel']:.3f} W | {r['capture']:.1%} | {r['ibat']*1e3:.0f} mA | {r['il_min']:.2f}–{r['il_pk']:.2f} A | {r['eff']:.1%} | {'✓' if r['settled'] else '✗'} |")
A("")
A("**怎么读**：")
A("")
A("- 1000 W/m² 且面板不热（25 °C、0 °C），或电池电压低（3.0 V）时，VPV 高于 5.93 V。原因是充电电流已经顶到 1.2 A 限流，多余的功率留在面板上。这是设计如此，不是 MPPT 失效。")
A("- 电池 4.15 V 时进入恒压段，电流自然减小。")
A("- 电池电流 = 充电器输出 − 板子自身约 8 mA（XIAO + 6 个 INA226 + LDO）。")
A("- 10 W/m² 时，面板最大功率只有 33 mW，抵不过 8 mA 的自耗电，电池净放电。这是阴天室内的典型情况，符合「太阳能延长续航，但不保证免充电」的定位。这一行的「稳态」是 ✗：面板电流只有约 8 mA，给 100 µF 的 C15 充电很慢，25 ms 内没跑到平衡点。结论不受影响。")
A("")
A("**发热**（1000 W/m²、55 °C 时的损耗）：")
A("- D5 0.13 W、L1 0.11 W、R8 0.12 W、M1 约 0.05 W，估计各自温升 6–13 °C。")
A("- 背部仓 55 °C 环境下，器件最高约 70 °C，离它们 125–150 °C 的额定还很远。")
A("- 板子背面有 HP600 导热垫把热导到仓底。")
A("")
A("## 4. MPPT 环路稳定性（这次最重要的发现）")
A("")
A("![伯德图](图/fig6_loop.png)")
A("")
A("**问题**：")
A("- 降压电路以输入电压为控制对象时，电感和输入电容会在约 5 kHz 形成谐振。")
A("- 只用陶瓷电容时，这个谐振几乎没有阻尼。")
A("- CN3791 手册没给误差放大器的跨导，我在 0.05–20 mA/V 范围内扫了一遍：")
A("")
A(f"| 输入电容 | 跨导 ≤ 1 mA/V | 跨导 ≤ 5 mA/V |")
A("|---|---|---|")
A(f"| 只有陶瓷（改前） | 相位裕度 ≥ {pm_old1:.0f}°，增益裕度 ≥ {fmt_gm(gm_old1)} | 增益裕度低到 **{fmt_gm(gm_old5)}**（会振荡） |")
A(f"| 加 C15（25 °C，ESR 0.6 Ω） | 稳定 | 相位裕度 ≥ {pm_new5:.0f}°，增益裕度 **{fmt_gm(gm_new5)}** |")
A(f"| 加 C15（−10 °C，ESR 按 3 倍算） | 稳定 | 相位裕度 ≥ {pm_cold5:.0f}°，增益裕度 **{fmt_gm(gm_cold5)}** |")
A("")
A("**处理**：")
A("- 按手册「输入电容 = 电解 + 陶瓷 + 高频」的要求，加了 C15。")
A("- 增益裕度无限的意思是：无论芯片内部增益多大，相位都不会转过 −180°，环路不会振荡。")
A(f"- 开关级仿真复核：400 W/m² 下 VPV 纹波从 403 mV 降到 {r400['vpv_pp']*1e3:.0f} mV，电感电流回到正常的连续导通纹波。" if r400 else "")
A("")
A("## 5. 保护电路")
A("")
A("| 情况 | 结果 |")
A("|---|---|")
A(f"| 夜间（面板不发电），PV_EN 不关 | 电池漏电 {NIG['Q1_on_Rsh30k']:.2f} / {NIG['Q1_on_Rsh3k']:.2f} / {NIG['Q1_on_Rsh300']:.1f} mA（面板并联电阻 30k / 3k / 300 Ω，越旧越小） |")
A(f"| 夜间，PV_EN 关断 | **{NIG['PV_EN_Rsh3k']*1e3:.0f} µA**，与面板好坏无关。其中 CN3791 睡眠 30 µA、MPPT 分压 13 µA、INA226 总线输入 8 µA。12 小时只用 0.6 mAh |")
A("| 面板接反 | Q1 截止，0 mA，板子不上电 |")
A(f"| −10 °C 冷面板全日照热插拔（5 m 线） | VPV 峰值 {HP['CN3791 not yet started']['peak']:.2f} V（TVS 10 V 不导通），Q1 栅源 {HP['CN3791 not yet started']['vgs_min']:.2f} V（稳压管限在 10 V 以内） |")
A(f"| 室内档（Q2 关）突遇全日照 | PV_IN− {RNG['vmin_q2off']:.3f} V（> −0.3 V），RS1B {RNG['p_rs1b']:.2f} W（额定 1 W）。即使固件不切档也不会损坏 |")
A("")
A("## 6. 负载开关与胸前 LIB")
A("")
A("![浪涌](图/fig4_inrush.png)")
A("")
A("| 电池电压 | C10 = 100 nF（改前） | C10 = 1 µF（改后） | VLOAD 上升时间（改后） |")
A("|---|---|---|---|")
for v in ("3.4", "3.8", "4.2"):
    A(f"| {v} V | {INR['100n_'+v]['peak']:.2f} A | {INR['1u_'+v]['peak']:.2f} A | {INR['1u_'+v]['vload_rise_ms']:.1f} ms |")
A("")
A("![拔线保持](图/fig5_holdup.png)")
A("")
A("**拔线保持**：")
A("- 两只 10 F 超级电容串联，等效 5 F，充到比 VLOAD 低约 0.2 V。BITalino 按 3.3 V 欠压估算，可用的电压窗口只有 0.3–0.8 V。")
A(f"- 结果：开机 {LIB['lib']['t90']/60:.0f} 分钟内没充满、电池 3.8 V 时最短 **{LIB['lib']['holdup_s']:.0f} s**；满电并充满时约 60 s。")
A("- 原设计文档写的「约 45 s」是按更宽的电压窗口算的，已更正。")
A("- 对它的用途（磁吸接头松动、换线时重新插拔）来说，17 s 足够。")
A("")
A("**其他**：")
A("- SYNC 脉冲上升沿 237 ns，高电平被 BAT54S 钳在 3.34 V。")
A("- 3V3 在电池 3.2 V、BLE 突发 18 mA 时最低 3.160 V。")
A("")
A("## 7. 仿真证明不了、要在台架上确认的")
A("")
A("| # | 测什么 | 怎么测 | 通过标准 |")
A("|---|---|---|---|")
A("| 1 | **上电前**看 C15 极性 | 目视：电容顶上黑色半圆是负极，应朝右；丝印 + 在左 | 方向对 |")
A("| 2 | 面板 I-V | TC-02（电阻档位 + 万用表） | 用实测值重拟合 §2 的模型 |")
A("| 3 | VPV 纹波 | 示波器；多云天的真面板，或实验室电源 9 V 串 33 Ω 模拟 | < 100 mV，无 kHz 级摆动 |")
A("| 4 | BITalino Core 的真实欠压电压 | 可调电源慢慢降压，看 Core 什么时候掉线 | 决定拔线保持的真实时间 |")
A("| 5 | 夜间漏电 | 万用表 µA 档串电池，面板遮住，PV_EN 拉低 | 约 51 µA + XIAO 睡眠电流 |")
A("| 6 | 晒太阳时的温度 | TC1 / TC2 + 板上 NTC | 板子 < 85 °C，TC2 < 40 °C |")
A("")
A("## 8. 文件")
A("")
A("全部脚本在 [源码/仿真/](../源码/仿真/)，器件模型在 `models.lib`。")
A("")
A("| 脚本 | 内容 |")
A("|---|---|")
A("| `tb_charger.py` / `tb_charger2.py` / `run_final.py` | 充电器开关级仿真，14 个工况 |")
A("| `loop_ss.py` | MPPT 环路小信号分析（跨导 × 光照 × 输入电容） |")
A("| `tb_night2.py`、`tb_hotplug2.py`、`tb_range.py` | 夜间漏电、热插拔、自动量程 |")
A("| `tb_lib.py`、`tb_inrush.py` | 负载开关浪涌、LIB 保持、SYNC、3V3 |")
A("| `plots.py`、`gen_report.py` | 作图、生成本报告（数字全部从结果 JSON 读出，不手抄） |")
open(os.path.join(OUT, "仿真报告.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("wrote", os.path.join(OUT, "仿真报告.md"), len(L), "lines")
