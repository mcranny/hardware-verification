import cocotb

from common import load_stimulus, reset_streaming_dut, stream_samples as drive_samples, write_outputs


@cocotb.test()
async def stream_samples(dut):
    stimulus = load_stimulus("HV_MOVING_AVERAGE_INPUT")
    await reset_streaming_dut(dut)
    outputs = await drive_samples(dut, stimulus["samples"], stimulus["idle_cycles"])
    write_outputs("HV_MOVING_AVERAGE_OUTPUT", outputs)
