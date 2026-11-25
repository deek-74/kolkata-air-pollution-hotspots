Air Pollution Hotspot Mapping – Kolkata Urban Agglomeration

Integrating LULC data and seasonal dynamics to map spatiotemporal AQI hotspots in Kolkata & Howrah (Jan–Dec 2025)

B.Tech Project · IIT (ISM) Dhanbad · Deeksha Dey Status: Phase I (data processing, AQI & GIS analysis) complete; Phase II (modelling) in progress.

About

This project analyses hourly AQI from 12 CPCB monitoring stations across Kolkata and Howrah. It finds where and when pollution hotspots occur, and relates them to land use, industry, road networks and meteorology (rainfall, temperature).

Data
CPCB: hourly AQI for 12 stations, 2025
IMD: gridded rainfall and maximum temperature
LULC: 10 m land use / land cover raster
OpenStreetMap: roads and industrial areas
Google Open Buildings: building footprints
Method
Cleaned and quality-flagged hourly AQI, then aggregated it to daily, monthly, seasonal and annual values with CPCB AQI categories
Converted IMD grids to GeoTIFF and correlated rainfall and Tmax with AQI
Computed land-use, road, industry and building metrics within 1 km and 2 km buffers around each station
Correlated AQI with the buffer metrics and mapped the results in QGIS
Structure
Folder	Contents
01_AQI	Cleaned hourly AQI + temporal summaries
02_Graphs	Station trends, heatmaps, seasonal plots, correlations
03_Stations	Station coordinates (CSV, GeoPackage)
04_IMD	Rainfall & temperature rasters + correlations
05_GIS	LULC raster, buffers, buffer statistics
06_Maps	Study area, LULC, AQI and hotspot maps
07_QGIS	QGIS project + GeoPackage + styles
08_Report	Report and presentation
scripts	Python scripts to reproduce the pipeline

Tools: Python (pandas, GeoPandas, rasterio, xarray, Matplotlib), QGIS

Future Scope
Pollutant-level analysis (PM2.5, PM10, NO₂) instead of composite AQI
Land Use Regression model and spatial interpolation (kriging) for city-wide pollution surfaces
Statistical hotspot detection (Getis-Ord Gi*)
Integration of satellite data (Sentinel-5P NO₂, AOD) and wind/transport analysis
Multi-year trend analysis and policy recommendations under NCAP
