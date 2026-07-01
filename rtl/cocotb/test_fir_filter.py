import cocotb
from cocotb.triggers import RisingEdge

from common import load_stimulus, reset_streaming_dut, stream_samples as drive_samples, write_outputs


async def write_coefficients(dut, coeffs: list[int]) -> None:
    dut.sample_valid.value = 0
    for address, coeff in enumerate(coeffs):
        dut.coeff_addr.value = address
        dut.coeff_data.value = int(coeff)
        dut.coeff_we.value = 1
        await RisingEdge(dut.clk)
    dut.coeff_we.value = 0
    await RisingEdge(dut.clk)


@cocotb.test()
async def stream_samples(dut):
    stimulus = load_stimulus("HV_FIR_INPUT")
    await reset_streaming_dut(dut)
    await write_coefficients(dut, stimulus["coeffs"])
    outputs = await drive_samples(dut, stimulus["samples"], stimulus["idle_cycles"])
    write_outputs("HV_FIR_OUTPUT", outputs)
