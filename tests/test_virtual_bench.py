from __future__ import annotations

import numpy as np
import pytest

from hardware_verification.dut import AmplifierDUT
from hardware_verification.virtual_bench import VirtualBench, VirtualDMM


def test_bench_drives_scope_sim_generator_and_scope() -> None:
    bench = VirtualBench(n_samples=10_000, sample_rate=1_000_000.0)
    bench.function_generator.set_waveform("sine", frequency=1_000.0, amplitude=0.5)
    path = bench.drive(AmplifierDUT(gain=2.0))
    record = bench.acquire_output(path)

    assert path.output_samples.shape == path.input_samples.shape
    assert np.max(record.samples) > 0.8
    assert np.min(record.samples) < -0.8


def test_dmm_dc_voltage_tracks_known_signal_within_spec() -> None:
    dmm = VirtualDMM(noise_floor=0.0, accuracy_pct_reading=0.0, accuracy_pct_range=0.0)
    measured = dmm.measure_dc_voltage(np.full(1_000, 1.234))

    assert measured == pytest.approx(1.234)


def test_seeded_dmm_noise_advances_between_successive_measurements() -> None:
    dmm = VirtualDMM(noise_floor=0.1, accuracy_pct_reading=0.0, accuracy_pct_range=0.0, seed=123)
    samples = np.full(1_000, 1.234)

    first = dmm.measure_dc_voltage(samples)
    second = dmm.measure_dc_voltage(samples)

    assert first != second


def test_dmm_accuracy_error_is_bounded_around_nominal_value() -> None:
    dmm = VirtualDMM(
        noise_floor=0.0,
        accuracy_pct_reading=1.0,
        accuracy_pct_range=0.0,
        seed=123,
    )

    measured = dmm.measure_dc_voltage(np.full(1_000, 1.0))

    assert 0.99 <= measured <= 1.01


def test_ac_current_rms_applies_current_range_error_after_shunt_conversion() -> None:
    dmm = VirtualDMM(
        voltage_range=1_000_000.0,
        current_range=1.0,
        noise_floor=0.0,
        accuracy_pct_reading=0.0,
        accuracy_pct_range=0.0,
    )
    phase = np.linspace(0.0, 2.0 * np.pi, 10_000, endpoint=False)
    voltage_samples = np.sin(phase)

    measured = dmm.measure_ac_current_rms(voltage_samples, shunt_ohms=10.0)

    assert measured == pytest.approx(np.sqrt(0.5) / 10.0)


def test_ac_rms_measurements_do_not_report_negative_magnitudes() -> None:
    dmm = VirtualDMM(
        voltage_range=10.0,
        noise_floor=0.0,
        accuracy_pct_reading=0.0,
        accuracy_pct_range=1.0,
        seed=123,
    )

    measured = dmm.measure_ac_rms(np.zeros(1_000))

    assert measured >= 0.0


def test_function_generator_rejects_unknown_settings() -> None:
    bench = VirtualBench()

    with pytest.raises(AttributeError, match="unknown function generator setting"):
        bench.function_generator.configure(amplitdue=1.0)
