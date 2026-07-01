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
    sample_count: int
    length_match: bool
    first_mismatch_index: int | None = None
    expected_value: float | int | None = None
    actual_value: float | int | None = None
    absolute_error: float | None = None

    @property
    def passed(self) -> bool:
        return self.length_match and all(metric.passed for metric in self.metrics)


def compare_waveforms(reference: np.ndarray, candidate: np.ndarray, *, max_abs_limit: float, mean_abs_limit: float) -> ComparisonReport:
    ref = np.asarray(reference, dtype=float)
    cand = np.asarray(candidate, dtype=float)
    if ref.shape != cand.shape:
        raise ValueError("reference and candidate waveforms must have the same shape")
    error = np.abs(ref - cand)
    mismatch_indices = np.flatnonzero(error > max_abs_limit)
    first_mismatch_index = int(mismatch_indices[0]) if mismatch_indices.size else None
    expected_value = float(ref[first_mismatch_index]) if first_mismatch_index is not None else None
    actual_value = float(cand[first_mismatch_index]) if first_mismatch_index is not None else None
    absolute_error = float(error[first_mismatch_index]) if first_mismatch_index is not None else None
    return ComparisonReport(
        metrics=[
            ComparisonMetric("max_abs_error", float(np.max(error)), max_abs_limit),
            ComparisonMetric("mean_abs_error", float(np.mean(error)), mean_abs_limit),
        ],
        sample_count=int(ref.size),
        length_match=True,
        first_mismatch_index=first_mismatch_index,
        expected_value=expected_value,
        actual_value=actual_value,
        absolute_error=absolute_error,
    )


@dataclass(frozen=True)
class IntegerWaveformReport:
    length_match: bool
    sample_count: int
    first_mismatch_index: int | None
    expected_value: int | None
    actual_value: int | None
    absolute_error: int | None
    max_absolute_error: int
    mean_absolute_error: float

    @property
    def passed(self) -> bool:
        return self.length_match and self.first_mismatch_index is None

    def describe(self) -> str:
        if self.passed:
            return f"integer waveforms matched for {self.sample_count} samples"
        if not self.length_match:
            return f"length mismatch while comparing {self.sample_count} samples"
        return (
            f"first mismatch at index {self.first_mismatch_index}: "
            f"expected {self.expected_value}, actual {self.actual_value}, "
            f"abs_error {self.absolute_error}, max_abs_error {self.max_absolute_error}"
        )


def compare_integer_waveforms(reference: np.ndarray, candidate: np.ndarray) -> IntegerWaveformReport:
    ref = np.asarray(reference, dtype=np.int64).reshape(-1)
    cand = np.asarray(candidate, dtype=np.int64).reshape(-1)
    sample_count = int(min(ref.size, cand.size))
    if ref.shape != cand.shape:
        return IntegerWaveformReport(
            length_match=False,
            sample_count=sample_count,
            first_mismatch_index=None,
            expected_value=None,
            actual_value=None,
            absolute_error=None,
            max_absolute_error=0,
            mean_absolute_error=0.0,
        )
    error = np.abs(ref - cand)
    mismatch_indices = np.flatnonzero(error)
    first_mismatch_index = int(mismatch_indices[0]) if mismatch_indices.size else None
    return IntegerWaveformReport(
        length_match=True,
        sample_count=int(ref.size),
        first_mismatch_index=first_mismatch_index,
        expected_value=int(ref[first_mismatch_index]) if first_mismatch_index is not None else None,
        actual_value=int(cand[first_mismatch_index]) if first_mismatch_index is not None else None,
        absolute_error=int(error[first_mismatch_index]) if first_mismatch_index is not None else None,
        max_absolute_error=int(np.max(error)) if error.size else 0,
        mean_absolute_error=float(np.mean(error)) if error.size else 0.0,
    )
