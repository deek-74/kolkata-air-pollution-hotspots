"""Step 6-7 (LULC part): clip Esri 10 m LULC 2025 to study area, station buffers (1 & 2 km), class percentages."""
import sys, numpy as np, pandas as pd, geopandas as gpd, rasterio
from rasterio.mask import mask
from rasterio.windows import from_bounds
from shapely.geometry import box
UP, OUT = sys.argv[1], sys.argv[2]
BBOX = (88.23, 22.45, 88.46, 22.68)
CLS = {1:("Water","#419bdf"),2:("Trees","#397d49"),4:("Flooded vegetation","#7a87c6"),5:("Crops","#e49635"),
       7:("Built area","#c4281b"),8:("Bare ground","#a59b8f"),9:("Snow/Ice","#a8ebff"),10:("Clouds","#616161"),11:("Rangeland","#e3e2c3")}
VEG = [2, 4, 5, 11]
st = gpd.read_file(f"{OUT}/03_Stations/stations_CAAQMS_Kolkata_Howrah.gpkg").to_crs(32645)
aoi = gpd.GeoDataFrame(geometry=[box(*BBOX)], crs=4326).to_crs(32645)
with rasterio.open(f"{UP}/45Q_20250101-20251231.tif") as src:
    win = from_bounds(*aoi.total_bounds, transform=src.transform).round_offsets().round_lengths()
    arr = src.read(1, window=win); tr = src.window_transform(win); prof = src.profile
prof.update(height=arr.shape[0], width=arr.shape[1], transform=tr, compress="deflate", tiled=True, nodata=0)
lp = f"{OUT}/05_GIS/LULC_Esri_2025_study_area_10m.tif"
with rasterio.open(lp, "w", **prof) as dst:
    dst.write(arr, 1)
    cm = {k: tuple(int(c[1][i:i+2], 16) for i in (1, 3, 5)) + (255,) for k, c in CLS.items()}
    cm[0] = (0, 0, 0, 0); dst.write_colormap(1, cm)
u, c = np.unique(arr[arr > 0], return_counts=True)
aoi_stats = pd.DataFrame({"class_code": u, "class": [CLS[k][0] for k in u], "area_km2": (c * 100 / 1e6).round(2),
                          "percent": (c / c.sum() * 100).round(2)})
print(aoi_stats.to_string())

rows, bufs = [], []
for r in (1000, 2000):
    b = st[["site_id","station","city","geometry"]].copy(); b["geometry"] = st.buffer(r); b["buffer_km"] = r // 1000
    bufs.append(b)
    with rasterio.open(lp) as src:
        for _, s in b.iterrows():
            a, _ = mask(src, [s.geometry], crop=True, nodata=0, filled=True)
            a = a[0]; v = a[a > 0]; n = v.size
            d = {"station": s.station, "buffer_km": r // 1000, "pixels": n}
            for k, (nm, _) in CLS.items():
                if k in (9, 10): continue
                d[f"pct_{nm.replace(' ', '_').replace('/', '_')}"] = round((v == k).sum() / n * 100, 2)
            d["pct_built"] = round((v == 7).sum() / n * 100, 2)
            d["pct_vegetation"] = round(np.isin(v, VEG).sum() / n * 100, 2)
            d["pct_water"] = round((v == 1).sum() / n * 100, 2)
            rows.append(d)
B = pd.concat(bufs).to_crs(4326)
B.to_file(f"{OUT}/05_GIS/station_buffers.gpkg", layer="buffers", driver="GPKG")
L = pd.DataFrame(rows)
L.to_csv(f"{OUT}/05_GIS/buffer_LULC_stats.csv", index=False)
aoi_stats.to_csv(f"{OUT}/05_GIS/study_area_LULC_class_area.csv", index=False)
print(L[["station","buffer_km","pct_built","pct_vegetation","pct_water"]].to_string())
