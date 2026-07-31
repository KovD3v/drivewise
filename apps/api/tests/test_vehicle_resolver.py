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


def test_resolver_does_not_match_short_make_inside_another_token():
    row = _panda_row(UUID("00000000-0000-4000-8000-000000000013"), "Base")
    row["make"] = "MG"

    response = resolve_vehicle_query(
        VehicleResolveRequest(
            query="AMG Panda 2024",
            market="IT",
            model_year=2024,
            fuel_type="mild_hybrid_petrol",
        ),
        [row],
    )

    assert response.status == "no_match"
    assert response.matches == []


def test_resolver_uses_exact_variant_preferences_and_stable_default_tie_break():
    vehicle_id = UUID("00000000-0000-4000-8000-000000000099")
    petrol_spec_id = UUID("20000000-0000-4000-8000-000000000098")
    electric_spec_id = UUID("20000000-0000-4000-8000-000000000099")
    base_row = {
        "id": vehicle_id,
        "canonical_key": "it-acme-metro-2026",
        "model_family_key": "it-acme-metro",
        "make": "Acme",
        "model": "Metro",
        "model_year": 2026,
        "body_style": "hatchback",
        "fuel_type": "petrol",
        "market": "IT",
        "base_price_eur": 20_000,
        "trim": "Tour",
        "drivetrain": "fwd",
        "transmission": "automatic",
        "engine": "test",
        "horsepower": 100,
        "battery_kwh": None,
        "energy_consumption_kwh_100km": None,
        "consumption_l_100km": 5.0,
        "wltp_range_km": None,
        "co2_g_km": 110,
        "euro_emission_standard": "Euro 6e",
        "seats": 5,
        "cargo_volume_liters": 350,
    }
    petrol_row = {
        **base_row,
        "spec_id": petrol_spec_id,
        "variant_key": "it-acme-metro-2026-tour-petrol",
        "is_default": True,
        "spec_body_style": "hatchback",
        "spec_fuel_type": "petrol",
    }
    electric_row = {
        **base_row,
        "spec_id": electric_spec_id,
        "variant_key": "it-acme-metro-2026-tour-electric",
        "is_default": False,
        "spec_body_style": "suv",
        "spec_fuel_type": "electric",
        "battery_kwh": 60,
        "energy_consumption_kwh_100km": 18.0,
        "consumption_l_100km": None,
        "wltp_range_km": 400,
        "co2_g_km": 0,
        "euro_emission_standard": None,
    }

    preferred = resolve_vehicle_query(
        VehicleResolveRequest(
            query="Metro Tour",
            market="IT",
            fuel_type="electric",
            body_style="suv",
        ),
        [petrol_row, electric_row],
    )
    assert preferred.status == "matched"
    assert preferred.matches[0].spec is not None
    assert preferred.matches[0].spec.id == electric_spec_id
    assert preferred.matches[0].matched_fields == [
        "model",
        "trim",
        "fuel_type",
        "body_style",
    ]

    for rows in ([petrol_row, electric_row], [electric_row, petrol_row]):
        tied = resolve_vehicle_query(
            VehicleResolveRequest(query="Metro Tour", market="IT"),
            rows,
        )
        assert tied.status == "ambiguous"
        assert tied.matches[0].spec is not None
        assert tied.matches[0].spec.id == petrol_spec_id


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
