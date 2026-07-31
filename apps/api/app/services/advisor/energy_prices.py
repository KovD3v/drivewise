"""Shared Italian energy-price assumptions for the advisor services.

This is the single source of truth for fuel and electricity prices used by
both the recommendation scorer (`scoring.py`) and Model Analysis
(`model_analysis.py`). Keeping the sourced MIMIT/ARERA figures here, instead
of duplicating them per module, ensures `/advisor/recommendations` and
`/advisor/model-analysis` can never quote different running costs for the
same vehicle.

Do not edit the numeric values below without updating the source citation
and `ENERGY_ASSUMPTION_VERSION` together.
"""

from __future__ import annotations

from datetime import date

ENERGY_ASSUMPTION_VERSION = "it-energy-2026-07-16-v1"

MIMIT_SOURCE_NAME = "MIMIT regional fuel-price averages"
MIMIT_SOURCE_URL = "https://www.mimit.gov.it/it/prezzo-medio-carburanti/regioni"
ARERA_SOURCE_NAME = "ARERA Q3 2026 vulnerable-customer reference"
ARERA_SOURCE_URL = (
    "https://www.arera.it/comunicati-stampa/dettaglio/"
    "elettricita-maggior-tutela-46-nel-iii-trimestre-2026-per-i-clienti-vulnerabili"
)

# Date the figures below were actually observed/published. This is
# intentionally a fixed historical date rather than something derived from
# "now": it records when the underlying MIMIT/ARERA data was captured, not
# when the code happens to run.
ENERGY_PRICES_OBSERVED_AT = date(2026, 7, 16)

LIQUID_ENERGY_PRICES_EUR_PER_LITER: dict[str, float] = {
    "petrol": 1.91662,
    "full_hybrid_petrol": 1.91662,
    "hybrid_petrol": 1.91662,
    "mild_hybrid_petrol": 1.91662,
    "diesel": 2.04276,
    "petrol_lpg": 0.77695,
}
ELECTRICITY_PRICE_EUR_PER_KWH = 0.29593

# Flat liquid-fuel rate for call sites that do not distinguish between
# petrol/diesel/LPG (e.g. Model Analysis V1's single-rate cost estimate).
DEFAULT_FUEL_PRICE_EUR_PER_LITER = LIQUID_ENERGY_PRICES_EUR_PER_LITER["petrol"]

ENERGY_ASSUMPTIONS = [
    (
        f"{ENERGY_ASSUMPTION_VERSION}: MIMIT arithmetic mean of published "
        "regional/provincial averages on 2026-07-16: petrol EUR 1.91662/L, "
        "diesel EUR 2.04276/L, LPG EUR 0.77695/L."
    ),
    (
        f"{ENERGY_ASSUMPTION_VERSION}: electricity EUR 0.29593/kWh, inferred "
        "from the ARERA Q3 2026 vulnerable-household reference of EUR 591.86 "
        "for 2,000 kWh/year; this is not a public-charging tariff."
    ),
]


def flat_rate_assumption_sentence() -> str:
    """Prose summary of the flat fuel/electricity rates.

    For call sites (like Model Analysis) whose assumptions list quotes a
    single number per energy type, this derives the sentence directly from
    the shared constants so the prose can never drift from the numbers.
    """
    return (
        f"Fuel is estimated at EUR {DEFAULT_FUEL_PRICE_EUR_PER_LITER:.2f}/L "
        f"and electricity at EUR {ELECTRICITY_PRICE_EUR_PER_KWH:.2f}/kWh "
        f"({ENERGY_ASSUMPTION_VERSION})."
    )
