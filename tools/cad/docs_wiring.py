"""Wiring documentation generated from harness.json: wiring-table.md / wiring-table.csv / system-wiring-diagram.svg"""
import json, os, csv, html
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "hardware", "wiring")
os.makedirs(OUT, exist_ok=True)
W = json.load(open(os.path.join(HERE, "out", "harness.json")))
CONN_EN = {"PHR-2": "PH2.0 2P plug", "PHR-5": "PH2.0 5P plug", "UC-E6": "UC-E6 plug", "K-mini": "Type-K mini plug", "ferrule": "Bootlace ferrule / tinned end",
           "snap": "Electrode snap", "Y": "3-lead split", None: "—"}
BENCH = [
    ("B01", "Bench supply replaces the panel", "Adjustable DC supply (lab)", "PMB-H J1 (screw terminal)", "red → J1-1 PV_IN+; black → J1-2 PV_IN−", "Banana plug / crocodile clip → stripped wire",
     "7.0 V, 1.0 A current limit. The board has reverse-polarity protection; a reversed connection will not damage it", "Charger burn-in and firmware bring-up (no sunlight needed)"),
    ("B02", "TC-01 power measurement (A or C)", "Device's original battery plug", "Device battery socket", "Battery + → breadboard → multimeter mA range (in series) → breadboard → device +; − straight through",
     "2 × BOM \"PH2mm straight-pin pre-wired\" leads + 1 straight-pin header on the breadboard + Dupont jumpers", "Not needed for B: U5 on PMB-H (INA226 0x42) already measures B's load current", "A requires opening the HeartBIT case (two snap-fit halves)"),
    ("B03", "TC-02 panel I-V curve", "Panel waterproof quick connector", "Resistor steps + multimeter", "Panel + → resistor → panel −; multimeter across the resistor reads voltage, I = V / R",
     "5 W ceramic (cement) resistors 3.3/4.7/6.8/10/15/22/33/68/150 Ω (purchased); open circuit = Voc, short circuit = Isc (multimeter 10 A range)", "Panel on the test stand, REF1 in the same plane records irradiance, TC1 records backsheet temperature", "Clear day around solar noon; finish one set within 10 minutes"),
    ("B04", "Charging / capacity", "Mac or USB charger", "micro-USB on A and C; USB-C on XIAO", "Through the BOM \"multi-function USB tester\" inserted in between", "Original cables",
     "A and C are charged only when not being worn; B has no USB (powered by the back unit)", "The tester reads mAh, which also verifies battery capacity"),
    ("B05", "Data (bench)", "A / B / C", "Mac (OpenSignals)", "A: pair with the Mac's built-in Bluetooth (Classic); B, C: BLE", "Wireless", "The USB Bluetooth dongle in the kit is not needed on a Mac", "Firmware: flash XIAO over USB-C from the Mac"),
]
WIRELESS = [("B (Core BLE, solar-powered)", "BLE", "Android phone app", "ECG 1000 Hz + I1 sync pulse"),
            ("C (Board BLE, battery)", "BLE", "Android phone app", "ECG 1000 Hz (control) + acceleration"),
            ("A (Core BT, HeartBIT)", "Classic Bluetooth SPP", "Android phone app (Android supports Classic Bluetooth)", "PPG heart-rate reference"),
            ("XIAO (on PMB-H)", "BLE", "Android phone app", "Panel / battery / load power, reference-cell irradiance, IMU attitude, NTC temperature"),
            ("Bench", "BLE / Classic Bluetooth", "Mac: OpenSignals", "TC-01, TC-05 and other indoor experiments")]

def md():
    L = ["# Wiring table (all cables, pin by pin)", "", "> Auto-generated from the 3D harness model: lengths are measured along the actual routes over the vest / inside the pods; cut length = route + 80 mm allowance, rounded up to 50 mm.",
         "> Colours: electrode leads follow PLUX manual Table 2 (red IN+, black IN−, white REF).", "", "## 1. On-body cables (W01–W15)", "",
         "| ID | Name | Connectors (from → to) | Conductors: colour · from → to | Route length | Cut | Cable source | Route |", "|---|---|---|---|---|---|---|---|"]
    for w in W:
        cond = "<br>".join(f"{c[0]} · {c[1]} → {c[2]}" for c in w["conductors"])
        L.append(f"| **{w['id']}** | {w['name']} | {CONN_EN.get(w['ends'][0], w['ends'][0])} → {CONN_EN.get(w['ends'][1], w['ends'][1])} | {cond} | {w['length_mm']} mm | {w['cut_mm']} mm | {w['source']} | {w['route']} |")
    L += ["", "## 2. On-board connector pinouts", "", "| Connector | 1 | 2 | 3 | 4 | 5 |", "|---|---|---|---|---|---|",
          "| PMB-H J1 (KF350 screw terminal) | PV_IN+ | PV_IN− | | | |", "| PMB-H J2 (PH2.0) | BAT+ | GND | | | |", "| PMB-H J3 | NTC_ADC | GND | | | |",
          "| PMB-H J6 (PH2.0 5P → chest) | VLOAD | GND | SYNC | unused (NC) | GND |", "| PMB-H J7 / J8 | REF1+ / REF2+ | GND | | | |",
          "| LIB J1 (PH2.0 5P ← back) | VLOAD | GND | SYNC_IN | spare (to TP5 only) | GND |", "| LIB J2 (→ Core B battery socket) | VBIT | GND | | | |", "| LIB J3 (→ Core B I1) | SYNC_OUT | GND | | | |", "",
          "**XIAO nRF52840 Sense socket** (plug-in, no wiring needed):", "",
          "| XIAO pin | D0/A0 | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 | 3V3 | GND | 5V |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
          "| PMB-H net | NTC_ADC | NTC_EN | SYNC_OUT | LOAD_EN | SDA | SCL | CHG_INH | RANGE_LO | CHRG_N | DONE_N | PV_EN (disconnects panel input at night) | 3V3 | GND | not connected |", "",
          "**UC-E6** (BITalino sensor port, 8 pins, looks like mini-USB): only SIGNAL and GND are used; VCC 3.3 V and REF (VCC/2) are cut short and insulated in W08. PLUX wire colours vary between batches — **go by signal name, not by colour**.", "",
          "**BITalino port positions** (engraved on the lid): Core B one side I1 / A4 / A3 / A2 / A1, other side O1 / O2 / PWM / A6 / A5. B uses **A2 = ECG, I1 = SYNC**; C uses the on-board ECG module; A uses **A3 = PPG**.", "",
          "## 3. Electrode positions (on skin)", "", "| Electrode | Position | Lead colour | Connects to |", "|---|---|---|---|",
          "| B_IN+ | On left clavicle (85 mm from midline) | red | HeartBIT ECG sensor → B's A2 |", "| B_IN− | On right clavicle | black | Same as above |", "| B_REF | Right lower ribs (lower costal margin, 100 mm from midline) | white | Same as above |",
          "| C_IN+ | Below left clavicle (50 mm directly below B_IN+) | red | C's 3-lead electrode cable → Board ECG module |", "| C_IN− | Below right clavicle (50 mm directly below B_IN−) | black | Same as above |", "| C_REF | Left lower ribs (mirror of B_REF) | white | Same as above |", "",
          "Both sets are Einthoven lead I (measuring electrodes on the clavicles per PLUX manual §2.3; the reference electrode is moved from the iliac crest up to the lower ribs — likewise a bony site with little EMG, but close enough for leads ≤ 30 cm to reach). B and C are offset vertically by 50 mm and the reference electrodes are left/right mirrored, satisfying TC-05's \"same subject, same time, mirror-symmetric leads\". Electrode centres are ≥ 50 mm apart, so both the Ø24 PLUX electrodes and common Ø40–50 disposable electrodes fit.", "",
          "## 4. Bench wiring (not on body)", "", "| ID | Purpose | From | To | How to connect | Materials | Notes | Remarks |", "|---|---|---|---|---|---|---|---|"]
    for b in BENCH: L.append("| " + " | ".join(b) + " |")
    L += ["", "## 5. Wireless data links", "", "| Device | Link | Received by | Content |", "|---|---|---|---|"]
    for r in WIRELESS: L.append("| " + " | ".join(r) + " |")
    L += ["", "> Your phone is Android: all three BITalinos and the XIAO can connect to the same phone **simultaneously**, so no computer has to be carried during walking experiments. An iPhone cannot do this (no Classic Bluetooth serial support), which is why A could previously only connect to a computer.",
          "", "![System wiring diagram](system-wiring-diagram.svg)", ""]
    open(os.path.join(OUT, "wiring-table.md"), "w").write("\n".join(L))
    with open(os.path.join(OUT, "wiring-table.csv"), "w", newline="") as fh:
        wr = csv.writer(fh); wr.writerow(["ID", "Name", "From connector", "To connector", "Conductors (colour · from → to)", "Route length mm", "Cut mm", "OD mm", "Source", "Route"])
        for w in W:
            wr.writerow([w["id"], w["name"], CONN_EN.get(w["ends"][0]), CONN_EN.get(w["ends"][1]), " | ".join(f"{c[0]} · {c[1]} → {c[2]}" for c in w["conductors"]),
                         w["length_mm"], w["cut_mm"], w["od_mm"], w["source"], w["route"]])
        for b in BENCH: wr.writerow([b[0], b[1], b[2], b[3], b[4], "", "", "", b[5], b[6]])

def svg():
    S = []; A = S.append
    Wd, Ht = 1680, 1060
    A(f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wd}" height="{Ht}" viewBox="0 0 {Wd} {Ht}" font-family="Helvetica, Arial, sans-serif" font-size="13">')
    A('<style>.box{fill:#fff;stroke:#2b2f36;stroke-width:1.5}.pin{font-size:11px;fill:#333}.t{font-weight:600;font-size:15px}.w{font-size:11px;font-weight:600}.sub{font-size:11px;fill:#666}.zone{fill:#f4f5f2;stroke:#c9cec8;stroke-dasharray:6 4}</style>')
    A(f'<rect width="{Wd}" height="{Ht}" fill="#fbfbf9"/>')
    A('<text x="24" y="34" font-size="20" font-weight="700">System wiring diagram · solar vest (on-body W01–W15 · bench B01–B05 · wireless)</text>')
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
    zone(14, 50, 640, 700, "Back (rear of the vest)"); zone(670, 50, 520, 700, "Chest pod (right chest pocket)"); zone(1206, 50, 460, 700, "Left chest / lower-left pocket · skin")
    panel = box(40, 80, 170, 80, "Panel 6 V 6 W", [("+", "+ red"), ("-", "− blue")], "r")
    r1 = box(40, 190, 170, 70, "REF1 ref. cell", [("+", "+"), ("-", "−")], "r", "Panel left edge, coplanar")
    r2 = box(40, 280, 170, 70, "REF2 ref. cell", [("+", "+"), ("-", "−")], "r", "Left shoulder, horizontal")
    bat = box(40, 370, 170, 70, "LiPo 2500 mAh", [("+", "+ red"), ("-", "− black")], "r")
    ntc = box(40, 460, 170, 52, "NTC 10 kΩ", [("a", "on the battery")], "r")
    tcs = box(40, 560, 170, 70, "Thermocouples", [("1", "TC1 panel back"), ("2", "TC2 air gap")], "r")
    pm = box(380, 80, 220, 480, "PMB-H", [("J1-1", "J1-1 PV_IN+"), ("J1-2", "J1-2 PV_IN−"), ("x", ""), ("J7-1", "J7-1 REF1+"), ("J7-2", "J7-2 GND"),
                                           ("J8-1", "J8-1 REF2+"), ("J8-2", "J8-2 GND"), ("y", ""), ("J2-1", "J2-1 BAT+"), ("J2-2", "J2-2 GND"),
                                           ("J3-1", "J3-1 NTC_ADC"), ("J3-2", "J3-2 GND"), ("z", ""), ("J6-1", "J6-1 VLOAD"), ("J6-2", "J6-2 GND"),
                                           ("J6-3", "J6-3 SYNC"), ("J6-4", "J6-4 NC"), ("J6-5", "J6-5 GND")], "l", "XIAO plugs into J4/J5")
    pmR = {k: (380 + 220, v[1]) for k, v in pm.items()}
    meter = box(380, 600, 220, 70, "TC plug pouch (L front)", [("k1", "K plug 1"), ("k2", "K plug 2")], "l", "Plug into the meter to read")
    link(panel["+"], pm["J1-1"], "#c62828", "W01"); link(panel["-"], pm["J1-2"], "#1e5bb8", "")
    link(r1["+"], pm["J7-1"], "#c99a00", "W04"); link(r1["-"], pm["J7-2"], "#555", "")
    link(r2["+"], pm["J8-1"], "#c99a00", "W05"); link(r2["-"], pm["J8-2"], "#555", "")
    link(bat["+"], pm["J2-1"], "#c62828", "W02"); link(bat["-"], pm["J2-2"], "#1a1a1a", "")
    link(ntc["a"], pm["J3-1"], "#444", "W03")
    link(tcs["1"], meter["k1"], "#6b4423", "W14"); link(tcs["2"], meter["k2"], "#6b4423", "W15")
    lib = box(720, 80, 200, 200, "LIB", [("J1-1", "J1-1 VLOAD"), ("J1-2", "J1-2 GND"), ("J1-3", "J1-3 SYNC_IN"), ("J1-4", "J1-4 spare"), ("J1-5", "J1-5 GND"),
                                         ("J2-1", "J2-1 VBIT"), ("J2-2", "J2-2 GND"), ("J3-1", "J3-1 SYNC_OUT"), ("J3-2", "J3-2 GND")], "l", "Supercaps 2×10 F")
    libR = {k: (920, v[1]) for k, v in lib.items()}
    for i, col in zip(range(1, 6), ("#c62828", "#1a1a1a", "#c99a00", "#2e8b3a", "#1a1a1a")):
        link(pmR[f"J6-{i}"], lib[f"J1-{i}"], col, "W06" if i == 3 else "", dx=-40)
    core = box(980, 330, 190, 160, "Core B (BLE)", [("bat+", "Batt socket +"), ("bat-", "Batt socket −"), ("I1", "I1  ← SYNC"), ("A2", "A2  ← ECG")], "l", "B: device under test")
    link(libR["J2-1"], core["bat+"], "#c62828", "W07"); link(libR["J2-2"], core["bat-"], "#1a1a1a", "")
    link(libR["J3-1"], core["I1"], "#777", "W08"); link(libR["J3-2"], core["I1"], "#777", "")
    ecg = box(720, 560, 200, 90, "HeartBIT ECG sensor", [("out", "UC-E6 → A2"), ("leads", "Leads red/black/white")], "r", "Inner pocket in vest lining")
    link(ecg["out"], core["A2"], "#888", "W09")
    eB = box(980, 560, 190, 110, "Electrodes B (skin)", [("+", "B_IN+ L clavicle · red"), ("-", "B_IN− R clavicle · black"), ("r", "B_REF R lower ribs · white")], "l")
    for k, col in (("+", "#c62828"), ("-", "#1a1a1a"), ("r", "#9a9a9a")): link(ecg["leads"], eB[k], col, "W10" if k == "+" else "")
    cB = box(1240, 80, 200, 130, "C: Board BLE", [("ecg", "ECG module UC-E6"), ("pwr", "PWR battery socket")], "r", "Control, lower-left pocket")
    c5 = box(1240, 240, 200, 70, "523450 1000 mAh", [("+", "+ / −")], "r")
    link(c5["+"], (1440, cB["pwr"][1]), "#c62828", "W12", dx=60)
    eC = box(1470, 80, 180, 110, "Electrodes C (skin)", [("+", "C_IN+ below L clav. · red"), ("-", "C_IN− below R clav. · black"), ("r", "C_REF L lower ribs · white")], "l")
    for k, col in (("+", "#c62828"), ("-", "#1a1a1a"), ("r", "#9a9a9a")): link(cB["ecg"], eC[k], col, "W11" if k == "+" else "")
    aU = box(1240, 360, 200, 90, "A: HeartBIT (Core BT)", [("A3", "A3 ← PPG")], "r", "Left chest pocket, own 700 mAh")
    ps = box(1470, 360, 180, 70, "PulseSensor clip", [("in", "Left earlobe")], "l")
    link(aU["A3"], ps["in"], "#7b3fa0", "W13")
    A('<text x="690" y="730" class="sub">W06: PH2.0 5P straight-through 0.7 m (pin-to-pin, magnetic connector optional)  ·  W08: LIB J3 → UC-E6 SIGNAL / GND → I1  ·  W09: original PLUX UC-E6 cable</text>')
    # wireless
    zone(14, 770, 1652, 270, "Wireless · bench (not on body)")
    phone = box(700, 800, 240, 110, "Android phone app", [("a", "B, C: BLE"), ("b", "A: Classic Bluetooth"), ("c", "XIAO: BLE power/irradiance/attitude")], "l", "Lower-right pocket during tests")
    mac = box(1010, 800, 240, 110, "Mac (macOS)", [("a", "OpenSignals: A/B/C"), ("b", "XIAO firmware: USB-C"), ("c", "Data analysis")], "l", "Bench / indoor")
    bench = box(40, 800, 600, 220, "Bench wiring (see table 4)", [("1", "B01 lab supply 7 V/1 A → J1 (replaces panel)"), ("2", "B02 TC-01: battery → breadboard → multimeter mA → device"),
                                                     ("3", "B03 TC-02: panel → resistor steps, multimeter reads voltage"), ("4", "B04 USB tester in the A/C charging and XIAO flashing cables"),
                                                     ("5", "B05 A/B/C → Mac OpenSignals"), ("6", "Panel test stand: 4 printed parts + M4 bolts")], "r")
    A(f'<text x="1300" y="860" class="sub">⚠ While worn (electrodes on skin): no USB, no mains-</text><text x="1300" y="878" class="sub">powered gear; battery phone/laptop only (PLUX warning)</text>')
    A("</svg>")
    open(os.path.join(OUT, "system-wiring-diagram.svg"), "w").write("\n".join(S))

if __name__ == "__main__":
    md(); svg(); print("wrote", os.listdir(OUT))
