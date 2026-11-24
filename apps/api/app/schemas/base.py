from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    # Responses always include fields that have defaults, so the OpenAPI
    # response schemas mark them required; request schemas keep them optional.
    # Infinity and NaN fail validation here instead of reaching Postgres JSONB,
    # which cannot store them. Over HTTP the default 422 handler still cannot
    # serialise the rejected inf input; that needs a handler in app/main.py.
    model_config = ConfigDict(
        json_schema_serialization_defaults_required=True,
        allow_inf_nan=False,
    )
