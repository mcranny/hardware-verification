from __future__ import annotations

from dataclasses import dataclass, field
from importlib.util import find_spec
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np

from .base import DUT


@dataclass
class VerilogDUT(DUT):
    """Verilog DUT adapter backed by local HDL simulation."""

    module_name: str
    source_files: list[Path]
    parameters: dict[str, int | float | str] = field(default_factory=dict)
    _input: np.ndarray = field(default_factory=lambda: np.array([], dtype=float), init=False)
    _output: np.ndarray = field(default_factory=lambda: np.array([], dtype=float), init=False)

    def apply_input(self, signal: np.ndarray, sample_rate: float) -> None:
        del sample_rate
        self._input = np.asarray(signal, dtype=float)
        self._output = self.simulate(self._input)

    def get_output(self) -> np.ndarray:
        return self._output.copy()

    def reset(self) -> None:
        self._input = np.array([], dtype=float)
        self._output = np.array([], dtype=float)

    def simulate(self, signal: np.ndarray) -> np.ndarray:
        if self.module_name != "dsp_block":
            raise NotImplementedError("VerilogDUT currently supports dsp_block simulation")
        if shutil.which("iverilog") is None or shutil.which("vvp") is None:
            raise RuntimeError("Icarus Verilog tools 'iverilog' and 'vvp' are required for HDL simulation")
        if find_spec("cocotb_tools.runner") is None:
            raise RuntimeError("cocotb and cocotb_tools are required for HDL simulation")
        return self._simulate_dsp_block(np.asarray(signal, dtype=int))

    def run_cocotb(self) -> np.ndarray:
        return self.simulate(self._input)

    def _simulate_dsp_block(self, samples: np.ndarray) -> np.ndarray:
        data_width = int(self.parameters.get("DATA_WIDTH", 16))
        gain_q15 = int(self.parameters.get("GAIN_Q15", (1 << 15) - 1))
        offset = int(self.parameters.get("OFFSET", 0))
        samples = np.asarray(samples, dtype=int)
        min_value = -(1 << (data_width - 1))
        max_value = (1 << (data_width - 1)) - 1
        if np.any(samples < min_value) or np.any(samples > max_value):
            raise ValueError(f"dsp_block samples must fit signed {data_width}-bit range")

        from cocotb_tools.runner import get_runner

        with tempfile.TemporaryDirectory(prefix="hardware_verification_rtl_") as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "input.json"
            output_path = tmp_path / "output.json"
            input_path.write_text(json.dumps([int(sample) for sample in samples]), encoding="utf-8")
            runner = get_runner("icarus")
            runner.build(
                sources=[str(Path(source)) for source in self.source_files],
                hdl_toplevel="dsp_block",
                parameters={"DATA_WIDTH": data_width, "GAIN_Q15": gain_q15, "OFFSET": offset},
                build_dir=tmp_path / "sim_build",
                timescale=("1ns", "1ps"),
                always=True,
            )
            runner.test(
                hdl_toplevel="dsp_block",
                test_module="test_dsp_block",
                test_dir=Path(__file__).resolve().parents[3] / "rtl" / "cocotb",
                build_dir=tmp_path / "sim_build",
                extra_env={"HV_DSP_INPUT": str(input_path), "HV_DSP_OUTPUT": str(output_path)},
                timescale=("1ns", "1ps"),
            )
            return np.asarray(json.loads(output_path.read_text(encoding="utf-8")), dtype=int)
