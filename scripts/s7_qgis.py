"""Step 8: one GeoPackage with all layers pre-styled (styles saved inside the GPKG) + QGIS project with 4 ready Print Layouts.
Run with: QT_QPA_PLATFORM=offscreen /usr/bin/python3.12 s7_qgis.py <OUT> <UPLOADS>"""
import os, sys, shutil, sqlite3
OUT, UP = sys.argv[1], sys.argv[2]
G = f"{OUT}/05_GIS"; Q = f"{OUT}/07_QGIS"; os.makedirs(Q, exist_ok=True)
GPKG = f"{Q}/Kolkata_AQI_GIS_2025.gpkg"
from osgeo import gdal, ogr, osr
gdal.UseExceptions()
if os.path.exists(GPKG): os.remove(GPKG)

# ---------- 1. write layers into one GeoPackage (EPSG:32645) ----------
def vec(src, name, layer=None, where=None, t_srs="EPSG:32645"):
    if not os.path.exists(src): print("skip", name); return False
    gdal.VectorTranslate(GPKG, src, format="GPKG", accessMode="append" if os.path.exists(GPKG) else None,
                         layers=[layer] if layer else None, layerName=name, dstSRS=t_srs, where=where, geometryType="PROMOTE_TO_MULTI" if name.startswith("roads") else None)
    return True
vec(f"{OUT}/03_Stations/stations_CAAQMS_Kolkata_Howrah.gpkg", "stations_AQI_2025")
vec(f"{G}/station_buffers.gpkg", "buffer_1km", where="buffer_km = 1")
vec(f"{G}/station_buffers.gpkg", "buffer_2km", where="buffer_km = 2")
has_roads = vec(f"{G}/roads_major_study_area.gpkg", "roads_major")
has_ind = vec(f"{G}/osm_industrial_areas.gpkg", "osm_industrial")
has_bld = vec(f"{G}/buildings_GoogleOB_centroids_study_area.gpkg", "buildings_google_centroids")
# study area box + Google tile boundary
vec(f"{G}/aux_layers.gpkg", "study_area", layer="study_area")
vec(f"{G}/aux_layers.gpkg", "google_buildings_tiles", layer="google_buildings_tiles")
# rasters -> GPKG raster tables (LULC keeps its classes as Byte)
def ras(src, name, rtype="Byte"):
    if not os.path.exists(src): print("skip", name); return False
    gdal.Warp(f"/tmp/{name}.tif", src, dstSRS="EPSG:32645", resampleAlg="near")
    gdal.Translate(GPKG, f"/tmp/{name}.tif", format="GPKG", outputType=getattr(gdal, "GDT_" + rtype),
                   creationOptions=[f"RASTER_TABLE={name}", "APPEND_SUBDATASET=YES", "TILE_FORMAT=PNG" if rtype == "Byte" else "TILE_FORMAT=TIFF"])
    return True
ras(f"{G}/LULC_Esri_2025_study_area_10m.tif", "lulc_esri_2025")
has_bd = ras(f"{G}/building_density_250m.tif", "building_cover_250m", "Float32")
gdal.Translate("/tmp/rain.tif", f"{OUT}/04_IMD/IMD_rainfall_annual_total_2025.tif", projWin=[86.5, 24.0, 90.0, 21.0])
ras("/tmp/rain.tif", "imd_rainfall_2025_total_mm", "Float32")

# ---------- 2. style layers with QGIS, save styles into the GPKG, build project + layouts ----------
from qgis.core import *
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtCore import QSizeF, QPointF, Qt
app = QgsApplication([], False); app.initQgis()
proj = QgsProject.instance(); proj.setCrs(QgsCoordinateReferenceSystem("EPSG:32645"))
proj.setFileName(f"{Q}/Kolkata_AQI_maps_2025.qgz")
def V(name):
    l = QgsVectorLayer(f"{GPKG}|layername={name}", name, "ogr"); assert l.isValid(), name; return l
def R(name):
    l = QgsRasterLayer(f"GPKG:{GPKG}:{name}", name, "gdal"); assert l.isValid(), name; return l

CLS = [(1,"Water","#419bdf"),(2,"Trees","#397d49"),(4,"Flooded vegetation","#7a87c6"),(5,"Crops","#e49635"),
       (7,"Built area","#c4281b"),(8,"Bare ground","#a59b8f"),(11,"Rangeland","#e3e2c3")]
lulc = R("lulc_esri_2025"); lulc.setName("LULC 2025 (Esri 10 m)")
cl = [QgsPalettedRasterRenderer.Class(v, QColor(c), n) for v, n, c in CLS]
lulc.setRenderer(QgsPalettedRasterRenderer(lulc.dataProvider(), 1, cl))
water = R("lulc_esri_2025"); water.setName("Water (from LULC)")
wcl = [QgsPalettedRasterRenderer.Class(1, QColor("#9cc8ec"), "Water")]
water.setRenderer(QgsPalettedRasterRenderer(water.dataProvider(), 1, wcl))

def single_marker(layer, color, size=3.2, shape="circle"):
    sym = QgsMarkerSymbol.createSimple({"name": shape, "color": color, "outline_color": "#0b0b0b", "outline_width": "0.35", "size": str(size)})
    return sym
st = V("stations_AQI_2025"); st.setName("CAAQMS stations")
cat = QgsCategorizedSymbolRenderer("city", [QgsRendererCategory("Kolkata", single_marker(st, "#1c5cab"), "Kolkata station (7)"),
                                            QgsRendererCategory("Howrah", single_marker(st, "#7b2cbf", 3.6, "triangle"), "Howrah station (5)")])
st.setRenderer(cat)
def labels(layer, expr="\"station\"", size=8):
    s = QgsPalLayerSettings(); s.fieldName = expr; s.isExpression = True
    tf = QgsTextFormat(); tf.setFont(QFont("Arial")); tf.setSize(size); tf.setColor(QColor("#0b0b0b"))
    b = QgsTextBufferSettings(); b.setEnabled(True); b.setSize(1.0); b.setColor(QColor("white")); tf.setBuffer(b)
    s.setFormat(tf); s.placement = QgsPalLayerSettings.OrderedPositionsAroundPoint; s.dist = 1.2
    layer.setLabeling(QgsVectorLayerSimpleLabeling(s)); layer.setLabelsEnabled(True)
labels(st)
# AQI graduated stations
aq = V("stations_AQI_2025"); aq.setName("Annual mean AQI 2025")
rng = []
for lo, hi, col, lab, sz in [(0, 95, "#fee391", "< 95 (Satisfactory)", 3.5), (95, 110, "#fec44f", "95–110", 4.8), (110, 125, "#fe9929", "110–125", 6.0),
                             (125, 140, "#d95f0e", "125–140", 7.2), (140, 400, "#993404", "> 140", 8.4)]:
    sym = QgsMarkerSymbol.createSimple({"name": "circle", "color": col, "outline_color": "#0b0b0b", "outline_width": "0.35", "size": str(sz)})
    rng.append(QgsRendererRange(lo, hi, sym, lab))
aq.setRenderer(QgsGraduatedSymbolRenderer("annual_mean_season_balanced", rng))
labels(aq, "\"station\" || '\\n' || round(\"annual_mean_season_balanced\") || ' (W ' || round(\"Winter\") || ' / M ' || round(\"Monsoon\") || ')'", 7.5)
b1 = V("buffer_1km"); b1.setName("1 km buffer"); b1.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": "#0b0b0b", "outline_width": "0.3"})))
b2 = V("buffer_2km"); b2.setName("2 km buffer"); b2.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": "#52514e", "outline_width": "0.3", "outline_style": "dash"})))
sa = V("study_area"); sa.setName("Study area"); sa.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": "#c4281b", "outline_width": "0.6"})))
tl = V("google_buildings_tiles"); tl.setName("Google Open Buildings tiles"); tl.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": "#6250d6", "outline_width": "0.5", "outline_style": "dot"})))
labels(tl, "'Google tile ' || \"tile_id\"", 8)
rain = R("imd_rainfall_2025_total_mm"); rain.setName("IMD rainfall 2025 (mm)")
shader = QgsRasterShader(); fn = QgsColorRampShader(); fn.setColorRampType(QgsColorRampShader.Interpolated)
fn.setColorRampItemList([QgsColorRampShader.ColorRampItem(v, QColor(c), str(v)) for v, c in [(1200, "#cde2fb"), (1600, "#6da7ec"), (2000, "#2a78d6"), (2600, "#0d366b")]])
shader.setRasterShaderFunction(fn); rr = QgsSingleBandPseudoColorRenderer(rain.dataProvider(), 1, shader); rain.setRenderer(rr); rain.setOpacity(0.8)
layers = [rain, lulc, water, sa, tl, b2, b1, st, aq]
idl = V("osm_industrial"); idl.setName("Industrial land (OSM)")
idl.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "107,63,160,210", "outline_color": "#3d1f66", "outline_width": "0.2"})))
layers.insert(4, idl)
RS = {"motorway": ("#c4281b", 1.1), "trunk": ("#eb6834", 0.9), "primary": ("#eda100", 0.7), "secondary": ("#2a78d6", 0.45), "tertiary": ("#1baf7a", 0.3)}
if has_roads:
    rd = V("roads_major"); rd.setName("Major roads (OSM)")
    cats = []
    for k, (c, w) in RS.items():
        cats.append(QgsRendererCategory(k, QgsLineSymbol.createSimple({"color": c, "width": str(w)}), k.capitalize()))
    r_ = QgsCategorizedSymbolRenderer("replace(\"fclass\", '_link', '')", cats); rd.setRenderer(r_); layers.insert(5, rd)
if has_bd:
    bd = R("building_cover_250m"); bd.setName("Building cover % (Google, 250 m)")
    sh = QgsRasterShader(); f2 = QgsColorRampShader(); f2.setColorRampType(QgsColorRampShader.Discrete)
    f2.setColorRampItemList([QgsColorRampShader.ColorRampItem(v, QColor(c), l) for v, c, l in
        [(5, "#f3f2ee", "< 5%"), (15, "#e4e3df", "5–15%"), (25, "#c3c2b7", "15–25%"), (35, "#a3a29b", "25–35%"), (45, "#7d7c76", "35–45%"), (100, "#52514e", "> 45%")]])
    sh.setRasterShaderFunction(f2); bd.setRenderer(QgsSingleBandPseudoColorRenderer(bd.dataProvider(), 1, sh)); layers.insert(3, bd)
for l in layers:
    proj.addMapLayer(l)
    try:
        if isinstance(l, QgsVectorLayer): l.saveStyleToDatabase(l.name(), "Pre-styled for B.Tech project", True, "")
    except Exception as e: print("style", l.name(), e)
    l.saveNamedStyle(f"{Q}/styles_{l.name().split(' (')[0].replace(' ', '_').replace('%','pct')}.qml")
root = proj.layerTreeRoot()
for l in layers: root.findLayer(l.id()).setItemVisibilityChecked(False)

# ---------- 3. print layouts ----------
ext = sa.extent(); ext.grow(300)
def layout(name, title, sub, vis, legend_layers, source, legend_title="Legend"):
    lay = QgsPrintLayout(proj); lay.initializeDefaults(); lay.setName(name)
    pg = lay.pageCollection().page(0); pg.setPageSize("A4", QgsLayoutItemPage.Portrait)
    m = QgsLayoutItemMap(lay); m.attemptMove(QgsLayoutPoint(10, 28, QgsUnitTypes.LayoutMillimeters)); m.attemptResize(QgsLayoutSize(190, 205, QgsUnitTypes.LayoutMillimeters))
    m.setLayers(vis); m.setCrs(proj.crs()); m.setExtent(ext); m.setFrameEnabled(True); lay.addLayoutItem(m)
    m.grid().setEnabled(True); g = m.grid(); g.setCrs(QgsCoordinateReferenceSystem("EPSG:4326")); g.setIntervalX(0.05); g.setIntervalY(0.05)
    g.setStyle(QgsLayoutItemMapGrid.FrameAnnotationsOnly); g.setAnnotationEnabled(True); g.setAnnotationFormat(QgsLayoutItemMapGrid.DegreeMinuteNoSuffix)
    g.setFrameStyle(QgsLayoutItemMapGrid.InteriorTicks); g.setAnnotationPrecision(2); g.setAnnotationFormat(QgsLayoutItemMapGrid.Decimal)
    g.setAnnotationDisplay(QgsLayoutItemMapGrid.HideAll, QgsLayoutItemMapGrid.Right); g.setAnnotationDisplay(QgsLayoutItemMapGrid.HideAll, QgsLayoutItemMapGrid.Top)
    tf = QgsTextFormat(); tf.setFont(QFont("Arial")); tf.setSize(7); g.setAnnotationTextFormat(tf)
    def txt(s, x, y, w, h, size, bold=False, color="#0b0b0b"):
        t = QgsLayoutItemLabel(lay); t.setText(s); f = QgsTextFormat(); ft = QFont("Arial"); ft.setBold(bold); f.setFont(ft); f.setSize(size); f.setColor(QColor(color))
        t.setTextFormat(f); t.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters)); t.attemptResize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters)); lay.addLayoutItem(t)
    txt(title, 10, 8, 190, 10, 15, True); txt(sub, 10, 18, 190, 8, 9, False, "#52514e")
    lg = QgsLayoutItemLegend(lay); lg.setTitle(legend_title); lg.setLinkedMap(m); lg.setAutoUpdateModel(False)
    lg.model().rootGroup().clear()
    for l in legend_layers:
        nl = lg.model().rootGroup().addLayer(l)
        if isinstance(l, QgsRasterLayer):
            n_ = len(lg.model().layerLegendNodes(nl))
            QgsMapLayerLegendUtils.setLegendNodeOrder(nl, list(range(1, n_)))
            lg.model().refreshLayerLegend(nl)
        if len(legend_layers) == 1 or l.name().startswith("Water") or isinstance(l, QgsRasterLayer) and "Building" not in l.name():
            QgsLegendRenderer.setNodeLegendStyle(nl, QgsLegendStyle.Hidden)
    lg.attemptMove(QgsLayoutPoint(10, 240, QgsUnitTypes.LayoutMillimeters)); lg.setColumnCount(3); lg.setSplitLayer(True)
    lg.setStyleFont(QgsLegendStyle.SymbolLabel, QFont("Arial", 8)); lay.addLayoutItem(lg)
    sb = QgsLayoutItemScaleBar(lay); sb.setStyle("Single Box"); sb.setLinkedMap(m); sb.setUnits(QgsUnitTypes.DistanceKilometers)
    sb.setNumberOfSegments(4); sb.setNumberOfSegmentsLeft(0); sb.setUnitsPerSegment(1); sb.setUnitLabel("km")
    sb.setHeight(2); stf = QgsTextFormat(); stf.setFont(QFont("Arial")); stf.setSize(8); sb.setTextFormat(stf)
    sb.attemptMove(QgsLayoutPoint(150, 236, QgsUnitTypes.LayoutMillimeters)); lay.addLayoutItem(sb)
    na = QgsLayoutItemPicture(lay); na.setPicturePath(QgsApplication.svgPaths()[0] + "arrows/NorthArrow_02.svg" if os.path.exists(QgsApplication.svgPaths()[0] + "arrows/NorthArrow_02.svg") else "")
    na.attemptMove(QgsLayoutPoint(185, 31, QgsUnitTypes.LayoutMillimeters)); na.attemptResize(QgsLayoutSize(11, 14, QgsUnitTypes.LayoutMillimeters)); lay.addLayoutItem(na)
    txt(source, 10, 283, 190, 8, 7, False, "#52514e")
    proj.layoutManager().addLayout(lay); return lay
src = "Data: CPCB/WBPCB CAAQMS hourly AQI 2025; Esri/Impact Observatory Sentinel-2 LULC 2025; OSM (ODbL); Google Open Buildings v3. CRS: WGS 84 / UTM 45N."
L1 = layout("(a) Study area", "(a) Study area: Kolkata–Howrah CAAQMS stations", "12 WBPCB continuous monitoring stations with 2 km buffers",
            [st, b2, sa, water] + ([rd] if has_roads else []), [st, b2, water], src)
L2 = layout("(b) LULC", "(b) Land use / land cover 2025 with stations", "Esri / Impact Observatory Sentinel-2 10 m LULC; 1 km buffers",
            [st, b1, lulc], [lulc, st, b1], src)
L3 = layout("(c) Roads and buildings", "(c) Major roads and industrial land", "OSM major roads and industrial land use; Google Open Buildings tiles shown",
            [st, tl, idl] + ([rd] if has_roads else []) + ([bd] if has_bd else []) + [water], [st, idl] + ([rd] if has_roads else []) + ([bd] if has_bd else []) + [tl], src)
lf = R("lulc_esri_2025"); lf.setName("LULC 2025 (faint background)")
lf.setRenderer(QgsPalettedRasterRenderer(lf.dataProvider(), 1, [QgsPalettedRasterRenderer.Class(v, QColor(c), n) for v, n, c in CLS])); lf.setOpacity(0.25)
proj.addMapLayer(lf); root_ = proj.layerTreeRoot(); root_.findLayer(lf.id()).setItemVisibilityChecked(False); lf.saveNamedStyle(f"{Q}/styles_LULC_faint.qml")
L4 = layout("(d) AQI", "(d) Annual mean AQI with industrial land and major roads, 2025", "Symbol size/colour = season-balanced annual mean AQI; label = annual (Winter / Monsoon)",
            [aq, idl] + ([rd] if has_roads else []) + [lf], [aq, idl] + ([rd] if has_roads else []), src, "")
lulc_faint = None
proj.write()
# export layouts to PNG to check
for lay in proj.layoutManager().layouts():
    ex = QgsLayoutExporter(lay); s = QgsLayoutExporter.ImageExportSettings(); s.dpi = 150
    r = ex.exportToImage(f"{Q}/layout_preview_{lay.name()[:3].strip('()')}.png", s); print(lay.name(), r)
app.exitQgis()
