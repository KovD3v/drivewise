import json
from pathlib import Path
from drivewise_engine import DecisionEngine, DecisionProfile

ROOT=Path(__file__).parents[1]
DATA=ROOT/"drivewise_engine"/"data"/"vehicles.json"
BENCH=ROOT/"drivewise_engine"/"data"/"calibration_profiles.json"

def test_all_calibration_scenarios_have_acceptable_top2():
    engine=DecisionEngine.from_json(str(DATA))
    scenarios=json.loads(BENCH.read_text(encoding="utf-8"))
    failures=[]
    for s in scenarios:
        profile=DecisionProfile(**s["profile"])
        ranking,_=engine.rank(profile,5)
        ids=[r.vehicle_id for r in ranking[:2]]
        if not any(x in ids for x in s["acceptable_top"]):
            failures.append((s["id"],s["acceptable_top"],ids))
    assert not failures, failures

def test_preference_alignment_exposed():
    engine=DecisionEngine.from_json(str(DATA))
    scenario=json.loads(BENCH.read_text(encoding="utf-8"))[0]
    profile=DecisionProfile(**scenario["profile"])
    payload=engine.api_payload(profile,5)
    exp=payload["ranking"][0]["explainability"]
    assert "preference_alignment" in exp
    assert exp["score_composition"]["preference_fit_weight"] == 35
