from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    # Responses always include fields that have defaults, so the OpenAPI
    # response schemas mark them required; request schemas keep them optional.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
