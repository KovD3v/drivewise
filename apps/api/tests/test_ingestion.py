from pathlib import Path
from uuid import UUID

from app.ingestion.local import (
    LocalDocument,
    compute_content_hash,
    ingest_local_documents,
    load_local_documents,
    normalize_vehicle_document,
    upsert_document,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURES_PATH = ROOT / "data/fixtures/ingestion"
SOURCE_ID = UUID("10000000-0000-4000-8000-000000000010")


def test_content_hash_is_stable_and_normalizes_newlines():
    assert compute_content_hash("Fiat Panda\n2024") == compute_content_hash(
        "Fiat Panda\r\n2024"
    )
    assert compute_content_hash("Fiat Panda\n2024") != compute_content_hash(
        "Toyota Yaris\n2024"
    )


def test_load_local_documents_reads_supported_fixture_files():
    documents = load_local_documents(FIXTURES_PATH)

    assert [document.file_name for document in documents] == [
        "fiat-panda-listing.txt",
        "fiat-panda.md",
        "toyota-yaris-hybrid.md",
    ]
    assert documents[0].document_type == "listing_snapshot"
    assert documents[1].document_type == "vehicle_profile"


def test_normalize_vehicle_document_extracts_only_explicit_fields():
    document = LocalDocument(
        title="Fiat Panda local note",
        content=(
            "Make: Fiat\n"
            "Model: Panda\n"
            "Year: 2024\n"
            "Indicative price EUR: 15500\n"
            "Mileage km: about 7000\n"
            "Fuel type: mild_hybrid_petrol\n"
            "Free text: compact city car\n"
        ),
        document_type="vehicle_profile",
        file_name="fiat-panda.md",
        local_path="data/fixtures/ingestion/fiat-panda.md",
        metadata={},
    )

    normalized = normalize_vehicle_document(document)

    assert normalized.proposed_vehicle == {
        "make": "Fiat",
        "model": "Panda",
        "model_year": 2024,
        "fuel_type": "mild_hybrid_petrol",
    }
    assert normalized.proposed_listing == {"price_eur": 15500}
    assert normalized.metadata["unparsed_fields"]["mileage_km"] == "about 7000"
    assert normalized.metadata["unparsed_fields"]["free_text"] == "compact city car"


def test_upsert_document_skips_duplicate_content_hash():
    conn = FakeIngestionConnection()
    document = load_local_documents(FIXTURES_PATH)[1]

    first = upsert_document(conn, SOURCE_ID, document)
    second = upsert_document(conn, SOURCE_ID, document)

    assert first.status == "inserted"
    assert second.status == "skipped"
    assert len(conn.documents) == 1


def test_upsert_document_updates_same_path_when_content_changes():
    conn = FakeIngestionConnection()
    document = load_local_documents(FIXTURES_PATH)[1]
    changed_document = LocalDocument(
        title=document.title,
        content=f"{document.content}\nNota locale aggiornata.",
        document_type=document.document_type,
        file_name=document.file_name,
        local_path=document.local_path,
        metadata=document.metadata,
    )

    first = upsert_document(conn, SOURCE_ID, document)
    second = upsert_document(conn, SOURCE_ID, changed_document)

    assert first.status == "inserted"
    assert second.status == "updated"
    assert len(conn.documents) == 1
    assert conn.documents[0]["content"].endswith("Nota locale aggiornata.")


def test_ingest_local_documents_counts_inserted_and_skipped():
    conn = FakeIngestionConnection()

    first = ingest_local_documents(conn, FIXTURES_PATH)
    second = ingest_local_documents(conn, FIXTURES_PATH)

    assert first.inserted == 3
    assert first.skipped == 0
    assert first.updated == 0
    assert second.inserted == 0
    assert second.skipped == 3
    assert second.updated == 0


class FakeCursor:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class FakeIngestionConnection:
    def __init__(self) -> None:
        self.source_id = SOURCE_ID
        self.documents: list[dict] = []

    def execute(self, query, params=()):
        query_upper = " ".join(query.upper().split())

        if query_upper.startswith("INSERT INTO SOURCES"):
            return FakeCursor({"id": self.source_id})

        if "METADATA->>'CONTENT_HASH'" in query_upper:
            source_id, content_hash = params
            return FakeCursor(
                next(
                    (
                        document
                        for document in self.documents
                        if document["source_id"] == source_id
                        and document["metadata"]["content_hash"] == content_hash
                    ),
                    None,
                )
            )

        if "METADATA->>'LOCAL_PATH'" in query_upper:
            source_id, local_path = params
            return FakeCursor(
                next(
                    (
                        document
                        for document in self.documents
                        if document["source_id"] == source_id
                        and document["metadata"]["local_path"] == local_path
                    ),
                    None,
                )
            )

        if query_upper.startswith("UPDATE DOCUMENTS"):
            title, content, document_type, metadata, document_id = params
            for document in self.documents:
                if document["id"] == document_id:
                    document.update(
                        {
                            "title": title,
                            "content": content,
                            "document_type": document_type,
                            "metadata": metadata.obj,
                        }
                    )
                    return FakeCursor({"id": document_id})
            return FakeCursor(None)

        if query_upper.startswith("INSERT INTO DOCUMENTS"):
            (
                document_id,
                source_id,
                document_type,
                title,
                content,
                metadata,
            ) = params
            self.documents.append(
                {
                    "id": document_id,
                    "source_id": source_id,
                    "document_type": document_type,
                    "title": title,
                    "content": content,
                    "metadata": metadata.obj,
                }
            )
            return FakeCursor({"id": document_id})

        raise AssertionError(f"Unexpected query: {query}")
