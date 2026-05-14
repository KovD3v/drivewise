from uuid import UUID

import pytest

from app.embeddings.planner import (
    DEFAULT_EMBEDDING_MODEL,
    EmbeddingPlanError,
    estimate_embedding_input,
    list_documents_missing_embeddings,
    mark_embedding_plan_dry_run,
    plan_embedding_batch,
)


FIRST_DOCUMENT_ID = UUID("40000000-0000-4000-8000-000000000001")
SECOND_DOCUMENT_ID = UUID("40000000-0000-4000-8000-000000000002")
THIRD_DOCUMENT_ID = UUID("40000000-0000-4000-8000-000000000003")


def test_list_documents_missing_embeddings_selects_only_rows_without_embedding():
    conn = FakeReadOnlyConnection(
        [
            document_row(FIRST_DOCUMENT_ID, "Fiat Panda note", "seed_note", None),
            document_row(
                SECOND_DOCUMENT_ID,
                "Toyota embedded profile",
                "vehicle_profile",
                "[0.1,0.2]",
            ),
            document_row(
                THIRD_DOCUMENT_ID,
                "Listing snapshot",
                "listing_snapshot",
                None,
            ),
        ]
    )

    documents = list_documents_missing_embeddings(conn, limit=10)

    assert [document.id for document in documents] == [
        FIRST_DOCUMENT_ID,
        THIRD_DOCUMENT_ID,
    ]
    assert "embedding IS NULL" in conn.query
    assert "ORDER BY created_at ASC" in conn.query
    assert conn.params == [10]
    assert conn.write_queries == []


def test_list_documents_missing_embeddings_filters_by_document_type():
    conn = FakeReadOnlyConnection(
        [
            document_row(FIRST_DOCUMENT_ID, "Fiat Panda note", "seed_note", None),
            document_row(
                THIRD_DOCUMENT_ID,
                "Listing snapshot",
                "listing_snapshot",
                None,
            ),
        ]
    )

    documents = list_documents_missing_embeddings(
        conn,
        limit=10,
        document_type="listing_snapshot",
    )

    assert [document.id for document in documents] == [THIRD_DOCUMENT_ID]
    assert "document_type = %s" in conn.query
    assert conn.params == ["listing_snapshot", 10]


def test_list_documents_missing_embeddings_rejects_limit_above_maximum():
    conn = FakeReadOnlyConnection([])

    with pytest.raises(EmbeddingPlanError, match="between 1 and 100"):
        list_documents_missing_embeddings(conn, limit=101)

    assert conn.query == ""


def test_plan_embedding_batch_estimates_input_and_marks_dry_run():
    document = document_row(
        FIRST_DOCUMENT_ID,
        "Long document",
        "seed_note",
        None,
        content="A" * 160,
    )
    conn = FakeReadOnlyConnection([document])
    documents = list_documents_missing_embeddings(conn, limit=1)

    plan = plan_embedding_batch(
        documents,
        model=DEFAULT_EMBEDDING_MODEL,
        limit=1,
        document_type=None,
    )
    dry_run = mark_embedding_plan_dry_run(plan)

    assert plan.model == "text-embedding-3-small"
    assert plan.total_documents == 1
    assert plan.total_estimated_characters == 160
    assert plan.documents[0].preview.endswith("...")
    assert len(plan.documents[0].preview) <= 123
    assert plan.external_provider_calls_enabled is False
    assert plan.database_writes_enabled is False
    assert dry_run["external_provider_calls"] == "disabled"
    assert dry_run["database_writes"] == "disabled"


def test_estimate_embedding_input_uses_short_preview():
    estimate = estimate_embedding_input("  Drivewise document content " + ("x" * 80))

    assert estimate.character_count == 107
    assert estimate.estimated_tokens == 27
    assert estimate.preview.startswith("Drivewise document content")
    assert len(estimate.preview) <= 123


def document_row(
    document_id: UUID,
    title: str,
    document_type: str,
    embedding: str | None,
    *,
    content: str = "Synthetic Drivewise content",
) -> dict:
    return {
        "id": document_id,
        "title": title,
        "document_type": document_type,
        "content": content,
        "embedding": embedding,
        "created_at": "2026-01-01T00:00:00Z",
    }


class FakeCursor:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def fetchall(self) -> list[dict]:
        return self.rows


class FakeReadOnlyConnection:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.query = ""
        self.params: list[object] = []
        self.write_queries: list[str] = []

    def execute(self, query: str, params=()) -> FakeCursor:
        normalized_query = " ".join(query.split())
        self.query = normalized_query
        self.params = list(params)

        query_upper = normalized_query.upper()
        if any(
            query_upper.startswith(prefix)
            for prefix in ("INSERT", "UPDATE", "DELETE", "ALTER", "CREATE", "DROP")
        ):
            self.write_queries.append(normalized_query)
            raise AssertionError(f"Unexpected write query: {normalized_query}")

        rows = [row for row in self.rows if row["embedding"] is None]
        if "document_type = %s" in normalized_query:
            document_type = self.params[0]
            limit = self.params[1]
            rows = [row for row in rows if row["document_type"] == document_type]
        else:
            limit = self.params[0]

        return FakeCursor(rows[:limit])
