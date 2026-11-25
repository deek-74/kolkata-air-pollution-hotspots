"""Step 1-2: Clean CPCB CAAQMS hourly AQI data (2025) and compute daily / monthly / seasonal AQI.
Input : CPCB 'AQI_Data_Station_Level_Site_<id>_<name>_WBPCB_<Month>_2025_Hourly.xlsx' (day x hour grid of hourly AQI)
Output: outputs/01_AQI/*.xlsx, *.csv
"""
import glob, re, sys, numpy as np, pandas as pd
SRC = sys.argv[1]; OUT = sys.argv[2]
MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]
SEASON = {1:"Winter",2:"Winter",12:"Winter",3:"Summer",4:"Summer",5:"Summer",6:"Monsoon",7:"Monsoon",8:"Monsoon",9:"Monsoon",10:"Post-monsoon",11:"Post-monsoon"}
NICE = {"Padmapukur_Howrah":"Padmapukur","Ghusuri_Howrah":"Ghusuri","Rabindra_Bharati_University_Kolkata":"Rabindra Bharati Univ.",
        "Victoria_Kolkata":"Victoria","Belur_Math_Howrah":"Belur Math","Fort_William_Kolkata":"Fort William","Jadavpur_Kolkata":"Jadavpur",
        "Rabindra_Sarobar_Kolkata":"Rabindra Sarobar","Bidhannagar_Kolkata":"Bidhannagar","Ballygunge_Kolkata":"Ballygunge",
        "Botanical_Garden_Howrah":"Botanical Garden","Dasnagar_Howrah":"Dasnagar"}
FLAT_RUN = 24      # >=24 consecutive identical hourly values => flat-lined (instrument stuck)
SPIKE = 100        # isolated jump >100 AQI points vs both neighbours => spike

def category(a):
    if pd.isna(a): return None
    return ("Good" if a<=50 else "Satisfactory" if a<=100 else "Moderate" if a<=200 else
            "Poor" if a<=300 else "Very Poor" if a<=400 else "Severe")

rows = []
for f in sorted(glob.glob(f"{SRC}/*.xlsx")):
    m = re.search(r"Site_(\d+)_(.+)_WBPCB_(\w+)_2025", f)
    sid, key, mon = m.group(1), m.group(2), MONTHS.index(m.group(3)) + 1
    g = pd.read_excel(f, header=0)
    for _, r in g.iterrows():
        day = int(r.iloc[0])
        for h in range(24):
            rows.append((sid, NICE[key], key.endswith("Howrah") and "Howrah" or "Kolkata",
                         pd.Timestamp(2025, mon, day, h), r.iloc[h + 1]))
H = pd.DataFrame(rows, columns=["site_id","station","city","datetime","aqi_raw"])
H["aqi_raw"] = pd.to_numeric(H["aqi_raw"], errors="coerce")
H = H.sort_values(["station","datetime"]).reset_index(drop=True)

# ---------- cleaning ----------
H["flag"] = np.where(H.aqi_raw.isna(), "missing", "ok")
bad = H.aqi_raw.notna() & ((H.aqi_raw <= 0) | (H.aqi_raw > 500))
H.loc[bad, "flag"] = "non-positive/>500"
def flat_and_spike(s):
    v = s.copy(); out = pd.Series("ok", index=s.index)
    grp = (v != v.shift()).cumsum()
    run = v.groupby(grp).transform("size")
    out[(run >= FLAT_RUN) & v.notna()] = "flat-line"
    d1 = v - v.shift(1); d2 = v - v.shift(-1)
    sp = (d1.abs() > SPIKE) & (d2.abs() > SPIKE) & (np.sign(d1) == np.sign(d2))
    out[sp] = "spike"
    return out
fs = H.groupby("station", group_keys=False)["aqi_raw"].apply(flat_and_spike)
H.loc[(H.flag == "ok") & (fs != "ok"), "flag"] = fs[(H.flag == "ok") & (fs != "ok")]
H["aqi_clean"] = H.aqi_raw.where(H.flag == "ok")

# ---------- daily ----------
H["date"] = H.datetime.dt.normalize()
D = H.groupby(["site_id","station","city","date"]).agg(
    valid_hours=("aqi_clean","count"), aqi_mean=("aqi_clean","mean"),
    aqi_min=("aqi_clean","min"), aqi_max=("aqi_clean","max")).reset_index()
four = H[H.datetime.dt.hour == 16].set_index(["station","date"])["aqi_clean"]
D["aqi_4pm_bulletin"] = [four.get((s, d), np.nan) for s, d in zip(D.station, D.date)]
D["valid_day"] = D.valid_hours >= 18
D["daily_AQI"] = D.aqi_mean.where(D.valid_day).round(0)
D["category"] = D.daily_AQI.map(category)
D["month"] = D.date.dt.month; D["season"] = D.month.map(SEASON)
for c in ["aqi_mean"]: D[c] = D[c].round(1)

# ---------- availability ----------
A = H.groupby("station").agg(total_hours=("aqi_raw","size"), raw_valid=("aqi_raw","count"),
        removed_invalid=("flag", lambda f: (f=="non-positive/>500").sum()),
        removed_flat=("flag", lambda f: (f=="flat-line").sum()),
        removed_spike=("flag", lambda f: (f=="spike").sum()),
        clean_valid=("aqi_clean","count")).reset_index()
vd = D.groupby("station").valid_day.sum().rename("valid_days")
A = A.merge(vd, on="station")
A["hourly_capture_%"] = (A.clean_valid / A.total_hours * 100).round(1)
A["daily_capture_%"] = (A.valid_days / 365 * 100).round(1)
mvd = D.pivot_table(index="station", columns="month", values="valid_day", aggfunc="sum")
mvd.columns = [MONTHS[c-1][:3] for c in mvd.columns]
A = A.merge(mvd.reset_index(), on="station")
meta = H[["site_id","station","city"]].drop_duplicates()
A = meta.merge(A, on="station")

# ---------- monthly / seasonal / annual ----------
V = D[D.valid_day]
M = V.groupby(["station","month"]).daily_AQI.agg(["mean","median","max","count"]).round(1).reset_index()
M.columns = ["station","month","mean_AQI","median_AQI","max_AQI","valid_days"]
M["month_name"] = M.month.map(lambda x: MONTHS[x-1][:3])
M["category"] = M.mean_AQI.map(category)
Mw = M.pivot(index="station", columns="month", values="mean_AQI"); Mw.columns = [MONTHS[c-1][:3] for c in Mw.columns]
S = V.groupby(["station","season"]).daily_AQI.agg(["mean","median","max","count"]).round(1).reset_index()
S.columns = ["station","season","mean_AQI","median_AQI","max_AQI","valid_days"]
Sw = S.pivot(index="station", columns="season", values="mean_AQI")[["Winter","Summer","Monsoon","Post-monsoon"]]
Y = V.groupby("station").daily_AQI.agg(annual_mean="mean", annual_median="median", annual_max="max", valid_days="count").round(1)
cats = ["Good","Satisfactory","Moderate","Poor","Very Poor","Severe"]
cc = V.pivot_table(index="station", columns="category", values="daily_AQI", aggfunc="count").reindex(columns=cats).fillna(0).astype(int)
cc.columns = [f"days_{c}" for c in cc.columns]
Y = meta.set_index("station").join(Y).join(Sw)
Y = Y.join(cc)
Y["annual_mean_season_balanced"] = Y[["Winter","Summer","Monsoon","Post-monsoon"]].mean(axis=1).round(1)
Y = Y.reset_index().sort_values("annual_mean_season_balanced", ascending=False)
Y["exceed_days_>100"] = V.groupby("station").daily_AQI.apply(lambda s: (s > 100).sum()).reindex(Y.station).values
Y["category_annual"] = Y.annual_mean.map(category)

# ---------- write ----------
H.to_csv(f"{OUT}/hourly_AQI_cleaned_all_stations.csv", index=False, columns=["site_id","station","city","datetime","aqi_raw","flag","aqi_clean"])
Dw = D.pivot(index="date", columns="station", values="daily_AQI")
with pd.ExcelWriter(f"{OUT}/AQI_Kolkata_Howrah_2025.xlsx", engine="openpyxl") as xw:
    pd.DataFrame({"Item":[
      "Source","Data content","Study period","Seasons (IMD)","Cleaning rule 1","Cleaning rule 2","Cleaning rule 3",
      "Daily AQI","Valid day","Monthly / seasonal","AQI categories","Limitation"],
     "Description":[
      "CPCB CCR portal, CAAQMS station-level hourly AQI (WBPCB stations), Jan-Dec 2025",
      "Hourly National AQI values already computed by CPCB from 24-h running averages (PM2.5, PM10, NO2, SO2, NH3) and 8-h max (CO, O3); AQI = max sub-index",
      "01-01-2025 to 31-12-2025, 12 stations (Kolkata 7, Howrah 5)",
      "Winter = Jan, Feb, Dec; Summer = Mar-May; Monsoon = Jun-Sep; Post-monsoon = Oct-Nov",
      "Missing/blank, non-numeric, zero, negative or >500 hourly values removed",
      f"Flat-lined readings removed: >= {FLAT_RUN} consecutive identical hourly values",
      f"Isolated spikes removed: hour differing by >{SPIKE} AQI points from both neighbouring hours (same direction)",
      "Mean of valid hourly AQI values for the calendar day (also reported: CPCB 4 PM bulletin value)",
      ">= 18 of 24 hours (75%) valid after cleaning; otherwise daily AQI left blank",
      "Mean of valid daily AQI values. Annual: simple mean of valid days AND season-balanced mean (average of 4 seasonal means, used for ranking because some stations have data gaps in particular seasons)",
      "Good 0-50, Satisfactory 51-100, Moderate 101-200, Poor 201-300, Very Poor 301-400, Severe 401-500",
      "Pollutant concentrations not in downloaded files: sub-index recomputation and prominent pollutant to be done in Phase II"]}).to_excel(xw, "README", index=False)
    A.to_excel(xw, "Data_Availability", index=False)
    D[["site_id","station","city","date","season","valid_hours","valid_day","aqi_mean","aqi_min","aqi_max","aqi_4pm_bulletin","daily_AQI","category"]].to_excel(xw, "Daily_AQI_long", index=False)
    Dw.to_excel(xw, "Daily_AQI_wide")
    M[["station","month","month_name","mean_AQI","median_AQI","max_AQI","valid_days","category"]].to_excel(xw, "Monthly_AQI_long", index=False)
    Mw.to_excel(xw, "Monthly_AQI_wide")
    S.to_excel(xw, "Seasonal_AQI_long", index=False)
    Y.to_excel(xw, "Annual_Station_Summary", index=False)
D.to_csv(f"{OUT}/daily_AQI_long.csv", index=False)
M.to_csv(f"{OUT}/monthly_AQI_long.csv", index=False)
Y.to_csv(f"{OUT}/annual_station_summary.csv", index=False)
print(A[["station","hourly_capture_%","valid_days","removed_flat","removed_spike","removed_invalid"]].to_string())
print(Y[["station","annual_mean","annual_mean_season_balanced","Winter","Summer","Monsoon","Post-monsoon","exceed_days_>100"]].to_string())
print("4pm vs mean corr:", D[["aqi_4pm_bulletin","daily_AQI"]].corr().iloc[0,1])
