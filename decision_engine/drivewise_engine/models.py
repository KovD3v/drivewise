from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class DecisionProfile:
    budget_max: float
    annual_km: int
    usage: List[str]
    priorities: List[str]
    vehicle_type: str = "car"
    category: Optional[str] = None
    category_is_hard_constraint: bool = False
    new_or_used: str = "indifferent"
    garage: Optional[Dict[str, float]] = None
    automatic_required: bool = False
    fuel_constraints: List[str] = field(default_factory=list)
    children_count: int = 0
    passengers_usual: int = 1

@dataclass
class VehicleScore:
    vehicle_id: str
    decision_score: float
    decision_confidence: float
    profile_completeness: float
    data_quality: float
    pillar_scores: Dict[str, float]
    strengths: List[str]
    tradeoffs: List[str]
    penalties: Dict[str, float]
    explainability: Dict
    excluded: bool = False
    hard_filter_failures: List[str] = field(default_factory=list)
