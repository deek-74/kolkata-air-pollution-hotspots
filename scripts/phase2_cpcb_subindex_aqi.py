"""PHASE II (ready to run once pollutant CONCENTRATION files are downloaded from CPCB CCR).
CPCB National AQI: sub-index per pollutant by linear interpolation within breakpoints,
24-h average for PM10, PM2.5, NO2, SO2, NH3; maximum 8-h running average for CO (mg/m3) and O3.
AQI = max sub-index; valid only if >= 3 pollutants available and at least one is PM2.5 or PM10.
Usage:  python phase2_cpcb_subindex_aqi.py hourly_concentrations.csv out.csv
Input CSV columns: station, datetime, PM2.5, PM10, NO2, SO2, CO, O3, NH3   (CO in mg/m3, others ug/m3)
"""
import sys, numpy as np, pandas as pd
IDX = [(0, 50), (51, 100), (101, 200), (201, 300), (301, 400), (401, 500)]
BP = {"PM10": [0, 50, 100, 250, 350, 430, 1000], "PM2.5": [0, 30, 60, 90, 120, 250, 500],
      "NO2": [0, 40, 80, 180, 280, 400, 1000], "SO2": [0, 40, 80, 380, 800, 1600, 3000],
      "CO": [0, 1.0, 2.0, 10, 17, 34, 50], "O3": [0, 50, 100, 168, 208, 748, 1000],
      "NH3": [0, 200, 400, 800, 1200, 1800, 3000]}
def sub_index(c, pol):
    if pd.isna(c) or c < 0: return np.nan
    b = BP[pol]
    for k in range(6):
        lo, hi = b[k], b[k + 1]
        if c <= hi:
            ilo, ihi = IDX[k]; lo_ = lo if k == 0 else lo + (1e-9)
            return round(ilo + (ihi - ilo) * (c - lo) / (hi - lo))
    return 500
def daily_aqi(h):
    h = h.set_index("datetime").sort_index()
    out = {}
    for p in ["PM10", "PM2.5", "NO2", "SO2", "NH3"]:
        if p in h: out[p] = h[p].resample("D").apply(lambda s: s.mean() if s.count() >= 16 else np.nan)
    for p in ["CO", "O3"]:
        if p in h:
            r8 = h[p].rolling("8h", min_periods=6).mean()
            out[p] = r8.resample("D").max()
    D = pd.DataFrame(out)
    S = pd.DataFrame({f"SI_{p}": D[p].map(lambda v, p=p: sub_index(v, p)) for p in D})
    n = S.notna().sum(axis=1); pm = S.filter(regex="SI_PM").notna().any(axis=1)
    D["AQI"] = S.max(axis=1).where((n >= 3) & pm)
    D["prominent_pollutant"] = S.idxmax(axis=1).str.replace("SI_", "").where(D.AQI.notna())
    return pd.concat([D, S], axis=1)
if __name__ == "__main__":
    df = pd.read_csv(sys.argv[1], parse_dates=["datetime"])
    res = df.groupby("station", group_keys=True).apply(daily_aqi).reset_index()
    res.to_csv(sys.argv[2], index=False); print(res.head())
