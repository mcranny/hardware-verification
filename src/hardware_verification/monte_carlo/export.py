from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .engine import TrialRecord


def trial_records_to_rows(records: Iterable[TrialRecord]) -> list[dict[str, float | str | bool | int]]:
    rows: list[dict[str, float | str | bool | int]] = []
    for record in records:
        base: dict[str, float | str | bool | int] = {
            "trial": record.index,
            "suite": record.result.name,
            "suite_passed": record.result.passed,
        }
        base.update({f"param.{name}": value for name, value in record.parameters.items()})
        if not record.result.test_results:
            rows.append({**base, "test": "", "test_status": "", "test_passed": ""})
            continue
        for test_result in record.result.test_results:
            row = {
                **base,
                "test": test_result.name,
                "test_status": test_result.status.value,
                "test_passed": test_result.passed,
            }
            row.update({f"measurement.{name}": value for name, value in test_result.measurements.items()})
            row.update({f"limit.{name}": value for name, value in test_result.limits.items()})
            rows.append(row)
    return rows


def write_trial_records_csv(records: Iterable[TrialRecord], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = trial_records_to_rows(records)
    fieldnames = _fieldnames(rows)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return path


def _fieldnames(rows: list[dict[str, float | str | bool | int]]) -> list[str]:
    leading = ["trial", "suite", "suite_passed", "test", "test_status", "test_passed"]
    discovered = sorted({key for row in rows for key in row if key not in leading})
    return leading + discovered
