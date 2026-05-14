from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_listings_repository, get_vehicles_repository
from app.main import app


FIAT_ID = UUID("00000000-0000-4000-8000-000000000001")
TESLA_ID = UUID("00000000-0000-4000-8000-000000000005")
FIAT_LISTING_ID = UUID("30000000-0000-4000-8000-000000000001")


class FakeVehiclesRepository:
    def __init__(self) -> None:
        self.last_filters = None
        self.vehicles = [
            {
                "id": FIAT_ID,
                "make": "Fiat",
                "model": "Panda",
                "model_year": 2024,
                "body_style": "city_car",
                "fuel_type": "mild_hybrid_petrol",
                "market": "IT",
                "base_price_eur": 15500.00,
            },
            {
                "id": TESLA_ID,
                "make": "Tesla",
                "model": "Model 3",
                "model_year": 2024,
                "body_style": "sedan",
                "fuel_type": "electric",
                "market": "EU",
                "base_price_eur": 42990.00,
            },
        ]

    def list_vehicles(self, filters):
        self.last_filters = filters
        vehicles = self.vehicles
        if filters.make:
            vehicles = [
                vehicle
                for vehicle in vehicles
                if filters.make.lower() in vehicle["make"].lower()
            ]
        return vehicles[filters.offset : filters.offset + filters.limit]

    def get_vehicle(self, vehicle_id):
        if vehicle_id != FIAT_ID:
            return None

        return {
            **self.vehicles[0],
            "specs": [
                {
                    "id": UUID("20000000-0000-4000-8000-000000000001"),
                    "trim": "1.0 FireFly Hybrid",
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
            ],
        }


class FakeListingsRepository:
    def __init__(self) -> None:
        self.last_filters = None
        self.listing = {
            "id": FIAT_LISTING_ID,
            "vehicle_id": FIAT_ID,
            "source_id": UUID("10000000-0000-4000-8000-000000000001"),
            "listing_ref": "seed-fiat-panda-2024-it",
            "title": "Fiat Panda 1.0 FireFly Hybrid",
            "price_eur": 14200.00,
            "mileage": 6400,
            "condition": "used",
            "location_region": "Piemonte",
            "listed_at": "2026-01-15",
            "vehicle": {
                "id": FIAT_ID,
                "make": "Fiat",
                "model": "Panda",
                "model_year": 2024,
                "body_style": "city_car",
                "fuel_type": "mild_hybrid_petrol",
                "market": "IT",
                "base_price_eur": 15500.00,
            },
        }

    def list_listings(self, filters):
        self.last_filters = filters
        if filters.location_region and (
            filters.location_region.lower() not in "Piemonte".lower()
        ):
            return []
        return [self.listing][filters.offset : filters.offset + filters.limit]

    def get_listing(self, listing_id):
        if listing_id != FIAT_LISTING_ID:
            return None
        return self.listing


@pytest.fixture(autouse=True)
def fake_repositories():
    repositories = {
        "vehicles": FakeVehiclesRepository(),
        "listings": FakeListingsRepository(),
    }
    app.dependency_overrides[get_vehicles_repository] = lambda: repositories["vehicles"]
    app.dependency_overrides[get_listings_repository] = lambda: repositories["listings"]
    yield repositories
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_get_vehicles_returns_vehicle_list(client):
    response = client.get("/vehicles")

    assert response.status_code == 200
    assert response.json()[0]["make"] == "Fiat"
    assert response.json()[0]["base_price_eur"] == 15500.00


def test_get_vehicles_filters_by_make(client):
    response = client.get("/vehicles", params={"make": "tes"})

    assert response.status_code == 200
    assert [vehicle["make"] for vehicle in response.json()] == ["Tesla"]


def test_get_vehicles_passes_limit_and_offset(client, fake_repositories):
    response = client.get("/vehicles", params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    assert [vehicle["make"] for vehicle in response.json()] == ["Tesla"]
    assert fake_repositories["vehicles"].last_filters.limit == 1
    assert fake_repositories["vehicles"].last_filters.offset == 1


def test_get_vehicle_returns_specs(client):
    response = client.get(f"/vehicles/{FIAT_ID}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "Panda"
    assert payload["specs"][0]["consumption_l_100km"] == 5.00
    assert payload["specs"][0]["euro_emission_standard"] == "Euro 6e"


def test_get_listings_returns_vehicle_summary(client):
    response = client.get("/listings")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["price_eur"] == 14200.00
    assert payload[0]["mileage"] == 6400
    assert payload[0]["vehicle"]["make"] == "Fiat"


def test_get_listings_passes_limit_offset_and_contains_region(
    client,
    fake_repositories,
):
    response = client.get(
        "/listings",
        params={"location_region": "mont", "limit": 1, "offset": 0},
    )

    assert response.status_code == 200
    assert response.json()[0]["location_region"] == "Piemonte"
    filters = fake_repositories["listings"].last_filters
    assert filters.location_region == "mont"
    assert filters.limit == 1
    assert filters.offset == 0


def test_get_listing_returns_detail(client):
    response = client.get(f"/listings/{FIAT_LISTING_ID}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Fiat Panda 1.0 FireFly Hybrid"
    assert payload["vehicle"]["model"] == "Panda"


def test_get_vehicle_returns_404_for_missing_id(client):
    response = client.get("/vehicles/00000000-0000-4000-8000-999999999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Vehicle not found"}


def test_get_listing_returns_404_for_missing_id(client):
    response = client.get("/listings/30000000-0000-4000-8000-999999999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Listing not found"}
