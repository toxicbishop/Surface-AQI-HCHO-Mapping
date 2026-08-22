# Dashboard

Streamlit app: `streamlit run dashboard/app.py` (or `make dashboard`).

The app is deliberately thin — it reads pre-rendered artifacts from `outputs/` and
tables from `data/processed/` so it never does heavy compute. Generate those first
with the pipelines (`make aqi`, `make hcho`). See `docs/15_dashboard.md` for the
full wiring and deployment notes.
