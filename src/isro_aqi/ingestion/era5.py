"""ERA5 meteorology ingestion.

ERA5-Land daily-aggregated bands come from GEE. Boundary-layer height (BLH) is
NOT in ERA5-Land, so it is pulled from the Copernicus CDS API (cdsapi). BLH
matters because it controls how representative a satellite column is of the
near-surface concentration (Dong et al. 2026): high BLH -> well-mixed column.

Derived variables:
    rh           relative humidity from T2m + dewpoint (Magnus formula)
    wind_speed   sqrt(u^2 + v^2)
    wind_dir     atan2-based meteorological direction (deg, from-north)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from isro_aqi.config import Config
from isro_aqi.ingestion.gee_auth import aoi_geometry, export_image, init_ee
from isro_aqi.utils.logging import get_logger

if TYPE_CHECKING:
    import ee

log = get_logger("era5")


def _relative_humidity(t2m: "ee.Image", d2m: "ee.Image") -> "ee.Image":
    """RH (%) from 2 m temperature and dewpoint (both Kelvin) via Magnus."""
    t_c = t2m.subtract(273.15)
    d_c = d2m.subtract(273.15)
    # e = 6.112 * exp(17.67*Tc/(Tc+243.5))
    es = t_c.expression("6.112*exp(17.67*T/(T+243.5))", {"T": t_c})
    e = d_c.expression("6.112*exp(17.67*D/(D+243.5))", {"D": d_c})
    return e.divide(es).multiply(100).rename("rh")


def build_stack(cfg: Config, start: str, end: str) -> "ee.Image":
    """Period-mean ERA5-Land met stack with derived RH and wind speed."""
    import ee

    spec = cfg.datasets["era5"]
    b = spec["bands"]
    region = aoi_geometry(cfg)
    coll = (
        ee.ImageCollection(spec["asset"]).filterDate(start, end).filterBounds(region).mean()
    )

    t2m = coll.select(b["temperature"]).rename("temperature")
    d2m = coll.select(b["dewpoint"])
    u = coll.select(b["u_wind"]).rename("u_wind")
    v = coll.select(b["v_wind"]).rename("v_wind")
    wind_speed = u.hypot(v).rename("wind_speed")

    return ee.Image.cat(
        t2m,
        _relative_humidity(t2m, d2m),
        u,
        v,
        wind_speed,
        coll.select(b["pressure"]).rename("pressure"),
        coll.select(b["precipitation"]).rename("precipitation"),
        coll.select(b["solar_radiation"]).rename("solar_radiation"),
    )


def export_period(cfg: Config, start: str, end: str) -> list:
    init_ee(cfg)
    img = build_stack(cfg, start, end)
    return [export_image(img, cfg, f"era5_{start}_{end}", 11132, folder="era5")]


def fetch_blh_cds(cfg: Config, year: int, out_path: str) -> None:
    """Download boundary-layer height for a year via the Copernicus CDS API.

    Requires ~/.cdsapirc credentials. Produces a NetCDF that the preprocessing
    step regrids onto the analysis grid and merges with the GEE met stack.
    """
    import cdsapi

    min_lon, min_lat, max_lon, max_lat = cfg.aoi.bbox
    spec = cfg.datasets["era5"]["blh"]
    c = cdsapi.Client()
    c.retrieve(
        spec["dataset"],
        {
            "product_type": "reanalysis",
            "variable": spec["variable"],
            "year": str(year),
            "month": [f"{m:02d}" for m in range(1, 13)],
            "day": [f"{d:02d}" for d in range(1, 32)],
            "time": ["00:00", "06:00", "12:00", "18:00"],
            "area": [max_lat, min_lon, min_lat, max_lon],  # N, W, S, E
            "format": "netcdf",
        },
        out_path,
    )
    log.info(f"BLH {year} -> {out_path}")
