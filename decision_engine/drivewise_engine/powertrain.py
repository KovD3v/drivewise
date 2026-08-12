from .utils import clamp

def powertrain_fit_score(profile, vehicle):
    fuel=vehicle.get("powertrain",{}).get("fuel","")
    km=profile.annual_km
    usage=set(profile.usage)
    score=75.0

    if fuel=="Electric":
        score=82
        if km>30000: score+=4
        if "city" in usage: score+=6
        if "highway" in usage: score-=6
    elif fuel in {"Full Hybrid","Hybrid","Mild Hybrid"}:
        score=86
        if "city" in usage: score+=5
        if km>30000 and "highway" in usage: score-=4
    elif fuel=="Diesel":
        score=78
        if km>=22000: score+=8
        if "highway" in usage: score+=7
        if "city" in usage and km<18000: score-=12
    elif fuel=="Petrol":
        score=78
        if km<15000: score+=7
        if km>25000: score-=8

    return clamp(score)
