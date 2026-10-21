import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dotkit import *
OUT = os.path.join(os.path.dirname(__file__), "..", "src/dot")

def state(nid, name, en, load, chg, duty, tele, fill, border):
    name, en = esc(name), esc(en)
    rows = [f'<TR><TD COLSPAN="2" BGCOLOR="{border}" ALIGN="LEFT">'
            f'<FONT FACE="{MONO}" POINT-SIZE="7.4" COLOR="#FFFFFF"><B>{name}</B></FONT>'
            f'<BR/><FONT FACE="{UI}" POINT-SIZE="5.6" COLOR="#E8EEF8">{en}</FONT></TD></TR>']
    for k, v in (("负载", load), ("充电", chg), ("占空比", duty), ("遥测", tele)):
        rows.append(f'<TR><TD ALIGN="LEFT"><FONT FACE="{CJK}" POINT-SIZE="6.6" COLOR="{MUTED}">{k}</FONT></TD>'
                    f'<TD ALIGN="LEFT"><FONT FACE="{CJK}" POINT-SIZE="6.8" COLOR="{INK}">{esc(v)}</FONT></TD></TR>')
    return (f'  {nid} [label=<<TABLE BORDER="1" COLOR="{border}" CELLBORDER="0" CELLSPACING="0" '
            f'CELLPADDING="3" BGCOLOR="{fill}">' + "".join(rows) + '</TABLE>>];\n')

b  = state("BOOT",     "BOOT",         "self-test",   "OFF", "ON",  "—",    "—",    "#F4F6FA", SLATE)
b += state("CRIT",     "CRITICAL",     "SoC < 10%",   "OFF", "ON",  "0%",   "60 s", RISK_L,  RISK)
b += state("HARV",     "HARVEST_ONLY", "10–30%",      "OFF", "ON",  "0%",   "30 s", SOLAR_L, SOLAR)
b += state("DUTY",     "DUTY_CYCLE",   "30–40%",      "周期性", "采集时关", "默认 3%", "10 s", "#FFFDF6", SOLAR)
b += state("FULL",     "FULL_RATE",    "SoC ≥ 40%",   "ON",  "交替电池", "100%", "1 s",  OK_L,    OK)
b += state("FAULT",    "FAULT",        "需人工介入",   "OFF", "OFF", "0%",   "60 s", RISK_L,  RISK)

E = [("BOOT","CRIT","SoC<10"), ("BOOT","FULL","SoC≥40"),
     ("CRIT","HARV",">15%"), ("HARV","DUTY",">35%"), ("DUTY","FULL",">40%"),
     ("FULL","DUTY","<35%"), ("DUTY","HARV","<25%"), ("HARV","CRIT","<8%")]
for a, c, l in E:
    b += edge(a, c, l, SLATE, 1.0)
b += edge("CRIT","FAULT","Vbat<3.2 V 或 T 越界", RISK, 1.2, "dashed")
b += ('  {rank=same; CRIT; HARV;}\n  {rank=same; DUTY; FULL;}\n')
open(os.path.join(OUT,"fw-fsm.dot"),"w").write(render(b, rankdir="LR", nodesep=0.35, ranksep=0.75))

# ── 固件模块 ──
b  = chip("HAL","drivers  /  HAL", [
      ("a","drv_ina226","双向电流 · 总线电压 · 16 bit"),
      ("b","drv_ntc","ADC + Steinhart-Hart"),
      ("c","load_switch","软启动 · 看门狗 fail-safe"),
      ("d","battery_switch","⚠ 4 条不变式 · 死区 1 ms"),
      ("e","sync_marker","GPIO 脉冲 + µs 时间戳")], sub="唯一接触硬件的一层", hdr=SOLAR)
b += chip("CORE","core  (无硬件调用)", [
      ("a","power_fsm","§ 状态机 · 滞回 ≥5 个百分点"),
      ("b","coulomb_counter","∫I dt · 满充/深放重标定"),
      ("c","scheduler","采集窗 · 电池轮换 30 min")],
      sub="纯逻辑 → 可在 PC 上单元测试与模糊测试", hdr=OK)
b += chip("IO","transport", [
      ("a","ble_telemetry","GATT：PowerSample / SyncMarker / Config / Fault"),
      ("b","nvs_log","断连时落 flash，重连后补传（按 seq 去重）")],
      sub="断连是常态，不是异常", hdr=VOLT)
b += chip("TEST","tests  (host)", [
      ("a","test_power_fsm","遍历状态转换，断言不变式"),
      ("b","test_switch","注入「切换中途复位」",),
      ("c","fuzz","10⁶ 次随机调用序列")], sub="不上硬件即可运行", hdr=PURP)
b += edge("HAL:a_o:e","CORE:a:w","",SLATE,1.1) + edge("HAL:d_o:e","CORE:c:w","",SLATE,1.1)
b += edge("CORE:a_o:e","IO:a:w","",SLATE,1.1) + edge("CORE:b_o:e","IO:a:w","",SLATE,1.1)
b += edge("CORE:c_o:e","TEST:a:w","",PURP,1.0,"dashed")
open(os.path.join(OUT,"fw-modules.dot"),"w").write(render(b, rankdir="LR", ranksep=0.7))
print("fw dots written")
