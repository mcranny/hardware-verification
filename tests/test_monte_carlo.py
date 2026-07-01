from __future__ import annotations

from hardware_verification.dut import AmplifierDUT
from hardware_verification.monte_carlo import MonteCarloEngine, VariationSpec
from hardware_verification.validation import GainTest, TestSpec, TestSuite
from hardware_verification.virtual_bench import VirtualBench


def test_monte_carlo_reports_yield_and_sensitivity() -> None:
    def suite_factory(bench: VirtualBench) -> TestSuite:
        return TestSuite(
            "gain",
            [GainTest(bench, TestSpec("gain", {"target_gain": 2.0, "gain_error_pct": 1.0}, {"kind": "sine", "amplitude": 0.5}))],
        )

    engine = MonteCarloEngine(
        bench_factory=lambda params: VirtualBench(n_samples=10_000),
        dut_factory=lambda params: AmplifierDUT(gain=2.0 + params["gain_delta"]),
        suite_factory=suite_factory,
        variation_specs=[VariationSpec("gain_delta", "dut", "gain", "gaussian", mean=0.0, sigma=0.005)],
        seed=42,
    )
    records, summary = engine.run(25)

    assert len(records) == 25
    assert 0.0 <= summary.yield_pct <= 100.0
    assert "gain_delta" in summary.sensitivity
