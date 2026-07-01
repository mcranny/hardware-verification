from __future__ import annotations

import numpy as np
import pytest

from hardware_verification.dut import ADCModelDUT, AmplifierDUT, FIRFilterDUT, MovingAverageDUT, SignalProcessingChainDUT


def test_amplifier_gain_offset_and_saturation() -> None:
    dut = AmplifierDUT(gain=2.0, offset=0.1, saturation=1.0)
    dut.apply_input(np.array([-1.0, 0.0, 0.4]), 1_000.0)

    np.testing.assert_allclose(dut.get_output(), [-1.0, 0.1, 0.9])


def test_fir_and_moving_average_are_swappable_duts() -> None:
    signal = np.array([0.0, 1.0, 0.0, 0.0])
    fir = FIRFilterDUT(coefficients=np.array([0.5, 0.5]))
    avg = MovingAverageDUT(window_size=2)

    fir.apply_input(signal, 1_000.0)
    avg.apply_input(signal, 1_000.0)

    np.testing.assert_allclose(fir.get_output(), avg.get_output())


def test_adc_model_dut_uses_scope_sim_adc() -> None:
    signal = np.linspace(-0.5, 0.5, 100)
    dut = ADCModelDUT(sample_rate=1_000.0, bits=10, full_scale=2.0)
    dut.apply_input(signal, 1_000.0)

    assert dut.get_output().size == signal.size


def test_adc_model_dut_rejects_mismatched_drive_sample_rate() -> None:
    dut = ADCModelDUT(sample_rate=2_000.0)

    with pytest.raises(ValueError, match="sample_rate must match"):
        dut.apply_input(np.linspace(-0.5, 0.5, 100), 1_000.0)


def test_seeded_noise_advances_between_successive_dut_calls() -> None:
    dut = AmplifierDUT(noise_rms=0.1, seed=123)
    signal = np.zeros(8)

    dut.apply_input(signal, 1_000.0)
    first = dut.get_output()
    dut.apply_input(signal, 1_000.0)
    second = dut.get_output()

    assert not np.array_equal(first, second)


def test_seeded_fir_variation_advances_between_successive_calls() -> None:
    dut = FIRFilterDUT(coefficients=np.array([0.5, 0.5]), coefficient_variation=0.01, seed=123)
    signal = np.array([0.0, 1.0, 0.0, 0.0])

    dut.apply_input(signal, 1_000.0)
    first = dut.get_output()
    dut.apply_input(signal, 1_000.0)
    second = dut.get_output()

    assert not np.array_equal(first, second)


def test_signal_processing_chain_runs_stages_in_order() -> None:
    chain = SignalProcessingChainDUT([AmplifierDUT(gain=2.0), AmplifierDUT(offset=1.0)])
    chain.apply_input(np.array([1.0, 2.0]), 1_000.0)

    np.testing.assert_allclose(chain.get_output(), [3.0, 5.0])
