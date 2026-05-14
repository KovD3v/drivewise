from dataclasses import dataclass, replace
from math import isfinite
from typing import Any

from app.embeddings.planner import (
    DEFAULT_EMBEDDING_BATCH_LIMIT,
    EmbeddingBatchPlan,
    EmbeddingDocumentCandidate,
    EmbeddingPlanError,
    estimate_embedding_input,
    plan_embedding_batch,
    validate_document_type,
    validate_embedding_limit,
)
from app.embeddings.providers import (
    EMBEDDING_DIMENSION,
    EmbeddingProvider,
    EmbeddingProviderError,
)


@dataclass(frozen=True)
class EmbeddingExecutionResult:
    provider_name: str
    plan: EmbeddingBatchPlan
    embedded: int
    skipped_existing: int
    write: bool
    force: bool


def embed_document_batch(
    conn,
    *,
    provider: EmbeddingProvider,
    model: str,
    provider_name: str = "fake",
    limit: int = DEFAULT_EMBEDDING_BATCH_LIMIT,
    document_type: str | None = None,
    write: bool = False,
    force: bool = False,
) -> EmbeddingExecutionResult:
    validated_limit = validate_embedding_limit(limit)
    validated_document_type = validate_document_type(document_type)
    documents = list_embedding_candidates(
        conn,
        limit=validated_limit,
        document_type=validated_document_type,
        include_existing=force,
    )
    plan = plan_embedding_batch(
        documents,
        model=model,
        limit=validated_limit,
        document_type=validated_document_type,
    )
    plan = replace(plan, database_writes_enabled=write)
    skipped_existing = (
        0
        if force
        else count_existing_embeddings(
            conn,
            document_type=validated_document_type,
        )
    )

    if not write or not plan.documents:
        return EmbeddingExecutionResult(
            provider_name=provider_name,
            plan=plan,
            embedded=0,
            skipped_existing=skipped_existing,
            write=write,
            force=force,
        )

    vectors = provider.embed_texts(
        [document.content for document in plan.documents],
        plan.model,
    )
    _validate_provider_vectors(vectors, expected_count=len(plan.documents))

    for document, vector in zip(plan.documents, vectors, strict=True):
        update_document_embedding(
            conn,
            document_id=document.id,
            embedding=vector,
            model=plan.model,
        )

    return EmbeddingExecutionResult(
        provider_name=provider_name,
        plan=plan,
        embedded=len(plan.documents),
        skipped_existing=skipped_existing,
        write=write,
        force=force,
    )


def list_embedding_candidates(
    conn,
    *,
    limit: int,
    document_type: str | None,
    include_existing: bool,
) -> list[EmbeddingDocumentCandidate]:
    where_clauses: list[str] = []
    params: list[object] = []

    if not include_existing:
        where_clauses.append("embedding IS NULL")
    if document_type is not None:
        where_clauses.append("document_type = %s")
        params.append(document_type)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    params.append(limit)

    query = f"""
        SELECT
          id,
          title,
          document_type,
          content,
          embedding,
          created_at
        FROM documents
        {where_sql}
        ORDER BY created_at ASC
        LIMIT %s
    """

    rows = conn.execute(query, params).fetchall()
    return [_candidate_from_row(row) for row in rows]


def count_existing_embeddings(conn, *, document_type: str | None) -> int:
    where_clauses = ["embedding IS NOT NULL"]
    params: list[object] = []

    if document_type is not None:
        where_clauses.append("document_type = %s")
        params.append(document_type)

    query = f"""
        SELECT count(*) AS count
        FROM documents
        WHERE {" AND ".join(where_clauses)}
    """
    row = conn.execute(query, params).fetchone()
    if isinstance(row, dict):
        return int(row["count"])
    return int(row[0])


def update_document_embedding(
    conn,
    *,
    document_id,
    embedding: list[float],
    model: str,
) -> None:
    conn.execute(
        """
        UPDATE documents
        SET embedding = %s::vector,
            embedding_model = %s
        WHERE id = %s
        """,
        (format_pgvector(embedding), model, document_id),
    )


def format_pgvector(embedding: list[float]) -> str:
    if not all(isfinite(value) for value in embedding):
        raise EmbeddingPlanError("embedding values must be finite")

    return "[" + ",".join(repr(float(value)) for value in embedding) + "]"


def _validate_provider_vectors(
    vectors: list[list[float]],
    *,
    expected_count: int,
) -> None:
    if len(vectors) != expected_count:
        raise EmbeddingProviderError(
            "embedding provider returned a different number of vectors"
        )

    for vector in vectors:
        if len(vector) != EMBEDDING_DIMENSION:
            raise EmbeddingProviderError(
                f"embedding provider must return {EMBEDDING_DIMENSION}-dimensional "
                "vectors"
            )
        if not all(isfinite(value) for value in vector):
            raise EmbeddingProviderError("embedding provider returned non-finite values")


def _candidate_from_row(row: Any) -> EmbeddingDocumentCandidate:
    content = _row_value(row, "content")
    estimate = estimate_embedding_input(content)
    return EmbeddingDocumentCandidate(
        id=_row_value(row, "id"),
        title=_row_value(row, "title"),
        document_type=_row_value(row, "document_type"),
        content=content,
        estimated_characters=estimate.character_count,
        estimated_tokens=estimate.estimated_tokens,
        preview=estimate.preview,
    )


def _row_value(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row[key]
    return getattr(row, key)
