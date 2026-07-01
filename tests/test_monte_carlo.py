from __future__ import annotations

import csv

from hardware_verification.dut import AmplifierDUT
from hardware_verification.monte_carlo import MonteCarloEngine, VariationSpec, trial_records_to_rows, write_trial_records_csv
from hardware_verification.validation import GainTest, TestSpec, TestSuite
from hardware_verification.virtual_bench import VirtualBench


def build_gain_engine() -> MonteCarloEngine:
    def suite_factory(bench: VirtualBench) -> TestSuite:
        return TestSuite(
            "gain",
            [GainTest(bench, TestSpec("gain", {"target_gain": 2.0, "gain_error_pct": 1.0}, {"kind": "sine", "amplitude": 0.5}))],
        )

    return MonteCarloEngine(
        bench_factory=lambda params: VirtualBench(n_samples=10_000),
        dut_factory=lambda params: AmplifierDUT(gain=2.0 + params["gain_delta"]),
        suite_factory=suite_factory,
        variation_specs=[VariationSpec("gain_delta", "dut", "gain", "gaussian", mean=0.0, sigma=0.005)],
        seed=42,
    )


def test_monte_carlo_reports_yield_and_sensitivity() -> None:
    engine = build_gain_engine()
    records, summary = engine.run(25)

    assert len(records) == 25
    assert 0.0 <= summary.yield_pct <= 100.0
    assert "gain_delta" in summary.sensitivity


def test_monte_carlo_gain_yield_is_not_corrupted_by_offset_sign() -> None:
    def suite_factory(bench: VirtualBench) -> TestSuite:
        return TestSuite(
            "gain",
            [GainTest(bench, TestSpec("gain", {"target_gain": 2.0, "gain_error_pct": 1.0}, {"kind": "sine", "frequency": 1_000.0, "amplitude": 0.5}))],
        )

    engine = MonteCarloEngine(
        bench_factory=lambda params: VirtualBench(n_samples=20_000, sample_rate=1_000_000.0),
        dut_factory=lambda params: AmplifierDUT(gain=2.0 + params["gain_delta"], offset=params["offset"]),
        suite_factory=suite_factory,
        variation_specs=[
            VariationSpec("gain_delta", "dut", "gain", "gaussian", mean=0.0, sigma=0.005),
            VariationSpec("offset", "dut", "offset", "gaussian", mean=0.0, sigma=0.001),
        ],
        seed=7,
    )

    _, summary = engine.run(50)

    assert summary.yield_pct == 100.0


def test_trial_records_export_to_flat_rows() -> None:
    records, _ = build_gain_engine().run(2)

    rows = trial_records_to_rows(records)

    assert len(rows) == 2
    assert rows[0]["trial"] == 0
    assert rows[0]["suite"] == "gain"
    assert rows[0]["test"] == "gain"
    assert "param.gain_delta" in rows[0]
    assert "measurement.gain" in rows[0]
    assert "limit.gain_error_pct" in rows[0]


def test_trial_records_write_csv(tmp_path) -> None:
    records, _ = build_gain_engine().run(2)
    output_path = write_trial_records_csv(records, tmp_path / "monte_carlo.csv")

    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 2
    assert rows[0]["trial"] == "0"
    assert rows[0]["suite"] == "gain"
    assert rows[0]["test_status"] in {"PASS", "FAIL"}


def test_trial_records_export_empty_suite_rows() -> None:
    records, _ = MonteCarloEngine(
        bench_factory=lambda params: VirtualBench(),
        dut_factory=lambda params: AmplifierDUT(),
        suite_factory=lambda bench: TestSuite("empty"),
        variation_specs=[VariationSpec("gain_delta", "dut", "gain", "constant", value=0.0)],
        seed=42,
    ).run(2)

    rows = trial_records_to_rows(records)

    assert len(rows) == 2
    assert rows[0]["test"] == ""
    assert rows[0]["test_status"] == ""
    assert rows[0]["suite_passed"] is True
