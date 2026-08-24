"""Applicability-first official recall penalty adapter."""

from collections.abc import Mapping, Sequence
from typing import Any

from app.services.advisor.decision import ModuleAssessment
from app.services.advisor.issues import _applicability

RECALLS_VERSION = "recalls-v1"


def recall_penalty(candidate: dict[str, Any], recalls: Sequence[Any]) -> ModuleAssessment:
    if not recalls:
        return ModuleAssessment(status="insufficient_data", version=RECALLS_VERSION, missing_data=("recalls",))
    penalty = 0.0
    unknown = False
    evidence = []
    for recall in recalls:
        applicability = str(_get(recall, "applicability") or "").lower()
        if applicability == "unknown":
            unknown = True
            continue
        state = "match" if applicability in {"applicable", "match", "confirmed"} else _applicability(candidate, recall)
        if state == "unknown":
            unknown = True
        elif state == "match" and str(_get(recall, "status") or "open").lower() == "open":
            penalty += float(_get(recall, "penalty") or 6.0)
            evidence.append(dict(recall) if isinstance(recall, Mapping) else {"recall": recall})
    missing = ("recall_applicability",) if unknown else ()
    return ModuleAssessment(status="available", version=RECALLS_VERSION, value=min(6.0, penalty), evidence=tuple(evidence), missing_data=missing)


def _get(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, Mapping) else getattr(value, key, None)
