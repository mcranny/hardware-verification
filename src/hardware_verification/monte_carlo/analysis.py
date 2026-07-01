from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MonteCarloSummary:
    trials: int
    passed: int
    yield_pct: float
    per_test_failure_rate: dict[str, float]
    worst_case_trial: int | None
    sensitivity: dict[str, float]
