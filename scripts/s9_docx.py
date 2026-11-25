"""Step 9: update the 2-page summary in place (keeps her formatting)."""
import copy, sys
from docx import Document
SRC, DST, EXTRA = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "")
d = Document(SRC); P = d.paragraphs

def setp(p, parts):
    """parts = [(text, bold)], reuse first run formatting."""
    runs = p.runs; base = runs[0]
    for r in runs[1:]: r._r.getparent().remove(r._r)
    base.text = parts[0][0]; base.bold = parts[0][1]
    last = base._r
    for t, b in parts[1:]:
        nr = copy.deepcopy(base._r); last.addnext(nr); last = nr
        from docx.text.run import Run
        R = Run(nr, p); R.text = t; R.bold = b
def clone_after(p_ref, p_after, parts):
    new = copy.deepcopy(p_ref._p); p_after._p.addnext(new)
    from docx.text.paragraph import Paragraph
    np_ = Paragraph(new, p_after._parent); setp(np_, parts); return np_

setp(P[12], [("Data acquisition → QA/QC and cleaning → daily/monthly/seasonal AQI → meteorological and CPF analysis → LULC, road and building buffer metrics → spatial interpolation and hotspot detection → regression and recommendations.", True),
             (" Seasons follow the IMD convention: Winter (Jan, Feb, Dec), Summer (Mar–May), Monsoon (Jun–Sep) and Post-monsoon (Oct–Nov). Analysis is scripted in Python (pandas, rasterio, GeoPandas) with QGIS for map layouts.", False)])
setp(P[13], [("4. Work Done So Far: Preliminary Analysis (January–December 2025)", True)])
setp(P[16], [("Sources:", True), (" NEERI (2017–18) attributed winter PM2.5 to secondary aerosols (32%) and vehicles (25%); TERI found non-energy sources (road/construction dust, refuse burning, cremation) give 61% of PM2.5 in KMC.", False)])
setp(P[18], [("Land use link and gap:", True), (" Built-up areas show the highest and dense vegetation the lowest PM2.5 in Indian cities (Jaiswal et al., 2024; Misra et al., 2019), but no Kolkata study yet combines 10 m LULC and building footprints with season-wise hotspot analysis across Kolkata and Howrah.", False)])
P[19]._p.getparent().remove(P[19]._p)
setp(P[20], [("4.2 Study area and monitoring network:", True),
             (" Twelve WBPCB CAAQMS stations, seven in Kolkata (Victoria, Fort William, Ballygunge, Jadavpur, Rabindra Sarobar, Bidhannagar, Rabindra Bharati University) and five in Howrah (Padmapukur, Ghusuri, Belur Math, Botanical Garden, Dasnagar). Coordinates were taken from CPCB station metadata (station codes matched to file IDs) and a GIS point layer was created; the analysis box is 88.23–88.46°E, 22.45–22.68°N.", False)])
# table
t = d.tables[0]
rows = [["Air quality", "Hourly National AQI (CPCB, from PM2.5, PM10, NO₂, SO₂, CO, O₃, NH₃)", "CPCB CCR portal", "Hourly, 12 stations", "Cleaned, analysed"],
        ["LULC", "9-class land cover (built area, trees, crops, water, etc.)", "Esri / Impact Observatory (Sentinel-2)", "10 m, 2025", "Clipped, buffers done"],
        ["Roads & buildings", "OSM major roads; footprints, area, confidence", "Geofabrik OSM; Google Open Buildings v3", "Vector", "Clipping in progress"],
        ["Meteorology", "Daily rainfall; daily maximum temperature", "IMD Pune gridded data", "0.25° / 1.0°", "GeoTIFF, analysed"]]
for i, r in enumerate(rows, 1):
    for j, v in enumerate(r):
        c = t.rows[i].cells[j]; p0 = c.paragraphs[0]; setp(p0, [(v, None)])
setp(P[22], [("Study period: 1 January – 31 December 2025 (365 days).", None)])
setp(P[23], [("4.4 Data cleaning (done):", True),
             (" 144 monthly hourly-AQI files were merged (105,120 station-hours). Missing, zero, negative or >500 values, flat-lined runs (≥24 identical hours; 1,192 h at Ballygunge, Jul–Oct) and isolated spikes were removed. A daily AQI was kept only when ≥18 of 24 hours were valid: 90% of station-days are valid (Jadavpur 360, Ballygunge 246, Fort William 239 days). Daily means agree with CPCB's 4 PM bulletin AQI (r = 0.99).", False)])
res = [
    ("4.5 Preliminary results:", " Daily, monthly and seasonal AQI, station graphs, an IMD-based meteorology table and LULC buffer metrics were produced (Excel, graphs, GeoPackage and maps)."),
    ("Seasonality:", " Mean daily AQI was 185 in winter, 137 post-monsoon, 79 in summer and 55 in the monsoon (3.4× winter/monsoon). 40% of station-days exceeded AQI 100 ('Moderate' or worse); 91 station-days were 'Very Poor'. Nov–Jan was 'Poor' at most stations; Belur Math reached 308 in December."),
    ("Spatial differences:", " Season-balanced annual AQI was highest at Padmapukur (138), Ghusuri (133), Jadavpur (131) and Belur Math (129) and lowest at Rabindra Sarobar (81) and Bidhannagar (88). Howrah stations averaged 116 versus 102 in Kolkata."),
    ("Meteorology:", " Kolkata received 1,898 mm of rain in 2025. City AQI fell with daily rainfall (Spearman ρ = −0.75, n = 365) and with Tmax (ρ = −0.47), reflecting monsoon wash-out and deeper summer mixing."),
    ("Land use:", " Within 1 km, built-up cover ranged from 40% (Botanical Garden) to >99% (Padmapukur, Ghusuri, Jadavpur, Ballygunge). Green cover within 1 km was negatively related to station AQI (ρ = −0.68, p = 0.02, n = 12), whereas 2 km composition showed no clear link, which suggests local sources dominate." + EXTRA),
    ("Limitations:", " The downloaded files contain AQI, not pollutant concentrations, so sub-indices and the prominent pollutant are deferred to Phase II. Google Open Buildings tile 3a1 fully covers 8 of 12 station buffers; Ghusuri, Belur Math, Rabindra Bharati University and most of Dasnagar need tile 39f (OSM buildings and LULC built-up % are used meanwhile)."),
]
after = P[23]
lead = clone_after(P[23], after, [(res[0][0], True), (res[0][1], False)]); after = lead
for h, tx in res[1:]:
    after = clone_after(P[17], after, [(h, True), (tx, False)])
# Phase II
setp(P[25], [("A. Pollutant-wise analysis:", True), (" Download hourly concentrations; recompute AQI sub-indices (24-h PM, NO₂, SO₂, NH₃; 8-h CO, O₃), prominent pollutant, NAAQS exceedance and diurnal profiles.", False)])
setp(P[26], [("B. Meteorology and source direction:", True), (" Wind speed/direction from CAAQMS; wind and pollution roses; CPF = m(Δθ)/n(Δθ) at the 75th percentile, calms < 1 m/s excluded (Ashbaugh et al., 1985), using R openair.", False)])
setp(P[27], [("C. LULC verification:", True), (" Stratified random points checked on Google Earth (confusion matrix, overall accuracy, kappa); add 500 m buffers.", False)])
setp(P[28], [("D. Roads and buildings:", True), (" Complete clipping of OSM roads (road length density, km/km²) and Google Open Buildings incl. tile 39f (count, footprint cover, confidence ≥ 0.70) for all 12 stations.", False)])
setp(P[29], [("E. Spatial interpolation:", True), (" Inverse Distance Weighting of seasonal AQI/pollutants, validated by leave-one-out cross-validation.", False)])
setp(P[31], [("G. Integration:", True), (" Multiple regression of seasonal AQI on buffer LULC, road, building and meteorological variables, interpreted with CPF source directions.", False)])
setp(P[32], [("Tentative timeline:", True), (" Nov–Dec 2026: pollutant-wise data and roads/buildings. Jan 2027: meteorology and CPF. Feb 2027: LULC verification. Mar 2027: IDW, Gi* hotspots, regression. Apr 2027: thesis writing.", False)])
for p in d.paragraphs:
    if p.text.startswith("Chowdhury"): p._p.getparent().remove(p._p)
d.save(DST); print("saved")
