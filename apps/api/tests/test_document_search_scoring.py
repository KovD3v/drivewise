from datetime import datetime, timezone
from uuid import UUID

from app.services.search.documents import (
    search_documents_text_only,
    search_documents_vector_fake,
)


FIRST_DOCUMENT_ID = UUID("40000000-0000-4000-8000-000000000001")
SECOND_DOCUMENT_ID = UUID("40000000-0000-4000-8000-000000000002")
THIRD_DOCUMENT_ID = UUID("40000000-0000-4000-8000-000000000003")


def test_title_match_scores_higher_than_content_match():
    results = search_documents_text_only(
        query="fiat panda",
        candidates=[
            candidate(
                FIRST_DOCUMENT_ID,
                title="General city-car note",
                content="This document mentions Fiat Panda in the body.",
            ),
            candidate(
                SECOND_DOCUMENT_ID,
                title="Fiat Panda profile",
                content="Compact synthetic fixture.",
            ),
        ],
        include_content=False,
        limit=10,
    )

    assert [item["id"] for item in results["items"]] == [
        SECOND_DOCUMENT_ID,
        FIRST_DOCUMENT_ID,
    ]
    assert results["items"][0]["score"] > results["items"][1]["score"]


def test_exact_query_match_scores_higher_than_token_only_match():
    results = search_documents_text_only(
        query="toyota yaris",
        candidates=[
            candidate(
                FIRST_DOCUMENT_ID,
                title="Toyota compact hybrid",
                content="Yaris city profile.",
            ),
            candidate(
                SECOND_DOCUMENT_ID,
                title="Toyota Yaris profile",
                content="Synthetic fixture.",
            ),
        ],
        include_content=False,
        limit=10,
    )

    assert [item["id"] for item in results["items"]] == [
        SECOND_DOCUMENT_ID,
        FIRST_DOCUMENT_ID,
    ]


def test_recent_documents_receive_small_boost_without_hiding_stronger_match():
    results = search_documents_text_only(
        query="compact",
        candidates=[
            candidate(
                FIRST_DOCUMENT_ID,
                title="Compact vehicle profile",
                content="Synthetic fixture.",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
            candidate(
                SECOND_DOCUMENT_ID,
                title="Compact vehicle profile",
                content="Synthetic fixture.",
                created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            ),
            candidate(
                THIRD_DOCUMENT_ID,
                title="Vehicle profile",
                content="Compact compact compact city car.",
                created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            ),
        ],
        include_content=False,
        limit=10,
    )

    assert [item["id"] for item in results["items"][:2]] == [
        SECOND_DOCUMENT_ID,
        FIRST_DOCUMENT_ID,
    ]
    assert results["items"][0]["score"] - results["items"][1]["score"] < 0.3
    assert results["items"][0]["score"] > results["items"][1]["score"]


def test_search_returns_empty_when_no_text_matches():
    results = search_documents_text_only(
        query="tesla",
        candidates=[
            candidate(
                FIRST_DOCUMENT_ID,
                title="Fiat Panda profile",
                content="Compact city car.",
            )
        ],
        include_content=False,
        limit=10,
    )

    assert results == {"query": "tesla", "mode": "text_only", "items": []}


def test_search_builds_short_snippet_and_optional_content():
    content = "Intro. " + ("Fiat Panda compact city car. " * 20)
    results = search_documents_text_only(
        query="fiat panda",
        candidates=[
            candidate(
                FIRST_DOCUMENT_ID,
                title="Local fixture",
                content=content,
            )
        ],
        include_content=True,
        limit=10,
    )

    item = results["items"][0]
    assert item["snippet"].startswith("Intro. Fiat Panda")
    assert len(item["snippet"]) <= 183
    assert item["content"] == content
    assert "embedding" not in item
    assert item["metadata"] == {
        "source_id": "10000000-0000-4000-8000-000000000010",
        "vehicle_id": None,
        "listing_id": None,
        "created_at": "2026-01-15T00:00:00+00:00",
    }


def test_vector_fake_search_uses_repository_score_without_text_match_filtering():
    results = search_documents_vector_fake(
        query="fiat panda",
        candidates=[
            {
                **candidate(
                    FIRST_DOCUMENT_ID,
                    title="Charging guide",
                    content="Battery maintenance and cable storage tips.",
                ),
                "score": 0.73456,
                "embedding": "[should-not-be-exposed]",
                "embedding_model": "fake-embedding-1536",
            }
        ],
        include_content=False,
        limit=10,
    )

    assert results["mode"] == "vector_fake"
    assert results["items"][0]["score"] == 0.7346
    assert results["items"][0]["snippet"].startswith("Battery maintenance")
    assert "embedding" not in results["items"][0]
    assert "embedding_model" not in results["items"][0]


def candidate(
    document_id: UUID,
    *,
    title: str,
    content: str,
    document_type: str = "vehicle_profile",
    created_at: datetime = datetime(2026, 1, 15, tzinfo=timezone.utc),
) -> dict:
    return {
        "id": document_id,
        "source_id": UUID("10000000-0000-4000-8000-000000000010"),
        "vehicle_id": None,
        "listing_id": None,
        "document_type": document_type,
        "title": title,
        "content": content,
        "metadata": {"content_hash": "not exposed in search metadata"},
        "created_at": created_at,
        "embedding": "[should-not-be-read]",
    }
