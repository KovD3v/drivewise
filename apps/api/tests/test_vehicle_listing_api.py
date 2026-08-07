from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_listings_repository, get_vehicles_repository
from app.main import app
from app.schemas.vehicles import VehicleSpec


FIAT_ID = UUID("00000000-0000-4000-8000-000000000001")
TESLA_ID = UUID("00000000-0000-4000-8000-000000000005")
FIAT_LISTING_ID = UUID("30000000-0000-4000-8000-000000000001")


class FakeVehiclesRepository:
    def __init__(self) -> None:
        self.last_filters = None
        self.last_resolve_market = None
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
        self.resolve_candidates = [
            {
                "id": FIAT_ID,
                "make": "Fiat",
                "model": "Panda",
                "model_year": 2024,
                "body_style": "city_car",
                "fuel_type": "mild_hybrid_petrol",
                "market": "IT",
                "base_price_eur": 15500.00,
                "spec_id": UUID("20000000-0000-4000-8000-000000000001"),
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
                "spec_id": UUID("20000000-0000-4000-8000-000000000005"),
                "trim": "Rear-Wheel Drive",
                "drivetrain": "rwd",
                "transmission": "single-speed",
                "engine": "single electric motor",
                "horsepower": 283,
                "battery_kwh": 57.50,
                "consumption_l_100km": None,
                "wltp_range_km": 513,
                "co2_g_km": 0,
                "euro_emission_standard": None,
                "seats": 5,
                "cargo_volume_liters": 594.00,
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
                    "identity": {
                        "generation_name": "Third generation",
                        "restyling_label": "2024 update",
                        "category": "city_car",
                        "doors": 5,
                    },
                    "dimensions": {
                        "length_mm": 3653,
                        "width_mm": 1643,
                        "height_mm": 1551,
                        "wheelbase_mm": 2300,
                        "curb_weight_kg": 980,
                        "gross_weight_kg": 1420,
                        "payload_kg": 440,
                        "seats": 4,
                        "cargo_volume_liters": 225.0,
                    },
                    "powertrain": {
                        "engine_description": "1.0L mild-hybrid petrol",
                        "engine_code": "SYN-F10",
                        "displacement_cc": 999,
                        "cylinders": 3,
                        "horsepower": 70,
                        "power_kw": 51.0,
                        "torque_nm": 92,
                        "fuel_type": "mild_hybrid_petrol",
                        "battery_total_kwh": None,
                        "battery_usable_kwh": None,
                        "wltp_range_km": None,
                    },
                    "transmission_details": {
                        "transmission": "6-speed manual",
                        "transmission_type": "manual",
                        "gear_count": 6,
                        "drivetrain": "fwd",
                        "differential_type": "open",
                    },
                    "performance": {
                        "acceleration_0_100_s": 13.9,
                        "top_speed_kmh": 164,
                        "braking_100_0_m": 39.6,
                        "power_to_weight_kw_per_t": 52.04,
                    },
                    "official_efficiency": {
                        "homologation_cycle": "WLTP",
                        "consumption_l_100km": 5.0,
                        "energy_consumption_kwh_100km": None,
                        "co2_g_km": 113,
                        "euro_emission_standard": "Euro 6e",
                    },
                    "maintenance_schedule": [
                        {
                            "id": UUID("40000000-0000-4000-8000-000000000001"),
                            "operation_code": "engine-oil",
                            "title": "Engine oil and filter",
                            "interval_km": 15000,
                            "interval_months": 12,
                            "notes": "Whichever occurs first",
                            "provenance": {
                                "source_id": UUID(
                                    "10000000-0000-4000-8000-000000000001"
                                ),
                                "source_key": "drivewise-synthetic-eu-seed",
                                "source_name": "Drivewise Synthetic EU Seed",
                                "source_url": "https://example.test/maintenance/engine-oil",
                                "source_license": "Synthetic test data",
                                "observed_at": "2026-07-16T09:00:00+02:00",
                            },
                        }
                    ],
                    "safety": {
                        "ratings": [
                            {
                                "id": UUID(
                                    "40000000-0000-4000-8000-000000000002"
                                ),
                                "assessment_system": "Euro NCAP",
                                "assessment_year": 2024,
                                "overall_stars": 4,
                                "adult_occupant_percent": 72,
                                "child_occupant_percent": 70,
                                "vulnerable_road_users_percent": 60,
                                "safety_assist_percent": 62,
                                "provenance": {
                                    "source_id": UUID(
                                        "10000000-0000-4000-8000-000000000001"
                                    ),
                                    "source_key": "drivewise-synthetic-eu-seed",
                                    "source_name": "Drivewise Synthetic EU Seed",
                                    "source_url": "https://example.test/safety/panda",
                                    "source_license": "Synthetic test data",
                                    "observed_at": "2026-07-16T09:00:00+02:00",
                                },
                            }
                        ],
                        "adas": [
                            {
                                "id": UUID(
                                    "40000000-0000-4000-8000-000000000003"
                                ),
                                "feature_key": "lane-support",
                                "category": "adas",
                                "name": "Lane support",
                                "availability": "optional",
                                "notes": None,
                                "provenance": {
                                    "source_id": UUID(
                                        "10000000-0000-4000-8000-000000000001"
                                    ),
                                    "source_key": "drivewise-synthetic-eu-seed",
                                    "source_name": "Drivewise Synthetic EU Seed",
                                    "source_url": "https://example.test/features/lane-support",
                                    "source_license": "Synthetic test data",
                                    "observed_at": "2026-07-16T09:00:00+02:00",
                                },
                            }
                        ],
                        "equipment": [],
                    },
                    "technology_comfort": [
                        {
                            "id": UUID("40000000-0000-4000-8000-000000000004"),
                            "feature_key": "air-conditioning",
                            "category": "comfort",
                            "name": "Air conditioning",
                            "availability": "standard",
                            "notes": None,
                            "provenance": {
                                "source_id": UUID(
                                    "10000000-0000-4000-8000-000000000001"
                                ),
                                "source_key": "drivewise-synthetic-eu-seed",
                                "source_name": "Drivewise Synthetic EU Seed",
                                "source_url": "https://example.test/features/air-conditioning",
                                "source_license": "Synthetic test data",
                                "observed_at": "2026-07-16T09:00:00+02:00",
                            },
                        }
                    ],
                    "media": [
                        {
                            "id": UUID("40000000-0000-4000-8000-000000000005"),
                            "asset_key": "panda-manual",
                            "asset_type": "manual",
                            "title": "Owner manual",
                            "url": "https://example.test/media/panda-manual.pdf",
                            "mime_type": "application/pdf",
                            "locale": "it-IT",
                            "provenance": {
                                "source_id": UUID(
                                    "10000000-0000-4000-8000-000000000001"
                                ),
                                "source_key": "drivewise-synthetic-eu-seed",
                                "source_name": "Drivewise Synthetic EU Seed",
                                "source_url": "https://example.test/media/panda-manual",
                                "source_license": "Synthetic test data",
                                "observed_at": "2026-07-16T09:00:00+02:00",
                            },
                        }
                    ],
                    "provenance": [
                        {
                            "source_id": UUID(
                                "10000000-0000-4000-8000-000000000001"
                            ),
                            "source_key": "drivewise-synthetic-eu-seed",
                            "source_name": "Drivewise Synthetic EU Seed",
                            "source_url": "https://example.test/specs/fiat-panda",
                            "source_license": "Synthetic test data",
                            "observed_at": "2026-07-16T09:00:00+02:00",
                            "record_observed_at": "2026-07-16T09:00:00+02:00",
                            "content_hash": "spec-content-hash",
                            "is_current": True,
                            "supported_metrics": [
                                "body_style",
                                "fuel_type",
                                "consumption_l_100km",
                            ],
                        }
                    ],
                }
            ],
            "provenance": [
                {
                    "source_id": UUID("10000000-0000-4000-8000-000000000001"),
                    "source_key": "drivewise-synthetic-eu-seed",
                    "source_name": "Drivewise Synthetic EU Seed",
                    "source_url": "https://example.test/vehicles/fiat-panda",
                    "source_license": "Synthetic test data",
                    "observed_at": "2026-07-16T09:00:00+02:00",
                    "record_observed_at": "2026-07-16T09:00:00+02:00",
                    "content_hash": "vehicle-content-hash",
                    "is_current": True,
                    "supported_metrics": ["make", "model", "model_year"],
                }
            ],
        }

    def list_resolve_candidates(self, market):
        self.last_resolve_market = market
        return [
            candidate
            for candidate in self.resolve_candidates
            if candidate["market"] == market
        ]


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
    assert payload["provenance"][0]["supported_metrics"] == [
        "make",
        "model",
        "model_year",
    ]
    assert payload["specs"][0]["provenance"][0]["supported_metrics"] == [
        "body_style",
        "fuel_type",
        "consumption_l_100km",
    ]


def test_get_vehicle_returns_complete_knowledge_profile(client):
    response = client.get(f"/vehicles/{FIAT_ID}")

    assert response.status_code == 200
    spec = response.json()["specs"][0]
    assert spec["identity"]["generation_name"] == "Third generation"
    assert spec["dimensions"]["curb_weight_kg"] == 980
    assert spec["powertrain"]["engine_code"] == "SYN-F10"
    assert spec["transmission_details"]["gear_count"] == 6
    assert spec["performance"]["power_to_weight_kw_per_t"] == 52.04
    assert spec["official_efficiency"]["homologation_cycle"] == "WLTP"
    assert spec["maintenance_schedule"][0]["operation_code"] == "engine-oil"
    assert spec["safety"]["ratings"][0]["overall_stars"] == 4
    assert spec["safety"]["adas"][0]["feature_key"] == "lane-support"
    assert spec["technology_comfort"][0]["category"] == "comfort"
    assert spec["media"][0]["asset_type"] == "manual"

    assert spec["engine"] == "1.0L mild-hybrid petrol"
    assert spec["consumption_l_100km"] == 5.0


def test_vehicle_spec_defaults_legacy_flat_records_to_empty_profile():
    spec = VehicleSpec.model_validate(
        {
            "id": UUID("20000000-0000-4000-8000-000000000099"),
            "trim": "Legacy flat specification",
            "engine": "Legacy engine",
        }
    )

    assert spec.identity.model_dump() == {
        "generation_name": None,
        "restyling_label": None,
        "category": None,
        "doors": None,
    }
    assert spec.dimensions.model_dump() == {
        "length_mm": None,
        "width_mm": None,
        "height_mm": None,
        "wheelbase_mm": None,
        "curb_weight_kg": None,
        "gross_weight_kg": None,
        "payload_kg": None,
        "seats": None,
        "cargo_volume_liters": None,
    }
    assert spec.powertrain.model_dump() == {
        "engine_description": None,
        "engine_code": None,
        "displacement_cc": None,
        "cylinders": None,
        "horsepower": None,
        "power_kw": None,
        "torque_nm": None,
        "fuel_type": None,
        "battery_total_kwh": None,
        "battery_usable_kwh": None,
        "wltp_range_km": None,
    }
    assert spec.transmission_details.model_dump() == {
        "transmission": None,
        "transmission_type": None,
        "gear_count": None,
        "drivetrain": None,
        "differential_type": None,
    }
    assert spec.performance.model_dump() == {
        "acceleration_0_100_s": None,
        "top_speed_kmh": None,
        "braking_100_0_m": None,
        "power_to_weight_kw_per_t": None,
    }
    assert spec.official_efficiency.model_dump() == {
        "homologation_cycle": None,
        "consumption_l_100km": None,
        "energy_consumption_kwh_100km": None,
        "co2_g_km": None,
        "euro_emission_standard": None,
    }
    assert spec.maintenance_schedule == []
    assert spec.safety.ratings == []
    assert spec.safety.adas == []
    assert spec.safety.equipment == []
    assert spec.technology_comfort == []
    assert spec.media == []


def test_post_vehicle_resolve_matches_dirty_query_to_ranked_spec(
    client,
    fake_repositories,
):
    response = client.post(
        "/vehicles/resolve",
        json={
            "query": "fiat panda 1.0 firefly hybrid 2024",
            "market": "IT",
            "model_year": 2024,
            "fuel_type": "mild_hybrid_petrol",
            "body_style": "city_car",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "fiat panda 1.0 firefly hybrid 2024"
    assert payload["normalized_query"] == "fiat panda 1 0 firefly hybrid 2024"
    assert payload["status"] == "matched"
    assert fake_repositories["vehicles"].last_resolve_market == "IT"

    match = payload["matches"][0]
    assert match["confidence"] >= 0.82
    assert match["match_level"] == "spec"
    assert match["vehicle"]["id"] == str(FIAT_ID)
    assert match["vehicle"]["make"] == "Fiat"
    assert match["spec"]["trim"] == "1.0 FireFly Hybrid"
    assert match["matched_fields"] == [
        "make",
        "model",
        "model_year",
        "trim",
        "fuel_type",
        "body_style",
    ]
    assert match["warnings"] == []


def test_post_vehicle_resolve_returns_no_match_for_weak_query(client):
    response = client.post(
        "/vehicles/resolve",
        json={"query": "unknown spaceship", "market": "IT"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "unknown spaceship",
        "normalized_query": "unknown spaceship",
        "status": "no_match",
        "matches": [],
    }


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
