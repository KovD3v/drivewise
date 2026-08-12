from datetime import datetime, timezone
from .utils import clamp

SOURCE_RELIABILITY = {
    "manufacturer": 1.00,
    "official_registry": 0.98,
    "euro_ncap": 0.98,
    "partner_api": 0.92,
    "licensed_dataset": 0.90,
    "marketplace": 0.82,
    "editorial": 0.78,
    "community": 0.62,
    "synthetic": 0.45,
    "unknown": 0.50,
}

FRESHNESS_HALF_LIFE_DAYS = {
    "pricing": 60,
    "ownership_costs": 90,
    "recalls": 180,
    "known_issues": 365,
    "reliability": 365,
    "dimensions": 1825,
    "safety": 1825,
    "vehicle_dna": 365,
}

def freshness_score(updated_at, domain):
    if not updated_at:
        return 0.55
    try:
        dt = datetime.fromisoformat(updated_at.replace("Z","+00:00"))
        now = datetime.now(timezone.utc)
        age_days = max(0.0, (now - dt.astimezone(timezone.utc)).total_seconds()/86400)
    except Exception:
        return 0.55

    half_life = FRESHNESS_HALF_LIFE_DAYS.get(domain, 365)
    return max(0.35, 0.5 ** (age_days / half_life))

def source_reliability(source):
    return SOURCE_RELIABILITY.get(source or "unknown", SOURCE_RELIABILITY["unknown"])

def field_confidence(meta, domain):
    if not meta:
        return 0.50
    base = float(meta.get("confidence", 0.8))
    source = source_reliability(meta.get("source"))
    fresh = freshness_score(meta.get("updated_at"), domain)
    verified_bonus = 0.05 if meta.get("verified") else 0.0
    return clamp((base*0.45 + source*0.35 + fresh*0.20 + verified_bonus) * 100) / 100

def vehicle_data_quality(vehicle):
    meta = vehicle.get("data_metadata", {})
    domains = [
        "pricing","dimensions","reliability","safety",
        "vehicle_dna","ownership_costs","known_issues","recalls"
    ]
    scores = []
    for d in domains:
        if vehicle.get(d) in (None, {}, []):
            scores.append(0.0)
        else:
            scores.append(field_confidence(meta.get(d), d))
    if not scores:
        return 0.0
    return round(sum(scores)/len(scores)*100, 1)

def domain_confidences(vehicle):
    meta = vehicle.get("data_metadata", {})
    out = {}
    for d in [
        "pricing","dimensions","reliability","safety",
        "vehicle_dna","ownership_costs","known_issues","recalls"
    ]:
        if vehicle.get(d) in (None, {}, []):
            out[d] = 0.0
        else:
            out[d] = round(field_confidence(meta.get(d), d)*100, 1)
    return out
