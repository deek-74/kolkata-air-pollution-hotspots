"""Step 6-7: roads + buildings clip, buffer metrics (1 & 2 km), correlation with station AQI, charts."""
import os, sys, numpy as np, pandas as pd, geopandas as gpd, rasterio, matplotlib
from rasterio.transform import from_origin
from scipy.stats import spearmanr, pearsonr
matplotlib.use("Agg"); import matplotlib.pyplot as plt
UP, OUT = sys.argv[1], sys.argv[2]; EX = f"{OUT}/_extract"; G = f"{OUT}/05_GIS"; FIG = f"{OUT}/02_Graphs"
INK, INK2 = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,"axes.edgecolor":"#8a8985"})
MAJOR = ["motorway","trunk","primary","secondary","tertiary"]
st = gpd.read_file(f"{OUT}/03_Stations/stations_CAAQMS_Kolkata_Howrah.gpkg").to_crs(32645)
L = pd.read_csv(f"{G}/buffer_LULC_stats.csv")
tiles = gpd.read_file(f"{UP}/open_building.geojson"); t3a1 = tiles[tiles.tile_id == "3a1"].to_crs(32645).geometry.iloc[0]
rows = []
have_roads = os.path.exists(f"{EX}/roads_study_area.gpkg")
have_gob = os.path.exists(f"{EX}/buildings_study_area.csv")
osm_b = [f for f in (os.listdir(EX) if os.path.isdir(EX) else []) if "building" in f and f.endswith(".gpkg")]
if have_roads:
    rd = gpd.read_file(f"{EX}/roads_study_area.gpkg").to_crs(32645)
    rd["base"] = rd.fclass.str.replace("_link", "", regex=False)
    maj = rd[rd.base.isin(MAJOR)].copy()
    maj.to_crs(4326).to_file(f"{G}/roads_major_study_area.gpkg", layer="roads_major", driver="GPKG")
    rd.to_crs(4326).to_file(f"{G}/roads_all_study_area.gpkg", layer="roads_all", driver="GPKG")
if have_gob:
    gb = pd.read_csv(f"{EX}/buildings_study_area.csv")
    gb = gb[gb.confidence >= 0.70]                                    # Google recommended threshold
    gbg = gpd.GeoDataFrame(gb, geometry=gpd.points_from_xy(gb.longitude, gb.latitude), crs=4326).to_crs(32645)
    # 250 m building-cover raster (% of cell covered by footprints)
    x0, y0, x1, y1 = gbg.total_bounds; res = 250
    nx, ny = int((x1 - x0) // res) + 1, int((y1 - y0) // res) + 1
    ix = ((gbg.geometry.x - x0) // res).astype(int); iy = ((y1 - gbg.geometry.y) // res).astype(int)
    grid = np.zeros((ny, nx)); np.add.at(grid, (iy, ix), gbg.area_in_meters.values)
    cov = grid / (res * res) * 100
    with rasterio.open(f"{G}/building_density_250m.tif", "w", driver="GTiff", height=ny, width=nx, count=1, dtype="float32",
                       crs="EPSG:32645", transform=from_origin(x0, y1, res, res), nodata=-1) as d: d.write(cov.astype("float32"), 1)
    # reproject to 4326 for the matplotlib map
    from rasterio.warp import reproject, Resampling, calculate_default_transform
    with rasterio.open(f"{G}/building_density_250m.tif") as s:
        tr, w, h = calculate_default_transform(s.crs, "EPSG:4326", s.width, s.height, *s.bounds)
        dst = np.full((h, w), -1, "float32")
        reproject(rasterio.band(s, 1), dst, src_transform=s.transform, src_crs=s.crs, dst_transform=tr, dst_crs="EPSG:4326", resampling=Resampling.nearest, dst_nodata=-1)
    # mask cells outside tile 3a1
    t4326 = tiles[tiles.tile_id == "3a1"].geometry.iloc[0]
    from rasterio.features import geometry_mask
    m = geometry_mask([t4326], (h, w), tr, invert=True); dst[~m] = -1
    with rasterio.open(f"{G}/building_density_250m_wgs84.tif", "w", driver="GTiff", height=h, width=w, count=1, dtype="float32", crs="EPSG:4326", transform=tr, nodata=-1) as d: d.write(dst, 1)
    # GeoPackage of building centroids (lightweight)
    gbg[["area_in_meters","confidence","geometry"]].to_crs(4326).to_file(f"{G}/buildings_GoogleOB_centroids_study_area.gpkg", layer="buildings_centroids", driver="GPKG")
if osm_b:
    ob = gpd.read_file(f"{EX}/{osm_b[0]}").to_crs(32645)
    ob["area_m2"] = ob.area

lu = gpd.read_file(f"{EX}/gis_osm_landuse_a_free.gpkg").to_crs(32645)
ind = lu[lu.fclass == "industrial"].copy(); ind["geometry"] = ind.buffer(0)
ind.to_crs(4326).to_file(f"{G}/osm_industrial_areas.gpkg", layer="industrial", driver="GPKG")
grn = lu[lu.fclass.isin(["park","forest","grass","meadow","recreation_ground","scrub","heath"])].copy(); grn["geometry"] = grn.buffer(0)
rail = gpd.read_file(f"{EX}/gis_osm_railways_free.gpkg").to_crs(32645)
ind_u = ind.union_all()
for r in (1000, 2000):
    for _, s in st.iterrows():
        buf = s.geometry.buffer(r); A = buf.area / 1e6
        d = {"station": s.station, "buffer_km": r // 1000, "buffer_area_km2": round(A, 3)}
        if have_roads:
            cl = maj.clip(buf); d["road_len_major_km"] = round(cl.length.sum() / 1000, 2)
            d["road_density_major_km_km2"] = round(cl.length.sum() / 1000 / A, 2)
            for k in MAJOR: d[f"len_{k}_km"] = round(cl[cl.base == k].length.sum() / 1000, 2)
            d["road_density_all_km_km2"] = round(rd.clip(buf).length.sum() / 1000 / A, 2)
        d["osm_industrial_%"] = round(ind_u.intersection(buf).area / buf.area * 100, 2)
        d["osm_industrial_area_km2"] = round(ind_u.intersection(buf).area / 1e6, 3)
        d["dist_nearest_industrial_km"] = round(s.geometry.distance(ind_u) / 1000, 2)
        d["osm_green_park_%"] = round(grn.union_all().intersection(buf).area / buf.area * 100, 2)
        d["railway_km_km2"] = round(rail.clip(buf).length.sum() / 1000 / A, 2)
        cover = t3a1.intersection(buf).area / buf.area * 100
        d["google_tile_cover_%"] = round(cover, 1)
        if have_gob and cover >= 99:
            inside = gbg[gbg.within(buf)]
            d["gob_building_count"] = len(inside); d["gob_buildings_per_km2"] = round(len(inside) / A, 0)
            d["gob_footprint_cover_%"] = round(inside.area_in_meters.sum() / (A * 1e6) * 100, 2)
            d["gob_mean_building_area_m2"] = round(inside.area_in_meters.mean(), 1)
        if osm_b:
            oc = ob[ob.intersects(buf)].clip(buf)
            d["osm_building_count"] = len(oc); d["osm_footprint_cover_%"] = round(oc.area.sum() / (A * 1e6) * 100, 2)
        rows.append(d)
B = pd.DataFrame(rows).merge(L[["station","buffer_km","pct_built","pct_vegetation","pct_water","pct_Trees","pct_Crops","pct_Rangeland"]], on=["station","buffer_km"])
Y = pd.read_csv(f"{OUT}/01_AQI/annual_station_summary.csv")[["station","city","annual_mean","annual_mean_season_balanced","Winter","Summer","Monsoon","Post-monsoon","exceed_days_>100"]]
B = Y.merge(B, on="station")
B.to_csv(f"{G}/buffer_metrics_vs_AQI.csv", index=False)

METRICS = [c for c in ["pct_built","pct_vegetation","pct_water","osm_industrial_%","dist_nearest_industrial_km","road_density_major_km_km2","road_density_all_km_km2",
                       "gob_footprint_cover_%","gob_buildings_per_km2","osm_footprint_cover_%"] if c in B]
AQIS = ["annual_mean_season_balanced","Winter","Summer","Monsoon","Post-monsoon"]
cr = []
for bk in (1, 2):
    sub = B[B.buffer_km == bk]
    for m in METRICS:
        for a in AQIS:
            v = sub[[m, a]].dropna()
            if len(v) < 6 or v[m].nunique() < 3: continue
            rs, ps = spearmanr(v[m], v[a]); rp, pp = pearsonr(v[m], v[a])
            cr.append((bk, m, a, len(v), round(rs, 2), round(ps, 3), round(rp, 2), round(pp, 3)))
C = pd.DataFrame(cr, columns=["buffer_km","metric","AQI","n_stations","spearman_rho","spearman_p","pearson_r","pearson_p"])
NAMES = {"osm_industrial_%":"Industrial land % (OSM)","dist_nearest_industrial_km":"Distance to industry (km)","pct_built":"Built-up %","pct_vegetation":"Vegetation %","pct_water":"Water %","road_density_major_km_km2":"Major-road density",
         "road_density_all_km_km2":"All-road density","gob_footprint_cover_%":"Building cover % (Google, n=8)",
         "gob_buildings_per_km2":"Buildings / km² (Google, n=8)","osm_footprint_cover_%":"Building cover % (OSM)"}
with pd.ExcelWriter(f"{G}/Buffer_analysis_LULC_roads_buildings_vs_AQI.xlsx") as xw:
    pd.DataFrame({"Item":["Buffers","LULC","Vegetation","Roads","Road density","Buildings (Google)","Buildings (OSM)","Correlation","Caution"],
                  "Description":["1 km and 2 km circular buffers around each station (UTM 45N, EPSG:32645)",
                                 "Esri/Impact Observatory Sentinel-2 10 m LULC 2025: % of buffer pixels per class",
                                 "Trees + Flooded vegetation + Crops + Rangeland",
                                 "OSM (Geofabrik eastern-zone, 8 Nov 2026) major roads = motorway, trunk, primary, secondary, tertiary (+ _link)",
                                 "Road length clipped to buffer (km) / buffer area (km2)",
                                 "Google Open Buildings v3 tile 3a1, confidence >= 0.70; computed only where buffer is fully inside tile 3a1 (8 of 12 stations)",
                                 "OpenStreetMap building polygons (all 12 stations; OSM completeness varies)",
                                 "Spearman rank and Pearson correlation between buffer metric and station mean AQI (n = 12 or 8)",
                                 "Small sample: correlations are indicative only; regression modelling with more predictors is Phase II"]}).to_excel(xw, "README", index=False)
    B.to_excel(xw, "Buffer_metrics_AQI", index=False); C.to_excel(xw, "Correlations", index=False)
print(B[["station","buffer_km","pct_built","pct_vegetation","pct_water"] + [c for c in ["road_density_major_km_km2","gob_footprint_cover_%","osm_footprint_cover_%"] if c in B] + ["annual_mean_season_balanced"]].to_string())
print(C[C.AQI.isin(["annual_mean_season_balanced","Winter"])].to_string())

# ---- charts ----
# correlation heat table
for bk in (1, 2):
    sub = C[C.buffer_km == bk].pivot(index="metric", columns="AQI", values="spearman_rho").reindex(index=[m for m in METRICS if m in C.metric.values], columns=AQIS)
    pv = C[C.buffer_km == bk].pivot(index="metric", columns="AQI", values="spearman_p").reindex(index=sub.index, columns=AQIS)
    fig, ax = plt.subplots(figsize=(9, 0.6 * len(sub) + 1.8), dpi=200)
    from matplotlib.colors import LinearSegmentedColormap
    cm = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#f0efec", "#e34948"])
    ax.imshow(sub.values, cmap=cm, vmin=-1, vmax=1, aspect="auto")
    for i in range(sub.shape[0]):
        for j in range(sub.shape[1]):
            v = sub.values[i, j]; p = pv.values[i, j]
            ax.text(j, i, "" if np.isnan(v) else f"{v:+.2f}{'*' if p < 0.05 else ''}", ha="center", va="center", fontsize=10, color=INK)
    ax.set_xticks(range(len(AQIS))); ax.set_xticklabels(["Annual","Winter","Summer","Monsoon","Post-monsoon"])
    ax.set_yticks(range(len(sub))); ax.set_yticklabels([NAMES[m] for m in sub.index])
    ax.set_xticks(np.arange(-.5, len(AQIS), 1), minor=True); ax.set_yticks(np.arange(-.5, len(sub), 1), minor=True)
    ax.grid(which="minor", color="white", lw=2); ax.tick_params(which="minor", length=0)
    for s_ in ax.spines.values(): s_.set_visible(False)
    ax.set_title(f"Spearman correlation: {bk} km buffer metrics vs station mean AQI (n = 12 unless noted; * p < 0.05)", loc="left", fontsize=11.5, fontweight="bold")
    fig.text(0.01, 0.01, "Red = higher metric ↔ higher AQI; blue = higher metric ↔ lower AQI", fontsize=8, color=INK2)
    fig.tight_layout(); fig.savefig(f"{FIG}/2{bk-1}_correlation_buffer{bk}km_vs_AQI.png"); plt.close(fig)

# scatter panel (2 km)
sub = B[B.buffer_km == 2]
show = [m for m in ["pct_built","pct_vegetation","osm_industrial_%","road_density_major_km_km2","gob_footprint_cover_%","osm_footprint_cover_%"] if m in B][:6]
n = len(show); fig, axs = plt.subplots(1 if n <= 3 else 2, 3, figsize=(14, 4.6 if n <= 3 else 8.6), dpi=200); axs = np.ravel(axs)
for ax, m in zip(axs, show):
    v = sub[["station","city", m, "annual_mean_season_balanced"]].dropna()
    for _, rr in v.iterrows():
        ax.scatter(rr[m], rr.annual_mean_season_balanced, s=55, marker="^" if rr.city == "Howrah" else "o",
                   color="#7b2cbf" if rr.city == "Howrah" else "#1c5cab", edgecolor="white", lw=0.8, zorder=3)
        ax.annotate(rr.station.replace(" Univ.", ""), (rr[m], rr.annual_mean_season_balanced), xytext=(4, 3), textcoords="offset points", fontsize=7, color=INK2)
    if len(v) > 2:
        k, b0 = np.polyfit(v[m], v.annual_mean_season_balanced, 1); xx = np.linspace(v[m].min(), v[m].max(), 10)
        ax.plot(xx, k * xx + b0, color=INK, lw=1, ls="--", zorder=2)
    rho = C[(C.buffer_km == 2) & (C.metric == m) & (C.AQI == "annual_mean_season_balanced")].spearman_rho
    ax.set_title(f"{NAMES[m]}  (ρ = {rho.iloc[0]:+.2f}, n = {len(v)})" if len(rho) else NAMES[m], loc="left", fontsize=10)
    ax.set_ylabel("Annual mean AQI"); ax.grid(color="#e4e3df", lw=0.6)
for ax in axs[len(show):]: ax.axis("off")
fig.suptitle("Station annual mean AQI vs land-use, road and building metrics within 2 km (● Kolkata, ▲ Howrah)", x=0.01, ha="left", fontweight="bold", fontsize=12.5)
fig.tight_layout(); fig.savefig(f"{FIG}/22_AQI_vs_buffer_metrics_2km_scatter.png"); plt.close(fig)
print("ok")
