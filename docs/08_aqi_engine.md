# Phase 8 — CPCB AQI Engine

Deterministic, fully unit-tested engine that converts gridded pollutant concentrations into the CPCB (2014) National Air Quality Index, with an optional Shannon-entropy aggregation [D] for publishable comparison.

## Objectives
- Implement the CPCB 2014 six-category AQI exactly: piecewise-linear sub-indices and the max-of-sub-indices overall AQI [C][D].
- Enforce CPCB validity (≥3 pollutants, at least one of PM2.5/PM10) and the correct averaging windows.
- Expose category labels and the official colour ramp for the Phase 9 atlas.
- Provide an entropy-based alternative (RAPI [D]) that accounts for co-occurring pollutants, since pure max ignores them.

## Scientific rationale
The max rule reports only the single worst pollutant, so two cells with very different multi-pollutant burdens can share an AQI. Lu et al. 2011 [D] critique this and propose Shannon-entropy weighting (RAPI); in Hong Kong RSP and NO2 dominate, mirroring PM2.5/NO2 dominance over India. Wang et al. 2023 [C] adopt the same interpolation-then-max construction, anchoring our engine to peer-reviewed practice while letting us publish a max-vs-entropy comparison.

## Input datasets
- **CPCB ground stations** (`ingestion/cpcb.py`) — 24-h means for PM2.5/PM10/NO2/SO2/NH3, 8-h max for CO/O3; ground truth.
- **Satellite/reanalysis surface estimates** — model-predicted surface concentrations on the India grid (Phases 4–7) feeding `compute_frame`.
- **`config/aqi_breakpoints.yaml`** — CPCB breakpoints, categories (`#00B050`→`#7E0023`), `mandatory`, `min_pollutants`, averaging windows.

## Algorithm / workflow
1. Resample each pollutant to its CPCB averaging window (24-h mean or 8-h rolling max).
2. Interpolate each concentration to its sub-index against the breakpoint table.
3. Drop invalid/NaN pollutants; check validity (≥3 present incl. PM2.5/PM10).
4. Overall AQI = max sub-index; record the dominant pollutant and category.
5. Optionally compute entropy aggregation for comparison.

## Mathematical formulation
Sub-index by piecewise-linear interpolation [C][D]:
```
I_p = (I_hi − I_lo)/(BP_hi − BP_lo) · (C_p − BP_lo) + I_lo
```
Overall AQI [C], CPCB:
```
AQI = max_p I_p        (valid iff ≥3 sub-indices AND PM2.5∈p OR PM10∈p)
```
Shannon-entropy aggregation (RAPI, Lu et al. 2011 [D]):
```
p_k = I_k / Σ_j I_j
H   = −Σ_k p_k ln p_k / ln(K)        (normalised, K = #sub-indices)
RAPI = max(I) · (1 + (mean(I)/max(I))·H)
```

## Python libraries
`numpy`, `pandas` (vectorised `compute_frame`), `pyyaml` (config), `math`. No GEE dependency — the engine runs locally and deterministically.

## Code in this repo
`src/isro_aqi/aqi/engine.py` — module fn `sub_index`; class `AQIEngine` (`sub_indices`, `aqi`, `category`, `color`, `compute_frame`, `aggregate_entropy`). Tested in `tests/test_aqi.py`; driven by `pipelines/05_generate_aqi.py`.

```python
def sub_index(conc, breakpoints):
    for c_lo, c_hi, i_lo, i_hi in breakpoints:
        if c_lo <= conc <= c_hi:
            return (i_hi - i_lo)/(c_hi - c_lo)*(conc - c_lo) + i_lo
    return float(breakpoints[-1][3])      # cap at top band

def aqi(self, concentrations):
    si = self.sub_indices(concentrations)
    if len(si) < self.min_pollutants or not any(m in si for m in self.mandatory):
        return None, None, None
    dominant = max(si, key=si.get)
    return si[dominant], dominant, self.category(si[dominant])
```

## Expected outputs
- Per-cell `aqi`, `aqi_dominant`, `aqi_category` columns/rasters over the India grid.
- A dominant-pollutant map (which pollutant drives AQI where).
- Parallel `aqi_entropy` (RAPI) field for the max-vs-entropy comparison.

## Potential challenges & mitigations
- **Unit mismatches** (CO in mg/m³, others µg/m³) → units fixed per-pollutant in the YAML; CO row uses mg/m³ breakpoints.
- **Sparse pollutants** → validity gate returns `None` rather than a misleading low AQI.
- **Above-top concentrations** → capped at the top sub-index (500) instead of extrapolating.
- **Averaging-window errors** → enforce 24-h mean vs 8-h max from the config, not ad hoc.

## Validation metrics
- Cell-level AQI vs CPCB station AQI: RMSE, MAE, bias, R²; per-category confusion matrix and weighted κ (penalising adjacent-band errors).
- Dominant-pollutant agreement (%) with CPCB.
- Max-vs-entropy: divergence statistics and category-shift frequency under multi-pollutant co-occurrence.

## Publication-quality figures
- CPCB six-band sub-index curves for all pollutants.
- Scatter of engine AQI vs CPCB AQI with 1:1 line and category bands.
- National dominant-pollutant choropleth.
- Side-by-side max-AQI vs entropy-AQI maps highlighting where they diverge.
