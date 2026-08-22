"""Unified India-wide database (Phase 3).

One tidy record per (date, lat, lon) carrying every predictor and every available
CPCB target. At India scale over multiple years this is the ~50-100 M row table
the models train on. Stored as year/month-partitioned parquet for lazy querying.
"""

from isro_aqi.database.schema import COLUMNS, TARGETS, PREDICTORS

__all__ = ["COLUMNS", "TARGETS", "PREDICTORS"]
