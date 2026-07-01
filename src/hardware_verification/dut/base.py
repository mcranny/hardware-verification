from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class DUT(ABC):
    @abstractmethod
    def apply_input(self, signal: np.ndarray, sample_rate: float) -> None:
        """Apply a sampled input signal to the DUT."""

    @abstractmethod
    def get_output(self) -> np.ndarray:
        """Return the latest output signal."""

    @abstractmethod
    def reset(self) -> None:
        """Clear DUT runtime state."""
