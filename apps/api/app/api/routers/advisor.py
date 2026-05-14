from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_advisor_repository, get_documents_repository
from app.repositories.advisor import AdvisorRepository
from app.repositories.documents import DocumentsRepository
from app.schemas.advisor import (
    AdvisorRecommendationRequest,
    AdvisorRecommendationResponse,
)
from app.services.advisor.document_evidence import attach_document_evidence
from app.services.advisor.scoring import build_recommendations


router = APIRouter(prefix="/advisor", tags=["advisor"])


@router.post("/recommendations", response_model=AdvisorRecommendationResponse)
def create_recommendations(
    request: AdvisorRecommendationRequest,
    repository: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
    documents_repository: Annotated[
        DocumentsRepository,
        Depends(get_documents_repository),
    ],
) -> AdvisorRecommendationResponse:
    candidates = repository.list_candidates()
    items = build_recommendations(request, candidates)
    run_id = repository.create_run(request.model_dump(mode="json"))
    repository.save_items(run_id, items)
    repository.mark_run_completed(run_id)
    response_items = attach_document_evidence(items, documents_repository)

    return AdvisorRecommendationResponse(run_id=run_id, items=response_items)
