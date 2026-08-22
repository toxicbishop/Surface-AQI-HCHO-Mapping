#!/usr/bin/env python
"""Ingestion readiness doctor -- what's set up, what's still missing.

Run this BEFORE `make ingest` to see exactly which Python deps, credentials,
config values and input files are present. It imports nothing heavy (uses
importlib.find_spec) so it runs even on the minimal demo install.

    python pipelines/check_ingest.py
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

HOME = Path.home()
OK, NO, WARN = "\033[32m✓\033[0m", "\033[31m✗\033[0m", "\033[33m●\033[0m"


def _has(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


def _row(ok: bool, label: str, hint: str = "") -> bool:
    mark = OK if ok else NO
    print(f"  {mark} {label}" + (f"   — {hint}" if (not ok and hint) else ""))
    return ok


def _yaml_get(path: Path, *keys):
    try:
        import yaml
        d = yaml.safe_load(path.read_text())
        for k in keys:
            d = d[k]
        return d
    except Exception:
        return None


def main():
    print("\n\033[1mISRO-AQI ingestion readiness\033[0m\n")

    print("Python packages")
    deps = {
        "ee": "pip install earthengine-api   (GEE: TROPOMI, ERA5, MODIS, land cover, DEM)",
        "cdsapi": "pip install cdsapi          (ERA5 boundary-layer height via Copernicus CDS)",
        "h5py": "pip install h5py             (read INSAT-3D AOD HDF5 granules)",
        "rioxarray": "pip install rioxarray   (read GEE-exported GeoTIFFs back to xarray)",
        "rasterio": "pip install rasterio     (raster I/O for exported tiles)",
        "xarray": "pip install xarray         (gridded stack assembly)",
        "pandas": "pip install pandas         (CPCB / FIRMS tables)",
        "requests": "pip install requests     (NASA FIRMS API)",
        "gcsfs": "pip install gcsfs           (only if exporting to a GCS bucket)",
    }
    dep_ok = {m: _has(m) for m in deps}
    for m, hint in deps.items():
        _row(dep_ok[m], f"{m:<10}", hint)
    core_ok = all(dep_ok[m] for m in ("ee", "xarray", "pandas", "requests"))

    print("\nCredentials")
    gee = _row((HOME / ".config/earthengine/credentials").exists(),
               "Google Earth Engine", "run: earthengine authenticate")
    cds = _row((HOME / ".cdsapirc").exists(),
               "Copernicus CDS (~/.cdsapirc)", "register at cds.climate.copernicus.eu, see docs/INGESTION_SETUP.md")
    firms = _row(bool(os.environ.get("FIRMS_MAP_KEY")),
                 "NASA FIRMS MAP_KEY (env)", "get a key at firms.modaps.eosdis.nasa.gov/api/map_key + export FIRMS_MAP_KEY=...")

    print("\nConfiguration")
    cfg_path = Path("config/config.yaml")
    cfg_exists = _row(cfg_path.exists(), "config/config.yaml", "cp config/config.example.yaml config/config.yaml")
    proj = _yaml_get(cfg_path, "gee", "project") if cfg_exists else None
    proj_set = bool(proj) and proj != "your-gee-cloud-project-id"
    _row(proj_set, f"gee.project set ({proj or '—'})", "set your Google Cloud / Earth Engine project id in config.yaml")
    bucket = _yaml_get(cfg_path, "paths", "gcs_bucket") if cfg_exists else None
    print(f"  {WARN} export target: {'GCS ' + bucket if bucket else 'Google Drive (folder isro_aqi)'}")

    print("\nManual-download inputs (data/external)")
    ext = Path("data/external")
    cpcb = list(ext.glob("**/*.csv")) if ext.exists() else []
    insat = (list(ext.glob("**/*.h5")) + list(ext.glob("**/*.hdf")) + list(ext.glob("**/*.nc"))) if ext.exists() else []
    _row(bool(cpcb), f"CPCB station CSVs ({len(cpcb)} found)", "download from airquality.cpcb.gov.in/ccr -> data/external/")
    _row(bool(insat), f"INSAT-3D AOD granules ({len(insat)} found)", "order from mosdac.gov.in -> data/external/")

    print("\n\033[1mVerdict\033[0m")
    if core_ok and gee and proj_set:
        print(f"  {OK} GEE ingestion is ready: run  make ingest")
        if not cds:
            print(f"  {WARN} ERA5 boundary-layer height will be skipped until CDS is set up")
        if not firms:
            print(f"  {WARN} VIIRS fire (FIRMS) will fall back to GEE MODIS until FIRMS_MAP_KEY is set")
        if not (cpcb and insat):
            print(f"  {WARN} CPCB targets and/or INSAT AOD still need manual download (see above)")
    else:
        print(f"  {NO} not ready yet. Next steps:")
        if not core_ok:
            print("     1. pip install -e .            (installs earthengine-api, cdsapi, rioxarray, ...)")
        if not gee:
            print("     2. earthengine authenticate")
        if not proj_set:
            print("     3. set gee.project in config/config.yaml")
        print("     full guide: docs/INGESTION_SETUP.md")
    print()


if __name__ == "__main__":
    main()
