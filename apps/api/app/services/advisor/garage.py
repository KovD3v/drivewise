from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.schemas.advisor import AdvisorRecommendationRequest
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


def garage_fit(
    request: AdvisorRecommendationRequest | dict[str, Any],
    candidate: dict[str, Any],
) -> ModuleAssessment:
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
    values = {key: _number(value) for key, value in required.items()}
    missing = tuple(key for key, value in values.items() if value is None)
    pairs = {
        "length_mm": ("garage.useful_length_mm", "vehicle.length_mm"),
        "width_mm": ("garage.useful_width_mm", "vehicle.body_width_mm"),
        "height_mm": ("garage.useful_height_mm", "vehicle.height_mm"),
        "door_width_mm": ("garage.door_width_mm", "vehicle.width_mirrors_folded_mm"),
        "door_height_mm": ("garage.door_height_mm", "vehicle.height_mm"),
    }
    # Subtract the raw values, as before, so integer inputs keep integer margins.
    margins = {
        name: required[garage_key] - required[vehicle_key]
        for name, (garage_key, vehicle_key) in pairs.items()
        if values[garage_key] is not None and values[vehicle_key] is not None
    }
    # A single negative margin proves the vehicle does not fit, even when
    # another dimension is unknown; a fit needs every dimension.
    if any(margin < 0 for margin in margins.values()):
        return ModuleAssessment(
            status="available",
            version=GARAGE_FIT_VERSION,
            value=0.0,
            details={"margins": margins},
            missing_data=missing,
        )
    if missing:
        return ModuleAssessment(
            status="insufficient_data", version=GARAGE_FIT_VERSION, missing_data=missing
        )
    return ModuleAssessment(
        status="available",
        version=GARAGE_FIT_VERSION,
        value=100.0,
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
