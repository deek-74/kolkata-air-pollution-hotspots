"""GIS findings: (e) AQI + LULC + OSM industry map, station land-use fingerprint chart, high vs low AQI station zoom panels."""
import sys, numpy as np, pandas as pd, geopandas as gpd, rasterio, matplotlib
from rasterio.windows import from_bounds
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch, Rectangle, Circle
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe
OUT = sys.argv[1]; G = f"{OUT}/05_GIS"; FIG = f"{OUT}/06_Maps"; GR = f"{OUT}/02_Graphs"
INK, INK2 = "#0b0b0b", "#52514e"; HALO = [pe.withStroke(linewidth=3, foreground="white")]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
CLS = {1:("Water","#419bdf"),2:("Trees","#397d49"),4:("Flooded veg.","#7a87c6"),5:("Crops","#e49635"),
       7:("Built area","#c4281b"),8:("Bare ground","#a59b8f"),11:("Rangeland","#e3e2c3")}
codes = sorted(CLS); lut = np.zeros(256, int); lut[codes] = np.arange(1, len(codes) + 1)
cmap_l = ListedColormap([CLS[k][1] for k in codes]); norm_l = BoundaryNorm(np.arange(0.5, len(codes) + 1.5), len(codes))
QB = [0, 95, 110, 125, 140, 999]; QC = ["#fee391", "#fec44f", "#fe9929", "#d95f0e", "#993404"]
aq_cm = ListedColormap(QC); aq_nm = BoundaryNorm(QB, aq_cm.N)
st = gpd.read_file(f"{OUT}/03_Stations/stations_CAAQMS_Kolkata_Howrah.gpkg").to_crs(32645)
ind = gpd.read_file(f"{G}/osm_industrial_areas.gpkg").to_crs(32645)
rd = gpd.read_file(f"{G}/roads_major_study_area.gpkg").to_crs(32645)
rail = gpd.read_file(f"{OUT}/_extract/gis_osm_railways_free.gpkg").to_crs(32645)
rail = rail[rail.fclass.isin(["rail", "subway", "light_rail", "narrow_gauge"])]
B = pd.read_csv(f"{G}/buffer_metrics_vs_AQI.csv")
src = rasterio.open(f"{G}/LULC_Esri_2025_study_area_10m.tif")
def lulc(bounds):
    w = from_bounds(*bounds, transform=src.transform); a = src.read(1, window=w, boundless=True, fill_value=0)
    li = lut[a].astype(float); li[a == 0] = np.nan; return li
def road_plot(ax, sub, scale=1.0):
    W = {"motorway": 2.2, "trunk": 2.0, "primary": 1.5, "secondary": 1.0, "tertiary": 0.6}
    for k in ["tertiary", "secondary", "primary", "trunk", "motorway"]:
        s = sub[sub.fclass.str.replace("_link", "") == k]
        if len(s): s.plot(ax=ax, color="#2b2b2b", lw=W[k] * scale, zorder=4, alpha=0.85)

def scalebar(ax, x0, y0, km=1, label=None):
    ax.add_patch(Rectangle((x0, y0), km * 1000, km * 60, facecolor=INK, edgecolor="white", lw=0.6, zorder=20))
    ax.text(x0 + km * 500, y0 + km * 140, label or f"{km} km", ha="center", fontsize=7.5, zorder=20, path_effects=HALO)

# ---------------- (e) overview map ----------------
bb = st.total_bounds; pad = 3000
X0, Y0, X1, Y1 = bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad
for FS, FN, SL in [((10, 10.6), "Map_e_AQI_LULC_industry.png", False), ((6.2, 6.6), "Map_e_slide.png", True)]:
    fig, ax = plt.subplots(figsize=FS, dpi=220)
    ax.imshow(lulc((X0, Y0, X1, Y1)), extent=(X0, X1, Y0, Y1), cmap=cmap_l, norm=norm_l, interpolation="nearest", alpha=0.55, zorder=0)
    ind.plot(ax=ax, facecolor="#6b3fa0", edgecolor="#3d1f66", lw=0.5, alpha=0.85, zorder=3)
    road_plot(ax, rd.cx[X0:X1, Y0:Y1], 0.6)
    rail.plot(ax=ax, color="#2b2b2b", lw=0.8, linestyle="--", zorder=4)
    v = st.annual_mean_season_balanced
    for i, s in st.iterrows():
        sz = float(np.clip((v[i] - 70) / 70, 0, 1) * 700 + 150) * (0.35 if SL else 1)
        ax.scatter(s.geometry.x, s.geometry.y, s=sz, color=aq_cm(aq_nm(v[i])), edgecolor=INK, lw=1.2, zorder=10, marker="^" if s.city == "Howrah" else "o")
        ax.add_patch(Circle((s.geometry.x, s.geometry.y), 1000, fill=False, ec=INK, lw=0.7, ls="--", zorder=9))
    OFF = {"Padmapukur":(16,12,"left"),"Ghusuri":(12,2,"left"),"Belur Math":(-12,8,"right"),"Botanical Garden":(-12,-16,"right"),
           "Dasnagar":(-12,6,"right"),"Victoria":(-12,-14,"right"),"Fort William":(-12,8,"right"),"Jadavpur":(12,-12,"left"),
           "Rabindra Sarobar":(-12,-14,"right"),"Bidhannagar":(12,4,"left"),"Ballygunge":(12,0,"left"),"Rabindra Bharati Univ.":(12,6,"left")}
    for i, s in st.iterrows():
        b1 = B[(B.station == s.station) & (B.buffer_km == 1)].iloc[0]
        dx, dy, ha = OFF[s.station]
        lab_ = (f"{s.station}  AQI {v[i]:.0f}\nbuilt {b1.pct_built:.0f}% · green {b1.pct_vegetation:.0f}% · ind. {b1['osm_industrial_%']:.0f}%" if not SL
                else f"{s.station.replace(' Univ.', '')} {v[i]:.0f}")
        ax.annotate(lab_, (s.geometry.x, s.geometry.y), xytext=(dx * (0.7 if SL else 1), dy * (0.7 if SL else 1)), textcoords="offset points", ha=ha,
                    fontsize=7.4 if not SL else 7.2, fontweight="bold" if SL else "normal", zorder=12, path_effects=HALO)
    ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(""); ax.set_ylabel("")
    for sp in ax.spines.values(): sp.set_color(INK)
    scalebar(ax, X0 + 1200, Y0 + 1000, 2, "2 km")
    ax.annotate("N", xy=(0.96, 0.97), xytext=(0.96, 0.91), xycoords="axes fraction", ha="center", fontsize=12, fontweight="bold", arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.5), path_effects=HALO)
    if not SL: ax.set_title("(e) GIS findings: AQI, land use and industrial areas around stations", loc="left", fontsize=13.5, fontweight="bold", pad=22)
    if not SL: ax.text(0, 1.012, "Symbol colour/size = annual mean AQI 2025; dashed circle = 1 km buffer; labels give 1 km built-up %, green (vegetation) % and OSM industrial %",
            transform=ax.transAxes, fontsize=8.3, color=INK2)
    h = [Line2D([], [], marker="o", ls="", mfc=QC[k], mec=INK, ms=9, label=l) for k, l in enumerate(["AQI < 95", "95–110", "110–125", "125–140", "> 140"][:4])] + \
        [Patch(facecolor="#6b3fa0", edgecolor="#3d1f66", label="Industrial land (OSM)"), Line2D([], [], color="#2b2b2b", lw=1.5, label="Major roads (OSM)"),
         Line2D([], [], color="#2b2b2b", lw=0.8, ls=(0, (3, 2)), label="Railway"),
         Patch(color=CLS[7][1], alpha=0.55, label="Built area (LULC)"), Patch(color=CLS[2][1], alpha=0.55, label="Trees (LULC)"),
         Patch(color=CLS[1][1], alpha=0.55, label="Water (LULC)"), Patch(color=CLS[11][1], alpha=0.55, label="Rangeland (LULC)"),
         Line2D([], [], marker="^", ls="", mfc="white", mec=INK, ms=8, label="Howrah station"), Line2D([], [], marker="o", ls="", mfc="white", mec=INK, ms=8, label="Kolkata station")]
    ax.legend(handles=h, loc="upper left" if not SL else "lower right", fontsize=7.6 if not SL else 5.2, framealpha=0.95, ncol=2 if not SL else 1, markerscale=1 if not SL else 0.6)
    if not SL: fig.text(0.01, 0.008, "Data: CPCB/WBPCB CAAQMS 2025 (cleaned); Esri/Impact Observatory Sentinel-2 LULC 2025; OpenStreetMap (Geofabrik, Nov 2026, ODbL). OSM industrial mapping is incomplete for small units.", fontsize=6.8, color=INK2)
    fig.tight_layout(); fig.savefig(f"{FIG}/{FN}"); plt.close(fig)

# ---------------- station fingerprint chart ----------------
b1 = B[B.buffer_km == 1].set_index("station"); b2 = B[B.buffer_km == 2].set_index("station")
order = list(b1.sort_values("annual_mean_season_balanced").index)       # bottom -> top = low -> high
fig = plt.figure(figsize=(13, 6.2), dpi=200)
gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 2.2, 1.6], wspace=0.06)
a0, a1, a2 = [fig.add_subplot(gs[i]) for i in range(3)]
y = np.arange(len(order))
vals = b1.loc[order, "annual_mean_season_balanced"]
a0.barh(y, vals, color=[aq_cm(aq_nm(x)) for x in vals], edgecolor=INK, lw=0.5, height=0.7)
a0.scatter(b1.loc[order, "Winter"], y, marker="|", s=120, color=INK, zorder=3)
for yi, x in zip(y, vals): a0.text(x - 4, yi, f"{x:.0f}", va="center", ha="right", fontsize=8.5, color=INK)
a0.set_yticks(y); a0.set_yticklabels([f"{s} ({b1.loc[s,'city'][0]})" for s in order]); a0.set_xlim(0, 260)
a0.set_xlabel("Annual mean AQI (bar) · winter mean (|)"); a0.set_title("AQI 2025", loc="left", fontweight="bold")
left = np.zeros(len(order))
for col, lab, c in [("pct_built", "Built area", CLS[7][1]), ("pct_vegetation", "Vegetation", CLS[2][1]), ("pct_water", "Water", CLS[1][1])]:
    v_ = b1.loc[order, col].values; a1.barh(y, v_, left=left, color=c, height=0.7, label=lab, edgecolor="white", lw=0.6)
    for yi, l, w_ in zip(y, left, v_):
        if w_ >= 6: a1.text(l + w_ / 2, yi, f"{w_:.0f}", ha="center", va="center", fontsize=7.8, color="white")
    left += v_
a1.set_xlim(0, 100); a1.set_yticks(y); a1.set_yticklabels([]); a1.set_xlabel("% of 1 km buffer (Esri 10 m LULC)")
a1.set_title("Land cover within 1 km", loc="left", fontweight="bold"); a1.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.06), frameon=False, fontsize=8.5)
a2.set_xlim(0, 3); a2.set_ylim(a1.get_ylim()); a2.set_yticks([]); a2.set_xticks([0.5, 1.5, 2.5])
a2.set_xticklabels(["Industrial land\n% within 1 km", "Nearest industry\n(km)", "Major roads\nkm/km² (2 km)"], fontsize=8.3)
a2.xaxis.tick_top()
for yi, s in zip(y, order):
    ip = b1.loc[s, "osm_industrial_%"]; dd = b1.loc[s, "dist_nearest_industrial_km"]; rr = b2.loc[s, "road_density_major_km_km2"]
    a2.add_patch(Rectangle((0.08, yi - 0.33), 0.84 * min(ip, 30) / 30, 0.66, color="#6b3fa0", alpha=0.85))
    a2.text(0.5, yi, f"{ip:.0f}%", ha="center", va="center", fontsize=8.5, color=INK, path_effects=HALO)
    a2.text(1.5, yi, f"{dd:.2f}", ha="center", va="center", fontsize=8.5, fontweight="bold" if dd < 0.6 else "normal")
    a2.text(2.5, yi, f"{rr:.1f}", ha="center", va="center", fontsize=8.5)
for a in (a0, a1, a2):
    for sp in ["top", "right"]: a.spines[sp].set_visible(False)
a2.spines["left"].set_visible(False); a2.spines["bottom"].set_visible(False)
for yi in y: a2.axhline(yi + 0.5, color="#e4e3df", lw=0.6)
fig.suptitle("Station land-use fingerprint: polluted stations are fully built-up with almost no green cover (sorted by AQI)", x=0.01, ha="left", fontsize=13, fontweight="bold")
fig.text(0.01, 0.01, "Spearman (n = 12): vegetation within 1 km vs AQI ρ = −0.68 (p = 0.02); built-up within 1 km ρ = +0.52 (p = 0.08); OSM industrial % not significant (small units unmapped). Data: CPCB, Esri LULC 2025, OSM.", fontsize=7.5, color=INK2)
fig.subplots_adjust(left=0.15, right=0.99, top=0.83, bottom=0.12)
fig.savefig(f"{GR}/23_station_landuse_fingerprint.png"); plt.close(fig)

# ---------------- high vs low station zooms ----------------
hi = list(b1.sort_values("annual_mean_season_balanced", ascending=False).index[:3])
lo = list(b1.sort_values("annual_mean_season_balanced").index[:3])
NOTE = {"Padmapukur": "Dense Howrah urban–industrial fabric;\nindustry 0.9 km; no green within 1 km",
        "Ghusuri": "Industrial estate 40 m from station (30% of\n1 km buffer); riverside mill belt; no green",
        "Jadavpur": "Fully built-up, busiest road grid of all\n(30 km roads/km²); traffic-dominated",
        "Rabindra Sarobar": "Lake + parks: 23% green (OSM parks)\nand 8% water within 1 km",
        "Bidhannagar": "Planned township: wide roads, 12% parks;\nfew industrial units",
        "Rabindra Bharati Univ.": "Built-up 96% but lower AQI: northern edge,\nB.T. Road corridor (exception)"}
fig, axs = plt.subplots(2, 3, figsize=(13, 9.6), dpi=200)
R = 2200
for row, grp, lab in [(0, hi, "HIGHEST AQI"), (1, lo, "LOWEST AQI")]:
    for col, name in enumerate(grp):
        ax = axs[row, col]; s = st[st.station == name].iloc[0]; x, y_ = s.geometry.x, s.geometry.y
        bx = (x - R, y_ - R, x + R, y_ + R)
        ax.imshow(lulc(bx), extent=(bx[0], bx[2], bx[1], bx[3]), cmap=cmap_l, norm=norm_l, interpolation="nearest", zorder=0)
        ind.cx[bx[0]:bx[2], bx[1]:bx[3]].plot(ax=ax, facecolor="none", edgecolor="#2d0f55", hatch="////", lw=1.0, zorder=3)
        road_plot(ax, rd.cx[bx[0]:bx[2], bx[1]:bx[3]], 1.0)
        rail.cx[bx[0]:bx[2], bx[1]:bx[3]].plot(ax=ax, color="#2b2b2b", lw=0.7, linestyle="--", zorder=4)
        for r_, ls in [(1000, "-"), (2000, "--")]: ax.add_patch(Circle((x, y_), r_, fill=False, ec="white", lw=1.6, ls=ls, zorder=6)); ax.add_patch(Circle((x, y_), r_, fill=False, ec=INK, lw=0.6, ls=ls, zorder=6))
        a = s.annual_mean_season_balanced
        ax.scatter(x, y_, s=170, color=aq_cm(aq_nm(a)), edgecolor=INK, lw=1.3, zorder=10, marker="^" if s.city == "Howrah" else "o")
        ax.set_xlim(bx[0], bx[2]); ax.set_ylim(bx[1], bx[3]); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(""); ax.set_ylabel("")
        for sp in ax.spines.values(): sp.set_color(INK); sp.set_linewidth(1.2)
        q = b1.loc[name]
        ax.set_title(f"{name} ({s.city[0]}) — AQI {a:.0f} (winter {s.Winter:.0f})", loc="left", fontsize=10.5, fontweight="bold", color="#7a1f00" if row == 0 else "#1c5cab")
        ax.text(0.02, 0.02, f"1 km: built {q.pct_built:.0f}% · green {q.pct_vegetation:.0f}% · water {q.pct_water:.0f}% · industry {q['osm_industrial_%']:.0f}%\n{NOTE.get(name, '')}",
                transform=ax.transAxes, fontsize=7.8, va="bottom", zorder=20, bbox=dict(facecolor="white", alpha=0.9, edgecolor="none", pad=3))
        scalebar(ax, bx[2] - 1350, bx[3] - 450, 1)
    axs[row, 0].text(-0.06, 0.5, lab, transform=axs[row, 0].transAxes, rotation=90, va="center", ha="center", fontsize=12, fontweight="bold", color="#7a1f00" if row == 0 else "#1c5cab")
h = [Patch(color=CLS[k][1], label=CLS[k][0]) for k in (7, 2, 1, 11, 5)] + [Patch(facecolor="none", edgecolor="#2d0f55", hatch="////", label="Industrial (OSM)"),
     Line2D([], [], color="#2b2b2b", lw=1.6, label="Major roads"), Line2D([], [], color="#2b2b2b", lw=0.8, ls="--", label="Railway"),
     Line2D([], [], color=INK, lw=0.8, label="1 km buffer"), Line2D([], [], color=INK, lw=0.8, ls="--", label="2 km buffer")]
fig.legend(handles=h, loc="lower center", ncol=10, frameon=False, fontsize=8.3)
fig.suptitle("Why AQI differs: land use around the 3 most and 3 least polluted stations (LULC 2025 + OSM)", x=0.01, ha="left", fontsize=14, fontweight="bold")
fig.tight_layout(rect=(0.01, 0.04, 1, 0.97), h_pad=2.2); fig.savefig(f"{FIG}/Map_f_high_vs_low_AQI_station_zooms.png"); plt.close(fig)
print("ok")
