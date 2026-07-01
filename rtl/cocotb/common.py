from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


def load_stimulus(env_name: str) -> dict[str, Any]:
    """Load JSON stimulus as {"samples": [...], "idle_cycles": [...], ...}.

    A bare JSON list is accepted for backward-compatible sample streams.
    idle_cycles[i] inserts deasserted-valid cycles before samples[i].
    """
    payload = json.loads(Path(os.environ[env_name]).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return {"samples": payload, "idle_cycles": [0] * len(payload)}
    samples = payload.get("samples", [])
    payload.setdefault("idle_cycles", [0] * len(samples))
    return payload


def write_outputs(env_name: str, outputs: list[int]) -> None:
    Path(os.environ[env_name]).write_text(json.dumps(outputs), encoding="utf-8")


async def reset_streaming_dut(dut) -> None:
    cocotb.start_soon(Clock(dut.clk, 2, unit="ns").start())
    dut.rst.value = 1
    dut.sample_valid.value = 0
    dut.sample_in.value = 0
    if hasattr(dut, "coeff_we"):
        dut.coeff_we.value = 0
        dut.coeff_addr.value = 0
        dut.coeff_data.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0


async def sample_output_if_valid(dut, outputs: list[int]) -> None:
    await Timer(1, unit="ns")
    if int(dut.output_valid.value):
        outputs.append(int(dut.sample_out.value.signed_integer))


async def stream_samples(dut, samples: list[int], idle_cycles: list[int]) -> list[int]:
    outputs: list[int] = []
    for index, sample in enumerate(samples):
        for _ in range(int(idle_cycles[index])):
            dut.sample_valid.value = 0
            dut.sample_in.value = 0
            await RisingEdge(dut.clk)
            await sample_output_if_valid(dut, outputs)
        dut.sample_in.value = int(sample)
        dut.sample_valid.value = 1
        await RisingEdge(dut.clk)
        await sample_output_if_valid(dut, outputs)

    dut.sample_valid.value = 0
    await RisingEdge(dut.clk)
    await sample_output_if_valid(dut, outputs)
    return outputs
