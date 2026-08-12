def derive_strengths(vehicle,pillars):
    labels={
        "economics":"Economics molto competitivo",
        "practicality":"Alta praticità per il tuo utilizzo",
        "reliability_safety":"Affidabilità e sicurezza elevate",
        "driving":"Comfort e qualità di marcia convincenti",
        "technology":"Dotazione tecnologica forte",
        "powertrain_fit":"Motorizzazione coerente con il tuo utilizzo",
    }
    ranked=sorted(pillars.items(), key=lambda x:x[1], reverse=True)
    return [labels[k] for k,v in ranked[:3] if v>=78]

def derive_tradeoffs(vehicle,pillars,penalties):
    items=list(vehicle.get("tradeoffs",[]))
    low=sorted(pillars.items(), key=lambda x:x[1])
    labels={
        "economics":"Costi meno favorevoli rispetto ad alcune alternative",
        "practicality":"Praticità non ottimale per il profilo",
        "reliability_safety":"Affidabilità/sicurezza non ai vertici",
        "driving":"Esperienza di guida non prioritaria",
        "technology":"Tecnologia migliorabile",
        "powertrain_fit":"Motorizzazione non ideale per il tuo utilizzo",
    }
    for k,v in low[:2]:
        if v<72 and labels[k] not in items:
            items.insert(0,labels[k])
    if penalties.get("known_issues",0)>=3:
        items.append("Difetti noti da considerare nel confronto")
    if penalties.get("recalls",0)>=2:
        items.append("Verificare eventuali campagne di richiamo")
    return items[:4]
