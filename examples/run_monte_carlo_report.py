from __future__ import annotations

from hardware_verification import AmplifierDUT, MonteCarloEngine, TestSpec, TestSuite, VariationSpec, VirtualBench
from hardware_verification.monte_carlo import write_trial_records_csv
from hardware_verification.reporting import plot_sensitivity_tornado, plot_yield_distribution
from hardware_verification.validation import GainTest


def build_suite(bench: VirtualBench) -> TestSuite:
    return TestSuite(
        "Amplifier gain",
        [
            GainTest(
                bench,
                TestSpec("Gain", {"target_gain": 2.0, "gain_error_pct": 1.0}, {"kind": "sine", "amplitude": 0.5}),
            )
        ],
    )


def main() -> None:
    engine = MonteCarloEngine(
        bench_factory=lambda params: VirtualBench(n_samples=10_000),
        dut_factory=lambda params: AmplifierDUT(gain=2.0 + params["gain_delta"]),
        suite_factory=build_suite,
        variation_specs=[VariationSpec("gain_delta", "dut", "gain", "gaussian", mean=0.0, sigma=0.005)],
        seed=42,
    )
    records, summary = engine.run(200)
    write_trial_records_csv(records, "reports/generated/monte_carlo_trials.csv")
    plot_yield_distribution(records, "reports/generated/gain_distribution.png")
    plot_sensitivity_tornado(summary, "reports/generated/sensitivity.png")


if __name__ == "__main__":
    main()
