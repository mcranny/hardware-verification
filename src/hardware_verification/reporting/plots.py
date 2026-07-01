from __future__ import annotations

import os
from pathlib import Path
import tempfile

from hardware_verification.monte_carlo import MonteCarloSummary, TrialRecord, trial_records_to_rows


def plot_yield_distribution(records: list[TrialRecord], output_path: str | Path, measurement: str = "measurement.gain") -> Path:
    pd, plt = _plot_dependencies()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(trial_records_to_rows(records))
    if measurement not in frame:
        raise ValueError(f"measurement column is not available: {measurement}")

    values = pd.to_numeric(frame[measurement], errors="coerce").dropna()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(values, bins=min(20, max(5, len(values))), color="#2f6f8f", edgecolor="white")
    ax.set_title(measurement.replace("measurement.", "").replace("_", " ").title())
    ax.set_xlabel(measurement)
    ax.set_ylabel("Trials")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_sensitivity_tornado(summary: MonteCarloSummary, output_path: str | Path) -> Path:
    pd, plt = _plot_dependencies()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        sorted(summary.sensitivity.items(), key=lambda item: item[1]),
        columns=["parameter", "sensitivity"],
    )

    fig, ax = plt.subplots(figsize=(7, 4))
    if frame.empty:
        ax.text(0.5, 0.5, "No sensitivity data", ha="center", va="center")
        ax.set_axis_off()
    else:
        ax.barh(frame["parameter"], frame["sensitivity"], color="#6b8e23")
        ax.set_xlabel("Absolute correlation")
        ax.set_ylabel("Parameter")
        ax.set_title("Sensitivity")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def _plot_dependencies():
    try:
        config_dir = Path(tempfile.gettempdir()) / "hardware_verification_mpl"
        config_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("MPLCONFIGDIR", str(config_dir))
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("plotting requires the 'viz' optional dependency group") from exc
    return pd, plt
