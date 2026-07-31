import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb


DocumentType = Literal[
    "vehicle_profile",
    "listing_snapshot",
    "review_excerpt",
    "spec_sheet",
    "seed_note",
]
SourceType = Literal["manual_seed", "public_dataset", "curated_internal"]

SUPPORTED_SUFFIXES = {".md", ".txt", ".json"}


@dataclass(frozen=True)
class LocalDocument:
    title: str
    content: str
    document_type: DocumentType
    file_name: str
    local_path: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedDocument:
    title: str
    content: str
    document_type: DocumentType
    proposed_vehicle: dict[str, Any]
    proposed_listing: dict[str, Any]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class DocumentUpsertResult:
    status: Literal["inserted", "skipped", "updated"]
    document_id: UUID


@dataclass(frozen=True)
class IngestionResult:
    inserted: int = 0
    skipped: int = 0
    updated: int = 0

    def add(self, result: DocumentUpsertResult) -> "IngestionResult":
        return IngestionResult(
            inserted=self.inserted + int(result.status == "inserted"),
            skipped=self.skipped + int(result.status == "skipped"),
            updated=self.updated + int(result.status == "updated"),
        )


def load_local_documents(path: str | Path) -> list[LocalDocument]:
    root = Path(path)
    if not root.exists():
        raise FileNotFoundError(f"Ingestion path does not exist: {root}")

    files = [root] if root.is_file() else sorted(root.rglob("*"))
    documents: list[LocalDocument] = []

    for file_path in files:
        if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if file_path.suffix.lower() == ".json":
            documents.extend(_load_json_documents(file_path))
        else:
            content = file_path.read_text()
            documents.append(
                LocalDocument(
                    title=_title_from_text(content, file_path),
                    content=content,
                    document_type=_infer_document_type(file_path),
                    file_name=file_path.name,
                    local_path=_local_path(file_path),
                    metadata={
                        "file_name": file_path.name,
                        "file_format": file_path.suffix.lower().removeprefix("."),
                    },
                )
            )

    return sorted(documents, key=lambda document: document.local_path)


def compute_content_hash(content: str) -> str:
    normalized_content = content.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()


def upsert_source(
    conn,
    *,
    name: str,
    source_key: str | None = None,
    market: str = "IT",
    source_type: SourceType = "curated_internal",
    url: str | None = None,
    license: str | None = "Synthetic local fixture",
    notes: str | None = "Local fixture ingestion. No external services called.",
) -> UUID:
    source_id = uuid4()
    stable_source_key = source_key or _stable_key(name)
    row = conn.execute(
        """
        INSERT INTO sources (
          id, source_key, name, source_type, market, url, license, notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_key) DO UPDATE SET
          name = EXCLUDED.name,
          source_type = EXCLUDED.source_type,
          market = EXCLUDED.market,
          url = EXCLUDED.url,
          license = EXCLUDED.license,
          notes = EXCLUDED.notes
        RETURNING id
        """,
        (
            source_id,
            stable_source_key,
            name,
            source_type,
            market,
            url,
            license,
            notes,
        ),
    ).fetchone()
    return _row_value(row, "id")


def upsert_document(
    conn,
    source_id: UUID,
    document: LocalDocument,
) -> DocumentUpsertResult:
    normalized = normalize_vehicle_document(document)
    metadata = _document_metadata(document, normalized)
    content_hash = metadata["content_hash"]

    existing_by_hash = conn.execute(
        """
        SELECT id
        FROM documents
        WHERE source_id = %s
          AND metadata->>'content_hash' = %s
        """,
        (source_id, content_hash),
    ).fetchone()
    if existing_by_hash is not None:
        return DocumentUpsertResult(
            status="skipped",
            document_id=_row_value(existing_by_hash, "id"),
        )

    existing_by_path = conn.execute(
        """
        SELECT id
        FROM documents
        WHERE source_id = %s
          AND metadata->>'local_path' = %s
        """,
        (source_id, document.local_path),
    ).fetchone()
    if existing_by_path is not None:
        document_id = _row_value(existing_by_path, "id")
        conn.execute(
            """
            UPDATE documents
            SET title = %s,
                content = %s,
                document_type = %s,
                metadata = %s,
                embedding = NULL,
                embedding_model = NULL
            WHERE id = %s
            RETURNING id
            """,
            (
                normalized.title,
                normalized.content,
                normalized.document_type,
                Jsonb(metadata),
                document_id,
            ),
        ).fetchone()
        return DocumentUpsertResult(status="updated", document_id=document_id)

    document_id = uuid4()
    conn.execute(
        """
        INSERT INTO documents (
          id,
          source_id,
          document_type,
          title,
          content,
          metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            document_id,
            source_id,
            normalized.document_type,
            normalized.title,
            normalized.content,
            Jsonb(metadata),
        ),
    ).fetchone()
    return DocumentUpsertResult(status="inserted", document_id=document_id)


def normalize_vehicle_document(document: LocalDocument) -> NormalizedDocument:
    fields = _extract_labeled_fields(document.content)
    proposed_vehicle: dict[str, Any] = {}
    proposed_listing: dict[str, Any] = {}
    unparsed_fields: dict[str, Any] = {}

    _assign_text(fields, proposed_vehicle, unparsed_fields, "make", "make")
    _assign_text(fields, proposed_vehicle, unparsed_fields, "model", "model")
    _assign_text(fields, proposed_vehicle, unparsed_fields, "fuel_type", "fuel_type")
    _assign_int(fields, proposed_vehicle, unparsed_fields, "year", "model_year")
    _assign_int(fields, proposed_listing, unparsed_fields, "price_eur", "price_eur")
    _assign_int(fields, proposed_listing, unparsed_fields, "mileage_km", "mileage")
    _assign_text(fields, proposed_listing, unparsed_fields, "condition", "condition")
    _assign_text(
        fields,
        proposed_listing,
        unparsed_fields,
        "location_region",
        "location_region",
    )
    if fields.get("free_text"):
        unparsed_fields["free_text"] = fields["free_text"]

    for key, value in fields.items():
        if key not in _KNOWN_FIELD_KEYS and value:
            unparsed_fields[key] = value

    metadata = {
        "normalization_version": 1,
        "proposed_vehicle": proposed_vehicle,
        "proposed_listing": proposed_listing,
        "unparsed_fields": unparsed_fields,
    }

    return NormalizedDocument(
        title=document.title,
        content=document.content,
        document_type=document.document_type,
        proposed_vehicle=proposed_vehicle,
        proposed_listing=proposed_listing,
        metadata=metadata,
    )


def ingest_local_documents(
    conn,
    path: str | Path,
    source_name: str = "Drivewise Local Fixture Ingestion",
    source_type: SourceType = "curated_internal",
) -> IngestionResult:
    source_id = upsert_source(conn, name=source_name, source_type=source_type)
    result = IngestionResult()

    for document in load_local_documents(path):
        result = result.add(upsert_document(conn, source_id, document))

    return result


def _load_json_documents(file_path: Path) -> list[LocalDocument]:
    payload = json.loads(file_path.read_text())
    entries = payload.get("documents", payload) if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        entries = [entries]

    documents: list[LocalDocument] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            content = json.dumps(entry, ensure_ascii=True, sort_keys=True)
            title = file_path.stem
            metadata: dict[str, Any] = {}
            document_type = _infer_document_type(file_path)
        else:
            content = str(
                entry.get("content")
                or json.dumps(entry, ensure_ascii=True, sort_keys=True)
            )
            title = str(entry.get("title") or _title_from_text(content, file_path))
            metadata = entry.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {"raw_metadata": metadata}
            document_type = _document_type_from_value(
                entry.get("document_type"),
                _infer_document_type(file_path),
            )

        documents.append(
            LocalDocument(
                title=title,
                content=content,
                document_type=document_type,
                file_name=file_path.name,
                local_path=f"{_local_path(file_path)}#{index}",
                metadata={
                    **metadata,
                    "file_name": file_path.name,
                    "file_format": "json",
                },
            )
        )

    return documents


def _title_from_text(content: str, file_path: Path) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        if stripped.lower().startswith("title:"):
            return stripped.split(":", maxsplit=1)[1].strip()
    return file_path.stem.replace("-", " ").title()


def _infer_document_type(file_path: Path) -> DocumentType:
    name = file_path.name.lower()
    if "listing" in name or "annuncio" in name:
        return "listing_snapshot"
    if "spec" in name:
        return "spec_sheet"
    return "vehicle_profile"


def _document_type_from_value(value: Any, fallback: DocumentType) -> DocumentType:
    allowed = {
        "vehicle_profile",
        "listing_snapshot",
        "review_excerpt",
        "spec_sheet",
        "seed_note",
    }
    return value if isinstance(value, str) and value in allowed else fallback


def _local_path(file_path: Path) -> str:
    return file_path.as_posix()


def _stable_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


FIELD_ALIASES = {
    "make": "make",
    "brand": "make",
    "marca": "make",
    "model": "model",
    "modello": "model",
    "year": "year",
    "model year": "year",
    "anno": "year",
    "fuel type": "fuel_type",
    "fuel": "fuel_type",
    "carburante": "fuel_type",
    "indicative price eur": "price_eur",
    "price eur": "price_eur",
    "prezzo eur": "price_eur",
    "prezzo": "price_eur",
    "mileage km": "mileage_km",
    "km": "mileage_km",
    "chilometri": "mileage_km",
    "condition": "condition",
    "condizione": "condition",
    "location region": "location_region",
    "regione": "location_region",
    "free text": "free_text",
}
_KNOWN_FIELD_KEYS = set(FIELD_ALIASES.values())


def _extract_labeled_fields(content: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in content.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", maxsplit=1)
        normalized_key = FIELD_ALIASES.get(key.strip().lower())
        if normalized_key:
            fields[normalized_key] = value.strip()
    return fields


def _assign_text(
    fields: dict[str, str],
    target: dict[str, Any],
    unparsed_fields: dict[str, Any],
    source_key: str,
    target_key: str,
) -> None:
    value = fields.get(source_key)
    if value:
        target[target_key] = value
    elif value is not None:
        unparsed_fields[source_key] = value


def _assign_int(
    fields: dict[str, str],
    target: dict[str, Any],
    unparsed_fields: dict[str, Any],
    source_key: str,
    target_key: str,
) -> None:
    value = fields.get(source_key)
    if value is None:
        return

    parsed = _parse_int(value)
    if parsed is None:
        unparsed_fields[source_key] = value
        return

    target[target_key] = parsed


def _parse_int(value: str) -> int | None:
    compact = value.strip().replace(".", "").replace(",", "")
    if not re.fullmatch(r"\d+", compact):
        return None
    return int(compact)


def _document_metadata(
    document: LocalDocument,
    normalized: NormalizedDocument,
) -> dict[str, Any]:
    return {
        **document.metadata,
        **normalized.metadata,
        "content_hash": compute_content_hash(document.content),
        "local_path": document.local_path,
        "file_name": document.file_name,
        "ingestion_mode": "local_fixture",
    }


def _row_value(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row[key]
    return row[0]
