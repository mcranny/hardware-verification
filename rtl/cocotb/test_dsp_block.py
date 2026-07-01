from __future__ import annotations

import json
import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


@cocotb.test()
async def stream_samples(dut):
    input_path = Path(os.environ["HV_DSP_INPUT"])
    output_path = Path(os.environ["HV_DSP_OUTPUT"])
    samples = json.loads(input_path.read_text(encoding="utf-8"))
    outputs: list[int] = []

    cocotb.start_soon(Clock(dut.clk, 2, unit="ns").start())
    dut.rst.value = 1
    dut.sample_valid.value = 0
    dut.sample_in.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0

    for sample in samples:
        dut.sample_in.value = int(sample)
        dut.sample_valid.value = 1
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        if int(dut.output_valid.value):
            outputs.append(int(dut.sample_out.value.signed_integer))

    dut.sample_valid.value = 0
    await RisingEdge(dut.clk)
    output_path.write_text(json.dumps(outputs), encoding="utf-8")
