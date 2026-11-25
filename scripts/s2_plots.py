"""Step 3: station-wise AQI graphs, all-station comparison and seasonal box plots."""
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as mdates
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
OUT = sys.argv[1]; FIG = sys.argv[2]
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.edgecolor":"#8a8985","axes.labelcolor":"#0b0b0b",
                     "xtick.color":"#52514e","ytick.color":"#52514e","axes.spines.top":False,"axes.spines.right":False})
INK, INK2 = "#0b0b0b", "#52514e"
# CPCB AQI category colours (official), used as light background tints
BANDS = [(0,50,"Good","#00b050"),(50,100,"Satisfactory","#92d050"),(100,200,"Moderate","#ffff00"),
         (200,300,"Poor","#ff9900"),(300,400,"Very Poor","#ff0000"),(400,500,"Severe","#c00000")]
SEAS = ["Winter","Summer","Monsoon","Post-monsoon"]
SCOL = {"Winter":"#2a78d6","Summer":"#eb6834","Monsoon":"#1baf7a","Post-monsoon":"#eda100"}
D = pd.read_csv(f"{OUT}/daily_AQI_long.csv", parse_dates=["date"])
M = pd.read_csv(f"{OUT}/monthly_AQI_long.csv")
Y = pd.read_csv(f"{OUT}/annual_station_summary.csv")
order = list(Y.sort_values("annual_mean_season_balanced", ascending=False).station)
ymax = 400

def bands(ax, top):
    for lo, hi, name, c in BANDS:
        if lo >= top: break
        ax.axhspan(lo, min(hi, top), color=c, alpha=0.16, lw=0, zorder=0)
        ax.text(1.005, (lo + min(hi, top)) / 2, name, transform=ax.get_yaxis_transform(), va="center", fontsize=8, color=INK2)

def station_plot(ax, st, small=False):
    d = D[D.station == st].set_index("date").reindex(pd.date_range("2025-01-01","2025-12-31")).daily_AQI
    m = M[M.station == st].set_index("month").mean_AQI.reindex(range(1, 13))
    bands(ax, ymax) if not small else [ax.axhspan(lo, min(hi,ymax), color=c, alpha=0.16, lw=0, zorder=0) for lo,hi,_,c in BANDS if lo < ymax]
    ax.plot(d.index, d.values, color="#2a2a28", lw=0.9 if not small else 0.6, zorder=3, label="Daily AQI")
    ax.scatter(d.index, d.values, s=6 if not small else 1.5, color="#2a2a28", zorder=3, lw=0)
    mid = [pd.Timestamp(2025, k, 15) for k in m.index]
    ax.plot(mid, m.values, color="#2a78d6", lw=2.2, marker="o", ms=6 if not small else 3, zorder=4,
            markeredgecolor="white", markeredgewidth=1.2, label="Monthly mean")
    if not small:
        for x, v in zip(mid, m.values):
            if np.isnan(v): continue
            ax.annotate(f"{v:.0f}", (x, v), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8, color="#1c5cab", zorder=5)
    # missing-data shading
    miss = d.isna()
    for x in d.index[miss]:
        ax.axvspan(x, x + pd.Timedelta("1D"), color="#d9d8d4", alpha=0.6, lw=0, zorder=1)
    ax.set_xlim(pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31")); ax.set_ylim(0, ymax)
    ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.grid(axis="y", color="#e4e3df", lw=0.6, zorder=0)

names = {s: s for s in order}
for i, st in enumerate(order, 1):
    y = Y.set_index("station").loc[st]
    fig, ax = plt.subplots(figsize=(12, 4.6), dpi=200)
    station_plot(ax, st)
    ax.set_ylabel("AQI (CPCB National AQI)")
    ax.set_title(f"{st} ({y.city}) — daily AQI, Jan–Dec 2025", loc="left", fontsize=13, color=INK, fontweight="bold", pad=22)
    ax.text(0, 1.02, f"Annual mean {y.annual_mean:.0f} (season-balanced {y.annual_mean_season_balanced:.0f}) · Winter {y.Winter:.0f} · Summer {y.Summer:.0f} · "
            f"Monsoon {y.Monsoon:.0f} · Post-monsoon {y['Post-monsoon']:.0f} · Valid days {int(y.valid_days)}/365 · Days AQI>100: {int(y['exceed_days_>100'])}",
            transform=ax.transAxes, fontsize=8.5, color=INK2)
    h = [Line2D([],[],color="#2a2a28",lw=1,marker="o",ms=3,label="Daily AQI (≥18 valid h)"),
         Line2D([],[],color="#2a78d6",lw=2.2,marker="o",ms=6,markeredgecolor="white",label="Monthly mean AQI"),
         Patch(color="#d9d8d4",label="No valid data")]
    ax.legend(handles=h, loc="upper center", ncol=3, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, -0.08))
    fig.text(0.01, 0.01, "Source: CPCB CAAQMS hourly AQI (WBPCB), cleaned; background bands = CPCB AQI categories", fontsize=7, color=INK2)
    fig.tight_layout(); fig.savefig(f"{FIG}/{i:02d}_AQI_{st.replace(' ','_').replace('.','')}.png"); plt.close(fig)

# 12-panel overview
fig, axs = plt.subplots(4, 3, figsize=(16, 13), dpi=180, sharex=True, sharey=True)
for ax, st in zip(axs.ravel(), order):
    station_plot(ax, st, small=True)
    y = Y.set_index("station").loc[st]
    ax.set_title(f"{st} ({y.city}) — annual mean {y.annual_mean_season_balanced:.0f}", fontsize=10, loc="left", color=INK)
for ax in axs[:, 0]: ax.set_ylabel("AQI")
h = [Line2D([],[],color="#2a2a28",lw=1,label="Daily AQI"), Line2D([],[],color="#2a78d6",lw=2.2,marker="o",label="Monthly mean")] + \
    [Patch(color=c, alpha=0.35, label=n) for _,_,n,c in BANDS[:5]]
fig.legend(handles=h, loc="lower center", ncol=7, frameon=False)
fig.suptitle("Daily AQI at 12 CAAQMS stations, Kolkata–Howrah, 2025 (sorted by season-balanced annual mean)", fontsize=14, fontweight="bold", x=0.01, ha="left")
fig.tight_layout(rect=(0, 0.03, 1, 0.97)); fig.savefig(f"{FIG}/13_AQI_all_stations_panel.png"); plt.close(fig)

# All-station comparison: heatmap station x month
W = M.pivot(index="station", columns="month", values="mean_AQI").reindex(order)
fig, ax = plt.subplots(figsize=(12, 6.2), dpi=200)
from matplotlib.colors import ListedColormap, BoundaryNorm
cmap = ListedColormap([c for *_, c in BANDS]); norm = BoundaryNorm([0,50,100,200,300,400,500], cmap.N)
ax.imshow(W.values, cmap=cmap, norm=norm, aspect="auto", alpha=0.85)
for i in range(W.shape[0]):
    for j in range(W.shape[1]):
        v = W.values[i, j]
        nd = M[(M.station == W.index[i]) & (M.month == j + 1)].valid_days
        star = "*" if (len(nd) and nd.iloc[0] < 15) else ""
        ax.text(j, i, "–" if np.isnan(v) else f"{v:.0f}{star}", ha="center", va="center", fontsize=9,
                color="white" if (not np.isnan(v) and v > 300) else INK)
ax.set_xticks(range(12)); ax.set_xticklabels(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"])
ax.set_yticks(range(len(order))); ax.set_yticklabels([f"{s} ({Y.set_index('station').loc[s,'city'][0]})" for s in order])
ax.set_xticks(np.arange(-.5, 12, 1), minor=True); ax.set_yticks(np.arange(-.5, len(order), 1), minor=True)
ax.grid(which="minor", color="white", lw=2); ax.tick_params(which="minor", length=0)
for s in ["left","bottom"]: ax.spines[s].set_visible(False)
for x in [1.5, 4.5, 8.5, 10.5]: ax.axvline(x, color=INK, lw=1.2)
for x, n in [(0.5,"Winter"),(3,"Summer"),(6.5,"Monsoon"),(9.5,"Post-monsoon"),(11,"Winter")]:
    ax.text(x, -0.8, n, ha="center", fontsize=9, color=INK2)
ax.legend(handles=[Patch(color=c, alpha=0.85, label=f"{n} ({lo}–{hi})") for lo, hi, n, c in BANDS[:5]], loc="upper center",
          bbox_to_anchor=(0.5, -0.06), ncol=5, frameon=False, fontsize=8.5)
fig.text(0.01, 0.005, "* fewer than 15 valid days in the month;  – no valid data", fontsize=8, color=INK2)
ax.set_title("Monthly mean AQI by station, 2025 (K = Kolkata, H = Howrah; colour = CPCB category)", loc="left", fontsize=13, fontweight="bold", pad=24)
fig.tight_layout(); fig.savefig(f"{FIG}/14_AQI_station_month_heatmap.png"); plt.close(fig)

# All-station seasonal comparison (grouped bars)
S = pd.read_csv(f"{OUT}/../01_AQI/daily_AQI_long.csv", parse_dates=["date"]) if False else None
SW = Y.set_index("station").loc[order, SEAS]
fig, ax = plt.subplots(figsize=(13, 5.2), dpi=200)
x = np.arange(len(order)); w = 0.2
for k, s in enumerate(SEAS):
    ax.bar(x + (k - 1.5) * w, SW[s], w * 0.9, color=SCOL[s], label=s, zorder=3)
ax.plot(x, Y.set_index("station").loc[order, "annual_mean_season_balanced"], "D", color=INK, ms=6, zorder=4, label="Annual (season-balanced)")
for lo, hi, n, c in BANDS[1:4]: ax.axhline(lo, color=INK2, lw=0.6, ls="--", zorder=2); ax.text(len(order)-0.45, lo + 3, f"{n[:3] if False else ''}{lo}", fontsize=7, color=INK2)
ax.set_xticks(x); ax.set_xticklabels(order, rotation=30, ha="right"); ax.set_ylabel("Mean AQI")
ax.grid(axis="y", color="#e4e3df", lw=0.6, zorder=0); ax.legend(ncol=5, frameon=False, loc="upper right", fontsize=9)
ax.set_title("Seasonal mean AQI by station, 2025 (dashed lines: CPCB category limits 50 / 100 / 200)", loc="left", fontsize=13, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{FIG}/15_AQI_seasonal_by_station_bars.png"); plt.close(fig)

# Seasonal box plots: pooled + per station
V = D[D.valid_day].copy()
fig, ax = plt.subplots(figsize=(8, 5.2), dpi=200)
bands(ax, 450)
data = [V[V.season == s].daily_AQI.values for s in SEAS]
bp = ax.boxplot(data, widths=0.55, patch_artist=True, showfliers=True, medianprops=dict(color=INK, lw=1.6),
                flierprops=dict(marker="o", ms=2.5, markerfacecolor=INK2, markeredgecolor="none", alpha=0.5), zorder=3)
for p, s in zip(bp["boxes"], SEAS): p.set_facecolor(SCOL[s]); p.set_edgecolor(INK); p.set_alpha(0.9)
for i, s in enumerate(SEAS, 1):
    v = V[V.season == s].daily_AQI
    ax.text(i, 455 * 0.97, f"mean {v.mean():.0f}\nn={len(v)}", ha="center", va="top", fontsize=8, color=INK2)
ax.set_xticklabels(["Winter\n(Jan, Feb, Dec)","Summer\n(Mar–May)","Monsoon\n(Jun–Sep)","Post-monsoon\n(Oct–Nov)"])
ax.set_ylim(0, 455); ax.set_ylabel("Daily AQI (all 12 stations)")
ax.set_title("Seasonal distribution of daily AQI, Kolkata–Howrah 2025", loc="left", fontsize=12.5, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{FIG}/16_AQI_seasonal_boxplot_pooled.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(15, 5.8), dpi=200)
bands(ax, 450)
pos, dat, col = [], [], []
for i, st in enumerate(order):
    for k, s in enumerate(SEAS):
        pos.append(i * 5 + k); dat.append(V[(V.station == st) & (V.season == s)].daily_AQI.values); col.append(SCOL[s])
bp = ax.boxplot(dat, positions=pos, widths=0.75, patch_artist=True, medianprops=dict(color=INK, lw=1.2),
                flierprops=dict(marker="o", ms=1.8, markerfacecolor=INK2, markeredgecolor="none", alpha=0.5), zorder=3)
for p, c in zip(bp["boxes"], col): p.set_facecolor(c); p.set_edgecolor(INK); p.set_linewidth(0.7)
ax.set_xticks([i * 5 + 1.5 for i in range(len(order))]); ax.set_xticklabels(order, rotation=25, ha="right")
ax.set_xlim(-1, len(order) * 5 - 1); ax.set_ylim(0, 455); ax.set_ylabel("Daily AQI")
ax.legend(handles=[Patch(facecolor=SCOL[s], edgecolor=INK, label=s) for s in SEAS], ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.0))
ax.set_title("Seasonal box plots of daily AQI by station, 2025", loc="left", fontsize=13, fontweight="bold", pad=18)
fig.tight_layout(); fig.savefig(f"{FIG}/17_AQI_seasonal_boxplot_by_station.png"); plt.close(fig)
print("done")
