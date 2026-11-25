"""Make slide 4 the GIS-findings slide (map e + land-use fingerprint) and add an appendix slide with station zooms."""
import copy, sys
from PIL import Image, ImageChops
from pptx import Presentation
from pptx.util import Inches, Pt
SRC, OUT, DST = sys.argv[1], sys.argv[2], sys.argv[3]
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
TMP = "/tmp/claude-0/-home-claude/513ca190-e76b-5be9-b48b-c9a4ad698c82/scratchpad"
def autocrop(src, dst, extra=(0, 0, 0, 0)):
    im = Image.open(src).convert("RGB"); bg = Image.new("RGB", im.size, (255, 255, 255))
    l, t, r, b = ImageChops.difference(im, bg).getbbox()
    im.crop((l + extra[0], t + extra[1], r - extra[2], b - extra[3])).save(dst); return Image.open(dst).size
autocrop(f"{OUT}/06_Maps/Map_e_slide.png", f"{TMP}/s_mape.png")
im = Image.open(f"{OUT}/02_Graphs/23_station_landuse_fingerprint.png"); w, h = im.size
im.crop((0, 70, w, h - 45)).save(f"{TMP}/s_fp.png")
im = Image.open(f"{OUT}/06_Maps/Map_f_high_vs_low_AQI_station_zooms.png"); w, h = im.size
im.crop((0, 95, w, h)).save(f"{TMP}/s_zoom.png")

p = Presentation(SRC)
s = p.slides[3]
def by_name(sl, n): return [x for x in sl.shapes if x.name == n]
for pic in [x for x in s.shapes if x.shape_type == 13]: pic._element.getparent().remove(pic._element)
t = by_name(s, "Text 0")[0]; t.text_frame.paragraphs[0].runs[0].text = "GIS findings: why AQI differs between stations"
mp = s.shapes.add_picture(f"{TMP}/s_mape.png", Inches(0.5), Inches(0.98), width=Inches(3.92))
fp = s.shapes.add_picture(f"{TMP}/s_fp.png", Inches(4.55), Inches(0.98), width=Inches(4.95))
for pic in (mp, fp):                                    # put pictures behind cards
    el = pic._element; tree = el.getparent(); tree.remove(el); tree.insert(3, el)
mp.name = "GIS findings map"; fp.name = "Land-use fingerprint chart"
mp._element.nvPicPr.cNvPr.set("descr", "Map of 12 stations coloured by annual AQI over LULC with OSM industrial areas and major roads")
fp._element.nvPicPr.cNvPr.set("descr", "Chart: AQI, 1 km land cover, industrial share and road density for each station, sorted by AQI")
def set_run(shape, text):
    r = shape.text_frame.paragraphs[0].runs[0]; r.text = text
cards = [("0%", "Green cover within 1 km of the 3 worst stations", "Esri 10 m LULC"),
         ("ρ = −0.68", "More green within 1 km → lower AQI (p = 0.02)", "Spearman, n = 12"),
         ("30%", "Ghusuri: industrial estate fills 30% of 1 km buffer, 40 m away", "OSM industrial land"),
         ("3.4×", "Winter vs monsoon AQI; rain washes out (ρ = −0.75)", "IMD rainfall")]
big = by_name(s, "Text 3"); desc = by_name(s, "Text 4"); src = by_name(s, "Text 5")
for i, (b, d, c) in enumerate(cards):
    set_run(big[i], b); set_run(desc[i], d); set_run(src[i], c)
# fit fingerprint above cards
fp_h = fp.height / 914400
for n in ["Shape 2", "Text 3", "Text 4", "Text 5"]:
    for sh in by_name(s, n): sh.top = int(sh.top + max(0, (0.98 + fp_h + 0.12) - 3.78) * 914400)
s.notes_slide.notes_text_frame.text = (
    "Left map: stations coloured and sized by 2025 annual mean AQI, over Esri 10 m LULC (red = built area, green = trees, blue = water) with OSM industrial land (purple), major roads and railways. "
    "Right: land-use fingerprint of each station within 1 km, sorted by AQI. "
    "The three most polluted stations, Padmapukur (138), Ghusuri (133) and Jadavpur (131), are 100% built-up with 0% green cover within 1 km. "
    "Ghusuri sits 40 m from an industrial estate on the Hooghly mill belt (30% of its 1 km buffer is industrial land); Padmapukur is in Howrah's dense urban-industrial fabric; "
    "Jadavpur has the densest road grid of all stations (30 km of roads per km2), pointing to traffic. "
    "The cleanest stations have green or water nearby: Rabindra Sarobar (81) has a lake and parks; Bidhannagar (88) is a planned township with wide roads and parks. "
    "Across 12 stations, green cover within 1 km is negatively correlated with AQI (Spearman -0.68, p = 0.02), and the link is weaker at 2 km, so local sources matter most. "
    "Exceptions to discuss: Victoria (126) has 30% green but sits beside the central traffic hub; Rabindra Bharati University (102) is 96% built-up but on the northern edge. "
    "OSM does not map small industrial units, so industrial share is not significant statistically - Phase II will use regression with wind direction (CPF) to separate source types. "
    "Seasonality: winter AQI is 3.4 times the monsoon value and daily rain is strongly linked to lower AQI (rho -0.75).")

# ---- appendix slide (slide 7) ----
lay = s.slide_layout
ns = p.slides.add_slide(lay)
ttl = ns.placeholders[100]
ttl.text_frame.text = "Appendix: land use at high vs low AQI stations"
sn = copy.deepcopy(by_name(s, "Slide Number Placeholder 0")[0]._element); ns.shapes._spTree.append(sn)
zoom = ns.shapes.add_picture(f"{TMP}/s_zoom.png", Inches(0.5), Inches(0.98), height=Inches(4.25))
zoom._element.nvPicPr.cNvPr.set("descr", "Six 2 km zoom maps: LULC, OSM industry and roads around the 3 most and 3 least polluted stations")
x0 = 0.5 + zoom.width / 914400 + 0.2
card = copy.deepcopy(by_name(s, "Shape 2")[0]._element); ns.shapes._spTree.append(card)
c = [x for x in ns.shapes if x._element is card][0]; c.left, c.top, c.width, c.height = Inches(x0), Inches(0.98), Inches(9.5 - x0), Inches(4.25)
tx = copy.deepcopy(by_name(s, "Text 4")[0]._element); ns.shapes._spTree.append(tx)
tb = [x for x in ns.shapes if x._element is tx][0]; tb.left, tb.top, tb.width, tb.height = Inches(x0 + 0.1), Inches(1.05), Inches(9.5 - x0 - 0.2), Inches(4.1)
pts = [("High AQI", None), ("Padmapukur: dense Howrah urban–industrial area, no green within 1 km.", 0),
       ("Ghusuri: industrial estate 40 m away; riverside mill belt.", 0), ("Jadavpur: busiest road grid; traffic-dominated.", 0),
       ("Low AQI", None), ("Rabindra Sarobar: lake + parks (23% green, 8% water).", 0),
       ("Bidhannagar: planned township, wide roads, 12% parks.", 0), ("Rabindra Bharati Univ.: built-up but on the northern edge (exception).", 0)]
tf = tb.text_frame; first = tf.paragraphs[0]
for i, (txt, lvl) in enumerate(pts):
    para = first if i == 0 else tf.add_paragraph()
    if i > 0: para._p.insert(0, copy.deepcopy(first._p.find(f"{A}pPr"))) if first._p.find(f"{A}pPr") is not None else None
    r = para.runs[0] if para.runs else para.add_run(); r.text = txt
    r.font.size = Pt(10.5 if lvl is None else 9.5); r.font.bold = lvl is None
    para.space_before = Pt(6 if lvl is None and i > 0 else 2)
ns.notes_slide.notes_text_frame.text = "Optional backup slide. Each panel is a 2 km window around a station: LULC 2025 colours, OSM industrial land (hatched), major roads and railways, 1 km and 2 km buffers. Delete this slide if the 6-slide limit is strict."
p.save(DST); print("saved", len(p.slides))
