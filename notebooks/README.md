# Notebooks

Exploratory / analysis notebooks. Keep production logic in `src/isro_aqi/`; import
from there rather than copy-pasting into notebooks.

Suggested notebooks:
- `01_data_exploration.ipynb` — sanity-check raw GEE exports & CPCB coverage
- `02_collocation_check.ipynb` — verify satellite↔station matching
- `03_model_experiments.ipynb` — quick model iterations before promoting to `models/`
- `04_hcho_hotspots.ipynb` — visual comparison of PHV / Gi* / DBSCAN
- `05_transport_cases.ipynb` — case studies (e.g. Nov 2021 Punjab fires → Delhi)

Run `pip install -e .` once so `import isro_aqi` works inside notebooks.
