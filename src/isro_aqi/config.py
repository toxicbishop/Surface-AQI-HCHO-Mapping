"""Configuration loader.

Loads the layered YAML config (config.yaml + datasets.yaml + aqi_breakpoints.yaml +
regions.yaml) into validated pydantic models so the rest of the code gets typed,
auto-completing access to settings instead of dict-spelunking.

Usage
-----
    from isro_aqi.config import load_config
    cfg = load_config("config/config.yaml")
    print(cfg.aoi.bbox, cfg.time.start)
    ds = cfg.datasets["sentinel5p"]      # raw dataset registry (dict)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Typed sub-models (only the fields code touches often are typed; the rest are
# accessible via the raw dicts on Config).
# --------------------------------------------------------------------------- #
class GEEConfig(BaseModel):
    project: str
    service_account: str | None = None
    key_file: str | None = None


class AOIConfig(BaseModel):
    name: str = "india"
    bbox: list[float]  # [min_lon, min_lat, max_lon, max_lat]
    boundary_asset: str | None = None
    boundary_filter: dict[str, Any] | None = None


class GridConfig(BaseModel):
    aqi_resolution_deg: float = 0.1
    hcho_resolution_deg: float = 0.01
    crs: str = "EPSG:4326"


class TimeConfig(BaseModel):
    start: str
    end: str
    aggregations: list[str] = ["daily", "monthly", "seasonal", "annual"]
    seasons: dict[str, list[int]] = {}


class PathsConfig(BaseModel):
    data_raw: str = "data/raw"
    data_interim: str = "data/interim"
    data_processed: str = "data/processed"
    data_external: str = "data/external"
    models: str = "models"
    outputs_figures: str = "outputs/figures"
    outputs_maps: str = "outputs/maps"
    outputs_atlas: str = "outputs/atlas"
    gcs_bucket: str | None = None


class ModelConfig(BaseModel):
    targets: list[str]
    recommended: str = "cnn_lstm"
    device: str = "auto"
    patch_size: int = 15
    sequence_length: int = 7
    batch_size: int = 256
    epochs: int = 100
    lr: float = 1e-3
    early_stopping_patience: int = 12


class ValidationConfig(BaseModel):
    scheme: list[str] = ["random_kfold", "spatial_kfold", "temporal_split"]
    k_folds: int = 10
    spatial_blocks: float = 0.5
    test_years: list[int] = []


class HCHOConfig(BaseModel):
    qa_threshold: float = 0.5            # HCHO community standard (not 0.75)
    cloud_fraction_max: float = 0.4
    hva_threshold: float = 1.0e16
    phv_min: float = 1.0
    percentile: int = 95
    getis_ord: dict[str, Any] = {}
    # NOTE: `dbscan` params are accepted for config compatibility but DBSCAN is
    # NOT used -- hcho/source_attribution.connected_clusters (connected
    # components) is the dependency-light clustering actually implemented.
    dbscan: dict[str, Any] = {}
    # `fnr` thresholds feed features/engineering.add_fnr (HCHO/NO2 ratio regimes).
    fnr: dict[str, float] = {}


class Config(BaseModel):
    project: dict[str, Any] = {}
    gee: GEEConfig
    aoi: AOIConfig
    grid: GridConfig = GridConfig()
    time: TimeConfig
    paths: PathsConfig = PathsConfig()
    model: ModelConfig
    validation: ValidationConfig = ValidationConfig()
    hcho: HCHOConfig = HCHOConfig()

    # Sibling registries loaded from the other YAML files (kept as raw dicts).
    datasets: dict[str, Any] = Field(default_factory=dict)
    aqi_breakpoints: dict[str, Any] = Field(default_factory=dict)
    regions: dict[str, Any] = Field(default_factory=dict)

    # --- convenience helpers ------------------------------------------------
    @property
    def seed(self) -> int:
        return int(self.project.get("random_seed", 42))

    def path(self, key: str) -> Path:
        """Return a configured path as a Path, creating parents lazily elsewhere."""
        return Path(getattr(self.paths, key))


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


@lru_cache(maxsize=8)
def load_config(config_path: str = "config/config.yaml") -> Config:
    """Load and validate the layered configuration.

    Resolves the sibling registry files (datasets / aqi_breakpoints / regions)
    relative to the main config file's directory. Cached per path.
    """
    main = Path(config_path)
    if not main.exists():
        raise FileNotFoundError(
            f"{main} not found. Copy config/config.example.yaml -> config/config.yaml "
            "and set your GEE project id."
        )
    base = main.parent
    raw = _read_yaml(main)
    raw["datasets"] = _read_yaml(base / "datasets.yaml")
    raw["aqi_breakpoints"] = _read_yaml(base / "aqi_breakpoints.yaml")
    raw["regions"] = _read_yaml(base / "regions.yaml")
    return Config(**raw)
