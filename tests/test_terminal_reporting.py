from __future__ import annotations

import builtins

from hardware_verification.monte_carlo import MonteCarloSummary
from hardware_verification.reporting import print_suite_summary, print_yield_summary
from hardware_verification.validation import PassFail, SuiteResult, TestResult


def test_print_suite_summary_outputs_key_fields(capsys) -> None:
    result = SuiteResult("demo", [TestResult("gain", PassFail.PASS, {"gain": 2.0}, {"gain_error_pct": 1.0})])

    print_suite_summary(result)

    captured = capsys.readouterr().out
    assert "demo" in captured
    assert "gain" in captured
    assert "PASS" in captured


def test_print_yield_summary_outputs_key_fields(capsys) -> None:
    print_yield_summary(MonteCarloSummary(10, 9, 90.0, {"gain": 10.0}, 3, {"gain_delta": 0.5}))

    captured = capsys.readouterr().out
    assert "Monte Carlo trials: 10" in captured
    assert "Yield: 90.00%" in captured


def test_print_suite_summary_plain_fallback(monkeypatch, capsys) -> None:
    real_import = builtins.__import__

    def fail_rich_import(name, *args, **kwargs):
        if name.startswith("rich"):
            raise ImportError("blocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_rich_import)
    result = SuiteResult("demo", [TestResult("gain", PassFail.FAIL, {"gain": 1.0}, {"gain_error_pct": 1.0})])

    print_suite_summary(result)

    captured = capsys.readouterr().out
    assert "Test Suite: demo" in captured
    assert "gain: FAIL" in captured
