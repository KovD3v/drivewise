from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_documents_repository
from app.embeddings.providers import DEFAULT_FAKE_EMBEDDING_MODEL, FakeEmbeddingProvider
from app.repositories.documents import DocumentsRepository
from app.schemas.search import DocumentSearchRequest, DocumentSearchResponse
from app.services.search.documents import (
    SEARCH_MODE_VECTOR_FAKE,
    search_documents_text_only,
    search_documents_vector_fake,
    tokenize_search_query,
)


router = APIRouter(prefix="/search", tags=["search"])


@router.post(
    "/documents",
    response_model=DocumentSearchResponse,
    response_model_exclude_none=True,
)
def search_documents(
    request: DocumentSearchRequest,
    repository: Annotated[DocumentsRepository, Depends(get_documents_repository)],
) -> dict:
    if request.mode == SEARCH_MODE_VECTOR_FAKE:
        query_embedding = FakeEmbeddingProvider().embed_texts(
            [request.query],
            DEFAULT_FAKE_EMBEDDING_MODEL,
        )[0]
        candidates = repository.search_document_vector_candidates(
            query_embedding=query_embedding,
            document_type=request.document_type,
            limit=request.limit,
        )

        return search_documents_vector_fake(
            query=request.query,
            candidates=candidates,
            include_content=request.include_content,
            limit=request.limit,
        )

    tokens = tokenize_search_query(request.query)
    candidates = repository.search_document_candidates(
        query=request.query,
        tokens=tokens,
        document_type=request.document_type,
        limit=min(request.limit * 5, 250),
    )

    return search_documents_text_only(
        query=request.query,
        candidates=candidates,
        include_content=request.include_content,
        limit=request.limit,
    )
