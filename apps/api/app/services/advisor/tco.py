from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.schemas.advisor import AdvisorRecommendationRequest
from app.services.advisor.decision import ModuleAssessment
from app.services.advisor.energy_prices import (
    ELECTRICITY_PRICE_EUR_PER_KWH,
    ENERGY_ASSUMPTION_VERSION,
    LIQUID_ENERGY_PRICES_EUR_PER_LITER,
)
from app.services.advisor.model_analysis import estimate_annual_maintenance


TCO_VERSION = "tco-v1"
_CENT = Decimal("0.01")


def _money(value: Decimal) -> float:
    return float(value.quantize(_CENT, rounding=ROUND_HALF_UP))


def estimate_tco(
    request: AdvisorRecommendationRequest,
    candidate: dict[str, Any],
    *,
    as_of: datetime,
) -> ModuleAssessment:
    vehicle = candidate.get("vehicle", {})
    spec = candidate.get("spec", {})
    offer = candidate.get("offer", {})
    missing: list[str] = []
    annual: dict[str, float] = {}

    price = offer.get("price_eur")
    if price is not None:
        price_decimal = Decimal(str(price))
        annual["insurance"] = _money(
            min(Decimal("650") + price_decimal * Decimal("0.008"), Decimal("1600"))
        )
        annual["depreciation"] = _money(price_decimal * Decimal("0.09333"))
    else:
        missing.extend(["insurance", "depreciation"])

    fuel_type = spec.get("fuel_type")
    consumption = (
        spec.get("energy_consumption_kwh_100km")
        if fuel_type == "electric"
        else spec.get("consumption_l_100km")
    )
    rate = (
        ELECTRICITY_PRICE_EUR_PER_KWH
        if fuel_type == "electric"
        else LIQUID_ENERGY_PRICES_EUR_PER_LITER.get(fuel_type)
    )
    if consumption is None or rate is None or request.annual_km is None:
        missing.append("consumption")
    else:
        annual["energy"] = _money(
            Decimal(str(consumption))
            * Decimal(str(rate))
            * Decimal(str(request.annual_km))
            / Decimal("100")
        )

    power_kw = spec.get("power_kw")
    if fuel_type == "electric":
        annual["tax"] = 0.0
    elif power_kw is None:
        missing.append("tax")
    else:
        power = Decimal(str(power_kw))
        annual["tax"] = _money(
            power * Decimal("2.58")
            if power <= 100
            else Decimal("100") * Decimal("2.58")
            + (power - Decimal("100")) * Decimal("3.87")
        )

    model_year = vehicle.get("model_year")
    if model_year is None:
        missing.append("maintenance")
    else:
        annual["maintenance"] = estimate_annual_maintenance(
            model_year=model_year,
            current_km=offer.get("mileage"),
            body_style=spec.get("body_style"),
            fuel_type=fuel_type,
            analysis_year=as_of.year,
        )

    tyre_rates = {
        "city_car": 180,
        "small_hatchback": 180,
        "hatchback": 240,
        "sedan": 240,
        "wagon": 240,
        "crossover": 300,
        "suv": 300,
        "mpv": 300,
        "van": 300,
    }
    tyres = tyre_rates.get(spec.get("body_style"))
    if tyres is None:
        missing.append("tyres")
    else:
        annual["tyres"] = float(tyres)

    if "energy" not in annual:
        return ModuleAssessment(
            status="insufficient_data",
            version=TCO_VERSION,
            assumptions=_assumptions(),
            missing_data=tuple(dict.fromkeys(missing)),
        )

    annual["total"] = sum(value for key, value in annual.items() if key != "total")
    return ModuleAssessment(
        status="estimated",
        version=TCO_VERSION,
        value=annual["total"],
        details={"annual_eur": annual},
        assumptions=_assumptions(),
        missing_data=tuple(dict.fromkeys(missing)),
    )


def _assumptions() -> tuple[str, ...]:
    return (
        f"{TCO_VERSION}: annual kilometres come from the request.",
        f"Energy uses MIMIT/ARERA rates ({ENERGY_ASSUMPTION_VERSION}).",
        "Insurance is EUR 650 plus 0.8% of offer price, capped at EUR 1,600.",
        "Tax, maintenance, tyres, and depreciation use the versioned TCO V1 heuristics.",
    )
