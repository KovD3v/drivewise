from __future__ import annotations

from dataclasses import dataclass

from app.schemas.guided_decisions import (
    DecisionProfile,
    GarageCompatibility,
    GarageMargins,
)


GARAGE_EVALUATION_VERSION = "garage-fit-v1"

# These are conservative product thresholds, not claims about door-opening
# ergonomics. They remain versioned so they can be calibrated independently.
COMFORTABLE_TOTAL_WIDTH_MARGIN_MM = 600
COMFORTABLE_LENGTH_MARGIN_MM = 500
COMFORTABLE_HEIGHT_MARGIN_MM = 150
COMFORTABLE_DOOR_WIDTH_MARGIN_MM = 200
COMFORTABLE_DOOR_HEIGHT_MARGIN_MM = 100


@dataclass(frozen=True)
class VehicleDimensions:
    length_mm: int | None
    body_width_mm: int | None
    height_mm: int | None
    entry_width_mm: int | None


def evaluate_garage_compatibility(
    profile: DecisionProfile,
    *,
    vehicle_id,
    spec_id,
    vehicle_dimensions: VehicleDimensions,
) -> GarageCompatibility | None:
    if profile.parking is None or profile.parking.value != "garage":
        return None

    garage = profile.garage
    # Each margin pairs one garage measure with the vehicle measure it bounds.
    pairs = {
        "length_mm": (
            ("garage.useful_length_mm", _fact_value(garage.useful_length_mm)),
            ("vehicle.length_mm", vehicle_dimensions.length_mm),
        ),
        "width_mm": (
            ("garage.useful_width_mm", _fact_value(garage.useful_width_mm)),
            ("vehicle.body_width_mm", vehicle_dimensions.body_width_mm),
        ),
        "height_mm": (
            ("garage.useful_height_mm", _fact_value(garage.useful_height_mm)),
            ("vehicle.height_mm", vehicle_dimensions.height_mm),
        ),
        "door_width_mm": (
            ("garage.door_width_mm", _fact_value(garage.door_width_mm)),
            ("vehicle.entry_width_mm", vehicle_dimensions.entry_width_mm),
        ),
        "door_height_mm": (
            ("garage.door_height_mm", _fact_value(garage.door_height_mm)),
            ("vehicle.height_mm", vehicle_dimensions.height_mm),
        ),
    }
    measured: dict[str, int] = {}
    missing_data: list[str] = []
    for margin_name, ((garage_key, garage_value), (vehicle_key, vehicle_value)) in (
        pairs.items()
    ):
        if garage_value is None:
            missing_data.append(garage_key)
        if vehicle_value is None:
            missing_data.append(vehicle_key)
        if garage_value is not None and vehicle_value is not None:
            measured[margin_name] = garage_value - vehicle_value
    missing_data = list(dict.fromkeys(missing_data))
    margins = GarageMargins(**measured)

    # One negative margin proves the vehicle does not fit, whatever else is
    # unknown; every margin is needed only to call the fit comfortable or tight.
    if any(margin < 0 for margin in measured.values()):
        return GarageCompatibility(
            vehicle_id=vehicle_id,
            spec_id=spec_id,
            status="incompatible",
            message="Il veicolo non è geometricamente compatibile con il garage.",
            margins=margins,
            missing_data=missing_data,
            evaluation_version=GARAGE_EVALUATION_VERSION,
        )

    if missing_data:
        return GarageCompatibility(
            vehicle_id=vehicle_id,
            spec_id=spec_id,
            status="insufficient_data",
            message=(
                "Non ci sono ancora misure sufficienti per verificare la "
                "compatibilità con il garage."
            ),
            missing_data=missing_data,
            evaluation_version=GARAGE_EVALUATION_VERSION,
        )

    comfortable = (
        measured["length_mm"] >= COMFORTABLE_LENGTH_MARGIN_MM
        and measured["width_mm"] >= COMFORTABLE_TOTAL_WIDTH_MARGIN_MM
        and measured["height_mm"] >= COMFORTABLE_HEIGHT_MARGIN_MM
        and measured["door_width_mm"] >= COMFORTABLE_DOOR_WIDTH_MARGIN_MM
        and measured["door_height_mm"] >= COMFORTABLE_DOOR_HEIGHT_MARGIN_MM
    )
    if comfortable:
        status = "comfortable"
        message = "Il veicolo entra nel garage con margini geometrici confortevoli."
    else:
        status = "tight"
        message = (
            "Il veicolo entra geometricamente, ma almeno uno dei margini è ridotto."
        )

    return GarageCompatibility(
        vehicle_id=vehicle_id,
        spec_id=spec_id,
        status=status,
        message=message,
        margins=margins,
        evaluation_version=GARAGE_EVALUATION_VERSION,
    )


def _fact_value(fact) -> int | None:
    return None if fact is None else fact.value
