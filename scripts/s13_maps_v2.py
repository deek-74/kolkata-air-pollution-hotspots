"""Consistent map set for the PPT: every map has lat/long border ticks, scale bar, north arrow,
the same legend frame/fonts and CPCB AQI category colours.
Fig 1 study area + station numbers | Fig 4 seasonal AQI maps (2x2) | Fig 5 GIS findings | Fig 7 station zooms."""
import sys, numpy as np, pandas as pd, geopandas as gpd, rasterio, matplotlib
from rasterio.warp import reproject, Resampling, calculate_default_transform
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch, Rectangle, Circle
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe
OUT = sys.argv[1]; G = f"{OUT}/05_GIS"; FIG = f"{OUT}/06_Maps"
INK, INK2 = "#0b0b0b", "#52514e"; HALO = [pe.withStroke(linewidth=2.6, foreground="white")]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
LAT0 = 22.56; KX = 1 / np.cos(np.radians(LAT0))
BB = (88.23, 22.45, 88.46, 22.68)
# ---- shared styling ----
AQI = [(0, 50, "Good", "#00b050"), (50, 100, "Satisfactory", "#92d050"), (100, 200, "Moderate", "#ffff00"),
       (200, 300, "Poor", "#ff9900"), (300, 400, "Very Poor", "#ff0000"), (400, 500, "Severe", "#c00000")]
def aqi_col(v): return [c for lo, hi, n, c in AQI if lo < v <= hi or (v == 0 and lo == 0)][0]
def aqi_size(v, k=1.0): return k * (40 + 4.2 * v)                 # marker area grows with AQI (same rule on every map)
CLS = {1: ("Water", "#419bdf"), 2: ("Trees", "#397d49"), 4: ("Flooded veg.", "#7a87c6"), 5: ("Crops", "#e49635"),
       7: ("Built area", "#c4281b"), 8: ("Bare ground", "#a59b8f"), 11: ("Rangeland", "#e3e2c3")}
codes = sorted(CLS); lut = np.zeros(256, int); lut[codes] = np.arange(1, len(codes) + 1)
cmap_l = ListedColormap([CLS[k][1] for k in codes]); norm_l = BoundaryNorm(np.arange(0.5, len(codes) + 1.5), len(codes))
IND = dict(facecolor="#6b3fa0", edgecolor="#3d1f66", lw=0.4, alpha=0.85)
def legend(ax, handles, title, loc="lower right", ncol=1, fs=7.2, **kw):
    lg = ax.legend(handles=handles, title=title, loc=loc, ncol=ncol, fontsize=fs, title_fontsize=fs + 0.6, frameon=True,
                   framealpha=0.95, edgecolor=INK, fancybox=False, borderpad=0.6, labelspacing=0.45, handlelength=1.6, **kw)
    lg.get_frame().set_linewidth(0.6); lg.get_title().set_fontweight("bold"); lg._legend_box.align = "left"; lg.set_zorder(30)
    return lg
def frame(ax, bb, step=0.05, fs=7.5, scale_km=2, arrow=True, label_sides=("bottom", "left")):
    ax.set_xlim(bb[0], bb[2]); ax.set_ylim(bb[1], bb[3]); ax.set_aspect(KX)
    xt = np.arange(np.ceil(bb[0] / step) * step, bb[2] + 1e-9, step); yt = np.arange(np.ceil(bb[1] / step) * step, bb[3] + 1e-9, step)
    dec = 2 if step < 0.05 or True else 2
    ax.set_xticks(xt); ax.set_yticks(yt)
    ax.set_xticklabels([f"{x:.{dec}f}°E" for x in xt], fontsize=fs); ax.set_yticklabels([f"{y:.{dec}f}°N" for y in yt], fontsize=fs, rotation=90, va="center")
    ax.tick_params(direction="in", length=4, width=0.8, top=True, right=True, labelbottom="bottom" in label_sides, labelleft="left" in label_sides, pad=2)
    ax.grid(color="#7d7c76", lw=0.3, ls=":", zorder=1); ax.set_xlabel(""); ax.set_ylabel("")
    for s in ax.spines.values(): s.set_visible(True); s.set_color(INK); s.set_linewidth(1.0)
    # scale bar (alternating), bottom-left
    km = 1 / (111.32 * np.cos(np.radians(LAT0))); w = bb[2] - bb[0]; h = bb[3] - bb[1]
    x0, y0 = bb[0] + 0.04 * w, bb[1] + 0.04 * h; seg = scale_km / 2
    for i in range(2):
        ax.add_patch(Rectangle((x0 + i * seg * km, y0), seg * km, 0.012 * h, facecolor=INK if i == 0 else "white", edgecolor=INK, lw=0.6, zorder=25))
    for d in (0, seg, scale_km):
        ax.text(x0 + d * km, y0 + 0.022 * h, f"{d:g}", ha="center", fontsize=fs - 0.5, zorder=25, path_effects=HALO)
    ax.text(x0 + scale_km * km + 0.012 * w, y0, "km", fontsize=fs - 0.5, zorder=25, path_effects=HALO, va="bottom")
    if arrow:
        ax.annotate("N", xy=(0.95, 0.965), xytext=(0.95, 0.89), xycoords="axes fraction", ha="center", va="center", fontsize=fs + 3,
                    fontweight="bold", arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.3), path_effects=HALO, zorder=25)
# ---- data ----
st = gpd.read_file(f"{OUT}/03_Stations/stations_CAAQMS_Kolkata_Howrah.gpkg")
st = st.sort_values(["city", "station"], ascending=[False, True]).reset_index(drop=True)   # Kolkata first
st["no"] = np.arange(1, len(st) + 1)
st[["no", "site_id", "station", "city", "lat", "lon", "setting", "annual_mean_season_balanced", "Winter", "Summer", "Monsoon", "Post-monsoon"]].to_csv(f"{OUT}/03_Stations/stations_numbered.csv", index=False)
ind = gpd.read_file(f"{G}/osm_industrial_areas.gpkg").to_crs(4326)
rd = gpd.read_file(f"{G}/roads_major_study_area.gpkg").to_crs(4326); rd["base"] = rd.fclass.str.replace("_link", "", regex=False)
rail = gpd.read_file(f"{OUT}/_extract/gis_osm_railways_free.gpkg").to_crs(4326); rail = rail[rail.fclass.isin(["rail", "subway", "light_rail"])]
B = pd.read_csv(f"{G}/buffer_metrics_vs_AQI.csv"); b1 = B[B.buffer_km == 1].set_index("station")
with rasterio.open(f"{G}/LULC_Esri_2025_study_area_10m.tif") as src:
    t, w, h = calculate_default_transform(src.crs, "EPSG:4326", src.width, src.height, *src.bounds)
    L = np.zeros((h, w), "uint8")
    reproject(rasterio.band(src, 1), L, src_transform=src.transform, src_crs=src.crs, dst_transform=t, dst_crs="EPSG:4326", resampling=Resampling.nearest)
ext = (t.c, t.c + t.a * w, t.f + t.e * h, t.f)
Li = lut[L].astype(float); Li[L == 0] = np.nan
water = np.where(L == 1, 1.0, np.nan); built = np.where(L == 7, 1.0, np.nan); green = np.where(np.isin(L, [2, 4, 5, 11]), 1.0, np.nan)
def roads(ax, scale=1.0, color="#3a3a38"):
    Wd = {"motorway": 1.8, "trunk": 1.6, "primary": 1.1, "secondary": 0.7, "tertiary": 0.4}
    for k in ["tertiary", "secondary", "primary", "trunk", "motorway"]:
        s = rd[rd.base == k]
        if len(s): s.plot(ax=ax, color=color, lw=Wd[k] * scale, zorder=4, alpha=0.8)
OFF = {"Padmapukur": (8, 9, "left"), "Ghusuri": (9, 3, "left"), "Belur Math": (-9, 6, "right"), "Botanical Garden": (-8, -12, "right"),
       "Dasnagar": (-9, 4, "right"), "Victoria": (-9, -10, "right"), "Fort William": (-9, 5, "right"), "Jadavpur": (9, -9, "left"),
       "Rabindra Sarobar": (-9, -10, "right"), "Bidhannagar": (9, 3, "left"), "Ballygunge": (9, 0, "left"), "Rabindra Bharati Univ.": (9, 5, "left")}
def station_markers(ax, values=None, k=1.0, label=None, fs=7.2):
    for _, s in st.iterrows():
        mk = "^" if s.city == "Howrah" else "o"
        if values is None:
            ax.scatter(s.lon, s.lat, s=70 * k, marker=mk, color="#1c5cab" if s.city == "Kolkata" else "#7b2cbf", edgecolor="white", lw=1.0, zorder=12)
        else:
            v = values[s.station]; ax.scatter(s.lon, s.lat, s=aqi_size(v, k), marker=mk, color=aqi_col(v), edgecolor=INK, lw=0.9, zorder=12)
        if label:
            dx, dy, ha = OFF[s.station]
            ax.annotate(label(s), (s.lon, s.lat), xytext=(dx, dy), textcoords="offset points", ha=ha, va="center", fontsize=fs, zorder=13, path_effects=HALO)
def aqi_handles(vmin, vmax, k=1.0):
    cats = [c for c in AQI if c[1] > vmin and c[0] < vmax]
    hs = [Line2D([], [], marker="s", ls="", mfc=c, mec=INK, mew=0.6, ms=8, label=f"{n} ({lo + 1 if lo else 0}–{hi})") for lo, hi, n, c in cats]
    hs += [Line2D([], [], marker="o", ls="", mfc="white", mec=INK, ms=np.sqrt(aqi_size(v, k)), label=f"AQI {v}") for v in (50, 100, 200) if vmin - 30 <= v <= vmax + 30]
    hs += [Line2D([], [], marker="o", ls="", mfc="white", mec=INK, ms=6, label="Kolkata station"), Line2D([], [], marker="^", ls="", mfc="white", mec=INK, ms=6.5, label="Howrah station")]
    return hs

# ================= Fig 1: study area =================
fig, ax = plt.subplots(figsize=(6.4, 6.9), dpi=250)
ax.imshow(np.where(L > 0, 1.0, np.nan), extent=ext, cmap=ListedColormap(["#f3f1ec"]), zorder=0)
ax.imshow(green, extent=ext, cmap=ListedColormap(["#cfe3c4"]), zorder=0.5, interpolation="nearest")
ax.imshow(water, extent=ext, cmap=ListedColormap(["#9cc8ec"]), zorder=1, interpolation="nearest")
ind.plot(ax=ax, zorder=2, **{**IND, "alpha": 0.55})
roads(ax, 0.8, "#8a8985"); rail.plot(ax=ax, color="#52514e", lw=0.6, ls="--", zorder=3)
station_markers(ax, None, 1.4, label=lambda s: f"{s.no}", fs=7.5)
for _, s in st.iterrows():
    pass
ax.text(88.333, 22.587, "Hooghly R.", fontsize=7, style="italic", color="#1c5cab", rotation=58, ha="center", path_effects=HALO, zorder=5)
ax.text(88.245, 22.595, "HOWRAH", fontsize=10, color=INK2, fontweight="bold", alpha=0.75, zorder=5)
ax.text(88.395, 22.525, "KOLKATA", fontsize=10, color=INK2, fontweight="bold", alpha=0.75, zorder=5)
frame(ax, BB, scale_km=4)
legend(ax, [Line2D([], [], marker="o", ls="", mfc="#1c5cab", mec="white", ms=7, label="Kolkata station (1–7)"),
            Line2D([], [], marker="^", ls="", mfc="#7b2cbf", mec="white", ms=7.5, label="Howrah station (8–12)"),
            Line2D([], [], color="#8a8985", lw=1.2, label="Major roads (OSM)"), Line2D([], [], color="#52514e", lw=0.6, ls="--", label="Railway"),
            Patch(**{**IND, "alpha": 0.55}, label="Industrial land (OSM)"), Patch(color="#cfe3c4", label="Vegetation (LULC)"),
            Patch(color="#9cc8ec", label="Water (LULC)")], "Legend", loc="lower right")
# inset India
try:
    with rasterio.open(f"{OUT}/04_IMD/IMD_rainfall_annual_total_2025.tif") as r: a = r.read(1); b = r.bounds
    ins = ax.inset_axes([0.005, 0.735, 0.24, 0.26]); ins.imshow(np.where(a > -999, 1.0, np.nan), extent=(b.left, b.right, b.bottom, b.top), cmap=ListedColormap(["#d9d8d4"]))
    ins.plot(88.35, 22.56, "s", color="#c4281b", ms=4); ins.set_xticks([]); ins.set_yticks([]); ins.set_title("India", fontsize=6.5, pad=1.5)
    for sp in ins.spines.values(): sp.set_color(INK); sp.set_linewidth(0.6)
    ins.set_zorder(26)
except Exception as e: print("inset", e)
fig.tight_layout(pad=0.4); fig.savefig(f"{FIG}/Fig1_study_area_stations.png"); plt.close(fig)

# ================= Fig 4: seasonal AQI maps =================
SEAS = [("Winter", "Winter (Dec–Feb)"), ("Summer", "Summer (Mar–May)"), ("Monsoon", "Monsoon (Jun–Sep)"), ("Post-monsoon", "Post-monsoon (Oct–Nov)")]
fig, axs = plt.subplots(2, 2, figsize=(9.6, 10.0), dpi=220)
for ax, (col, title) in zip(axs.ravel(), SEAS):
    ax.imshow(built, extent=ext, cmap=ListedColormap(["#ecdcd8"]), zorder=0, interpolation="nearest")
    ax.imshow(green, extent=ext, cmap=ListedColormap(["#d6e8cc"]), zorder=0.5, interpolation="nearest")
    ax.imshow(water, extent=ext, cmap=ListedColormap(["#a9cdee"]), zorder=1, interpolation="nearest")
    vals = st.set_index("station")[col]
    station_markers(ax, vals, 0.55, label=lambda s, c=col: f"{s[c]:.0f}", fs=7.4)
    frame(ax, BB, fs=6.8, scale_km=4)
    m = vals.mean(); ax.set_title(f"{title}: network mean AQI {m:.0f}", loc="left", fontsize=10, fontweight="bold", pad=4)
_lg = fig.legend(handles=aqi_handles(30, 260, 0.55), title="Seasonal mean AQI (CPCB category colour; symbol size ∝ AQI)", loc="lower center", ncol=5,
           fontsize=8, title_fontsize=8.6, frameon=True, edgecolor=INK, fancybox=False, framealpha=1, labelspacing=1.5, borderpad=1.0, columnspacing=1.8, handletextpad=1.2)
_lg.get_frame().set_linewidth(0.6); _lg.get_title().set_fontweight("bold")
fig.tight_layout(rect=(0, 0.095, 1, 1), h_pad=1.2, w_pad=0.6); fig.savefig(f"{FIG}/Fig4_seasonal_AQI_maps.png"); plt.close(fig)

# ================= Fig 5: GIS findings (annual AQI + LULC + industry) =================
fig, ax = plt.subplots(figsize=(6.4, 6.9), dpi=250)
ax.imshow(Li, extent=ext, cmap=cmap_l, norm=norm_l, interpolation="nearest", alpha=0.5, zorder=0)
ind.plot(ax=ax, zorder=3, **IND); roads(ax, 0.55); rail.plot(ax=ax, color="#2b2b2b", lw=0.6, ls="--", zorder=4)
vals = st.set_index("station").annual_mean_season_balanced
for _, s in st.iterrows():
    ax.add_patch(Circle((s.lon, s.lat), 1 / 111.32, transform=ax.transData, fill=False, ec=INK, lw=0.6, ls="--", zorder=9))
from matplotlib.patches import Ellipse
for p in list(ax.patches): p.remove()
for _, s in st.iterrows():
    ax.add_patch(Ellipse((s.lon, s.lat), 2 / (111.32 * np.cos(np.radians(LAT0))), 2 / 110.57, fill=False, ec=INK, lw=0.6, ls="--", zorder=9))
station_markers(ax, vals, 0.9, label=lambda s: f"{s.no} {s.station.replace(' Univ.', '')} {s.annual_mean_season_balanced:.0f}", fs=6.6)
frame(ax, BB, scale_km=4)
legend(ax, [h_ for h_ in aqi_handles(70, 145, 0.9) if not h_.get_label().startswith("AQI ")] + [Patch(**IND, label="Industrial land (OSM)"), Line2D([], [], color="#3a3a38", lw=1.2, label="Major roads (OSM)"),
       Line2D([], [], color="#2b2b2b", lw=0.6, ls="--", label="Railway"), Line2D([], [], color=INK, lw=0.6, ls="--", label="1 km buffer")] +
       [Patch(color=CLS[k][1], alpha=0.5, label=f"{CLS[k][0]} (LULC)") for k in (7, 2, 1, 11)], "Annual mean AQI 2025 (size ∝ AQI)", loc="lower right", fs=6.2)
fig.tight_layout(pad=0.4); fig.savefig(f"{FIG}/Fig5_GIS_findings_AQI_LULC_industry.png"); plt.close(fig)

# ================= Fig 7: high vs low station zooms =================
hi = list(b1.sort_values("annual_mean_season_balanced", ascending=False).index[:3]); lo = list(b1.sort_values("annual_mean_season_balanced").index[:3])
NOTE = {"Padmapukur": "Dense Howrah urban–industrial area", "Ghusuri": "Industrial estate 40 m away (30% of 1 km)",
        "Jadavpur": "Densest road grid (30 km/km²)", "Rabindra Sarobar": "Lake + parks (23% green, 8% water)",
        "Bidhannagar": "Planned township, 12% parks", "Rabindra Bharati Univ.": "Built-up, northern edge (exception)"}
fig, axs = plt.subplots(2, 3, figsize=(12.5, 9.4), dpi=200)
R = 0.021
for row, grp in [(0, hi), (1, lo)]:
    for c_, name in enumerate(grp):
        ax = axs[row, c_]; s = st[st.station == name].iloc[0]
        bb = (s.lon - R * KX, s.lat - R, s.lon + R * KX, s.lat + R)
        ax.imshow(Li, extent=ext, cmap=cmap_l, norm=norm_l, interpolation="nearest", zorder=0)
        ind.plot(ax=ax, facecolor="none", edgecolor="#2d0f55", hatch="////", lw=0.9, zorder=3); roads(ax, 1.0, "#2b2b2b")
        rail.plot(ax=ax, color="#2b2b2b", lw=0.7, ls="--", zorder=4)
        for r_, ls in [(1, "-"), (2, "--")]:
            ax.add_patch(Ellipse((s.lon, s.lat), 2 * r_ / (111.32 * np.cos(np.radians(LAT0))), 2 * r_ / 110.57, fill=False, ec="white", lw=1.8, ls=ls, zorder=6))
            ax.add_patch(Ellipse((s.lon, s.lat), 2 * r_ / (111.32 * np.cos(np.radians(LAT0))), 2 * r_ / 110.57, fill=False, ec=INK, lw=0.7, ls=ls, zorder=6))
        a = s.annual_mean_season_balanced
        ax.scatter(s.lon, s.lat, s=aqi_size(a, 0.9), marker="^" if s.city == "Howrah" else "o", color=aqi_col(a), edgecolor=INK, lw=1.0, zorder=10)
        frame(ax, bb, step=0.01, fs=6.8, scale_km=1, arrow=True)
        q = b1.loc[name]
        ax.set_title(f"{s.no}. {name} — AQI {a:.0f} (winter {s.Winter:.0f})", loc="left", fontsize=9.6, fontweight="bold", color="#7a1f00" if row == 0 else "#1c5cab", pad=4)
        ax.text(0.03, 0.97, f"1 km: built {q.pct_built:.0f}% · green {q.pct_vegetation:.0f}% · industry {q['osm_industrial_%']:.0f}%\n{NOTE[name]}",
                transform=ax.transAxes, fontsize=7.2, va="top", zorder=30, bbox=dict(facecolor="white", alpha=0.92, edgecolor=INK, lw=0.5, pad=2.5))
    axs[row, 0].text(-0.2, 0.5, "HIGHEST AQI" if row == 0 else "LOWEST AQI", transform=axs[row, 0].transAxes, rotation=90, va="center", ha="center",
                     fontsize=11, fontweight="bold", color="#7a1f00" if row == 0 else "#1c5cab")
h = [Patch(color=CLS[k][1], label=CLS[k][0]) for k in (7, 2, 1, 11, 5)] + [Patch(facecolor="none", edgecolor="#2d0f55", hatch="////", label="Industrial (OSM)"),
     Line2D([], [], color="#2b2b2b", lw=1.4, label="Major roads"), Line2D([], [], color="#2b2b2b", lw=0.7, ls="--", label="Railway"),
     Line2D([], [], color=INK, lw=0.8, label="1 km buffer"), Line2D([], [], color=INK, lw=0.8, ls="--", label="2 km buffer")]
lg = fig.legend(handles=h, title="Legend (LULC 2025 + OSM)", loc="lower center", ncol=10, fontsize=7.8, title_fontsize=8.4, frameon=True, edgecolor=INK, fancybox=False)
lg.get_frame().set_linewidth(0.6); lg.get_title().set_fontweight("bold")
fig.tight_layout(rect=(0.02, 0.06, 1, 1), h_pad=1.6, w_pad=1.0); fig.savefig(f"{FIG}/Fig7_high_vs_low_station_zooms.png"); plt.close(fig)
print("maps ok")
