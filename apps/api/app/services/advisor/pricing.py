"""Where a candidate's price, condition and mileage come from (ADR-013).

An eligible offer supplies its own terms. A variant with no eligible offer is
evaluated as a new vehicle at its list price. Scoring formulas read these terms
and never need to know which basis supplied them.
"""

from typing import Any, Literal

PriceBasis = Literal["offer", "list_price"]


def price_basis(candidate: dict[str, Any]) -> PriceBasis:
    return "list_price" if candidate.get("price_basis") == "list_price" else "offer"


def priced_terms(candidate: dict[str, Any]) -> dict[str, Any]:
    """Price, condition and mileage as one offer-shaped mapping."""
    if price_basis(candidate) == "list_price":
        list_price = candidate.get("list_price") or {}
        return {
            "price_eur": list_price.get("price_eur"),
            "condition": "new",
            "mileage": None,
        }
    return candidate.get("offer") or {}
