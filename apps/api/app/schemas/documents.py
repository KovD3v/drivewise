from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import ApiModel


class DocumentRead(ApiModel):
    id: UUID
    source_id: UUID
    vehicle_id: UUID | None = None
    listing_id: UUID | None = None
    document_type: str
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
