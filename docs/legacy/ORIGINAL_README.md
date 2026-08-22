# Surface AQI & HCHO Hotspot Detection over India

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![Scikit--learn](https://img.shields.io/badge/Scikit--learn-F7931E?logo=scikitlearn&logoColor=white)
![Google Earth Engine](https://img.shields.io/badge/Google_Earth_Engine-4285F4?logo=googleearth&logoColor=white)
![Sentinel--5P](https://img.shields.io/badge/Sentinel--5P-Copernicus-0072CE)
![Random Forest](https://img.shields.io/badge/Model-Random_Forest-brightgreen)
![K--Means](https://img.shields.io/badge/Model-K--Means-orange)
![Isolation Forest](https://img.shields.io/badge/Model-Isolation_Forest-yellow)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Folium](https://img.shields.io/badge/Folium-Geospatial-informational)
![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)
![GeoPandas](https://img.shields.io/badge/GeoPandas-139C5A?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

An AI/ML-driven framework for producing a high-resolution surface Air Quality Index and identifying Formaldehyde (HCHO) hotspots across India, built on freely available Sentinel-5P satellite data and CPCB ground station observations.

## Overview

India's ground-based AQI monitoring network is sparse and urban-biased, leaving large rural, industrial, and agricultural regions unmonitored. Toxic pollutants like HCHO — emitted from industry, biomass burning, and vehicles — currently lack a systematic national-level detection framework.

This project combines Sentinel-5P satellite columns (HCHO, NO2, CO) with CPCB ground readings to:

- Predict continuous surface AQI across India using Random Forest Regression
- Segment the country into pollution severity zones using K-Means Clustering
- Flag anomalous HCHO hotspot regions using Isolation Forest
- Present all of the above on an interactive Streamlit dashboard

## Architecture

```
Sentinel-5P (GEE) ─┐
                    ├─▶ Merge & Feature Engineering ─▶ ML Models ─▶ Streamlit Dashboard
CPCB Ground Data ──┘
```

## Tech Stack

| Category | Tools |
|---|---|
| Satellite Data | Sentinel-5P (Copernicus), Google Earth Engine |
| Ground Data | CPCB Open Data Portal |
| Language | Python |
| Data Processing | Pandas, NumPy, GeoPandas, Rasterio |
| ML Models | Scikit-learn (Random Forest, K-Means, Isolation Forest) |
| Visualization | Folium, Plotly, Matplotlib |
| Dashboard | Streamlit |
| Development | Jupyter Notebook, Google Colab |

## Features

- High-resolution surface AQI map of India
- HCHO hotspot identification across industrial, agricultural, and urban corridors
- Pollution zone classification (Good / Moderate / Poor / Severe)
- Time-series trend charts for seasonal pollution patterns
- Interactive Streamlit dashboard for public and policy use

## Repository Structure

```
aqi-hcho-satellite-india/
├── data/
│   ├── raw/
│   └── processed/
├── notebooks/
│   ├── 01_data_acquisition.ipynb
│   ├── 02_preprocessing_merge.ipynb
│   ├── 03_rf_aqi_model.ipynb
│   ├── 04_kmeans_zones.ipynb
│   └── 05_isolation_forest_hotspots.ipynb
├── src/
│   ├── gee_extract.py
│   ├── cpcb_loader.py
│   ├── features.py
│   ├── models.py
│   └── evaluate.py
├── dashboard/
│   └── app.py
├── outputs/
│   ├── figures/
│   └── model_artifacts/
├── requirements.txt
└── LICENSE
```

## Installation

```bash
git clone https://github.com/toxicbishop/Surface-AQI-HCHO-Mapping.git
cd aqi-hcho-satellite-india
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Authenticate Google Earth Engine (one-time):

```bash
earthengine authenticate
```

## Usage

Run the data pipeline notebooks in order (`01` through `05`), or use the source modules directly:

```bash
python src/gee_extract.py
python src/cpcb_loader.py
python src/features.py
python src/models.py
```

Launch the dashboard:

```bash
streamlit run dashboard/app.py
```

## Methodology Notes

- Train/test splits are spatial (held-out stations/regions), not random row splits, to avoid inflated metrics from spatial autocorrelation.
- CPCB stations are urban-biased; AQI predictions in rural/industrial zones extrapolate beyond direct ground truth and should be read with that caveat.
- HCHO hotspots are cross-checked against known source regions (e.g., biomass-burning corridors, industrial clusters) as a validation step.

## Future Scope

- Real-time Sentinel-5P data feeds for live monitoring
- Additional pollutant coverage: SO2, O3, PM2.5 estimation
- Mobile-friendly alert system for high-pollution zones
- Alignment with India's National Clean Air Programme (NCAP) targets

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
