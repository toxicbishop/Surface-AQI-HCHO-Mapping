"""Preprocessing: turn heterogeneous downloads into a co-registered, QA-screened,
temporally-aggregated, station-collocated analysis dataset.

    regrid     -> one common lat/lon grid
    qa_filter  -> TROPOMI qa screening, valid-range clipping, outlier removal
    temporal   -> daily / monthly / seasonal / annual aggregation
    collocate  -> match grid cells to CPCB stations for supervised training
"""
