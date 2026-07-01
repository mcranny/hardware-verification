from __future__ import annotations

import numpy as np
import pytest

from hardware_verification.dut import AmplifierDUT, FirstOrderLagDUT, MovingAverageDUT
from hardware_verification.validation import FrequencyResponseTest, SettlingTimeTest, StepResponseTest, TestSpec, TestSuite
from hardware_verification.virtual_bench import VirtualBench


def test_step_response_reports_sane_values_for_memoryless_dut() -> None:
    bench = VirtualBench(n_samples=20_000, sample_rate=1_000_000.0)
    suite = TestSuite(
        "step",
        [
            StepResponseTest(
                bench,
                TestSpec(
                    "step",
                    {"overshoot": 0.01, "rise_time_us": 10.0},
                    {"kind": "square", "frequency": 1_000.0, "amplitude": 0.5, "rise_time": 2e-6, "fall_time": 2e-6},
                ),
            )
        ],
    )

    result = suite.run_all(AmplifierDUT(gain=1.0))

    assert result.passed
    assert 0.0 <= result.test_results[0].measurements["overshoot"] <= 0.01
    assert result.test_results[0].measurements["rise_time_us"] < 10.0


def test_settling_time_reports_real_dynamics() -> None:
    bench = VirtualBench(n_samples=20_000, sample_rate=1_000_000.0)
    suite = TestSuite(
        "settling",
        [
            SettlingTimeTest(
                bench,
                TestSpec(
                    "settling",
                    {"settling_time_us": 800.0},
                    {"kind": "pulse", "frequency": 100.0, "amplitude": 1.0, "duty_cycle": 0.5},
                    tolerance=0.02,
                ),
            )
        ],
    )

    result = suite.run_all(FirstOrderLagDUT(time_constant=50e-6))

    assert result.passed
    assert 100.0 < result.test_results[0].measurements["settling_time_us"] < 800.0


def test_settling_time_preserves_explicit_zero_tolerance() -> None:
    bench = VirtualBench(n_samples=20_000, sample_rate=1_000_000.0)
    suite = TestSuite(
        "settling",
        [
            SettlingTimeTest(
                bench,
                TestSpec(
                    "settling",
                    {"settling_time_us": 800.0},
                    {"kind": "pulse", "frequency": 100.0, "amplitude": 1.0, "duty_cycle": 0.5},
                    tolerance=0.0,
                ),
            )
        ],
    )

    with pytest.raises(ValueError, match="tolerance must be positive"):
        suite.run_all(FirstOrderLagDUT(time_constant=50e-6))


def test_step_response_negative_offset_boundary_case_stays_sane() -> None:
    bench = VirtualBench(n_samples=20_000, sample_rate=1_000_000.0)
    suite = TestSuite(
        "step",
        [
            StepResponseTest(
                bench,
                TestSpec(
                    "step",
                    {"overshoot": 1.0, "rise_time_us": 10.0},
                    {"kind": "square", "frequency": 1_000.0, "amplitude": 0.5, "rise_time": 2e-6, "fall_time": 2e-6},
                ),
            )
        ],
    )

    result = suite.run_all(AmplifierDUT(gain=1.0, offset=-0.001))

    assert result.passed
    assert np.isfinite(result.test_results[0].measurements["rise_time_us"])


def test_frequency_response_flat_amplifier_passes() -> None:
    bench = VirtualBench(n_samples=20_000, sample_rate=1_000_000.0)
    suite = TestSuite(
        "frequency",
        [
            FrequencyResponseTest(
                bench,
                TestSpec(
                    "flat",
                    {"frequencies_hz": [1_000.0, 10_000.0, 50_000.0], "target_gain": 2.0, "max_deviation_db": 0.05},
                    {"kind": "sine", "amplitude": 0.25},
                ),
            )
        ],
    )

    result = suite.run_all(AmplifierDUT(gain=2.0))

    assert result.passed
    assert result.test_results[0].measurements["max_deviation_db"] < 0.05


def test_frequency_response_allows_default_frequency_in_stimulus_params() -> None:
    bench = VirtualBench(n_samples=20_000, sample_rate=1_000_000.0)
    suite = TestSuite(
        "frequency",
        [
            FrequencyResponseTest(
                bench,
                TestSpec(
                    "flat",
                    {"frequencies_hz": [1_000.0, 10_000.0], "target_gain": 2.0, "max_deviation_db": 0.05},
                    {"kind": "sine", "frequency": 123.0, "amplitude": 0.25},
                ),
            )
        ],
    )

    result = suite.run_all(AmplifierDUT(gain=2.0))

    assert result.passed
    assert bench.function_generator.frequency == 10_000.0


def test_frequency_response_filter_shows_rolloff() -> None:
    bench = VirtualBench(n_samples=20_000, sample_rate=1_000_000.0)
    suite = TestSuite(
        "frequency",
        [
            FrequencyResponseTest(
                bench,
                TestSpec(
                    "filtered",
                    {"frequencies_hz": [1_000.0, 200_000.0], "target_gain": 1.0, "max_deviation_db": 0.1},
                    {"kind": "sine", "amplitude": 0.5},
                ),
            )
        ],
    )

    result = suite.run_all(MovingAverageDUT(window_size=8))

    assert not result.passed
    assert result.test_results[0].measurements["max_deviation_db"] > 3.0
