import re
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DocumentSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=160)
    document_type: str | None = None
    limit: int = Field(default=10, ge=1, le=50)
    include_content: bool = False
    mode: Literal["text_only", "vector_fake"] = "text_only"

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("query must not be blank")
        tokens = tuple(dict.fromkeys(re.findall(r"[a-zA-Z0-9]+", normalized.lower())))
        if len(tokens) > 16:
            raise ValueError("query must contain at most 16 unique tokens")
        return normalized


class DocumentSearchItem(BaseModel):
    id: UUID
    title: str
    document_type: str
    score: float
    snippet: str
    metadata: dict[str, Any]
    content: str | None = None


class DocumentSearchResponse(BaseModel):
    query: str
    mode: Literal["text_only", "vector_fake"]
    items: list[DocumentSearchItem]
