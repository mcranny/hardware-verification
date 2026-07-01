from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scope_sim import AcquisitionRecord, MeasurementEngine, OscilloscopeEngine, WaveformGenerator

WAVEFORM_EXTRA_SETTINGS = frozenset({"rise_time", "fall_time", "arbitrary_samples"})


class VirtualInstrument(ABC):
    """Common interface for virtual bench instruments."""

    @abstractmethod
    def configure(self, **kwargs: Any) -> None:
        """Update instrument settings."""

    @abstractmethod
    def measure(self) -> float | np.ndarray | dict[str, float]:
        """Return the current measurement."""

    @abstractmethod
    def reset(self) -> None:
        """Restore runtime state."""


@dataclass
class VirtualFunctionGenerator(VirtualInstrument):
    kind: str = "sine"
    frequency: float = 1_000.0
    amplitude: float = 1.0
    offset: float = 0.0
    duty_cycle: float = 0.5
    output_enabled: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def configure(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if key in WAVEFORM_EXTRA_SETTINGS:
                self.extra[key] = value
            elif hasattr(self, key) and key != "extra":
                setattr(self, key, value)
            else:
                raise AttributeError(f"unknown function generator setting: {key}")

    def set_waveform(self, kind: str, **kwargs: Any) -> None:
        self.kind = kind
        self.configure(**kwargs)

    def set_frequency(self, frequency: float) -> None:
        self.frequency = frequency

    def set_amplitude(self, amplitude: float) -> None:
        self.amplitude = amplitude

    def enable_output(self, enabled: bool = True) -> None:
        self.output_enabled = enabled

    def generate(self, n_samples: int, sample_rate: float) -> tuple[np.ndarray, np.ndarray]:
        time, samples = WaveformGenerator(
            kind=self.kind,
            frequency=self.frequency,
            amplitude=self.amplitude,
            offset=self.offset,
            duty_cycle=self.duty_cycle,
            **self.extra,
        ).generate(n_samples, sample_rate)
        if not self.output_enabled:
            samples = np.zeros_like(samples)
        return time, samples

    def measure(self) -> np.ndarray:
        _, samples = self.generate(1_000, 1_000_000.0)
        return samples

    def reset(self) -> None:
        self.output_enabled = False


@dataclass
class VirtualOscilloscope(VirtualInstrument):
    time_per_div: float = 100e-6
    divisions: int = 10
    trigger_level: float = 0.0
    trigger_edge: str = "rising"
    pre_trigger_fraction: float = 0.5
    bandwidth_limit: float | None = None
    _last_record: AcquisitionRecord | None = field(default=None, init=False)

    def configure(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError(f"unknown oscilloscope setting: {key}")
            setattr(self, key, value)

    def set_timebase(self, time_per_div: float, divisions: int | None = None) -> None:
        self.time_per_div = time_per_div
        if divisions is not None:
            self.divisions = divisions

    def set_bandwidth(self, bandwidth_limit: float | None) -> None:
        self.bandwidth_limit = bandwidth_limit

    def acquire(self, samples: np.ndarray, sample_rate: float) -> AcquisitionRecord:
        scope = OscilloscopeEngine(
            time_per_div=self.time_per_div,
            divisions=self.divisions,
            trigger_level=self.trigger_level,
            trigger_edge=self.trigger_edge,
            pre_trigger_fraction=self.pre_trigger_fraction,
            bandwidth_limit=self.bandwidth_limit,
        )
        self._last_record = scope.acquire(samples, sample_rate)
        return self._last_record

    def measure(self) -> dict[str, float]:
        if self._last_record is None:
            raise RuntimeError("no acquisition is available")
        return MeasurementEngine(self._last_record).all()

    def reset(self) -> None:
        self._last_record = None
