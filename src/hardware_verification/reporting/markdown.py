from __future__ import annotations

from hardware_verification.monte_carlo import MonteCarloSummary
from hardware_verification.validation import SuiteResult


def suite_to_markdown(result: SuiteResult) -> str:
    lines = [f"# Test Summary: {result.name}", "", "| Test | Status | Measurements | Limits |", "|---|---|---|---|"]
    for test in result.test_results:
        measurements = ", ".join(f"{key}={value:.6g}" for key, value in test.measurements.items())
        limits = ", ".join(f"{key}={value:.6g}" for key, value in test.limits.items())
        lines.append(f"| {test.name} | {test.status.value} | {measurements} | {limits} |")
    lines.extend(["", f"Overall: {'PASS' if result.passed else 'FAIL'}"])
    return "\n".join(lines)


def yield_to_markdown(summary: MonteCarloSummary) -> str:
    lines = [
        "# Monte Carlo Yield Summary",
        "",
        f"- Trials: {summary.trials}",
        f"- Passing trials: {summary.passed}",
        f"- Yield: {summary.yield_pct:.2f}%",
        f"- Worst-case trial: {summary.worst_case_trial}",
        "",
        "## Failure Rate",
    ]
    if summary.per_test_failure_rate:
        lines.extend(f"- {name}: {rate:.2f}%" for name, rate in summary.per_test_failure_rate.items())
    else:
        lines.append("- No failures")
    lines.append("")
    lines.append("## Sensitivity")
    if summary.sensitivity:
        lines.extend(f"- {name}: {value:.3f}" for name, value in summary.sensitivity.items())
    else:
        lines.append("- No sensitivity data")
    return "\n".join(lines)
