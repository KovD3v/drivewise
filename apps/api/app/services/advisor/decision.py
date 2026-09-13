from dataclasses import dataclass, field
from typing import Any, Literal


ModuleStatus = Literal["available", "estimated", "insufficient_data"]


@dataclass(frozen=True)
class ModuleAssessment:
    status: ModuleStatus
    version: str
    value: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    assumptions: tuple[str, ...] = ()
    evidence: tuple[dict[str, Any], ...] = ()
    missing_data: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status == "insufficient_data" and self.value is not None:
            raise ValueError("insufficient_data cannot carry a value")
        if self.status == "estimated" and (
            not self.version.strip() or not self.assumptions
        ):
            raise ValueError("estimated assessments require version and assumptions")
