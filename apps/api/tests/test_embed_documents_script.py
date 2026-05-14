import importlib.util
from pathlib import Path
from uuid import UUID


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT / "apps/api/scripts/embed_documents.py"


def load_embed_script():
    spec = importlib.util.spec_from_file_location(
        "drivewise_embed_documents",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_embed_documents_script_requires_fake_provider(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://drivewise:secret@db.example.test/drivewise?sslmode=require",
    )
    module = load_embed_script()

    exit_code = module.main(["--provider", "openai"], env_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Only the fake provider is available" in captured.err


def test_embed_documents_script_dry_run_does_not_write(
    monkeypatch,
    capsys,
    tmp_path,
):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://drivewise:secret@db.example.test/drivewise?sslmode=require",
    )
    module = load_embed_script()
    conn = FakeEmbeddingConnection([document_row()])
    monkeypatch.setattr(module.psycopg, "connect", lambda *args, **kwargs: conn)

    exit_code = module.main(
        ["--provider", "fake", "--limit", "1"],
        env_path=tmp_path / ".env",
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Embedding dry-run plan" in captured.out
    assert "Provider: fake" in captured.out
    assert "Documents selected: 1" in captured.out
    assert "Embedded: 0" in captured.out
    assert "No database writes were made." in captured.out
    assert conn.update_queries == []
    assert "secret" not in captured.out


def test_embed_documents_script_write_updates_embeddings(
    monkeypatch,
    capsys,
    tmp_path,
):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://drivewise:secret@db.example.test/drivewise?sslmode=require",
    )
    module = load_embed_script()
    conn = FakeEmbeddingConnection([document_row()])
    monkeypatch.setattr(module.psycopg, "connect", lambda *args, **kwargs: conn)

    exit_code = module.main(
        [
            "--provider",
            "fake",
            "--write",
            "--limit",
            "1",
            "--model",
            "fake-embedding-1536",
        ],
        env_path=tmp_path / ".env",
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Embedding write result" in captured.out
    assert "Embedded: 1" in captured.out
    assert "Skipped existing: 0" in captured.out
    assert conn.rows[0]["embedding"] is not None
    assert conn.rows[0]["embedding_model"] == "fake-embedding-1536"


def test_embed_documents_script_does_not_import_openai():
    module = load_embed_script()

    assert "openai" not in module.__dict__


def document_row() -> dict:
    return {
        "id": UUID("40000000-0000-4000-8000-000000000001"),
        "title": "Fiat Panda seed note",
        "document_type": "seed_note",
        "content": "Fiat Panda compact city car.",
        "embedding": None,
        "embedding_model": None,
        "created_at": "2026-01-01T00:00:00Z",
    }


class FakeCursor:
    def __init__(self, rows: list[dict] | dict) -> None:
        self.rows = rows

    def fetchall(self) -> list[dict]:
        assert isinstance(self.rows, list)
        return self.rows

    def fetchone(self) -> dict:
        assert isinstance(self.rows, dict)
        return self.rows


class FakeEmbeddingConnection:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.update_queries: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query: str, params=()) -> FakeCursor:
        normalized_query = " ".join(query.split())

        if normalized_query.startswith("SELECT count(*) AS count FROM documents"):
            return FakeCursor(
                {
                    "count": len(
                        [row for row in self.rows if row["embedding"] is not None]
                    )
                }
            )

        if normalized_query.startswith("SELECT id, title, document_type"):
            limit = params[-1]
            rows = [row for row in self.rows if row["embedding"] is None]
            return FakeCursor(rows[:limit])

        if normalized_query.startswith("UPDATE documents"):
            embedding, model, document_id = params
            for row in self.rows:
                if row["id"] == document_id:
                    row["embedding"] = embedding
                    row["embedding_model"] = model
                    break
            self.update_queries.append(normalized_query)
            return FakeCursor([])

        raise AssertionError(f"Unexpected query: {normalized_query}")
