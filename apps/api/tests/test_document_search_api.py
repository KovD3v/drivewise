from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api import dependencies
from app.main import app


FIRST_DOCUMENT_ID = UUID("40000000-0000-4000-8000-000000000001")
SECOND_DOCUMENT_ID = UUID("40000000-0000-4000-8000-000000000002")
SOURCE_ID = UUID("10000000-0000-4000-8000-000000000010")


class FakeSearchDocumentsRepository:
    def __init__(self) -> None:
        self.last_query = None
        self.last_tokens = None
        self.last_document_type = None
        self.last_limit = None
        self.last_vector_query_embedding = None
        self.last_vector_document_type = None
        self.last_vector_limit = None
        self.vector_rows = None
        self.rows = [
            {
                "id": FIRST_DOCUMENT_ID,
                "source_id": SOURCE_ID,
                "vehicle_id": None,
                "listing_id": None,
                "document_type": "seed_note",
                "title": "Fiat Panda seed note",
                "content": "Synthetic Fiat Panda local fixture content.",
                "metadata": {"content_hash": "hash-is-not-exposed"},
                "created_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
                "embedding": "[should-not-be-exposed]",
            },
            {
                "id": SECOND_DOCUMENT_ID,
                "source_id": SOURCE_ID,
                "vehicle_id": None,
                "listing_id": None,
                "document_type": "vehicle_profile",
                "title": "Toyota Yaris profile",
                "content": "Hybrid city car synthetic fixture.",
                "metadata": {"content_hash": "hash-is-not-exposed"},
                "created_at": datetime(2026, 1, 16, tzinfo=timezone.utc),
                "embedding": "[should-not-be-exposed]",
            },
        ]

    def search_document_candidates(
        self,
        *,
        query: str,
        tokens: tuple[str, ...],
        document_type: str | None,
        limit: int,
    ):
        self.last_query = query
        self.last_tokens = tokens
        self.last_document_type = document_type
        self.last_limit = limit

        rows = self.rows
        if document_type is not None:
            rows = [row for row in rows if row["document_type"] == document_type]
        return rows[:limit]

    def search_document_vector_candidates(
        self,
        *,
        query_embedding: list[float],
        document_type: str | None,
        limit: int,
    ):
        self.last_vector_query_embedding = query_embedding
        self.last_vector_document_type = document_type
        self.last_vector_limit = limit

        rows = [
            {
                **row,
                "score": 0.812345,
                "embedding_model": "fake-embedding-1536",
            }
            for row in self.rows
        ]
        if self.vector_rows is not None:
            rows = self.vector_rows
        if document_type is not None:
            rows = [row for row in rows if row["document_type"] == document_type]
        return rows[:limit]


@pytest.fixture
def fake_repository():
    repository = FakeSearchDocumentsRepository()
    app.dependency_overrides[dependencies.get_documents_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()


@pytest.fixture
def client(fake_repository):
    return TestClient(app)


def test_post_search_documents_returns_text_only_results(client, fake_repository):
    response = client.post(
        "/search/documents",
        json={"query": "fiat panda", "document_type": "seed_note", "limit": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "fiat panda"
    assert payload["mode"] == "text_only"
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == str(FIRST_DOCUMENT_ID)
    assert payload["items"][0]["title"] == "Fiat Panda seed note"
    assert payload["items"][0]["document_type"] == "seed_note"
    assert payload["items"][0]["score"] > 0
    assert "Fiat Panda" in payload["items"][0]["snippet"]
    assert payload["items"][0]["metadata"]["source_id"] == str(SOURCE_ID)
    assert "content" not in payload["items"][0]
    assert "embedding" not in payload["items"][0]

    assert fake_repository.last_query == "fiat panda"
    assert fake_repository.last_tokens == ("fiat", "panda")
    assert fake_repository.last_document_type == "seed_note"
    assert fake_repository.last_limit == 5
    assert fake_repository.last_vector_query_embedding is None


def test_post_search_documents_can_include_content(client):
    response = client.post(
        "/search/documents",
        json={"query": "fiat", "limit": 1, "include_content": True},
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["content"].startswith("Synthetic Fiat Panda")
    assert "embedding" not in item


def test_post_search_documents_returns_empty_for_no_matches(client):
    response = client.post("/search/documents", json={"query": "tesla"})

    assert response.status_code == 200
    assert response.json() == {"query": "tesla", "mode": "text_only", "items": []}


def test_post_search_documents_validates_query_and_limit(client):
    blank_query = client.post("/search/documents", json={"query": "   "})
    too_large_limit = client.post(
        "/search/documents",
        json={"query": "fiat", "limit": 51},
    )

    assert blank_query.status_code == 422
    assert too_large_limit.status_code == 422


def test_post_search_documents_explicit_text_only_keeps_text_path(
    client,
    fake_repository,
):
    response = client.post(
        "/search/documents",
        json={"query": "fiat", "mode": "text_only"},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "text_only"
    assert fake_repository.last_query == "fiat"
    assert fake_repository.last_vector_query_embedding is None


def test_post_search_documents_vector_fake_uses_fake_query_embedding(
    client,
    fake_repository,
):
    response = client.post(
        "/search/documents",
        json={
            "query": "fiat panda",
            "document_type": "seed_note",
            "limit": 2,
            "mode": "vector_fake",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "fiat panda"
    assert payload["mode"] == "vector_fake"
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == str(FIRST_DOCUMENT_ID)
    assert payload["items"][0]["score"] == 0.8123
    assert "Fiat Panda" in payload["items"][0]["snippet"]
    assert "content" not in payload["items"][0]
    assert "embedding" not in payload["items"][0]
    assert "embedding_model" not in payload["items"][0]

    assert fake_repository.last_query is None
    assert fake_repository.last_vector_document_type == "seed_note"
    assert fake_repository.last_vector_limit == 2
    assert fake_repository.last_vector_query_embedding is not None
    assert len(fake_repository.last_vector_query_embedding) == 1536


def test_post_search_documents_vector_fake_returns_empty_without_embedded_rows(
    client,
    fake_repository,
):
    fake_repository.vector_rows = []

    response = client.post(
        "/search/documents",
        json={"query": "fiat panda", "mode": "vector_fake"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "fiat panda",
        "mode": "vector_fake",
        "items": [],
    }
    assert fake_repository.last_vector_query_embedding is not None
