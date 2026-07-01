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
    wire signed [2*DATA_WIDTH-1:0] product;
    wire signed [2*DATA_WIDTH-1:0] scaled;

    assign product = sample_in * GAIN_Q15;
    assign scaled = product >>> 15;

    function signed [DATA_WIDTH-1:0] saturate;
        input signed [2*DATA_WIDTH-1:0] value;
        reg signed [2*DATA_WIDTH-1:0] biased;
        reg signed [2*DATA_WIDTH-1:0] max_value;
        reg signed [2*DATA_WIDTH-1:0] min_value;
        begin
            biased = value + OFFSET;
            max_value = (1 <<< (DATA_WIDTH - 1)) - 1;
            min_value = -(1 <<< (DATA_WIDTH - 1));
            if (biased > max_value) begin
                saturate = max_value[DATA_WIDTH-1:0];
            end else if (biased < min_value) begin
                saturate = min_value[DATA_WIDTH-1:0];
            end else begin
                saturate = biased[DATA_WIDTH-1:0];
            end
        end
    endfunction

    always @(posedge clk) begin
        if (rst) begin
            sample_out <= 0;
            output_valid <= 0;
        end else if (sample_valid) begin
            sample_out <= saturate(scaled);
            output_valid <= 1;
        end else begin
            output_valid <= 0;
        end
    end
endmodule
