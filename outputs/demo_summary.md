# Demo run summary

_Synthetic India data; exercises the full redesigned pipeline (6 changes)._

- Training rows: **450** | features: **36**


## AOD gap-fill (Change 1)
- 9% missing filled; clustered-holdout CV r2=None, rmse=None


## TROPOMI NO2 calibration (Change 2)
- surface-NO2 r2 **0.986** (raw column r2 0.9268283351715378); gain over raw column +0.0595


## Surface-pollutant skill — trend vs hybrid (Changes 3, 6)

| Pollutant | trend R² | hybrid R² | India target |
|---|---|---|---|
| pm25 | 0.903 | 0.900 | 0.86 |
| pm10 | 0.871 | 0.868 | 0.85 |
| no2_obs | 0.949 | 0.949 | 0.83 |
| so2_obs | 0.574 | 0.575 | 0.4 |
| o3_obs | 0.469 | 0.466 | 0.6 |
| co_obs | 0.494 | 0.491 | 0.58 |

## PM2.5 CV (random vs spatial vs temporal)
- random **0.874**, spatial **0.246**, temporal **0.901** (spatial < random confirms autocorrelation leakage — Wang 2023).


## CNN-LSTM (ISRO-specified learner, val)

pm25 R²=0.71, pm10 R²=0.65, no2_obs R²=0.44, so2_obs R²=-0.04, o3_obs R²=0.11, co_obs R²=0.25


## Dual AQI atlas — 2021-10-22 (dual index)
- **Main (CPCB):** mean 147, max 430
- **USP (RAPI):** mean 212; mean RAPI−CPCB divergence 64.5
- category cells: {'Moderate': 380, 'Satisfactory': 306, 'Poor': 143, 'Severe': 12, 'Very Poor': 58}


## HCHO hotspots (Change 5)
- PHV 4.7% of cells (42 HVA); Gi* 280 cells; 22 clusters; attribution {'biogenic': 8, 'other': 7, 'industrial': 3, 'urban': 3, 'agri_burning': 1}


## Comparative analysis layers
- K-Means selected k **3**, silhouette scores {'3': 0.44412128223109354, '4': 0.4430676961892559, '5': 0.3367830041570892}
- Isolation Forest flagged **45** cells in **11** contiguous regions
- PHV/Isolation Forest agreement is a diagnostic comparison, not supervised accuracy: None


## Transport
- Delhi 48h back-trajectory: 17 points, 47 fires within 150 km of path


## Artifacts
- `outputs/maps/` CPCB + RAPI + divergence + PM2.5 + HCHO + fire maps
- `outputs/figures/` wind rose
- `outputs/*.csv` hotspots, trajectory
