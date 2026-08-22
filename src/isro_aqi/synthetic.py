"""Synthetic India dataset generator.

The live data sources (INSAT/MOSDAC, CPCB, Sentinel-5P via GEE, ERA5 via CDS,
VIIRS via FIRMS) all need interactive credentials, so this module manufactures a
*physically-plausible* India dataset that exercises the ENTIRE pipeline end-to-end
without any external access. Swapping synthetic -> real later means only providing
credentials + running the ingestion modules; every downstream stage is unchanged.

What it builds (all on the project analysis grid, dims time/lat/lon):
  * a predictor stack (AOD, TROPOMI gases incl. HCHO, ERA5 met + BLH, MODIS fire +
    EVI, static land-cover/elevation) with realistic spatial structure (IGP haze
    belt, urban/industrial NO2 plumes, terrain) and post-monsoon stubble-burning
    EPISODES over Punjab/Haryana that spike AOD/HCHO/fire together;
  * ~N CPCB-like stations whose observed PM2.5/PM10/NO2/SO2/O3/CO are generated
    from the local predictors via documented, physically-motivated response
    functions (so the ML models have genuine, learnable signal);
  * VIIRS-style fire pixels (lon/lat/FRP/date) for transport analysis;
  * an HCHO field with planted hotspots over agri-burning / urban / industrial
    zones so PHV / Gi* / DBSCAN have real anomalies to find.

Everything is seeded -> fully reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import xarray as xr

from isro_aqi.utils.geo import Grid
from isro_aqi.utils.logging import get_logger

log = get_logger("synthetic")

INDIA_BBOX = (68.0, 6.5, 97.5, 37.5)

# Approximate source locations (lon, lat) used to plant structure.
CITIES = {
    "delhi": (77.10, 28.65), "mumbai": (72.88, 19.08), "kolkata": (88.36, 22.57),
    "chennai": (80.27, 13.08), "bangalore": (77.59, 12.97), "hyderabad": (78.49, 17.39),
    "ahmedabad": (72.57, 23.03), "lucknow": (80.95, 26.85), "patna": (85.14, 25.61),
    "kanpur": (80.33, 26.45),
}
INDUSTRIAL = {"ankleshwar": (72.99, 21.63), "jharia": (86.41, 23.75), "korba": (82.69, 22.36)}
# Stubble-burning core cells (Punjab/Haryana) and a NE forest-fire patch.
BURN_CORES = [(75.3, 30.6), (76.2, 30.2), (75.8, 29.7), (76.8, 29.4)]  # Punjab/Haryana
FOREST_CORES = [(94.0, 26.5), (92.8, 25.2)]  # NE India


@dataclass
class SyntheticConfig:
    bbox: tuple = INDIA_BBOX
    resolution_deg: float = 0.5         # demo grid (~55 km); fine enough, fast
    n_days: int = 60
    start: str = "2021-10-15"           # post-monsoon: paddy stubble-burning window
    n_stations: int = 120
    seed: int = 42


def _gauss(lon2d, lat2d, lon0, lat0, amp, sigma):
    """A 2-D Gaussian blob centred at (lon0, lat0)."""
    return amp * np.exp(-(((lon2d - lon0) ** 2 + (lat2d - lat0) ** 2) / (2 * sigma**2)))


def _norm(a):
    a = np.asarray(a, dtype="float64")
    lo, hi = np.nanmin(a), np.nanmax(a)
    return (a - lo) / (hi - lo + 1e-12)


def _static_fields(grid: Grid, rng) -> dict[str, np.ndarray]:
    """Time-invariant predictors: elevation/terrain + land-cover fractions."""
    lon2d, lat2d = np.meshgrid(grid.lons, grid.lats)
    h, w = grid.shape

    # Elevation: Himalayan arc (north) + Western Ghats (SW coast) + plains.
    elevation = (
        _gauss(lon2d, lat2d, 80, 34, 5000, 6)          # Himalaya
        + _gauss(lon2d, lat2d, 75, 13, 1500, 5)        # Western Ghats
        + 50 + 20 * rng.standard_normal((h, w))
    ).clip(0, 8000)
    slope = np.abs(np.gradient(elevation)[0]) + np.abs(np.gradient(elevation)[1])
    aspect = (np.degrees(np.arctan2(*np.gradient(elevation))) % 360)

    # Land cover fractions (sum ~1). Crop dominates the IGP; built peaks at cities.
    crop = _norm(_gauss(lon2d, lat2d, 80, 27, 1, 7))               # IGP cropland belt
    built = np.zeros((h, w))
    for lon0, lat0 in CITIES.values():
        built += _gauss(lon2d, lat2d, lon0, lat0, 1.0, 0.6)
    built = _norm(built)
    tree = _norm(_gauss(lon2d, lat2d, 94, 26, 1, 4) + _gauss(lon2d, lat2d, 75, 13, 1, 4))
    water = _norm(_gauss(lon2d, lat2d, 88, 22, 1, 2))             # Gangetic delta-ish
    bare = _norm(_gauss(lon2d, lat2d, 71, 27, 1, 4))              # Thar desert
    # normalise the big classes so fractions are sensible
    total = crop + built + tree + water + bare + 0.1
    return {
        "elevation": elevation, "slope": slope, "aspect": aspect,
        "lc_crop": crop / total, "lc_built": built / total, "lc_tree": tree / total,
        "lc_water": water / total, "lc_bare": bare / total,
        "lc_grass": (0.05 / total), "lc_shrub": (0.03 / total),
        "lc_wetland": water / total * 0.3,
    }


def _burn_intensity(day_idx: int, n_days: int, rng) -> float:
    """Stubble-burning intensity over the season: rises, peaks mid-window, episodic."""
    base = np.exp(-((day_idx - n_days * 0.5) ** 2) / (2 * (n_days * 0.22) ** 2))
    episodic = 0.4 + 0.6 * (rng.random() < 0.5)  # some days flare, some calm
    return float(base * episodic)


def generate_stack(cfg: SyntheticConfig) -> xr.Dataset:
    """Build the full (time, lat, lon) predictor Dataset."""
    rng = np.random.default_rng(cfg.seed)
    grid = Grid(cfg.bbox, cfg.resolution_deg)
    lon2d, lat2d = np.meshgrid(grid.lons, grid.lats)
    h, w = grid.shape
    dates = pd.date_range(cfg.start, periods=cfg.n_days, freq="D")
    statics = _static_fields(grid, rng)

    # latitudinal temperature gradient (warmer south), seasonal cooling over window
    lat_norm = _norm(-lat2d)  # 1 in south, 0 in north
    channels = {k: np.repeat(v[None, :, :], cfg.n_days, axis=0) for k, v in statics.items()}
    dyn = {c: np.zeros((cfg.n_days, h, w), "float64") for c in (
        "aod", "no2", "so2", "co", "o3", "hcho", "temperature", "rh", "u_wind",
        "v_wind", "wind_speed", "pressure", "precipitation", "solar_radiation",
        "blh", "frp_mean", "frp_max", "fire_count", "burned", "evi",
    )}

    igp_haze = _gauss(lon2d, lat2d, 81, 27, 1.0, 7.0)  # Indo-Gangetic haze belt
    no2_plumes = np.zeros((h, w))
    for lon0, lat0 in {**CITIES, **INDUSTRIAL}.values():
        no2_plumes += _gauss(lon2d, lat2d, lon0, lat0, 1.0, 0.7)
    so2_plumes = sum(_gauss(lon2d, lat2d, lo, la, 1.0, 0.6) for lo, la in INDUSTRIAL.values())

    for t, _date in enumerate(dates):
        burn = _burn_intensity(t, cfg.n_days, rng)
        fire = np.zeros((h, w))
        for lon0, lat0 in BURN_CORES:
            fire += _gauss(lon2d, lat2d, lon0, lat0, burn, 0.5)
        for lon0, lat0 in FOREST_CORES:
            fire += _gauss(lon2d, lat2d, lon0, lat0, burn * 0.5, 0.6)
        noise = lambda s=1.0: s * rng.standard_normal((h, w))

        temperature = 300 - 12 * _norm(lat2d) - 0.5 * t / cfg.n_days * 10 + 2 * noise()
        blh = (1200 - 600 * burn + 300 * lat_norm + 150 * noise()).clip(150, 2500)
        ssrd = (1.8e7 + 3e6 * lat_norm - 4e6 * burn + 1e6 * noise()).clip(1e6, None)
        precip = np.clip(0.002 * rng.random((h, w)) - 0.0015, 0, None)
        rh = (55 + 20 * _norm(statics["lc_water"]) + 10 * noise()).clip(5, 100)
        u = 2 + 1.5 * noise()          # broadly westerly with variability
        v = -1.5 + 1.5 * noise()       # NW->SE drift over IGP in this season

        aod = (0.25 + 1.4 * igp_haze + 2.2 * fire + 0.6 * _norm(no2_plumes)
               + 0.5 * (1 - _norm(blh)) + 0.08 * noise()).clip(0.02, 4.5)
        hcho = (3e15 + 9e15 * igp_haze + 1.4e16 * fire + 4e15 * _norm(no2_plumes)
                + 1.5e15 * np.abs(noise())) * 1.0  # molec/cm^2-scale magnitudes
        # NO2 column on a molec/cm^2 scale comparable to HCHO so the HCHO/NO2
        # (FNR) ratio is physically meaningful (~0.5-5, spanning O3 regimes).
        no2 = (1.5e15 + 9e15 * _norm(no2_plumes) + 2e15 * fire + 5e14 * np.abs(noise()))
        so2 = (1e-5 + 8e-5 * _norm(so2_plumes) + 5e-6 * np.abs(noise()))
        co = (0.02 + 0.03 * igp_haze + 0.05 * fire + 0.005 * np.abs(noise()))
        o3 = (0.10 + 0.03 * _norm(ssrd) + 0.06 * _norm(hcho) - 0.01 * _norm(no2_plumes)
              + 0.005 * noise()).clip(0.02, None)

        dyn["temperature"][t] = temperature
        dyn["blh"][t] = blh
        dyn["solar_radiation"][t] = ssrd
        dyn["precipitation"][t] = precip
        dyn["rh"][t] = rh
        dyn["u_wind"][t] = u
        dyn["v_wind"][t] = v
        dyn["wind_speed"][t] = np.hypot(u, v)
        dyn["pressure"][t] = 1.0e5 - 8 * statics["elevation"] + 50 * noise()
        dyn["aod"][t] = aod
        dyn["hcho"][t] = hcho
        dyn["no2"][t] = no2
        dyn["so2"][t] = so2
        dyn["co"][t] = co
        dyn["o3"][t] = o3
        frp = (fire * 120).clip(0, None)
        dyn["frp_mean"][t] = frp
        dyn["frp_max"][t] = frp * 1.6
        dyn["fire_count"][t] = (fire > 0.3).astype("float64") * np.round(fire * 20)
        dyn["burned"][t] = (fire > 0.5).astype("float64")
        dyn["evi"][t] = (0.2 + 0.4 * statics["lc_tree"] + 0.3 * statics["lc_crop"]
                         + 0.02 * noise()).clip(0, 1)

    data_vars = {}
    for name, arr in {**channels, **dyn}.items():
        data_vars[name] = (("time", "lat", "lon"), arr.astype("float32"))
    ds = xr.Dataset(
        data_vars,
        coords={"time": dates, "lat": grid.lats, "lon": grid.lons},
        attrs={"source": "synthetic", "seed": cfg.seed, "note": "physically-plausible demo data"},
    )
    log.info(f"synthetic stack: {dict(ds.sizes)} | {len(ds.data_vars)} channels")
    return ds


def generate_stations(cfg: SyntheticConfig) -> pd.DataFrame:
    """CPCB-like stations: clustered near cities + scattered across India."""
    rng = np.random.default_rng(cfg.seed + 1)
    rows = []
    # ~60% near cities, 40% scattered
    n_city = int(cfg.n_stations * 0.6)
    cities = list(CITIES.items())
    for i in range(n_city):
        name, (lon0, lat0) = cities[i % len(cities)]
        rows.append({
            "station_id": f"S{i:03d}",
            "name": f"{name}_{i}",
            "lon": float(np.clip(lon0 + 0.4 * rng.standard_normal(), cfg.bbox[0], cfg.bbox[2])),
            "lat": float(np.clip(lat0 + 0.4 * rng.standard_normal(), cfg.bbox[1], cfg.bbox[3])),
        })
    for i in range(n_city, cfg.n_stations):
        rows.append({
            "station_id": f"S{i:03d}",
            "name": f"rural_{i}",
            "lon": float(rng.uniform(cfg.bbox[0] + 1, cfg.bbox[2] - 1)),
            "lat": float(rng.uniform(cfg.bbox[1] + 1, cfg.bbox[3] - 1)),
        })
    return pd.DataFrame(rows)


def generate_observations(stack: xr.Dataset, stations: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Generate CPCB-like daily surface observations from local predictors.

    Response functions are physically motivated (documented inline) so the ML
    models learn real relationships: PM2.5 rises with AOD, fire and low BLH;
    O3 is photochemical (solar radiation + HCHO, suppressed by fresh NO2); SO2/CO
    are deliberately noisier (mirrors their poor real-world satellite skill).
    """
    rng = np.random.default_rng(seed + 2)
    lons = xr.DataArray(stations["lon"].values, dims="station")
    lats = xr.DataArray(stations["lat"].values, dims="station")
    s = stack.sel(lon=lons, lat=lats, method="nearest")  # (time, station)

    def N(name):  # normalised 0..1 across the whole sampled array
        a = s[name].values
        return _norm(a)

    aod, blh, fire = N("aod"), N("blh"), N("frp_mean")
    built, rh, precip = N("lc_built"), N("rh"), N("precipitation")
    ssrd, temp, hcho, no2c, so2c, coc = N("solar_radiation"), N("temperature"), N("hcho"), N("no2"), N("so2"), N("co")
    crop = N("lc_crop")
    noise = lambda s_=1.0: s_ * rng.standard_normal(aod.shape)

    # Per-station UNOBSERVED local-emission factor (not a predictor). Models can
    # only capture it by seeing a station in training (via lat/lon) -> this is
    # what makes spatial CV degrade vs random CV (the Wang 2023 leakage effect).
    station_eff = rng.normal(0.0, 0.22, aod.shape[1])[None, :]

    pm25 = ((12 + 110 * aod + 55 * fire + 30 * built + 35 * (1 - blh)
            + 12 * rh - 25 * precip + 9 * noise()) * (1 + station_eff)).clip(2, 950)
    pm10 = (1.7 * pm25 + 40 * N("lc_bare") + 12 * noise()).clip(5, 999)
    no2_obs = ((6 + 70 * no2c + 18 * built + 8 * (1 - blh) + 5 * noise()) * (1 + 0.6 * station_eff)).clip(1, 400)
    so2_obs = (4 + 45 * so2c + 9 * np.abs(noise(1.4))).clip(1, 350)            # noisier
    co_obs = (0.3 + 2.6 * coc + 1.4 * fire + 0.5 * np.abs(noise(1.4))).clip(0.1, 30)  # noisier
    # O3 is photochemical: HCHO (VOC proxy) is a strong positive precursor signal
    # (R(HCHO,O3) ~ 0.4-0.9 in the ozone season per Dong 2026), modulated by
    # radiation/temperature and suppressed by fresh NO2 titration.
    o3_obs = (20 + 50 * ssrd + 25 * temp + 55 * hcho - 18 * no2c + 8 * noise()).clip(2, 300)

    out = []
    times = pd.to_datetime(stack["time"].values)
    for j, sid in enumerate(stations["station_id"].values):
        for i, date in enumerate(times):
            out.append({
                "station_id": sid, "date": date,
                "pm25": pm25[i, j], "pm10": pm10[i, j], "no2_obs": no2_obs[i, j],
                "so2_obs": so2_obs[i, j], "o3_obs": o3_obs[i, j], "co_obs": co_obs[i, j],
            })
    df = pd.DataFrame(out)
    log.info(f"synthetic observations: {len(df):,} station-days")
    return df


def generate_fire_pixels(stack: xr.Dataset, seed: int = 42) -> pd.DataFrame:
    """VIIRS-style fire-pixel table (lon/lat/frp/confidence/acq_date)."""
    rng = np.random.default_rng(seed + 3)
    rows = []
    times = pd.to_datetime(stack["time"].values)
    frp = stack["frp_mean"]
    lon, lat = stack["lon"].values, stack["lat"].values
    for i, date in enumerate(times):
        f = frp.isel(time=i).values
        idx = np.argwhere(f > 20)
        for r, c in idx:
            rows.append({
                "latitude": float(lat[r]), "longitude": float(lon[c]),
                "frp": float(f[r, c]), "confidence": int(rng.integers(50, 100)),
                "acq_date": date.strftime("%Y-%m-%d"), "daynight": "D",
            })
    df = pd.DataFrame(rows)
    log.info(f"synthetic fire pixels: {len(df):,}")
    return df


def generate_all(cfg: SyntheticConfig | None = None) -> dict:
    """Produce stack + stations + observations + fire pixels (in memory)."""
    cfg = cfg or SyntheticConfig()
    stack = generate_stack(cfg)
    stations = generate_stations(cfg)
    obs = generate_observations(stack, stations, cfg.seed)
    fires = generate_fire_pixels(stack, cfg.seed)
    return {"stack": stack, "stations": stations, "observations": obs, "fires": fires, "cfg": cfg}
