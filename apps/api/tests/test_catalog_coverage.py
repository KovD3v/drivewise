from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import pytest

from app.schemas.advisor import AdvisorRecommendationRequest
from app.services.advisor.scoring import score_recommendations


ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = ROOT / "data/fixtures/catalog/catalog-v1.synthetic.json"
BODY_STYLES = {
    "city_car",
    "crossover",
    "hatchback",
    "mpv",
    "sedan",
    "small_hatchback",
    "suv",
    "van",
    "wagon",
}
FUEL_TYPES = {
    "diesel",
    "electric",
    "full_hybrid_petrol",
    "hybrid_petrol",
    "mild_hybrid_petrol",
    "petrol",
    "petrol_lpg",
}
PRIMARY_USES = ("city", "highway", "family", "work", "new_driver")


def load_fixture_candidates() -> tuple[list[dict[str, Any]], datetime]:
    payload = json.loads(FIXTURE_PATH.read_text())
    vehicles = {
        vehicle["canonical_key"]: vehicle for vehicle in payload["vehicles"]
    }
    variants = {
        variant["variant_key"]: variant for variant in payload["variants"]
    }
    sources = {source["source_key"]: source for source in payload["sources"]}
    candidates = []

    for listing in payload["listings"]:
        variant = variants[listing["variant_key"]]
        vehicle = vehicles[variant["vehicle_key"]]
        source = sources[listing["source_key"]]
        vehicle_id = uuid5(NAMESPACE_URL, vehicle["canonical_key"])
        spec_id = uuid5(NAMESPACE_URL, variant["variant_key"])
        offer_id = uuid5(
            NAMESPACE_URL,
            f"{listing['source_key']}:{listing['listing_ref']}",
        )
        provenance = []
        for claim in variant["provenance_claims"]:
            claim_source = sources[claim["source_key"]]
            provenance.extend(
                {
                    "metric": metric,
                    "source_name": claim_source["name"],
                    "source_url": claim["source_url"],
                    "observed_at": claim["observed_at"],
                }
                for metric in claim["supported_metrics"]
            )
        candidates.append(
            {
                "vehicle": {
                    "id": vehicle_id,
                    "canonical_key": vehicle["canonical_key"],
                    "model_family_key": vehicle["model_family_key"],
                    "make": vehicle["make"],
                    "model": vehicle["model"],
                    "model_year": vehicle["model_year"],
                    "body_style": variant["body_style"],
                    "fuel_type": variant["fuel_type"],
                    "market": vehicle["market"],
                    "base_price_eur": listing["price_eur"],
                },
                "spec": {
                    "id": spec_id,
                    "variant_key": variant["variant_key"],
                    "is_default": variant["is_default"],
                    "trim": variant["trim"],
                    "body_style": variant["body_style"],
                    "fuel_type": variant["fuel_type"],
                    "list_price_eur": variant.get("list_price_eur"),
                    "drivetrain": variant.get("drivetrain"),
                    "transmission": variant.get("transmission"),
                    "engine": variant.get("engine"),
                    "horsepower": variant.get("horsepower"),
                    "battery_kwh": variant.get("battery_kwh"),
                    "energy_consumption_kwh_100km": variant.get(
                        "energy_consumption_kwh_100km"
                    ),
                    "consumption_l_100km": variant.get("consumption_l_100km"),
                    "wltp_range_km": variant.get("wltp_range_km"),
                    "co2_g_km": variant.get("co2_g_km"),
                    "euro_emission_standard": variant.get(
                        "euro_emission_standard"
                    ),
                    "seats": variant["seats"],
                    "cargo_volume_liters": variant["cargo_volume_liters"],
                },
                "offer": {
                    "id": offer_id,
                    "vehicle_id": vehicle_id,
                    "spec_id": spec_id,
                    "source_id": uuid5(NAMESPACE_URL, listing["source_key"]),
                    "listing_ref": listing["listing_ref"],
                    "title": listing["title"],
                    "price_eur": listing["price_eur"],
                    "mileage": listing.get("mileage"),
                    "condition": listing["condition"],
                    "location_region": listing.get("location_region"),
                    "source_url": listing["source_url"],
                    "listed_at": listing.get("listed_at"),
                    "last_seen_at": listing["observed_at"],
                    "valid_until": listing.get("valid_until"),
                    "is_active": listing["is_active"],
                },
                "reviewed": True,
                "source": {
                    "name": source["name"],
                    "license": source["license"],
                    "ranking_permission": source["ranking_permission"],
                },
                "import_status": "completed",
                "provenance": provenance,
            }
        )

    # The committed observation time is deliberately the test clock. Using a
    # wall-clock value would make this coverage test expire after 30 days.
    as_of = datetime.fromisoformat(payload["listings"][0]["observed_at"])
    assert all(
        listing["observed_at"] == payload["listings"][0]["observed_at"]
        for listing in payload["listings"]
    )
    return candidates, as_of


def rankable_candidates() -> list[dict[str, Any]]:
    candidates, as_of = load_fixture_candidates()
    request = AdvisorRecommendationRequest(
        budget_max_eur=60_000,
        primary_use="city",
    )
    return [
        candidate
        for candidate in candidates
        if score_recommendations(request, [candidate], as_of=as_of).items
    ]


def test_fixture_has_required_catalog_scale_and_price_shape():
    payload = json.loads(FIXTURE_PATH.read_text())
    prices = [listing["price_eur"] for listing in payload["listings"]]
    conditions = Counter(
        "new" if listing["condition"] == "new" else "used"
        for listing in payload["listings"]
    )

    assert len(payload["vehicles"]) >= 24
    assert len({vehicle["make"] for vehicle in payload["vehicles"]}) >= 6
    assert conditions["new"] >= 8
    assert conditions["used"] >= 16
    assert min(prices) == 7_000
    assert max(prices) == 60_000
    assert sum(price < 12_000 for price in prices) >= 4
    assert sum(price > 35_000 for price in prices) >= 4


@pytest.mark.parametrize("body_style", sorted(BODY_STYLES))
def test_each_body_style_has_two_rankable_offers(body_style):
    counts = Counter(
        candidate["spec"]["body_style"] for candidate in rankable_candidates()
    )

    assert counts[body_style] >= 2


@pytest.mark.parametrize("fuel_type", sorted(FUEL_TYPES))
def test_each_fuel_type_has_two_rankable_offers(fuel_type):
    counts = Counter(
        candidate["spec"]["fuel_type"] for candidate in rankable_candidates()
    )

    assert counts[fuel_type] >= 2


@pytest.mark.parametrize("primary_use", PRIMARY_USES)
def test_every_primary_use_returns_new_and_used_groups(primary_use):
    candidates, as_of = load_fixture_candidates()
    request = AdvisorRecommendationRequest(
        budget_max_eur=60_000,
        primary_use=primary_use,
    )

    result = score_recommendations(request, candidates, as_of=as_of)
    groups = {group.condition: group.items for group in result.groups}

    assert groups["new"]
    assert groups["used"]


def test_deliberately_unrankable_offers_keep_exclusions_observable():
    candidates, as_of = load_fixture_candidates()
    request = AdvisorRecommendationRequest(
        budget_max_eur=60_000,
        primary_use="city",
    )

    result = score_recommendations(request, candidates, as_of=as_of)

    assert result.excluded_counts_by_reason["source_not_permitted"] == 1
    assert result.excluded_counts_by_reason["inactive_offer"] == 1


def test_multiple_variants_are_deduplicated_per_family_and_group():
    candidates, as_of = load_fixture_candidates()
    family_counts = Counter(
        candidate["vehicle"]["model_family_key"] for candidate in candidates
    )
    multi_variant_families = {
        family for family, count in family_counts.items() if count > 1
    }
    multi_variant_candidates = [
        candidate
        for candidate in candidates
        if candidate["vehicle"]["model_family_key"] in multi_variant_families
    ]
    request = AdvisorRecommendationRequest(
        budget_max_eur=60_000,
        primary_use="city",
        condition="new",
    )

    result = score_recommendations(
        request,
        multi_variant_candidates,
        as_of=as_of,
    )
    ranked_families = [
        item.vehicle.model_family_key for item in result.groups[0].items
    ]

    assert len(multi_variant_families) >= 3
    assert len(multi_variant_candidates) > len(ranked_families)
    assert len(ranked_families) == len(set(ranked_families))
    assert set(ranked_families) == multi_variant_families
