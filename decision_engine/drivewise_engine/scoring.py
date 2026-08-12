from .utils import clamp
from .tco import tco_score
from .garage import garage_fit
from .powertrain import powertrain_fit_score

def budget_score(profile, vehicle):
    price=float(vehicle.get("pricing",{}).get("new_price_estimate",0) or 0)
    if price<=0 or profile.budget_max<=0: return 50.0
    if price<=profile.budget_max:
        headroom=(profile.budget_max-price)/profile.budget_max
        return clamp(92+min(headroom*18,8))
    over=(price-profile.budget_max)/profile.budget_max
    return clamp(88-over*145)

def category_fit(profile, vehicle):
    if not profile.category: return 82.0
    return 100.0 if vehicle.get("category")==profile.category else 58.0

def usage_fit(profile, vehicle):
    dna=vehicle.get("vehicle_dna",{})
    mapping={
        "family":dna.get("family",70),
        "city":dna.get("city",70),
        "highway":dna.get("travel",70),
        "travel":dna.get("travel",70),
        "work":(dna.get("comfort",70)+dna.get("technology",70))/2,
        "weekend":(dna.get("sport",70)+dna.get("comfort",70))/2,
    }
    vals=[mapping.get(x,70) for x in profile.usage] or [75]
    return sum(vals)/len(vals)

def family_fit(profile, vehicle):
    dna=vehicle.get("vehicle_dna",{})
    score=dna.get("family",70)
    boot=vehicle.get("dimensions",{}).get("boot_liters")
    if profile.children_count>=2 and boot:
        score += 5 if boot>=500 else -8 if boot<380 else 0
    if profile.passengers_usual>=4: score+=2
    return clamp(score)

def pillar_scores(profile, vehicle):
    dna=vehicle.get("vehicle_dna",{})
    reliability=vehicle.get("reliability",{}).get("score",dna.get("reliability",70))
    safety=vehicle.get("safety",{}).get("score",70)

    economics=budget_score(profile,vehicle)*0.45+tco_score(profile,vehicle)*0.40+dna.get("running_cost",70)*0.15
    gf=garage_fit(profile,vehicle)["score"]
    practicality=category_fit(profile,vehicle)*0.22+usage_fit(profile,vehicle)*0.33+family_fit(profile,vehicle)*0.25+gf*0.20
    reliability_safety=reliability*0.58+safety*0.42
    driving=dna.get("comfort",70)*0.48+dna.get("sport",70)*0.22+dna.get("travel",70)*0.30
    technology=dna.get("technology",70)
    powertrain_fit=powertrain_fit_score(profile,vehicle)

    return {
        "economics":round(clamp(economics),2),
        "practicality":round(clamp(practicality),2),
        "reliability_safety":round(clamp(reliability_safety),2),
        "driving":round(clamp(driving),2),
        "technology":round(clamp(technology),2),
        "powertrain_fit":round(clamp(powertrain_fit),2),
    }
