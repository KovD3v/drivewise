from app.repositories.documents import DocumentsRepository
from app.schemas.advisor import AdvisorDocumentEvidence, AdvisorRecommendationItem
from app.services.search.documents import search_documents_text_only, tokenize_search_query


MAX_DOCUMENT_EVIDENCE_PER_ITEM = 3
DOCUMENT_CANDIDATE_LIMIT = 15


def attach_document_evidence(
    items: list[AdvisorRecommendationItem],
    documents_repository: DocumentsRepository,
) -> list[AdvisorRecommendationItem]:
    return [
        item.model_copy(
            update={
                "document_evidence": find_document_evidence_for_item(
                    item,
                    documents_repository,
                )
            }
        )
        for item in items
    ]


def find_document_evidence_for_item(
    item: AdvisorRecommendationItem,
    documents_repository: DocumentsRepository,
) -> list[AdvisorDocumentEvidence]:
    query = f"{item.vehicle.make} {item.vehicle.model}".strip()
    if not query:
        return []

    tokens = tokenize_search_query(query)
    candidates = documents_repository.search_document_candidates(
        query=query,
        tokens=tokens,
        document_type=None,
        limit=DOCUMENT_CANDIDATE_LIMIT,
    )
    search_result = search_documents_text_only(
        query=query,
        candidates=candidates,
        include_content=False,
        limit=MAX_DOCUMENT_EVIDENCE_PER_ITEM,
    )

    return [
        AdvisorDocumentEvidence(
            document_id=result["id"],
            title=result["title"],
            document_type=result["document_type"],
            score=result["score"],
            snippet=result["snippet"],
        )
        for result in search_result["items"]
    ]
