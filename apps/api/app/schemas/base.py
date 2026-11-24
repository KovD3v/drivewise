from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    # Responses always include fields that have defaults, so the OpenAPI
    # response schemas mark them required; request schemas keep them optional.
    # Infinity and NaN are rejected at validation time (HTTP 422): Postgres
    # JSONB cannot store them, so accepting them would fail later with a 500.
    model_config = ConfigDict(
        json_schema_serialization_defaults_required=True,
        allow_inf_nan=False,
    )
