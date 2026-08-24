from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.schemas.guided_decisions import (
    DecisionProfile,
    MissingInformation,
    NextQuestion,
    QuestionConstraints,
)


@dataclass(frozen=True)
class QuestionDefinition:
    key: str
    priority: float
    completion_weight: float
    question: NextQuestion
    is_answered: Callable[[DecisionProfile], bool]
    is_applicable: Callable[[DecisionProfile], bool] = lambda _profile: True


def _has(field_name: str) -> Callable[[DecisionProfile], bool]:
    return lambda profile: getattr(profile, field_name) is not None


def _garage_has(field_name: str) -> Callable[[DecisionProfile], bool]:
    return lambda profile: getattr(profile.garage, field_name) is not None


def _has_garage(profile: DecisionProfile) -> bool:
    return profile.parking is not None and profile.parking.value == "garage"


QUESTION_DEFINITIONS = (
    QuestionDefinition(
        key="budget_eur",
        priority=1.0,
        completion_weight=1.0,
        question=NextQuestion(
            id="budget_eur",
            type="number",
            label="Qual è il budget massimo che vuoi considerare?",
            reason="Il budget definisce quali offerte possono entrare nel confronto.",
            constraints=QuestionConstraints(minimum=1_000, unit="EUR"),
        ),
        is_answered=_has("budget_eur"),
    ),
    QuestionDefinition(
        key="primary_use",
        priority=0.97,
        completion_weight=0.95,
        question=NextQuestion(
            id="primary_use",
            type="single_select",
            label="Quale sarà l'uso principale del veicolo?",
            reason="L'uso principale cambia il peso di spazio, consumi e autonomia.",
            constraints=QuestionConstraints(
                options=["city", "highway", "family", "work", "new_driver"]
            ),
        ),
        is_answered=_has("primary_use"),
    ),
    QuestionDefinition(
        key="annual_km",
        priority=0.92,
        completion_weight=0.90,
        question=NextQuestion(
            id="annual_km",
            type="number",
            label="Quanti chilometri percorri ogni anno?",
            reason=(
                "La percorrenza annua incide sulla scelta dell'alimentazione e "
                "sulla stima dei costi di utilizzo."
            ),
            constraints=QuestionConstraints(minimum=1, unit="km/year"),
        ),
        is_answered=_has("annual_km"),
    ),
    QuestionDefinition(
        key="condition",
        priority=0.82,
        completion_weight=0.55,
        question=NextQuestion(
            id="condition",
            type="single_select",
            label="Vuoi considerare auto nuove, usate o entrambe?",
            reason="La condizione cambia prezzi, disponibilità e controlli necessari.",
            constraints=QuestionConstraints(options=["any", "new", "used"]),
        ),
        is_answered=_has("condition"),
    ),
    QuestionDefinition(
        key="category",
        priority=0.76,
        completion_weight=0.60,
        question=NextQuestion(
            id="category",
            type="single_select",
            label="Hai già in mente una categoria di carrozzeria?",
            reason="La categoria aiuta a restringere spazio, ingombri e tipo di utilizzo.",
            constraints=QuestionConstraints(
                options=[
                    "city_car",
                    "small_hatchback",
                    "hatchback",
                    "crossover",
                    "suv",
                    "sedan",
                    "wagon",
                    "mpv",
                    "van",
                ]
            ),
        ),
        is_answered=_has("category"),
    ),
    QuestionDefinition(
        key="preferred_fuel_type",
        priority=0.68,
        completion_weight=0.40,
        question=NextQuestion(
            id="preferred_fuel_type",
            type="single_select",
            label="Hai una preferenza sull'alimentazione?",
            reason="Una preferenza esplicita può cambiare il ranking, ma resta un vincolo morbido.",
            constraints=QuestionConstraints(
                options=[
                    "diesel",
                    "electric",
                    "full_hybrid_petrol",
                    "hybrid_petrol",
                    "mild_hybrid_petrol",
                    "petrol",
                    "petrol_lpg",
                ]
            ),
        ),
        is_answered=_has("preferred_fuel_type"),
    ),
    QuestionDefinition(
        key="parking",
        priority=0.64,
        completion_weight=0.35,
        question=NextQuestion(
            id="parking",
            type="single_select",
            label="Dove parcheggi normalmente il veicolo?",
            reason="Garage e posto auto possono introdurre vincoli reali di ingombro e ricarica.",
            constraints=QuestionConstraints(
                options=["garage", "covered_space", "outdoor_space", "none"]
            ),
        ),
        is_answered=_has("parking"),
    ),
    QuestionDefinition(
        key="priorities",
        priority=0.55,
        completion_weight=0.30,
        question=NextQuestion(
            id="priorities",
            type="multi_select",
            label="Quali aspetti vuoi privilegiare?",
            reason="Le priorità dichiarate modificano in modo trasparente i pesi del ranking.",
            constraints=QuestionConstraints(
                options=["price", "efficiency_range", "space", "running_cost"]
            ),
        ),
        is_answered=_has("priorities"),
    ),
    QuestionDefinition(
        key="garage.door_width_mm",
        priority=0.80,
        completion_weight=0.40,
        question=NextQuestion(
            id="garage.door_width_mm",
            type="number",
            label="Quanto è larga l'apertura del garage?",
            reason="La larghezza dell'ingresso può escludere un veicolo anche se lo spazio interno è sufficiente.",
            constraints=QuestionConstraints(minimum=1_000, unit="mm"),
        ),
        is_answered=_garage_has("door_width_mm"),
        is_applicable=_has_garage,
    ),
    QuestionDefinition(
        key="garage.useful_width_mm",
        priority=0.74,
        completion_weight=0.35,
        question=NextQuestion(
            id="garage.useful_width_mm",
            type="number",
            label="Qual è la larghezza utile interna del garage?",
            reason="Serve per stimare lo spazio laterale disponibile attorno al veicolo.",
            constraints=QuestionConstraints(minimum=1_000, unit="mm"),
        ),
        is_answered=_garage_has("useful_width_mm"),
        is_applicable=_has_garage,
    ),
    QuestionDefinition(
        key="garage.useful_length_mm",
        priority=0.72,
        completion_weight=0.35,
        question=NextQuestion(
            id="garage.useful_length_mm",
            type="number",
            label="Qual è la lunghezza utile interna del garage?",
            reason="La lunghezza utile permette di verificare l'ingombro longitudinale.",
            constraints=QuestionConstraints(minimum=1_500, unit="mm"),
        ),
        is_answered=_garage_has("useful_length_mm"),
        is_applicable=_has_garage,
    ),
    QuestionDefinition(
        key="garage.door_height_mm",
        priority=0.61,
        completion_weight=0.25,
        question=NextQuestion(
            id="garage.door_height_mm",
            type="number",
            label="Quanto è alta l'apertura del garage?",
            reason="L'altezza dell'ingresso è un vincolo distinto dall'altezza interna.",
            constraints=QuestionConstraints(minimum=1_000, unit="mm"),
        ),
        is_answered=_garage_has("door_height_mm"),
        is_applicable=_has_garage,
    ),
    QuestionDefinition(
        key="garage.useful_height_mm",
        priority=0.50,
        completion_weight=0.20,
        question=NextQuestion(
            id="garage.useful_height_mm",
            type="number",
            label="Qual è l'altezza utile interna del garage?",
            reason="Completa la verifica geometrica dello spazio disponibile.",
            constraints=QuestionConstraints(minimum=1_000, unit="mm"),
        ),
        is_answered=_garage_has("useful_height_mm"),
        is_applicable=_has_garage,
    ),
)


def missing_information(profile: DecisionProfile) -> list[MissingInformation]:
    missing = []
    for definition in QUESTION_DEFINITIONS:
        if not definition.is_applicable(profile) or definition.is_answered(profile):
            continue
        missing.append(
            MissingInformation(
                key=definition.key,
                priority=definition.priority,
                reason=definition.question.reason,
                affects=_affected_components(definition.key),
            )
        )
    return sorted(missing, key=lambda item: (-item.priority, item.key))


def next_question(profile: DecisionProfile) -> NextQuestion | None:
    missing_keys = {item.key for item in missing_information(profile)}
    for definition in sorted(
        QUESTION_DEFINITIONS,
        key=lambda item: (-item.priority, item.key),
    ):
        if definition.key in missing_keys:
            return definition.question
    return None


def profile_completion(profile: DecisionProfile) -> float:
    applicable = [
        definition
        for definition in QUESTION_DEFINITIONS
        if definition.is_applicable(profile)
    ]
    total = sum(definition.completion_weight for definition in applicable)
    completed = sum(
        definition.completion_weight
        for definition in applicable
        if definition.is_answered(profile)
    )
    return round(completed / total, 2) if total else 0.0


def weighted_fact_confidence(profile: DecisionProfile) -> float:
    applicable = [
        definition
        for definition in QUESTION_DEFINITIONS
        if definition.is_applicable(profile)
    ]
    total = sum(definition.completion_weight for definition in applicable)
    if not total:
        return 0.0

    confidence_sum = 0.0
    for definition in applicable:
        fact = _fact_for_key(profile, definition.key)
        if fact is None:
            continue
        confirmation_factor = 1.0 if fact.confirmed else 0.8
        confidence_sum += (
            definition.completion_weight * fact.confidence * confirmation_factor
        )
    return confidence_sum / total


def _fact_for_key(profile: DecisionProfile, key: str):
    if key.startswith("garage."):
        return getattr(profile.garage, key.split(".", maxsplit=1)[1])
    return getattr(profile, key)


def _affected_components(key: str) -> list[str]:
    affected = {
        "budget_eur": ["eligibility", "price_fit"],
        "primary_use": ["use_case_fit", "space", "running_cost"],
        "annual_km": ["running_cost", "efficiency_range"],
        "condition": ["eligibility", "price_fit"],
        "category": ["use_case_fit"],
        "preferred_fuel_type": ["use_case_fit", "running_cost"],
        "parking": ["garage_compatibility", "charging_context"],
        "priorities": ["component_weights"],
    }
    if key.startswith("garage."):
        return ["garage_compatibility"]
    return affected.get(key, [])
