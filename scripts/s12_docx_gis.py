"""Add GIS findings (LULC/industry/roads vs AQI) + figure to the 2-page summary."""
import copy, sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
SRC, OUT, DST = sys.argv[1], sys.argv[2], sys.argv[3]
TMP = "/tmp/claude-0/-home-claude/513ca190-e76b-5be9-b48b-c9a4ad698c82/scratchpad"
d = Document(SRC); P = d.paragraphs
def setp(p, parts):
    runs = p.runs; base = runs[0]
    for r in runs[1:]: r._r.getparent().remove(r._r)
    base.text = parts[0][0]; base.bold = parts[0][1]; last = base._r
    from docx.text.run import Run
    for t, b in parts[1:]:
        nr = copy.deepcopy(base._r); last.addnext(nr); last = nr; R = Run(nr, p); R.text = t; R.bold = b
def find(prefix): return [p for p in d.paragraphs if p.text.startswith(prefix)][0]

setp(find("Seasonality: Winter PM10"), [("Seasonality:", True), (" Winter PM10 at Kolkata residential and industrial sites was 1.6–2.3× the monsoon level (Karar & Gupta, 2006); intra-city winter PM2.5 ranged 54–80 µg/m³ (CSE, 2025).", False)])
ic = find("Intra-city variability"); ic._p.getparent().remove(ic._p)
lu = find("Land use: Within 1 km")
setp(lu, [("GIS findings – why AQI differs:", True),
          (" Howrah stations averaged AQI 116 vs 102 in Kolkata. The three most polluted stations (Padmapukur 138, Ghusuri 133, Jadavpur 131) are 100% built-up with 0% green cover within 1 km. "
           "Ghusuri lies 40 m from an OSM-mapped industrial estate on the Hooghly mill belt (30% of its 1 km buffer), Padmapukur sits in Howrah's dense urban–industrial fabric, "
           "and Jadavpur has the densest road grid (30 km/km²), pointing to traffic. The cleanest stations have green/blue space: Rabindra Sarobar (81; lake and parks, 23% green) and "
           "Bidhannagar (88; planned township with parks). Green cover within 1 km is negatively correlated with AQI (Spearman ρ = −0.68, p = 0.02, n = 12); the link weakens at 2 km, "
           "so local sources dominate.", False)])
# figure: borderless 1x2 table
tbl = d.add_table(rows=1, cols=2); tbl.autofit = False
tblPr = tbl._tbl.tblPr; borders = OxmlElement("w:tblBorders")
for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
    b = OxmlElement(f"w:{e}"); b.set(qn("w:val"), "nil"); borders.append(b)
tblPr.append(borders)
from PIL import Image
im = Image.open(f"{TMP}/s_fp.png"); w, h = im.size; im.crop((0, 0, int(w * 0.735), h)).save(f"{TMP}/s_fp_doc.png")
for cell, path, wd in [(tbl.cell(0, 0), f"{TMP}/s_mape.png", 1.55), (tbl.cell(0, 1), f"{TMP}/s_fp_doc.png", 3.1)]:
    cell.width = Inches(wd + 0.05); pp = cell.paragraphs[0]; pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pp.paragraph_format.space_after = Pt(0); pp.add_run().add_picture(path, width=Inches(wd))
lu._p.addnext(tbl._tbl)
cap = copy.deepcopy(lu._p); tbl._tbl.addnext(cap)
from docx.text.paragraph import Paragraph
cp = Paragraph(cap, lu._parent)
for r in cp.runs[1:]: r._r.getparent().remove(r._r)
cp.runs[0].text = "Fig. 1. Left: annual mean AQI at stations over 2025 LULC with OSM industrial land (purple) and major roads. Right: AQI and land cover within 1 km of each station, sorted by AQI."
cp.runs[0].bold = False; cp.runs[0].italic = True; cp.runs[0].font.size = Pt(8)
pPr = cap.find(qn("w:pPr"))
if pPr is not None:
    for n in pPr.findall(qn("w:numPr")): pPr.remove(n)
    ind = pPr.find(qn("w:ind"))
    if ind is not None: pPr.remove(ind)
sp = find("Spatial differences"); sp._p.getparent().remove(sp._p)
setp(find("Limitations"), [("Limitations:", True), (" Files contain AQI, not concentrations (prominent pollutant in Phase II); Google buildings tile 3a1 covers 8 of 12 buffers; OSM under-maps small industrial units.", False)])
# table of data + phase II row
t = d.tables[0]
c = t.rows[3].cells[4].paragraphs[0]; setp(c, [("Roads, industry done; buildings in progress", None)])
setp(find("D. Roads and buildings"), [("D. Buildings:", True), (" Google Open Buildings incl. tile 39f (count, footprint cover, confidence ≥ 0.70) for all 12 stations; add OSM industrial-unit verification on Google Earth.", False)])
setp(find("4.5 Preliminary results"), [("4.5 Preliminary results", True), (" (Excel tables, graphs, GeoPackage and maps prepared):", False)])
setp(find("B. Meteorology and source direction"), [("B. Meteorology and CPF:", True), (" CAAQMS wind data; wind/pollution roses; CPF at the 75th percentile (Ashbaugh et al., 1985).", False)])
setp(find("C. LULC verification"), [("C. LULC verification:", True), (" Google Earth reference points; confusion matrix and kappa; 500 m buffers.", False)])
setp(find("E. Spatial interpolation"), [("E. Spatial interpolation:", True), (" IDW of seasonal AQI with leave-one-out cross-validation.", False)])
setp(find("Expected outcomes"), [("Expected outcomes:", True), (" Seasonal hotspot maps, dominant source directions per station, and quantified links between built-up density, green cover, industry and AQI.", False)])
d.save(DST); print("saved")
