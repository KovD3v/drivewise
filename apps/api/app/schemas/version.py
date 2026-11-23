from app.schemas.base import ApiModel


class VersionResponse(ApiModel):
    service: str
    api_version: str | None
    git_commit: str | None
    scoring_version: str
    schema_version: str | None
