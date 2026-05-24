from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_advisor_repository, get_vehicles_repository
from app.main import app


FIAT_ID = UUID("00000000-0000-4000-8000-000000000001")
FIAT_SPEC_ID = UUID("20000000-0000-4000-8000-000000000001")
FIAT_LISTING_ID = UUID("30000000-0000-4000-8000-000000000001")
GOLF_2024_ID = UUID("00000000-0000-4000-8000-000000000003")
GOLF_2023_ID = UUID("00000000-0000-4000-8000-000000000013")
GOLF_2024_SPEC_ID = UUID("20000000-0000-4000-8000-000000000003")
GOLF_2023_SPEC_ID = UUID("20000000-0000-4000-8000-000000000013")


def vehicle_row(
    *,
    vehicle_id: UUID,
    make: str,
    model: str,
    model_year: int,
    body_style: str,
    fuel_type: str,
    market: str,
    base_price_eur: float,
    spec_id: UUID,
    trim: str,
    consumption_l_100km: float | None,
    wltp_range_km: int | None = None,
    co2_g_km: int | None = None,
) -> dict:
    return {
        "id": vehicle_id,
        "make": make,
        "model": model,
        "model_year": model_year,
        "body_style": body_style,
        "fuel_type": fuel_type,
        "market": market,
        "base_price_eur": base_price_eur,
        "spec_id": spec_id,
        "trim": trim,
        "drivetrain": "fwd",
        "transmission": "6-speed manual",
        "engine": trim,
        "horsepower": 100,
        "battery_kwh": None,
        "consumption_l_100km": consumption_l_100km,
        "wltp_range_km": wltp_range_km,
        "co2_g_km": co2_g_km,
        "euro_emission_standard": "Euro 6e",
        "seats": 5,
        "cargo_volume_liters": 300.00,
    }


def candidate_from_row(row: dict, *, listing_price: float, mileage: int) -> dict:
    vehicle = {
        "id": row["id"],
        "make": row["make"],
        "model": row["model"],
        "model_year": row["model_year"],
        "body_style": row["body_style"],
        "fuel_type": row["fuel_type"],
        "market": row["market"],
        "base_price_eur": row["base_price_eur"],
    }
    spec = {
        "id": row["spec_id"],
        "trim": row["trim"],
        "drivetrain": row["drivetrain"],
        "transmission": row["transmission"],
        "engine": row["engine"],
        "horsepower": row["horsepower"],
        "battery_kwh": row["battery_kwh"],
        "consumption_l_100km": row["consumption_l_100km"],
        "wltp_range_km": row["wltp_range_km"],
        "co2_g_km": row["co2_g_km"],
        "euro_emission_standard": row["euro_emission_standard"],
        "seats": row["seats"],
        "cargo_volume_liters": row["cargo_volume_liters"],
    }
    return {
        "vehicle": vehicle,
        "specs": [spec],
        "listings": [
            {
                "id": FIAT_LISTING_ID,
                "vehicle_id": row["id"],
                "source_id": UUID("10000000-0000-4000-8000-000000000001"),
                "listing_ref": f"seed-{row['make']}-{row['model']}",
                "title": f"{row['make']} {row['model']} {row['trim']}",
                "price_eur": listing_price,
                "mileage": mileage,
                "condition": "used",
                "location_region": "Piemonte",
                "listed_at": "2026-01-15",
            }
        ],
    }


FIAT_ROW = vehicle_row(
    vehicle_id=FIAT_ID,
    make="Fiat",
    model="Panda",
    model_year=2024,
    body_style="city_car",
    fuel_type="mild_hybrid_petrol",
    market="IT",
    base_price_eur=15500.00,
    spec_id=FIAT_SPEC_ID,
    trim="1.0 FireFly Hybrid",
    consumption_l_100km=5.00,
    co2_g_km=113,
)

GOLF_2024_ROW = vehicle_row(
    vehicle_id=GOLF_2024_ID,
    make="Volkswagen",
    model="Golf",
    model_year=2024,
    body_style="hatchback",
    fuel_type="petrol",
    market="EU",
    base_price_eur=30250.00,
    spec_id=GOLF_2024_SPEC_ID,
    trim="1.5 TSI",
    consumption_l_100km=5.40,
    co2_g_km=123,
)

GOLF_2023_ROW = vehicle_row(
    vehicle_id=GOLF_2023_ID,
    make="Volkswagen",
    model="Golf",
    model_year=2023,
    body_style="hatchback",
    fuel_type="petrol",
    market="EU",
    base_price_eur=28600.00,
    spec_id=GOLF_2023_SPEC_ID,
    trim="1.5 TSI",
    consumption_l_100km=5.50,
    co2_g_km=125,
)


class FakeVehiclesRepository:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.last_resolve_market = None

    def list_resolve_candidates(self, market):
        self.last_resolve_market = market
        return [row for row in self.rows if row["market"] == market]


class FakeAdvisorRepository:
    def __init__(self, candidates: list[dict]) -> None:
        self.candidates = candidates

    def list_candidates(self):
        return self.candidates


@pytest.fixture
def fake_repositories():
    vehicles_repository = FakeVehiclesRepository(
        [FIAT_ROW, GOLF_2024_ROW, GOLF_2023_ROW]
    )
    advisor_repository = FakeAdvisorRepository(
        [
            candidate_from_row(FIAT_ROW, listing_price=14200.00, mileage=6400),
            candidate_from_row(GOLF_2024_ROW, listing_price=28900.00, mileage=9500),
            candidate_from_row(GOLF_2023_ROW, listing_price=26500.00, mileage=34000),
        ]
    )
    app.dependency_overrides[get_vehicles_repository] = lambda: vehicles_repository
    app.dependency_overrides[get_advisor_repository] = lambda: advisor_repository
    yield vehicles_repository, advisor_repository
    app.dependency_overrides.clear()


@pytest.fixture
def client(fake_repositories):
    return TestClient(app)


def test_post_model_analysis_resolves_query_and_returns_completed_contract(
    client,
    fake_repositories,
):
    vehicles_repository, _ = fake_repositories

    response = client.post(
        "/advisor/model-analysis",
        json={
            "query": "fiat panda 1.0 firefly hybrid 2024",
            "market": "IT",
            "asking_price_eur": 14500,
            "current_km": 6400,
            "usage_profile": ["city", "mixed"],
            "analysis_scope": ["price", "maintenance", "red_flags", "tco"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["resolved_vehicle"]["id"] == str(FIAT_ID)
    assert payload["resolved_spec"]["id"] == str(FIAT_SPEC_ID)
    assert payload["verdict"] == "interesting_with_checks"
    assert payload["price_assessment"] == "in_range"
    assert payload["estimated_costs"]["market_reference_price_eur"] == 14200.00
    assert payload["estimated_costs"]["estimated_annual_maintenance_eur"] > 0
    assert payload["red_flags"] == []
    assert "verify_service_history" in payload["checklist"]
    assert payload["confidence"] >= 0.74
    assert payload["warnings"] == []
    assert payload["missing_data"] == []
    assert payload["next_actions"] == [
        "modify_parameters",
        "open_checklist",
        "compare_alternatives",
    ]
    assert vehicles_repository.last_resolve_market == "IT"


def test_post_model_analysis_returns_low_confidence_for_ambiguous_model(client):
    response = client.post(
        "/advisor/model-analysis",
        json={
            "query": "volkswagen golf 1.5 tsi",
            "market": "EU",
            "asking_price_eur": 28000,
            "current_km": 12000,
            "usage_profile": ["mixed"],
            "analysis_scope": ["price", "red_flags"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "low_confidence"
    assert payload["resolved_vehicle"]["make"] == "Volkswagen"
    assert payload["resolved_spec"]["trim"] == "1.5 TSI"
    assert payload["confidence"] < 0.74
    assert "vehicle_resolution_ambiguous" in payload["warnings"]
    assert payload["next_actions"][0] == "modify_parameters"


def test_post_model_analysis_flags_price_above_range(client):
    response = client.post(
        "/advisor/model-analysis",
        json={
            "query": "fiat panda 1.0 firefly hybrid 2024",
            "market": "IT",
            "asking_price_eur": 19000,
            "current_km": 6400,
            "usage_profile": ["city"],
            "analysis_scope": ["price", "red_flags"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["verdict"] == "risky_at_price"
    assert payload["price_assessment"] == "above_range"
    assert "asking_price_above_reference" in payload["red_flags"]
    assert "asking_price_above_market_reference" in payload["warnings"]
