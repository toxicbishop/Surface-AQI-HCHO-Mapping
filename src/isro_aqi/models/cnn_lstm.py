"""CNN-LSTM spatio-temporal model (Model 5 -- RECOMMENDED).

Surface pollution depends on BOTH spatial behaviour (sources, terrain, transport)
and temporal behaviour (accumulation, photochemistry). This hybrid runs a shared
CNN over each day's spatial patch to get a per-day spatial embedding, then feeds
the sequence of embeddings to an LSTM for the temporal dynamics.

Input: (B, T, C, P, P) -- T daily patches per sample.
Output: (B, n_targets) -- pollutant concentrations for the centre cell on day T.
"""

from __future__ import annotations

import torch
from torch import nn

from isro_aqi.models.cnn import PollutantCNN


class PollutantCNNLSTM(nn.Module):
    def __init__(
        self,
        in_channels: int,
        n_targets: int,
        patch_size: int = 15,
        cnn_embed: int = 128,
        lstm_hidden: int = 128,
        lstm_layers: int = 2,
    ):
        super().__init__()
        # reuse the CNN feature extractor as a per-frame spatial encoder
        self.cnn = PollutantCNN(in_channels, n_targets, patch_size)
        self.lstm = nn.LSTM(
            input_size=cnn_embed,
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            batch_first=True,
            dropout=0.2 if lstm_layers > 1 else 0.0,
        )
        self.head = nn.Sequential(
            nn.Linear(lstm_hidden, 64), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64, n_targets),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # x: (B, T, C, P, P)
        b, t, c, p, _ = x.shape
        frames = x.view(b * t, c, p, p)
        emb = self.cnn.embed(frames).view(b, t, -1)   # (B, T, cnn_embed)
        out, _ = self.lstm(emb)
        return self.head(out[:, -1, :])
