# Hardware Verification Framework

Automated validation environment for testing behavioral signal-processing models, estimating statistical yield, and preparing the same validation flow for RTL implementations.

The framework wraps the virtual oscilloscope simulator from Project 1 through the published `scope-sim` package. Local development and tests also support a sibling checkout at `../scope_sim/src`.

## What is included

- `virtual_bench/`: function generator, oscilloscope, DMM, and bench orchestration.
- `dut/`: behavioral DUTs plus a Verilog adapter for the DSP block.
- `validation/`: reusable test definitions, pass/fail results, and suite runner.
- `monte_carlo/`: variation sampling, repeated trial execution, yield, worst-case, and sensitivity analysis.
- `rtl/`: example Verilog implementations.
- `rtl_verification/`: behavioral-vs-RTL comparison utilities.
- `reporting/`: terminal, Markdown, CSV-driven plotting, and summary generation.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,reporting]"
pytest
```

If `scope-sim` is already checked out beside this repository, pytest uses it directly. Otherwise the package dependency resolves from GitHub.

## Example

```bash
python examples/run_validation.py
```

The example builds a virtual bench, drives an amplifier DUT with a sine wave, runs gain, noise, and offset checks, then runs a small Monte Carlo yield study.

## RTL verification

**Status:** `dsp_block.v` has an end-to-end local simulator path through `VerilogDUT` using Icarus Verilog. The FIR and moving-average modules are currently syntax/lint checked and are ready for later co-simulation coverage.

Install the optional Python RTL dependencies and the host simulator:

```bash
python -m pip install -e ".[rtl]"
brew install icarus-verilog verilator
```

On Debian/Ubuntu:

```bash
sudo apt-get install iverilog verilator
```

Run the RTL checks locally:

```bash
pytest tests/test_rtl_dut.py
iverilog -g2012 -tnull rtl/fir_filter.v rtl/moving_average.v rtl/dsp_block.v
verilator --lint-only --timing -Wall --top-module dsp_block rtl/dsp_block.v
```

## Monte Carlo reports

The CSV export and plotting helpers can write reusable report artifacts:

```bash
python -m pip install -e ".[viz]"
python examples/run_monte_carlo_report.py
```
