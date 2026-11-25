OUTPUTS - Kolkata-Howrah AQI hotspot project (Deeksha Dey), preliminary analysis, Jan-Dec 2025
=========================================================================================
01_AQI        AQI_Kolkata_Howrah_2025.xlsx  -> README, Data_Availability, Daily (long + wide), Monthly, Seasonal, Annual summary
              hourly_AQI_cleaned_all_stations.csv (every hour with cleaning flag)
02_Graphs     01-12 one graph per station (daily AQI + category bands + monthly mean)
              13 all-station panel, 14 station x month heatmap, 15 seasonal bars, 16-17 seasonal box plots
              18-19 AQI vs rainfall/Tmax, 20-21 correlation tables (1 km / 2 km), 22 AQI vs buffer metrics
03_Stations   station coordinates (CSV + GeoPackage), verified against CPCB station codes
04_IMD        rainfall (.nc) and Tmax (.GRD) converted to GeoTIFF (daily multiband + annual/seasonal);
              Kolkata 365-day rainfall/Tmax/AQI table + correlations (Excel)
05_GIS        clipped LULC (10 m GeoTIFF with colours), 1 & 2 km buffers, buffer statistics + correlations (Excel)
06_Maps       finished maps: (a) study area, (b) LULC, (d) annual AQI,
              (e) GIS findings: AQI + LULC + OSM industrial land + roads  [Map_e_AQI_LULC_industry.png]
              (f) 2 km zooms of the 3 most vs 3 least polluted stations  [Map_f_high_vs_low_AQI_station_zooms.png]
              02_Graphs/23_station_landuse_fingerprint.png = AQI vs land cover/industry/roads per station
07_QGIS       Kolkata_AQI_GIS_2025.gpkg (all layers, vector styles saved inside) + Kolkata_AQI_maps_2025.qgz
              HOW TO EXPORT A MAP: double-click the .qgz -> Project > Layouts -> pick (a)/(b)/(c)/(d)
              -> Layout > Export as Image / PDF.  Keep the .qgz and .gpkg in the same folder.
              styles_*.qml = same styles as files (Layer Properties > Style > Load Style) if ever needed.
08_Report     *_GIS.pptx / *_GIS.docx = latest versions with GIS findings (slide 4 + appendix slide 7; Fig. 1 in summary)
scripts       Python scripts that produced everything (re-runnable)
_extract      extract_on_my_pc.py - run once in QGIS Python console to cut roads/buildings to the study area

Notes: CPCB files contain hourly AQI (not concentrations) - prominent pollutant is Phase II.
Google Open Buildings tile 3a1 fully covers 8 of 12 station buffers (Ghusuri, Belur Math, Rabindra Bharati Univ.,
most of Dasnagar are in tile 39f).
