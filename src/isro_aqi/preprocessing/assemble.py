"""Assemble the unified gridded stack from real downloaded data (Bucket C glue).

Bridges INGESTION (GEE exports + INSAT granules + CPCB CSVs on disk) and the
SCIENCE pipeline (QA -> gap-fill -> calibrate -> collocate -> train). It scans the
exported rasters, regrids every layer onto the 1 km analysis grid, and builds an
xarray Dataset (time, lat, lon) with one variable per predictor.

GEE exports are PERIOD-MEAN composites (one image per gas over [start,end]), so a
single ingest run yields one time slice labelled by the period start. Running the
ingest per-day (loop --start/--end) yields a true daily time series; the assembler
handles both -- it groups rasters by the date parsed from their filename.

Filename conventions (from the ingestion modules):
    s5p_<gas>_<start>_<end>.tif        single band  -> no2/so2/co/o3/hcho
    era5_<start>_<end>.tif             8 bands      -> temperature,rh,u_wind,...
    modis_frp_<start>_<end>.tif        3 bands      -> frp_mean,frp_max,fire_count
    modis_burned_<start>_<end>.tif     1 band       -> burned
    modis_evi_<start>_<end>.tif        1 band       -> evi
    worldcover_fractions.tif (static)  lc_* bands   -> land-cover fractions
    srtm_terrain.tif (static)          3 bands      -> elevation,slope,aspect
    INSAT granules (data/external)     HDF5/NetCDF  -> aod

Raster I/O (rioxarray/h5py) is isolated in lazily-imported helpers so this module
imports -- and its assembly core is unit-tested -- without those heavy deps.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import pandas as pd
import xarray as xr

from isro_aqi.utils.geo import Grid, regrid
from isro_aqi.utils.logging import get_logger

log = get_logger("assemble")

# explicit band orders (match the ee.Image.cat order in the ingestion modules)
ERA5_BANDS = ["temperature", "rh", "u_wind", "v_wind", "wind_speed",
              "pressure", "precipitation", "solar_radiation"]
MODIS_FRP_BANDS = ["frp_mean", "frp_max", "fire_count"]
SRTM_BANDS = ["elevation", "slope", "aspect"]

_PERIOD_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_\d{4}-\d{2}-\d{2}")
# fields that must be resampled with nearest (categorical / fractional / binary)
_NEAREST = {"burned"}


def period_label(fname: str) -> str | None:
    """Parse the period START date from an export filename, or None if static."""
    m = _PERIOD_RE.search(fname)
    return m.group(1) if m else None


def _method_for(name: str) -> str:
    return "nearest" if name.startswith("lc_") or name in _NEAREST else "linear"


# --- raster I/O (lazy rioxarray; not importable-blocking) ------------------- #
def open_raster(path: str | Path) -> xr.DataArray:
    """Open a single-band GeoTIFF as a (lat, lon) DataArray."""
    import rioxarray  # noqa: F401  (registers .rio); lazy so module imports w/o it

    da = rioxarray.open_rasterio(path, masked=True).squeeze(drop=True)
    return da.rename({"x": "lon", "y": "lat"})


def open_multiband(path: str | Path, band_names: list[str] | None = None) -> dict[str, xr.DataArray]:
    """Open a multi-band GeoTIFF -> {var: (lat,lon) DataArray}.

    Uses `band_names` if given, else the raster's embedded band descriptions
    (GEE preserves the .rename() names), else generic bandN names.
    """
    import rioxarray  # noqa: F401

    da = rioxarray.open_rasterio(path, masked=True).rename({"x": "lon", "y": "lat"})
    n = int(da.sizes["band"])
    embedded = da.attrs.get("long_name")
    if band_names is None and isinstance(embedded, (list, tuple)) and len(embedded) == n:
        band_names = list(embedded)
    names = band_names or [f"band{i + 1}" for i in range(n)]
    return {names[i]: da.isel(band=i, drop=True) for i in range(n)}


def collect_raster_layers(raw_dir: str | Path) -> tuple[dict, dict]:
    """Scan a directory of GEE-exported GeoTIFFs.

    Returns (dated, static):
        dated  : {date_str: {var: DataArray}}   period/daily layers
        static : {var: DataArray}               time-invariant (land cover, DEM)
    """
    raw = Path(raw_dir)
    dated: dict[str, dict] = defaultdict(dict)
    static: dict[str, xr.DataArray] = {}
    for tif in sorted(raw.glob("**/*.tif")):
        stem, date = tif.stem, period_label(tif.name)
        if stem.startswith("s5p_"):
            dated[date][stem.split("_")[1]] = open_raster(tif)
        elif stem.startswith("era5_"):
            dated[date].update(open_multiband(tif, ERA5_BANDS))
        elif stem.startswith("modis_frp_"):
            dated[date].update(open_multiband(tif, MODIS_FRP_BANDS))
        elif stem.startswith("modis_burned_"):
            dated[date]["burned"] = open_raster(tif)
        elif stem.startswith("modis_evi_"):
            dated[date]["evi"] = open_raster(tif)
        elif stem.startswith("worldcover"):
            static.update(open_multiband(tif))                 # lc_* (embedded names)
        elif stem.startswith("srtm"):
            static.update(open_multiband(tif, SRTM_BANDS))
        else:
            log.warning(f"unrecognised raster, skipped: {tif.name}")
    log.info(f"collected rasters: {len(dated)} date(s), {len(static)} static layer(s)")
    return dict(dated), static


def collect_insat(external_dir: str | Path, grid: Grid) -> dict[str, dict]:
    """Read INSAT-3D AOD granules (HDF5/NetCDF) from data/external -> {date:{aod:DA}}."""
    ext = Path(external_dir)
    out: dict[str, dict] = {}
    granules = list(ext.glob("**/*.h5")) + list(ext.glob("**/*.hdf")) + list(ext.glob("**/insat*/*.nc"))
    if not granules:
        return out
    from isro_aqi.ingestion import insat_aod
    for g in sorted(granules):
        date = period_label(g.name) or _date_from_any(g.name)
        try:
            out.setdefault(date, {})["aod"] = insat_aod.read_granule(str(g), grid)
        except Exception as e:
            log.warning(f"INSAT granule {g.name} skipped: {e}")
    log.info(f"collected INSAT AOD for {len(out)} date(s)")
    return out


def _date_from_any(name: str) -> str | None:
    m = re.search(r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})", name)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


# --- assembly core (pure xarray; unit-tested without rasterio) -------------- #
def assemble_from_layers(dated: dict, static: dict, grid: Grid,
                         insat: dict | None = None) -> xr.Dataset:
    """Regrid + broadcast layers into a single (time, lat, lon) Dataset.

    dated/insat: {date: {var: DataArray}}. static: {var: DataArray} broadcast to
    every date. Each layer is interpolated onto `grid` (nearest for categorical).
    """
    dated = {k: dict(v) for k, v in dated.items()}
    for d, layers in (insat or {}).items():
        dated.setdefault(d, {}).update(layers)
    if not dated:
        raise ValueError("no dated layers to assemble (need at least one dynamic raster)")

    static_rg = {k: regrid(v, grid, method=_method_for(k)) for k, v in static.items()}
    dates = sorted(d for d in dated if d is not None)
    if not dates:                       # everything was static-only / undated
        dates = list(dated)

    slices = []
    for d in dates:
        vars_ = {n: regrid(da, grid, method=_method_for(n)) for n, da in dated[d].items()}
        vars_.update(static_rg)         # same static fields in every time slice
        slices.append(xr.Dataset(vars_))
    times = pd.to_datetime([d if d is not None else "1970-01-01" for d in dates])
    stack = xr.concat(slices, dim=pd.Index(times, name="time")) if len(slices) > 1 else \
        slices[0].expand_dims(time=[times[0]])
    log.info(f"assembled stack: {dict(stack.sizes)} | {len(stack.data_vars)} variables")
    return stack


def assemble_stack(cfg, raw_dir: str | Path | None = None,
                   external_dir: str | Path | None = None) -> xr.Dataset:
    """End-to-end: scan downloaded rasters + INSAT granules -> gridded stack.

    Uses the 1 km AQI backbone grid from config. Requires rioxarray (+ h5py for
    INSAT) at runtime.
    """
    grid = Grid(tuple(cfg.aoi.bbox), cfg.grid.aqi_resolution_deg)
    dated, static = collect_raster_layers(raw_dir or cfg.paths.data_raw)
    insat = collect_insat(external_dir or cfg.paths.data_external, grid)
    return assemble_from_layers(dated, static, grid, insat)
