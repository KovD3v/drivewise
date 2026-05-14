from app.repositories.filters import ListingFilters, VehicleFilters
from app.repositories.document_vector_search import search_document_vector_candidates
from app.repositories.documents import DocumentsRepository
from app.repositories.listings import ListingsRepository
from app.repositories.vehicles import VehiclesRepository


def test_vehicle_repository_uses_contains_for_text_and_exact_for_enums():
    conn = RecordingConnection()
    repository = VehiclesRepository(conn)

    repository.list_vehicles(
        VehicleFilters(
            make="yat",
            model="aris",
            fuel_type="hybrid_petrol",
            body_style="hatchback",
            market="IT",
            limit=10,
            offset=5,
        )
    )

    assert "make ILIKE %s" in conn.query
    assert "model ILIKE %s" in conn.query
    assert "fuel_type = %s" in conn.query
    assert "body_style = %s" in conn.query
    assert "market = %s" in conn.query
    assert conn.params == [
        "%yat%",
        "%aris%",
        "hybrid_petrol",
        "hatchback",
        "IT",
        10,
        5,
    ]


def test_listing_repository_uses_contains_for_text_filters():
    conn = RecordingConnection()
    repository = ListingsRepository(conn)

    repository.list_listings(
        ListingFilters(
            make="volks",
            model="gol",
            location_region="net",
            limit=25,
            offset=10,
        )
    )

    assert "v.make ILIKE %s" in conn.query
    assert "v.model ILIKE %s" in conn.query
    assert "l.location_region ILIKE %s" in conn.query
    assert conn.params == ["%volks%", "%gol%", "%net%", 25, 10]


def test_document_search_repository_uses_text_filters_without_vector_operators():
    conn = RecordingConnection()
    repository = DocumentsRepository(conn)

    repository.search_document_candidates(
        query="fiat panda",
        tokens=("fiat", "panda"),
        document_type="seed_note",
        limit=50,
    )

    assert "document_type = %s" in conn.query
    assert "title ILIKE %s OR content ILIKE %s" in conn.query
    assert "embedding" not in conn.query
    assert "<=>" not in conn.query
    assert "@@" not in conn.query
    assert conn.params == [
        "seed_note",
        "%fiat panda%",
        "%fiat panda%",
        "%fiat%",
        "%fiat%",
        "%panda%",
        "%panda%",
        50,
    ]


def test_document_vector_search_repository_uses_pgvector_without_selecting_embedding():
    conn = RecordingConnection()
    repository = DocumentsRepository(conn)

    repository.search_document_vector_candidates(
        query_embedding=[0.0] * 1536,
        document_type="seed_note",
        limit=7,
    )

    select_clause = conn.query.split("FROM documents d", maxsplit=1)[0]
    assert "WITH query_embedding" in conn.query
    assert "embedding IS NOT NULL" in conn.query
    assert "document_type = %s" in conn.query
    assert "d.embedding <=> q.value" in conn.query
    assert "1 - (d.embedding <=> q.value)" in conn.query
    assert "embedding_model" not in conn.query
    assert "embedding," not in select_clause
    assert conn.params[0].startswith("[0.0,0.0,0.0")
    assert conn.params[1:] == ["seed_note", 7]


def test_document_vector_search_rejects_wrong_embedding_dimension():
    conn = RecordingConnection()

    try:
        search_document_vector_candidates(
            conn,
            query_embedding=[0.0, 0.1],
            document_type=None,
            limit=10,
        )
    except ValueError as error:
        assert "1536 dimensions" in str(error)
    else:
        raise AssertionError("Expected invalid query embedding dimension")

    assert conn.query == ""


class RecordingConnection:
    def __init__(self) -> None:
        self.query = ""
        self.params: list[object] = []

    def execute(self, query: str, params: list[object]):
        self.query = query
        self.params = params
        return self

    def fetchall(self):
        return []

    def __iter__(self):
        return iter([])
