from __future__ import annotations

from dataclasses import dataclass, field

from hardware_verification.dut import DUT

from .results import SuiteResult
from .test_cases import InstrumentTest


@dataclass
class TestSuite:
    __test__ = False

    name: str
    tests: list[InstrumentTest] = field(default_factory=list)
    stop_on_critical_failure: bool = True

    def add(self, test: InstrumentTest) -> None:
        self.tests.append(test)

    def run_all(self, dut: DUT) -> SuiteResult:
        results = []
        for test in self.tests:
            result = test.run(dut)
            results.append(result)
            if not result.passed and test.spec.critical and self.stop_on_critical_failure:
                break
        return SuiteResult(self.name, results)
