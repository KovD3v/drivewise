from pathlib import Path
from drivewise_engine import DecisionEngine, DecisionProfile

DATA=Path(__file__).parents[1]/"drivewise_engine"/"data"/"vehicles.json"

def test_family_cost_reliability_prefers_corolla():
    e=DecisionEngine.from_json(str(DATA))
    p=DecisionProfile(
        budget_max=35000,annual_km=22000,
        usage=["family","city","highway"],
        priorities=["reliability","running_cost","comfort"],
        vehicle_type="car",children_count=2,passengers_usual=4
    )
    ranking,_=e.rank(p,5)
    assert ranking[0].vehicle_id=="toyota-corolla-ts-hybrid-2026"

def test_strict_suv_excludes_corolla():
    e=DecisionEngine.from_json(str(DATA))
    p=DecisionProfile(
        budget_max=42000,annual_km=18000,
        usage=["family","city"],priorities=["family","technology","comfort"],
        vehicle_type="car",category="SUV",category_is_hard_constraint=True,
        children_count=2,passengers_usual=4
    )
    ranking,excluded=e.rank(p,5)
    excluded_ids={x["vehicle_id"] for x in excluded}
    assert "toyota-corolla-ts-hybrid-2026" in excluded_ids
    assert ranking[0].vehicle_id in {"kia-sportage-hev-2026","volvo-xc40-b3-2026"}

def test_ev_constraint_returns_tesla():
    e=DecisionEngine.from_json(str(DATA))
    p=DecisionProfile(
        budget_max=50000,annual_km=16000,
        usage=["city","weekend"],priorities=["technology","running_cost","comfort"],
        vehicle_type="car",fuel_constraints=["Electric"]
    )
    ranking,_=e.rank(p,5)
    assert ranking and ranking[0].vehicle_id=="tesla-model-y-rwd-2026"
