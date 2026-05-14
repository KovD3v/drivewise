import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.config import get_settings
from app.ingestion.sources import (
    DOCUMENT_TYPES,
    FirecrawlSourceConfig,
    LocalFixtureSourceConfig,
    PlannerDocumentType,
)


MAX_SOURCE_LIMIT = 100
MAX_CRAWL_DEPTH = 3


class FirecrawlConfigError(ValueError):
    pass


@dataclass(frozen=True)
class FirecrawlIngestionPlan:
    firecrawl_sources: tuple[FirecrawlSourceConfig, ...]
    local_sources: tuple[LocalFixtureSourceConfig, ...]
    api_key_present: bool
    warnings: tuple[str, ...]
    http_requests_enabled: bool = False
    database_writes_enabled: bool = False


def load_sources_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    try:
        payload = json.loads(config_path.read_text())
    except FileNotFoundError as error:
        raise FirecrawlConfigError(f"Sources config not found: {config_path}") from error
    except json.JSONDecodeError as error:
        raise FirecrawlConfigError(
            f"Sources config is not valid JSON: {config_path}"
        ) from error

    if not isinstance(payload, dict):
        raise FirecrawlConfigError("Sources config must be a JSON object")
    return payload


def plan_firecrawl_ingestion(
    source_config: dict[str, Any],
    firecrawl_api_key: str | None = None,
) -> FirecrawlIngestionPlan:
    sources = _source_entries(source_config)
    firecrawl_sources: list[FirecrawlSourceConfig] = []
    local_sources: list[LocalFixtureSourceConfig] = []

    for index, source in enumerate(sources, start=1):
        source_type = _required_string(source, "type", index)
        if source_type == "firecrawl":
            firecrawl_sources.append(_parse_firecrawl_source(source, index))
        elif source_type == "local_fixture":
            local_sources.append(_parse_local_source(source, index))
        else:
            raise FirecrawlConfigError(
                f"Invalid source type at sources[{index}]: {source_type}"
            )

    api_key = firecrawl_api_key
    if api_key is None:
        api_key = get_settings().firecrawl_api_key

    warnings: list[str] = []
    if not api_key:
        warnings.append(
            "FIRECRAWL_API_KEY is not set; this plan is still valid but cannot "
            "be executed until a key is configured."
        )

    return FirecrawlIngestionPlan(
        firecrawl_sources=tuple(firecrawl_sources),
        local_sources=tuple(local_sources),
        api_key_present=bool(api_key),
        warnings=tuple(warnings),
    )


def _source_entries(source_config: dict[str, Any]) -> list[dict[str, Any]]:
    sources = source_config.get("sources")
    if not isinstance(sources, list) or not sources:
        raise FirecrawlConfigError("Sources config must contain a non-empty sources list")

    entries: list[dict[str, Any]] = []
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            raise FirecrawlConfigError(f"Source at sources[{index}] must be an object")
        entries.append(source)
    return entries


def _parse_firecrawl_source(
    source: dict[str, Any],
    index: int,
) -> FirecrawlSourceConfig:
    url = _required_string(source, "url", index)
    _validate_http_url(url, index)

    document_type = source.get("document_type", "vehicle_profile")
    if not isinstance(document_type, str) or document_type not in DOCUMENT_TYPES:
        raise FirecrawlConfigError(
            f"Invalid document_type at sources[{index}]: {document_type}"
        )

    return FirecrawlSourceConfig(
        name=_required_string(source, "name", index),
        source_type="firecrawl",
        url=url,
        limit=_bounded_int(source.get("limit", 10), "limit", index, MAX_SOURCE_LIMIT),
        document_type=document_type,  # type: ignore[arg-type]
        crawl_depth=_bounded_int(
            source.get("crawl_depth", 1),
            "crawl_depth",
            index,
            MAX_CRAWL_DEPTH,
            minimum=0,
        ),
    )


def _parse_local_source(
    source: dict[str, Any],
    index: int,
) -> LocalFixtureSourceConfig:
    return LocalFixtureSourceConfig(
        name=_required_string(source, "name", index),
        source_type="local_fixture",
        path=_required_string(source, "path", index),
        limit=_bounded_int(source.get("limit", 10), "limit", index, MAX_SOURCE_LIMIT),
    )


def _required_string(source: dict[str, Any], key: str, index: int) -> str:
    value = source.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise FirecrawlConfigError(f"Missing or invalid {key} at sources[{index}]")
    return value.strip()


def _bounded_int(
    value: Any,
    key: str,
    index: int,
    maximum: int,
    minimum: int = 1,
) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise FirecrawlConfigError(f"Missing or invalid {key} at sources[{index}]")
    if value < minimum or value > maximum:
        raise FirecrawlConfigError(
            f"{key} at sources[{index}] must be between {minimum} and {maximum}"
        )
    return value


def _validate_http_url(url: str, index: int) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise FirecrawlConfigError(
            f"Invalid url at sources[{index}]: expected http or https URL"
        )


def document_type_value(value: str) -> PlannerDocumentType:
    if value not in DOCUMENT_TYPES:
        raise FirecrawlConfigError(f"Invalid document_type: {value}")
    return value  # type: ignore[return-value]
