from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pytest

from hardware_verification.dut import VerilogDUT
from hardware_verification.rtl_verification import compare_integer_waveforms, compare_waveforms


RTL_ROOT = Path(__file__).resolve().parents[1] / "rtl"


def q15_reference(signal: np.ndarray, gain_q15: int, offset: int = 0, data_width: int = 16) -> np.ndarray:
    """RTL model: signed DATA_WIDTH input, Q15 gain, DATA_WIDTH saturated output."""
    minimum = -(1 << (data_width - 1))
    maximum = (1 << (data_width - 1)) - 1
    scaled = (signal.astype(int) * gain_q15) >> 15
    return np.clip(scaled + offset, minimum, maximum).astype(int)


def moving_average_reference(samples: np.ndarray, window_bits: int = 3, data_width: int = 16) -> np.ndarray:
    """RTL model: signed DATA_WIDTH input, zeroed history, arithmetic shift average.

    Output width is DATA_WIDTH + WINDOW_BITS. There is no warm-up discard: the
    zero-initialized buffer contributes until enough valid samples fill it.
    """
    values = np.asarray(samples, dtype=int)
    _assert_signed_range(values, data_width, "moving_average samples")
    window_size = 1 << window_bits
    buffer = [0] * window_size
    index = 0
    total = 0
    outputs: list[int] = []
    for sample in values:
        total = total - buffer[index] + int(sample)
        buffer[index] = int(sample)
        index = (index + 1) % window_size
        outputs.append(total >> window_bits)
    return np.asarray(outputs, dtype=int)


def fir_reference(
    samples: np.ndarray,
    coeffs: np.ndarray,
    *,
    tap_count: int = 4,
    data_width: int = 16,
    coeff_width: int = 16,
) -> np.ndarray:
    """RTL model: raw signed product sum with saturated DATA_WIDTH+COEFF_WIDTH output.

    The current input multiplies coeffs[0]. Older valid samples in the delay
    line multiply higher taps. The delay line updates after output evaluation.
    """
    values = np.asarray(samples, dtype=int)
    coefficients = np.asarray(coeffs, dtype=int)
    _assert_signed_range(values, data_width, "fir_filter samples")
    _assert_signed_range(coefficients, coeff_width, "fir_filter coefficients")
    if coefficients.size != tap_count:
        raise ValueError("coefficient count must match tap_count")
    output_width = data_width + coeff_width
    sat_min = -(1 << (output_width - 1))
    sat_max = (1 << (output_width - 1)) - 1
    delay_line = [0] * tap_count
    outputs: list[int] = []
    for sample in values:
        acc = int(sample) * int(coefficients[0])
        for tap in range(1, tap_count):
            acc += delay_line[tap - 1] * int(coefficients[tap])
        outputs.append(min(max(acc, sat_min), sat_max))
        for tap in range(tap_count - 1, 0, -1):
            delay_line[tap] = delay_line[tap - 1]
        delay_line[0] = int(sample)
    return np.asarray(outputs, dtype=int)


def _assert_signed_range(values: np.ndarray, width: int, name: str) -> None:
    minimum = -(1 << (width - 1))
    maximum = (1 << (width - 1)) - 1
    if np.any(values < minimum) or np.any(values > maximum):
        raise ValueError(f"{name} must fit signed {width}-bit range")


def assert_integer_match(expected: np.ndarray, actual: np.ndarray) -> None:
    report = compare_integer_waveforms(expected, actual)
    assert report.passed, report.describe()


@pytest.fixture
def require_icarus() -> None:
    if shutil.which("iverilog") is None or shutil.which("vvp") is None:
        pytest.skip("Icarus Verilog is not installed")


def test_reference_models_cover_boundary_vectors() -> None:
    assert moving_average_reference(np.array([8, 8, 8, 8]), window_bits=2).tolist() == [2, 4, 6, 8]
    assert moving_average_reference(np.array([7, -8, 7, -8]), window_bits=1, data_width=4).tolist() == [3, -1, -1, -1]

    assert fir_reference(np.array([4, 0, 0]), np.array([2, -1, 3]), tap_count=3).tolist() == [8, -4, 12]
    assert fir_reference(np.array([127]), np.array([127]), tap_count=1, data_width=8, coeff_width=8).tolist() == [16_129]
    assert fir_reference(np.array([127]), np.array([127, 127]), tap_count=2, data_width=8, coeff_width=8).tolist() == [16_129]


def test_verilog_dut_runs_dsp_block_against_q15_reference(require_icarus: None) -> None:
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


@pytest.mark.parametrize(
    ("signal", "gain_q15", "offset"),
    [
        (np.array([-32_768, -1, 0, 1, 32_767], dtype=int), 32_767, 0),
        (np.array([20_000, 30_000, 32_767], dtype=int), 32_767, 20_000),
        (np.array([-20_000, -30_000, -32_768], dtype=int), 32_767, -20_000),
        (np.array([-5_000, 5_000], dtype=int), -16_384, 0),
    ],
)
def test_dsp_block_cosim_boundary_cases(require_icarus: None, signal: np.ndarray, gain_q15: int, offset: int) -> None:
    dut = VerilogDUT("dsp_block", [RTL_ROOT / "dsp_block.v"], parameters={"DATA_WIDTH": 16, "GAIN_Q15": gain_q15, "OFFSET": offset})

    dut.apply_input(signal, 1_000_000.0)

    assert_integer_match(q15_reference(signal, gain_q15, offset), dut.get_output())


def test_dsp_block_cosim_randomized_signed_samples(require_icarus: None) -> None:
    rng = np.random.default_rng(1234)
    signal = rng.integers(-32_768, 32_768, size=64, dtype=np.int64)
    gain_q15 = 12_345
    dut = VerilogDUT("dsp_block", [RTL_ROOT / "dsp_block.v"], parameters={"GAIN_Q15": gain_q15, "OFFSET": -17})

    dut.apply_input(signal, 1_000_000.0)

    assert_integer_match(q15_reference(signal, gain_q15, offset=-17), dut.get_output())


@pytest.mark.parametrize(
    ("signal", "window_bits"),
    [
        (np.array([64, 0, 0, 0, 0], dtype=int), 2),
        (np.array([8, 8, 8, 8, 8], dtype=int), 2),
        (np.array([7, -8, 7, -8, 7, -8], dtype=int), 1),
        (np.array([1, 2], dtype=int), 3),
        (np.arange(1, 10, dtype=int), 2),
    ],
)
def test_moving_average_cosim_deterministic_cases(require_icarus: None, signal: np.ndarray, window_bits: int) -> None:
    dut = VerilogDUT("moving_average", [RTL_ROOT / "moving_average.v"], parameters={"DATA_WIDTH": 16, "WINDOW_BITS": window_bits})

    dut.apply_input(signal, 1_000_000.0)

    assert_integer_match(moving_average_reference(signal, window_bits=window_bits), dut.get_output())


def test_moving_average_cosim_valid_gaps(require_icarus: None) -> None:
    signal = np.array([16, 0, -16, 32], dtype=int)
    dut = VerilogDUT(
        "moving_average",
        [RTL_ROOT / "moving_average.v"],
        parameters={"DATA_WIDTH": 16, "WINDOW_BITS": 2, "IDLE_CYCLES": [0, 2, 1, 0]},
    )

    dut.apply_input(signal, 1_000_000.0)

    assert_integer_match(moving_average_reference(signal, window_bits=2), dut.get_output())


def test_moving_average_cosim_randomized_signed_samples(require_icarus: None) -> None:
    rng = np.random.default_rng(5678)
    signal = rng.integers(-2_048, 2_048, size=96, dtype=np.int64)
    dut = VerilogDUT("moving_average", [RTL_ROOT / "moving_average.v"], parameters={"WINDOW_BITS": 3})

    dut.apply_input(signal, 1_000_000.0)

    assert_integer_match(moving_average_reference(signal, window_bits=3), dut.get_output())


@pytest.mark.parametrize(
    ("signal", "coeffs", "tap_count"),
    [
        (np.array([5, 0, 0, 0], dtype=int), np.array([1, 2, 3, 4], dtype=int), 4),
        (np.array([5, 5, 5, 5], dtype=int), np.array([1, 1, 1, 1], dtype=int), 4),
        (np.array([10, -10, 20, -20], dtype=int), np.array([-2, 3, -4, 5], dtype=int), 4),
        (np.array([7, 8, 9], dtype=int), np.array([3], dtype=int), 1),
        (np.array([1, 2, 3, 4, 5], dtype=int), np.array([1, -1, 2, -2, 3, -3], dtype=int), 6),
    ],
)
def test_fir_filter_cosim_deterministic_cases(require_icarus: None, signal: np.ndarray, coeffs: np.ndarray, tap_count: int) -> None:
    dut = VerilogDUT(
        "fir_filter",
        [RTL_ROOT / "fir_filter.v"],
        parameters={"DATA_WIDTH": 16, "COEFF_WIDTH": 16, "TAP_COUNT": tap_count, "COEFFS": coeffs.tolist()},
    )

    dut.apply_input(signal, 1_000_000.0)

    assert_integer_match(fir_reference(signal, coeffs, tap_count=tap_count), dut.get_output())


def test_fir_filter_cosim_saturates_high_and_low(require_icarus: None) -> None:
    signal = np.array([127, 127, -128, -128], dtype=int)
    coeffs = np.array([127, 127, 127, 127], dtype=int)
    dut = VerilogDUT(
        "fir_filter",
        [RTL_ROOT / "fir_filter.v"],
        parameters={"DATA_WIDTH": 8, "COEFF_WIDTH": 8, "TAP_COUNT": 4, "COEFFS": coeffs.tolist()},
    )

    dut.apply_input(signal, 1_000_000.0)

    assert_integer_match(fir_reference(signal, coeffs, tap_count=4, data_width=8, coeff_width=8), dut.get_output())


def test_fir_filter_cosim_randomized_signed_samples_and_coeffs(require_icarus: None) -> None:
    rng = np.random.default_rng(9012)
    signal = rng.integers(-256, 256, size=80, dtype=np.int64)
    coeffs = rng.integers(-64, 64, size=5, dtype=np.int64)
    dut = VerilogDUT(
        "fir_filter",
        [RTL_ROOT / "fir_filter.v"],
        parameters={"DATA_WIDTH": 16, "COEFF_WIDTH": 16, "TAP_COUNT": 5, "COEFFS": coeffs.tolist()},
    )

    dut.apply_input(signal, 1_000_000.0)

    assert_integer_match(fir_reference(signal, coeffs, tap_count=5), dut.get_output())


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


def test_verilog_dut_rejects_float_samples(require_icarus: None) -> None:
    dut = VerilogDUT("dsp_block", [RTL_ROOT / "dsp_block.v"])

    with pytest.raises(TypeError, match="integer"):
        dut.apply_input(np.array([1.0, 2.0]), 1_000_000.0)


def test_verilog_dut_rejects_out_of_range_samples(require_icarus: None) -> None:
    dut = VerilogDUT("moving_average", [RTL_ROOT / "moving_average.v"], parameters={"DATA_WIDTH": 4})

    with pytest.raises(ValueError, match="signed 4-bit"):
        dut.apply_input(np.array([8], dtype=int), 1_000_000.0)


def test_verilog_dut_rejects_fir_coefficients_out_of_range(require_icarus: None) -> None:
    dut = VerilogDUT(
        "fir_filter",
        [RTL_ROOT / "fir_filter.v"],
        parameters={"DATA_WIDTH": 8, "COEFF_WIDTH": 4, "TAP_COUNT": 2, "COEFFS": [0, 8]},
    )

    with pytest.raises(ValueError, match="signed 4-bit"):
        dut.apply_input(np.array([1], dtype=int), 1_000_000.0)
