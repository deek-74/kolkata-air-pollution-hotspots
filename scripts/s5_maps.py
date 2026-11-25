"""Step 8: finished map images (study area, LULC, roads+buildings, AQI)."""
import os, sys, numpy as np, pandas as pd, geopandas as gpd, rasterio, matplotlib
from rasterio.warp import reproject, Resampling, calculate_default_transform
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe
OUT = sys.argv[1]; FIG = f"{OUT}/06_Maps"; os.makedirs(FIG, exist_ok=True)
INK, INK2 = "#0b0b0b", "#52514e"
BB = (88.23, 22.45, 88.46, 22.68)
CLS = {1:("Water","#419bdf"),2:("Trees","#397d49"),4:("Flooded vegetation","#7a87c6"),5:("Crops","#e49635"),
       7:("Built area","#c4281b"),8:("Bare ground","#a59b8f"),11:("Rangeland","#e3e2c3")}
AQIB = [(0,50,"Good","#00b050"),(50,100,"Satisfactory","#92d050"),(100,200,"Moderate","#ffff00"),(200,300,"Poor","#ff9900"),(300,400,"Very Poor","#ff0000")]
st = gpd.read_file(f"{OUT}/03_Stations/stations_CAAQMS_Kolkata_Howrah.gpkg")
OFF = {"Padmapukur":(-6,-14,"right"),"Ghusuri":(8,4,"left"),"Belur Math":(-8,6,"right"),"Botanical Garden":(-6,-14,"right"),
       "Dasnagar":(-8,4,"right"),"Victoria":(-8,-12,"right"),"Fort William":(-8,6,"right"),"Jadavpur":(8,-10,"left"),
       "Rabindra Sarobar":(-8,-12,"right"),"Bidhannagar":(8,4,"left"),"Ballygunge":(8,0,"left"),"Rabindra Bharati Univ.":(8,4,"left")}
HALO = [pe.withStroke(linewidth=3, foreground="white")]

# LULC to WGS84 for display
with rasterio.open(f"{OUT}/05_GIS/LULC_Esri_2025_study_area_10m.tif") as src:
    t, w, h = calculate_default_transform(src.crs, "EPSG:4326", src.width, src.height, *src.bounds)
    L = np.zeros((h, w), "uint8")
    reproject(rasterio.band(src, 1), L, src_transform=src.transform, src_crs=src.crs, dst_transform=t, dst_crs="EPSG:4326", resampling=Resampling.nearest)
ext = (t.c, t.c + t.a * w, t.f + t.e * h, t.f)
codes = sorted(CLS); lut = np.zeros(256, int); lut[codes] = np.arange(1, len(codes) + 1)
Li = lut[L].astype(float); Li[L == 0] = np.nan
cmap_l = ListedColormap([CLS[k][1] for k in codes]); norm_l = BoundaryNorm(np.arange(0.5, len(codes) + 1.5), len(codes))
water = np.where(L == 1, 1.0, np.nan)

def frame(ax, title, sub=None):
    ax.set_xlim(BB[0], BB[2]); ax.set_ylim(BB[1], BB[3]); ax.set_aspect(1 / np.cos(np.radians(22.56)))
    ax.set_xticks(np.arange(88.25, 88.46, 0.05)); ax.set_yticks(np.arange(22.45, 22.69, 0.05))
    ax.set_xticklabels([f"{x:.2f}°E" for x in ax.get_xticks()], fontsize=8); ax.set_yticklabels([f"{y:.2f}°N" for y in ax.get_yticks()], fontsize=8)
    ax.grid(color="#9a9a96", lw=0.4, ls=":", zorder=1); ax.set_xlabel(""); ax.set_ylabel("")
    for s in ax.spines.values(): s.set_visible(True); s.set_color(INK)
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", pad=(20 if sub else 8))
    if sub: ax.text(0, 1.012, sub, transform=ax.transAxes, fontsize=8.5, color=INK2)
    # north arrow + scale bar (5 km)
    ax.annotate("N", xy=(0.95, 0.95), xytext=(0.95, 0.88), xycoords="axes fraction", ha="center", fontsize=12, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.5), path_effects=HALO)
    km = 1 / (111.32 * np.cos(np.radians(22.56))); x0, y0 = BB[0] + 0.012, BB[1] + 0.01
    for i in range(5):
        ax.add_patch(Rectangle((x0 + i * km, y0), km, 0.0018, facecolor=INK if i % 2 == 0 else "white", edgecolor=INK, lw=0.6, zorder=10))
    for i in (0, 5): ax.text(x0 + i * km, y0 + 0.0035, f"{i}", ha="center", fontsize=7.5, zorder=10, path_effects=HALO)
    ax.text(x0 + 5 * km + 0.003, y0 + 0.0002, "km", fontsize=7.5, zorder=10, path_effects=HALO)

def stations(ax, size=60, color=None, labels=True, edge=INK):
    for _, s in st.iterrows():
        ax.scatter(s.lon, s.lat, s=size if np.isscalar(size) else size[_], marker="^" if s.city == "Howrah" else "o",
                   c=color if color is not None else ("#7b2cbf" if s.city == "Howrah" else "#1c5cab"), edgecolor=edge, lw=1, zorder=12)
        if labels:
            dx, dy, ha = OFF[s.station]
            ax.annotate(s.station, (s.lon, s.lat), xytext=(dx, dy), textcoords="offset points", ha=ha, fontsize=8.5, zorder=13, path_effects=HALO)

src_note = "Data: CPCB/WBPCB CAAQMS (2025); Esri / Impact Observatory Sentinel-2 10 m LULC 2025"

# (a) study area map, with India inset from IMD grid
fig, ax = plt.subplots(figsize=(9, 9.6), dpi=220)
ax.imshow(np.where(L > 0, 1.0, np.nan), extent=ext, cmap=ListedColormap(["#f1efe9"]), zorder=0)
ax.imshow(water, extent=ext, cmap=ListedColormap(["#9cc8ec"]), zorder=2, interpolation="nearest")
buf = gpd.read_file(f"{OUT}/05_GIS/station_buffers.gpkg")
buf[buf.buffer_km == 2].boundary.plot(ax=ax, color="#52514e", lw=0.6, ls="--", zorder=4)
if os.path.exists(f"{OUT}/05_GIS/roads_major_study_area.gpkg"):
    rd = gpd.read_file(f"{OUT}/05_GIS/roads_major_study_area.gpkg")
    rd[rd.fclass.str.startswith(("motorway","trunk","primary"))].plot(ax=ax, color="#8a8985", lw=0.7, zorder=3)
stations(ax)
ax.text(88.333, 22.585, "Hooghly\nRiver", fontsize=9, style="italic", color="#1c5cab", ha="center", path_effects=HALO, rotation=55, zorder=5)
ax.text(88.245, 22.585, "HOWRAH", fontsize=13, color=INK2, fontweight="bold", alpha=0.7, zorder=5)
ax.text(88.40, 22.53, "KOLKATA", fontsize=13, color=INK2, fontweight="bold", alpha=0.7, zorder=5)
frame(ax, "(a) Study area: Kolkata–Howrah CAAQMS stations", "12 continuous ambient air quality monitoring stations (WBPCB); dashed circles = 2 km buffers")
ax.legend(handles=[Line2D([],[],marker="o",ls="",color="#1c5cab",mec=INK,ms=8,label="Kolkata station (7)"),
                   Line2D([],[],marker="^",ls="",color="#7b2cbf",mec=INK,ms=8,label="Howrah station (5)"),
                   Line2D([],[],color="#52514e",ls="--",label="2 km buffer"), Patch(color="#9cc8ec",label="Water (LULC)")],
          loc="lower right", fontsize=8.5, framealpha=0.95)
# inset: India from IMD rainfall grid
try:
    with rasterio.open(f"{OUT}/04_IMD/IMD_rainfall_annual_total_2025.tif") as r:
        a = r.read(1); b = r.bounds
    ins = ax.inset_axes([0.0, 0.70, 0.27, 0.30])
    ins.imshow(np.where(a > -999, 1.0, np.nan), extent=(b.left, b.right, b.bottom, b.top), cmap=ListedColormap(["#d9d8d4"]))
    ins.plot(88.35, 22.56, "s", color="#c4281b", ms=5); ins.set_xticks([]); ins.set_yticks([])
    ins.set_title("India (IMD grid)", fontsize=7, pad=2); ins.set_facecolor("white")
    for s in ins.spines.values(): s.set_color(INK)
except Exception as e: print("inset", e)
fig.text(0.01, 0.01, src_note, fontsize=7, color=INK2); fig.tight_layout(); fig.savefig(f"{FIG}/Map_a_study_area.png"); plt.close(fig)

# (b) LULC map
fig, ax = plt.subplots(figsize=(9, 9.6), dpi=220)
ax.imshow(Li, extent=ext, cmap=cmap_l, norm=norm_l, interpolation="nearest", zorder=0)
buf[buf.buffer_km == 1].boundary.plot(ax=ax, color="black", lw=0.6, zorder=4)
stations(ax, color="white")
pa = pd.read_csv(f"{OUT}/05_GIS/study_area_LULC_class_area.csv").set_index("class_code")
frame(ax, "(b) Land use / land cover 2025 with monitoring stations", "Esri / Impact Observatory Sentinel-2 10 m LULC; black circles = 1 km buffers")
ax.legend(handles=[Patch(color=CLS[k][1], label=f"{CLS[k][0]} ({pa.percent.get(k, 0):.1f}%)") for k in codes if k in pa.index],
          loc="lower right", fontsize=8, framealpha=0.95, title="LULC class (% of study area)", title_fontsize=8)
fig.text(0.01, 0.01, src_note, fontsize=7, color=INK2); fig.tight_layout(); fig.savefig(f"{FIG}/Map_b_LULC.png"); plt.close(fig)

# (c) roads + building density
if os.path.exists(f"{OUT}/05_GIS/roads_major_study_area.gpkg") and os.path.exists(f"{OUT}/05_GIS/building_density_250m.tif"):
    rd = gpd.read_file(f"{OUT}/05_GIS/roads_major_study_area.gpkg")
    with rasterio.open(f"{OUT}/05_GIS/building_density_250m.tif") as r:
        bd = r.read(1).astype(float); bb = r.bounds; bd[bd < 0] = np.nan
    fig, ax = plt.subplots(figsize=(9, 9.6), dpi=220)
    ax.imshow(water, extent=ext, cmap=ListedColormap(["#c9dff3"]), zorder=0, interpolation="nearest")
    bl = ListedColormap(["#f3f2ee","#e4e3df","#c3c2b7","#a3a29b","#7d7c76","#52514e"])
    bn = BoundaryNorm([0, 5, 15, 25, 35, 45, 100], bl.N)
    im = ax.imshow(np.where(bd > 0, bd, np.nan), extent=(bb.left, bb.right, bb.bottom, bb.top), cmap=bl, norm=bn, zorder=1, alpha=0.95)
    RS = {"motorway":("#c4281b",2.2),"trunk":("#eb6834",1.8),"primary":("#eda100",1.4),"secondary":("#2a78d6",0.9),"tertiary":("#1baf7a",0.5)}
    for k in ["tertiary","secondary","primary","trunk","motorway"]:
        sub = rd[rd.fclass.str.replace("_link","") == k]
        if len(sub): sub.plot(ax=ax, color=RS[k][0], lw=RS[k][1], zorder=3)
    stations(ax, color="white")
    frame(ax, "(c) Major road network and building density", "OSM roads (Geofabrik, Nov 2026); Google Open Buildings v3 footprint cover (% of 250 m cell)")
    h = [Line2D([],[],color=c,lw=w + 0.5,label=k.capitalize()) for k, (c, w) in RS.items()] + \
        [Patch(color=bl(i), label=l) for i, l in enumerate(["<5%","5–15%","15–25%","25–35%","35–45%",">45%"])]
    ax.legend(handles=h, loc="lower right", fontsize=7.5, framealpha=0.95, ncol=2, title="Road class  |  Building cover", title_fontsize=8)
    fig.text(0.01, 0.01, "Data: OpenStreetMap contributors (ODbL); Google Open Buildings v3 (CC BY 4.0); CPCB/WBPCB. Belur Math & northern edge partly outside tile 3a1.", fontsize=6.5, color=INK2)
    fig.tight_layout(); fig.savefig(f"{FIG}/Map_c_roads_buildings.png"); plt.close(fig)

# (d) AQI map
for FS, FN in [((9, 9.6), "Map_d_AQI_stations.png"), ((6.4, 6.6), "Map_d_slide.png")]:
    fig, ax = plt.subplots(figsize=FS, dpi=220)
    ax.imshow(Li, extent=ext, cmap=cmap_l, norm=norm_l, interpolation="nearest", zorder=0, alpha=0.25)
    v = st.annual_mean_season_balanced
    QB = [70, 95, 110, 125, 140]; QC = ["#fee391","#fec44f","#fe9929","#d95f0e","#993404"]
    cm = ListedColormap(QC); nm = BoundaryNorm([0] + QB[1:] + [999], cm.N)
    def msz(a): return float(np.clip((a - 70) / (140 - 70), 0, 1) * 500 + 120)
    for i, s in st.iterrows():
        ax.scatter(s.lon, s.lat, s=msz(v[i]), color=cm(nm(v[i])), edgecolor=INK, lw=1, zorder=12, marker="^" if s.city == "Howrah" else "o")
        dx, dy, ha = OFF[s.station]
        ax.annotate(f"{s.station}\n{v[i]:.0f} (W {s.Winter:.0f} / M {s.Monsoon:.0f})", (s.lon, s.lat), xytext=(dx * 1.6, dy * 1.4),
                    textcoords="offset points", ha=ha, fontsize=7.8, zorder=13, path_effects=HALO)
    frame(ax, "(d) Annual mean AQI at monitoring stations, 2025", "Symbol size and colour = season-balanced annual mean AQI; label = annual (Winter / Monsoon mean)")
    labs = ["< 95 (Satisfactory)", "95–110", "110–125", "125–140", "> 140"]; reps = [82, 102, 117, 132, 145]
    hh = [Line2D([],[],marker="o",ls="",mfc=QC[k],mec=INK,ms=np.sqrt(msz(reps[k])),label=labs[k]) for k in range(4)] + \
         [Line2D([],[],marker="^",ls="",mfc="white",mec=INK,ms=9,label="Howrah"), Line2D([],[],marker="o",ls="",mfc="white",mec=INK,ms=9,label="Kolkata")]
    ax.legend(handles=hh, loc="upper left", fontsize=8 if FN.startswith("Map_d_AQI") else 6.5, framealpha=0.95, title="Annual mean AQI (100–200 = Moderate)", title_fontsize=8 if FN.startswith("Map_d_AQI") else 6.5, labelspacing=1.1 if FN.startswith("Map_d_AQI") else 0.5, markerscale=1 if FN.startswith("Map_d_AQI") else 0.6)
    fig.text(0.01, 0.01, "Data: CPCB/WBPCB CAAQMS hourly AQI 2025 (cleaned); faint background = LULC 2025. Interpolated surface (IDW) and Gi* hotspots: Phase II.", fontsize=7, color=INK2)
    fig.tight_layout(); fig.savefig(f"{FIG}/{FN}"); plt.close(fig)
print("maps ok")
