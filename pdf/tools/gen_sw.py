import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dotkit import *
OUT = os.path.join(os.path.dirname(__file__), "..", "src/dot")

b = chip("SRC","数据源  ×3", [
      ("a","BITalino DUT","太阳能供电 · ECG A1 · 1000 Hz"),
      ("b","BITalino CTRL","纯电池对照 · 同导联"),
      ("c","PMB 遥测","功率 / SoC / 温度 / 辐照度 · 1 Hz")], sub="三条独立无线链路", hdr=SOLAR)
b += chip("COL","collectors", [
      ("a","bitalino_ble.py","bleak · GATT"),
      ("b","bitalino_bt.py","pyserial · SPP"),
      ("c","pmb_ble.py","自定义 GATT + 补传去重")], sub="asyncio · 背压与重连", hdr=VOLT)
b += chip("SYN","sync  引擎", [
      ("a","marker_align","检测 I1 上升沿 ↔ MCU µs 时间戳"),
      ("b","clock_fit","线性回归 → 真实采样率 + 漂移 ppm"),
      ("c","residual check","残差 >2 样点 → 该段标记为可疑")],
      sub="ADR-005 的软件侧 · 误差 <10 ms 且可证明", hdr=PURP)
part_a = b
b = chip("STO","storage", [
      ("a","Parquet","原始信号 · 写入后只读"),
      ("b","TimescaleDB","power_samples 超表 + events"),
      ("c","manifest","固件 SHA · 硬件哈希 · 标定容量")], sub="原始不可变 · 处理可重跑", hdr=OK)
b += chip("PROC","processing", [
      ("a","ecg_quality","0.5–40 Hz 噪声底 µVrms · 基线漂移"),
      ("b","hrv","NeuroKit2 · R 峰 · SDNN / RMSSD"),
      ("c","energy","EAR / RES / 自主度"),
      ("d","agreement","Bland-Altman：DUT vs 对照")], sub="全部可重跑，不覆盖原始数据", hdr=VOLT)
b += chip("OUT","交付", [("a","Grafana","实时能量与温度看板"),
      ("b","report.ipynb","每个 TC 一份，进 Git"),
      ("c","CI","schema 校验 + 黄金用例 + fw SHA 存在性")], sub="", hdr=DEEP)
A = "".join(x for x in (SRC_, COL_, SYN_)) if False else None
part_b = b
open(os.path.join(OUT,"sw-ingest.dot"),"w").write(render(
    part_a + edge("SRC:a_o:e","COL:a:w","",SLATE,1.2) + edge("COL:a_o:e","SYN:a:w","",SLATE,1.2),
    rankdir="LR", ranksep=0.65))
open(os.path.join(OUT,"sw-serve.dot"),"w").write(render(
    part_b + edge("STO:a_o:e","PROC:a:w","",SLATE,1.2) + edge("PROC:a_o:e","OUT:a:w","",SLATE,1.2),
    rankdir="LR", ranksep=0.65))
print("sw dot written")
