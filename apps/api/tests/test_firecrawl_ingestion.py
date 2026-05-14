import socket

import pytest

from app.ingestion.firecrawl import (
    FirecrawlConfigError,
    load_sources_config,
    plan_firecrawl_ingestion,
)


VALID_CONFIG = {
    "sources": [
        {
            "name": "Example listing pages",
            "type": "firecrawl",
            "url": "https://example.com/cars",
            "limit": 5,
            "document_type": "listing_snapshot",
            "crawl_depth": 1,
        },
        {
            "name": "Local fixture documents",
            "type": "local_fixture",
            "path": "data/fixtures/ingestion",
            "limit": 3,
        },
    ]
}


def test_plan_firecrawl_ingestion_returns_dry_run_plan_with_valid_config():
    plan = plan_firecrawl_ingestion(VALID_CONFIG, firecrawl_api_key="fc-test-key")

    assert plan.api_key_present is True
    assert plan.http_requests_enabled is False
    assert plan.database_writes_enabled is False
    assert len(plan.firecrawl_sources) == 1
    assert plan.firecrawl_sources[0].name == "Example listing pages"
    assert plan.firecrawl_sources[0].url == "https://example.com/cars"
    assert plan.firecrawl_sources[0].limit == 5
    assert plan.firecrawl_sources[0].document_type == "listing_snapshot"
    assert plan.local_sources[0].path == "data/fixtures/ingestion"


@pytest.mark.parametrize(
    "source, expected_message",
    [
        ({"type": "firecrawl", "url": "https://example.com", "limit": 1}, "name"),
        ({"name": "Bad type", "type": "rss", "limit": 1}, "type"),
        ({"name": "Bad URL", "type": "firecrawl", "url": "notaurl"}, "url"),
        (
            {
                "name": "Bad limit",
                "type": "firecrawl",
                "url": "https://example.com",
                "limit": 0,
            },
            "limit",
        ),
    ],
)
def test_plan_firecrawl_ingestion_rejects_invalid_config(
    source,
    expected_message,
):
    with pytest.raises(FirecrawlConfigError, match=expected_message):
        plan_firecrawl_ingestion({"sources": [source]})


def test_plan_firecrawl_ingestion_allows_missing_api_key():
    plan = plan_firecrawl_ingestion(VALID_CONFIG, firecrawl_api_key=None)

    assert plan.api_key_present is False
    assert any("FIRECRAWL_API_KEY is not set" in warning for warning in plan.warnings)


def test_plan_firecrawl_ingestion_does_not_open_network_connections(monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("network call attempted")

    monkeypatch.setattr(socket, "create_connection", fail_network)

    plan = plan_firecrawl_ingestion(VALID_CONFIG)

    assert plan.http_requests_enabled is False


def test_load_sources_config_reads_json(tmp_path):
    config_path = tmp_path / "sources.json"
    config_path.write_text(
        """
        {
          "sources": [
            {
              "name": "Example listing pages",
              "type": "firecrawl",
              "url": "https://example.com/cars",
              "limit": 5
            }
          ]
        }
        """
    )

    config = load_sources_config(config_path)

    assert config["sources"][0]["name"] == "Example listing pages"
