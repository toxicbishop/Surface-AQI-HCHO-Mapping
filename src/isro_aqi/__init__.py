"""isro_aqi -- Satellite-derived surface AQI and HCHO hotspot detection over India.

Top-level package. Sub-packages:
    ingestion       data download (GEE / MOSDAC / CPCB)
    preprocessing   regridding, QA filtering, temporal aggregation, collocation
    database        unified record schema + builder
    features        feature engineering
    models          RF / XGBoost / CNN / LSTM / CNN-LSTM + training
    aqi             CPCB AQI (max) + RAPI entropy engine
    hcho            PHV / Getis-Ord Gi* / attribution / transport
    viz             maps + publication figures
    utils           config-agnostic geo / io / logging helpers
"""

__version__ = "0.1.0"
