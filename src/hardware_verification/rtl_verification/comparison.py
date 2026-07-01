from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ComparisonMetric:
    name: str
    value: float
    limit: float

    @property
    def passed(self) -> bool:
        return self.value <= self.limit


@dataclass(frozen=True)
class ComparisonReport:
    metrics: list[ComparisonMetric]

    @property
    def passed(self) -> bool:
        return all(metric.passed for metric in self.metrics)


def compare_waveforms(reference: np.ndarray, candidate: np.ndarray, *, max_abs_limit: float, mean_abs_limit: float) -> ComparisonReport:
    ref = np.asarray(reference, dtype=float)
    cand = np.asarray(candidate, dtype=float)
    if ref.shape != cand.shape:
        raise ValueError("reference and candidate waveforms must have the same shape")
    error = np.abs(ref - cand)
    return ComparisonReport(
        [
            ComparisonMetric("max_abs_error", float(np.max(error)), max_abs_limit),
            ComparisonMetric("mean_abs_error", float(np.mean(error)), mean_abs_limit),
        ]
    )
