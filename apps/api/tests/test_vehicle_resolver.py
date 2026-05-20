from uuid import UUID

from app.schemas.vehicles import VehicleResolveRequest
from app.services.vehicles.resolver import resolve_vehicle_query


GOLF_ID = UUID("00000000-0000-4000-8000-000000000003")
GOLF_SPEC_ID = UUID("20000000-0000-4000-8000-000000000003")
TOYOTA_ID = UUID("00000000-0000-4000-8000-000000000002")
TOYOTA_SPEC_ID = UUID("20000000-0000-4000-8000-000000000002")


def test_resolver_matches_model_and_trim_when_make_is_missing():
    response = resolve_vehicle_query(
        VehicleResolveRequest(query="Golf 1.5 tsi", market="EU"),
        [
            {
                "id": GOLF_ID,
                "make": "Volkswagen",
                "model": "Golf",
                "model_year": 2024,
                "body_style": "hatchback",
                "fuel_type": "petrol",
                "market": "EU",
                "base_price_eur": 30250.00,
                "spec_id": GOLF_SPEC_ID,
                "trim": "1.5 TSI",
                "drivetrain": "fwd",
                "transmission": "6-speed manual",
                "engine": "1.5L turbo petrol",
                "horsepower": 150,
                "battery_kwh": None,
                "consumption_l_100km": 5.40,
                "wltp_range_km": None,
                "co2_g_km": 123,
                "euro_emission_standard": "Euro 6e",
                "seats": 5,
                "cargo_volume_liters": 381.00,
            }
        ],
    )

    assert response.status == "matched"
    assert response.matches[0].confidence >= 0.82
    assert response.matches[0].match_level == "spec"
    assert response.matches[0].vehicle.id == GOLF_ID
    assert response.matches[0].spec.id == GOLF_SPEC_ID
    assert response.matches[0].matched_fields == ["model", "trim"]


def test_resolver_uses_distinctive_trim_token_for_partial_model_match():
    response = resolve_vehicle_query(
        VehicleResolveRequest(query="toyota yaris active", market="IT"),
        [
            {
                "id": TOYOTA_ID,
                "make": "Toyota",
                "model": "Yaris Hybrid",
                "model_year": 2024,
                "body_style": "hatchback",
                "fuel_type": "hybrid_petrol",
                "market": "IT",
                "base_price_eur": 24550.00,
                "spec_id": TOYOTA_SPEC_ID,
                "trim": "1.5 Hybrid Active",
                "drivetrain": "fwd",
                "transmission": "ecvt",
                "engine": "1.5L full-hybrid petrol",
                "horsepower": 116,
                "battery_kwh": None,
                "consumption_l_100km": 3.80,
                "wltp_range_km": None,
                "co2_g_km": 87,
                "euro_emission_standard": "Euro 6e",
                "seats": 5,
                "cargo_volume_liters": 286.00,
            }
        ],
    )

    assert response.status == "matched"
    assert response.matches[0].confidence >= 0.82
    assert response.matches[0].vehicle.id == TOYOTA_ID
    assert response.matches[0].matched_fields == ["make", "model", "trim"]


def test_resolver_marks_close_candidates_as_ambiguous():
    rows = [
        _panda_row(UUID("00000000-0000-4000-8000-000000000011"), "Base"),
        _panda_row(UUID("00000000-0000-4000-8000-000000000012"), "City"),
    ]

    response = resolve_vehicle_query(
        VehicleResolveRequest(
            query="fiat panda 2024",
            market="IT",
            model_year=2024,
            fuel_type="mild_hybrid_petrol",
            body_style="city_car",
        ),
        rows,
    )

    assert response.status == "ambiguous"
    assert len(response.matches) == 2
    assert response.matches[0].confidence == response.matches[1].confidence


def test_resolver_keeps_ambiguity_when_response_limit_is_one():
    rows = [
        _panda_row(UUID("00000000-0000-4000-8000-000000000011"), "Hybrid"),
        _panda_row(
            UUID("00000000-0000-4000-8000-000000000012"),
            "FireFly Hybrid",
        ),
    ]

    response = resolve_vehicle_query(
        VehicleResolveRequest(
            query="fiat panda hybrid 2024",
            market="IT",
            model_year=2024,
            fuel_type="mild_hybrid_petrol",
            body_style="city_car",
            limit=1,
        ),
        rows,
    )

    assert response.status == "ambiguous"
    assert len(response.matches) == 1


def _panda_row(vehicle_id: UUID, trim: str):
    return {
        "id": vehicle_id,
        "make": "Fiat",
        "model": "Panda",
        "model_year": 2024,
        "body_style": "city_car",
        "fuel_type": "mild_hybrid_petrol",
        "market": "IT",
        "base_price_eur": 15500.00,
        "spec_id": UUID(f"20000000-0000-4000-8000-{vehicle_id.int % 1000:012d}"),
        "trim": trim,
        "drivetrain": "fwd",
        "transmission": "6-speed manual",
        "engine": "1.0L mild-hybrid petrol",
        "horsepower": 70,
        "battery_kwh": None,
        "consumption_l_100km": 5.00,
        "wltp_range_km": None,
        "co2_g_km": 113,
        "euro_emission_standard": "Euro 6e",
        "seats": 4,
        "cargo_volume_liters": 225.00,
    }
