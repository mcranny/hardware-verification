from __future__ import annotations

import numpy as np

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


def test_signal_processing_chain_runs_stages_in_order() -> None:
    chain = SignalProcessingChainDUT([AmplifierDUT(gain=2.0), AmplifierDUT(offset=1.0)])
    chain.apply_input(np.array([1.0, 2.0]), 1_000.0)

    np.testing.assert_allclose(chain.get_output(), [3.0, 5.0])
