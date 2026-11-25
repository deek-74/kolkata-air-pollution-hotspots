"""Step 9: update Deeksha's 6-slide PPT in place (keeps her design)."""
import copy, sys
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
SRC, OUT, DST = sys.argv[1], sys.argv[2], sys.argv[3]
im = Image.open(f"{OUT}/02_Graphs/14_AQI_station_month_heatmap.png"); w, h = im.size; im.crop((0, 85, w, h)).save("/tmp/s_heat.png")
im = Image.open(f"{OUT}/06_Maps/Map_d_slide.png"); w, h = im.size; im.crop((0, 170, w, h - 40)).save("/tmp/s_map.png")
import pandas as pd
Y = pd.read_csv(f"{OUT}/01_AQI/annual_station_summary.csv").set_index("station")
C = pd.read_csv(f"{OUT}/05_GIS/buffer_metrics_vs_AQI.csv")
p = Presentation(SRC)

def set_text(shape, text):
    """Replace text keeping first run's formatting."""
    tf = shape.text_frame; para = tf.paragraphs[0]
    r0 = para.runs[0]
    for r in para.runs[1:]: r._r.getparent().remove(r._r)
    for extra in tf.paragraphs[1:]: extra._p.getparent().remove(extra._p)
    r0.text = text
def by_name(slide, name): return [s for s in slide.shapes if s.name == name][0]

# ---- slide 1 ----
s = p.slides[0]
set_text(by_name(s, "Text 7"), "12"); set_text(by_name(s, "Text 8"), "CAAQMS stations (Kolkata 7, Howrah 5)")
set_text(by_name(s, "Text 10"), "90%"); set_text(by_name(s, "Text 11"), "valid station-days, Jan–Dec 2025")
s.notes_slide.notes_text_frame.text = ("Project: hotspot mapping of air quality across Kolkata–Howrah, integrating land use/land cover and seasonal meteorology. "
    "Current stage: preliminary analysis complete for 2025 (12 stations, cleaned daily AQI, seasonal and station comparison, IMD meteorology, LULC buffer analysis). "
    "Spatial interpolation, hotspot statistics and regression are Phase II.")

# admission no. & supervisor (values from her summary doc); remove yellow highlight + stray pPr
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
tb = by_name(s, "Text 2")._element.txBody
for para in tb.findall(f"{A}p"):
    pprs = para.findall(f"{A}pPr")
    for extra in pprs[1:]: para.remove(extra)
    for r in para.findall(f"{A}r"):
        rp = r.find(f"{A}rPr"); hl = rp.find(f"{A}highlight")
        if hl is not None:
            rp.remove(hl); sf = rp.find(f"{A}solidFill"); clr = sf[0]; sf.remove(clr)
            import lxml.etree as ET; sc = ET.SubElement(sf, f"{A}schemeClr"); sc.set("val", "bg2")
            t = r.find(f"{A}t"); t.text = "23JE0294" if "Prof" not in t.text else "Prof. Manish Jain"

# ---- slide 3: mark step 5 as done (accent1 -> accent2) & update descriptions ----
s = p.slides[2]
set_text(by_name(s, "Text 11"), "75% rule, flat-line (≥24 h) & spike removal")
set_text(by_name(s, "Text 17"), "Daily, monthly, seasonal AQI; category days")
set_text(by_name(s, "Text 23"), "Rain/Tmax vs AQI done; wind & CPF in Phase II")
set_text(by_name(s, "Text 28"), "LULC, roads, buildings in 1 & 2 km buffers")
for n in ["Shape 24", "Shape 25", "Shape 13", "Shape 14"]:
    el = by_name(s, n)._element
    for c in el.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}schemeClr"):
        if c.get("val") == "accent1": c.set("val", "accent2")
set_text(by_name(s, "Text 48"), "Phase I – done (preliminary)")

# ---- slide 4: rebuild as results slide ----
s = p.slides[3]
keep = {"Text 0", "Slide Number Placeholder 0"}
tmpl = {n: copy.deepcopy(by_name(s, n)._element) for n in ["Shape 2", "Text 3", "Text 4", "Text 5"]}
for sh in list(s.shapes):
    if sh.name not in keep: sh._element.getparent().remove(sh._element)
set_text(by_name(s, "Text 0"), "Work done so far: preliminary results (2025)")
s.shapes.add_picture("/tmp/s_map.png", Inches(0.5), Inches(0.98), height=Inches(4.2))
pic = s.shapes.add_picture("/tmp/s_heat.png", Inches(4.55), Inches(0.98), width=Inches(4.95))
tree = s.shapes._spTree
EMU = 914400
def place(el, x, y, w=None, h=None):
    off = el.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}off"); ext = el.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}ext")
    off.set("x", str(int(x * EMU))); off.set("y", str(int(y * EMU)))
    if w: ext.set("cx", str(int(w * EMU)))
    if h: ext.set("cy", str(int(h * EMU)))
def settxt(el, text, size=None):
    ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    ps = el.findall(f".//{ns}p"); rs = ps[0].findall(f"{ns}r")
    rs[0].find(f"{ns}t").text = text
    for r in rs[1:]: ps[0].remove(r)
    if size: rs[0].find(f"{ns}rPr").set("sz", str(int(size * 100)))
y = Y.loc
season_ratio = 184.95 / 54.97
cards = [("3.4×", "Winter vs monsoon mean AQI (185 vs 55)", "All 12 stations"),
         ("ρ = −0.75", "Daily rainfall vs city AQI; 1,898 mm in 2025", "IMD gridded data"),
         ("138 vs 81", "Highest vs lowest station: Padmapukur vs Rabindra Sarobar", "Season-balanced mean"),
         ("ρ = −0.68", "Green cover within 1 km vs station AQI (p = 0.02)", "Esri 10 m LULC, n = 12")]
x0, cw, gap, top, ch = 4.55, 1.17, 0.09, 3.78, 1.42
for i, (big, desc, src) in enumerate(cards):
    x = x0 + i * (cw + gap)
    c = copy.deepcopy(tmpl["Shape 2"]); place(c, x, top, cw, ch); tree.append(c)
    b = copy.deepcopy(tmpl["Text 3"]); place(b, x + 0.08, top + 0.06, cw - 0.16, 0.42); settxt(b, big, 17); tree.append(b)
    d = copy.deepcopy(tmpl["Text 4"]); place(d, x + 0.08, top + 0.5, cw - 0.16, 0.62); settxt(d, desc, 9); tree.append(d)
    e = copy.deepcopy(tmpl["Text 5"]); place(e, x + 0.08, top + 1.13, cw - 0.16, 0.22); settxt(e, src, 8); tree.append(e)
# ensure unique ids
nid = 200
for el in tree.iter("{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr"):
    nid += 1; el.set("id", str(nid))
s.notes_slide.notes_text_frame.text = (
    "Data: CPCB CAAQMS hourly AQI for 12 WBPCB stations, Jan–Dec 2025. Cleaning removed missing, non-positive/>500 values, flat-lined runs (>=24 identical hours, mainly Ballygunge Jul–Oct) and isolated spikes; "
    "daily AQI kept only with >=18 valid hours (90% of station-days valid; Ballygunge and Fort William weakest). "
    "Left: annual mean AQI map — Howrah industrial stations (Padmapukur 138, Ghusuri 133) and Jadavpur (131) highest; Rabindra Sarobar (81) and Bidhannagar (88) lowest. "
    "Right: monthly AQI heatmap — 'Poor' to 'Very Poor' in Nov–Jan, 'Good/Satisfactory' in Jun–Sep. "
    "Rainfall washes out pollutants (Spearman -0.75); stations with more green cover within 1 km have lower AQI (rho -0.68), while the 2 km scale shows no clear relationship. "
    "Limitation: the downloaded files contain AQI, not pollutant concentrations, so the prominent pollutant is a Phase II task.")

# ---- slide 5: work to be done ----
s = p.slides[4]
rows = {"Text 7": "A. Pollutant-wise analysis", "Text 8": "Concentrations, AQI sub-indices, prominent pollutant, NAAQS",
        "Text 10": "B. Meteorology & CPF", "Text 11": "Wind speed/direction; wind & pollution roses; CPF (75th pct)",
        "Text 14": "C. LULC verification", "Text 15": "Google Earth check, confusion matrix, kappa; 500 m buffers",
        "Text 17": "D. Buildings & roads (complete)", "Text 18": "Google tile 39f for 4 northern stations; density metrics",
        "Text 21": "E. IDW interpolation", "Text 22": "Seasonal AQI surfaces; leave-one-out cross-validation",
        "Text 24": "F. Hotspots & regression", "Text 25": "Getis-Ord Gi*; multiple regression AQI ~ LULC, roads, met",
        "Text 31": "Expected outcome: seasonal hotspot maps, dominant source directions per station, and a regression model linking built-up density, roads and green cover to AQI."}
for k, v in rows.items(): set_text(by_name(s, k), v)
p.save(DST); print("saved", DST)
