module dsp_block #(
    parameter integer DATA_WIDTH = 16,
    parameter signed [DATA_WIDTH-1:0] GAIN_Q15 = 16'sd32767,
    parameter signed [DATA_WIDTH-1:0] OFFSET = 16'sd0
) (
    input wire clk,
    input wire rst,
    input wire signed [DATA_WIDTH-1:0] sample_in,
    input wire sample_valid,
    output reg signed [DATA_WIDTH-1:0] sample_out,
    output reg output_valid
);
    reg signed [2*DATA_WIDTH-1:0] product;

    always @(posedge clk) begin
        if (rst) begin
            sample_out <= 0;
            output_valid <= 0;
        end else if (sample_valid) begin
            product = sample_in * GAIN_Q15;
            sample_out <= (product >>> 15) + OFFSET;
            output_valid <= 1;
        end else begin
            output_valid <= 0;
        end
    end
endmodule
