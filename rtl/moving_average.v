module moving_average #(
    parameter integer WINDOW_BITS = 3,
    parameter integer DATA_WIDTH = 16
) (
    input wire clk,
    input wire rst,
    input wire signed [DATA_WIDTH-1:0] sample_in,
    input wire sample_valid,
    output reg signed [DATA_WIDTH+WINDOW_BITS-1:0] sample_out,
    output reg output_valid
);
    localparam integer WINDOW_SIZE = 1 << WINDOW_BITS;
    reg signed [DATA_WIDTH-1:0] buffer [0:WINDOW_SIZE-1];
    reg [WINDOW_BITS-1:0] index;
    reg signed [DATA_WIDTH+WINDOW_BITS-1:0] sum;
    wire signed [DATA_WIDTH+WINDOW_BITS-1:0] next_sum;
    integer i;

    assign next_sum = sum - buffer[index] + sample_in;

    always @(posedge clk) begin
        if (rst) begin
            index <= 0;
            sum <= 0;
            sample_out <= 0;
            output_valid <= 0;
            for (i = 0; i < WINDOW_SIZE; i = i + 1) begin
                buffer[i] <= 0;
            end
        end else if (sample_valid) begin
            sum <= next_sum;
            buffer[index] <= sample_in;
            index <= index + 1'b1;
            sample_out <= next_sum >>> WINDOW_BITS;
            output_valid <= 1;
        end else begin
            output_valid <= 0;
        end
    end
endmodule
