import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotkit import *
OUT = os.path.join(os.path.dirname(__file__), "..", "src-en/dot")

def state(nid, name, en, load, chg, duty, tele, fill, border):
    name, en = esc(name), esc(en)
    rows = [f'<TR><TD COLSPAN="2" BGCOLOR="{border}" ALIGN="LEFT">'
            f'<FONT FACE="{MONO}" POINT-SIZE="7.4" COLOR="#FFFFFF"><B>{name}</B></FONT>'
            f'<BR/><FONT FACE="{UI}" POINT-SIZE="5.6" COLOR="#E8EEF8">{en}</FONT></TD></TR>']
    for k, v in (("load", load), ("chg", chg), ("duty", duty), ("telem", tele)):
        rows.append(f'<TR><TD ALIGN="LEFT"><FONT FACE="{CJK}" POINT-SIZE="6.6" COLOR="{MUTED}">{k}</FONT></TD>'
                    f'<TD ALIGN="LEFT"><FONT FACE="{CJK}" POINT-SIZE="6.8" COLOR="{INK}">{esc(v)}</FONT></TD></TR>')
    return (f'  {nid} [label=<<TABLE BORDER="1" COLOR="{border}" CELLBORDER="0" CELLSPACING="0" '
            f'CELLPADDING="3" BGCOLOR="{fill}">' + "".join(rows) + '</TABLE>>];\n')

b  = state("BOOT",     "BOOT",         "self-test",   "OFF", "ON",  "—",    "—",    "#F4F6FA", SLATE)
b += state("CRIT",     "CRITICAL",     "SoC < 10%",   "OFF", "ON",  "0%",   "60 s", RISK_L,  RISK)
b += state("HARV",     "HARVEST_ONLY", "10–30%",      "OFF", "ON",  "0%",   "30 s", SOLAR_L, SOLAR)
b += state("DUTY",     "DUTY_CYCLE",   "30–40%",      "periodic", "off while acq", "dflt 3%", "10 s", "#FFFDF6", SOLAR)
b += state("FULL",     "FULL_RATE",    "SoC ≥ 40%",   "ON",  "alternating", "100%", "1 s",  OK_L,    OK)
b += state("FAULT",    "FAULT",        "manual check", "OFF", "OFF", "0%",   "60 s", RISK_L,  RISK)

E = [("BOOT","CRIT","SoC<10"), ("BOOT","FULL","SoC≥40"),
     ("CRIT","HARV",">15%"), ("HARV","DUTY",">35%"), ("DUTY","FULL",">40%"),
     ("FULL","DUTY","<35%"), ("DUTY","HARV","<25%"), ("HARV","CRIT","<8%")]
for a, c, l in E:
    b += edge(a, c, l, SLATE, 1.0)
b += edge("CRIT","FAULT","Vbat<3.2 V or T out", RISK, 1.2, "dashed")
b += ('  {rank=same; CRIT; HARV;}\n  {rank=same; DUTY; FULL;}\n')
open(os.path.join(OUT,"fw-fsm.dot"),"w").write(render(b, rankdir="LR", nodesep=0.35, ranksep=0.75))

# ── firmware modules ──
b  = chip("HAL","drivers  /  HAL", [
      ("a","drv_ina226","bidir current · bus voltage · 16 bit"),
      ("b","drv_ntc","ADC + Steinhart-Hart"),
      ("c","load_switch","soft start · watchdog fail-safe"),
      ("d","battery_switch","⚠ 4 invariants · 1 ms dead time"),
      ("e","sync_marker","GPIO pulse + µs timestamp")], sub="the only layer touching hardware", hdr=SOLAR)
b += chip("CORE","core  (no hardware calls)", [
      ("a","power_fsm","§ FSM · hysteresis ≥5 pct pts"),
      ("b","coulomb_counter","∫I dt · recalib on full/empty"),
      ("c","scheduler","acq windows · 30-min batt rotation")],
      sub="pure logic → unit-testable & fuzzable on PC", hdr=OK)
b += chip("IO","transport", [
      ("a","ble_telemetry","GATT: PowerSample / SyncMarker / Config / Fault"),
      ("b","nvs_log","flash on disconnect, replay on reconnect (dedup by seq)")],
      sub="disconnection is the norm, not the exception", hdr=VOLT)
b += chip("TEST","tests  (host)", [
      ("a","test_power_fsm","walk all transitions, assert invariants"),
      ("b","test_switch","inject 'reset mid-switch'",),
      ("c","fuzz","10⁶ random call sequences")], sub="runs without hardware", hdr=PURP)
b += edge("HAL:a_o:e","CORE:a:w","",SLATE,1.1) + edge("HAL:d_o:e","CORE:c:w","",SLATE,1.1)
b += edge("CORE:a_o:e","IO:a:w","",SLATE,1.1) + edge("CORE:b_o:e","IO:a:w","",SLATE,1.1)
b += edge("CORE:c_o:e","TEST:a:w","",PURP,1.0,"dashed")
open(os.path.join(OUT,"fw-modules.dot"),"w").write(render(b, rankdir="LR", ranksep=0.7))
print("fw dots written (en)")
