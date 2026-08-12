PILLAR_LABELS={
    "economics":"Economics",
    "practicality":"Practicality",
    "reliability_safety":"Affidabilità e sicurezza",
    "driving":"Driving",
    "technology":"Technology",
    "powertrain_fit":"Compatibilità motorizzazione",
}

def build_explainability(vehicle, pillars, weights, penalties, data_quality, domain_conf):
    ranked=sorted(pillars.items(), key=lambda x:x[1], reverse=True)
    drivers=[]
    for key,score in ranked[:3]:
        drivers.append({
            "pillar":key,
            "label":PILLAR_LABELS[key],
            "score":round(score,1),
            "weight":round(weights.get(key,0)*100,1),
            "impact":round(score*weights.get(key,0),2),
        })

    risks=[]
    for name,val in penalties.items():
        if val>0:
            risks.append({"type":name,"penalty":val})

    return {
        "top_drivers":drivers,
        "penalties":risks,
        "vehicle_data_quality":data_quality,
        "domain_confidence":domain_conf,
        "summary_template":{
            "best_for":drivers[0]["label"] if drivers else None,
            "main_tradeoff":vehicle.get("tradeoffs",[None])[0] if vehicle.get("tradeoffs") else None
        }
    }
