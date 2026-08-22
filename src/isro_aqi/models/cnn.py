"""CNN for spatial feature extraction (Model 3).

Input: a (C, P, P) patch centred on the target cell, where C = number of
predictor channels and P = patch_size (odd, e.g. 15). The CNN learns spatial
context -- upwind sources, urban gradients, terrain -- that a tabular model
cannot see. Output: one value per target pollutant for the centre cell.
"""

from __future__ import annotations

import torch
from torch import nn


class PollutantCNN(nn.Module):
    def __init__(self, in_channels: int, n_targets: int, patch_size: int = 15):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(in_channels, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
        )
        self.head = nn.Sequential(
            nn.Flatten(), nn.Linear(128, 64), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64, n_targets),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # x: (B, C, P, P)
        return self.head(self.features(x))

    def embed(self, x: torch.Tensor) -> torch.Tensor:
        """128-d spatial embedding (used by the CNN-LSTM hybrid)."""
        return self.features(x).flatten(1)
