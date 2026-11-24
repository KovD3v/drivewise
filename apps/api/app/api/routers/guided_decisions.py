from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_advisor_repository,
    get_guided_decisions_repository,
)
from app.repositories.advisor import AdvisorRepository
from app.repositories.guided_decisions import (
    GuidedDecisionNotFoundError,
    GuidedDecisionsRepository,
    GuidedDecisionVersionConflictError,
)
from app.schemas.guided_decisions import (
    AddGuidedDecisionTurnRequest,
    CreateGuidedDecisionRequest,
    DecisionProfile,
    GuidedDecisionResponse,
)
from app.services.guided_decisions.engine import (
    MAX_GUIDED_DECISION_TURNS,
    process_guided_decision_turn,
    recompute_guided_decision_response,
)


router = APIRouter(prefix="/guided-decisions", tags=["guided-decisions"])


def get_guided_decision_clock() -> datetime:
    return datetime.now(timezone.utc)


@router.post(
    "",
    response_model=GuidedDecisionResponse,
    status_code=status.HTTP_200_OK,
)
def create_guided_decision(
    request: CreateGuidedDecisionRequest,
    decisions_repository: Annotated[
        GuidedDecisionsRepository,
        Depends(get_guided_decisions_repository),
    ],
    advisor_repository: Annotated[
        AdvisorRepository,
        Depends(get_advisor_repository),
    ],
    as_of: Annotated[datetime, Depends(get_guided_decision_clock)],
) -> GuidedDecisionResponse:
    result = process_guided_decision_turn(
        decision_id=uuid4(),
        profile_version=1,
        current_profile=DecisionProfile(),
        message=request.message,
        advisor_repository=advisor_repository,
        as_of=as_of,
    )
    decisions_repository.create(
        response=result.response,
        locale=request.locale,
        market=request.market,
        user_message=request.message,
    )
    return result.response


@router.post(
    "/{decision_id}/turns",
    response_model=GuidedDecisionResponse,
)
def add_guided_decision_turn(
    decision_id: UUID,
    request: AddGuidedDecisionTurnRequest,
    decisions_repository: Annotated[
        GuidedDecisionsRepository,
        Depends(get_guided_decisions_repository),
    ],
    advisor_repository: Annotated[
        AdvisorRepository,
        Depends(get_advisor_repository),
    ],
    as_of: Annotated[datetime, Depends(get_guided_decision_clock)],
) -> GuidedDecisionResponse:
    try:
        record = decisions_repository.get_at_version(
            decision_id,
            expected_profile_version=request.expected_profile_version,
        )
        if record.status != "active":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "guided_decision_not_active",
                    "status": record.status,
                },
            )
        # Checked before any catalogue query, so a capped link costs nothing.
        if record.profile_version >= MAX_GUIDED_DECISION_TURNS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "max_turns_reached"},
            )

        result = process_guided_decision_turn(
            decision_id=decision_id,
            profile_version=record.profile_version + 1,
            current_profile=record.decision_profile,
            message=request.message,
            advisor_repository=advisor_repository,
            as_of=as_of,
        )
        decisions_repository.update(
            response=result.response,
            previous_profile_version=record.profile_version,
            user_message=request.message,
        )
        return result.response
    except GuidedDecisionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "guided_decision_not_found"},
        ) from error
    except GuidedDecisionVersionConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "profile_version_conflict",
                "currentProfileVersion": error.current_version,
            },
        ) from error


@router.get("/{decision_id}", response_model=GuidedDecisionResponse)
def get_guided_decision(
    decision_id: UUID,
    decisions_repository: Annotated[
        GuidedDecisionsRepository,
        Depends(get_guided_decisions_repository),
    ],
    advisor_repository: Annotated[
        AdvisorRepository,
        Depends(get_advisor_repository),
    ],
    as_of: Annotated[datetime, Depends(get_guided_decision_clock)],
) -> GuidedDecisionResponse:
    try:
        record = decisions_repository.get(decision_id)
    except GuidedDecisionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "guided_decision_not_found"},
        ) from error

    if record.last_response is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "guided_decision_has_no_response"},
        )
    # The ranking is rebuilt from the stored profile on every read, so a
    # reopened link follows the current catalogue and source permissions.
    return recompute_guided_decision_response(
        GuidedDecisionResponse.model_validate(record.last_response),
        record.decision_profile,
        advisor_repository=advisor_repository,
        as_of=as_of,
    )
