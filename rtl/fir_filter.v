module fir_filter #(
    parameter integer TAP_COUNT = 4,
    parameter integer DATA_WIDTH = 16,
    parameter integer COEFF_WIDTH = 16
) (
    input wire clk,
    input wire rst,
    input wire signed [DATA_WIDTH-1:0] sample_in,
    input wire sample_valid,
    input wire coeff_we,
    input wire [((TAP_COUNT > 1) ? $clog2(TAP_COUNT) : 1)-1:0] coeff_addr,
    input wire signed [COEFF_WIDTH-1:0] coeff_data,
    output reg signed [DATA_WIDTH+COEFF_WIDTH-1:0] sample_out,
    output reg output_valid
);
    localparam integer OUTPUT_WIDTH = DATA_WIDTH + COEFF_WIDTH;
    localparam integer ACC_GUARD_BITS = (TAP_COUNT > 1) ? $clog2(TAP_COUNT) : 1;
    localparam integer ACC_WIDTH = OUTPUT_WIDTH + ACC_GUARD_BITS;
    localparam integer ADDR_WIDTH = (TAP_COUNT > 1) ? $clog2(TAP_COUNT) : 1;
    reg signed [DATA_WIDTH-1:0] delay_line [0:TAP_COUNT-1];
    reg signed [COEFF_WIDTH-1:0] coeffs [0:TAP_COUNT-1];
    wire [31:0] coeff_addr_wide;
    integer i;
    integer j;
    reg signed [ACC_WIDTH-1:0] next_acc;

    assign coeff_addr_wide = {{(32-ADDR_WIDTH){1'b0}}, coeff_addr};

    initial begin
        for (i = 0; i < TAP_COUNT; i = i + 1) begin
            coeffs[i] = (i == 0) ? {1'b0, {(COEFF_WIDTH-1){1'b1}}} : {COEFF_WIDTH{1'b0}};
        end
    end

    always @* begin
        next_acc = sample_in * coeffs[0];
        for (j = 1; j < TAP_COUNT; j = j + 1) begin
            next_acc = next_acc + delay_line[j - 1] * coeffs[j];
        end
    end

    function signed [OUTPUT_WIDTH-1:0] saturate;
        input signed [ACC_WIDTH-1:0] value;
        reg signed [ACC_WIDTH-1:0] max_value;
        reg signed [ACC_WIDTH-1:0] min_value;
        begin
            max_value = {{(ACC_WIDTH-OUTPUT_WIDTH){1'b0}}, 1'b0, {(OUTPUT_WIDTH-1){1'b1}}};
            min_value = {{(ACC_WIDTH-OUTPUT_WIDTH){1'b1}}, 1'b1, {(OUTPUT_WIDTH-1){1'b0}}};
            if (value > max_value) begin
                saturate = {{1'b0, {{(OUTPUT_WIDTH-1){{1'b1}}}}}};
            end else if (value < min_value) begin
                saturate = {{1'b1, {{(OUTPUT_WIDTH-1){{1'b0}}}}}};
            end else begin
                saturate = value[OUTPUT_WIDTH-1:0];
            end
        end
    endfunction

    always @(posedge clk) begin
        if (rst) begin
            for (i = 0; i < TAP_COUNT; i = i + 1) begin
                delay_line[i] <= 0;
            end
            sample_out <= 0;
            output_valid <= 0;
        end else begin
            if (coeff_we && coeff_addr_wide < TAP_COUNT) begin
                coeffs[coeff_addr] <= coeff_data;
            end
            if (sample_valid) begin
                for (i = TAP_COUNT - 1; i > 0; i = i - 1) begin
                    delay_line[i] <= delay_line[i - 1];
                end
                delay_line[0] <= sample_in;
                sample_out <= saturate(next_acc);
                output_valid <= 1;
            end else begin
                output_valid <= 0;
            end
        end
    end
endmodule
