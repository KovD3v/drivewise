import json, uuid
from pathlib import Path
from .models import VehicleScore
from .filters import evaluate_hard_filters
from .scoring import pillar_scores
from .penalties import quality_penalties
from .confidence import profile_completeness, ranking_stability, decision_confidence
from .data_quality import vehicle_data_quality, domain_confidences
from .explainability import build_explainability
from .tradeoffs import derive_strengths, derive_tradeoffs
from .preference import preference_alignment
from .utils import normalize_weights

BASE_WEIGHTS={'economics': 0.266667, 'practicality': 0.177778, 'reliability_safety': 0.222222, 'driving': 0.111111, 'technology': 0.111111, 'powertrain_fit': 0.111111}

PRIORITY_TO_PILLAR={
    "reliability":"reliability_safety","safety":"reliability_safety",
    "running_cost":"economics","costs":"economics","budget":"economics",
    "comfort":"driving","performance":"driving","sport":"driving",
    "technology":"technology","family":"practicality","space":"practicality",
    "fuel":"powertrain_fit",
}

class DecisionEngine:
    def __init__(self,vehicles):
        self.vehicles=vehicles

    @classmethod
    def from_json(cls,path):
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def weights_for_profile(self,profile):
        w=dict(BASE_WEIGHTS); boosts=[0.12,0.08,0.05]
        for i,p in enumerate(profile.priorities[:3]):
            pillar=PRIORITY_TO_PILLAR.get(p)
            if pillar: w[pillar]+=boosts[i]
        return normalize_weights(w)

    def _raw(self,profile,vehicle):
        failures=evaluate_hard_filters(profile,vehicle)
        if failures: return None,failures

        pillars=pillar_scores(profile,vehicle)
        weights=self.weights_for_profile(profile)
        penalties=quality_penalties(vehicle)
        base_score=sum(pillars[k]*weights[k] for k in weights)-sum(penalties.values())
        pref=preference_alignment(profile,vehicle)
        score=base_score*0.65 + pref["score"]*0.35
        return {
            "pillars":pillars,
            "weights":weights,
            "penalties":penalties,
            "base_score":max(0,min(100,base_score)),
            "preference_alignment":pref,
            "score":max(0,min(100,score))
        },[]

    def rank(self,profile,limit=10):
        pcomp=profile_completeness(profile)
        candidates=[]
        excluded=[]

        for v in self.vehicles:
            raw,failures=self._raw(profile,v)
            if failures:
                excluded.append({"vehicle_id":v["id"],"reasons":failures})
            else:
                candidates.append({"vehicle":v,"raw":raw})

        candidates.sort(key=lambda x:x["raw"]["score"],reverse=True)
        stability=ranking_stability([c["raw"]["score"] for c in candidates[:3]])

        final=[]
        for c in candidates[:limit]:
            v=c["vehicle"]; raw=c["raw"]
            dq=vehicle_data_quality(v)
            dc=domain_confidences(v)
            conf=decision_confidence(pcomp,dq,stability)
            explanation=build_explainability(
                v,raw["pillars"],raw["weights"],raw["penalties"],dq,dc
            )
            explanation["preference_alignment"] = raw["preference_alignment"]
            explanation["structural_score"] = round(raw["base_score"], 1)
            explanation["preference_score"] = round(raw["preference_alignment"]["score"], 1)
            explanation["score_composition"] = {
                "structural_fit_weight": 65,
                "preference_fit_weight": 35
            }
            final.append(VehicleScore(
                vehicle_id=v["id"],
                decision_score=round(raw["score"],1),
                decision_confidence=conf,
                profile_completeness=pcomp,
                data_quality=dq,
                pillar_scores=raw["pillars"],
                strengths=derive_strengths(v,raw["pillars"]),
                tradeoffs=derive_tradeoffs(v,raw["pillars"],raw["penalties"]),
                penalties=raw["penalties"],
                explainability=explanation,
            ))
        return final, excluded

    def api_payload(self,profile,limit=5):
        ranking,excluded=self.rank(profile,limit)
        decision_id="dec_"+uuid.uuid4().hex[:12]
        return {
            "decision_id":decision_id,
            "decision_confidence": ranking[0].decision_confidence if ranking else 0,
            "profile_completeness": ranking[0].profile_completeness if ranking else profile_completeness(profile),
            "ranking":[
                {
                    "rank":i+1,
                    "vehicle_id":r.vehicle_id,
                    "decision_score":r.decision_score,
                    "decision_confidence":r.decision_confidence,
                    "data_quality":r.data_quality,
                    "pillars":r.pillar_scores,
                    "strengths":r.strengths,
                    "tradeoffs":r.tradeoffs,
                    "penalties":r.penalties,
                    "explainability":r.explainability,
                }
                for i,r in enumerate(ranking)
            ],
            "excluded":excluded
        }
