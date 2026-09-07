from __future__ import annotations

from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from app.schemas.guided_decisions import GuidedDecisionRecord, GuidedDecisionResponse


class GuidedDecisionNotFoundError(LookupError):
    pass


class GuidedDecisionVersionConflictError(RuntimeError):
    def __init__(self, current_version: int) -> None:
        super().__init__(f"Current profile version is {current_version}.")
        self.current_version = current_version


class GuidedDecisionsRepository:
    def __init__(self, conn) -> None:
        self.conn = conn

    def create(
        self,
        *,
        response: GuidedDecisionResponse,
        locale: str,
        market: str,
        user_message: str,
    ) -> None:
        profile_payload = response.decision_profile.model_dump(mode="json")
        response_payload = response.model_dump(mode="json", by_alias=True)
        self.conn.execute(
            """
            INSERT INTO guided_decisions (
              id,
              locale,
              market,
              status,
              profile_version,
              decision_profile,
              last_response,
              created_at,
              updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now())
            """,
            (
                response.decision_id,
                locale,
                market,
                response.status,
                response.profile_version,
                Jsonb(profile_payload),
                Jsonb(response_payload),
            ),
        )
        self._insert_turn(response=response, user_message=user_message)

    def get(self, decision_id: UUID, *, for_update: bool = False):
        lock_clause = "FOR UPDATE" if for_update else ""
        row = self.conn.execute(
            f"""
            SELECT
              id,
              locale,
              market,
              status,
              profile_version,
              decision_profile,
              last_response,
              created_at,
              updated_at
            FROM guided_decisions
            WHERE id = %s
            {lock_clause}
            """,
            (decision_id,),
        ).fetchone()
        if row is None:
            raise GuidedDecisionNotFoundError(str(decision_id))
        return GuidedDecisionRecord.model_validate(row)

    def get_at_version(
        self,
        decision_id: UUID,
        *,
        expected_profile_version: int,
    ) -> GuidedDecisionRecord:
        record = self.get(decision_id, for_update=True)
        if record.profile_version != expected_profile_version:
            raise GuidedDecisionVersionConflictError(record.profile_version)
        return record

    def update(
        self,
        *,
        response: GuidedDecisionResponse,
        previous_profile_version: int,
        user_message: str,
    ) -> None:
        profile_payload = response.decision_profile.model_dump(mode="json")
        response_payload = response.model_dump(mode="json", by_alias=True)
        result = self.conn.execute(
            """
            UPDATE guided_decisions
            SET status = %s,
                profile_version = %s,
                decision_profile = %s,
                last_response = %s,
                updated_at = now()
            WHERE id = %s
              AND profile_version = %s
            """,
            (
                response.status,
                response.profile_version,
                Jsonb(profile_payload),
                Jsonb(response_payload),
                response.decision_id,
                previous_profile_version,
            ),
        )
        if result.rowcount != 1:
            current = self.get(response.decision_id, for_update=True)
            raise GuidedDecisionVersionConflictError(current.profile_version)
        self._insert_turn(response=response, user_message=user_message)

    def _insert_turn(
        self,
        *,
        response: GuidedDecisionResponse,
        user_message: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO guided_decision_turns (
              id,
              decision_id,
              profile_version,
              user_message,
              assistant_message,
              updated_fields,
              profile_snapshot,
              response_payload,
              created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
            """,
            (
                uuid4(),
                response.decision_id,
                response.profile_version,
                user_message,
                response.message,
                Jsonb(response.updated_fields),
                Jsonb(response.decision_profile.model_dump(mode="json")),
                Jsonb(response.model_dump(mode="json", by_alias=True)),
            ),
        )
