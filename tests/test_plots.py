from __future__ import annotations

import pytest

from hardware_verification.dut import AmplifierDUT
from hardware_verification.monte_carlo import MonteCarloEngine, VariationSpec
from hardware_verification.reporting import plot_sensitivity_tornado, plot_yield_distribution
from hardware_verification.validation import GainTest, TestSpec, TestSuite
from hardware_verification.virtual_bench import VirtualBench


pytest.importorskip("matplotlib")
pytest.importorskip("pandas")


def test_monte_carlo_plots_write_png_files(tmp_path) -> None:
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
    records, summary = engine.run(10)

    distribution = plot_yield_distribution(records, tmp_path / "gain.png")
    tornado = plot_sensitivity_tornado(summary, tmp_path / "sensitivity.png")

    assert distribution.stat().st_size > 1_000
    assert tornado.stat().st_size > 1_000
