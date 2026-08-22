"""Publication-quality India maps.

Uses Cartopy (coastlines/borders/projection) when available; otherwise degrades
gracefully to plain matplotlib with lon/lat axes so figures still render in a
minimal environment. AQI maps use the official CPCB 6-class colour ramp.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")  # headless-safe backend
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import xarray as xr  # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap  # noqa: E402

INDIA_EXTENT = [68, 97.5, 6.5, 37.5]  # lon_min, lon_max, lat_min, lat_max
CPCB_BOUNDS = [0, 50, 100, 200, 300, 400, 500]
CPCB_COLORS = ["#009865", "#84CF33", "#FFFB26", "#F2A93B", "#EA3324", "#9C2E2C"]

try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    _HAVE_CARTOPY = True
except Exception:  # pragma: no cover - cartopy optional
    _HAVE_CARTOPY = False


# Cartopy coastline/border features download Natural Earth shapefiles at draw
# time, which needs network. Opt in with ISRO_AQI_MAP_FEATURES=1 when online;
# otherwise we render the data on plain lon/lat axes (offline-safe, no downloads).
_USE_FEATURES = os.environ.get("ISRO_AQI_MAP_FEATURES", "0") == "1"


def _india_axes(figsize=(8, 9)):
    """Return (fig, ax, transform_kw). transform_kw is {} when cartopy is absent."""
    if _HAVE_CARTOPY and _USE_FEATURES:
        fig = plt.figure(figsize=figsize)
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.set_extent(INDIA_EXTENT, crs=ccrs.PlateCarree())
        ax.add_feature(cfeature.COASTLINE, linewidth=0.4)
        ax.add_feature(cfeature.BORDERS, linewidth=0.4)
        try:
            ax.add_feature(cfeature.STATES, linewidth=0.2)
        except Exception:
            pass
        ax.gridlines(draw_labels=True, linewidth=0.2, alpha=0.4)
        return fig, ax, {"transform": ccrs.PlateCarree()}
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(INDIA_EXTENT[0], INDIA_EXTENT[1])
    ax.set_ylim(INDIA_EXTENT[2], INDIA_EXTENT[3])
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal")
    return fig, ax, {}


def aqi_map(aqi: xr.DataArray, title: str = "Daily AQI", out_path: str | None = None):
    """Render an AQI DataArray (lat, lon) with the CPCB colour scheme."""
    fig, ax, tk = _india_axes()
    cmap = ListedColormap(CPCB_COLORS)
    norm = BoundaryNorm(CPCB_BOUNDS, cmap.N)
    p = ax.pcolormesh(aqi["lon"], aqi["lat"], aqi.values, cmap=cmap, norm=norm, shading="auto", **tk)
    cbar = fig.colorbar(p, ax=ax, orientation="vertical", shrink=0.7, ticks=CPCB_BOUNDS)
    cbar.set_label("AQI")
    ax.set_title(title)
    if out_path:
        fig.savefig(out_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
    return fig


def hcho_map(hcho: xr.DataArray, hotspots=None, title="TROPOMI HCHO", out_path=None):
    """HCHO column map; optionally overlay hotspot points (DataFrame lon/lat)."""
    fig, ax, tk = _india_axes()
    p = ax.pcolormesh(hcho["lon"], hcho["lat"], hcho.values, cmap="YlOrRd", shading="auto", **tk)
    fig.colorbar(p, ax=ax, shrink=0.7, label="HCHO column (molec cm$^{-2}$)")
    if hotspots is not None and len(hotspots):
        ax.scatter(hotspots["lon"], hotspots["lat"], s=14, facecolors="none",
                   edgecolors="blue", linewidths=0.7, label="hotspot", **tk)
        ax.legend(loc="lower left", fontsize=8)
    ax.set_title(title)
    if out_path:
        fig.savefig(out_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
    return fig


def scalar_map(da: xr.DataArray, title: str, cmap="viridis", label="", out_path=None):
    """Generic continuous-field map (pollutant concentration, AOD, etc.)."""
    fig, ax, tk = _india_axes()
    p = ax.pcolormesh(da["lon"], da["lat"], da.values, cmap=cmap, shading="auto", **tk)
    fig.colorbar(p, ax=ax, shrink=0.7, label=label or da.name)
    ax.set_title(title)
    if out_path:
        fig.savefig(out_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
    return fig


def fire_density_map(fires, title="Fire density", out_path=None):
    """2-D histogram of fire-pixel locations over India (Phase 11)."""
    fig, ax, _ = _india_axes()
    h = ax.hist2d(fires["longitude"], fires["latitude"], bins=(120, 120),
                  range=[[INDIA_EXTENT[0], INDIA_EXTENT[1]], [INDIA_EXTENT[2], INDIA_EXTENT[3]]],
                  cmap="hot", cmin=1)
    fig.colorbar(h[3], ax=ax, shrink=0.7, label="fire pixels")
    ax.set_title(title)
    if out_path:
        fig.savefig(out_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
    return fig
