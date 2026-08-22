"""Surface-pollutant retrieval models (Phase 4/6).

Progression of complexity (each is a baseline for the next):
    baselines.RandomForestModel / XGBoostModel  -- tabular, fast, interpretable
    cnn.PollutantCNN                            -- per-frame spatial encoder (used by CNN-LSTM)
    cnn_lstm.PollutantCNNLSTM                   -- spatio-temporal trend learner (RECOMMENDED)

The trend learner feeds the hybrid (models/hybrid.py): C(s,t) = μ(s,t) + kriged-residual.

Targets: PM2.5, PM10, NO2, SO2, CO, O3 (multi-output regression).
"""
