from .utils import clamp
from .data_quality import vehicle_data_quality

PROFILE_FIELD_WEIGHTS={
    "budget_max":0.18,"annual_km":0.16,"usage":0.16,"priorities":0.18,
    "vehicle_type":0.08,"category":0.06,"new_or_used":0.06,
    "garage":0.06,"children_count":0.03,"passengers_usual":0.03,
}

def profile_completeness(profile):
    total=0
    for field,w in PROFILE_FIELD_WEIGHTS.items():
        value=getattr(profile,field,None)
        if field=="children_count" and value==0: continue
        if value not in (None,"",[],{}):
            total+=w
    return round(clamp(total*100),1)

def ranking_stability(scores):
    if len(scores)<2: return 70.0
    gap=scores[0]-scores[1]
    return clamp(60+gap*4.5)

def decision_confidence(profile_score, data_quality, stability):
    return round(clamp(profile_score*0.45+data_quality*0.35+stability*0.20),1)
