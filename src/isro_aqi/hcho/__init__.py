"""HCHO hotspot detection, attribution and transport (Objective 2).

Detection (two complementary methods -- "statistical thresholds or clustering"):
    phv             PHV = centre / mean(8 neighbours), >1 = anomaly [Dong et al. 2026]
    getis_ord       Getis-Ord Gi* statistically-significant clusters (FDR-corrected)

Interpretation:
    source_attribution   connected_clusters(mask) -> attribute: urban / industrial /
                         agri_burning / forest_fire / biogenic (IGP = anthropogenic-
                         dominated, Kuttippurath 2022)
    transport            ERA5 back-trajectories + VIIRS fire-pixel intersection
"""
