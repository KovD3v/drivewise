import json
from drivewise_engine import DecisionEngine, DecisionProfile

engine=DecisionEngine.from_json("drivewise_engine/data/vehicles.json")
profile_data=json.load(open("drivewise_engine/data/profiles.json",encoding="utf-8"))["family_balanced"]
profile=DecisionProfile(**profile_data)

payload=engine.api_payload(profile,5)
print(json.dumps(payload,indent=2,ensure_ascii=False))
