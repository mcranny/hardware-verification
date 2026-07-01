from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .dmm import VirtualDMM
from .instruments import VirtualFunctionGenerator, VirtualOscilloscope


@dataclass
class SignalPath:
    input_time: np.ndarray
    input_samples: np.ndarray
    output_samples: np.ndarray
    sample_rate: float


@dataclass
class VirtualBench:
    function_generator: VirtualFunctionGenerator = field(default_factory=VirtualFunctionGenerator)
    oscilloscope: VirtualOscilloscope = field(default_factory=VirtualOscilloscope)
    dmm: VirtualDMM = field(default_factory=VirtualDMM)
    sample_rate: float = 1_000_000.0
    n_samples: int = 20_000

    def reset(self) -> None:
        self.function_generator.reset()
        self.oscilloscope.reset()
        self.dmm.reset()

    def drive(self, dut) -> SignalPath:
        time, stimulus = self.function_generator.generate(self.n_samples, self.sample_rate)
        dut.apply_input(stimulus, self.sample_rate)
        output = dut.get_output()
        return SignalPath(time, stimulus, output, self.sample_rate)

    def acquire_output(self, signal_path: SignalPath):
        return self.oscilloscope.acquire(signal_path.output_samples, signal_path.sample_rate)
