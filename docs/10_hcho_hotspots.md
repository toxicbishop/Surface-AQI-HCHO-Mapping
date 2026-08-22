# Phase 10 — HCHO Hotspot Detection (PHV / Getis-Ord Gi* / connected-component clusters)

Detect localised tropospheric HCHO enhancements over India from Sentinel-5P/TROPOMI, with PHV at 1 km as the flagship [A].

> **Note:** the DBSCAN and P95 detectors described in earlier drafts were removed in the
> redesign. Clustering is now done with **scipy connected-components** on the significant-cell
> mask (`hcho/source_attribution.py`).

## Objectives
- Map HCHO High-Value Areas (HVAs) and statistically-significant clusters over India.
- Cross-validate the detectors — PHV [A] and Getis-Ord Gi* — and reconcile their flags.
- Hand significant clusters (centroids) to source attribution (urban/industrial/biomass per `config/regions.yaml`).

## Scientific rationale
HCHO is a short-lived VOC-oxidation product; localised columns mark fresh VOC sources (traffic, industry, fires). Dong et al. 2026 [A] show HVAs concentrate in VOC-limited zones and that a percentage-higher-than-vicinity ratio isolates local anomalies far better than absolute thresholds. Single-pixel TROPOMI retrievals are noisy, so we add spatial-significance (Gi*) and group significant cells into clusters via scipy connected-components.

## Input datasets
- **TROPOMI HCHO L3** (`COPERNICUS/S5P/OFFL/L3_HCHO`, `tropospheric_HCHO_column_number_density`, mol/m²), screened **qa_value > 0.75**, composited to daily/monthly/seasonal means.
- **`config/regions.yaml`** — urban/industrial/burning bboxes for attribution.

## Algorithm / workflow
1. QA-filter (qa>0.75) and composite HCHO to the chosen grid; convert mol/m² → molec/cm² (×6.022e19).
2. **PHV** [A]: ratio of each cell to its 8-neighbour mean; HVA = PHV>1 AND column ≥ 1e16; optional mutation/change-detection vs a reference field.
3. **Gi***: distance-band Gi* z-scores with Benjamini-Hochberg FDR → significant high clusters.
4. **Connected-component clustering**: group significant cells into contiguous clusters with centroids (scipy `ndimage.label`).
5. Overlay PHV + Gi* + clusters; export hotspot tables for attribution.

### Method comparison
| Method | Unit | Strength | Weakness | When to use |
|---|---|---|---|---|
| **PHV [A]** | cell | Scale-aware local anomaly; physically interpretable ratio | No significance test; sensitive to grid choice | **Flagship** HVA mapping at 1 km |
| Gi* | cell | Statistical significance + FDR; noise-robust | Bandwidth sensitive; heavier compute | Confirm PHV flags are not noise |
| Connected-components | cluster | Groups significant cells → centroids for attribution; parameter-free | Requires a thresholded mask first | Convert flagged cells into source objects |

### Why PHV at 1 km is the flagship
Dong et al. 2026 [A] find 0.01° (~1 km) optimal: 0.5 km over-fits TROPOMI retrieval noise, 2 km smooths real anomalies away. The **mutation/change-detection** refinement is decisive — it cut HVA candidates **60,042 → 4,431 (−92.6%)** and raised factory/HVA query accuracy **5.38% → 41.32%**, with per-year PHV% ≈ 5–13%. PHV is thus both selective and attributable. Gi* and connected-component clustering are methodological extensions, not paper methods.

## Mathematical formulation
PHV ratio [A] (`>1` ⇒ local anomaly):
```
PHV(i,j) = C(i,j) / [ (1/8) Σ_{8 Moore neighbours} C ]
HVA = (PHV > 1) AND (C ≥ 1×10¹⁶ molec/cm²)
mutation-confirmed: (C / C_ref) > mutation_factor (≈1.2)
```
Getis-Ord Gi* z-score (extension):
```
Gi*(i) = [ Σ_j w_ij x_j − X̄ Σ_j w_ij ] / [ S · sqrt( (n Σ_j w_ij² − (Σ_j w_ij)²)/(n−1) ) ]
S = sqrt( Σ_j x_j²/n − X̄² );  hotspot ⇔ p_BH < α AND z>0
```
Connected-component clustering (extension): label contiguous runs of significant cells (4-/8-connectivity) into clusters; each cluster reduces to a centroid + cell count for attribution.

## Python libraries
`xarray`, `numpy`, `pandas`; `esda` + `libpysal` (Gi*, DistanceBand); `scipy.ndimage` (connected components). Tested with `pytest`.

## Code in this repo
`src/isro_aqi/hcho/phv.py` (`phv_field`, `detect_hotspots` → `phv`/`hva`/`hva_confirmed`, `phv_percent`), `getis_ord.py` (`gi_star`, `summarise`, `_benjamini_hochberg`), `source_attribution.py` (`connected_clusters` + `attribute`). Tests: `test_phv.py`, `test_getis_ord.py`. Driver: `pipelines/06_hcho_analysis.py`.

```python
def phv_field(hcho):
    neighbour_mean = np.nanmean(moore_neighbourhood(hcho), axis=0)
    return hcho / neighbour_mean        # PHV > 1 ⇒ local anomaly

hva = (phv > phv_min) & (values >= hva_threshold)   # 1e16 molec/cm²
ds["hva_confirmed"] = hva & ((values / ref) > mutation_factor)
```

## Expected outputs
- PHV field + HVA / mutation-confirmed masks; per-scene PHV% (≈5–13%).
- Gi* z/p/hotspot rasters (FDR-corrected); connected-component cluster table (centroid, n_cells, hcho_mean).
- Consensus hotspot table feeding attribution.

## Potential challenges & mitigations
- **Retrieval noise** → qa>0.75, 1 km grid, mutation step, Gi* significance.
- **Grid sensitivity** → fix 0.01° per [A]; report PHV% stability.
- **Cluster threshold** → set the significant-cell mask carefully; sensitivity sweep.
- **Multiple comparisons in Gi*** → Benjamini-Hochberg FDR.

## Validation metrics
- Candidate reduction % (target ≈−92.6% [A]); attribution query accuracy.
- Inter-method overlap (Jaccard / Cohen's κ) PHV vs Gi*.
- Hotspot ↔ known-source coincidence rate using `regions.yaml`.

## Publication-quality figures
- HCHO column map with PHV-HVA overlay (`hcho_map`).
- PHV / Gi* / cluster-overlay comparison over the IGP–industrial belt.
- Candidate-reduction bar (raw vs mutation-confirmed).
- Seasonal PHV% time series.
