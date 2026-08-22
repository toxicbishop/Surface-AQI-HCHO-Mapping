.PHONY: help setup auth demo demo-fast check-ingest real fetch-web ingest preprocess database train aqi hcho transport dashboard test lint clean

CONFIG ?= config/config.yaml
PY     := python3

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	 awk 'BEGIN {FS=":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup:        ## Install the package in editable mode
	pip install -e .

auth:         ## Authenticate Google Earth Engine (one-time)
	earthengine authenticate

demo:         ## Run the FULL pipeline end-to-end on synthetic data (no credentials)
	$(PY) pipelines/run_demo.py

demo-fast:    ## Quick smoke run of the full pipeline
	$(PY) pipelines/run_demo.py --fast

check-ingest: ## Show which ingestion deps / credentials / inputs are ready
	$(PY) pipelines/check_ingest.py

fetch-web:    ## Pull REAL TROPOMI/MODIS/ERA5 observation layers into the web app (no CPCB needed)
	$(PY) pipelines/fetch_real_web.py

real:         ## ONE-COMMAND real run: fetch GEE predictors + (with CPCB in data/external) train+validate -> real AQI
	$(PY) pipelines/run_real.py

ingest:       ## Phase 2: download all datasets (GEE + INSAT/MOSDAC + CPCB)
	$(PY) pipelines/01_ingest.py --config $(CONFIG)

preprocess:   ## Phase 4: regrid, QA-filter, temporally aggregate, collocate
	$(PY) pipelines/02_preprocess.py --config $(CONFIG)

database:     ## Phase 3: assemble the unified India-wide training table
	$(PY) pipelines/03_build_database.py --config $(CONFIG)

train:        ## Phases 6-7: train RF/XGB baselines (CNN-LSTM training lives in run_demo.py)
	$(PY) pipelines/04_train.py --config $(CONFIG)

aqi:          ## [scaffold] Phases 5,8,9 stub — the real AQI run is `make demo` / `make real`
	$(PY) pipelines/05_generate_aqi.py --config $(CONFIG)

hcho:         ## [scaffold] Phases 10,11 stub — the real HCHO run is `make demo` / `make fetch-web`
	$(PY) pipelines/06_hcho_analysis.py --config $(CONFIG)

transport:    ## [scaffold] Phase 13 stub — the real transport run is `make demo` / `make fetch-web`
	$(PY) pipelines/07_transport.py --config $(CONFIG)

dashboard:    ## Launch the Streamlit dashboard
	streamlit run dashboard/app.py

test:         ## Run unit tests (AQI engine, PHV, Getis-Ord are fully tested)
	pytest -q

lint:         ## Lint with ruff
	ruff check src pipelines tests

clean:        ## Remove caches and interim artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache
