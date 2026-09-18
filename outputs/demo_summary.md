# Demo run summary

_Synthetic India data; exercises the full redesigned pipeline (6 changes)._

- Training rows: **7,200** | features: **36**


## AOD gap-fill (Change 1)
- 8% missing filled; clustered-holdout CV r2=0.9190972800714725, rmse=0.12703847578103972


## TROPOMI NO2 calibration (Change 2)
- surface-NO2 r2 **0.963** (raw column r2 0.8743564414160051); gain over raw column +0.0885


## Surface-pollutant skill — trend vs hybrid (Changes 3, 6)

| Pollutant | trend R² | hybrid R² | India target |
|---|---|---|---|
| pm25 | 0.863 | 0.864 | 0.86 |
| pm10 | 0.835 | 0.836 | 0.85 |
| no2_obs | 0.927 | 0.927 | 0.83 |
| so2_obs | 0.228 | 0.229 | 0.4 |
| o3_obs | 0.477 | 0.476 | 0.6 |
| co_obs | 0.615 | 0.616 | 0.58 |

## PM2.5 CV (random vs spatial vs temporal)
- random **0.792**, spatial **-0.184**, temporal **0.862** (spatial < random confirms autocorrelation leakage — Wang 2023).


## CNN-LSTM (ISRO-specified learner, val)

pm25 R²=0.80, pm10 R²=0.78, no2_obs R²=0.91, so2_obs R²=0.07, o3_obs R²=0.25, co_obs R²=0.58


## Dual AQI atlas — 2021-11-13 (dual index)
- **Main (CPCB):** mean 159, max 408
- **USP (RAPI):** mean 226; mean RAPI−CPCB divergence 67.0
- category cells: {'Moderate': 1450, 'Poor': 951, 'Satisfactory': 1008, 'Severe': 44, 'Very Poor': 205}


## HCHO hotspots (Change 5)
- PHV 2.8% of cells (102 HVA); Gi* None cells; 68 clusters; attribution {'biogenic': 37, 'other': 17, 'industrial': 10, 'urban': 3, 'agri_burning': 1}


## Comparative analysis layers
- K-Means selected k **4**, silhouette scores {'3': 0.42123653140972184, '4': 0.4237893675038184, '5': 0.3487061885145502}
- Isolation Forest flagged **183** cells in **16** contiguous regions
- PHV/Isolation Forest agreement is a diagnostic comparison, not supervised accuracy: None


## Transport
- Delhi 48h back-trajectory: 17 points, 741 fires within 150 km of path


## Artifacts
- `outputs/maps/` CPCB + RAPI + divergence + PM2.5 + HCHO + fire maps
- `outputs/figures/` wind rose
- `outputs/*.csv` hotspots, trajectory
