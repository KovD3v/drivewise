from dataclasses import dataclass
from math import ceil
from typing import Any
from uuid import UUID


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_BATCH_LIMIT = 20
MAX_EMBEDDING_BATCH_LIMIT = 100
DOCUMENT_TYPES = frozenset(
    {
        "vehicle_profile",
        "listing_snapshot",
        "review_excerpt",
        "spec_sheet",
        "seed_note",
    }
)
DEFAULT_PREVIEW_CHARACTERS = 120


class EmbeddingPlanError(ValueError):
    pass


@dataclass(frozen=True)
class EmbeddingInputEstimate:
    character_count: int
    estimated_tokens: int
    preview: str


@dataclass(frozen=True)
class EmbeddingDocumentCandidate:
    id: UUID
    title: str
    document_type: str
    content: str
    estimated_characters: int
    estimated_tokens: int
    preview: str


@dataclass(frozen=True)
class EmbeddingBatchPlan:
    model: str
    limit: int
    document_type: str | None
    documents: tuple[EmbeddingDocumentCandidate, ...]
    external_provider_calls_enabled: bool = False
    database_writes_enabled: bool = False

    @property
    def total_documents(self) -> int:
        return len(self.documents)

    @property
    def total_estimated_characters(self) -> int:
        return sum(document.estimated_characters for document in self.documents)

    @property
    def total_estimated_tokens(self) -> int:
        return sum(document.estimated_tokens for document in self.documents)


def list_documents_missing_embeddings(
    conn,
    *,
    limit: int = DEFAULT_EMBEDDING_BATCH_LIMIT,
    document_type: str | None = None,
) -> list[EmbeddingDocumentCandidate]:
    validated_limit = validate_embedding_limit(limit)
    validated_document_type = validate_document_type(document_type)

    where_clauses = ["embedding IS NULL"]
    params: list[object] = []
    if validated_document_type is not None:
        where_clauses.append("document_type = %s")
        params.append(validated_document_type)

    params.append(validated_limit)
    query = f"""
        SELECT
          id,
          title,
          document_type,
          content,
          created_at
        FROM documents
        WHERE {" AND ".join(where_clauses)}
        ORDER BY created_at ASC
        LIMIT %s
    """

    rows = conn.execute(query, params).fetchall()
    return [_candidate_from_row(row) for row in rows]


def plan_embedding_batch(
    documents: list[EmbeddingDocumentCandidate]
    | tuple[EmbeddingDocumentCandidate, ...],
    *,
    model: str = DEFAULT_EMBEDDING_MODEL,
    limit: int = DEFAULT_EMBEDDING_BATCH_LIMIT,
    document_type: str | None = None,
) -> EmbeddingBatchPlan:
    validated_limit = validate_embedding_limit(limit)
    validated_document_type = validate_document_type(document_type)
    model_name = model.strip()
    if not model_name:
        raise EmbeddingPlanError("model must not be empty")

    return EmbeddingBatchPlan(
        model=model_name,
        limit=validated_limit,
        document_type=validated_document_type,
        documents=tuple(documents),
    )


def estimate_embedding_input(
    content: str,
    *,
    preview_characters: int = DEFAULT_PREVIEW_CHARACTERS,
) -> EmbeddingInputEstimate:
    normalized_content = " ".join(content.strip().split())
    character_count = len(normalized_content)
    estimated_tokens = ceil(character_count / 4) if character_count else 0
    preview = _short_preview(normalized_content, preview_characters)

    return EmbeddingInputEstimate(
        character_count=character_count,
        estimated_tokens=estimated_tokens,
        preview=preview,
    )


def mark_embedding_plan_dry_run(plan: EmbeddingBatchPlan) -> dict[str, str | bool]:
    return {
        "dry_run": True,
        "external_provider_calls": (
            "enabled" if plan.external_provider_calls_enabled else "disabled"
        ),
        "database_writes": "enabled" if plan.database_writes_enabled else "disabled",
    }


def validate_embedding_limit(limit: int) -> int:
    if limit < 1 or limit > MAX_EMBEDDING_BATCH_LIMIT:
        raise EmbeddingPlanError(
            f"limit must be between 1 and {MAX_EMBEDDING_BATCH_LIMIT}"
        )
    return limit


def validate_document_type(document_type: str | None) -> str | None:
    if document_type is None:
        return None

    normalized_document_type = document_type.strip()
    if not normalized_document_type:
        raise EmbeddingPlanError("document_type must not be empty")

    if normalized_document_type not in DOCUMENT_TYPES:
        allowed = ", ".join(sorted(DOCUMENT_TYPES))
        raise EmbeddingPlanError(
            f"document_type must be one of: {allowed}"
        )

    return normalized_document_type


def _candidate_from_row(row: Any) -> EmbeddingDocumentCandidate:
    estimate = estimate_embedding_input(_row_value(row, "content"))
    return EmbeddingDocumentCandidate(
        id=_row_value(row, "id"),
        title=_row_value(row, "title"),
        document_type=_row_value(row, "document_type"),
        content=_row_value(row, "content"),
        estimated_characters=estimate.character_count,
        estimated_tokens=estimate.estimated_tokens,
        preview=estimate.preview,
    )


def _row_value(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row[key]
    return getattr(row, key)


def _short_preview(content: str, preview_characters: int) -> str:
    if preview_characters < 1:
        return ""
    if len(content) <= preview_characters:
        return content
    return f"{content[:preview_characters].rstrip()}..."
