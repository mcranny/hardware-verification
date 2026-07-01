from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pytest

from hardware_verification.dut import VerilogDUT
from hardware_verification.rtl_verification import compare_waveforms


RTL_ROOT = Path(__file__).resolve().parents[1] / "rtl"


def q15_reference(signal: np.ndarray, gain_q15: int, offset: int = 0, data_width: int = 16) -> np.ndarray:
    minimum = -(1 << (data_width - 1))
    maximum = (1 << (data_width - 1)) - 1
    scaled = (signal.astype(int) * gain_q15) >> 15
    return np.clip(scaled + offset, minimum, maximum).astype(int)


def test_verilog_dut_runs_dsp_block_against_q15_reference() -> None:
    if shutil.which("iverilog") is None or shutil.which("vvp") is None:
        pytest.skip("Icarus Verilog is not installed")
    signal = np.array([-20_000, -1_000, 0, 1_000, 20_000, 32_000], dtype=int)
    dut = VerilogDUT(
        "dsp_block",
        [RTL_ROOT / "dsp_block.v"],
        parameters={"DATA_WIDTH": 16, "GAIN_Q15": 16_384, "OFFSET": 10},
    )

    dut.apply_input(signal, 1_000_000.0)
    report = compare_waveforms(
        q15_reference(signal, 16_384, offset=10),
        dut.get_output(),
        max_abs_limit=0.0,
        mean_abs_limit=0.0,
    )

    assert report.passed


def test_verilog_dut_reset_clears_state() -> None:
    dut = VerilogDUT("dsp_block", [RTL_ROOT / "dsp_block.v"])
    dut._input = np.array([1, 2])
    dut._output = np.array([3, 4])

    dut.reset()

    assert dut.get_output().size == 0
    assert dut._input.size == 0


def test_verilog_dut_rejects_unsupported_modules() -> None:
    dut = VerilogDUT("unknown", [RTL_ROOT / "dsp_block.v"])

    with pytest.raises(NotImplementedError, match="dsp_block"):
        dut.apply_input(np.array([1, 2]), 1_000_000.0)
