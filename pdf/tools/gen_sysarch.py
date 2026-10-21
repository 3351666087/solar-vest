import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from svgkit import *

W, H = 720, 452
s = Svg(W, H)
LANEX, LANEW = 96, 612          # label strip width / lane content width
lanes = [
    ("L1", "硬件层",   "HARDWARE",       SOLAR, SOLAR_L,  8, 104),
    ("L2", "嵌入式层", "FIRMWARE",       OK,    OK_L,   118, 100),
    ("L3", "软件层",   "SOFTWARE",       VOLT,  VOLT_L, 232,  96),
    ("L4", "数据与运维","DATA & OPS",    PURP,  PURP_L, 342, 100),
]
for lid, cn, en, c, cl, y, h in lanes:
    s.rect(6, y, W-12, h, cl, None, 6)
    s.rect(6, y, LANEX-6, h, c, None, 6)
    s.rect(LANEX-14, y, 14, h, c, None, 0)
    s.text(16, y+21, lid, 9.5, WHITE, UI, weight=700, ls="1.4")
    s.text(16, y+38, cn, 11, WHITE, CJK, weight=700)
    s.text(16, y+52, en, 6.8, "#FFFFFF", UI, ls="1.3")

def row(y, items, h=30, gap=7, x0=LANEX+10, wtot=LANEW-20, **kw):
    n = len(items); w = (wtot - gap*(n-1))/n
    xs = []
    for i, it in enumerate(items):
        x = x0 + i*(w+gap)
        box(s, x, y, w, h, it[0], it[1] if len(it) > 1 else None, **kw)
        xs.append((x, x+w/2, x+w))
    return xs, w

# ---- L1 硬件 ----
s.text(LANEX+10, 24, "背包单元 PMB-H（18 V 区）", 7.6, SOLAR, CJK, weight=700, ls="0.6")
s.text(LANEX+424, 24, "屏蔽线缆 ＜4.2 V", 7.6, SLATE, CJK, weight=700)
s.text(LANEX+520, 24, "胸口单元 LIB", 7.6, VOLT, CJK, weight=700)
s.rect(LANEX+8, 30, 404, 64, "#FFFFFF", SOLAR_B, 5, 1)
s.rect(LANEX+516, 30, 86, 64, "#FFFFFF", VOLT, 5, 1)
hw1, _ = row(38, [("光伏板","30 W / 18 V"), ("输入保护","F·TVS·防反"), ("CN3791","MPPT 充电")],
             h=24, x0=LANEX+16, wtot=388, ts=8.4, ss=6.6, fill=PANEL)
hw2, _ = row(66, [("电池 A","2500 mAh"), ("电池 B","2500 mAh"), ("Q1–Q4","充放切换")],
             h=24, x0=LANEX+16, wtot=388, ts=8.4, ss=6.6, fill=PANEL)
box(s, LANEX+420, 46, 92, 38, "5 芯屏蔽", "防拉脱连接器", fill="#FFFFFF", stroke=LINE, ts=8.4, ss=6.6)
box(s, LANEX+522, 38, 74, 24, "超容 hold-up", None, fill=PANEL, ts=7.6)
box(s, LANEX+522, 66, 74, 24, "BITalino", None, fill=PANEL, ts=7.6)

# ---- L2 嵌入式 ----
fw, _ = row(132, [("驱动层","INA226·NTC"), ("能量状态机","5 态 + 滞回"), ("电池切换","互锁 + 死区"),
                  ("库仑计","双向积分"), ("同步脉冲","硬件时标"), ("BLE 遥测","+ 离线日志")],
            h=34, ts=8.4, ss=6.6, fill=WHITE, accent=OK)
s.text(LANEX+10, 180, "XIAO nRF52840 · Zephyr · 状态机纯逻辑可在 PC 上单元测试", 7.2, SLATE, CJK)
s.text(LANEX+10, 196, "看门狗失效 → GPIO 高阻 → 负载开关默认关断（fail-safe）", 7.2, MUTED, CJK)

# ---- L3 软件 ----
sw, _ = row(246, [("采集服务","bleak / pyserial"), ("时间对齐","同步标记回归"),
                  ("处理管线","NeuroKit2 · HRV"), ("能量分析","EAR / RES"), ("看板","Grafana")],
            h=34, ts=8.4, ss=6.6, fill=WHITE, accent=VOLT)
s.text(LANEX+10, 294, "三路数据源：BITalino DUT · BITalino 对照 · 功率遥测 —— 按硬件同步脉冲对齐后落盘", 7.2, SLATE, CJK)
s.text(LANEX+10, 310, "拟合真实采样率并报告时钟漂移 ppm，长时记录的主要误差源", 7.2, MUTED, CJK)

# ---- L4 数据 ----
dt, _ = row(356, [("原始信号","Parquet 不可变"), ("时序库","TimescaleDB"),
                  ("Run Manifest","固件 SHA + 硬件哈希"), ("CI 校验","schema + 黄金用例")],
            h=34, ts=8.4, ss=6.6, fill=WHITE, accent=PURP)
s.text(LANEX+10, 404, "每次实验可追溯到当时的固件 commit、硬件版本、电池标定容量与实测辐照度", 7.2, SLATE, CJK)

# ---- 层间箭头 ----
for x in (LANEX+90, LANEX+300, LANEX+500):
    s.arrow(x, 112, x, 126, MUTED, 1.1)
    s.arrow(x, 218, x, 240, MUTED, 1.1)
    s.arrow(x, 328, x, 350, MUTED, 1.1)
s.text(LANEX+96, 122, "I²C / GPIO", 6.4, MUTED, MONO)
s.text(LANEX+306, 236, "BLE / BT", 6.4, MUTED, MONO)
s.text(LANEX+506, 346, "写入", 6.4, MUTED, CJK)

# 右侧纵向说明条
s.rect(6, 428, W-12, 18, "#F1F4F9", None, 4)
s.text(16, 440, "贯穿全栈的两条纪律：①  能量链与测量链在时间上分离（采集时不充电）　②  每一次实验都必须能复现",
       7.4, DEEP, CJK, weight=700)

open(os.path.join(os.path.dirname(__file__), "..", "assets/svg/sys-arch.svg"), "w").write(s.out())
print("sys-arch.svg", W, "x", H)
