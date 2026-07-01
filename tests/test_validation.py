from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

import numpy as np
import pytest

from hardware_verification.dut import AmplifierDUT, DUT, VerilogDUT
from hardware_verification.validation import DCOffsetTest, GainTest, NoiseTest, PassFail, TestResult, TestSpec, TestSuite
from hardware_verification.virtual_bench import VirtualBench

RTL_ROOT = Path(__file__).resolve().parents[1] / "rtl"


def test_suite_runs_gain_noise_and_offset_checks() -> None:
    bench = VirtualBench(n_samples=20_000)
    suite = TestSuite(
        "amplifier",
        [
            GainTest(bench, TestSpec("gain", {"target_gain": 2.0, "gain_error_pct": 0.5}, {"kind": "sine", "amplitude": 0.5})),
            NoiseTest(bench, TestSpec("noise", {"noise_rms_mv": 2.0}, {"kind": "sine", "amplitude": 0.5})),
            DCOffsetTest(bench, TestSpec("offset", {"offset_mv": 2.0}, {"kind": "sine", "amplitude": 0.0})),
        ],
    )

    result = suite.run_all(AmplifierDUT(gain=2.0, noise_rms=0.0005, seed=123))

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


def test_gain_test_uses_unpadded_output_for_negative_offset_boundary_case() -> None:
    bench = VirtualBench(n_samples=20_000, sample_rate=1_000_000.0)
    suite = TestSuite(
        "amplifier",
        [GainTest(bench, TestSpec("gain", {"target_gain": 2.0, "gain_error_pct": 1.0}, {"kind": "sine", "frequency": 1_000.0, "amplitude": 0.5}))],
    )

    result = suite.run_all(AmplifierDUT(gain=2.0, offset=-0.001))

    assert result.passed
    assert result.test_results[0].measurements["gain"] == 2.0


def test_critical_failure_stops_suite_by_default() -> None:
    bench = VirtualBench(n_samples=20_000)
    suite = TestSuite(
        "critical",
        [
            GainTest(
                bench,
                TestSpec("critical gain", {"target_gain": 2.0, "gain_error_pct": 0.5}, {"kind": "sine", "amplitude": 0.5}, critical=True),
            ),
            NoiseTest(bench, TestSpec("noise", {"noise_rms_mv": 2.0}, {"kind": "sine", "amplitude": 0.5})),
        ],
    )

    result = suite.run_all(AmplifierDUT(gain=1.8))

    assert [test.name for test in result.test_results] == ["critical gain"]


def test_noise_test_forces_zero_amplitude_stimulus() -> None:
    bench = VirtualBench(n_samples=20_000)
    suite = TestSuite(
        "noise",
        [NoiseTest(bench, TestSpec("noise", {"noise_rms_mv": 2.0}, {"kind": "sine", "amplitude": 1.0, "offset": 0.2}))],
    )

    result = suite.run_all(AmplifierDUT(gain=10.0, noise_rms=0.0002, seed=123))

    assert result.passed
    assert bench.function_generator.amplitude == 0.0
    assert bench.function_generator.offset == 0.0


@dataclass
class IntegerPassthroughTest:
    bench: VirtualBench
    spec: TestSpec

    def run(self, dut: DUT) -> TestResult:
        del self
        signal = np.array([-200, -1, 0, 1, 200], dtype=int)
        dut.apply_input(signal, 1_000_000.0)
        passed = np.array_equal(dut.get_output(), signal)
        return TestResult("rtl integer passthrough", PassFail.PASS if passed else PassFail.FAIL, {}, {})


def test_suite_can_run_rtl_backed_dut_path() -> None:
    if shutil.which("iverilog") is None or shutil.which("vvp") is None:
        pytest.skip("Icarus Verilog is not installed")
    suite = TestSuite("rtl", [IntegerPassthroughTest(VirtualBench(n_samples=8), TestSpec("rtl integer passthrough", {}))])
    dut = VerilogDUT("fir_filter", [RTL_ROOT / "fir_filter.v"], parameters={"TAP_COUNT": 1, "COEFFS": [1]})

    result = suite.run_all(dut)

    assert result.passed
