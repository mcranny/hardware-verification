from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .base import DUT


@dataclass
class VerilogDUT(DUT):
    """Adapter boundary for an HDL simulation backend."""

    module_name: str
    source_files: list[Path]
    parameters: dict[str, int | float | str] = field(default_factory=dict)
    _input: np.ndarray = field(default_factory=lambda: np.array([], dtype=float), init=False)
    _output: np.ndarray = field(default_factory=lambda: np.array([], dtype=float), init=False)

    def apply_input(self, signal: np.ndarray, sample_rate: float) -> None:
        del sample_rate
        self._input = np.asarray(signal, dtype=float)
        self._output = self._input.copy()

    def get_output(self) -> np.ndarray:
        return self._output.copy()

    def reset(self) -> None:
        self._input = np.array([], dtype=float)
        self._output = np.array([], dtype=float)

    def run_cocotb(self) -> np.ndarray:
        try:
            import cocotb  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("cocotb is required for HDL simulation") from exc
        raise NotImplementedError("connect this adapter to a project-specific cocotb runner")
