from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from hardware_verification.dut import DUT
from hardware_verification.validation import TestSuite
from hardware_verification.validation.results import SuiteResult
from hardware_verification.virtual_bench import VirtualBench

from .analysis import MonteCarloSummary
from .variation import VariationSpec


@dataclass(frozen=True)
class TrialRecord:
    index: int
    parameters: dict[str, float]
    result: SuiteResult


class MonteCarloEngine:
    def __init__(
        self,
        bench_factory: Callable[[dict[str, float]], VirtualBench],
        dut_factory: Callable[[dict[str, float]], DUT],
        suite_factory: Callable[[VirtualBench], TestSuite],
        variation_specs: list[VariationSpec],
        seed: int | None = None,
    ) -> None:
        self.bench_factory = bench_factory
        self.dut_factory = dut_factory
        self.suite_factory = suite_factory
        self.variation_specs = variation_specs
        self.seed = seed

    def run(self, trials: int) -> tuple[list[TrialRecord], MonteCarloSummary]:
        if trials <= 0:
            raise ValueError("trials must be positive")
        rng = np.random.default_rng(self.seed)
        records: list[TrialRecord] = []
        for index in range(trials):
            params = {spec.name: spec.sample(rng) for spec in self.variation_specs}
            bench = self.bench_factory(self._target_params(params, "bench"))
            dut = self.dut_factory(self._target_params(params, "dut"))
            suite = self.suite_factory(bench)
            result = suite.run_all(dut)
            if not result.test_results:
                raise ValueError("test suite produced no test results")
            records.append(TrialRecord(index, params, result))
        return records, self.summarize(records)

    def _target_params(self, params: dict[str, float], target: str) -> dict[str, float]:
        return {spec.name: params[spec.name] for spec in self.variation_specs if spec.target == target}

    def summarize(self, records: list[TrialRecord]) -> MonteCarloSummary:
        passed = sum(record.result.passed for record in records)
        failure_counts: dict[str, int] = {}
        worst_index: int | None = None
        worst_failure_count = -1
        for record in records:
            failures = record.result.failed
            if len(failures) > worst_failure_count:
                worst_failure_count = len(failures)
                worst_index = record.index
            for failure in failures:
                failure_counts[failure.name] = failure_counts.get(failure.name, 0) + 1

        per_test_failure_rate = {name: count / len(records) * 100.0 for name, count in failure_counts.items()}
        return MonteCarloSummary(
            trials=len(records),
            passed=passed,
            yield_pct=passed / len(records) * 100.0,
            per_test_failure_rate=per_test_failure_rate,
            worst_case_trial=worst_index,
            sensitivity=self._sensitivity(records),
        )

    def _sensitivity(self, records: list[TrialRecord]) -> dict[str, float]:
        if len(records) < 2 or not self.variation_specs:
            return {}
        pass_vector = np.asarray([1.0 if record.result.passed else 0.0 for record in records])
        if np.all(pass_vector == pass_vector[0]):
            return {spec.name: 0.0 for spec in self.variation_specs}
        sensitivity: dict[str, float] = {}
        for spec in self.variation_specs:
            values = np.asarray([record.parameters[spec.name] for record in records], dtype=float)
            if np.allclose(values, values[0]):
                sensitivity[spec.name] = 0.0
            else:
                sensitivity[spec.name] = float(abs(np.corrcoef(values, pass_vector)[0, 1]))
        return sensitivity
