from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any

from app.schemas.advisor import AdvisorConstraintModes
from app.schemas.guided_decisions import DecisionFact, DecisionProfile


BODY_STYLE_TERMS = {
    "city car": "city_car",
    "utilitaria": "city_car",
    "berlina compatta": "small_hatchback",
    "compatta": "hatchback",
    "crossover": "crossover",
    "suv": "suv",
    "berlina": "sedan",
    "station wagon": "wagon",
    "familiare": "wagon",
    "monovolume": "mpv",
    "furgone": "van",
    "van": "van",
}

FUEL_TERMS = {
    "diesel": "diesel",
    "elettrica": "electric",
    "elettrico": "electric",
    "full hybrid": "full_hybrid_petrol",
    "ibrida": "hybrid_petrol",
    "ibrido": "hybrid_petrol",
    "mild hybrid": "mild_hybrid_petrol",
    "benzina": "petrol",
    "gpl": "petrol_lpg",
}

PRIORITY_TERMS = {
    "prezzo": "price",
    "budget": "price",
    "consumi": "running_cost",
    "costi di gestione": "running_cost",
    "spazio": "space",
    "bagagliaio": "space",
    "autonomia": "efficiency_range",
    "efficienza": "efficiency_range",
}

GARAGE_DIMENSION_FIELDS = {
    "garage.useful_length_mm": "useful_length_mm",
    "garage.useful_width_mm": "useful_width_mm",
    "garage.useful_height_mm": "useful_height_mm",
    "garage.door_width_mm": "door_width_mm",
    "garage.door_height_mm": "door_height_mm",
}


def extract_profile_updates(
    message: str,
    profile: DecisionProfile,
    *,
    expected_question_id: str | None,
    captured_at: datetime,
) -> tuple[DecisionProfile, list[str]]:
    """Extract a conservative Italian baseline without external model calls.

    This adapter deliberately accepts only high-signal phrases. The decision
    engine is independent from it, so an LLM-backed interpreter can replace it
    without changing the HTTP contract or deterministic scoring layer.
    """

    updated_profile = profile.model_copy(deep=True)
    updated_fields: list[str] = []
    normalized = _normalize(message)

    category = _first_matching_value(normalized, BODY_STYLE_TERMS)
    if category is not None:
        _set_fact(
            updated_profile,
            "category",
            category,
            captured_at,
            confidence=0.98,
            updated_fields=updated_fields,
        )
        _set_fact(
            updated_profile,
            "vehicle_type",
            "car",
            captured_at,
            confidence=0.99,
            source="inferred",
            confirmed=False,
            updated_fields=updated_fields,
        )

    budget = _extract_budget(normalized)
    if budget is not None:
        _set_fact(
            updated_profile,
            "budget_eur",
            float(budget),
            captured_at,
            confidence=0.98,
            updated_fields=updated_fields,
        )

    annual_km = _extract_annual_km(normalized)
    if annual_km is not None:
        _set_fact(
            updated_profile,
            "annual_km",
            annual_km,
            captured_at,
            confidence=0.98,
            updated_fields=updated_fields,
        )

    children_count = _extract_count(normalized, ("figli", "bambini"))
    if children_count is not None:
        _set_fact(
            updated_profile,
            "children_count",
            children_count,
            captured_at,
            confidence=0.98,
            updated_fields=updated_fields,
        )

    passengers_usual = _extract_passengers(normalized)
    if passengers_usual is not None:
        _set_fact(
            updated_profile,
            "passengers_usual",
            passengers_usual,
            captured_at,
            confidence=0.96,
            updated_fields=updated_fields,
        )

    if _contains_any(normalized, ("famiglia", "familiare", "figli", "bambini")):
        _set_fact(
            updated_profile,
            "family",
            True,
            captured_at,
            confidence=0.98,
            updated_fields=updated_fields,
        )
        _set_fact(
            updated_profile,
            "primary_use",
            "family",
            captured_at,
            confidence=0.95,
            updated_fields=updated_fields,
        )
    else:
        primary_use = _extract_primary_use(normalized)
        if primary_use is not None:
            _set_fact(
                updated_profile,
                "primary_use",
                primary_use,
                captured_at,
                confidence=0.95,
                updated_fields=updated_fields,
            )

    condition = _extract_condition(normalized)
    if condition is not None:
        _set_fact(
            updated_profile,
            "condition",
            condition,
            captured_at,
            confidence=0.98,
            updated_fields=updated_fields,
        )

    usage = _extract_usage(normalized)
    if usage:
        _set_fact(
            updated_profile,
            "usage",
            usage,
            captured_at,
            confidence=0.93,
            updated_fields=updated_fields,
        )

    automatic_required = _extract_automatic_required(normalized)
    if automatic_required is not None:
        _set_fact(
            updated_profile,
            "automatic_required",
            automatic_required,
            captured_at,
            confidence=0.99,
            updated_fields=updated_fields,
        )

    _extract_constraint_modes(
        normalized,
        updated_profile,
        updated_fields=updated_fields,
    )

    fuel_type = _first_matching_value(normalized, FUEL_TERMS)
    if fuel_type is not None:
        _set_fact(
            updated_profile,
            "preferred_fuel_type",
            fuel_type,
            captured_at,
            confidence=0.95,
            updated_fields=updated_fields,
        )

    parking = _extract_parking(normalized)
    if parking is not None:
        _set_fact(
            updated_profile,
            "parking",
            parking,
            captured_at,
            confidence=0.98,
            updated_fields=updated_fields,
        )

    priorities = _matching_values(normalized, PRIORITY_TERMS)
    if priorities and (
        expected_question_id == "priorities"
        or _contains_any(
            normalized,
            ("priorita", "importante", "privilegio", "preferisco"),
        )
    ):
        _set_fact(
            updated_profile,
            "priorities",
            priorities,
            captured_at,
            confidence=0.90,
            updated_fields=updated_fields,
        )

    _extract_contextual_answer(
        normalized,
        updated_profile,
        expected_question_id=expected_question_id,
        captured_at=captured_at,
        updated_fields=updated_fields,
    )

    return updated_profile, _deduplicate(updated_fields)


def _extract_contextual_answer(
    normalized: str,
    profile: DecisionProfile,
    *,
    expected_question_id: str | None,
    captured_at: datetime,
    updated_fields: list[str],
) -> None:
    if expected_question_id is None:
        return

    if expected_question_id in GARAGE_DIMENSION_FIELDS:
        millimetres = _standalone_millimetres(normalized)
        if millimetres is None:
            return
        _set_garage_fact(
            profile,
            GARAGE_DIMENSION_FIELDS[expected_question_id],
            millimetres,
            captured_at,
            updated_fields=updated_fields,
        )
        return

    number = _standalone_number(normalized)

    if expected_question_id == "annual_km" and number is not None:
        _set_fact(
            profile,
            "annual_km",
            int(number),
            captured_at,
            confidence=0.96,
            updated_fields=updated_fields,
        )
    elif expected_question_id == "budget_eur" and number is not None:
        _set_fact(
            profile,
            "budget_eur",
            float(number),
            captured_at,
            confidence=0.96,
            updated_fields=updated_fields,
        )
    elif expected_question_id == "parking":
        yes_no = _yes_no(normalized)
        if yes_no is not None:
            _set_fact(
                profile,
                "parking",
                "garage" if yes_no else "none",
                captured_at,
                confidence=0.96,
                updated_fields=updated_fields,
            )


def _set_fact(
    profile: DecisionProfile,
    field_name: str,
    value: Any,
    captured_at: datetime,
    *,
    confidence: float,
    source: str = "user",
    confirmed: bool = True,
    updated_fields: list[str],
) -> None:
    current = getattr(profile, field_name)
    if current is not None and current.value == value:
        return
    setattr(
        profile,
        field_name,
        DecisionFact(
            value=value,
            confidence=confidence,
            source=source,
            confirmed=confirmed,
            updated_at=captured_at,
        ),
    )
    updated_fields.append(field_name)


def _set_garage_fact(
    profile: DecisionProfile,
    field_name: str,
    value: int,
    captured_at: datetime,
    *,
    updated_fields: list[str],
) -> None:
    current = getattr(profile.garage, field_name)
    if current is not None and current.value == value:
        return
    setattr(
        profile.garage,
        field_name,
        DecisionFact(
            value=value,
            confidence=0.96,
            source="user",
            confirmed=True,
            updated_at=captured_at,
        ),
    )
    updated_fields.append(f"garage.{field_name}")


def _extract_budget(normalized: str) -> int | None:
    patterns = (
        r"(?:budget|spendere|massimo|fino a)(?: di| circa| intorno a| sui)?\s*"
        r"(?:euro|eur)?\s*([0-9][0-9\s.,']*(?:k|mila)?)",
        r"([0-9][0-9\s.,']*(?:k|mila)?)\s*(?:euro|eur)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            value = _parse_number(match.group(1))
            if value is not None and value >= 1_000:
                return value
    return None


def _extract_annual_km(normalized: str) -> int | None:
    patterns = (
        r"([0-9][0-9\s.,']*(?:k|mila)?)\s*(?:km|chilometri)\s*"
        r"(?:all anno|annui|l anno|anno)",
        r"(?:all anno|annui|l anno|anno)\s*"
        r"([0-9][0-9\s.,']*(?:k|mila)?)\s*(?:km|chilometri)",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return _parse_number(match.group(1))
    return None


def _extract_primary_use(normalized: str) -> str | None:
    if _contains_any(normalized, ("autostrada", "extraurbano", "lunghi viaggi")):
        return "highway"
    if _contains_any(normalized, ("lavoro", "professionale", "trasporto merci")):
        return "work"
    if _contains_any(normalized, ("neopatentato", "prima auto")):
        return "new_driver"
    if _contains_any(normalized, ("citta", "urbano", "tragitti brevi")):
        return "city"
    return None


_ITALIAN_COUNTS = {
    "uno": 1,
    "una": 1,
    "due": 2,
    "tre": 3,
    "quattro": 4,
    "cinque": 5,
    "sei": 6,
    "sette": 7,
    "otto": 8,
    "nove": 9,
    "dieci": 10,
}


def _extract_count(normalized: str, terms: tuple[str, ...]) -> int | None:
    expression = rf"\b(\d+|{'|'.join(_ITALIAN_COUNTS)})\s+(?:{'|'.join(terms)})\b"
    match = re.search(expression, normalized)
    if match is None:
        return None
    return _count_value(match.group(1))


def _extract_passengers(normalized: str) -> int | None:
    expression = rf"\b(?:siamo|viaggiamo|viaggiano)\s+in\s+(\d+|{'|'.join(_ITALIAN_COUNTS)})\b"
    match = re.search(expression, normalized)
    if match is not None:
        return _count_value(match.group(1))
    return _extract_count(normalized, ("persone", "passeggeri"))


def _count_value(value: str) -> int | None:
    return int(value) if value.isdigit() else _ITALIAN_COUNTS.get(value)


def _extract_usage(normalized: str) -> list[str]:
    terms = (
        ("citta", "city"),
        ("urbano", "city"),
        ("autostrada", "highway"),
        ("extraurbano", "highway"),
        ("lunghi viaggi", "highway"),
        ("lavoro", "work"),
        ("professionale", "work"),
        ("neopatentato", "new_driver"),
        ("prima auto", "new_driver"),
    )
    matches = [
        (normalized.find(term), mapped)
        for term, mapped in terms
        if normalized.find(term) >= 0
    ]
    return _deduplicate([mapped for _, mapped in sorted(matches)])


def _extract_automatic_required(normalized: str) -> bool | None:
    if re.search(
        r"\b(?:automatico|cambio automatico)\b.*\b(?:obbligatorio|required|necessario|solo)\b",
        normalized,
    ):
        return True
    if re.search(r"\b(?:manuale|cambio manuale)\b.*\b(?:va bene|ok|preferito)\b", normalized):
        return False
    return None


def _extract_constraint_modes(
    normalized: str,
    profile: DecisionProfile,
    *,
    updated_fields: list[str],
) -> None:
    changes = {}
    if re.search(r"\b(?:budget|spesa)\b.*\b(?:rigido|fisso|obbligatorio)\b", normalized):
        changes["budget"] = "hard"
    if re.search(r"\b(?:suv|categoria|carrozzeria)\b.*\b(?:obbligatorio|necessario)\b", normalized):
        changes["body_style"] = "hard"
    if re.search(r"\b(?:diesel|benzina|elettric[oa]|ibrid[oa])\b.*\b(?:obbligatorio|necessario)\b", normalized):
        changes["fuel_type"] = "hard"
    if re.search(r"\b(?:automatico|cambio automatico)\b.*\b(?:obbligatorio|required|necessario|solo)\b", normalized):
        changes["transmission"] = "hard"
    if re.search(r"\b(?:garage|box)\b.*\b(?:obbligatorio|necessario)\b", normalized):
        changes["garage"] = "hard"
    if not changes:
        return
    modes = profile.constraint_modes.model_copy(deep=True)
    changed = False
    for field_name, value in changes.items():
        if getattr(modes, field_name) != value:
            setattr(modes, field_name, value)
            changed = True
    if changed:
        profile.constraint_modes = AdvisorConstraintModes.model_validate(modes)
        updated_fields.append("constraint_modes")


def _extract_condition(normalized: str) -> str | None:
    has_new = _contains_any(normalized, ("nuova", "nuovo"))
    has_used = _contains_any(normalized, ("usata", "usato", "seconda mano"))
    if has_new and has_used:
        return "any"
    if has_new:
        return "new"
    if has_used:
        return "used"
    if _contains_any(normalized, ("entrambe", "indifferente")):
        return "any"
    return None


def _extract_parking(normalized: str) -> str | None:
    if normalized in {"garage", "box", "box auto"}:
        return "garage"
    if normalized in {"nessuno", "nessun posto auto"}:
        return "none"
    if re.search(r"\b(non ho|senza) (?:un |il )?garage\b", normalized):
        return "none"
    if re.search(r"\b(ho|dispongo di|uso) (?:un |il )?garage\b", normalized):
        return "garage"
    if _contains_any(normalized, ("posto auto coperto", "parcheggio coperto")):
        return "covered_space"
    if _contains_any(normalized, ("posto auto scoperto", "parcheggio in strada")):
        return "outdoor_space"
    return None


def _yes_no(normalized: str) -> bool | None:
    if normalized in {"si", "certo", "esatto", "confermo"}:
        return True
    if normalized in {"no", "non ce l ho", "non lo ho"}:
        return False
    return None


def _standalone_number(normalized: str) -> int | None:
    match = re.fullmatch(
        r"\s*(?:circa\s+)?([0-9][0-9\s.,']*(?:k|mila)?)\s*"
        r"(?:mm|cm|m|km|euro|eur)?\s*",
        normalized,
    )
    return _parse_number(match.group(1)) if match else None


def _standalone_millimetres(normalized: str) -> int | None:
    match = re.fullmatch(
        r"\s*(?:circa\s+)?([0-9][0-9\s.,']*)\s*(mm|cm|m)?\s*",
        normalized,
    )
    if match is None:
        return None

    raw_value = match.group(1).replace(" ", "").replace("'", "")
    unit = match.group(2) or "mm"
    if unit == "m":
        try:
            metres = float(raw_value.replace(",", "."))
        except ValueError:
            return None
        return round(metres * 1_000)

    number = _parse_number(raw_value)
    if number is None:
        return None
    return number * 10 if unit == "cm" else number


def _parse_number(raw_value: str) -> int | None:
    value = raw_value.strip().lower()
    multiplier = 1
    if value.endswith("mila"):
        multiplier = 1_000
        value = value.removesuffix("mila")
    elif value.endswith("k"):
        multiplier = 1_000
        value = value.removesuffix("k")

    digits = re.sub(r"[^0-9]", "", value)
    if not digits:
        return None
    return int(digits) * multiplier


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    without_accents = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    normalized = re.sub(r"[€?!;:]", " ", without_accents).replace("’", "'")
    return normalized.replace("'", " ").strip()


def _contains_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(term in value for term in terms)


def _first_matching_value(value: str, mapping: dict[str, str]) -> str | None:
    for term, mapped_value in mapping.items():
        if term in value:
            return mapped_value
    return None


def _matching_values(value: str, mapping: dict[str, str]) -> list[str]:
    return _deduplicate(
        [mapped_value for term, mapped_value in mapping.items() if term in value]
    )


def _deduplicate(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
