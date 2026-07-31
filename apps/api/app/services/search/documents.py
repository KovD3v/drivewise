import re
from datetime import datetime
from typing import Any


SEARCH_MODE_TEXT_ONLY = "text_only"
SEARCH_MODE_VECTOR_FAKE = "vector_fake"
TITLE_EXACT_WEIGHT = 8.0
CONTENT_EXACT_WEIGHT = 4.0
TITLE_TOKEN_WEIGHT = 2.0
CONTENT_TOKEN_WEIGHT = 1.0
MAX_RECENCY_BOOST = 0.25
SINGLE_DOCUMENT_RECENCY_BOOST = 0.05
SNIPPET_CHARACTERS = 180
TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")
MAX_QUERY_TOKENS = 16


def search_documents_text_only(
    *,
    query: str,
    candidates: list[dict[str, Any]],
    include_content: bool,
    limit: int,
) -> dict[str, Any]:
    normalized_query = normalize_search_query(query)
    tokens = tokenize_search_query(normalized_query)
    scored_candidates = []

    for candidate in candidates:
        base_score = score_document_candidate(candidate, normalized_query, tokens)
        if base_score <= 0:
            continue
        scored_candidates.append((candidate, base_score))

    recency_bounds = _recency_bounds(
        [candidate for candidate, _score in scored_candidates]
    )
    items = [
        _build_item(
            candidate,
            score=base_score + _recency_boost(candidate, recency_bounds),
            query=normalized_query,
            tokens=tokens,
            include_content=include_content,
        )
        for candidate, base_score in scored_candidates
    ]
    items.sort(
        key=lambda item: (
            -item["score"],
            item["title"].lower(),
            str(item["id"]),
        )
    )

    return {
        "query": normalized_query,
        "mode": SEARCH_MODE_TEXT_ONLY,
        "items": items[:limit],
    }


def search_documents_vector_fake(
    *,
    query: str,
    candidates: list[dict[str, Any]],
    include_content: bool,
    limit: int,
) -> dict[str, Any]:
    normalized_query = normalize_search_query(query)
    tokens = tokenize_search_query(normalized_query)
    items = [
        _build_item(
            candidate,
            score=float(_row_value(candidate, "score")),
            query=normalized_query,
            tokens=tokens,
            include_content=include_content,
        )
        for candidate in candidates
    ]

    return {
        "query": normalized_query,
        "mode": SEARCH_MODE_VECTOR_FAKE,
        "items": items[:limit],
    }


def normalize_search_query(query: str) -> str:
    return " ".join(query.strip().split())


def tokenize_search_query(query: str) -> tuple[str, ...]:
    tokens = []
    seen = set()
    for match in TOKEN_PATTERN.finditer(query.lower()):
        token = match.group(0)
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
        if len(tokens) == MAX_QUERY_TOKENS:
            break
    return tuple(tokens)


def score_document_candidate(
    candidate: dict[str, Any],
    normalized_query: str,
    tokens: tuple[str, ...],
) -> float:
    title = _normalized_text(_row_value(candidate, "title"))
    content = _normalized_text(_row_value(candidate, "content"))
    query = normalized_query.lower()
    score = 0.0

    if query and query in title:
        score += TITLE_EXACT_WEIGHT
    if query and query in content:
        score += CONTENT_EXACT_WEIGHT

    for token in tokens:
        if token in title:
            score += TITLE_TOKEN_WEIGHT
        if token in content:
            score += CONTENT_TOKEN_WEIGHT

    return score


def _build_item(
    candidate: dict[str, Any],
    *,
    score: float,
    query: str,
    tokens: tuple[str, ...],
    include_content: bool,
) -> dict[str, Any]:
    content = _row_value(candidate, "content")
    item = {
        "id": _row_value(candidate, "id"),
        "title": _row_value(candidate, "title"),
        "document_type": _row_value(candidate, "document_type"),
        "score": round(score, 4),
        "snippet": build_search_snippet(
            title=_row_value(candidate, "title"),
            content=content,
            query=query,
            tokens=tokens,
        ),
        "metadata": _minimal_metadata(candidate),
    }
    if include_content:
        item["content"] = content
    return item


def build_search_snippet(
    *,
    title: str,
    content: str,
    query: str,
    tokens: tuple[str, ...],
) -> str:
    content_match = _first_match_index(content, (query, *tokens))
    if content_match is not None:
        return _snippet_from(content, content_match)

    title_match = _first_match_index(title, (query, *tokens))
    if title_match is not None:
        return _snippet_from(title, title_match)

    return _snippet_from(content, 0)


def _first_match_index(text: str, needles: tuple[str, ...]) -> int | None:
    normalized_text = text.lower()
    for needle in needles:
        if not needle:
            continue
        index = normalized_text.find(needle.lower())
        if index >= 0:
            return index
    return None


def _snippet_from(text: str, match_index: int) -> str:
    start = 0 if match_index <= 40 else max(match_index - 40, 0)
    end = min(start + SNIPPET_CHARACTERS, len(text))
    snippet = text[start:end].strip()
    if start > 0:
        snippet = f"...{snippet}"
    if end < len(text):
        snippet = f"{snippet}..."
    return snippet


def _minimal_metadata(candidate: dict[str, Any]) -> dict[str, Any]:
    created_at = _row_value(candidate, "created_at")
    return {
        "source_id": _string_or_none(_row_value(candidate, "source_id")),
        "vehicle_id": _string_or_none(_row_value(candidate, "vehicle_id")),
        "listing_id": _string_or_none(_row_value(candidate, "listing_id")),
        "created_at": _datetime_or_string(created_at),
    }


def _recency_bounds(
    candidates: list[dict[str, Any]],
) -> tuple[datetime | None, datetime | None]:
    dates = [
        created_at
        for created_at in (_parse_datetime(_row_value(candidate, "created_at")) for candidate in candidates)
        if created_at is not None
    ]
    if not dates:
        return (None, None)
    return (min(dates), max(dates))


def _recency_boost(
    candidate: dict[str, Any],
    bounds: tuple[datetime | None, datetime | None],
) -> float:
    oldest, newest = bounds
    created_at = _parse_datetime(_row_value(candidate, "created_at"))
    if created_at is None or oldest is None or newest is None:
        return 0.0

    total_seconds = (newest - oldest).total_seconds()
    if total_seconds <= 0:
        return SINGLE_DOCUMENT_RECENCY_BOOST

    age_seconds = (created_at - oldest).total_seconds()
    return (age_seconds / total_seconds) * MAX_RECENCY_BOOST


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _datetime_or_string(value: Any) -> str | None:
    parsed = _parse_datetime(value)
    if parsed is not None:
        return parsed.isoformat()
    return _string_or_none(value)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _normalized_text(value: str) -> str:
    return " ".join(value.lower().split())


def _row_value(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row[key]
    return getattr(row, key)
