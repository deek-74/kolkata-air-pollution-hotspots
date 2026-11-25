"""Step 4-5: station point layer; IMD rainfall (.nc) and Tmax (.GRD) -> GeoTIFF; Kolkata 365-day table; AQI vs meteorology."""
import sys, numpy as np, pandas as pd, xarray as xr, rasterio, geopandas as gpd, matplotlib
from rasterio.transform import from_origin
from scipy.stats import spearmanr, pearsonr
matplotlib.use("Agg"); import matplotlib.pyplot as plt
UP, OUT = sys.argv[1], sys.argv[2]
INK, INK2 = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,"axes.edgecolor":"#8a8985"})
SEASON = {1:"Winter",2:"Winter",12:"Winter",3:"Summer",4:"Summer",5:"Summer",6:"Monsoon",7:"Monsoon",8:"Monsoon",9:"Monsoon",10:"Post-monsoon",11:"Post-monsoon"}
SCOL = {"Winter":"#2a78d6","Summer":"#eb6834","Monsoon":"#1baf7a","Post-monsoon":"#eda100"}

# ---------------- stations ----------------
ST = pd.DataFrame([
 # site_id, station, city, lat, lon, setting, coordinate source
 (1416,"Padmapukur","Howrah",22.5687319,88.2797276,"Residential-industrial (Howrah, near NH-16/Kona Expressway)","CPCB CAAQMS list (#1416)"),
 (274,"Ghusuri","Howrah",22.611968,88.347422,"Industrial / riverside (G.T. Road, Hooghly bank)","CPCB CAAQMS list (#274)"),
 (5101,"Belur Math","Howrah",22.629801,88.352017,"Mixed riverside / residential (Hooghly bank)","CPCB CAAQMS list (#5101)"),
 (5989,"Botanical Garden","Howrah",22.554954,88.292568,"Green space (AJC Bose Botanic Garden, Shibpur)","CPCB station metadata (CCR)"),
 (6009,"Dasnagar","Howrah",22.6025571,88.3105664,"Industrial-residential (Dasnagar, Howrah)","CCR/IQAir station map"),
 (309,"Victoria","Kolkata",22.5448082,88.3403691,"Urban green / central business (Victoria Memorial)","CPCB CAAQMS list (#309)"),
 (5110,"Fort William","Kolkata",22.55664,88.342674,"Maidan open space / cantonment","CPCB CAAQMS list (#5110)"),
 (5111,"Jadavpur","Kolkata",22.49929,88.36917,"Residential-commercial, high traffic (south Kolkata)","CPCB CAAQMS list (#5111)"),
 (5126,"Rabindra Sarobar","Kolkata",22.51106,88.35142,"Urban lake & park","CPCB CAAQMS list (#5126)"),
 (5129,"Bidhannagar","Kolkata",22.58157048,88.41002457,"Planned township (Salt Lake)","CPCB CAAQMS list (#5129)"),
 (5238,"Ballygunge","Kolkata",22.5367507,88.3638022,"Residential-commercial, traffic (south-central)","CPCB CAAQMS list (#5238)"),
 (296,"Rabindra Bharati Univ.","Kolkata",22.627847,88.380669,"Institutional / B.T. Road traffic corridor (north)","CPCB CAAQMS list (#296)"),
], columns=["site_id","station","city","lat","lon","setting","coord_source"])
Y = pd.read_csv(f"{OUT}/01_AQI/annual_station_summary.csv")
ST = ST.merge(Y.drop(columns=["site_id","city"]), on="station")
ST.to_csv(f"{OUT}/03_Stations/stations_CAAQMS_Kolkata_Howrah.csv", index=False)
gST = gpd.GeoDataFrame(ST, geometry=gpd.points_from_xy(ST.lon, ST.lat), crs=4326)
gST.to_file(f"{OUT}/03_Stations/stations_CAAQMS_Kolkata_Howrah.gpkg", layer="stations", driver="GPKG")

# ---------------- IMD rainfall NetCDF -> GeoTIFF ----------------
ds = xr.open_dataset(f"{UP}/RF25_ind2025_rfp25.nc")
rf = ds.RAINFALL.where(ds.RAINFALL > -1)                      # -999 => NaN
lat, lon = rf.LATITUDE.values, rf.LONGITUDE.values
res = 0.25
tr = from_origin(lon.min() - res/2, lat.max() + res/2, res, res)
def write(path, arr, transform, desc=None):
    arr = np.asarray(arr, dtype="float32"); arr = arr[None] if arr.ndim == 2 else arr
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[1], width=arr.shape[2], count=arr.shape[0],
                       dtype="float32", crs="EPSG:4326", transform=transform, nodata=-999, compress="deflate") as dst:
        dst.write(np.where(np.isnan(arr), -999, arr))
        if desc:
            for i, d in enumerate(desc, 1): dst.set_band_description(i, d)
dates = pd.to_datetime(rf.TIME.values)
R = rf.values[:, ::-1, :]                                      # north-up
write(f"{OUT}/04_IMD/IMD_rainfall_daily_2025_0p25deg.tif", R, tr, [d.strftime("%Y-%m-%d") for d in dates])
write(f"{OUT}/04_IMD/IMD_rainfall_annual_total_2025.tif", np.nansum(R, 0) * np.where(np.isnan(R).all(0), np.nan, 1), tr)
seas = pd.Series(dates.month).map(SEASON).values
for s in SCOL: write(f"{OUT}/04_IMD/IMD_rainfall_{s.replace('-','')}_total_2025.tif", np.nansum(R[seas == s], 0) * np.where(np.isnan(R).all(0), np.nan, 1), tr)

# ---------------- IMD Tmax GRD (1 deg binary) -> GeoTIFF ----------------
raw = np.fromfile(f"{UP}/Maxtemp_MaxT_2025.GRD", dtype="<f4")
nd = raw.size // (31 * 31); T = raw.reshape(nd, 31, 31)       # [day, lat(7.5->37.5), lon(67.5->97.5)]
T = np.where(T > 99, np.nan, T)
tlat = np.arange(7.5, 38, 1.0); tlon = np.arange(67.5, 98, 1.0)
trT = from_origin(67.0, 38.0, 1.0, 1.0)
T_n = T[:, ::-1, :]
write(f"{OUT}/04_IMD/IMD_Tmax_daily_2025_1deg.tif", T_n, trT, [d.strftime("%Y-%m-%d") for d in dates[:nd]])
write(f"{OUT}/04_IMD/IMD_Tmax_annual_mean_2025.tif", np.nanmean(T_n, 0), trT)

# ---------------- Kolkata region extraction ----------------
box = rf.sel(LATITUDE=slice(22.25, 22.75), LONGITUDE=slice(88.25, 88.5))
rain_k = box.mean(dim=["LATITUDE","LONGITUDE"]).values
iy, ix = np.where(tlat == 22.5)[0][0], np.where(tlon == 88.5)[0][0]
tmax_k = T[:, iy, ix]
MET = pd.DataFrame({"date": dates, "rainfall_mm": np.round(rain_k, 2), "tmax_C": np.round(tmax_k, 2)})
MET["month"] = MET.date.dt.month; MET["season"] = MET.month.map(SEASON)
D = pd.read_csv(f"{OUT}/01_AQI/daily_AQI_long.csv", parse_dates=["date"])
city = D[D.valid_day].groupby("date").agg(city_mean_AQI=("daily_AQI","mean"), n_stations=("daily_AQI","count")).round(1)
MET = MET.merge(city, left_on="date", right_index=True, how="left")
MET.to_csv(f"{OUT}/04_IMD/Kolkata_daily_rainfall_Tmax_AQI_2025.csv", index=False)
mon = MET.groupby("month").agg(rain_total_mm=("rainfall_mm","sum"), rain_days=("rainfall_mm", lambda r: (r >= 2.5).sum()),
                               tmax_mean_C=("tmax_C","mean"), city_mean_AQI=("city_mean_AQI","mean")).round(1)
sea = MET.groupby("season").agg(rain_total_mm=("rainfall_mm","sum"), rain_days=("rainfall_mm", lambda r: (r >= 2.5).sum()),
                                tmax_mean_C=("tmax_C","mean"), city_mean_AQI=("city_mean_AQI","mean")).round(1).loc[list(SCOL)]
v = MET.dropna(subset=["city_mean_AQI","rainfall_mm","tmax_C"])
cor = []
for var in ["rainfall_mm","tmax_C"]:
    r, p = spearmanr(v[var], v.city_mean_AQI); cor.append(("All days", var, "Spearman", round(r,3), p, len(v)))
    for s in SCOL:
        vv = v[v.season == s]; r, p = spearmanr(vv[var], vv.city_mean_AQI); cor.append((s, var, "Spearman", round(r,3), p, len(vv)))
# next-day effect of rain (washout): AQI change vs rain
v2 = MET.copy(); v2["dAQI"] = v2.city_mean_AQI.shift(-1) - v2.city_mean_AQI
vv = v2.dropna(subset=["dAQI"]); vv = vv[vv.rainfall_mm >= 0]
r, p = spearmanr(vv.rainfall_mm, vv.dAQI); cor.append(("All days", "rainfall_mm vs next-day AQI change", "Spearman", round(r,3), p, len(vv)))
COR = pd.DataFrame(cor, columns=["period","variable","method","rho","p_value","n_days"]); COR["p_value"] = COR.p_value.map(lambda x: f"{x:.2e}")
with pd.ExcelWriter(f"{OUT}/04_IMD/IMD_Kolkata_rainfall_Tmax_AQI_2025.xlsx") as xw:
    pd.DataFrame({"Item":["Rainfall","Tmax","Kolkata rainfall","Kolkata Tmax","City mean AQI","Rain day"],
                  "Description":["IMD Pune gridded daily rainfall 0.25 deg (RF25_ind2025_rfp25.nc)",
                                 "IMD Pune gridded daily maximum temperature 1 deg (Maxtemp_MaxT_2025.GRD, 31x31 grid 7.5-37.5N, 67.5-97.5E, float32, missing 99.9)",
                                 "Mean of 0.25 deg grid points within 22.25-22.75N, 88.25-88.50E (Kolkata-Howrah)",
                                 "Grid point 22.5N, 88.5E (nearest 1 deg node)",
                                 "Mean of valid daily AQI across stations with valid data that day",
                                 "Day with rainfall >= 2.5 mm (IMD definition)"]}).to_excel(xw, "README", index=False)
    MET.to_excel(xw, "Daily_365", index=False); mon.to_excel(xw, "Monthly"); sea.to_excel(xw, "Seasonal"); COR.to_excel(xw, "Correlations", index=False)
print(mon.to_string()); print(sea.to_string()); print(COR.to_string())
print("Tmax range", np.nanmin(tmax_k), np.nanmax(tmax_k), "rain annual", np.nansum(rain_k))

# ---------------- figures ----------------
FIG = f"{OUT}/02_Graphs"
fig, axs = plt.subplots(3, 1, figsize=(11, 8.5), dpi=200, sharex=True)
x = np.arange(1, 13); lab = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
cols = [SCOL[SEASON[m]] for m in x]
axs[0].bar(x, mon.city_mean_AQI, color=cols, zorder=3); axs[0].set_ylabel("City mean AQI")
axs[1].bar(x, mon.rain_total_mm, color=cols, zorder=3); axs[1].set_ylabel("Rainfall (mm/month)")
axs[2].plot(x, mon.tmax_mean_C, color=INK, lw=2, marker="o", ms=7, markeredgecolor="white", zorder=3); axs[2].set_ylabel("Mean Tmax (°C)")
for ax, c, f in zip(axs, ["city_mean_AQI","rain_total_mm","tmax_mean_C"], ["{:.0f}","{:.0f}","{:.1f}"]):
    ax.grid(axis="y", color="#e4e3df", lw=0.6, zorder=0)
    for xi, v_ in zip(x, mon[c]): ax.annotate(f.format(v_), (xi, v_), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8, color=INK2)
axs[2].set_xticks(x); axs[2].set_xticklabels(lab)
from matplotlib.patches import Patch
axs[0].legend(handles=[Patch(color=c, label=s) for s, c in SCOL.items()], ncol=4, frameon=False, loc="upper center", fontsize=8.5)
fig.suptitle("Monthly AQI vs rainfall and maximum temperature, Kolkata 2025 (IMD gridded data)", x=0.01, ha="left", fontweight="bold", fontsize=12.5)
fig.tight_layout(); fig.savefig(f"{FIG}/18_AQI_vs_rainfall_Tmax_monthly.png"); plt.close(fig)

fig, axs = plt.subplots(1, 2, figsize=(12, 4.8), dpi=200, sharey=True)
for s, c in SCOL.items():
    vv = v[v.season == s]
    axs[0].scatter(vv.rainfall_mm + 0.1, vv.city_mean_AQI, s=16, color=c, label=s, alpha=0.8, edgecolor="white", lw=0.4)
    axs[1].scatter(vv.tmax_C, vv.city_mean_AQI, s=16, color=c, label=s, alpha=0.8, edgecolor="white", lw=0.4)
axs[0].set_xscale("log"); axs[0].set_xlabel("Daily rainfall (mm, +0.1, log scale)"); axs[1].set_xlabel("Daily Tmax (°C)")
axs[0].set_ylabel("City mean daily AQI")
ra = COR[(COR.period=="All days")&(COR.variable=="rainfall_mm")].rho.iloc[0]; rt = COR[(COR.period=="All days")&(COR.variable=="tmax_C")].rho.iloc[0]
axs[0].set_title(f"AQI vs rainfall (Spearman ρ = {ra:.2f})", loc="left", fontsize=11); axs[1].set_title(f"AQI vs Tmax (Spearman ρ = {rt:.2f})", loc="left", fontsize=11)
for ax in axs: ax.grid(color="#e4e3df", lw=0.6)
axs[1].legend(frameon=False, fontsize=8.5)
fig.tight_layout(); fig.savefig(f"{FIG}/19_AQI_vs_rainfall_Tmax_scatter.png"); plt.close(fig)
