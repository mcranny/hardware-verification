# Hardware Verification Framework

Automated validation environment for testing behavioral signal-processing models, estimating statistical yield, and preparing the same validation flow for RTL implementations.

The framework wraps the virtual oscilloscope simulator from Project 1 through the published `scope-sim` package. Local development and tests also support a sibling checkout at `../scope_sim/src`.

## What is included

- `virtual_bench/`: function generator, oscilloscope, DMM, and bench orchestration.
- `dut/`: behavioral DUTs plus a Verilog-facing adapter stub.
- `validation/`: reusable test definitions, pass/fail results, and suite runner.
- `monte_carlo/`: variation sampling, repeated trial execution, yield, worst-case, and sensitivity analysis.
- `rtl/`: example Verilog implementations.
- `rtl_verification/`: behavioral-vs-RTL comparison utilities and optional cocotb hook.
- `reporting/`: terminal and Markdown report generation.

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

The RTL layer is structured so the same validation results can be compared against HDL simulator output. The initial repository includes Verilog examples and a cocotb-ready adapter boundary; full simulator execution requires installing the optional RTL toolchain:

```bash
python -m pip install -e ".[rtl]"
```

Icarus Verilog or Verilator must also be installed on the host before running HDL simulations.
