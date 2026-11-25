"""PPT v3: station coordinates, temporal + seasonal slides, consistent maps, figure numbers, references slide."""
import copy, sys
from PIL import Image, ImageChops
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_THEME_COLOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
import pandas as pd
SRC, OUT, DST = sys.argv[1], sys.argv[2], sys.argv[3]
TMP = "/tmp/claude-0/-home-claude/513ca190-e76b-5be9-b48b-c9a4ad698c82/scratchpad"
GREY = RGBColor(0x52, 0x51, 0x4E)
def autocrop(src, dst, top=0, bottom=0):
    im = Image.open(src).convert("RGB"); bg = Image.new("RGB", im.size, (255, 255, 255))
    l, t, r, b = ImageChops.difference(im, bg).getbbox(); im = im.crop((l, t + top, r, b - bottom)); im.save(dst); return im.size
sz = {}
sz["f1"] = autocrop(f"{OUT}/06_Maps/Fig1_study_area_stations.png", f"{TMP}/f1.png")
sz["f2"] = autocrop(f"{OUT}/02_Graphs/14_AQI_station_month_heatmap.png", f"{TMP}/f2.png", top=80)
sz["f3"] = autocrop(f"{OUT}/02_Graphs/Fig3_monthly_AQI_trend.png", f"{TMP}/f3.png")
sz["f4"] = autocrop(f"{OUT}/06_Maps/Fig4_seasonal_AQI_maps.png", f"{TMP}/f4.png")
sz["f5"] = autocrop(f"{OUT}/06_Maps/Fig5_GIS_findings_AQI_LULC_industry.png", f"{TMP}/f5.png")
im = Image.open(f"{OUT}/02_Graphs/23_station_landuse_fingerprint.png"); w, h = im.size; im.crop((0, 70, w, h - 45)).save(f"{TMP}/f6.png"); sz["f6"] = Image.open(f"{TMP}/f6.png").size
sz["f7"] = autocrop(f"{OUT}/06_Maps/Fig7_high_vs_low_station_zooms.png", f"{TMP}/f7.png")

p = Presentation(SRC)
S = list(p.slides)
gis, appx, cert = S[3], S[5], S[6]
def named(sl, n): return [x for x in sl.shapes if x.name == n]
CARD = {k: copy.deepcopy(named(gis, k)[0]._element) for k in ["Shape 2", "Text 3", "Text 4", "Text 5"]}
SLNUM = copy.deepcopy(named(gis, "Slide Number Placeholder 0")[0]._element)
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
def place(sh, x, y, w=None, h=None):
    sh.left, sh.top = Inches(x), Inches(y)
    if w: sh.width = Inches(w)
    if h: sh.height = Inches(h)
def add_el(sl, el):
    e = copy.deepcopy(el); sl.shapes._spTree.append(e); return [x for x in sl.shapes if x._element is e][0]
def set_text(sh, text, size=None):
    tf = sh.text_frame; r = tf.paragraphs[0].runs[0]; r.text = text
    for extra in tf.paragraphs[0].runs[1:]: extra._r.getparent().remove(extra._r)
    for pp in tf.paragraphs[1:]: pp._p.getparent().remove(pp._p)
    if size: r.font.size = Pt(size)
def card(sl, x, y, w, h, big, desc, src=None, big_size=17):
    c = add_el(sl, CARD["Shape 2"]); place(c, x, y, w, h)
    b = add_el(sl, CARD["Text 3"]); place(b, x + 0.08, y + 0.05, w - 0.16, 0.4); set_text(b, big, big_size)
    d = add_el(sl, CARD["Text 4"]); place(d, x + 0.08, y + 0.45, w - 0.16, h - (0.75 if src else 0.5)); set_text(d, desc, 9)
    if src: s_ = add_el(sl, CARD["Text 5"]); place(s_, x + 0.08, y + h - 0.28, w - 0.16, 0.22); set_text(s_, src, 8)
def caption(sl, x, y, w, text, h=0.24):
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    r = tf.paragraphs[0].add_run(); r.text = text; r.font.size = Pt(8.5); r.font.italic = True; r.font.color.rgb = GREY
    tb.name = text.split(".")[0] + " caption"; return tb
def pic(sl, path, x, y, w=None, h=None, name="", descr=""):
    pc = sl.shapes.add_picture(path, Inches(x), Inches(y), width=Inches(w) if w else None, height=Inches(h) if h else None)
    pc.name = name; pc._element.nvPicPr.cNvPr.set("descr", descr); return pc
def set_notes(sl, text):
    nsl = sl.notes_slide; tf = nsl.notes_text_frame
    if tf is None:
        body = [x for x in gis.notes_slide.placeholders if x.placeholder_format.type == 2][0]
        nsl.shapes._spTree.append(copy.deepcopy(body._element)); tf = nsl.notes_text_frame
    tf.text = text
def new_slide(title, notes=""):
    ns = p.slides.add_slide(gis.slide_layout)
    ns.placeholders[100].text_frame.text = title
    ns.shapes._spTree.append(copy.deepcopy(SLNUM))
    if notes: set_notes(ns, notes)
    return ns
def H(key, w): W_, H_ = sz[key]; return w * H_ / W_
def Wd(key, h): W_, H_ = sz[key]; return h * W_ / H_
def table(sl, x, y, w, colw, rows, header, fs=8, rh=0.255, hdr_fill=MSO_THEME_COLOR.TEXT_2):
    shp = sl.shapes.add_table(len(rows) + 1, len(header), Inches(x), Inches(y), Inches(w), Inches(rh * (len(rows) + 1)))
    t = shp.table
    for j, cw in enumerate(colw): t.columns[j].width = Inches(cw)
    for i in range(len(rows) + 1): t.rows[i].height = Inches(rh)
    for i, row in enumerate([header] + rows):
        for j, v in enumerate(row):
            c = t.cell(i, j); c.margin_left = c.margin_right = Inches(0.05); c.margin_top = c.margin_bottom = Inches(0.01)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.fill.solid()
            if i == 0: c.fill.fore_color.theme_color = hdr_fill
            else: c.fill.fore_color.theme_color = MSO_THEME_COLOR.BACKGROUND_2 if i % 2 else MSO_THEME_COLOR.BACKGROUND_1
            tf = c.text_frame; tf.text = str(v); para = tf.paragraphs[0]
            para.alignment = PP_ALIGN.LEFT if j in (1,) or (isinstance(v, str) and not v.replace(".", "").isdigit()) else PP_ALIGN.CENTER
            r = para.runs[0]; r.font.size = Pt(fs); r.font.bold = (i == 0)
            if i == 0: r.font.color.theme_color = MSO_THEME_COLOR.BACKGROUND_1
            else: r.font.color.theme_color = MSO_THEME_COLOR.TEXT_1
    return shp

st = pd.read_csv(f"{OUT}/03_Stations/stations_numbered.csv")
Y = pd.read_csv(f"{OUT}/01_AQI/annual_station_summary.csv").set_index("station")

# ---------- Slide: study area & stations ----------
s4 = new_slide("Study area and monitoring stations",
    "Twelve WBPCB continuous ambient air quality monitoring stations (CAAQMS): 7 in Kolkata and 5 in Howrah. Coordinates are from the CPCB list of CAAQM stations "
    "(station codes matched to the downloaded file IDs) and checked on the map; Dasnagar from the CPCB/IQAir station map. Study box 88.23–88.46°E, 22.45–22.68°N.")
mh = 4.0; mw = Wd("f1", mh)
pic(s4, f"{TMP}/f1.png", 0.5, 0.95, h=mh, name="Fig 1 map", descr="Map of the 12 CAAQMS stations in Kolkata and Howrah")
caption(s4, 0.5, 0.95 + mh + 0.04, mw, "Fig. 1. Study area with the 12 CAAQMS stations (numbers match Table 1).")
rows = [[int(r.no), r.station, r.city, f"{r.lat:.4f}", f"{r.lon:.4f}", f"{r.annual_mean_season_balanced:.0f}"] for r in st.itertuples()]
tx = 0.5 + mw + 0.25; tw = 9.5 - tx
table(s4, tx, 0.95, tw, [0.32, 1.55, 0.68, 0.85, 0.85, tw - 4.25], rows, ["No.", "Station", "City", "Latitude (°N)", "Longitude (°E)", "Annual AQI"], fs=8, rh=0.27)
caption(s4, tx, 0.95 + 0.27 * 13 + 0.06, tw, "Table 1. Station coordinates (WGS 84) and season-balanced annual mean AQI, 2025. Source: CPCB CAAQMS station list.", h=0.4)

# ---------- Slide: temporal variation ----------
s5 = new_slide("Temporal variation of AQI, 2025",
    "Fig. 2: monthly mean AQI for every station; colours are CPCB categories. Fig. 3: the network monthly mean (blue), the range across the 12 stations (shaded) and the daily city mean (grey). "
    "AQI follows a U-shape: 202 in January, falling to 49 in July, rising again to 212 in December. Winter months are 'Poor' at the Howrah stations; the monsoon brings 'Good/Satisfactory' air everywhere. "
    "Highest monthly mean: Belur Math 308 in December and Padmapukur 285 in January; lowest: Rabindra Sarobar 32 in July. Daily AQI per station (12 graphs) is in outputs/02_Graphs.")
w2 = 4.6; h2 = H("f2", w2); w3 = 4.3; h3 = H("f3", w3); hh = max(h2, h3)
pic(s5, f"{TMP}/f2.png", 0.5, 0.95, w=w2, name="Fig 2 heatmap", descr="Heatmap of monthly mean AQI by station")
pic(s5, f"{TMP}/f3.png", 9.5 - w3, 0.95 + (hh - h3) / 2, w=w3, name="Fig 3 trend", descr="Monthly AQI trend with station range")
cy = 0.95 + hh + 0.05
caption(s5, 0.5, cy, w2, "Fig. 2. Monthly mean AQI by station (K = Kolkata, H = Howrah).")
caption(s5, 9.5 - w3, cy, w3, "Fig. 3. Network monthly mean AQI with range across stations.")
ky = cy + 0.38; kh = 5.12 - ky; kw = (9.0 - 0.2) / 3
card(s5, 0.5, ky, kw, kh, "202 → 49 → 212", "Network monthly mean AQI: January → July → December (U-shaped annual cycle)", "Fig. 3", 15)
card(s5, 0.5 + kw + 0.1, ky, kw, kh, "Nov–Jan", "'Poor' months at the Howrah stations; Belur Math peaks at 308 in December", "Fig. 2", 15)
card(s5, 0.5 + 2 * (kw + 0.1), ky, kw, kh, "Jun–Sep", "'Good/Satisfactory' at all stations; lowest: Rabindra Sarobar 32 (July)", "Fig. 2", 15)

# ---------- Slide: seasonal maps ----------
s6 = new_slide("Seasonal AQI maps (IMD seasons, 2025)",
    "Fig. 4 shows the seasonal mean AQI at each station, using the same CPCB colours and symbol sizes in all four panels. "
    "Winter: network mean 185; Ghusuri, Padmapukur and Belur Math are 'Poor' (>200). Post-monsoon: 138, 11 of 12 stations 'Moderate'. Summer: 79, only Dasnagar above 100. "
    "Monsoon: 54, all stations 'Good' or 'Satisfactory'. The Howrah industrial belt stays highest in winter and post-monsoon; Rabindra Sarobar is lowest in winter and monsoon.")
mh = 3.98; mw = Wd("f4", mh)
pic(s6, f"{TMP}/f4.png", 0.5, 0.95, h=mh, name="Fig 4 seasonal maps", descr="Four maps of seasonal mean AQI at 12 stations")
caption(s6, 0.5, 0.95 + mh + 0.03, mw, "Fig. 4. Seasonal mean AQI at each station (IMD seasons, 2025).")
tx = 0.5 + mw + 0.25; tw = 9.5 - tx
srows = []
for sname, lab in [("Winter", "Winter (Dec–Feb)"), ("Summer", "Summer (Mar–May)"), ("Monsoon", "Monsoon (Jun–Sep)"), ("Post-monsoon", "Post-mon. (Oct–Nov)")]:
    c = Y[sname]; srows.append([lab, f"{c.mean():.0f}", f"{c.idxmax().replace(' Univ.', '')} {c.max():.0f}", f"{c.idxmin().replace(' Univ.', '')} {c.min():.0f}"])
table(s6, tx, 0.95, tw, [1.35, 0.62, (tw - 1.97) / 2, (tw - 1.97) / 2], srows, ["Season", "Mean", "Highest", "Lowest"], fs=8, rh=0.34)
caption(s6, tx, 0.95 + 0.34 * 5 + 0.05, tw, "Table 2. Seasonal network mean AQI and highest/lowest station.", h=0.36)
card(s6, tx, 3.2, tw, 1.55, "3.4× winter / monsoon",
     "Winter inversions and calm winds trap pollutants, and the Howrah industrial stations turn 'Poor'. Monsoon rain washes them out, so every station is 'Good' or 'Satisfactory'.", "Fig. 4, Table 2", 15)

# ---------- GIS findings slide (existing) ----------
for x in [x for x in gis.shapes if x.shape_type == 13]: x._element.getparent().remove(x._element)
mh = 3.9; mw = Wd("f5", mh)
m5 = pic(gis, f"{TMP}/f5.png", 0.5, 0.95, h=mh, name="Fig 5 map", descr="Map of annual AQI with LULC, industrial land and roads")
fx = 0.5 + mw + 0.2; fw = 9.5 - fx; fh = H("f6", fw)
f6 = pic(gis, f"{TMP}/f6.png", fx, 0.95, w=fw, name="Fig 6 chart", descr="Land-use fingerprint chart by station")
for el in (m5._element, f6._element): tr = el.getparent(); tr.remove(el); tr.insert(3, el)
caption(gis, 0.5, 0.95 + mh + 0.03, mw, "Fig. 5. Annual mean AQI with LULC, OSM industrial land and roads.", h=0.36)
caption(gis, fx, 0.95 + fh + 0.03, fw, "Fig. 6. AQI and land cover within 1 km of each station, sorted by AQI.")
ky = 0.95 + fh + 0.32; kh = 5.12 - ky; kw = (fw - 0.3) / 4
for i, grp in enumerate([named(gis, n) for n in ["Shape 2", "Text 3", "Text 4", "Text 5"]]):
    for k, sh in enumerate(grp):
        x = fx + k * (kw + 0.1)
        if i == 0: place(sh, x, ky, kw, kh)
        elif i == 1: place(sh, x + 0.06, ky + 0.04, kw - 0.12, 0.38)
        elif i == 2: place(sh, x + 0.06, ky + 0.42, kw - 0.12, kh - 0.68)
        else: place(sh, x + 0.06, ky + kh - 0.26, kw - 0.12, 0.22)
srcs = named(gis, "Text 5")
for sh, t in zip(srcs, ["Fig. 6 (Esri LULC)", "Spearman, n = 12", "Fig. 5 (OSM)", "Fig. 3, IMD"]): set_text(sh, t)

# ---------- Appendix (existing) ----------
for x in [x for x in appx.shapes if x.shape_type == 13]: x._element.getparent().remove(x._element)
mh = 3.95; mw = Wd("f7", mh)
f7 = pic(appx, f"{TMP}/f7.png", 0.5, 0.95, h=mh, name="Fig 7 zooms", descr="2 km zoom maps of the 3 most and 3 least polluted stations")
el = f7._element; tr = el.getparent(); tr.remove(el); tr.insert(3, el)
caption(appx, 0.5, 0.95 + mh + 0.04, mw, "Fig. 7. Land use within 2 km of the three most and three least polluted stations (LULC 2025 + OSM).", h=0.36)
cx = 0.5 + mw + 0.2
place(named(appx, "Shape 2")[0], cx, 0.95, 9.5 - cx, mh); place(named(appx, "Text 4")[0], cx + 0.08, 1.02, 9.5 - cx - 0.16, mh - 0.14)

# ---------- References & data sources ----------
s10 = new_slide("References and data sources", "All datasets were downloaded between October and November 2026. Links are clickable.")
DATA = [("CPCB CCR – CAAQMS hourly AQI, 12 WBPCB stations, 2025", "https://airquality.cpcb.gov.in/ccr/"),
        ("CPCB – list of CAAQM stations (codes and coordinates)", "https://app.cpcbccr.com/ccr_docs/caaqms_list_All_India.pdf"),
        ("CPCB (2014) National Air Quality Index – breakpoints and categories", "https://smartnet.niua.org/sites/default/files/resources/Air%20Quality%20Index.pdf"),
        ("Esri / Impact Observatory Sentinel-2 10 m LULC 2025 (tile 45Q)", "https://livingatlas.arcgis.com/landcover"),
        ("OpenStreetMap, Geofabrik Eastern Zone (India) – roads, industrial land", "https://download.geofabrik.de/asia/india/eastern-zone.html"),
        ("Google Open Buildings v3 (tile 3a1)", "https://sites.research.google/open-buildings/"),
        ("IMD Pune gridded daily rainfall 0.25° (NetCDF)", "https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html"),
        ("IMD Pune gridded daily max temperature 1.0° (binary)", "https://imdpune.gov.in/cmpg/Griddata/Max_1_Bin.html")]
LIT = [("Ashbaugh, Malm & Sadeh (1985). Residence time probability analysis of sulfur at Grand Canyon. Atmos. Environ. 19(8).", "https://doi.org/10.1016/0004-6981(85)90256-2"),
       ("Karar & Gupta (2006). Seasonal variations and chemical characterisation of ambient PM10 at residential and industrial sites of Kolkata. Atmos. Res. 81.", None),
       ("Misra, Imasu & Takeuchi (2019). Impact of urban growth on air quality in Indian cities using hierarchical Bayesian approach. Atmosphere 10, 517.", "https://www.mdpi.com/2073-4433/10/9/517"),
       ("Jaiswal et al. (2024). Assessing the impact of land use changes on PM2.5: a GWR approach. EGU24-16601.", "https://meetingorganizer.copernicus.org/EGU24/EGU24-16601.html"),
       ("CSE (2025). Winter pollution crisis in megacities of India: Kolkata.", "https://www.cseindia.org/winter-pollution-crisis-in-megacities-of-india-going-beyond-delhi-kolkata-12643"),
       ("TERI (2024). Air pollution emission inventory and source apportionment, Kolkata–Howrah (for WBPCB).", "https://teriin.org/project/air-pollution-emission-inventory-source-apportionment-and-atmospheric-carrying-capacity"),
       ("NEERI (2019). Source apportionment of air pollution in Kolkata (for WBPCB).", None),
       ("CPCB (2024). Counter affidavit before the NGT on CAAQMS in Kolkata (case record).", None)]
def ref_box(x, w, head, items, n0):
    c = add_el(s10, CARD["Shape 2"]); place(c, x, 0.95, w, 4.2)
    tb = s10.shapes.add_textbox(Inches(x + 0.12), Inches(1.02), Inches(w - 0.24), Inches(4.05)); tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = 0
    r = tf.paragraphs[0].add_run(); r.text = head; r.font.bold = True; r.font.size = Pt(10.5)
    for i, (t, u) in enumerate(items, n0):
        para = tf.add_paragraph(); para.space_before = Pt(5)
        r = para.add_run(); r.text = f"[{i}] {t} "; r.font.size = Pt(9)
        if u:
            r2 = para.add_run(); r2.text = u; r2.font.size = Pt(8); r2.hyperlink.address = u; r2.font.color.theme_color = MSO_THEME_COLOR.HYPERLINK
ref_box(0.5, 4.4, "Data sources", DATA, 1)
ref_box(5.0, 4.5, "Literature", LIT, len(DATA) + 1)

# ---------- reorder: title, obj, method, study area, temporal, seasonal, GIS, detailed, appendix, refs, certificate ----------
lst = p.slides._sldIdLst; ids = list(lst)
order_ids = [sl.slide_id for sl in [S[0], S[1], S[2], s4, s5, s6, gis, S[4], appx, s10, cert]]
idmap = {int(e.get("id")): e for e in ids}
for e in ids: lst.remove(e)
for i in order_ids: lst.append(idmap[i])
p.save(DST); print("saved", len(p.slides))
