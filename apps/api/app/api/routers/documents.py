from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_documents_repository
from app.repositories.documents import DocumentsRepository
from app.repositories.filters import DocumentFilters
from app.schemas.documents import DocumentRead


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRead])
def list_documents(
    repository: Annotated[DocumentsRepository, Depends(get_documents_repository)],
    source_id: UUID | None = Query(default=None),
    vehicle_id: UUID | None = Query(default=None),
    listing_id: UUID | None = Query(default=None),
    document_type: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    filters = DocumentFilters(
        source_id=source_id,
        vehicle_id=vehicle_id,
        listing_id=listing_id,
        document_type=document_type,
        q=q,
        limit=limit,
        offset=offset,
    )
    return repository.list_documents(filters)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: UUID,
    repository: Annotated[DocumentsRepository, Depends(get_documents_repository)],
) -> dict:
    document = repository.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
