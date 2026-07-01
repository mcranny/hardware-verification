from __future__ import annotations

from hardware_verification.dut import AmplifierDUT
from hardware_verification.validation import DCOffsetTest, GainTest, NoiseTest, TestSpec, TestSuite
from hardware_verification.virtual_bench import VirtualBench


def test_suite_runs_gain_noise_and_offset_checks() -> None:
    bench = VirtualBench(n_samples=20_000)
    suite = TestSuite(
        "amplifier",
        [
            GainTest(bench, TestSpec("gain", {"target_gain": 2.0, "gain_error_pct": 0.5}, {"kind": "sine", "amplitude": 0.5})),
            NoiseTest(bench, TestSpec("noise", {"noise_rms_mv": 1_420.0}, {"kind": "sine", "amplitude": 0.5})),
            DCOffsetTest(bench, TestSpec("offset", {"offset_mv": 2.0}, {"kind": "sine", "amplitude": 0.0})),
        ],
    )

    result = suite.run_all(AmplifierDUT(gain=2.0))

    assert result.passed
    assert [test.name for test in result.test_results] == ["gain", "noise", "offset"]


def test_gain_test_fails_when_margin_exceeds_limit() -> None:
    bench = VirtualBench(n_samples=20_000)
    suite = TestSuite(
        "amplifier",
        [GainTest(bench, TestSpec("gain", {"target_gain": 2.0, "gain_error_pct": 0.5}, {"kind": "sine", "amplitude": 0.5}))],
    )

    result = suite.run_all(AmplifierDUT(gain=1.8))

    assert not result.passed
    assert result.failed[0].measurements["gain_error_pct"] > 0.5
