import json
from pathlib import Path
from drivewise_engine import DecisionEngine, DecisionProfile
from drivewise_engine.data_quality import vehicle_data_quality, domain_confidences

DATA=Path(__file__).parents[1]/"drivewise_engine"/"data"/"vehicles.json"

def make_engine():
    return DecisionEngine.from_json(str(DATA))

def make_profile():
    return DecisionProfile(
        budget_max=35000,annual_km=22000,
        usage=["family","city","highway"],
        priorities=["reliability","running_cost","comfort"],
        vehicle_type="car",new_or_used="indifferent",
        children_count=2,passengers_usual=4,
        garage={"length_mm":5000,"width_mm":2400,"height_mm":2100,"door_width_mm":2200,"door_height_mm":2050}
    )

def test_api_payload_shape():
    payload=make_engine().api_payload(make_profile(),5)
    assert payload["ranking"]
    assert "decision_id" in payload
    assert "explainability" in payload["ranking"][0]

def test_data_quality_is_not_uniform():
    engine=make_engine()
    qs=[vehicle_data_quality(v) for v in engine.vehicles]
    assert len(set(qs)) > 1

def test_domain_confidence_available():
    v=make_engine().vehicles[0]
    dc=domain_confidences(v)
    assert "pricing" in dc
    assert 0 <= dc["pricing"] <= 100

def test_score_and_confidence_bounds():
    payload=make_engine().api_payload(make_profile(),5)
    for r in payload["ranking"]:
        assert 0 <= r["decision_score"] <= 100
        assert 0 <= r["decision_confidence"] <= 100
        assert 0 <= r["data_quality"] <= 100

def test_explainability_has_top_drivers():
    payload=make_engine().api_payload(make_profile(),5)
    assert payload["ranking"][0]["explainability"]["top_drivers"]

def test_missing_metadata_reduces_quality():
    engine=make_engine()
    vehicle=dict(engine.vehicles[0])
    vehicle["data_metadata"]={}
    assert vehicle_data_quality(vehicle) < vehicle_data_quality(engine.vehicles[0])
