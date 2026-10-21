import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from svgkit import *

W, H = 720, 452
s = Svg(W, H)
LANEX, LANEW = 96, 612          # label strip width / lane content width
lanes = [
    ("L1", "Hardware",   "HARDWARE",       SOLAR, SOLAR_L,  8, 104),
    ("L2", "Firmware",   "FIRMWARE",       OK,    OK_L,   118, 100),
    ("L3", "Software",   "SOFTWARE",       VOLT,  VOLT_L, 232,  96),
    ("L4", "Data & Ops", "DATA & OPS",     PURP,  PURP_L, 342, 100),
]
for lid, cn, en, c, cl, y, h in lanes:
    s.rect(6, y, W-12, h, cl, None, 6)
    s.rect(6, y, LANEX-6, h, c, None, 6)
    s.rect(LANEX-14, y, 14, h, c, None, 0)
    s.text(16, y+21, lid, 9.5, WHITE, UI, weight=700, ls="1.4")
    s.text(16, y+38, cn, 10, WHITE, UI, weight=700)
    s.text(16, y+52, en, 6.4, "#FFFFFF", UI, ls="1.1")

def row(y, items, h=30, gap=7, x0=LANEX+10, wtot=LANEW-20, **kw):
    n = len(items); w = (wtot - gap*(n-1))/n
    xs = []
    for i, it in enumerate(items):
        x = x0 + i*(w+gap)
        box(s, x, y, w, h, it[0], it[1] if len(it) > 1 else None, **kw)
        xs.append((x, x+w/2, x+w))
    return xs, w

# ---- L1 hardware ----
s.text(LANEX+10, 24, "Backpack unit PMB-H (18 V zone)", 7.4, SOLAR, UI, weight=700, ls="0.4")
s.text(LANEX+424, 24, "shielded <4.2 V", 7.2, SLATE, UI, weight=700)
s.text(LANEX+520, 24, "Chest unit LIB", 7.4, VOLT, UI, weight=700)
s.rect(LANEX+8, 30, 404, 64, "#FFFFFF", SOLAR_B, 5, 1)
s.rect(LANEX+516, 30, 86, 64, "#FFFFFF", VOLT, 5, 1)
hw1, _ = row(38, [("PV panel","30 W / 18 V"), ("Protection","F·TVS·anti-rev"), ("CN3791","MPPT charger")],
             h=24, x0=LANEX+16, wtot=388, ts=7.8, ss=6.2, fill=PANEL)
hw2, _ = row(66, [("Battery A","2500 mAh"), ("Battery B","2500 mAh"), ("Q1–Q4","chg/dis sw")],
             h=24, x0=LANEX+16, wtot=388, ts=7.8, ss=6.2, fill=PANEL)
box(s, LANEX+420, 46, 92, 38, "5-core shielded", "break-away plug", fill="#FFFFFF", stroke=LINE,
    ts=7.0, ss=6.0, title_fam=UI)
box(s, LANEX+522, 38, 74, 24, "hold-up cap", None, fill=PANEL, ts=6.8, title_fam=UI)
box(s, LANEX+522, 66, 74, 24, "BITalino", None, fill=PANEL, ts=7.6, title_fam=UI)

# ---- L2 firmware ----
fw, _ = row(132, [("drivers","INA226·NTC"), ("power FSM","5-state+hyst"), ("batt switch","interlock+dead"),
                  ("coulomb ctr","bidir integ"), ("sync pulse","hw timestamp"), ("BLE telem","+ offline log")],
            h=34, ts=7.6, ss=5.8, fill=WHITE, accent=OK, title_fam=UI)
s.text(LANEX+10, 180, "XIAO nRF52840 · Zephyr · pure-logic FSM is unit-testable on PC", 7.0, SLATE, UI)
s.text(LANEX+10, 196, "watchdog fail → GPIO hi-Z → load switch defaults OFF (fail-safe)", 7.0, MUTED, UI)

# ---- L3 software ----
sw, _ = row(246, [("collectors","bleak / pyserial"), ("time align","sync-marker fit"),
                  ("processing","NeuroKit2 · HRV"), ("energy","EAR / RES"), ("dashboard","Grafana")],
            h=34, ts=7.6, ss=6.0, fill=WHITE, accent=VOLT, title_fam=UI)
s.text(LANEX+10, 294, "3 sources: BITalino DUT · BITalino CTRL · power telemetry — persisted after hw-sync alignment",
       7.0, SLATE, UI)
s.text(LANEX+10, 310, "fits the true sample rate and reports clock drift in ppm — main error in long recordings",
       7.0, MUTED, UI)

# ---- L4 data ----
dt, _ = row(356, [("raw signals","Parquet immutable"), ("time series","TimescaleDB"),
                  ("Run Manifest","fw SHA + hw hash"), ("CI checks","schema + golden")],
            h=34, ts=7.6, ss=6.0, fill=WHITE, accent=PURP, title_fam=UI)
s.text(LANEX+10, 404, "every run traceable to its fw commit, hw version, calibrated capacity & measured irradiance",
       7.0, SLATE, UI)

# ---- inter-layer arrows ----
for x in (LANEX+90, LANEX+300, LANEX+500):
    s.arrow(x, 112, x, 126, MUTED, 1.1)
    s.arrow(x, 218, x, 240, MUTED, 1.1)
    s.arrow(x, 328, x, 350, MUTED, 1.1)
s.text(LANEX+96, 122, "I²C / GPIO", 6.4, MUTED, MONO)
s.text(LANEX+306, 236, "BLE / BT", 6.4, MUTED, MONO)
s.text(LANEX+506, 346, "write", 6.4, MUTED, UI)

# bottom rule strip
s.rect(6, 428, W-12, 18, "#F1F4F9", None, 4)
s.text(16, 440, "Two stack-wide rules: ①  energy and measurement chains are separated in time (no charging while acquiring)   ②  every experiment must reproduce",
       7.0, DEEP, UI, weight=700)

open(os.path.join(os.path.dirname(__file__), "..", "assets/svg-en/sys-arch.svg"), "w").write(s.out())
print("sys-arch.svg (en)", W, "x", H)
