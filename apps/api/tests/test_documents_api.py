from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api import dependencies
from app.main import app


DOCUMENT_ID = UUID("40000000-0000-4000-8000-000000000001")
SOURCE_ID = UUID("10000000-0000-4000-8000-000000000010")
VEHICLE_ID = UUID("00000000-0000-4000-8000-000000000001")
LISTING_ID = UUID("30000000-0000-4000-8000-000000000001")


class FakeDocumentsRepository:
    def __init__(self) -> None:
        self.document = {
            "id": DOCUMENT_ID,
            "source_id": SOURCE_ID,
            "vehicle_id": VEHICLE_ID,
            "listing_id": LISTING_ID,
            "document_type": "listing_snapshot",
            "title": "Fiat Panda local listing",
            "content": "Fiat Panda in Piemonte, prezzo 14200 EUR, 6400 km.",
            "metadata": {
                "content_hash": "hash-fiat-panda",
                "local_path": "data/fixtures/ingestion/fiat-panda-listing.txt",
                "proposed_vehicle": {"make": "Fiat", "model": "Panda"},
                "proposed_listing": {"price_eur": 14200, "mileage": 6400},
                "unparsed_fields": {"free_text": "synthetic fixture"},
            },
            "created_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
        }
        self.last_filters = None

    def list_documents(self, filters):
        self.last_filters = filters
        if filters.q and "panda" not in filters.q.lower():
            return []
        if filters.source_id and filters.source_id != SOURCE_ID:
            return []
        return [self.document]

    def get_document(self, document_id):
        if document_id != DOCUMENT_ID:
            return None
        return self.document


@pytest.fixture
def fake_repository():
    repository = FakeDocumentsRepository()
    if hasattr(dependencies, "get_documents_repository"):
        app.dependency_overrides[dependencies.get_documents_repository] = (
            lambda: repository
        )
    yield repository
    app.dependency_overrides.clear()


@pytest.fixture
def client(fake_repository):
    return TestClient(app)


def test_get_documents_returns_documents_without_embedding(client, fake_repository):
    response = client.get("/documents", params={"q": "panda", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["title"] == "Fiat Panda local listing"
    assert payload[0]["metadata"]["proposed_listing"]["price_eur"] == 14200
    assert "embedding" not in payload[0]
    assert fake_repository.last_filters.q == "panda"
    assert fake_repository.last_filters.limit == 5


def test_get_documents_filters_by_source_id(client, fake_repository):
    response = client.get("/documents", params={"source_id": str(SOURCE_ID)})

    assert response.status_code == 200
    assert response.json()[0]["source_id"] == str(SOURCE_ID)
    assert fake_repository.last_filters.source_id == SOURCE_ID


def test_get_document_returns_detail_with_metadata(client):
    response = client.get(f"/documents/{DOCUMENT_ID}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["content"].startswith("Fiat Panda")
    assert payload["metadata"]["content_hash"] == "hash-fiat-panda"
    assert "embedding" not in payload


def test_get_document_returns_404_for_missing_id(client):
    response = client.get("/documents/40000000-0000-4000-8000-999999999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}
