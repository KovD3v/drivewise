"""F-30: Firecrawl source URLs carry no credentials and plans never print secrets."""

import importlib.util
import json
from pathlib import Path

import pytest

from app.ingestion.firecrawl import (
    FirecrawlConfigError,
    load_sources_config,
    plan_firecrawl_ingestion,
)

ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT / "apps/api/scripts/plan_firecrawl.py"


def load_plan_script():
    spec = importlib.util.spec_from_file_location(
        "drivewise_plan_firecrawl_hardening", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_config(path: Path, url: str) -> Path:
    path.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "name": "Synthetic listing pages",
                        "type": "firecrawl",
                        "url": url,
                        "limit": 5,
                        "document_type": "listing_snapshot",
                        "crawl_depth": 1,
                    }
                ]
            }
        )
    )
    return path


@pytest.mark.parametrize(
    "url",
    [
        "https://fake-user:fake-pass@example.com/cars",
        "https://fake-user@example.com/cars",
        "http://:fake-pass@example.com/cars",
    ],
)
def test_source_urls_with_credentials_are_rejected(tmp_path, url):
    with pytest.raises(FirecrawlConfigError, match="credentials"):
        plan_firecrawl_ingestion(
            load_sources_config(write_config(tmp_path / "sources.json", url))
        )


def test_plan_redacts_sensitive_query_values(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    url = (
        "https://example.com/cars?page=2&api_key=FAKE-KEY-VALUE"
        "&access_token=FAKE-TOKEN-VALUE&Signature=FAKE-SIG"
    )
    path = write_config(tmp_path / "sources.json", url)
    module = load_plan_script()
    assert module.main(["--sources", str(path)], env_path=tmp_path / ".env") == 0
    out = capsys.readouterr().out
    assert "FAKE-" not in out
    assert (
        "URL: https://example.com/cars?page=2&api_key=REDACTED"
        "&access_token=REDACTED&Signature=REDACTED"
    ) in out


def test_redaction_keeps_plain_urls_unchanged():
    module = load_plan_script()
    assert module.redact_url("https://example.com/cars") == "https://example.com/cars"
    assert (
        module.redact_url("https://example.com/cars?page=2&sort=price")
        == "https://example.com/cars?page=2&sort=price"
    )
