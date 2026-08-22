# Real-Data Ingestion Setup

How to go from the synthetic demo to **real India data**. Work top to bottom;
after each step run the doctor to see progress:

```bash
python pipelines/check_ingest.py
```

The system degrades gracefully — once GEE is set up you can ingest the satellite
+ met + fire stack even before CDS/FIRMS/MOSDAC/CPCB are ready (those add BLH,
hi-res fire, INSAT AOD, and the ground-truth targets respectively).

---

## 0. Install the full dependency set

The demo runs on a minimal install; ingestion needs the heavy geospatial stack.

```bash
pip install -e .            # installs earthengine-api, cdsapi, rioxarray, rasterio, h5py, gcsfs, ...
# (or: conda env create -f environment.yml && conda activate isro-aqi)
python pipelines/check_ingest.py   # all "Python packages" should now be ✓
```

---

## 1. Google Earth Engine — TROPOMI, ERA5 met, MODIS fire, land cover, DEM  *(required)*

GEE provides 6 of the data sources. One-time setup:

1. **Create / pick a Google Cloud project** and enable Earth Engine:
   - Go to <https://code.earthengine.google.com> and sign in (free for research).
   - Register a Cloud project for Earth Engine: <https://console.cloud.google.com/earth-engine>
     (or use the EE Code Editor's prompt to create one). Note the **project id**.
2. **Authenticate locally:**
   ```bash
   earthengine authenticate          # opens a browser, writes ~/.config/earthengine/credentials
   ```
3. **Put your project id in the config:**
   ```yaml
   # config/config.yaml
   gee:
     project: "your-actual-project-id"   # <-- replace the placeholder
   ```
4. *(Optional, headless/cron):* create a service account + JSON key, then set
   `gee.service_account` and `gee.key_file` in `config.yaml`.

> GEE exports run **server-side and asynchronously** — `make ingest` *starts* the
> export tasks; you monitor + download the results (Step 6–7).

---

## 2. Copernicus CDS — ERA5 boundary-layer height (BLH)  *(recommended)*

BLH is not on GEE; it comes from the Copernicus Climate Data Store.

1. Register (free): <https://cds.climate.copernicus.eu> → accept the ERA5 licence.
2. Create `~/.cdsapirc`:
   ```
   url: https://cds.climate.copernicus.eu/api
   key: <YOUR-UID>:<YOUR-API-KEY>
   ```
   (find UID + key on your CDS profile page).
3. Verify: `python -c "import cdsapi; cdsapi.Client()"` should not error.

If skipped, BLH is omitted from the predictor stack (PM2.5/mixing skill drops a bit).

---

## 3. NASA FIRMS — VIIRS active fire (375 m)  *(recommended)*

Higher-resolution, near-real-time fire than MODIS.

1. Get a free **MAP_KEY**: <https://firms.modaps.eosdis.nasa.gov/api/map_key>
2. Export it before ingesting:
   ```bash
   export FIRMS_MAP_KEY="your-map-key"      # add to ~/.zshrc to persist
   ```

If skipped, ingestion falls back to GEE MODIS fire automatically.

---

## 4. MOSDAC — INSAT-3D AOD (ISRO's own sensor)  *(manual download)*

INSAT-3D AOD is **not on GEE** and must be ordered from ISRO's MOSDAC portal.

1. Register (free): <https://www.mosdac.gov.in> (login required to order).
2. Order **3DIMG_L2B_AOD** (10 km, half-hourly daytime) for your dates/AOI, or use
   the VEDAS mirror <https://vedas.sac.gov.in>.
3. Download the HDF5 granules into `data/external/insat/`.
4. They're read by `ingestion/insat_aod.read_granule()` during preprocessing.

> `insat_aod.download_order()` (SFTP automation) is a stub — ordering is manual.
> Cross-check option: GEE MAIAC AOD (`MODIS/061/MCD19A2_GRANULES`, 1 km) is wired as
> a fallback and is what the 1 km backbone (Change 4) was designed around.

---

## 5. CPCB — ground-station observations (the model targets)  *(manual download)*

The supervised targets (surface PM2.5/PM10/NO₂/SO₂/O₃/CO) come from CPCB CAAQMS.

1. Download station data (captcha-gated, no API):
   <https://airquality.cpcb.gov.in/ccr/#/caaqm-dashboard-all/caaqm-landing/caaqm-data-repository>
   (or data.gov.in CPCB datasets).
2. Place the CSVs in `data/external/cpcb/`.
3. Parsed by `ingestion/cpcb.py`: `load_station_metadata`, `load_raw_hourly`,
   `to_daily` (24-h mean for PM/NO₂/SO₂; 8-h rolling max for O₃/CO — CPCB AQI rules).

> Without CPCB you can still produce satellite predictor stacks, but you **cannot
> train or validate** the surface model — these are the ground truth.

---

## 6. Where exports land — Drive vs GCS

By default GEE exports to **Google Drive** (folder `isro_aqi`). For the
`milestone-2-bucket` workflow, set a bucket and exports go to **GCS** instead:

```yaml
# config/config.yaml
paths:
  gcs_bucket: "gs://your-bucket"   # needs `pip install gcsfs` + gcloud auth
```

---

## 7. Run it

```bash
python pipelines/check_ingest.py          # confirm ✓ before spending quota

# one burning season is the recommended first real run (Change-aligned):
python pipelines/01_ingest.py --start 2021-10-01 --end 2021-12-31 --static
#   --static also exports DEM + land cover (only needed once)
```

Then:
1. **Monitor** GEE tasks in the EE Code Editor → *Tasks* tab (each gas/met/fire layer).
2. **Download** finished GeoTIFFs from Drive/GCS into `data/raw/`.
3. Place INSAT AOD + CPCB CSVs in `data/external/`.
4. Continue the pipeline:
   ```bash
   make preprocess     # regrid -> 1 km, QA, AOD gap-fill, NO2 calibration, collocate
   make database       # unified training table
   make train          # hybrid (CNN-LSTM/RF trend + kriged residual) + spatial CV
   make aqi            # dual AQI atlas (CPCB + RAPI + divergence)
   make hcho           # PHV + Gi* hotspots + attribution
   ```

---

## Recommended first target

**Post-monsoon 2021 (Oct–Dec), Indo-Gangetic Plain** — peak paddy-stubble burning,
strong HCHO signal, dense CPCB coverage around Delhi. Smallest run that exercises
every change end-to-end on real data. Validate PM2.5 spatial-CV R² against the
India benchmark (~0.86) before scaling to all-India / multi-season.
```
