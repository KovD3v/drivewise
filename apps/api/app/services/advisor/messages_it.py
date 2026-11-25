"""Italian user-facing text for the Advisor.

Scoring decides every number; this module only words the results. Keeping the
prose here means a wording change can never touch a score, a ranking or the
structured fields of an ``AdvisorFactor`` (component, metric, value, threshold,
contribution). Every figure quoted below comes from the shared constants, so
the text cannot drift from the numbers the scorer uses.
"""

from __future__ import annotations

from app.services.advisor.energy_prices import (
    ELECTRICITY_PRICE_EUR_PER_KWH,
    ENERGY_ASSUMPTION_VERSION,
    ENERGY_PRICES_OBSERVED_AT,
    LIQUID_ENERGY_PRICES_EUR_PER_LITER,
)


PRIMARY_USE_LABELS = {
    "city": "città",
    "highway": "autostrada ed extraurbano",
    "family": "famiglia",
    "work": "lavoro",
    "new_driver": "neopatentato",
}

POSITIVE_FACTOR_MESSAGES = {
    "price_fit": "Il prezzo usa bene il budget disponibile.",
    "use_case_fit": "Carrozzeria e preferenze sono adatte all'uso principale.",
    "running_cost": "Il costo energia stimato è contenuto.",
    "space": "Posti e bagagliaio offrono una buona versatilità.",
    "efficiency_range": "Efficienza e autonomia sono competitive.",
}

TRADEOFF_FACTOR_MESSAGES = {
    "price_fit": "Il prezzo lascia poco margine nel budget.",
    "use_case_fit": "Carrozzeria o preferenze si adattano poco all'uso.",
    "running_cost": "Il costo energia stimato è elevato.",
    "space": "Posti o bagagliaio sono sotto la fascia più versatile.",
    "efficiency_range": "Efficienza o autonomia sono sotto la fascia migliore.",
}

# Soft constraints the user accepted to bend: the factor keeps the code in
# ``value`` and shows this sentence as ``message``.
SOFT_TRADEOFF_MESSAGES = {
    "above_budget": "il prezzo supera di poco il budget indicato.",
    "body_style_mismatch": "la carrozzeria è diversa da quella preferita.",
    "fuel_type_mismatch": "l'alimentazione è diversa da quella preferita.",
    "transmission_insufficient_data": (
        "non è confermato che il cambio sia automatico."
    ),
    "transmission_mismatch": "il cambio non è automatico.",
    "garage_insufficient_data": (
        "mancano le misure per verificare che il veicolo entri nel garage."
    ),
    "garage_incompatible": "il veicolo non entra nel garage indicato.",
}


def soft_tradeoff_message(code: str) -> str:
    detail = SOFT_TRADEOFF_MESSAGES.get(code, f"{code}.")
    return f"Compromesso accettato: {detail}"


def budget_overrun_message(overrun_eur: float, overrun_percent: float) -> str:
    return (
        "Il prezzo supera il budget massimo di "
        f"EUR {overrun_eur:.2f} ({overrun_percent:.2f}%)."
    )


def annual_distance_assumption(
    annual_km: int, *, primary_use: str, defaulted: bool
) -> str:
    if defaulted:
        label = PRIMARY_USE_LABELS.get(primary_use, primary_use)
        source = f"valore predefinito per l'uso principale «{label}»"
    else:
        source = "indicata nella richiesta"
    return (
        f"Percorrenza annua: {_italian_integer(annual_km)} km ({source}); "
        "serve solo a stimare il costo annuo dell'energia."
    )


RUNNING_COST_SCOPE_ASSUMPTION = (
    "Il costo di gestione considera solo l'energia: manutenzione, bollo, "
    "assicurazione, svalutazione e finanziamento sono esclusi."
)

PRIORITY_LIMIT_ASSUMPTION = (
    "Solo le prime tre priorità, in ordine, contano per l'aderenza alle "
    "preferenze; le altre restano registrate ma non cambiano il punteggio."
)


def energy_assumptions() -> list[str]:
    observed = ENERGY_PRICES_OBSERVED_AT.strftime("%d/%m/%Y")
    fuels = LIQUID_ENERGY_PRICES_EUR_PER_LITER
    return [
        (
            f"{ENERGY_ASSUMPTION_VERSION}: media aritmetica MIMIT delle medie "
            f"regionali e provinciali pubblicate il {observed}: benzina "
            f"{_italian_decimal(fuels['petrol'])} EUR/L, gasolio "
            f"{_italian_decimal(fuels['diesel'])} EUR/L, GPL "
            f"{_italian_decimal(fuels['petrol_lpg'])} EUR/L."
        ),
        (
            f"{ENERGY_ASSUMPTION_VERSION}: elettricità "
            f"{_italian_decimal(ELECTRICITY_PRICE_EUR_PER_KWH)} EUR/kWh, ricavata "
            "dal riferimento ARERA per i clienti domestici vulnerabili; non è "
            "una tariffa di ricarica pubblica."
        ),
    ]


def _italian_integer(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _italian_decimal(value: float) -> str:
    return str(value).replace(".", ",")
