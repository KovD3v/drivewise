import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT / "apps/api/scripts/plan_firecrawl.py"


def load_plan_script():
    spec = importlib.util.spec_from_file_location("drivewise_plan_firecrawl", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_sources_config(path: Path) -> None:
    path.write_text(
        """
        {
          "sources": [
            {
              "name": "Example listing pages",
              "type": "firecrawl",
              "url": "https://example.com/cars",
              "limit": 5,
              "document_type": "listing_snapshot",
              "crawl_depth": 1
            }
          ]
        }
        """
    )


def test_plan_firecrawl_script_prints_plan_without_database_url(
    monkeypatch,
    capsys,
    tmp_path,
):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    sources_path = tmp_path / "sources.json"
    write_sources_config(sources_path)
    module = load_plan_script()

    exit_code = module.main(["--sources", str(sources_path)], env_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Firecrawl ingestion plan" in captured.out
    assert "Example listing pages" in captured.out
    assert "API key configured: no" in captured.out
    assert "No HTTP requests were made." in captured.out
    assert "No database writes were made." in captured.out
    assert "DATABASE_URL" not in captured.err


def test_plan_firecrawl_script_reports_invalid_config(capsys, tmp_path):
    sources_path = tmp_path / "sources.json"
    sources_path.write_text(
        """
        {
          "sources": [
            {
              "name": "Bad URL",
              "type": "firecrawl",
              "url": "notaurl",
              "limit": 1
            }
          ]
        }
        """
    )
    module = load_plan_script()

    exit_code = module.main(["--sources", str(sources_path)], env_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Invalid Firecrawl source config" in captured.err


def test_plan_firecrawl_script_does_not_import_psycopg_or_write_db(tmp_path):
    sources_path = tmp_path / "sources.json"
    write_sources_config(sources_path)
    module = load_plan_script()

    assert "psycopg" not in module.__dict__
