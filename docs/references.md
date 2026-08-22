# References

Bibliography for the blueprint. The four anchor papers are cited inline across the
docs as **[A]–[D]**; the local PDFs are in [`../references/`](../references/) (move
the four PDFs there once any background processing finishes).

---

## Anchor papers

- **[A]** Dong, X., *et al.* (2026). *Satellite-Based Identification of VOC-Driven
  HCHO Hotspots and Their Role in Ozone Pollution Formation in the
  Beijing–Tianjin–Hebei Region.* **Atmosphere**, 17, 321.
  → PHV (Percentage Higher than Vicinity) / HVA hotspot method on a 1 km grid;
  mutation/change-detection; FNR (HCHO/NO₂) ozone-sensitivity regimes; KZ-filter
  driver attribution. *PDF: `atmosphere-17-00321.pdf`.*

- **[B]** Kuttippurath, J., *et al.* (2022). *Investigation of long-term trends and
  major sources of atmospheric HCHO over India.* **Environmental Challenges**, 7,
  100477.
  → TROPOMI/OMI HCHO trends over India; MODIS fire-count + FRP (pyrogenic) and EVI
  (biogenic) proxies; COVID-lockdown natural experiment; biomass-burning belts.
  *PDF: `1-s2.0-S2667010022000373-main.pdf`.*

- **[C]** Wang, W., *et al.* (2023). *High-resolution modeling for criteria air
  pollutants and the associated air quality index in a metropolitan city.*
  **Environment International**, 172, 107752.
  → Spatiotemporal geostatistical modelling (MAIAC AOD + NO₂), RF gap-filling,
  universal kriging + PLS; 10-fold CV benchmarks; spatial-vs-temporal CV; max-of-
  sub-index AQI. *PDF: `1-s2.0-S0160412023000259-main.pdf`.*

- **[D]** Lu, W.-Z., *et al.* (2011). *Assessing air quality in Hong Kong: A
  proposed, revised air pollution index (API).* **Building & Environment**, 46.
  → Linear-interpolation sub-index API; critique of max-only aggregation;
  Shannon-entropy RAPI alternative. *PDF: `Assessing_air_quality_in_Hong_Kong_A_proposed_revi.pdf`.*

---

## Methods

- **CPCB (2014).** *National Air Quality Index.* Central Pollution Control Board,
  MoEFCC, Government of India. — sub-index breakpoints + categories (config/aqi_breakpoints.yaml).
- **US EPA (2018).** *Technical Assistance Document for the Reporting of Daily Air
  Quality — the Air Quality Index (AQI).* EPA-454/B-18-007.
- **Getis, A. & Ord, J. K. (1992).** The analysis of spatial association by use of
  distance statistics. *Geographical Analysis*, 24(3), 189–206. — Getis-Ord Gi*.
- **Ord, J. K. & Getis, A. (1995).** Local spatial autocorrelation statistics:
  distributional issues and an application. *Geographical Analysis*, 27(4), 286–306.
- **Ester, M., Kriegel, H.-P., Sander, J., & Xu, X. (1996).** A density-based
  algorithm for discovering clusters (DBSCAN). *Proc. KDD-96*, 226–231.
- **Benjamini, Y. & Hochberg, Y. (1995).** Controlling the false discovery rate.
  *J. R. Stat. Soc. B*, 57(1), 289–300. — FDR correction for Gi* p-values.
- **Lundberg, S. M. & Lee, S.-I. (2017).** A unified approach to interpreting model
  predictions (SHAP). *NeurIPS 30*.
- **Theil, H. (1950)** / **Sen, P. K. (1968).** Rank-based (Theil–Sen) trend slope.
  *Proc. KNAW* / *JASA*, 63, 1379–1389.
- **Mann, H. B. (1945).** Nonparametric tests against trend. *Econometrica*, 13(3),
  245–259. — Mann–Kendall significance for HCHO trends.
- **Duncan, B. N., *et al.* (2010).** Application of OMI observations to a space-based
  indicator of NOₓ and VOC controls on surface ozone. *Atmos. Environ.*, 44, 2213–2223.
- **Jin, X. & Holloway, T. (2015).** Spatial and temporal variability of ozone
  sensitivity over China observed from OMI. *J. Geophys. Res. Atmos.*, 120.
- **Stein, A. F., *et al.* (2015).** NOAA's HYSPLIT atmospheric transport and
  dispersion modeling system. *Bull. Amer. Meteor. Soc.*, 96, 2059–2077.
- **Hochreiter, S. & Schmidhuber, J. (1997).** Long short-term memory. *Neural
  Computation*, 9(8). — LSTM.

---

## Datasets

| Dataset | Variable(s) | Source / access | Reference |
|---------|-------------|-----------------|-----------|
| INSAT-3D Imager L2B | AOD (~10 km) | **MOSDAC** (ISRO/SAC), product `3DIMG_L2B_AOD` | MOSDAC, mosdac.gov.in |
| Sentinel-5P TROPOMI | NO₂, SO₂, CO, O₃, HCHO | GEE `COPERNICUS/S5P/OFFL/L3_*` | ESA/Copernicus; Veefkind et al. 2012 |
| CPCB CAAQMS | PM2.5, PM10, NO₂, SO₂, O₃, CO | CPCB CCR portal / data.gov.in | CPCB |
| ERA5 / ERA5-Land | T, dewpoint, U/V, SP, precip, SSRD | GEE `ECMWF/ERA5_LAND/DAILY_AGGR` | Hersbach et al. 2020; Muñoz-Sabater et al. 2021 |
| ERA5 single-levels | Boundary-layer height (BLH) | Copernicus **CDS** API | Hersbach et al. 2020 |
| MODIS active fire | FireMask, MaxFRP | GEE `MODIS/061/MOD14A1` | Giglio et al. 2016 |
| MODIS burned area | BurnDate | GEE `MODIS/061/MCD64A1` | Giglio et al. 2018 |
| MODIS vegetation | EVI (biogenic proxy) | GEE `MODIS/061/MOD13A2` | Didan 2015 |
| VIIRS active fire | FRP, confidence (375 m) | NASA **FIRMS** API `VNP14IMGTDL_NRT`; GEE `FIRMS` | Schroeder et al. 2014 |
| MAIAC AOD (cross-check) | AOD (1 km) | GEE `MODIS/061/MCD19A2` | Lyapustin et al. 2018 |
| ESA WorldCover | Land cover (10 m, 11 classes) | GEE `ESA/WorldCover/v200` | Zanaga et al. 2022 |
| SRTM | Elevation (30 m) | GEE `USGS/SRTMGL1_003` | Farr et al. 2007 |
| FAO GAUL | India boundary | GEE `FAO/GAUL/2015/level0` | FAO |

*GEE asset IDs and bands are the source of truth in [`../config/datasets.yaml`](../config/datasets.yaml).*
