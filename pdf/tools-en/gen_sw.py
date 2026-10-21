import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from dotkit import *
OUT = os.path.join(os.path.dirname(__file__), "..", "src-en/dot")

b = chip("SRC","sources  ×3", [
      ("a","BITalino DUT","solar-powered · ECG A1 · 1000 Hz"),
      ("b","BITalino CTRL","battery-only control · same lead"),
      ("c","PMB telemetry","power / SoC / temp / irradiance · 1 Hz")], sub="three independent radio links", hdr=SOLAR)
b += chip("COL","collectors", [
      ("a","bitalino_ble.py","bleak · GATT"),
      ("b","bitalino_bt.py","pyserial · SPP"),
      ("c","pmb_ble.py","custom GATT + replay dedup")], sub="asyncio · back-pressure & reconnect", hdr=VOLT)
b += chip("SYN","sync  engine", [
      ("a","marker_align","detect I1 rising edge ↔ MCU µs stamps"),
      ("b","clock_fit","linear fit → true rate + drift ppm"),
      ("c","residual check","residual >2 samples → flag segment")],
      sub="software side of ADR-005 · error <10 ms, provable", hdr=PURP)
part_a = b
b = chip("STO","storage", [
      ("a","Parquet","raw signals · read-only after write"),
      ("b","TimescaleDB","power_samples hypertable + events"),
      ("c","manifest","fw SHA · hw hash · calib capacity")], sub="raw immutable · processing re-runnable", hdr=OK)
b += chip("PROC","processing", [
      ("a","ecg_quality","0.5–40 Hz noise floor µVrms · baseline drift"),
      ("b","hrv","NeuroKit2 · R peaks · SDNN / RMSSD"),
      ("c","energy","EAR / RES / autonomy"),
      ("d","agreement","Bland-Altman: DUT vs control")], sub="all re-runnable, never overwrites raw", hdr=VOLT)
b += chip("OUT","delivery", [("a","Grafana","live energy & temp dashboard"),
      ("b","report.ipynb","one per TC, committed to Git"),
      ("c","CI","schema checks + golden cases + fw SHA exists")], sub="", hdr=DEEP)
part_b = b
open(os.path.join(OUT,"sw-ingest.dot"),"w").write(render(
    part_a + edge("SRC:a_o:e","COL:a:w","",SLATE,1.2) + edge("COL:a_o:e","SYN:a:w","",SLATE,1.2),
    rankdir="LR", ranksep=0.65))
open(os.path.join(OUT,"sw-serve.dot"),"w").write(render(
    part_b + edge("STO:a_o:e","PROC:a:w","",SLATE,1.2) + edge("PROC:a_o:e","OUT:a:w","",SLATE,1.2),
    rankdir="LR", ranksep=0.65))
print("sw dot written (en)")
