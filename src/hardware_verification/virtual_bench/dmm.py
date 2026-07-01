from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .instruments import VirtualInstrument


@dataclass
class VirtualDMM(VirtualInstrument):
    """Benchtop digital multimeter model with range and reading error terms."""

    voltage_range: float = 10.0
    current_range: float = 1.0
    resistance_range: float = 10_000.0
    accuracy_pct_reading: float = 0.02
    accuracy_pct_range: float = 0.005
    noise_floor: float = 50e-6
    offset_error: float = 0.0
    gain_error: float = 0.0
    seed: int | None = None
    _rng: np.random.Generator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)

    def configure(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError(f"unknown DMM setting: {key}")
            setattr(self, key, value)
            if key == "seed":
                self._rng = np.random.default_rng(self.seed)

    def measure(self) -> float:
        return self.measure_dc_voltage(np.array([0.0]))

    def measure_dc_voltage(self, samples: np.ndarray) -> float:
        return self._apply_error(float(np.mean(samples)), self.voltage_range)

    def measure_ac_rms(self, samples: np.ndarray) -> float:
        centered = np.asarray(samples, dtype=float) - float(np.mean(samples))
        return max(0.0, self._apply_error(float(np.sqrt(np.mean(np.square(centered)))), self.voltage_range))

    def measure_dc_current(self, samples: np.ndarray, shunt_ohms: float = 1.0) -> float:
        if shunt_ohms <= 0:
            raise ValueError("shunt_ohms must be positive")
        return self._apply_error(float(np.mean(samples)) / shunt_ohms, self.current_range)

    def measure_ac_current_rms(self, samples: np.ndarray, shunt_ohms: float = 1.0) -> float:
        if shunt_ohms <= 0:
            raise ValueError("shunt_ohms must be positive")
        centered = np.asarray(samples, dtype=float) - float(np.mean(samples))
        current_rms = float(np.sqrt(np.mean(np.square(centered)))) / shunt_ohms
        return max(0.0, self._apply_error(current_rms, self.current_range))

    def measure_resistance(self, voltage_samples: np.ndarray, current_amps: float) -> float:
        if current_amps <= 0:
            raise ValueError("current_amps must be positive")
        return max(0.0, self._apply_error(float(np.mean(voltage_samples)) / current_amps, self.resistance_range))

    def reset(self) -> None:
        self._rng = np.random.default_rng(self.seed)

    def _apply_error(self, value: float, measurement_range: float) -> float:
        span_error = abs(value) * self.accuracy_pct_reading / 100.0
        range_error = measurement_range * self.accuracy_pct_range / 100.0
        systematic_error = self._rng.uniform(-(span_error + range_error), span_error + range_error)
        noise = self._rng.normal(0.0, self.noise_floor)
        return float((value + self.offset_error) * (1.0 + self.gain_error) + systematic_error + noise)
