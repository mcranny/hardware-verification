from __future__ import annotations

import numpy as np

from hardware_verification.reporting import suite_to_markdown, yield_to_markdown
from hardware_verification.rtl_verification import compare_integer_waveforms, compare_waveforms
from hardware_verification.validation import PassFail, SuiteResult, TestResult
from hardware_verification.monte_carlo import MonteCarloSummary


def test_markdown_reports_render_core_fields() -> None:
    suite = SuiteResult("demo", [TestResult("gain", PassFail.PASS, {"gain": 2.0}, {"gain_error_pct": 1.0})])
    summary = MonteCarloSummary(10, 9, 90.0, {"gain": 10.0}, 3, {"gain_delta": 0.5})

    assert "Overall: PASS" in suite_to_markdown(suite)
    assert "Yield: 90.00%" in yield_to_markdown(summary)


def test_waveform_comparison_reports_pass_fail_metrics() -> None:
    report = compare_waveforms(np.array([0.0, 1.0]), np.array([0.0, 1.01]), max_abs_limit=0.02, mean_abs_limit=0.02)

    assert report.passed
    assert report.sample_count == 2


def test_integer_waveform_comparison_reports_first_mismatch() -> None:
    report = compare_integer_waveforms(np.array([10, 20, 30]), np.array([10, 21, 35]))

    assert not report.passed
    assert report.first_mismatch_index == 1
    assert report.expected_value == 20
    assert report.actual_value == 21
    assert report.absolute_error == 1
    assert report.max_absolute_error == 5
    assert "first mismatch at index 1" in report.describe()


def test_integer_waveform_comparison_reports_length_mismatch() -> None:
    report = compare_integer_waveforms(np.array([1, 2, 3]), np.array([1, 2]))

    assert not report.passed
    assert not report.length_match
    assert report.sample_count == 2
