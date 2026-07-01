from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
from scope_sim import MeasurementEngine

from hardware_verification.dut import DUT
from hardware_verification.virtual_bench import VirtualBench

from .results import PassFail, TestResult
from .specs import TestSpec


@dataclass
class InstrumentTest(ABC):
    bench: VirtualBench
    spec: TestSpec

    def run(self, dut: DUT) -> TestResult:
        self._configure_stimulus()
        signal_path = self.bench.drive(dut)
        measurements = self.measure(signal_path)
        return self.evaluate(measurements)

    def _configure_stimulus(self) -> None:
        self.bench.function_generator.configure(**self.spec.stimulus_params)

    @abstractmethod
    def measure(self, signal_path) -> dict[str, float]:
        """Measure a driven signal path."""

    @abstractmethod
    def evaluate(self, measurements: dict[str, float]) -> TestResult:
        """Evaluate measurements against test limits."""


class GainTest(InstrumentTest):
    def measure(self, signal_path) -> dict[str, float]:
        record = self.bench.acquire_output(signal_path)
        output_vpp = MeasurementEngine(record).vpp()
        input_vpp = float(np.max(signal_path.input_samples) - np.min(signal_path.input_samples))
        gain = output_vpp / input_vpp if input_vpp else float("nan")
        return {"gain": gain}

    def evaluate(self, measurements: dict[str, float]) -> TestResult:
        target = self.spec.pass_criteria["target_gain"]
        error_pct = abs(measurements["gain"] - target) / abs(target) * 100.0
        limit = self.spec.pass_criteria["gain_error_pct"]
        status = PassFail.PASS if error_pct <= limit else PassFail.FAIL
        return TestResult(self.spec.name, status, {**measurements, "gain_error_pct": error_pct}, {"gain_error_pct": limit})


class NoiseTest(InstrumentTest):
    def measure(self, signal_path) -> dict[str, float]:
        noise_rms = self.bench.dmm.measure_ac_rms(signal_path.output_samples)
        return {"noise_rms": noise_rms, "noise_rms_mv": noise_rms * 1_000.0}

    def evaluate(self, measurements: dict[str, float]) -> TestResult:
        limit = self.spec.pass_criteria["noise_rms_mv"]
        status = PassFail.PASS if measurements["noise_rms_mv"] <= limit else PassFail.FAIL
        return TestResult(self.spec.name, status, measurements, {"noise_rms_mv": limit})


class DCOffsetTest(InstrumentTest):
    def measure(self, signal_path) -> dict[str, float]:
        offset = self.bench.dmm.measure_dc_voltage(signal_path.output_samples)
        return {"offset": offset, "offset_mv": offset * 1_000.0}

    def evaluate(self, measurements: dict[str, float]) -> TestResult:
        limit = self.spec.pass_criteria["offset_mv"]
        status = PassFail.PASS if abs(measurements["offset_mv"]) <= limit else PassFail.FAIL
        return TestResult(self.spec.name, status, measurements, {"offset_mv": limit})


class SettlingTimeTest(InstrumentTest):
    def measure(self, signal_path) -> dict[str, float]:
        record = self.bench.acquire_output(signal_path)
        settling_time = MeasurementEngine(record).settling_time(self.spec.tolerance or 0.02)
        return {"settling_time": settling_time, "settling_time_us": settling_time * 1_000_000.0}

    def evaluate(self, measurements: dict[str, float]) -> TestResult:
        limit = self.spec.pass_criteria["settling_time_us"]
        status = PassFail.PASS if measurements["settling_time_us"] <= limit else PassFail.FAIL
        return TestResult(self.spec.name, status, measurements, {"settling_time_us": limit})


class StepResponseTest(InstrumentTest):
    def measure(self, signal_path) -> dict[str, float]:
        record = self.bench.acquire_output(signal_path)
        engine = MeasurementEngine(record)
        return {"overshoot": engine.overshoot(), "rise_time": engine.rise_time(), "rise_time_us": engine.rise_time() * 1e6}

    def evaluate(self, measurements: dict[str, float]) -> TestResult:
        overshoot_limit = self.spec.pass_criteria["overshoot"]
        rise_limit = self.spec.pass_criteria["rise_time_us"]
        passed = measurements["overshoot"] <= overshoot_limit and measurements["rise_time_us"] <= rise_limit
        return TestResult(
            self.spec.name,
            PassFail.PASS if passed else PassFail.FAIL,
            measurements,
            {"overshoot": overshoot_limit, "rise_time_us": rise_limit},
        )


class FrequencyResponseTest(InstrumentTest):
    def run(self, dut: DUT) -> TestResult:
        frequencies = self.spec.pass_criteria["frequencies_hz"]
        target_gain = self.spec.pass_criteria["target_gain"]
        max_deviation_db = 0.0
        for frequency in frequencies:
            self.bench.function_generator.configure(**self.spec.stimulus_params, frequency=frequency)
            signal_path = self.bench.drive(dut)
            input_vpp = float(np.max(signal_path.input_samples) - np.min(signal_path.input_samples))
            output_vpp = float(np.max(signal_path.output_samples) - np.min(signal_path.output_samples))
            gain = output_vpp / input_vpp if input_vpp else float("nan")
            deviation_db = abs(20.0 * np.log10(max(gain, np.finfo(float).eps) / target_gain))
            max_deviation_db = max(max_deviation_db, float(deviation_db))
        return self.evaluate({"max_deviation_db": max_deviation_db})

    def measure(self, signal_path) -> dict[str, float]:
        del signal_path
        raise NotImplementedError("FrequencyResponseTest uses a sweep in run()")

    def evaluate(self, measurements: dict[str, float]) -> TestResult:
        limit = self.spec.pass_criteria["max_deviation_db"]
        status = PassFail.PASS if measurements["max_deviation_db"] <= limit else PassFail.FAIL
        return TestResult(self.spec.name, status, measurements, {"max_deviation_db": limit})
