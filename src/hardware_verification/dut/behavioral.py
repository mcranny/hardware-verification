from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scope_sim import ADCModel

from .base import DUT


@dataclass
class AmplifierDUT(DUT):
    gain: float = 1.0
    offset: float = 0.0
    saturation: float | None = None
    noise_rms: float = 0.0
    seed: int | None = None
    _output: np.ndarray = field(default_factory=lambda: np.array([], dtype=float), init=False)

    def apply_input(self, signal: np.ndarray, sample_rate: float) -> None:
        del sample_rate
        values = np.asarray(signal, dtype=float) * self.gain + self.offset
        if self.noise_rms:
            values = values + np.random.default_rng(self.seed).normal(0.0, self.noise_rms, size=values.shape)
        if self.saturation is not None:
            values = np.clip(values, -abs(self.saturation), abs(self.saturation))
        self._output = values

    def get_output(self) -> np.ndarray:
        return self._output.copy()

    def reset(self) -> None:
        self._output = np.array([], dtype=float)


@dataclass
class FIRFilterDUT(DUT):
    coefficients: np.ndarray
    coefficient_variation: float = 0.0
    seed: int | None = None
    _output: np.ndarray = field(default_factory=lambda: np.array([], dtype=float), init=False)

    def apply_input(self, signal: np.ndarray, sample_rate: float) -> None:
        del sample_rate
        coeffs = np.asarray(self.coefficients, dtype=float)
        if self.coefficient_variation:
            rng = np.random.default_rng(self.seed)
            coeffs = coeffs + rng.normal(0.0, self.coefficient_variation, size=coeffs.shape)
        self._output = np.convolve(np.asarray(signal, dtype=float), coeffs, mode="same")

    def get_output(self) -> np.ndarray:
        return self._output.copy()

    def reset(self) -> None:
        self._output = np.array([], dtype=float)


@dataclass
class MovingAverageDUT(DUT):
    window_size: int = 8
    _output: np.ndarray = field(default_factory=lambda: np.array([], dtype=float), init=False)

    def apply_input(self, signal: np.ndarray, sample_rate: float) -> None:
        del sample_rate
        if self.window_size <= 0:
            raise ValueError("window_size must be positive")
        kernel = np.ones(self.window_size, dtype=float) / self.window_size
        self._output = np.convolve(np.asarray(signal, dtype=float), kernel, mode="same")

    def get_output(self) -> np.ndarray:
        return self._output.copy()

    def reset(self) -> None:
        self._output = np.array([], dtype=float)


@dataclass
class ADCModelDUT(DUT):
    sample_rate: float
    bits: int = 12
    full_scale: float = 5.0
    gain_error: float = 0.0
    offset_error: float = 0.0
    enob: float | None = None
    aperture_jitter: float = 0.0
    seed: int | None = None
    _output: np.ndarray = field(default_factory=lambda: np.array([], dtype=float), init=False)

    def apply_input(self, signal: np.ndarray, sample_rate: float) -> None:
        time = np.arange(len(signal), dtype=float) / sample_rate
        _, self._output = ADCModel(
            sample_rate=self.sample_rate,
            bits=self.bits,
            full_scale=self.full_scale,
            gain_error=self.gain_error,
            offset_error=self.offset_error,
            enob=self.enob,
            aperture_jitter=self.aperture_jitter,
            seed=self.seed,
        ).convert(time, np.asarray(signal, dtype=float))

    def get_output(self) -> np.ndarray:
        return self._output.copy()

    def reset(self) -> None:
        self._output = np.array([], dtype=float)


@dataclass
class SignalProcessingChainDUT(DUT):
    stages: list[DUT]
    _output: np.ndarray = field(default_factory=lambda: np.array([], dtype=float), init=False)

    def apply_input(self, signal: np.ndarray, sample_rate: float) -> None:
        values = np.asarray(signal, dtype=float)
        for stage in self.stages:
            stage.apply_input(values, sample_rate)
            values = stage.get_output()
        self._output = values

    def get_output(self) -> np.ndarray:
        return self._output.copy()

    def reset(self) -> None:
        for stage in self.stages:
            stage.reset()
        self._output = np.array([], dtype=float)
