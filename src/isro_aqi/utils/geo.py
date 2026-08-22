"""Geospatial helpers: regular grids, regridding, distances, neighbourhoods.

The whole project is resampled onto a single regular lat/lon grid so that
heterogeneous datasets (INSAT AOD ~10 km, TROPOMI ~1 km, ERA5 ~0.1 deg,
WorldCover 10 m) become co-registered tensors. This module is the one place that
defines that grid.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import xarray as xr

EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True)
class Grid:
    """A regular lon/lat grid (cell-centre coordinates)."""

    bbox: tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat
    resolution_deg: float

    @property
    def lons(self) -> np.ndarray:
        min_lon, _, max_lon, _ = self.bbox
        return np.arange(min_lon + self.resolution_deg / 2, max_lon, self.resolution_deg)

    @property
    def lats(self) -> np.ndarray:
        _, min_lat, _, max_lat = self.bbox
        # north-to-south so row 0 is the top of the map (image convention)
        return np.arange(max_lat - self.resolution_deg / 2, min_lat, -self.resolution_deg)

    @property
    def shape(self) -> tuple[int, int]:
        return (self.lats.size, self.lons.size)

    def empty(self, fill: float = np.nan, name: str = "value") -> xr.DataArray:
        """An all-`fill` DataArray on this grid (lat, lon)."""
        data = np.full(self.shape, fill, dtype="float32")
        return xr.DataArray(
            data,
            coords={"lat": self.lats, "lon": self.lons},
            dims=("lat", "lon"),
            name=name,
        )

    def cell_index(self, lon: float, lat: float) -> tuple[int, int] | None:
        """Return (row, col) of the cell containing (lon, lat), or None if outside."""
        min_lon, min_lat, max_lon, max_lat = self.bbox
        if not (min_lon <= lon < max_lon and min_lat <= lat < max_lat):
            return None
        col = int((lon - min_lon) // self.resolution_deg)
        row = int((max_lat - lat) // self.resolution_deg)
        return row, col


def regrid(da: xr.DataArray, grid: Grid, method: str = "linear") -> xr.DataArray:
    """Resample a DataArray (with 'lat'/'lon' coords) onto `grid`.

    method: 'linear' (bilinear, for continuous fields like AOD/met) or
            'nearest' (for categorical fields like land cover).
    """
    return da.interp(lat=grid.lats, lon=grid.lons, method=method)


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in km between two points."""
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return float(2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a)))


def moore_neighbourhood(arr: np.ndarray) -> np.ndarray:
    """Stack the 8 Moore-neighbour shifts of a 2-D array along a new axis 0.

    Used by the PHV index (mean of 8 surrounding cells). Edge neighbours that
    fall off the array are NaN so callers can nan-aggregate.
    """
    padded = np.pad(arr.astype("float64"), 1, mode="constant", constant_values=np.nan)
    shifts = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            shifts.append(padded[1 + dr : 1 + dr + arr.shape[0], 1 + dc : 1 + dc + arr.shape[1]])
    return np.stack(shifts, axis=0)
