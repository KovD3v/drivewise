import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT / "apps/api/scripts/ingest_local.py"


def load_ingest_script():
    spec = importlib.util.spec_from_file_location("drivewise_ingest_script", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ingest_local_script_requires_database_url(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    module = load_ingest_script()

    exit_code = module.main(["--path", str(tmp_path)], env_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "DATABASE_URL is not set" in captured.err


def test_ingest_local_script_prints_result(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://drivewise:secret@db.example.test/drivewise?sslmode=require",
    )
    module = load_ingest_script()
    result = module.IngestionResult(inserted=2, skipped=1, updated=0)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(module.psycopg, "connect", lambda *args, **kwargs: FakeConnection())
    monkeypatch.setattr(
        module,
        "ingest_local_documents",
        lambda conn, path, source_name, source_type: result,
    )

    exit_code = module.main(["--path", str(tmp_path)], env_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Inserted: 2" in captured.out
    assert "Skipped: 1" in captured.out
    assert "Updated: 0" in captured.out
