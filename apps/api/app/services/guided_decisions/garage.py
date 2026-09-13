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

    profile_dimensions = {
        "garage.useful_length_mm": profile.garage.useful_length_mm,
        "garage.useful_width_mm": profile.garage.useful_width_mm,
        "garage.useful_height_mm": profile.garage.useful_height_mm,
        "garage.door_width_mm": profile.garage.door_width_mm,
        "garage.door_height_mm": profile.garage.door_height_mm,
    }
    missing_data = [key for key, fact in profile_dimensions.items() if fact is None]
    vehicle_values = {
        "vehicle.length_mm": vehicle_dimensions.length_mm,
        "vehicle.body_width_mm": vehicle_dimensions.body_width_mm,
        "vehicle.height_mm": vehicle_dimensions.height_mm,
        "vehicle.entry_width_mm": vehicle_dimensions.entry_width_mm,
    }
    missing_data.extend(key for key, value in vehicle_values.items() if value is None)

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

    length_margin = profile.garage.useful_length_mm.value - vehicle_dimensions.length_mm
    width_margin = (
        profile.garage.useful_width_mm.value - vehicle_dimensions.body_width_mm
    )
    height_margin = profile.garage.useful_height_mm.value - vehicle_dimensions.height_mm
    door_width_margin = (
        profile.garage.door_width_mm.value - vehicle_dimensions.entry_width_mm
    )
    door_height_margin = (
        profile.garage.door_height_mm.value - vehicle_dimensions.height_mm
    )
    margins = GarageMargins(
        length_mm=length_margin,
        width_mm=width_margin,
        height_mm=height_margin,
        door_width_mm=door_width_margin,
        door_height_mm=door_height_margin,
    )

    if (
        min(
            length_margin,
            width_margin,
            height_margin,
            door_width_margin,
            door_height_margin,
        )
        < 0
    ):
        return GarageCompatibility(
            vehicle_id=vehicle_id,
            spec_id=spec_id,
            status="incompatible",
            message="Il veicolo non è geometricamente compatibile con il garage.",
            margins=margins,
            evaluation_version=GARAGE_EVALUATION_VERSION,
        )

    comfortable = (
        length_margin >= COMFORTABLE_LENGTH_MARGIN_MM
        and width_margin >= COMFORTABLE_TOTAL_WIDTH_MARGIN_MM
        and height_margin >= COMFORTABLE_HEIGHT_MARGIN_MM
        and door_width_margin >= COMFORTABLE_DOOR_WIDTH_MARGIN_MM
        and door_height_margin >= COMFORTABLE_DOOR_HEIGHT_MARGIN_MM
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
