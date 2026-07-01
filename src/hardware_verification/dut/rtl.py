from __future__ import annotations

from dataclasses import dataclass, field
from importlib.util import find_spec
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np

from .base import DUT


@dataclass(frozen=True)
class RTLModuleConfig:
    top_level: str
    test_module: str
    input_env: str
    output_env: str
    parameter_defaults: dict[str, int]
    data_width_parameter: str = "DATA_WIDTH"
    coeff_width_parameter: str | None = None


MODULE_CONFIGS = {
    "dsp_block": RTLModuleConfig(
        top_level="dsp_block",
        test_module="test_dsp_block",
        input_env="HV_DSP_INPUT",
        output_env="HV_DSP_OUTPUT",
        parameter_defaults={"DATA_WIDTH": 16, "GAIN_Q15": (1 << 15) - 1, "OFFSET": 0},
    ),
    "moving_average": RTLModuleConfig(
        top_level="moving_average",
        test_module="test_moving_average",
        input_env="HV_MOVING_AVERAGE_INPUT",
        output_env="HV_MOVING_AVERAGE_OUTPUT",
        parameter_defaults={"DATA_WIDTH": 16, "WINDOW_BITS": 3},
    ),
    "fir_filter": RTLModuleConfig(
        top_level="fir_filter",
        test_module="test_fir_filter",
        input_env="HV_FIR_INPUT",
        output_env="HV_FIR_OUTPUT",
        parameter_defaults={"DATA_WIDTH": 16, "COEFF_WIDTH": 16, "TAP_COUNT": 4},
        coeff_width_parameter="COEFF_WIDTH",
    ),
}


@dataclass
class VerilogDUT(DUT):
    """Verilog DUT adapter backed by local HDL simulation."""

    module_name: str
    source_files: list[Path]
    parameters: dict[str, object] = field(default_factory=dict)
    _input: np.ndarray = field(default_factory=lambda: np.array([], dtype=float), init=False)
    _output: np.ndarray = field(default_factory=lambda: np.array([], dtype=float), init=False)

    def apply_input(self, signal: np.ndarray, sample_rate: float) -> None:
        del sample_rate
        self._input = np.asarray(signal)
        self._output = self.simulate(self._input)

    def get_output(self) -> np.ndarray:
        return self._output.copy()

    def reset(self) -> None:
        self._input = np.array([], dtype=float)
        self._output = np.array([], dtype=float)

    def simulate(self, signal: np.ndarray) -> np.ndarray:
        if self.module_name not in MODULE_CONFIGS:
            supported = ", ".join(sorted(MODULE_CONFIGS))
            raise NotImplementedError(f"VerilogDUT supports these modules: {supported}")
        if shutil.which("iverilog") is None or shutil.which("vvp") is None:
            raise RuntimeError("Icarus Verilog tools 'iverilog' and 'vvp' are required for HDL simulation")
        if find_spec("cocotb_tools.runner") is None:
            raise RuntimeError("cocotb and cocotb_tools are required for HDL simulation")
        return self._simulate_module(signal)

    def run_cocotb(self) -> np.ndarray:
        return self.simulate(self._input)

    def _simulate_module(self, signal: np.ndarray) -> np.ndarray:
        config = MODULE_CONFIGS[self.module_name]
        parameters = self._resolved_parameters(config)
        samples = self._validated_int_array(signal, "samples")
        data_width = int(parameters[config.data_width_parameter])
        min_value = -(1 << (data_width - 1))
        max_value = (1 << (data_width - 1)) - 1
        if np.any(samples < min_value) or np.any(samples > max_value):
            raise ValueError(f"{self.module_name} samples must fit signed {data_width}-bit range")
        payload: dict[str, list[int]] = {"samples": [int(sample) for sample in samples]}
        if "IDLE_CYCLES" in self.parameters:
            idle_cycles = self._validated_int_array(np.asarray(self.parameters["IDLE_CYCLES"]), "idle cycles")
            if idle_cycles.size != samples.size:
                raise ValueError(f"{self.module_name} IDLE_CYCLES length must match samples length")
            if np.any(idle_cycles < 0):
                raise ValueError(f"{self.module_name} IDLE_CYCLES values must be non-negative")
            payload["idle_cycles"] = [int(cycle) for cycle in idle_cycles]
        if self.module_name == "fir_filter":
            coeffs = self._validated_coefficients(config, parameters)
            payload["coeffs"] = [int(coeff) for coeff in coeffs]

        from cocotb_tools.runner import get_runner

        with tempfile.TemporaryDirectory(prefix="hardware_verification_rtl_") as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "input.json"
            output_path = tmp_path / "output.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            runner = get_runner("icarus")
            runner.build(
                sources=[str(Path(source)) for source in self.source_files],
                hdl_toplevel=config.top_level,
                parameters=parameters,
                build_dir=tmp_path / "sim_build",
                timescale=("1ns", "1ps"),
                always=True,
            )
            runner.test(
                hdl_toplevel=config.top_level,
                test_module=config.test_module,
                test_dir=Path(__file__).resolve().parents[3] / "rtl" / "cocotb",
                build_dir=tmp_path / "sim_build",
                extra_env={config.input_env: str(input_path), config.output_env: str(output_path)},
                timescale=("1ns", "1ps"),
            )
            return np.asarray(json.loads(output_path.read_text(encoding="utf-8")), dtype=int)

    def _resolved_parameters(self, config: RTLModuleConfig) -> dict[str, int]:
        parameters: dict[str, int] = dict(config.parameter_defaults)
        for name, value in self.parameters.items():
            if isinstance(value, bool) or not isinstance(value, int):
                if name not in {"COEFFS", "IDLE_CYCLES"}:
                    raise TypeError(f"{self.module_name} parameter {name} must be an integer")
                continue
            if name not in {"COEFFS", "IDLE_CYCLES"}:
                parameters[name] = value
        return parameters

    def _validated_int_array(self, values: np.ndarray, name: str) -> np.ndarray:
        array = np.asarray(values)
        if not np.issubdtype(array.dtype, np.integer):
            raise TypeError(f"{self.module_name} {name} must be integer values")
        return array.astype(np.int64, copy=False).reshape(-1)

    def _validated_coefficients(self, config: RTLModuleConfig, parameters: dict[str, int]) -> np.ndarray:
        if "COEFFS" not in self.parameters:
            raise ValueError("fir_filter requires COEFFS in parameters")
        coeffs = self._validated_int_array(np.asarray(self.parameters["COEFFS"]), "coefficients")
        tap_count = int(parameters["TAP_COUNT"])
        if coeffs.size != tap_count:
            raise ValueError(f"fir_filter requires exactly {tap_count} coefficients")
        if config.coeff_width_parameter is None:
            return coeffs
        coeff_width = int(parameters[config.coeff_width_parameter])
        min_coeff = -(1 << (coeff_width - 1))
        max_coeff = (1 << (coeff_width - 1)) - 1
        if np.any(coeffs < min_coeff) or np.any(coeffs > max_coeff):
            raise ValueError(f"fir_filter coefficients must fit signed {coeff_width}-bit range")
        return coeffs
