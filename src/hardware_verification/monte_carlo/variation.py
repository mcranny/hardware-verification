from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

Distribution = Literal["gaussian", "uniform", "constant"]


@dataclass(frozen=True)
class VariationSpec:
    name: str
    target: Literal["bench", "dut"]
    parameter: str
    distribution: Distribution
    mean: float = 0.0
    sigma: float = 0.0
    minimum: float = 0.0
    maximum: float = 0.0
    value: float = 0.0

    def sample(self, rng: np.random.Generator) -> float:
        if self.distribution == "gaussian":
            return float(rng.normal(self.mean, self.sigma))
        if self.distribution == "uniform":
            return float(rng.uniform(self.minimum, self.maximum))
        if self.distribution == "constant":
            return float(self.value)
        raise ValueError(f"unsupported distribution: {self.distribution}")
