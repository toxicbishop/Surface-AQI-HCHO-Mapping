"""Data ingestion.

Server-side (Google Earth Engine):
    sentinel5p   NO2, SO2, CO, O3, HCHO   (COPERNICUS/S5P/OFFL/L3_*)
    era5         meteorology              (ECMWF/ERA5_LAND/DAILY_AGGR)
    modis_fire   active fire / burned area / EVI
    viirs_fire   active fire (FIRMS + 375 m VNP14 via API)
    worldcover   ESA WorldCover land cover
    srtm         elevation + slope/aspect

Local / external:
    insat_aod    INSAT-3D AOD via ISRO MOSDAC
    cpcb         CPCB ground-station observations (targets / ground truth)
"""
