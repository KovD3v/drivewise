import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT / "apps/api/scripts/migrate.py"


def load_migrate_script():
    spec = importlib.util.spec_from_file_location("drivewise_migrate_script", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migrate_script_requires_database_url(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    module = load_migrate_script()

    exit_code = module.main(env_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "DATABASE_URL is not set" in captured.err
    assert ".env" in captured.err


def test_migrate_script_rejects_placeholder_database_url(
    monkeypatch,
    capsys,
    tmp_path,
):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://your-user:your-password@your-neon-host.neon.tech/"
        "your-database?sslmode=require",
    )
    module = load_migrate_script()

    exit_code = module.main(env_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "DATABASE_URL still contains placeholders" in captured.err


def test_migrate_script_rejects_masked_database_url(
    monkeypatch,
    capsys,
    tmp_path,
):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://drivewise:***@db.example.test/drivewise?sslmode=require",
    )
    module = load_migrate_script()

    exit_code = module.main(env_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "DATABASE_URL still contains placeholders" in captured.err


def test_migrate_script_prints_applied_and_existing_migrations(
    monkeypatch,
    capsys,
    tmp_path,
):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://drivewise:secret@db.example.test/drivewise?sslmode=require",
    )
    module = load_migrate_script()
    report = module.MigrationRun(
        applied=["0002_create_mvp_schema.sql"],
        already_applied=["0001_enable_pgvector.sql"],
    )
    monkeypatch.setattr(module, "run_migrations", lambda database_url: report)

    exit_code = module.main(env_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Already applied 0001_enable_pgvector.sql" in captured.out
    assert "Applied 0002_create_mvp_schema.sql" in captured.out


def test_migrate_script_loads_database_url_from_env_file(
    monkeypatch,
    capsys,
    tmp_path,
):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(
        'DATABASE_URL="postgresql://drivewise:secret@db.example.test/'
        'drivewise?sslmode=require"\n'
    )
    module = load_migrate_script()
    report = module.MigrationRun(applied=[], already_applied=[])
    monkeypatch.setattr(module, "run_migrations", lambda database_url: report)

    exit_code = module.main(env_path=env_path)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No pending migrations." in captured.out


def test_migrate_script_reports_connection_failure_without_printing_url(
    monkeypatch,
    capsys,
    tmp_path,
):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://drivewise:secret@db.example.test/drivewise?sslmode=require",
    )
    module = load_migrate_script()

    def fail_connection(database_url):
        raise module.psycopg.OperationalError("connection failed")

    monkeypatch.setattr(module, "run_migrations", fail_connection)

    exit_code = module.main(env_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Could not connect to the database configured by DATABASE_URL" in captured.err
    assert "secret" not in captured.err
    assert "db.example.test" not in captured.err


def test_migrate_script_reports_failing_migration_and_error_type(
    monkeypatch,
    capsys,
    tmp_path,
):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://drivewise:secret@db.example.test/drivewise?sslmode=require",
    )
    module = load_migrate_script()

    def fail_migration(database_url):
        error = module.psycopg.ProgrammingError('syntax error at or near "BROKEN"')
        error.migration_name = "0004_broken.sql"
        raise error

    monkeypatch.setattr(module, "run_migrations", fail_migration)

    exit_code = module.main(env_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "0004_broken.sql" in captured.err
    assert "Exception type: ProgrammingError" in captured.err
    assert 'syntax error at or near "BROKEN"' in captured.err
    assert "secret" not in captured.err
    assert "db.example.test" not in captured.err
