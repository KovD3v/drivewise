from .utils import clamp
from .scoring import budget_score

RANK_WEIGHTS = [0.50, 0.30, 0.20]

def _space_score(vehicle):
    boot = vehicle.get("dimensions", {}).get("boot_liters")
    if not boot:
        return 70.0
    return clamp(55 + (boot - 300) * 0.12)

def preference_metric(profile, vehicle, key):
    dna = vehicle.get("vehicle_dna", {})
    if key == "reliability":
        return vehicle.get("reliability", {}).get("score", dna.get("reliability", 70))
    if key == "safety":
        return vehicle.get("safety", {}).get("score", 70)
    if key == "running_cost":
        return dna.get("running_cost", 70)
    if key == "comfort":
        return dna.get("comfort", 70)
    if key == "technology":
        return dna.get("technology", 70)
    if key in {"performance", "sport"}:
        return dna.get("sport", 70)
    if key == "family":
        return dna.get("family", 70)
    if key == "space":
        return _space_score(vehicle)
    if key == "budget":
        return budget_score(profile, vehicle)
    return 70.0

def preference_alignment(profile, vehicle):
    priorities = profile.priorities[:3]
    if not priorities:
        return {"score": 70.0, "details": []}

    details = []
    weighted = 0.0
    used_weight = 0.0

    for index, priority in enumerate(priorities):
        weight = RANK_WEIGHTS[index]
        score = preference_metric(profile, vehicle, priority)
        weighted += score * weight
        used_weight += weight
        details.append({
            "priority": priority,
            "rank": index + 1,
            "score": round(score, 1),
            "weight": round(weight * 100, 1)
        })

    return {
        "score": round(weighted / used_weight, 2),
        "details": details
    }
