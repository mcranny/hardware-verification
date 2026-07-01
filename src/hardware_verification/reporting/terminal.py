from __future__ import annotations

from hardware_verification.monte_carlo import MonteCarloSummary
from hardware_verification.validation import SuiteResult


def print_suite_summary(result: SuiteResult) -> None:
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        print(f"Test Suite: {result.name}")
        for test in result.test_results:
            print(f"{test.name}: {test.status.value} {test.measurements}")
        print(f"Overall: {'PASS' if result.passed else 'FAIL'}")
        return

    console = Console()
    table = Table(title=f"Test Suite: {result.name}")
    table.add_column("Test")
    table.add_column("Status")
    table.add_column("Measurements")
    for test in result.test_results:
        measurements = ", ".join(f"{key}={value:.6g}" for key, value in test.measurements.items())
        table.add_row(test.name, test.status.value, measurements)
    console.print(table)
    console.print(f"Overall: {'PASS' if result.passed else 'FAIL'}")


def print_yield_summary(summary: MonteCarloSummary) -> None:
    print(f"Monte Carlo trials: {summary.trials}")
    print(f"Yield: {summary.yield_pct:.2f}%")
    print(f"Worst-case trial: {summary.worst_case_trial}")
    print(f"Failure rates: {summary.per_test_failure_rate or 'none'}")
