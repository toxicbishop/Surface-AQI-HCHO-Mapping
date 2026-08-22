"""Atmospheric transport analysis (Phase 13) -- the differentiator.

Did upwind fires raise HCHO at a receptor city? Three tools, increasing rigour:

1. wind_rose          frequency of wind speed/direction at a receptor (windrose).
2. back_trajectory    lightweight ERA5-wind back-trajectory (kinematic, single
                      level) -- where did today's air parcel come from? Good for
                      quick "Punjab fires -> Delhi" screening without HYSPLIT.
3. HYSPLIT (external) production-grade trajectories via NOAA HYSPLIT / pysplit
                      -- see run_hysplit() docstring for the wiring.

The back-trajectory steps a parcel backwards through the ERA5 (u,v) field with an
hourly time step on a sphere, returning the lon/lat path. Overlay the path on the
fire-count map to test source-receptor links (e.g. Punjab fires -> Delhi HCHO).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

from isro_aqi.utils.geo import EARTH_RADIUS_KM
from isro_aqi.utils.logging import get_logger

log = get_logger("transport")

# Single source of truth for the Earth radius (was re-declared here).
EARTH_R_KM = EARTH_RADIUS_KM


def wind_rose(u: pd.Series, v: pd.Series, out_path: str | None = None):
    """Plot (and optionally save) a wind rose from u/v components."""
    import matplotlib.pyplot as plt
    from windrose import WindroseAxes

    speed = np.hypot(u, v)
    # meteorological direction the wind blows FROM (deg, 0=N, clockwise)
    direction = (270 - np.degrees(np.arctan2(v, u))) % 360
    ax = WindroseAxes.from_ax()
    ax.bar(direction, speed, normed=True, opening=0.8, edgecolor="white")
    ax.set_legend(title="m/s")
    if out_path:
        plt.savefig(out_path, dpi=200, bbox_inches="tight")
    return ax


def back_trajectory(
    winds: xr.Dataset,
    start_lon: float,
    start_lat: float,
    start_time: str,
    hours: int = 48,
    dt_hours: float = 1.0,
    u_var: str = "u_wind",
    v_var: str = "v_wind",
) -> pd.DataFrame:
    """Kinematic single-level back-trajectory through an ERA5 (u,v) field.

    Steps a parcel BACKWARDS for `hours`, sampling (u,v) at the parcel's current
    position/time each step. Returns a path DataFrame (time, lon, lat). Overlay on
    a fire map to attribute receptor HCHO to upwind burning.
    """
    times = pd.to_datetime(winds["time"].values)
    # AOI bounds of the wind field. Without clamping, once a parcel leaves the
    # grid ``.sel(method="nearest")`` keeps returning the EDGE cell's wind,
    # fabricating a plausible-looking but unsupported off-grid trajectory. We clip
    # each step back into [lon_min,lon_max] x [lat_min,lat_max] and stop stepping
    # once the parcel has left the AOI (its origin is then outside our data).
    lon_min, lon_max = float(winds["lon"].min()), float(winds["lon"].max())
    lat_min, lat_max = float(winds["lat"].min()), float(winds["lat"].max())

    lon, lat = start_lon, start_lat
    t = pd.to_datetime(start_time)
    path = [{"time": t, "lon": lon, "lat": lat}]

    steps = int(hours / dt_hours)
    dt_s = dt_hours * 3600.0
    for _ in range(steps):
        ti = int(np.argmin(np.abs(times - t)))
        frame = winds.isel(time=ti)
        u = float(frame[u_var].sel(lon=lon, lat=lat, method="nearest"))
        v = float(frame[v_var].sel(lon=lon, lat=lat, method="nearest"))
        # backward step: subtract displacement
        dlat = -(v * dt_s) / (EARTH_R_KM * 1000) * (180 / np.pi)
        dlon = -(u * dt_s) / (EARTH_R_KM * 1000 * np.cos(np.radians(lat))) * (180 / np.pi)
        lat += dlat
        lon += dlon
        t -= pd.Timedelta(hours=dt_hours)
        # clamp to the AOI so the next .sel(nearest) cannot fabricate off-grid wind
        clamped_lon = min(max(lon, lon_min), lon_max)
        clamped_lat = min(max(lat, lat_min), lat_max)
        left_aoi = clamped_lon != lon or clamped_lat != lat
        lon, lat = clamped_lon, clamped_lat
        path.append({"time": t, "lon": lon, "lat": lat})
        if left_aoi:
            # parcel reached the AOI edge -> upstream source is outside our winds
            log.info("back_trajectory: parcel reached AOI boundary; stopping early")
            break
    return pd.DataFrame(path)


def fires_along_path(path: pd.DataFrame, fires: pd.DataFrame, radius_km: float = 50.0) -> int:
    """Count fire pixels within `radius_km` of any point on a trajectory path.

    Vectorised haversine over the (fires x path) grid so it scales to thousands
    of fire pixels and long trajectories.
    """
    if len(fires) == 0 or len(path) == 0:
        return 0
    flon = np.radians(fires["longitude"].to_numpy())[:, None]
    flat = np.radians(fires["latitude"].to_numpy())[:, None]
    plon = np.radians(path["lon"].to_numpy())[None, :]
    plat = np.radians(path["lat"].to_numpy())[None, :]
    dlon, dlat = plon - flon, plat - flat
    a = np.sin(dlat / 2) ** 2 + np.cos(flat) * np.cos(plat) * np.sin(dlon / 2) ** 2
    dist_km = 2 * EARTH_R_KM * np.arcsin(np.sqrt(a))   # (n_fires, n_path)
    return int((dist_km.min(axis=1) <= radius_km).sum())


def run_hysplit(*args, **kwargs):
    """Production trajectories via NOAA HYSPLIT (external engine).

    NOT IMPLEMENTED -- requires an external native engine (NOAA HYSPLIT) and
    staged ARL met files that cannot run in this environment; the lightweight
    ``back_trajectory`` above is the in-repo substitute.

    Recommended wiring: install HYSPLIT + `pysplit`, stage GDAS/ERA5 ARL met
    files, then generate ensembles of backward trajectories per receptor/day and
    cluster them (pysplit's trajectory clustering) into transport corridors.
    Kept as an explicit hook so the lightweight back_trajectory() above can be
    swapped for HYSPLIT without changing callers.
    """
    raise NotImplementedError("Wire NOAA HYSPLIT / pysplit; see docs/13_transport_analysis.md")
