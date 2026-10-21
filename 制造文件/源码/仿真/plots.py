"""Figures for 仿真报告.md — static PNGs, reference palette (light), one y-axis per panel."""
import sys, json, numpy as np; sys.path.insert(0, ".")
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from ngs import NGS
import tb_charger as TC
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"; SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 2,
                     "font.size": 10, "axes.titlesize": 11, "axes.titlecolor": INK, "legend.frameon": False, "font.family": ["PingFang SC", "Heiti SC", "Arial Unicode MS", "sans-serif"]})
def save(fig, name): fig.tight_layout(); fig.savefig(f"plots/{name}", dpi=160); plt.close(fig); print("wrote", name)

# 1 — panel P-V curves and the MPPT set point
fig, ax = plt.subplots(figsize=(7, 3.6))
for T, c in ((-10, S1), (25, S2), (55, S3)):
    s = NGS(); s.run(f"pv\n{TC.LIB}\n.options TEMP={T} TNOM=25\nX_PV p 0 PV12 PARAMS: G=1000 RSH=3k\nVt p 0 DC 0\n.dc Vt 0 9 0.01\n.end")
    v = s.vec("v-sweep"); p = v * s.vec("vt#branch"); m = p > 0
    k = np.argmax(p); ax.plot(v[m], p[m], color=c, label=f"{T} °C：Vmp {v[k]:.2f} V，Pmax {p[k]:.2f} W"); ax.plot(v[k], p[k], "o", color=c, ms=6, mec=SURF, mew=2)
ax.axvline(5.93, color=INK2, lw=1, ls="--"); ax.text(5.85, 0.4, "MPPT 设定 5.93 V\n(R5 200k / R6 51k)", color=INK2, fontsize=9, ha="right")
ax.set_xlabel("面板电压 V"); ax.set_ylabel("面板功率 W"); ax.set_title("6 V / 6 W 面板 P–V 曲线（1000 W/m²）"); ax.set_xlim(0, 9.2); ax.set_ylim(0, 6.6); ax.legend(loc="upper left")
save(fig, "fig1_pv.png")

# 2 — switching waveforms, 1000 W/m², 25 °C, battery 3.7 V (steady state, last 4 cycles)
s = NGS(); s.run(TC.netlist(1000, 25, 3.7, tstop=8e-3)); t = s.vec("time"); m = t > 8e-3 - 13.3e-6; tt = (t[m] - t[m][0]) * 1e6
il = (s.vec("lx")[m] - s.vec("csp")[m]) / 0.09
fig, axs = plt.subplots(3, 1, figsize=(7, 5.4), sharex=True)
axs[0].plot(tt, s.vec("sw")[m], color=S1); axs[0].set_ylabel("开关节点 V"); axs[0].set_title("CN3791 稳态开关波形（1000 W/m²、25 °C、电池 3.7 V）")
axs[1].plot(tt, il, color=S2); axs[1].set_ylabel("电感电流 A"); axs[1].axhline(1.8, color=INK2, lw=1, ls="--"); axs[1].text(0.2, 1.62, "SWPA6045 22 µH 饱和 1.8 A", color=INK2, fontsize=9); axs[1].set_ylim(0, 2.0)
axs[2].plot(tt, s.vec("vpv")[m], color=S3); axs[2].set_ylabel("面板端 VPV V"); axs[2].set_xlabel("时间 µs")
save(fig, "fig2_switching.png")

# 3 — MPPT capture and battery current vs irradiance (long run results)
R = [r for r in json.load(open("tb_charger_final.json")) if abs(r["vbat"] - 3.7) < 0.01 and r["settled"]]
R = sorted({r["G"]: r for r in R if not (r["G"] == 1000 and r["T"] != 55)}.values(), key=lambda r: r["G"])
G = [r["G"] for r in R]; x = np.arange(len(G))
fig, axs = plt.subplots(2, 1, figsize=(7, 5), sharex=True)
for a_ in axs: a_.set_axisbelow(True); a_.grid(axis="x", visible=False)
cap = [100 * r["capture"] for r in R]; axs[0].bar(x, cap, width=0.6, color=S1); axs[0].set_ylabel("MPPT 捕获率 %"); axs[0].set_ylim(0, 110)
axs[0].set_title("各光照下：面板功率利用率与充电电流（电池 3.7 V）")
for i, v in enumerate(cap): axs[0].text(i, v + 2, f"{v:.0f}%", ha="center", color=INK, fontsize=9)
ib = [r["ibat"] * 1e3 + 8 for r in R]; axs[1].bar(x, ib, width=0.6, color=S2); axs[1].set_ylabel("充电器输出 mA")
for i, v in enumerate(ib): axs[1].text(i, v + 15, f"{v:.0f}", ha="center", color=INK, fontsize=9)
axs[1].set_xticks(x, [f"{g}" for g in G]); axs[1].set_xlabel("光照 W/m²（1000 W/m² 为 55 °C 面板温度；10 W/m² 未到稳态，未画）")
save(fig, "fig3_capture.png")

# 4 — load-switch inrush, battery 4.2 V
src = open("tb_lib.py", encoding="utf-8").read(); ns = {}; exec(compile(src[:src.index("s = sim(lib_net(")], "h", "exec"), ns)
fig, ax = plt.subplots(figsize=(7, 3.4))
for c10, col, lab in (("100n", S2, "C10 = 100 nF（原设计）"), ("1u", S1, "C10 = 1 µF（已改）")):
    s = NGS(); s.run(ns["lib_net"](t_cable_pull=50, t_end=1.03, c10=c10, vb=4.2).replace(".tran 2m 1.03 0 50m uic", ".tran 1u 1.03 0 10u uic"))
    t = s.vec("time"); k = (t > 0.999) & (t < 1.025); ib = (s.vec("bocv") - s.vec("vsys")) / 0.08
    ax.plot((t[k] - 1.0) * 1e3, ib[k], color=col, label=lab); j = np.argmax(ib[k]); ax.annotate(f"峰值 {ib[k][j]:.2f} A", ((t[k][j] - 1) * 1e3, ib[k][j]), xytext=(8, -4), textcoords="offset points", color=INK2, fontsize=9)
ax.set_xlabel("LOAD_EN 拉高后的时间 ms"); ax.set_ylabel("电池电流 A"); ax.set_title("负载开关上电浪涌（电池 4.2 V，胸前 LIB + Core B 负载）"); ax.legend(loc="upper right")
save(fig, "fig4_inrush.png")

# 5 — LIB cable pull at t = 700 s
d = np.load("tb5.npy"); t, vbit, vsc, vload, ib = d.T; k = (t > 690) & (t < 770)
fig, ax = plt.subplots(figsize=(7, 3.4))
ax.axvspan(0, 60, color=GRID, alpha=0.5, lw=0); ax.text(1, 3.93, "背部线缆断开 60 s", color=INK2, fontsize=9)
ax.plot(t[k] - 700, vsc[k], color=S3, label="VSC（超级电容串）"); ax.plot(t[k] - 700, vbit[k], color=S1, label="VBIT（Core B 电源）")
ax.axhline(3.3, color=INK2, lw=1, ls="--"); ax.text(69, 3.24, "3.3 V 欠压（估计）", color=INK2, fontsize=9, ha="right", va="top")
ax.set_xlabel("拔线后的时间 s"); ax.set_ylabel("电压 V"); ax.set_ylim(3.0, 4.0); ax.set_title("胸前 LIB：拔线 60 s 再插回（Core B 65 mA）"); ax.legend(loc="upper right")
save(fig, "fig5_holdup.png")

# 6 — MPPT loop Bode plot, 400 W/m², gm = 5 mA/V (worst plausible), without vs with C15
import loop_ss as LS
f = np.logspace(2, 5, 1500); ipv, r_pv = LS.pv_point(400, 37)
fig, axs = plt.subplots(2, 1, figsize=(7, 5.2), sharex=True)
for damp, col, lab in ((None, S2, "只有陶瓷电容（改前）"), ((100e-6, 0.6), S1, "加 C15 100 µF 电解（改后）")):
    Tl = LS.loop(f, 0.66, 5.93, 0.47, r_pv, 5e-3, damp); m = LS.margins(f, Tl)
    gm_txt = "增益裕度 ∞" if m["gm_db"] is None else f"增益裕度 {m['gm_db']:.0f} dB"
    lab = f"{lab}：相位裕度 {m['pm']:.0f}°，{gm_txt}"
    axs[0].semilogx(f, 20 * np.log10(np.abs(Tl)), color=col, label=lab)
    axs[1].semilogx(f, np.unwrap(np.angle(Tl)) * 180 / np.pi, color=col, label=lab)
axs[0].axhline(0, color=INK2, lw=1); axs[1].axhline(-180, color=INK2, lw=1, ls="--")
axs[0].set_ylabel("回路增益 dB"); axs[1].set_ylabel("相位 °"); axs[1].set_xlabel("频率 Hz")
axs[0].set_title("MPPT 环路（400 W/m²，误差放大器跨导取 5 mA/V）"); axs[0].legend(loc="upper right")
save(fig, "fig6_loop.png")
