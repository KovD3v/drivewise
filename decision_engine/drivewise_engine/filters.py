from .models import DecisionProfile

def evaluate_hard_filters(profile: DecisionProfile, vehicle: dict):
    failures = []

    if vehicle.get("type") != profile.vehicle_type:
        failures.append("vehicle_type")

    if profile.category and profile.category_is_hard_constraint:
        if vehicle.get("category") != profile.category:
            failures.append("category")

    if profile.automatic_required:
        transmission = vehicle.get("powertrain", {}).get("transmission")
        if transmission not in {"automatic", "single_speed"}:
            failures.append("automatic_required")

    if profile.fuel_constraints:
        fuel = vehicle.get("powertrain", {}).get("fuel")
        if fuel not in profile.fuel_constraints:
            failures.append("fuel_constraint")

    if profile.garage:
        dims = vehicle.get("dimensions", {})
        g = profile.garage
        width = dims.get("width_with_mirrors_mm") or dims.get("width_mm", 0)
        if g.get("length_mm") and dims.get("length_mm", 0) > g["length_mm"]:
            failures.append("garage_length")
        if g.get("door_width_mm") and width > g["door_width_mm"]:
            failures.append("garage_door_width")
        if g.get("door_height_mm") and dims.get("height_mm", 0) > g["door_height_mm"]:
            failures.append("garage_door_height")

    return failures
