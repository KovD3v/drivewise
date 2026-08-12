def quality_penalties(vehicle):
    penalties={}
    severity={"low":0.8,"medium":2.0,"high":4.0}
    frequency={"rare":0.5,"occasional":1.0,"common":1.6,"common_characteristic":0.4}

    issue_penalty=0.0
    for i in vehicle.get("known_issues",[]):
        issue_penalty += severity.get(i.get("severity"),1.0)*frequency.get(i.get("frequency"),1.0)

    recall_penalty=0.0
    for r in vehicle.get("recalls",[]):
        recall_penalty += {"low":0.8,"medium":2.0,"high":4.0}.get(r.get("severity"),1.0)
        if r.get("status") in {"resolved","ota_completed"}:
            recall_penalty *= 0.25

    penalties["known_issues"]=round(min(issue_penalty,8.0),2)
    penalties["recalls"]=round(min(recall_penalty,6.0),2)
    return penalties
