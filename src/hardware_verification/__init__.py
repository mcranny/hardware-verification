"""Automated validation framework for virtual hardware benches."""

from .dut import ADCModelDUT, AmplifierDUT, FIRFilterDUT, FirstOrderLagDUT, MovingAverageDUT, SignalProcessingChainDUT, VerilogDUT
from .monte_carlo import MonteCarloEngine, VariationSpec
from .validation import TestSpec, TestSuite
from .virtual_bench import VirtualBench

__all__ = [
    "ADCModelDUT",
    "AmplifierDUT",
    "FIRFilterDUT",
    "FirstOrderLagDUT",
    "MonteCarloEngine",
    "MovingAverageDUT",
    "SignalProcessingChainDUT",
    "TestSpec",
    "TestSuite",
    "VariationSpec",
    "VerilogDUT",
    "VirtualBench",
]
