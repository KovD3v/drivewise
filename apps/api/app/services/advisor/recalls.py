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
    unknown_status = False
    evidence = []
    for recall in recalls:
        applicability = str(_get(recall, "applicability") or "").lower()
        if applicability == "unknown":
            unknown = True
            continue
        state = "match" if applicability in {"applicable", "matched", "match", "confirmed"} else _applicability(candidate, recall)
        if state == "unknown":
            unknown = True
        elif state == "match":
            status = str(_get(recall, "status") or "").strip().lower()
            item = dict(recall) if isinstance(recall, Mapping) else {"recall": recall}
            if status in {"open", "action_required", "action-required"}:
                penalty += float(_get(recall, "penalty") or 6.0)
                evidence.append(item)
            elif status in {"resolved", "closed", "remediated"}:
                evidence.append(item)
            else:
                unknown_status = True
                evidence.append({**item, "status": "unknown"})
    missing = tuple(name for name, flag in (("recall_applicability", unknown), ("recall_status", unknown_status)) if flag)
    return ModuleAssessment(status="available", version=RECALLS_VERSION, value=min(6.0, penalty), evidence=tuple(evidence), missing_data=missing)


def _get(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, Mapping) else getattr(value, key, None)
