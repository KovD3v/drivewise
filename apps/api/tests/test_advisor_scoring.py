from uuid import UUID

from app.schemas.advisor import AdvisorRecommendationRequest
from app.services.advisor.scoring import build_recommendations


def candidate(
    *,
    vehicle_id: str,
    make: str,
    model: str,
    body_style: str,
    fuel_type: str,
    base_price_eur: float,
    price_eur: float | None,
    mileage: int | None,
    consumption_l_100km: float | None,
    wltp_range_km: int | None = None,
    co2_g_km: int | None = None,
    seats: int | None = 5,
    cargo_volume_liters: float | None = 300,
) -> dict:
    vehicle_uuid = UUID(vehicle_id)
    listing = None
    if price_eur is not None:
        listing = {
            "id": UUID(vehicle_id.replace("00000000", "30000000", 1)),
            "vehicle_id": vehicle_uuid,
            "source_id": UUID("10000000-0000-4000-8000-000000000001"),
            "listing_ref": f"listing-{model.lower().replace(' ', '-')}",
            "title": f"{make} {model}",
            "price_eur": price_eur,
            "mileage": mileage,
            "condition": "used",
            "location_region": "Piemonte",
            "listed_at": "2026-01-15",
        }

    return {
        "vehicle": {
            "id": vehicle_uuid,
            "make": make,
            "model": model,
            "model_year": 2024,
            "body_style": body_style,
            "fuel_type": fuel_type,
            "market": "IT",
            "base_price_eur": base_price_eur,
        },
        "specs": [
            {
                "id": UUID(vehicle_id.replace("00000000", "20000000", 1)),
                "trim": "Test trim",
                "drivetrain": "fwd",
                "transmission": "manual",
                "engine": "test engine",
                "horsepower": 100,
                "battery_kwh": None,
                "consumption_l_100km": consumption_l_100km,
                "wltp_range_km": wltp_range_km,
                "co2_g_km": co2_g_km,
                "euro_emission_standard": "Euro 6e",
                "seats": seats,
                "cargo_volume_liters": cargo_volume_liters,
            }
        ],
        "listings": [] if listing is None else [listing],
    }


def test_city_use_rewards_small_efficient_vehicle():
    request = AdvisorRecommendationRequest(
        budget_max_eur=22000,
        primary_use="city",
        priorities=["consumption", "price"],
    )
    fiat = candidate(
        vehicle_id="00000000-0000-4000-8000-000000000001",
        make="Fiat",
        model="Panda",
        body_style="city_car",
        fuel_type="mild_hybrid_petrol",
        base_price_eur=15500,
        price_eur=14200,
        mileage=6400,
        consumption_l_100km=5.0,
        co2_g_km=113,
        seats=4,
        cargo_volume_liters=225,
    )
    tesla = candidate(
        vehicle_id="00000000-0000-4000-8000-000000000005",
        make="Tesla",
        model="Model 3",
        body_style="sedan",
        fuel_type="electric",
        base_price_eur=42990,
        price_eur=39700,
        mileage=17600,
        consumption_l_100km=None,
        wltp_range_km=513,
        co2_g_km=0,
        cargo_volume_liters=594,
    )

    recommendations = build_recommendations(request, [tesla, fiat])

    assert recommendations[0].vehicle.make == "Fiat"
    assert recommendations[0].score > recommendations[1].score
    assert recommendations[0].evidence["within_budget"] is True


def test_family_use_rewards_space_and_seats():
    request = AdvisorRecommendationRequest(
        budget_max_eur=35000,
        primary_use="family",
        priorities=["space"],
    )
    spacious = candidate(
        vehicle_id="00000000-0000-4000-8000-000000000003",
        make="Volkswagen",
        model="Golf",
        body_style="hatchback",
        fuel_type="petrol",
        base_price_eur=30250,
        price_eur=28900,
        mileage=9500,
        consumption_l_100km=5.4,
        co2_g_km=123,
        seats=5,
        cargo_volume_liters=381,
    )
    small = candidate(
        vehicle_id="00000000-0000-4000-8000-000000000001",
        make="Fiat",
        model="Panda",
        body_style="city_car",
        fuel_type="mild_hybrid_petrol",
        base_price_eur=15500,
        price_eur=14200,
        mileage=6400,
        consumption_l_100km=5.0,
        co2_g_km=113,
        seats=4,
        cargo_volume_liters=225,
    )

    recommendations = build_recommendations(request, [small, spacious])

    assert recommendations[0].vehicle.make == "Volkswagen"
    assert recommendations[0].evidence["cargo_volume_liters"] == 381


def test_missing_data_is_penalized_but_candidate_is_kept():
    request = AdvisorRecommendationRequest(
        budget_max_eur=25000,
        primary_use="highway",
        priorities=["consumption", "range"],
    )
    missing = candidate(
        vehicle_id="00000000-0000-4000-8000-000000000004",
        make="Dacia",
        model="Sandero",
        body_style="hatchback",
        fuel_type="petrol_lpg",
        base_price_eur=13750,
        price_eur=None,
        mileage=None,
        consumption_l_100km=None,
        wltp_range_km=None,
        co2_g_km=None,
        cargo_volume_liters=None,
    )

    recommendations = build_recommendations(request, [missing])

    assert len(recommendations) == 1
    assert recommendations[0].vehicle.make == "Dacia"
    assert "Missing price data" in recommendations[0].rationale
    assert recommendations[0].evidence["missing_fields"]


def test_budget_max_prefers_closest_listing_when_all_candidates_are_over_budget():
    request = AdvisorRecommendationRequest(
        budget_max_eur=12000,
        primary_use="city",
        priorities=[],
    )
    panda = candidate(
        vehicle_id="00000000-0000-4000-8000-000000000001",
        make="Fiat",
        model="Panda",
        body_style="city_car",
        fuel_type="mild_hybrid_petrol",
        base_price_eur=15500,
        price_eur=14200,
        mileage=6400,
        consumption_l_100km=5.0,
        co2_g_km=113,
        seats=4,
        cargo_volume_liters=225,
    )
    sandero = candidate(
        vehicle_id="00000000-0000-4000-8000-000000000004",
        make="Dacia",
        model="Sandero",
        body_style="hatchback",
        fuel_type="petrol_lpg",
        base_price_eur=13750,
        price_eur=12800,
        mileage=14300,
        consumption_l_100km=6.5,
        co2_g_km=108,
        seats=5,
        cargo_volume_liters=328,
    )

    recommendations = build_recommendations(request, [panda, sandero])

    assert recommendations[0].vehicle.make == "Dacia"
    assert recommendations[0].evidence["price_eur"] == 12800


def test_budget_max_prefers_listing_closest_to_ceiling_over_cheapest_under_budget():
    request = AdvisorRecommendationRequest(
        budget_max_eur=12000,
        primary_use="city",
        priorities=[],
    )
    near_ceiling = candidate(
        vehicle_id="00000000-0000-4000-8000-000000000006",
        make="Seat",
        model="Ibiza",
        body_style="hatchback",
        fuel_type="petrol",
        base_price_eur=13500,
        price_eur=11900,
        mileage=12000,
        consumption_l_100km=5.8,
    )
    cheapest = candidate(
        vehicle_id="00000000-0000-4000-8000-000000000007",
        make="Skoda",
        model="Fabia",
        body_style="hatchback",
        fuel_type="petrol",
        base_price_eur=13200,
        price_eur=9000,
        mileage=12000,
        consumption_l_100km=5.8,
    )

    recommendations = build_recommendations(request, [cheapest, near_ceiling])

    assert recommendations[0].vehicle.make == "Seat"
    assert recommendations[0].evidence["price_eur"] == 11900


def test_budget_max_prefers_in_budget_listing_over_slightly_closer_over_budget():
    request = AdvisorRecommendationRequest(
        budget_max_eur=12000,
        primary_use="city",
        priorities=[],
    )
    in_budget = candidate(
        vehicle_id="00000000-0000-4000-8000-000000000008",
        make="Hyundai",
        model="i20",
        body_style="hatchback",
        fuel_type="petrol",
        base_price_eur=14000,
        price_eur=11900,
        mileage=12000,
        consumption_l_100km=5.8,
    )
    over_budget = candidate(
        vehicle_id="00000000-0000-4000-8000-000000000009",
        make="Kia",
        model="Rio",
        body_style="hatchback",
        fuel_type="petrol",
        base_price_eur=14500,
        price_eur=12100,
        mileage=12000,
        consumption_l_100km=5.8,
    )

    recommendations = build_recommendations(request, [over_budget, in_budget])

    assert recommendations[0].vehicle.make == "Hyundai"
    assert recommendations[0].evidence["within_budget"] is True


def test_budget_min_penalizes_listing_below_requested_range():
    request = AdvisorRecommendationRequest(
        budget_min_eur=10000,
        budget_max_eur=12000,
        primary_use="city",
        priorities=[],
    )
    inside_range = candidate(
        vehicle_id="00000000-0000-4000-8000-000000000010",
        make="Mazda",
        model="2",
        body_style="hatchback",
        fuel_type="petrol",
        base_price_eur=14500,
        price_eur=11000,
        mileage=12000,
        consumption_l_100km=5.8,
    )
    below_range = candidate(
        vehicle_id="00000000-0000-4000-8000-000000000011",
        make="Opel",
        model="Corsa",
        body_style="hatchback",
        fuel_type="petrol",
        base_price_eur=13500,
        price_eur=9000,
        mileage=12000,
        consumption_l_100km=5.8,
    )

    recommendations = build_recommendations(request, [below_range, inside_range])

    assert recommendations[0].vehicle.make == "Mazda"
    assert recommendations[0].evidence["within_budget"] is True


def test_best_listing_for_vehicle_uses_price_closest_to_budget_ceiling():
    request = AdvisorRecommendationRequest(
        budget_max_eur=12000,
        primary_use="city",
        priorities=[],
    )
    vehicle = candidate(
        vehicle_id="00000000-0000-4000-8000-000000000012",
        make="Renault",
        model="Clio",
        body_style="hatchback",
        fuel_type="petrol",
        base_price_eur=14000,
        price_eur=9000,
        mileage=18000,
        consumption_l_100km=5.8,
    )
    higher_listing = dict(vehicle["listings"][0])
    higher_listing["id"] = UUID("30000000-0000-4000-8000-000000000112")
    higher_listing["listing_ref"] = "listing-clio-higher"
    higher_listing["title"] = "Renault Clio higher"
    higher_listing["price_eur"] = 11900
    higher_listing["mileage"] = 12000
    vehicle["listings"].append(higher_listing)

    recommendations = build_recommendations(request, [vehicle])

    assert recommendations[0].best_listing is not None
    assert recommendations[0].best_listing.price_eur == 11900
