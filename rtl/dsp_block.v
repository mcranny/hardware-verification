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
    wire signed [2*DATA_WIDTH-1:0] offset_extended;
    wire signed [2*DATA_WIDTH-1:0] biased;
    localparam signed [2*DATA_WIDTH-1:0] MAX_VALUE = (1 <<< (DATA_WIDTH - 1)) - 1;
    localparam signed [2*DATA_WIDTH-1:0] MIN_VALUE = -(1 <<< (DATA_WIDTH - 1));

    assign product = sample_in * GAIN_Q15;
    assign scaled = product >>> 15;
    assign offset_extended = {{DATA_WIDTH{OFFSET[DATA_WIDTH-1]}}, OFFSET};
    assign biased = scaled + offset_extended;

    function signed [DATA_WIDTH-1:0] saturate;
        input signed [2*DATA_WIDTH-1:0] value;
        begin
            if (value > MAX_VALUE) begin
                saturate = MAX_VALUE[DATA_WIDTH-1:0];
            end else if (value < MIN_VALUE) begin
                saturate = MIN_VALUE[DATA_WIDTH-1:0];
            end else begin
                saturate = value[DATA_WIDTH-1:0];
            end
        end
    endfunction

    always @(posedge clk) begin
        if (rst) begin
            sample_out <= 0;
            output_valid <= 0;
        end else if (sample_valid) begin
            sample_out <= saturate(biased);
            output_valid <= 1;
        end else begin
            output_valid <= 0;
        end
    end
endmodule
