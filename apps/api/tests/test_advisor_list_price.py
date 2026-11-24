"""ADR-013: a variant with no eligible offer is evaluated as new at its list price."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.advisor import AdvisorRecommendationItem, AdvisorRecommendationRequest
from app.services.advisor.scoring import score_recommendations
from app.services.advisor.tco import estimate_tco
from tests.test_advisor_scoring import AS_OF, candidate


def list_price_candidate(index: int, **kwargs: Any) -> dict[str, Any]:
    """The same synthetic variant as `candidate`, with its offer replaced by a list price."""
    priced = candidate(index, condition="new", mileage=None, **kwargs)
    price = priced["spec"]["list_price_eur"]
    priced.update(
        offer=None,
        source=None,
        price_basis="list_price",
        list_price={
            "price_eur": price,
            "computed_from_excl_vat": True,
            "printed_amount_eur": 10_000.01,
            "printed_basis": "excl_vat",
            "vat_rate_percent": 22,
            "trim_label": "Synthetic Trim 50/68",
            "price_list_valid_from": "2026-01-01",
            "substitute_note": None,
            "source_name": "Synthetic manufacturer list",
            "source_url": f"https://example.test/price-lists/{index}",
            "observed_at": "2026-07-15T00:00:00Z",
            "decision_id": UUID(f"40000000-0000-4000-8000-{index:012d}"),
            "observation_id": UUID(f"50000000-0000-4000-8000-{index:012d}"),
        },
    )
    priced["provenance"].append(
        {
            "metric": "list_price_eur",
            "source_name": "Synthetic manufacturer list",
            "source_url": f"https://example.test/price-lists/{index}",
            "observed_at": "2026-07-15T00:00:00Z",
        }
    )
    return priced


def only_item(result) -> AdvisorRecommendationItem:
    assert len(result.items) == 1, result.excluded_counts_by_reason
    return result.items[0]


def test_list_price_uses_the_same_formulas_as_a_new_offer_at_that_price():
    request = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use="family",
        priorities=["price", "space"],
    )
    offer = only_item(
        score_recommendations(
            request,
            [candidate(1, condition="new", mileage=None, price_eur=18_500)],
            as_of=AS_OF,
        )
    )
    listed = only_item(
        score_recommendations(
            request, [list_price_candidate(1, price_eur=18_500)], as_of=AS_OF
        )
    )

    assert (offer.price_basis, listed.price_basis) == ("offer", "list_price")
    assert offer.offer is not None and listed.offer is None
    assert listed.list_price.price_eur == 18_500
    assert listed.list_price.computed_from_excl_vat is True
    for field in (
        "score",
        "decision_status",
        "decision_score",
        "decision_confidence",
        "structural_fit",
        "preference_fit",
        "pillar_scores",
        "component_scores",
        "missing_factors",
        "positive_factors",
        "tradeoffs",
        "evidence",
    ):
        assert getattr(listed, field) == getattr(offer, field), field
    assert listed.evidence["assessments"]["tco"] == offer.evidence["assessments"]["tco"]
    assert listed.condition_group == "new"
    assert any(p.metric == "list_price_eur" for p in listed.provenance)
    assert not any(p.metric == "price_eur" for p in listed.provenance)


def test_tco_reads_the_list_price_as_a_new_vehicle_price():
    request = AdvisorRecommendationRequest(budget_max_eur=20_000, primary_use="city")
    offer = estimate_tco(
        request, candidate(2, condition="new", mileage=None), as_of=AS_OF
    )
    listed = estimate_tco(request, list_price_candidate(2), as_of=AS_OF)
    assert listed.status == offer.status
    assert listed.details == offer.details
    # Insurance and depreciation are the price-driven parts; both are computed.
    assert {"insurance", "depreciation"} <= set(listed.details["annual_eur"])


@pytest.mark.parametrize(
    ("change", "request_fields", "reason"),
    [
        (lambda c: c["provenance"].pop(), {}, "missing_spec_provenance"),
        (lambda c: c["list_price"].update(source_url="http://example.test"), {}, "missing_list_price"),
        (lambda c: c["list_price"].update(decision_id=None), {}, "missing_list_price"),
        (lambda c: c["list_price"].update(price_eur=None), {}, "missing_list_price"),
        # The candidate's price must be the spec's projected, permitted list price.
        (lambda c: c["spec"].update(list_price_eur=None), {}, "missing_list_price"),
        (lambda c: None, {"condition": "used"}, "condition_mismatch"),
        (lambda c: None, {"budget_max_eur": 15_000}, "above_budget_tolerance"),
        (lambda c: c["spec"].update(seats=None), {}, "missing_seats"),
    ],
)
def test_list_price_candidates_keep_every_gate(change, request_fields, reason):
    priced = list_price_candidate(3)
    change(priced)
    request = AdvisorRecommendationRequest(
        **{"budget_max_eur": 20_000, "primary_use": "city", **request_fields}
    )
    result = score_recommendations(request, [priced], as_of=AS_OF)
    assert not result.items
    assert result.excluded_counts_by_reason == {reason: 1}


def test_list_price_skips_offer_freshness_and_lands_in_the_new_group():
    request = AdvisorRecommendationRequest(budget_max_eur=20_000, primary_use="city")
    result = score_recommendations(
        request,
        [list_price_candidate(4), candidate(5, condition="used")],
        as_of=AS_OF,
    )
    groups = {group.condition: group.items for group in result.groups}
    assert [item.price_basis for item in groups["new"]] == ["list_price"]
    assert [item.price_basis for item in groups["used"]] == ["offer"]


def test_item_requires_the_source_of_its_price_basis():
    listed = only_item(
        score_recommendations(
            AdvisorRecommendationRequest(budget_max_eur=20_000, primary_use="city"),
            [list_price_candidate(6)],
            as_of=AS_OF,
        )
    )
    payload = listed.model_dump()
    for broken in [
        {"list_price": None},
        {"price_basis": "offer"},
        {"offer": deepcopy(candidate(6)["offer"])},
    ]:
        with pytest.raises(ValidationError, match="present exactly"):
            AdvisorRecommendationItem.model_validate({**payload, **broken})
