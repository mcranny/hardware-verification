from __future__ import annotations

from hardware_verification import AmplifierDUT, MonteCarloEngine, TestSpec, TestSuite, VariationSpec, VirtualBench
from hardware_verification.reporting import print_suite_summary, print_yield_summary
from hardware_verification.validation import DCOffsetTest, GainTest, NoiseTest


def build_suite(bench: VirtualBench) -> TestSuite:
    return TestSuite(
        "Amplifier validation",
        [
            GainTest(
                bench,
                TestSpec(
                    "Gain",
                    {"target_gain": 2.0, "gain_error_pct": 1.0},
                    {"kind": "sine", "frequency": 1_000.0, "amplitude": 0.5},
                ),
            ),
            NoiseTest(
                bench,
                TestSpec(
                    "Noise",
                    {"noise_rms_mv": 1_420.0},
                    {"kind": "sine", "frequency": 1_000.0, "amplitude": 0.5},
                ),
            ),
            DCOffsetTest(bench, TestSpec("DC offset", {"offset_mv": 20.0}, {"kind": "sine", "amplitude": 0.0})),
        ],
    )


def main() -> None:
    bench = VirtualBench()
    dut = AmplifierDUT(gain=2.0, offset=0.0)
    result = build_suite(bench).run_all(dut)
    print_suite_summary(result)

    engine = MonteCarloEngine(
        bench_factory=lambda params: VirtualBench(),
        dut_factory=lambda params: AmplifierDUT(gain=2.0 + params["gain_delta"], offset=params["offset"]),
        suite_factory=build_suite,
        variation_specs=[
            VariationSpec("gain_delta", "dut", "gain", "gaussian", mean=0.0, sigma=0.005),
            VariationSpec("offset", "dut", "offset", "gaussian", mean=0.0, sigma=0.001),
        ],
        seed=7,
    )
    _, summary = engine.run(50)
    print_yield_summary(summary)


if __name__ == "__main__":
    main()
