import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from dotkit import *
OUT = os.path.join(os.path.dirname(__file__), "..", "src-en/dot")

def w(name, body, **kw):
    open(os.path.join(OUT, name + ".dot"), "w").write(render(body, **kw))

# ═══════════ HW-1  input protection & MPPT charging (18 V zone) ═══════════
b  = chip("PV", "PV PANEL", [("p","PV+","red 18AWG shielded"), ("n","PV−","black")],
          sub="30 W / 18 V", hdr=SOLAR)
b += chip("PROT", "PROTECTION", [
      ("i","F1","2 A slow-blow · in panel j-box"),
      (None,"TVS1","SMAJ26A across PV+/PV−"),
      (None,"D1","SS54 anti-reverse 40 V/5 A"),
      (None,"C1","220 µF/35 V low ESR"),
      ("o","L1","CM choke + ferrite")], sub="18 V zone", hdr=SOLAR)
b += chip("RS1", "RS1  0.02 Ω", [("a","IN","← L1"), ("b","OUT","→ VIN"),
      ("k","K+/K−","Kelvin → INA226#1")], sub="1% / 2512", hdr=VOLT)
b += chip("CHG", "CN3791", [
      ("vin","VIN","18 V input"), ("gnd","GND","PGND"),
      ("mppt","MPPT","divider ≈0.76×Voc ≈16.5 V"),
      ("cs","CS","Rcs → charge 1.25 A"),
      ("bat","BAT","4.2 V CC/CV → CHG_OUT"),
      ("chrg","CHRG","→ MCU D8")],
      sub="MPPT 1-cell Li charger　⚠ pin nos. per datasheet", hdr=SOLAR)
b += edge("PV:p_o:e","PROT:i:w","PV+ 18V",SOLAR,1.6)
b += edge("PROT:o_o:e","RS1:a:w","VBUS18",SOLAR,1.6)
b += edge("RS1:b_o:e","CHG:vin:w","",SOLAR,1.6)
w("hw1-input", cluster("hv","18 V power zone — ≥3 mm copper-free band to low-voltage zone on PCB", b,
                       color=SOLAR, bg="#FEFBF5", fc=SOLAR), ranksep=0.7)

# ═══════════ HW-2  charge-side switching ═══════════
b  = plain("CO","CHG_OUT","from CN3791.BAT<BR/>4.2 V / 1.25 A", fill=SOLAR_L, border=SOLAR, tcol=SOLAR)
b += chip("Q12","Q1 · Q2  charge switching", [
      ("g1","Q1.G","← MCU D1 (via interlock)"), ("s1","Q1.S","CHG_OUT"), ("d1","Q1.D","→ BAT_A+"),
      ("g2","Q2.G","← MCU D2 (via interlock)"), ("s2","Q2.S","CHG_OUT"), ("d2","Q2.D","→ BAT_B+")],
      sub="P-MOS AO3401 / SOT-23", hdr=DEEP)
b += plain("ILK","hw interlock: inverter + AND","Q1·Q2 never on together<BR/>MCU runaway = parallel cells → 4.2 A",
           fill=RISK_L, border=RISK, tcol=RISK)
b += chip("BA","BATTERY A", [("p","+","JST-PH pin1 ⚠ verify polarity"), ("n","−","pin2 → PGND"),
      ("t","NTC_A","10 kΩ B3950 → MCU A0")], sub="2500 mAh / with PCM", hdr=OK)
b += chip("BB","BATTERY B", [("p","+","JST-PH pin1"), ("n","−","pin2 → PGND"),
      ("t","NTC_B","10 kΩ B3950 → MCU A1")], sub="2500 mAh / with PCM", hdr=OK)
b += edge("CO","Q12:s1:w","",SOLAR,1.5) + edge("CO","Q12:s2:w","",SOLAR,1.5)
b += edge("Q12:d1_o:e","BA:p:w","BAT_A+",OK,1.5) + edge("Q12:d2_o:e","BB:p:w","BAT_B+",OK,1.5)
b += edge("ILK","Q12:g1:w","",RISK,1.0,"dashed") + edge("ILK","Q12:g2:w","",RISK,1.0,"dashed")
w("hw2-charge", b, ranksep=0.75)

# ═══════════ HW-3  discharge-side switching & umbilical ═══════════
b  = chip("BAT2","BATTERY A / B", [("a","BAT_A+","→ Q3.S"), ("b","BAT_B+","→ Q4.S"),
      (None,"PGND","single-point star")], sub="only one discharges at a time", hdr=OK)
b += chip("Q34","Q3 · Q4  discharge switching", [
      ("g3","Q3.G","← MCU D3"), ("s3","Q3.S","BAT_A+"), ("d3","Q3.D","→ LOAD_BUS"),
      ("g4","Q4.G","← MCU D6"), ("s4","Q4.S","BAT_B+"), ("d4","Q4.D","→ LOAD_BUS"),
      (None,"⚠ body diode","must block reverse")],
      sub="back-to-back dual FET or LM66100", hdr=DEEP)
b += chip("RS2","RS2  0.02 Ω", [("a","IN","LOAD_BUS"), ("b","OUT","→ J6.1"),
      ("k","K+/K−","→ INA226#2 bidir")], sub="1% / 2512 · coulomb ctr", hdr=VOLT)
b += chip("CBL","J6  CABLE", [
      ("p1","1  BAT_OUT+","≤ 4.2 V supply"), ("p2","2  GND","power return"),
      ("p3","3  GND","signal gnd"), ("p4","4  CTRL_LOAD","← MCU D7"),
      ("p5","5  SYNC","← MCU D10"), (None,"SHIELD","gnd at PMB-H end only")],
      sub="5-core shielded · magnetic break-away", hdr=VOLT)
b += edge("BAT2:a_o:e","Q34:s3:w","",VOLT,1.5) + edge("BAT2:b_o:e","Q34:s4:w","",VOLT,1.5)
b += edge("Q34:d3_o:e","RS2:a:w","LOAD_BUS",VOLT,1.5) + edge("Q34:d4_o:e","RS2:a:w","",VOLT,1.5)
b += edge("RS2:b_o:e","CBL:p1:w","",VOLT,1.5)
w("hw3-discharge", b, ranksep=0.7)

# ═══════════ HW-4  metering & control (I²C + GPIO) ═══════════
b  = chip("I1","INA226 #1", [("vp","VIN+","RS1 Kelvin +"), ("vn","VIN−","RS1 Kelvin −"),
      ("vb","VBUS","VBUS18 divider ⚠ 36 V max → divide"), ("vs","VS","3V3"), ("g","GND","AGND"),
      ("sc","SCL","I²C"), ("sd","SDA","I²C"), ("a0","A0/A1","GND/GND → 0x40")],
      sub="PV-side power metering", hdr=VOLT)
b += chip("I2","INA226 #2", [("vp","VIN+","RS2 Kelvin +"), ("vn","VIN−","RS2 Kelvin −"),
      ("vb","VBUS","LOAD_BUS direct"), ("vs","VS","3V3"), ("g","GND","AGND"),
      ("sc","SCL","I²C"), ("sd","SDA","I²C"), ("a0","A0/A1","VS/GND → 0x41")],
      sub="battery-side bidir · coulomb ctr", hdr=VOLT)
b += chip("NTC","NTC dividers ×2", [("o1","A0_IN","10 kΩ ÷ NTC_A"), ("o2","A1_IN","10 kΩ ÷ NTC_B")],
      sub="charge only 0 °C < T < 45 °C", hdr=OK)
b += chip("MCU","XIAO nRF52840", [
      ("sda","D4 / SDA","I²C data ⚠ check default map"), ("scl","D5 / SCL","I²C clock"),
      ("a0","D0 / A0","NTC_A"), ("a1","D1x / A1","NTC_B"),
      ("q1","D1","Q1 gate (charge A)"), ("q2","D2","Q2 gate (charge B)"),
      ("q3","D3","Q3 gate (discharge A)"), ("q4","D6","Q4 gate (discharge B)"),
      ("ld","D7","CTRL_LOAD → J6.4"), ("ch","D8","CN3791 CHRG read"),
      ("sy","D10","SYNC pulse → J6.5"), ("p","3V3 / GND","on-board LDO · star gnd")],
      sub="BLE telem · power FSM · coulomb integ", hdr=PURP)
for n in ("I1","I2"):
    b += edge(f"{n}:sc:e","MCU:scl:w","SCL",VOLT,1.1)
    b += edge(f"{n}:sd:e","MCU:sda:w","SDA",VOLT,1.1)
b += edge("NTC:o1_o:e","MCU:a0:w","",OK,1.1) + edge("NTC:o2_o:e","MCU:a1:w","",OK,1.1)
w("hw4-sense", b, ranksep=0.8, nodesep=0.3)

# ═══════════ HW-5  chest unit LIB → BITalino ═══════════
b  = chip("CBL2","J6 (chest end)", [("p1","1 BAT_OUT+","≤ 4.2 V"), ("p2","2 GND","—"),
      ("p4","4 CTRL_LOAD","switch enable"), ("p5","5 SYNC","sync pulse")],
      sub="shield floating this end", hdr=VOLT)
b += chip("SC","supercap hold-up", [("i","+","BAT_OUT+"), ("m","MID","bal 100 kΩ×2"), ("n","−","GND"),
      (None,"pre-chg","10 Ω + Q6 bypass"), (None,"⚠","direct parallel = tens of A")],
      sub="2×2.7 V 10 F series → 5.4 V/5 F · 15.2 J · 63 s", hdr=OK)
b += chip("Q5","Q5 load switch + π filter", [("g","G","← CTRL_LOAD"),
      (None,"R1","100 kΩ pull-up to S"), ("s","S","BAT_OUT+"), ("d","D","→ π filter"),
      (None,"soft start","R2 10 kΩ + 100 nF ≈1 ms"),
      (None,"fail-safe","MCU hi-Z → off"),
      ("o","π","10 µH + 22 µF×2 → J7")], sub="P-MOS AO3401", hdr=DEEP)
b += chip("SY","sync inject", [("i","IN","← SYNC"), ("o","OUT","→ I1")],
      sub="1 kΩ + BAT54S clamp to 3V3", hdr=PURP)
b += chip("BIT","BITalino", [("v","BAT +","J7 pin1 ⚠ measure polarity first"),
      ("g","BAT −","pin2"), ("i1","I1","10 ms sync pulse ⚠ verify level"),
      ("gg","GND","must share gnd with PMB-H")], sub="(r)evolution · ECG → A1", hdr=RISK)
b += edge("CBL2:p1_o:e","SC:i:w","",VOLT,1.5)
b += edge("SC:i_o:e","Q5:s:w","",VOLT,1.5)
b += edge("CBL2:p4_o:e","Q5:g:w","",PURP,1.1,"dashed")
b += edge("Q5:o_o:e","BIT:v:w","J7",VOLT,1.5)
b += edge("CBL2:p5_o:e","SY:i:w","",PURP,1.1)
b += edge("SY:o_o:e","BIT:i1:w","",PURP,1.1)
w("hw5-chest", cluster("chest","Chest unit LIB — no switching supply · no 18 V · < 1 mW", b,
                       color=VOLT, bg="#FAFBFE", fc=VOLT), ranksep=0.6)
print("hw dot files written (en)")
