from uuid import UUID

from app.embeddings.pipeline import embed_document_batch, format_pgvector
from app.embeddings.providers import EMBEDDING_DIMENSION, FakeEmbeddingProvider


FIRST_DOCUMENT_ID = UUID("40000000-0000-4000-8000-000000000001")
SECOND_DOCUMENT_ID = UUID("40000000-0000-4000-8000-000000000002")


def test_embed_document_batch_dry_run_does_not_write():
    conn = FakeEmbeddingWriteConnection(
        [
            document_row(FIRST_DOCUMENT_ID, embedding=None),
            document_row(SECOND_DOCUMENT_ID, embedding="[0.1,0.2]"),
        ]
    )

    result = embed_document_batch(
        conn,
        provider=FakeEmbeddingProvider(),
        model="fake-embedding-1536",
        limit=20,
        document_type=None,
        write=False,
        force=False,
    )

    assert result.embedded == 0
    assert result.skipped_existing == 1
    assert result.plan.total_documents == 1
    assert result.plan.documents[0].id == FIRST_DOCUMENT_ID
    assert conn.update_queries == []


def test_embed_document_batch_write_updates_missing_embeddings():
    conn = FakeEmbeddingWriteConnection([document_row(FIRST_DOCUMENT_ID)])

    result = embed_document_batch(
        conn,
        provider=FakeEmbeddingProvider(),
        model="fake-embedding-1536",
        limit=20,
        document_type=None,
        write=True,
        force=False,
    )

    assert result.embedded == 1
    assert result.skipped_existing == 0
    assert conn.rows[0]["embedding"] is not None
    assert conn.rows[0]["embedding_model"] == "fake-embedding-1536"
    assert conn.update_queries == [
        "UPDATE documents SET embedding = %s::vector, embedding_model = %s WHERE id = %s"
    ]


def test_embed_document_batch_does_not_overwrite_without_force():
    conn = FakeEmbeddingWriteConnection(
        [document_row(FIRST_DOCUMENT_ID, embedding="[0.1,0.2]")]
    )

    result = embed_document_batch(
        conn,
        provider=FakeEmbeddingProvider(),
        model="fake-embedding-1536",
        limit=20,
        document_type=None,
        write=True,
        force=False,
    )

    assert result.embedded == 0
    assert result.skipped_existing == 1
    assert conn.rows[0]["embedding"] == "[0.1,0.2]"
    assert conn.rows[0]["embedding_model"] == "old-model"
    assert conn.update_queries == []


def test_embed_document_batch_overwrites_with_force():
    conn = FakeEmbeddingWriteConnection(
        [document_row(FIRST_DOCUMENT_ID, embedding="[0.1,0.2]")]
    )

    result = embed_document_batch(
        conn,
        provider=FakeEmbeddingProvider(),
        model="fake-embedding-1536",
        limit=20,
        document_type=None,
        write=True,
        force=True,
    )

    assert result.embedded == 1
    assert result.skipped_existing == 0
    assert conn.rows[0]["embedding"] != "[0.1,0.2]"
    assert conn.rows[0]["embedding_model"] == "fake-embedding-1536"
    assert len(parse_pgvector(conn.rows[0]["embedding"])) == EMBEDDING_DIMENSION


def test_format_pgvector_outputs_vector_literal():
    assert format_pgvector([0.1, -0.25, 1.0]) == "[0.1,-0.25,1.0]"


def document_row(
    document_id: UUID,
    *,
    document_type: str = "seed_note",
    embedding: str | None = None,
) -> dict:
    return {
        "id": document_id,
        "title": "Fiat Panda seed note",
        "document_type": document_type,
        "content": "Fiat Panda compact city car.",
        "embedding": embedding,
        "embedding_model": "old-model" if embedding is not None else None,
        "created_at": "2026-01-01T00:00:00Z",
    }


def parse_pgvector(value: str | None) -> list[float]:
    assert value is not None
    return [float(item) for item in value.strip("[]").split(",")]


class FakeCursor:
    def __init__(self, rows: list[dict] | dict) -> None:
        self.rows = rows

    def fetchall(self) -> list[dict]:
        assert isinstance(self.rows, list)
        return self.rows

    def fetchone(self) -> dict:
        assert isinstance(self.rows, dict)
        return self.rows


class FakeEmbeddingWriteConnection:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.update_queries: list[str] = []

    def execute(self, query: str, params=()) -> FakeCursor:
        normalized_query = " ".join(query.split())

        if normalized_query.startswith("SELECT count(*) AS count FROM documents"):
            return FakeCursor(
                {
                    "count": len(
                        [row for row in self.rows if row["embedding"] is not None]
                    )
                }
            )

        if normalized_query.startswith("SELECT id, title, document_type"):
            limit = params[-1]
            rows = self.rows
            if "document_type = %s" in normalized_query:
                rows = [row for row in rows if row["document_type"] == params[0]]
            if "embedding IS NULL" in normalized_query:
                rows = [row for row in rows if row["embedding"] is None]
            return FakeCursor(rows[:limit])

        if normalized_query.startswith("UPDATE documents"):
            embedding, model, document_id = params
            for row in self.rows:
                if row["id"] == document_id:
                    row["embedding"] = embedding
                    row["embedding_model"] = model
                    break
            self.update_queries.append(normalized_query)
            return FakeCursor([])

        raise AssertionError(f"Unexpected query: {normalized_query}")
