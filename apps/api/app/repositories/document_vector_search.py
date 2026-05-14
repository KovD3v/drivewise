from typing import Any

from app.embeddings.pipeline import format_pgvector
from app.embeddings.providers import EMBEDDING_DIMENSION


def search_document_vector_candidates(
    conn,
    *,
    query_embedding: list[float],
    document_type: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    if len(query_embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"query_embedding must have {EMBEDDING_DIMENSION} dimensions"
        )

    where_clauses = ["d.embedding IS NOT NULL"]
    params: list[object] = [format_pgvector(query_embedding)]

    if document_type:
        where_clauses.append("d.document_type = %s")
        params.append(document_type)

    params.append(limit)
    where_sql = "WHERE " + " AND ".join(where_clauses)

    query = f"""
        WITH query_embedding AS (
          SELECT %s::vector AS value
        )
        SELECT
          d.id,
          d.source_id,
          d.vehicle_id,
          d.listing_id,
          d.document_type,
          d.title,
          d.content,
          d.metadata,
          d.created_at,
          (1 - (d.embedding <=> q.value))::double precision AS score
        FROM documents d
        CROSS JOIN query_embedding q
        {where_sql}
        ORDER BY
          d.embedding <=> q.value ASC,
          d.created_at DESC,
          d.title ASC,
          d.id ASC
        LIMIT %s
    """

    return list(conn.execute(query, params).fetchall())
