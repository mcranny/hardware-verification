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
