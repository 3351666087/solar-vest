"""Wiring documentation generated from harness.json: 接线表.md / 接线表.csv / 系统接线图.svg"""
import json, os, csv, html
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "接线")
os.makedirs(OUT, exist_ok=True)
W = json.load(open(os.path.join(HERE, "out", "harness.json")))
CONN_CN = {"PHR-2": "PH2.0 2P 插头", "PHR-5": "PH2.0 5P 插头", "UC-E6": "UC-E6 插头", "K-mini": "K 型小插头", "ferrule": "管形端子/镀锡线头",
           "snap": "电极按扣", "Y": "3-lead 分叉", None: "—"}
BENCH = [
    ("B01", "台架电源代替面板", "可调直流电源（实验室）", "PMB-H J1（螺丝端子）", "红 → J1-1 PV_IN+；黑 → J1-2 PV_IN−", "香蕉头/鳄鱼夹 → 剥线",
     "7.0 V、限流 1.0 A。板上有反接保护，接反不会坏", "充电器烧机、固件联调（不用晒太阳）"),
    ("B02", "TC-01 功耗测量（A 或 C）", "设备原电池插头", "设备电池座", "电池 + → 面包板 → 万用表 mA 档（串联）→ 面包板 → 设备 +；− 直通",
     "清单「PH2mm 直针带线」2 根 + 直针座 1 个插面包板 + 杜邦线", "B 不用：PMB-H 的 U5（INA226 0x42）已经在测 B 的负载电流", "A 需打开 HeartBIT 外壳（两半卡扣）"),
    ("B03", "TC-02 面板 I-V 曲线", "面板防水快接头", "电阻档位 + 万用表", "面板 + → 电阻 → 面板 −；万用表并在电阻两端读电压，I = V / R",
     "5 W 水泥电阻 3.3/4.7/6.8/10/15/22/33/68/150 Ω（采购），开路 = Voc，短路 = Isc（万用表 10 A 档）", "面板在测试支架上，REF1 同平面记录辐照度，TC1 记录背板温度", "晴天正午，10 分钟内测完一组"),
    ("B04", "充电 / 电量", "Mac 或 USB 充电器", "A、C 的 micro-USB；XIAO 的 USB-C", "经清单「多功能 USB 检测仪」串在中间", "原装线",
     "A、C 只在不佩戴时充电；B 没有 USB（由背部单元供电）", "检测仪读 mAh，顺便验证电池容量"),
    ("B05", "数据（台架）", "A / B / C", "Mac（OpenSignals）", "A：Mac 自带蓝牙配对经典蓝牙；B、C：BLE", "无线", "套件里的 USB 蓝牙适配器在 Mac 上用不到", "固件：XIAO 用 USB-C 接 Mac 烧录"),
]
WIRELESS = [("B（Core BLE，太阳能供电）", "BLE", "Android 手机 App", "心电 1000 Hz + I1 同步脉冲"),
            ("C（Board BLE，电池）", "BLE", "Android 手机 App", "心电 1000 Hz（对照组）+ 加速度"),
            ("A（Core BT，HeartBIT）", "经典蓝牙 SPP", "Android 手机 App（安卓支持经典蓝牙）", "PPG 心率参考"),
            ("XIAO（PMB-H 上）", "BLE", "Android 手机 App", "面板 / 电池 / 负载功率、参考片辐照度、IMU 姿态、NTC 温度"),
            ("台架", "BLE / 经典蓝牙", "Mac：OpenSignals", "TC-01、TC-05 等室内实验")]

def md():
    L = ["# 接线表（全部线缆，逐针）", "", "> 由三维线束模型自动生成：长度是沿背心/仓内实际走线量出来的，下料长度 = 走线 + 80 mm 余量，向上取整到 50 mm。",
         "> 颜色：电极导联按 PLUX 手册表 2（红 IN+、黑 IN−、白 REF）。", "", "## 1. 上身线缆（W01–W15）", "",
         "| 编号 | 名称 | 连接器（起 → 止） | 导线：线色 · 起点 → 终点 | 走线长度 | 下料 | 线从哪来 | 走线路径 |", "|---|---|---|---|---|---|---|---|"]
    for w in W:
        cond = "<br>".join(f"{c[0]} · {c[1]} → {c[2]}" for c in w["conductors"])
        L.append(f"| **{w['id']}** | {w['name']} | {CONN_CN.get(w['ends'][0], w['ends'][0])} → {CONN_CN.get(w['ends'][1], w['ends'][1])} | {cond} | {w['length_mm']} mm | {w['cut_mm']} mm | {w['source']} | {w['route']} |")
    L += ["", "## 2. 板上连接器针脚", "", "| 连接器 | 1 | 2 | 3 | 4 | 5 |", "|---|---|---|---|---|---|",
          "| PMB-H J1（KF350 螺丝端子） | PV_IN+ | PV_IN− | | | |", "| PMB-H J2（PH2.0） | BAT+ | GND | | | |", "| PMB-H J3 | NTC_ADC | GND | | | |",
          "| PMB-H J6（PH2.0 5P → 胸前） | VLOAD | GND | SYNC | 空（NC） | GND |", "| PMB-H J7 / J8 | REF1+ / REF2+ | GND | | | |",
          "| LIB J1（PH2.0 5P ← 背部） | VLOAD | GND | SYNC_IN | 备用（只到 TP5） | GND |", "| LIB J2（→ Core B 电池座） | VBIT | GND | | | |", "| LIB J3（→ Core B I1） | SYNC_OUT | GND | | | |", "",
          "**XIAO nRF52840 Sense 插座**（插上即连，无需接线）：", "",
          "| XIAO 脚 | D0/A0 | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 | 3V3 | GND | 5V |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
          "| PMB-H 网络 | NTC_ADC | NTC_EN | SYNC_OUT | LOAD_EN | SDA | SCL | CHG_INH | RANGE_LO | CHRG_N | DONE_N | PV_EN（夜间关断面板输入） | 3V3 | GND | 不接 |", "",
          "**UC-E6**（BITalino 传感器口，8 针，形似 mini-USB）：只用到 SIGNAL 和 GND；VCC 3.3 V 与 REF（VCC/2）在 W08 里剪短绝缘。PLUX 不同批次线色不同，**以信号名为准，不以颜色为准**。", "",
          "**BITalino 口位**（盖子上已刻字）：Core B 一侧 I1 / A4 / A3 / A2 / A1，另一侧 O1 / O2 / PWM / A6 / A5。B 用 **A2 = ECG、I1 = SYNC**；C 用板载 ECG 模块；A 用 **A3 = PPG**。", "",
          "## 3. 电极位置（贴皮肤）", "", "| 电极 | 位置 | 导联色 | 接到 |", "|---|---|---|---|",
          "| B_IN+ | 左锁骨上（离中线 85 mm） | 红 | HeartBIT ECG 传感器 → B 的 A2 |", "| B_IN− | 右锁骨上 | 黑 | 同上 |", "| B_REF | 右侧下肋（肋弓下缘，离中线 100 mm） | 白 | 同上 |",
          "| C_IN+ | 左锁骨下（B_IN+ 正下方 50 mm） | 红 | C 的 3-lead 电极线 → Board ECG 模块 |", "| C_IN− | 右锁骨下（B_IN− 正下方 50 mm） | 黑 | 同上 |", "| C_REF | 左侧下肋（与 B_REF 镜像） | 白 | 同上 |", "",
          "两组都是 Einthoven I 导联（测量电极按 PLUX 手册 §2.3 放在锁骨处；参考电极从髂嵴上移到下肋骨面——同样是骨性、肌电少的位置，但导联才能 ≤ 30 cm 够得着），B 和 C 上下错开 50 mm，参考电极左右镜像，满足 TC-05「同一受试者、同一时间、导联镜像对称」。电极中心距 ≥ 50 mm，Ø24 的 PLUX 电极和常见 Ø40–50 的一次性电极都放得下。", "",
          "## 4. 台架接线（不上身）", "", "| 编号 | 用途 | 从 | 到 | 怎么接 | 材料 | 说明 | 备注 |", "|---|---|---|---|---|---|---|---|"]
    for b in BENCH: L.append("| " + " | ".join(b) + " |")
    L += ["", "## 5. 无线数据链路", "", "| 设备 | 方式 | 收到哪里 | 内容 |", "|---|---|---|---|"]
    for r in WIRELESS: L.append("| " + " | ".join(r) + " |")
    L += ["", "> 你的手机是 Android：三台 BITalino 和 XIAO 可以**同时**连到同一部手机，走路做实验时不用带电脑。iPhone 做不到这点（不支持经典蓝牙串口），所以 A 原先只能连电脑。",
          "", "![系统接线图](系统接线图.svg)", ""]
    open(os.path.join(OUT, "接线表.md"), "w").write("\n".join(L))
    with open(os.path.join(OUT, "接线表.csv"), "w", newline="") as fh:
        wr = csv.writer(fh); wr.writerow(["编号", "名称", "起点连接器", "终点连接器", "导线（色 · 起 → 止）", "走线长度 mm", "下料 mm", "外径 mm", "来源", "路径"])
        for w in W:
            wr.writerow([w["id"], w["name"], CONN_CN.get(w["ends"][0]), CONN_CN.get(w["ends"][1]), " | ".join(f"{c[0]} · {c[1]} → {c[2]}" for c in w["conductors"]),
                         w["length_mm"], w["cut_mm"], w["od_mm"], w["source"], w["route"]])
        for b in BENCH: wr.writerow([b[0], b[1], b[2], b[3], b[4], "", "", "", b[5], b[6]])

def svg():
    S = []; A = S.append
    Wd, Ht = 1680, 1060
    A(f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wd}" height="{Ht}" viewBox="0 0 {Wd} {Ht}" font-family="PingFang SC, Helvetica, sans-serif" font-size="13">')
    A('<style>.box{fill:#fff;stroke:#2b2f36;stroke-width:1.5}.pin{font-size:11px;fill:#333}.t{font-weight:600;font-size:15px}.w{font-size:11px;font-weight:600}.sub{font-size:11px;fill:#666}.zone{fill:#f4f5f2;stroke:#c9cec8;stroke-dasharray:6 4}</style>')
    A(f'<rect width="{Wd}" height="{Ht}" fill="#fbfbf9"/>')
    A('<text x="24" y="34" font-size="20" font-weight="700">系统接线图 · 太阳能背心（上身 W01–W15 · 台架 B01–B05 · 无线）</text>')
    def zone(x, y, w, h, title): A(f'<rect class="zone" x="{x}" y="{y}" width="{w}" height="{h}" rx="14"/><text x="{x + 14}" y="{y + 22}" class="sub">{title}</text>')
    def box(x, y, w, h, title, pins, side="r", sub=""):
        A(f'<rect class="box" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/><text class="t" x="{x + 10}" y="{y + 22}">{html.escape(title)}</text>')
        if sub: A(f'<text class="sub" x="{x + 10}" y="{y + 38}">{html.escape(sub)}</text>')
        P = {}
        for i, (k, lab) in enumerate(pins):
            py = y + 54 + i * 18
            px = x + w if side == "r" else x
            A(f'<circle cx="{px}" cy="{py}" r="3.5" fill="#2b2f36"/><text class="pin" x="{px - 6 if side == "r" else px + 8}" y="{py + 4}" text-anchor="{"end" if side == "r" else "start"}">{html.escape(lab)}</text>')
            P[k] = (px, py)
        return P
    def link(p, q, col, label, dx=0):
        mx = (p[0] + q[0]) / 2 + dx
        A(f'<path d="M{p[0]},{p[1]} C{mx},{p[1]} {mx},{q[1]} {q[0]},{q[1]}" fill="none" stroke="{col}" stroke-width="2.4"/>')
        A(f'<text class="w" x="{mx + 4}" y="{(p[1] + q[1]) / 2 - 4}" fill="{col}">{html.escape(label)}</text>')
    zone(14, 50, 640, 700, "背部（背心背面）"); zone(670, 50, 520, 700, "胸前仓（右胸口袋）"); zone(1206, 50, 460, 700, "左胸 / 左下口袋 · 皮肤")
    panel = box(40, 80, 170, 80, "太阳能板 6 V 6 W", [("+", "+ 红"), ("-", "− 蓝")], "r")
    r1 = box(40, 190, 170, 70, "REF1 参考片", [("+", "+"), ("-", "−")], "r", "面板左缘，同平面")
    r2 = box(40, 280, 170, 70, "REF2 参考片", [("+", "+"), ("-", "−")], "r", "左肩，水平")
    bat = box(40, 370, 170, 70, "LiPo 2500 mAh", [("+", "+ 红"), ("-", "− 黑")], "r")
    ntc = box(40, 460, 170, 52, "NTC 10 kΩ", [("a", "贴在电池上")], "r")
    tcs = box(40, 560, 170, 70, "热电偶 TC1 / TC2", [("1", "TC1 面板背板"), ("2", "TC2 气隙")], "r")
    pm = box(380, 80, 220, 480, "PMB-H", [("J1-1", "J1-1 PV_IN+"), ("J1-2", "J1-2 PV_IN−"), ("x", ""), ("J7-1", "J7-1 REF1+"), ("J7-2", "J7-2 GND"),
                                           ("J8-1", "J8-1 REF2+"), ("J8-2", "J8-2 GND"), ("y", ""), ("J2-1", "J2-1 BAT+"), ("J2-2", "J2-2 GND"),
                                           ("J3-1", "J3-1 NTC_ADC"), ("J3-2", "J3-2 GND"), ("z", ""), ("J6-1", "J6-1 VLOAD"), ("J6-2", "J6-2 GND"),
                                           ("J6-3", "J6-3 SYNC"), ("J6-4", "J6-4 空"), ("J6-5", "J6-5 GND")], "l", "XIAO 插在 J4/J5")
    pmR = {k: (380 + 220, v[1]) for k, v in pm.items()}
    meter = box(380, 600, 220, 70, "热电偶插头袋（左前）", [("k1", "K 插头 1"), ("k2", "K 插头 2")], "l", "测温仪需要时插上读数")
    link(panel["+"], pm["J1-1"], "#c62828", "W01"); link(panel["-"], pm["J1-2"], "#1e5bb8", "")
    link(r1["+"], pm["J7-1"], "#c99a00", "W04"); link(r1["-"], pm["J7-2"], "#555", "")
    link(r2["+"], pm["J8-1"], "#c99a00", "W05"); link(r2["-"], pm["J8-2"], "#555", "")
    link(bat["+"], pm["J2-1"], "#c62828", "W02"); link(bat["-"], pm["J2-2"], "#1a1a1a", "")
    link(ntc["a"], pm["J3-1"], "#444", "W03")
    link(tcs["1"], meter["k1"], "#6b4423", "W14"); link(tcs["2"], meter["k2"], "#6b4423", "W15")
    lib = box(720, 80, 200, 200, "LIB", [("J1-1", "J1-1 VLOAD"), ("J1-2", "J1-2 GND"), ("J1-3", "J1-3 SYNC_IN"), ("J1-4", "J1-4 备用"), ("J1-5", "J1-5 GND"),
                                         ("J2-1", "J2-1 VBIT"), ("J2-2", "J2-2 GND"), ("J3-1", "J3-1 SYNC_OUT"), ("J3-2", "J3-2 GND")], "l", "超级电容 2×10 F")
    libR = {k: (920, v[1]) for k, v in lib.items()}
    for i, col in zip(range(1, 6), ("#c62828", "#1a1a1a", "#c99a00", "#2e8b3a", "#1a1a1a")):
        link(pmR[f"J6-{i}"], lib[f"J1-{i}"], col, "W06" if i == 3 else "", dx=-40)
    core = box(980, 330, 190, 160, "Core B（BLE）", [("bat+", "电池座 +"), ("bat-", "电池座 −"), ("I1", "I1  ← SYNC"), ("A2", "A2  ← ECG")], "l", "B：被测机")
    link(libR["J2-1"], core["bat+"], "#c62828", "W07"); link(libR["J2-2"], core["bat-"], "#1a1a1a", "")
    link(libR["J3-1"], core["I1"], "#777", "W08"); link(libR["J3-2"], core["I1"], "#777", "")
    ecg = box(720, 560, 200, 90, "HeartBIT ECG 传感器", [("out", "UC-E6 → A2"), ("leads", "导联 红/黑/白")], "r", "背心里布内袋")
    link(ecg["out"], core["A2"], "#888", "W09")
    eB = box(980, 560, 190, 110, "电极 B（皮肤）", [("+", "B_IN+ 左锁骨 · 红"), ("-", "B_IN− 右锁骨 · 黑"), ("r", "B_REF 右下肋 · 白")], "l")
    for k, col in (("+", "#c62828"), ("-", "#1a1a1a"), ("r", "#9a9a9a")): link(ecg["leads"], eB[k], col, "W10" if k == "+" else "")
    cB = box(1240, 80, 200, 130, "C：Board BLE", [("ecg", "ECG 模块 UC-E6"), ("pwr", "PWR 电池座")], "r", "对照组，左下口袋")
    c5 = box(1240, 240, 200, 70, "523450 1000 mAh", [("+", "+ / −")], "r")
    link(c5["+"], (1440, cB["pwr"][1]), "#c62828", "W12", dx=60)
    eC = box(1470, 80, 180, 110, "电极 C（皮肤）", [("+", "C_IN+ 左锁骨下 · 红"), ("-", "C_IN− 右锁骨下 · 黑"), ("r", "C_REF 左下肋 · 白")], "l")
    for k, col in (("+", "#c62828"), ("-", "#1a1a1a"), ("r", "#9a9a9a")): link(cB["ecg"], eC[k], col, "W11" if k == "+" else "")
    aU = box(1240, 360, 200, 90, "A：HeartBIT（Core BT）", [("A3", "A3 ← PPG")], "r", "左胸口袋，自带 700 mAh")
    ps = box(1470, 360, 180, 70, "PulseSensor 耳夹", [("in", "左耳垂")], "l")
    link(aU["A3"], ps["in"], "#7b3fa0", "W13")
    A('<text x="690" y="730" class="sub">W06：PH2.0 5P 同向线 0.7 m（针对针，可串磁吸连接器）  ·  W08：LIB J3 → UC-E6 SIGNAL / GND → I1  ·  W09：PLUX 原装 UC-E6 线</text>')
    # wireless
    zone(14, 770, 1652, 270, "无线 · 台架（不上身）")
    phone = box(700, 800, 240, 110, "Android 手机 App", [("a", "B、C：BLE"), ("b", "A：经典蓝牙"), ("c", "XIAO：BLE 功率/辐照/姿态")], "l", "实验时放右下口袋")
    mac = box(1010, 800, 240, 110, "Mac（macOS）", [("a", "OpenSignals：A/B/C"), ("b", "XIAO 固件：USB-C"), ("c", "数据分析")], "l", "台架 / 室内")
    bench = box(40, 800, 600, 220, "台架接线（详见表 4）", [("1", "B01 实验室电源 7 V/1 A → J1（代替面板）"), ("2", "B02 TC-01：电池 → 面包板 → 万用表 mA → 设备"),
                                                     ("3", "B03 TC-02：面板 → 电阻档位，万用表测电压"), ("4", "B04 USB 检测仪串在 A/C 充电线、XIAO 烧录线上"),
                                                     ("5", "B05 A/B/C → Mac OpenSignals"), ("6", "面板测试支架：打印件 ×4 + M4 螺栓")], "r")
    A(f'<text x="1300" y="860" class="sub">⚠ 佩戴（贴着电极）时：不接 USB、不接市电设备；</text><text x="1300" y="878" class="sub">只用电池供电的手机 / 笔记本（PLUX 数据手册警告）</text>')
    A("</svg>")
    open(os.path.join(OUT, "系统接线图.svg"), "w").write("\n".join(S))

if __name__ == "__main__":
    md(); svg(); print("wrote", os.listdir(OUT))
