from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_advisor_repository, get_documents_repository
from app.main import app


RUN_ID = UUID("50000000-0000-4000-8000-000000000001")
FIAT_ID = UUID("00000000-0000-4000-8000-000000000001")
TOYOTA_ID = UUID("00000000-0000-4000-8000-000000000002")
DOCUMENT_ID = UUID("40000000-0000-4000-8000-000000000001")


class FakeAdvisorRepository:
    def __init__(self) -> None:
        self.saved_payload = None
        self.saved_items = None
        self.completed_run_id = None

    def list_candidates(self):
        return [
            {
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
                "listings": [
                    {
                        "id": UUID("30000000-0000-4000-8000-000000000001"),
                        "vehicle_id": FIAT_ID,
                        "source_id": UUID("10000000-0000-4000-8000-000000000001"),
                        "listing_ref": "seed-fiat-panda-2024-it",
                        "title": "Fiat Panda 1.0 FireFly Hybrid",
                        "price_eur": 14200.00,
                        "mileage": 6400,
                        "condition": "used",
                        "location_region": "Piemonte",
                        "listed_at": "2026-01-15",
                    }
                ],
            }
        ]

    def create_run(self, request_payload):
        self.saved_payload = request_payload
        return RUN_ID

    def save_items(self, run_id, items):
        self.saved_items = (run_id, items)

    def mark_run_completed(self, run_id):
        self.completed_run_id = run_id


class FakeRankingAdvisorRepository(FakeAdvisorRepository):
    def list_candidates(self):
        fiat_candidate = super().list_candidates()[0]
        toyota_candidate = {
            "vehicle": {
                "id": TOYOTA_ID,
                "make": "Toyota",
                "model": "Yaris Hybrid",
                "model_year": 2024,
                "body_style": "small_hatchback",
                "fuel_type": "full_hybrid_petrol",
                "market": "EU",
                "base_price_eur": 24500.00,
            },
            "specs": [
                {
                    "id": UUID("20000000-0000-4000-8000-000000000002"),
                    "trim": "1.5 Hybrid Active",
                    "drivetrain": "fwd",
                    "transmission": "e-CVT",
                    "engine": "1.5L full-hybrid petrol",
                    "horsepower": 116,
                    "battery_kwh": 0.8,
                    "consumption_l_100km": 4.20,
                    "wltp_range_km": None,
                    "co2_g_km": 96,
                    "euro_emission_standard": "Euro 6e",
                    "seats": 5,
                    "cargo_volume_liters": 286.00,
                }
            ],
            "listings": [
                {
                    "id": UUID("30000000-0000-4000-8000-000000000002"),
                    "vehicle_id": TOYOTA_ID,
                    "source_id": UUID("10000000-0000-4000-8000-000000000001"),
                    "listing_ref": "seed-toyota-yaris-2024-eu",
                    "title": "Toyota Yaris Hybrid Active",
                    "price_eur": 22800.00,
                    "mileage": 8200,
                    "condition": "used",
                    "location_region": "Lombardia",
                    "listed_at": "2026-01-16",
                }
            ],
        }
        return [toyota_candidate, fiat_candidate]


class FakeDocumentsRepository:
    def __init__(self) -> None:
        self.last_searches = []
        self.rows = [
            {
                "id": DOCUMENT_ID,
                "source_id": UUID("10000000-0000-4000-8000-000000000010"),
                "vehicle_id": FIAT_ID,
                "listing_id": None,
                "document_type": "vehicle_profile",
                "title": "Fiat Panda local profile",
                "content": "Fiat Panda compact city-car evidence from local ingestion.",
                "metadata": {},
                "created_at": "2026-01-15T00:00:00+00:00",
            }
        ]

    def search_document_candidates(
        self,
        *,
        query: str,
        tokens: tuple[str, ...],
        document_type: str | None,
        limit: int,
    ):
        self.last_searches.append(
            {
                "query": query,
                "tokens": tokens,
                "document_type": document_type,
                "limit": limit,
            }
        )
        query_lower = query.lower()
        return [
            row
            for row in self.rows
            if query_lower in row["title"].lower()
            or any(token in row["content"].lower() for token in tokens)
        ][:limit]


@pytest.fixture
def fake_repository():
    repository = FakeAdvisorRepository()
    documents_repository = FakeDocumentsRepository()
    app.dependency_overrides[get_advisor_repository] = lambda: repository
    app.dependency_overrides[get_documents_repository] = lambda: documents_repository
    yield repository, documents_repository
    app.dependency_overrides.clear()


@pytest.fixture
def client(fake_repository):
    return TestClient(app)


def test_post_advisor_recommendations_returns_items_and_persists_run(
    client,
    fake_repository,
):
    advisor_repository, documents_repository = fake_repository
    response = client.post(
        "/advisor/recommendations",
        json={
            "budget_max_eur": 20000,
            "primary_use": "city",
            "priorities": ["price", "consumption"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == str(RUN_ID)
    assert payload["items"][0]["vehicle"]["make"] == "Fiat"
    assert payload["items"][0]["best_listing"]["price_eur"] == 14200.00
    assert payload["items"][0]["evidence"]["within_budget"] is True
    assert payload["items"][0]["document_evidence"] == [
        {
            "document_id": str(DOCUMENT_ID),
            "title": "Fiat Panda local profile",
            "document_type": "vehicle_profile",
            "score": 18.05,
            "snippet": "Fiat Panda compact city-car evidence from local ingestion.",
        }
    ]

    assert documents_repository.last_searches[0]["query"] == "Fiat Panda"
    assert advisor_repository.saved_payload["budget_max_eur"] == 20000.0
    assert advisor_repository.saved_items[0] == RUN_ID
    assert all(
        item.document_evidence == [] for item in advisor_repository.saved_items[1]
    )
    assert advisor_repository.completed_run_id == RUN_ID


def test_post_advisor_document_evidence_does_not_change_ranking():
    advisor_repository = FakeRankingAdvisorRepository()
    documents_repository = FakeDocumentsRepository()
    documents_repository.rows.append(
        {
            "id": UUID("40000000-0000-4000-8000-000000000002"),
            "source_id": UUID("10000000-0000-4000-8000-000000000010"),
            "vehicle_id": TOYOTA_ID,
            "listing_id": None,
            "document_type": "vehicle_profile",
            "title": "Toyota Yaris Hybrid Toyota Yaris Hybrid Toyota Yaris Hybrid",
            "content": "Toyota Yaris Hybrid " * 10,
            "metadata": {},
            "created_at": "2026-01-16T00:00:00+00:00",
        }
    )
    app.dependency_overrides[get_advisor_repository] = lambda: advisor_repository
    app.dependency_overrides[get_documents_repository] = lambda: documents_repository

    try:
        response = TestClient(app).post(
            "/advisor/recommendations",
            json={
                "budget_max_eur": 20000,
                "primary_use": "city",
                "priorities": ["price", "consumption"],
            },
        )
    finally:
        app.dependency_overrides.clear()

    payload = response.json()

    assert response.status_code == 200
    assert [item["vehicle"]["make"] for item in payload["items"]] == [
        "Fiat",
        "Toyota",
    ]
    assert payload["items"][0]["score"] == advisor_repository.saved_items[1][0].score
    assert payload["items"][1]["score"] == advisor_repository.saved_items[1][1].score
    assert payload["items"][1]["document_evidence"][0]["title"].startswith("Toyota")
