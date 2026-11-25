"""Fig 3: monthly AQI trend - network mean with station range, plus daily city mean, CPCB category bands."""
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
OUT = sys.argv[1]; INK, INK2 = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False})
BANDS = [(0, 50, "Good", "#00b050"), (50, 100, "Satisfactory", "#92d050"), (100, 200, "Moderate", "#ffff00"), (200, 300, "Poor", "#ff9900"), (300, 400, "Very Poor", "#ff0000")]
M = pd.read_csv(f"{OUT}/01_AQI/monthly_AQI_long.csv"); D = pd.read_csv(f"{OUT}/01_AQI/daily_AQI_long.csv", parse_dates=["date"])
W = M.pivot(index="month", columns="station", values="mean_AQI")
city = D[D.valid_day].groupby("date").daily_AQI.mean()
fig, ax = plt.subplots(figsize=(8.6, 4.4), dpi=230)
for lo, hi, n, c in BANDS[:4]:
    ax.axhspan(lo, hi, color=c, alpha=0.13, lw=0, zorder=0); ax.text(12.62, (lo + hi) / 2, n, fontsize=7.5, color=INK2, va="center")
x = city.index.dayofyear / 365 * 12 + 0.5
ax.plot(x, city.values, color="#9a9a96", lw=0.7, zorder=2, label="Daily city mean")
ax.fill_between(W.index, W.min(axis=1), W.max(axis=1), color="#2a78d6", alpha=0.18, zorder=3, label="Range across 12 stations (monthly mean)")
ax.plot(W.index, W.mean(axis=1), color="#1c5cab", lw=2.4, marker="o", ms=6, mec="white", mew=1.2, zorder=5, label="Network monthly mean")
hi_st = W.idxmax(axis=1); lo_st = W.idxmin(axis=1)
for m in W.index:
    ax.annotate(f"{W.mean(axis=1)[m]:.0f}", (m, W.mean(axis=1)[m]), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8, color="#1c5cab", fontweight="bold")
for m in [1, 12]:
    ax.annotate(f"highest: {hi_st[m]} {W.max(axis=1)[m]:.0f}", (m, W.max(axis=1)[m]), xytext=(6 if m == 1 else -8, -2), textcoords="offset points", fontsize=7.2, color=INK2, ha="left" if m == 1 else "right", va="top")
ax.annotate(f"lowest: {lo_st[7]} {W.min(axis=1)[7]:.0f}", (7, W.min(axis=1)[7]), xytext=(0, -12), textcoords="offset points", fontsize=7.2, color=INK2, ha="center")
for xs, name in [(1.5, "Winter"), (4, "Summer"), (7.5, "Monsoon"), (10.5, "Post-monsoon"), (12, "Win.")]:
    ax.text(xs, 322, name, ha="center", fontsize=8, color=INK2)
for b in [2.5, 5.5, 9.5, 11.5]: ax.axvline(b, color=INK2, lw=0.7, ls=":", zorder=1)
ax.set_xlim(0.5, 12.5); ax.set_ylim(0, 335)
ax.set_xticks(range(1, 13)); ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
ax.set_ylabel("AQI (CPCB National AQI)"); ax.grid(axis="y", color="#e4e3df", lw=0.6)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=3, frameon=False, fontsize=8.2)
fig.tight_layout(); fig.savefig(f"{OUT}/02_Graphs/Fig3_monthly_AQI_trend.png"); plt.close(fig)
print(W.mean(axis=1).round(0).to_dict()); print(hi_st.to_dict())
