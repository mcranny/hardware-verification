from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PassFail(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class TestResult:
    __test__ = False

    name: str
    status: PassFail
    measurements: dict[str, float]
    limits: dict[str, float]
    message: str = ""

    @property
    def passed(self) -> bool:
        return self.status == PassFail.PASS


@dataclass(frozen=True)
class SuiteResult:
    name: str
    test_results: list[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.test_results) and all(result.passed for result in self.test_results)

    @property
    def failed(self) -> list[TestResult]:
        return [result for result in self.test_results if not result.passed]

    def measurement_table(self) -> list[dict[str, float | str]]:
        rows: list[dict[str, float | str]] = []
        for result in self.test_results:
            row: dict[str, float | str] = {"test": result.name, "status": result.status.value}
            row.update(result.measurements)
            rows.append(row)
        return rows
