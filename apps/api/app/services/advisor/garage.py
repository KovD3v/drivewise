from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.services.advisor.decision import ModuleAssessment


FAMILY_FIT_VERSION = "family-fit-v1"
GARAGE_FIT_VERSION = "garage-fit-v1"


def family_fit(
    *, children_count: int | None,
    passengers_usual: int | None,
    candidate: dict[str, Any],
) -> ModuleAssessment:
    children = children_count or 0
    target = min(550, 250 + 75 * children)
    spec = candidate.get("spec") or {}
    seats = _number(spec.get("seats"))
    cargo = _number(spec.get("cargo_volume_liters"))
    missing: list[str] = []
    if passengers_usual is not None and seats is None:
        missing.append("vehicle.seats")
    if cargo is None:
        missing.append("vehicle.cargo_volume_liters")
    if missing:
        return ModuleAssessment(
            status="insufficient_data",
            version=FAMILY_FIT_VERSION,
            details={"cargo_target_liters": target},
            missing_data=tuple(missing),
        )
    return ModuleAssessment(
        status="available",
        version=FAMILY_FIT_VERSION,
        value=min(100.0, cargo / target * 100),
        details={
            "cargo_target_liters": target,
            "cargo_volume_liters": cargo,
            "seats": seats,
            "passengers_usual": passengers_usual,
        },
    )


def garage_fit(request: Any, candidate: dict[str, Any]) -> ModuleAssessment:
    garage = _value(request, "garage")
    if garage is None and isinstance(request, Mapping):
        garage = request
    dimensions = (candidate.get("decision_context") or {}).get("dimensions") or {}
    required = {
        "garage.useful_length_mm": _field(garage, "useful_length_mm"),
        "garage.useful_width_mm": _field(garage, "useful_width_mm"),
        "garage.useful_height_mm": _field(garage, "useful_height_mm"),
        "garage.door_width_mm": _field(garage, "door_width_mm"),
        "garage.door_height_mm": _field(garage, "door_height_mm"),
        "vehicle.length_mm": dimensions.get("length_mm"),
        "vehicle.body_width_mm": dimensions.get("body_width_mm"),
        "vehicle.height_mm": dimensions.get("height_mm"),
        "vehicle.width_mirrors_folded_mm": dimensions.get(
            "width_mirrors_folded_mm"
        ),
    }
    missing = tuple(key for key, value in required.items() if _number(value) is None)
    if missing:
        return ModuleAssessment(
            status="insufficient_data", version=GARAGE_FIT_VERSION, missing_data=missing
        )
    margins = {
        "length_mm": required["garage.useful_length_mm"] - required["vehicle.length_mm"],
        "width_mm": required["garage.useful_width_mm"] - required["vehicle.body_width_mm"],
        "height_mm": required["garage.useful_height_mm"] - required["vehicle.height_mm"],
        "door_width_mm": required["garage.door_width_mm"]
        - required["vehicle.width_mirrors_folded_mm"],
        "door_height_mm": required["garage.door_height_mm"] - required["vehicle.height_mm"],
    }
    return ModuleAssessment(
        status="available",
        version=GARAGE_FIT_VERSION,
        value=100.0 if min(margins.values()) >= 0 else 0.0,
        details={"margins": margins},
    )


def _value(obj: Any, name: str) -> Any:
    return getattr(obj, name, None) if not isinstance(obj, Mapping) else obj.get(name)


def _field(obj: Any, name: str) -> Any:
    value = _value(obj, name)
    if value is None:
        return None
    if isinstance(value, Mapping) or hasattr(value, "value"):
        return _value(value, "value")
    return value


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None
