from typing import Any
from uuid import UUID

from app.repositories.document_vector_search import search_document_vector_candidates
from app.repositories.filters import DocumentFilters


class DocumentsRepository:
    def __init__(self, conn) -> None:
        self.conn = conn

    def list_documents(self, filters: DocumentFilters) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[object] = []

        if filters.source_id:
            where_clauses.append("source_id = %s")
            params.append(filters.source_id)
        if filters.vehicle_id:
            where_clauses.append("vehicle_id = %s")
            params.append(filters.vehicle_id)
        if filters.listing_id:
            where_clauses.append("listing_id = %s")
            params.append(filters.listing_id)
        if filters.document_type:
            where_clauses.append("document_type = %s")
            params.append(filters.document_type)
        if filters.q:
            where_clauses.append("(title ILIKE %s OR content ILIKE %s)")
            q_pattern = f"%{filters.q}%"
            params.extend([q_pattern, q_pattern])

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        query = f"""
            SELECT
              id,
              source_id,
              vehicle_id,
              listing_id,
              document_type,
              title,
              content,
              metadata,
              created_at
            FROM documents
            {where_sql}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """

        return list(
            self.conn.execute(query, [*params, filters.limit, filters.offset]).fetchall()
        )

    def get_document(self, document_id: UUID) -> dict[str, Any] | None:
        return self.conn.execute(
            """
            SELECT
              id,
              source_id,
              vehicle_id,
              listing_id,
              document_type,
              title,
              content,
              metadata,
              created_at
            FROM documents
            WHERE id = %s
            """,
            (document_id,),
        ).fetchone()

    def search_document_candidates(
        self,
        *,
        query: str,
        tokens: tuple[str, ...],
        document_type: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[object] = []

        if document_type:
            where_clauses.append("document_type = %s")
            params.append(document_type)

        text_clauses: list[str] = []
        patterns = [f"%{query}%", *(f"%{token}%" for token in tokens)]
        for pattern in patterns:
            text_clauses.append("(title ILIKE %s OR content ILIKE %s)")
            params.extend([pattern, pattern])

        where_clauses.append("(" + " OR ".join(text_clauses) + ")")
        where_sql = "WHERE " + " AND ".join(where_clauses)

        sql = f"""
            SELECT
              id,
              source_id,
              vehicle_id,
              listing_id,
              document_type,
              title,
              content,
              metadata,
              created_at
            FROM documents
            {where_sql}
            ORDER BY created_at DESC
            LIMIT %s
        """

        return list(self.conn.execute(sql, [*params, limit]).fetchall())

    def search_document_vector_candidates(
        self,
        *,
        query_embedding: list[float],
        document_type: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        return search_document_vector_candidates(
            self.conn,
            query_embedding=query_embedding,
            document_type=document_type,
            limit=limit,
        )
