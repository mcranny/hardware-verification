module fir_filter #(
    parameter integer TAP_COUNT = 4,
    parameter integer DATA_WIDTH = 16,
    parameter integer COEFF_WIDTH = 16
) (
    input wire clk,
    input wire rst,
    input wire signed [DATA_WIDTH-1:0] sample_in,
    input wire sample_valid,
    output reg signed [DATA_WIDTH+COEFF_WIDTH-1:0] sample_out,
    output reg output_valid
);
    reg signed [DATA_WIDTH-1:0] delay_line [0:TAP_COUNT-1];
    reg signed [COEFF_WIDTH-1:0] coeffs [0:TAP_COUNT-1];
    integer i;
    reg signed [DATA_WIDTH+COEFF_WIDTH-1:0] acc;

    initial begin
        for (i = 0; i < TAP_COUNT; i = i + 1) begin
            coeffs[i] = (i == 0) ? 16'sd32767 : 16'sd0;
        end
    end

    always @(posedge clk) begin
        if (rst) begin
            for (i = 0; i < TAP_COUNT; i = i + 1) begin
                delay_line[i] <= 0;
            end
            sample_out <= 0;
            output_valid <= 0;
        end else if (sample_valid) begin
            for (i = TAP_COUNT - 1; i > 0; i = i - 1) begin
                delay_line[i] <= delay_line[i - 1];
            end
            delay_line[0] <= sample_in;
            acc = sample_in * coeffs[0];
            for (i = 1; i < TAP_COUNT; i = i + 1) begin
                acc = acc + delay_line[i - 1] * coeffs[i];
            end
            sample_out <= acc;
            output_valid <= 1;
        end else begin
            output_valid <= 0;
        end
    end
endmodule
