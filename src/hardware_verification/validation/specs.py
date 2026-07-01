from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TestSpec:
    __test__ = False

    name: str
    pass_criteria: dict[str, float]
    stimulus_params: dict[str, float | str] = field(default_factory=dict)
    tolerance: float | None = None
    critical: bool = False
