from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT / "apps/api/scripts/catalog_status.py"
AS_OF = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)


def load_catalog_status_script():
    spec = importlib.util.spec_from_file_location(
        "drivewise_catalog_status",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_catalog_status_help_exits_zero():
    module = load_catalog_status_script()

    try:
        module.main(["--help"])
    except SystemExit as error:
        assert error.code == 0
    else:
        raise AssertionError("--help should exit through argparse")


def test_catalog_status_requires_database_url(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    module = load_catalog_status_script()

    exit_code = module.main([], env_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "DATABASE_URL is not set" in captured.err


def test_catalog_status_rejects_placeholder_database_url(
    monkeypatch,
    capsys,
    tmp_path,
):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://your-user:your-password@your-neon-host.neon.tech/"
        "your-database?sslmode=require",
    )
    module = load_catalog_status_script()

    exit_code = module.main([], env_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "DATABASE_URL still contains placeholders" in captured.err


def test_catalog_status_formats_rankable_coverage_and_blind_spots():
    module = load_catalog_status_script()
    candidates = [
        {
            "spec": {"body_style": "city_car", "fuel_type": "petrol"},
            "offer": {"condition": "new", "price_eur": 10_000},
        },
        {
            "spec": {"body_style": "wagon", "fuel_type": "diesel"},
            "offer": {"condition": "certified", "price_eur": 30_000},
        },
    ]

    report = module.format_report(
        candidates,
        {"inactive_offer": 1, "source_not_permitted": 2},
        as_of=AS_OF,
    )

    assert "Listings: total=5, rankable=2" in report
    assert report.index("source_not_permitted: 2") < report.index(
        "inactive_offer: 1"
    )
    assert "city_car: 1" in report
    assert "petrol: 1" in report
    assert "new: 1" in report
    assert "used: 1" in report
    assert "min=10000.00, max=30000.00" in report
    assert "Zero-coverage body styles: crossover" in report
    assert "Zero-coverage fuel types: electric" in report


def test_catalog_status_reads_repository_at_pinned_time(
    monkeypatch,
    capsys,
    tmp_path,
):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://drivewise:secret@db.example.test/drivewise?sslmode=require",
    )
    module = load_catalog_status_script()
    calls: list[tuple[str, datetime]] = []

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, query):
            assert query == "SET TRANSACTION READ ONLY"

    class FakeRepository:
        def __init__(self, conn):
            assert isinstance(conn, FakeConnection)

        def list_candidates(self, *, as_of):
            calls.append(("candidates", as_of))
            return []

        def count_excluded_candidates(self, *, as_of):
            calls.append(("exclusions", as_of))
            return {"inactive_offer": 1}

    monkeypatch.setattr(module.psycopg, "connect", lambda *args, **kwargs: FakeConnection())
    monkeypatch.setattr(module, "AdvisorRepository", FakeRepository)

    exit_code = module.main(
        ["--as-of", AS_OF.isoformat()],
        env_path=tmp_path / ".env",
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert calls == [("candidates", AS_OF), ("exclusions", AS_OF)]
    assert "Listings: total=1, rankable=0" in captured.out
    assert "Zero-coverage body styles: city_car" in captured.out
