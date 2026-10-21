import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dotkit import *
OUT = os.path.join(os.path.dirname(__file__), "..", "src/dot")

def w(name, body, **kw):
    open(os.path.join(OUT, name + ".dot"), "w").write(render(body, **kw))

# ═══════════ HW-1  输入保护与 MPPT 充电（18 V 区）═══════════
b  = chip("PV", "PV PANEL", [("p","PV+","红 18AWG 屏蔽"), ("n","PV−","黑")],
          sub="30 W / 18 V", hdr=SOLAR)
b += chip("PROT", "PROTECTION", [
      ("i","F1","2 A 慢断 · 装面板接线盒"),
      (None,"TVS1","SMAJ26A 跨 PV+/PV−"),
      (None,"D1","SS54 防反 40 V/5 A"),
      (None,"C1","220 µF/35 V 低 ESR"),
      ("o","L1","共模扼流 + 磁环")], sub="18 V 区", hdr=SOLAR)
b += chip("RS1", "RS1  0.02 Ω", [("a","IN","← L1"), ("b","OUT","→ VIN"),
      ("k","K+/K−","开尔文 → INA226#1")], sub="1% / 2512", hdr=VOLT)
b += chip("CHG", "CN3791", [
      ("vin","VIN","18 V 输入"), ("gnd","GND","PGND"),
      ("mppt","MPPT","分压 ≈0.76×Voc ≈16.5 V"),
      ("cs","CS","Rcs → 充电 1.25 A"),
      ("bat","BAT","4.2 V CC/CV → CHG_OUT"),
      ("chrg","CHRG","→ MCU D8")],
      sub="MPPT 单节锂电充电器　⚠ 引脚号以手册为准", hdr=SOLAR)
b += edge("PV:p_o:e","PROT:i:w","PV+ 18V",SOLAR,1.6)
b += edge("PROT:o_o:e","RS1:a:w","VBUS18",SOLAR,1.6)
b += edge("RS1:b_o:e","CHG:vin:w","",SOLAR,1.6)
w("hw1-input", cluster("hv","18 V 功率区　—　PCB 上以 ≥3 mm 无铜隔离带与低压区分开", b,
                       color=SOLAR, bg="#FEFBF5", fc=SOLAR), ranksep=0.7)

# ═══════════ HW-2  充电侧切换 ═══════════
b  = plain("CO","CHG_OUT","来自 CN3791.BAT<BR/>4.2 V / 1.25 A", fill=SOLAR_L, border=SOLAR, tcol=SOLAR)
b += chip("Q12","Q1 · Q2　充电切换", [
      ("g1","Q1.G","← MCU D1（经互锁）"), ("s1","Q1.S","CHG_OUT"), ("d1","Q1.D","→ BAT_A+"),
      ("g2","Q2.G","← MCU D2（经互锁）"), ("s2","Q2.S","CHG_OUT"), ("d2","Q2.D","→ BAT_B+")],
      sub="P-MOS AO3401 / SOT-23", hdr=DEEP)
b += plain("ILK","硬件互锁　反相器 + 与门","Q1·Q2 不得同时导通<BR/>MCU 跑飞 = 电池并联 → 环流 4.2 A",
           fill=RISK_L, border=RISK, tcol=RISK)
b += chip("BA","BATTERY A", [("p","+","JST-PH pin1 ⚠ 极性须实测"), ("n","−","pin2 → PGND"),
      ("t","NTC_A","10 kΩ B3950 → MCU A0")], sub="2500 mAh / 带 PCM", hdr=OK)
b += chip("BB","BATTERY B", [("p","+","JST-PH pin1"), ("n","−","pin2 → PGND"),
      ("t","NTC_B","10 kΩ B3950 → MCU A1")], sub="2500 mAh / 带 PCM", hdr=OK)
b += edge("CO","Q12:s1:w","",SOLAR,1.5) + edge("CO","Q12:s2:w","",SOLAR,1.5)
b += edge("Q12:d1_o:e","BA:p:w","BAT_A+",OK,1.5) + edge("Q12:d2_o:e","BB:p:w","BAT_B+",OK,1.5)
b += edge("ILK","Q12:g1:w","",RISK,1.0,"dashed") + edge("ILK","Q12:g2:w","",RISK,1.0,"dashed")
w("hw2-charge", b, ranksep=0.75)

# ═══════════ HW-3  放电侧切换与出线 ═══════════
b  = chip("BAT2","BATTERY A / B", [("a","BAT_A+","→ Q3.S"), ("b","BAT_B+","→ Q4.S"),
      (None,"PGND","星型地单点")], sub="任一时刻仅一块放电", hdr=OK)
b += chip("Q34","Q3 · Q4　放电切换", [
      ("g3","Q3.G","← MCU D3"), ("s3","Q3.S","BAT_A+"), ("d3","Q3.D","→ LOAD_BUS"),
      ("g4","Q4.G","← MCU D6"), ("s4","Q4.S","BAT_B+"), ("d4","Q4.D","→ LOAD_BUS"),
      (None,"⚠ 体二极管","须反向阻断")],
      sub="背靠背双 FET 或 LM66100", hdr=DEEP)
b += chip("RS2","RS2  0.02 Ω", [("a","IN","LOAD_BUS"), ("b","OUT","→ J6.1"),
      ("k","K+/K−","→ INA226#2 双向")], sub="1% / 2512 · 库仑计", hdr=VOLT)
b += chip("CBL","J6　CABLE", [
      ("p1","1  BAT_OUT+","≤ 4.2 V 供电"), ("p2","2  GND","功率地回流"),
      ("p3","3  GND","信号地"), ("p4","4  CTRL_LOAD","← MCU D7"),
      ("p5","5  SYNC","← MCU D10"), (None,"SHIELD","仅 PMB-H 端接地")],
      sub="5 芯屏蔽 · 磁吸防拉脱", hdr=VOLT)
b += edge("BAT2:a_o:e","Q34:s3:w","",VOLT,1.5) + edge("BAT2:b_o:e","Q34:s4:w","",VOLT,1.5)
b += edge("Q34:d3_o:e","RS2:a:w","LOAD_BUS",VOLT,1.5) + edge("Q34:d4_o:e","RS2:a:w","",VOLT,1.5)
b += edge("RS2:b_o:e","CBL:p1:w","",VOLT,1.5)
w("hw3-discharge", b, ranksep=0.7)

# ═══════════ HW-4  计量与控制（I²C + GPIO）═══════════
b  = chip("I1","INA226 #1", [("vp","VIN+","RS1 开尔文 +"), ("vn","VIN−","RS1 开尔文 −"),
      ("vb","VBUS","VBUS18 分压 ⚠ 超 36 V 上限须分压"), ("vs","VS","3V3"), ("g","GND","AGND"),
      ("sc","SCL","I²C"), ("sd","SDA","I²C"), ("a0","A0/A1","GND/GND → 0x40")],
      sub="PV 侧功率计量", hdr=VOLT)
b += chip("I2","INA226 #2", [("vp","VIN+","RS2 开尔文 +"), ("vn","VIN−","RS2 开尔文 −"),
      ("vb","VBUS","LOAD_BUS 直接"), ("vs","VS","3V3"), ("g","GND","AGND"),
      ("sc","SCL","I²C"), ("sd","SDA","I²C"), ("a0","A0/A1","VS/GND → 0x41")],
      sub="电池侧双向 · 兼作库仑计", hdr=VOLT)
b += chip("NTC","NTC 分压 ×2", [("o1","A0_IN","10 kΩ ÷ NTC_A"), ("o2","A1_IN","10 kΩ ÷ NTC_B")],
      sub="0 °C < T < 45 °C 方可充电", hdr=OK)
b += chip("MCU","XIAO nRF52840", [
      ("sda","D4 / SDA","I²C 数据 ⚠ 核实默认映射"), ("scl","D5 / SCL","I²C 时钟"),
      ("a0","D0 / A0","NTC_A"), ("a1","D1x / A1","NTC_B"),
      ("q1","D1","Q1 栅极（充电 A）"), ("q2","D2","Q2 栅极（充电 B）"),
      ("q3","D3","Q3 栅极（放电 A）"), ("q4","D6","Q4 栅极（放电 B）"),
      ("ld","D7","CTRL_LOAD → J6.4"), ("ch","D8","CN3791 CHRG 读取"),
      ("sy","D10","SYNC 脉冲 → J6.5"), ("p","3V3 / GND","板载 LDO · 星型地")],
      sub="BLE 遥测 · 能量状态机 · 库仑积分", hdr=PURP)
for n in ("I1","I2"):
    b += edge(f"{n}:sc:e","MCU:scl:w","SCL",VOLT,1.1)
    b += edge(f"{n}:sd:e","MCU:sda:w","SDA",VOLT,1.1)
b += edge("NTC:o1_o:e","MCU:a0:w","",OK,1.1) + edge("NTC:o2_o:e","MCU:a1:w","",OK,1.1)
w("hw4-sense", b, ranksep=0.8, nodesep=0.3)

# ═══════════ HW-5  胸口单元 LIB → BITalino ═══════════
b  = chip("CBL2","J6（胸口端）", [("p1","1 BAT_OUT+","≤ 4.2 V"), ("p2","2 GND","—"),
      ("p4","4 CTRL_LOAD","开关使能"), ("p5","5 SYNC","同步脉冲")],
      sub="屏蔽层此端浮空", hdr=VOLT)
b += chip("SC","超容 hold-up", [("i","+","BAT_OUT+"), ("m","MID","均压 100 kΩ×2"), ("n","−","GND"),
      (None,"预充","10 Ω + Q6 旁路"), (None,"⚠","直接并联浪涌数十 A")],
      sub="2×2.7 V 10 F 串联 → 5.4 V/5 F · 15.2 J · 63 s", hdr=OK)
b += chip("Q5","Q5 负载开关 + π 滤波", [("g","G","← CTRL_LOAD"),
      (None,"R1","100 kΩ 上拉至 S"), ("s","S","BAT_OUT+"), ("d","D","→ π 滤波"),
      (None,"软启动","R2 10 kΩ + 100 nF ≈1 ms"),
      (None,"fail-safe","MCU 高阻 → 关断"),
      ("o","π","10 µH + 22 µF×2 → J7")], sub="P-MOS AO3401", hdr=DEEP)
b += chip("SY","同步注入", [("i","IN","← SYNC"), ("o","OUT","→ I1")],
      sub="1 kΩ + BAT54S 钳位 3V3", hdr=PURP)
b += chip("BIT","BITalino", [("v","BAT +","J7 pin1 ⚠ 极性先实测"),
      ("g","BAT −","pin2"), ("i1","I1","10 ms 同步脉冲 ⚠ 核实电平"),
      ("gg","GND","必须与 PMB-H 共地")], sub="(r)evolution · ECG → A1", hdr=RISK)
b += edge("CBL2:p1_o:e","SC:i:w","",VOLT,1.5)
b += edge("SC:i_o:e","Q5:s:w","",VOLT,1.5)
b += edge("CBL2:p4_o:e","Q5:g:w","",PURP,1.1,"dashed")
b += edge("Q5:o_o:e","BIT:v:w","J7",VOLT,1.5)
b += edge("CBL2:p5_o:e","SY:i:w","",PURP,1.1)
b += edge("SY:o_o:e","BIT:i1:w","",PURP,1.1)
w("hw5-chest", cluster("chest","胸口单元 LIB　—　无开关电源 · 无 18 V · 功耗 < 1 mW", b,
                       color=VOLT, bg="#FAFBFE", fc=VOLT), ranksep=0.6)
print("hw dot files written")
