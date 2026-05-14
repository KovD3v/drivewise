import importlib.util
from pathlib import Path
from uuid import UUID


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT / "apps/api/scripts/plan_embeddings.py"


def load_plan_script():
    spec = importlib.util.spec_from_file_location("drivewise_plan_embeddings", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plan_embeddings_script_requires_database_url(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    module = load_plan_script()

    exit_code = module.main([], env_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "DATABASE_URL is not set" in captured.err


def test_plan_embeddings_script_prints_dry_run_plan(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://drivewise:secret@db.example.test/drivewise?sslmode=require",
    )
    module = load_plan_script()
    conn = FakeEmbeddingConnection(
        [
            {
                "id": UUID("40000000-0000-4000-8000-000000000001"),
                "title": "Fiat Panda seed note",
                "document_type": "seed_note",
                "content": "Fiat Panda compact city car. " * 8,
                "embedding": None,
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]
    )

    monkeypatch.setattr(
        module.psycopg,
        "connect",
        lambda *args, **kwargs: conn,
    )

    exit_code = module.main(
        [
            "--limit",
            "1",
            "--document-type",
            "seed_note",
            "--model",
            "text-embedding-3-small",
        ],
        env_path=tmp_path / ".env",
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Embedding dry-run plan" in captured.out
    assert "Model: text-embedding-3-small" in captured.out
    assert "Documents selected: 1" in captured.out
    assert "Fiat Panda seed note" in captured.out
    assert "Type: seed_note" in captured.out
    assert "Estimated chars:" in captured.out
    assert "No external provider calls were made." in captured.out
    assert "No database writes were made." in captured.out
    assert "secret" not in captured.out
    assert conn.write_queries == []


def test_plan_embeddings_script_rejects_limit_above_maximum(
    monkeypatch,
    capsys,
    tmp_path,
):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://drivewise:secret@db.example.test/drivewise?sslmode=require",
    )
    module = load_plan_script()

    exit_code = module.main(["--limit", "101"], env_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "limit must be between 1 and 100" in captured.err


def test_plan_embeddings_script_does_not_import_openai():
    module = load_plan_script()

    assert "openai" not in module.__dict__


class FakeCursor:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def fetchall(self) -> list[dict]:
        return self.rows


class FakeEmbeddingConnection:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.write_queries: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query: str, params=()) -> FakeCursor:
        normalized_query = " ".join(query.split())
        query_upper = normalized_query.upper()
        if any(
            query_upper.startswith(prefix)
            for prefix in ("INSERT", "UPDATE", "DELETE", "ALTER", "CREATE", "DROP")
        ):
            self.write_queries.append(normalized_query)
            raise AssertionError(f"Unexpected write query: {normalized_query}")

        document_type = params[0] if len(params) == 2 else None
        limit = params[-1]
        rows = [row for row in self.rows if row["embedding"] is None]
        if document_type is not None:
            rows = [row for row in rows if row["document_type"] == document_type]
        return FakeCursor(rows[:limit])
