#!/usr/bin/env python
"""Streamlit dashboard (Phase 14).

Interactive explorer for the full project: pick a date and layer, view the AQI /
pollutant / HCHO / fire / hotspot map, and inspect HCHO source attribution and
transport trajectories.

    streamlit run dashboard/app.py

Tabs:
    AQI        daily AQI map + dominant-pollutant + category legend
    Pollutants per-pollutant surface concentration maps
    HCHO       HCHO column + PHV/Gi* hotspots (method selector)
    Fire       VIIRS/MODIS fire density + FRP
    Hotspots   attributed hotspot table (urban/industrial/agri/forest) + map
    Transport  back-trajectory overlay for a chosen receptor/date

This file is intentionally thin: it reads the artifacts produced by the pipelines
(outputs/maps, data/processed) so the dashboard never does heavy compute itself.
"""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from isro_aqi.config import load_config

st.set_page_config(page_title="India AQI & HCHO Atlas", layout="wide")


@st.cache_resource
def get_config():
    try:
        return load_config("config/config.yaml")
    except FileNotFoundError:
        st.warning("config/config.yaml not found -- copy config/config.example.yaml.")
        return None


def main():
    cfg = get_config()
    st.title("🛰️ India Satellite AQI & HCHO Hotspot Atlas")
    st.caption("INSAT-3D · Sentinel-5P TROPOMI · CPCB · ERA5 · MODIS/VIIRS")

    with st.sidebar:
        st.header("Controls")
        sel_date = st.date_input("Date", value=date(2021, 11, 5))
        layer = st.radio("Layer", ["AQI", "Pollutants", "HCHO", "Fire", "Hotspots", "Zones", "Isolation Forest", "Transport"])
        if layer == "Pollutants":
            st.selectbox("Pollutant", ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"])
        if layer == "HCHO":
            st.selectbox("Hotspot method", ["PHV", "Getis-Ord Gi*"])
        if layer == "Transport":
            receptors = list((cfg.regions.get("receptors", {}) if cfg else {}).keys()) or ["delhi"]
            st.selectbox("Receptor", receptors)

    tabs = st.tabs(["Map", "Statistics", "About"])
    with tabs[0]:
        st.subheader(f"{layer} — {sel_date}")
        if layer == "Zones":
            path = Path("public/data/zone_cells.json")
            if path.exists():
                payload = json.loads(path.read_text())
                st.caption(f"K-Means relative segmentation; selected k={payload.get('selected_k')}. These are not official CPCB categories.")
                st.dataframe(pd.DataFrame(payload.get("cells", [])), use_container_width=True)
            else:
                st.warning("No zone_cells.json found. Run `make demo` or the real-data pipeline first.")
        elif layer == "Isolation Forest":
            path = Path("public/data/isolation_hotspots.json")
            if path.exists():
                payload = json.loads(path.read_text())
                st.caption("Unsupervised HCHO/NO₂/CO anomaly comparison; flagged cells require PHV/Gi* and ground validation.")
                st.write({k: payload.get(k) for k in ("contamination", "n_anomalies", "n_clusters", "feature_cols")})
                st.dataframe(pd.DataFrame(payload.get("cells", [])), use_container_width=True)
            else:
                st.warning("No isolation_hotspots.json found. Run `make demo` or the real-data pipeline first.")
        else:
            # The primary polished presentation is the Next.js VAYU frontend.
            st.info("Point this at outputs/maps/* produced by the pipelines (see docstring).")
    with tabs[1]:
        st.write("Category distribution, dominant pollutant frequency, trends.")
    with tabs[2]:
        st.markdown(
            "Built from the `isro_aqi` package. See `docs/ADAPTED_ARCHITECTURE.md` and `docs/` "
            "for the full methodology. The Next.js VAYU site is the primary presentation layer."
        )


if __name__ == "__main__":
    main()
