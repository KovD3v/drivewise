"""Offline provider simulations exercise the actual runner and v2 output."""

import copy
import importlib.util
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from pydantic import ValidationError

from app.ingestion.catalog_v2 import CatalogV2
from app.ingestion.catalog_v2_writer import verify_artifacts
from app.ingestion.scraping import Collector, RunPaused, digest, proposal_observation
from app.ingestion.scraping_contract import (
    Browse,
    Extraction,
    Investigation,
    ObservationProposal,
    ReadEvidence,
    ScrapingConfig,
)
from app.ingestion import scraping_providers as providers
from app.ingestion import scraping


ROOT = Path(__file__).resolve().parents[3]
URL = "https://newsroom.toyota.it/synthetic-test-document"
CAPTURE = {
    "success": True,
    "data": {
        "markdown": "SYNTHETIC TEST ONLY\nToyota Yaris IT MY20 Active HEV e-CVT\nEngine: 68 kW\nSystem: 85 kW\nWLTP combined: 4.0 l/100km\n",
        "rawHtml": "<p>Synthetic test; no real vehicle claim.</p>",
        "metadata": {"sourceURL": URL, "url": URL, "statusCode": 200},
        "links": [
            "https://newsroom.toyota.it/next",
            "https://untrusted.example/ignore",
        ],
    },
}
RUN_ID = str(uuid5(NAMESPACE_URL, "synthetic-run"))
SNAPSHOT_ID = str(uuid5(NAMESPACE_URL, RUN_ID + URL + digest(CAPTURE)))


@pytest.fixture(autouse=True)
def fixed_run_id(monkeypatch):
    monkeypatch.setattr(scraping, "uuid4", lambda: UUID(RUN_ID))


def config():
    data = json.loads((ROOT / "data/scraping.example.json").read_text())
    data["sources"][0]["seed_urls"] = [URL]
    data["target"]["metrics"] = [
        "engine_power_kw",
        "system_power_kw",
        "liquid_consumption_l_100km",
    ]
    return ScrapingConfig.model_validate(data)


def extraction():
    return {
        "vehicles": [
            {
                "canonical_key": "toyota-yaris-xp210-2020-it",
                "model_family_key": "toyota-yaris",
                "make": "Toyota",
                "model": "Yaris",
                "vehicle_type": "car",
                "generation_key": "xp210",
                "phase_key": "initial",
                "body_style": "hatchback",
                "model_year": 2020,
                "market": "IT",
                "evidence_snapshot_ids": [SNAPSHOT_ID],
            }
        ],
        "variants": [
            {
                "variant_key": "yaris-xp210-active-hev-2020-it",
                "vehicle_key": "toyota-yaris-xp210-2020-it",
                "trim": "Active",
                "powertrain_type": "HEV",
                "fuel": "petrol",
                "transmission": "e-cvt",
                "drivetrain": "FWD",
                "valid_from": "2020-07-10",
                "valid_to": "2021-01-01",
                "evidence_snapshot_ids": [SNAPSHOT_ID],
            }
        ],
        "observations": [
            {
                "snapshot_id": SNAPSHOT_ID,
                "variant_key": "yaris-xp210-active-hev-2020-it",
                "metric": metric,
                "raw_value": str(value),
                "raw_unit": "kW",
                "value_min": float(value),
                "value_max": float(value),
                "unit": "kW",
                "context": {
                    "market": "IT",
                    "valid_from": "2020-07-10",
                    "valid_to": "2021-01-01",
                },
                "evidence_excerpt": f"{label}: {value} kW",
                "evidence_locator": f"markdown line {line}",
            }
            for metric, label, value, line in [
                ("engine_power_kw", "Engine", 68, 3),
                ("system_power_kw", "System", 85, 4),
            ]
        ],
        "gaps": ["Synthetic test deliberately omits consumption extraction."],
    }


def investigation():
    observations = [
        proposal_observation(ObservationProposal.model_validate(o))
        for o in extraction()["observations"]
    ]
    return {
        "decisions": [
            {
                "variant_key": o.variant_key,
                "metric": o.metric,
                "context": o.context.model_dump(mode="json"),
                "status": "verified",
                "selected_observation_id": str(o.id),
                "evidence_ids": [str(o.id)],
                "reason": "Synthetic test: re-read the explicit component label and identity.",
            }
            for o in observations
        ]
    }


def response(name, arguments, call_id="call-1"):
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(arguments),
                            },
                        }
                    ],
                }
            }
        ],
        "usage": {"cost": 0.01},
    }


class Browser:
    def __init__(self):
        self.calls = 0

    def scrape(self, url):
        self.calls += 1
        assert url == URL
        return copy.deepcopy(CAPTURE)

    def discover(self, url, search):
        self.calls += 1
        return {
            "success": True,
            "links": [{"url": URL}, {"url": "https://untrusted.example/doc"}],
        }


class Router:
    model = "synthetic/tool-model"

    def __init__(self, replies):
        self.replies = iter(replies)
        self.messages = []

    def complete(self, messages, tools, max_tokens):
        self.messages.append(copy.deepcopy(messages))
        reply = next(self.replies)
        if isinstance(reply, Exception):
            raise reply
        return reply


def replies():
    return [
        response("discover", {"url": URL, "search": "Yaris MY20"}),
        response("scrape", {"url": URL}),
        response("submit_extraction", extraction()),
        response("read_evidence", {"snapshot_id": SNAPSHOT_ID}),
        response("submit_investigation", investigation()),
    ]


def test_complete_tool_loop_bundle_hashes_and_no_repeat_work(tmp_path):
    router, browser = Router(replies()), Browser()
    report = Collector(config(), tmp_path, router, browser).run()
    assert report["phase"] == "complete" and not report["published"]
    assert report["fleet_coverage"] is None
    assert report["browser_calls"] == browser.calls == 2
    assert report["model_calls"] == 5
    assert report["missing_or_unverified"] == {
        "yaris-xp210-active-hev-2020-it": ["liquid_consumption_l_100km"]
    }
    bundle = CatalogV2.model_validate_json((tmp_path / "bundle.json").read_text())
    verify_artifacts(bundle, tmp_path)
    assert bundle.sources[0].ranking_permission == "manual_validation_only"
    assert [(o.metric, o.value_min) for o in bundle.observations] == [
        ("engine_power_kw", 68),
        ("system_power_kw", 85),
    ]
    assert all(d.actor_kind == "agent" for d in bundle.decisions)
    assert (
        len(router.messages[3]) == 2
    )  # Fresh investigation context, not first-pass conversation.
    assert "PASS 2" in router.messages[3][0]["content"]
    assert Collector(config(), tmp_path, Router([]), Browser()).run() == report


def test_budget_pause_resume_preserves_pending_calls_and_captures(tmp_path):
    settings = config()
    settings.limits.max_model_calls = 2
    browser = Browser()
    with pytest.raises(RunPaused, match="model_calls"):
        Collector(settings, tmp_path, Router(replies()[:2]), browser).run()
    assert browser.calls == 2
    settings.limits.max_model_calls = 6
    report = Collector(settings, tmp_path, Router(replies()[2:]), browser).run()
    assert report["model_calls"] == 5
    assert browser.calls == 2


def test_failed_model_attempt_consumes_budget_and_resumes(tmp_path):
    with pytest.raises(providers.ProviderError):
        Collector(
            config(), tmp_path, Router([providers.ProviderError("Timeout")]), Browser()
        ).run()
    report = Collector(config(), tmp_path, Router(replies()), Browser()).run()
    assert report["model_calls"] == 6
    assert report["model_cost_unknown_calls"] == 1
    assert report["failures"] == [{"operation": "model", "error": "Timeout"}]


@pytest.mark.parametrize(
    "url",
    [
        "https://newsroom.toyota.it.evil.example/x",
        "http://newsroom.toyota.it/",
        "https://user:secret@newsroom.toyota.it/",
        "https://127.0.0.1/",
        "https://newsroom.toyota.it:444/",
        "https://untrusted.example/",
    ],
)
def test_untrusted_browse_is_rejected_before_network(tmp_path, url):
    browser = Browser()
    runner = Collector(config(), tmp_path, Router([]), browser)
    runner.load()
    result = runner.execute({"name": "scrape", "arguments": json.dumps({"url": url})})
    assert "error" in result and browser.calls == 0
    assert runner.state["browser_calls"] == 0


def prepared(tmp_path):
    runner = Collector(config(), tmp_path, Router([]), Browser())
    runner.load()
    runner.scrape(Browse(url=URL))
    return runner


@pytest.mark.parametrize(
    "mutation",
    ["quote", "raw", "source", "unit", "market", "family", "dates", "permission"],
)
def test_invalid_extraction_cannot_enter_bundle(tmp_path, mutation):
    runner = prepared(tmp_path)
    data = extraction()
    if mutation == "quote":
        data["observations"][0]["evidence_excerpt"] = "Fabricated evidence"
    if mutation == "raw":
        data["observations"][0]["raw_value"] = "999"
    if mutation == "source":
        data["observations"][0]["snapshot_id"] = str(uuid5(NAMESPACE_URL, "invented"))
    if mutation == "unit":
        data["observations"][0]["unit"] = "CV"
    if mutation == "market":
        data["vehicles"][0]["market"] = "FR"
    if mutation == "family":
        data["vehicles"][0]["generation_key"] = "xp130"
        data["variants"][0]["vehicle_key"] = "unknown-generation"
    if mutation == "dates":
        data["observations"][0]["context"]["valid_from"] = "2022-01-01"
        data["observations"][0]["context"]["valid_to"] = "2023-01-01"
    if mutation == "permission":
        data["sources"] = [{"ranking_permission": "permitted"}]
    result = runner.execute(
        {"name": "submit_extraction", "arguments": json.dumps(data)}
    )
    assert "error" in result and runner.state["phase"] == "extract"
    assert "bundle" not in runner.state


def test_review_must_read_cited_excerpt_and_cannot_cross_identity(tmp_path):
    runner = prepared(tmp_path)
    runner.extract(Extraction.model_validate(extraction()))
    with pytest.raises(ValueError, match="re-reading"):
        runner.investigate(Investigation.model_validate(investigation()))
    runner.read(ReadEvidence(snapshot_id=SNAPSHOT_ID, start_line=5))
    with pytest.raises(ValueError, match="re-reading"):
        runner.investigate(Investigation.model_validate(investigation()))
    runner.read(ReadEvidence(snapshot_id=SNAPSHOT_ID))
    data = investigation()
    data["decisions"][0]["metric"] = "system_power_kw"
    with pytest.raises(ValidationError, match="different identity/metric/context"):
        runner.investigate(Investigation.model_validate(data))


def test_conflicting_evidence_is_retained_without_selected_value(tmp_path):
    runner = prepared(tmp_path)
    runner.extract(Extraction.model_validate(extraction()))
    # A second interpretation of the same source is NOT independent corroboration.
    additional = copy.deepcopy(extraction()["observations"][1])
    additional["metric"] = "engine_power_kw"
    first_id = runner.state["bundle"]["observations"][0]["id"]
    other = proposal_observation(ObservationProposal.model_validate(additional))
    data = {
        "additional_observations": [additional],
        "decisions": [
            {
                "variant_key": other.variant_key,
                "metric": other.metric,
                "context": other.context.model_dump(mode="json"),
                "status": "conflicted",
                "evidence_ids": [first_id, str(other.id)],
                "reason": "Synthetic competing interpretations left unresolved.",
            }
        ],
    }
    runner.investigate(Investigation.model_validate(data))
    decision = runner.state["bundle"]["decisions"][0]
    assert (
        decision["status"] == "conflicted"
        and decision["selected_observation_id"] is None
    )
    assert len(runner.state["bundle"]["observations"]) == 3


def test_hash_tampering_and_changed_scope_refuse_resume(tmp_path):
    runner = prepared(tmp_path)
    snapshot = runner.snapshots()[0]
    (tmp_path / snapshot["artifact_path"]).write_text("changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        Collector(config(), tmp_path, Router([]), Browser()).run()
    changed = config()
    changed.target.make = "Fiat"
    with pytest.raises(ValueError, match="scope/model changed"):
        Collector(changed, tmp_path, Router([]), Browser()).run()


def test_new_run_same_bytes_has_new_snapshot_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(scraping, "uuid4", uuid4)
    first, second = prepared(tmp_path / "one"), prepared(tmp_path / "two")
    assert (
        first.snapshots()[0]["content_sha256"]
        == second.snapshots()[0]["content_sha256"]
    )
    assert first.snapshots()[0]["id"] != second.snapshots()[0]["id"]


def test_redirected_evidence_is_not_accepted(tmp_path):
    class Redirected(Browser):
        def scrape(self, url):
            result = super().scrape(url)
            result["data"]["metadata"]["url"] = "https://untrusted.example/doc"
            return result

    runner = Collector(config(), tmp_path, Router([]), Redirected())
    runner.load()
    assert "error" in runner.scrape(Browse(url=URL))
    assert runner.snapshots() == []


def test_provider_capture_warning_is_visible_in_both_passes(tmp_path):
    class Warned(Browser):
        def scrape(self, url):
            result = super().scrape(url)
            result["data"]["warning"] = "Synthetic incomplete PDF warning"
            return result

    runner = Collector(config(), tmp_path, Router([]), Warned())
    runner.load()
    result = runner.scrape(Browse(url=URL))
    assert result["warning"] == "Synthetic incomplete PDF warning"
    runner.state["phase"] = "investigate"
    assert (
        runner.read(ReadEvidence(snapshot_id=result["snapshot"]["id"]))["warning"]
        == result["warning"]
    )


def test_cli_full_flow_uses_real_clients_with_simulated_http(
    tmp_path, monkeypatch, capsys
):
    module = script()
    monkeypatch.setattr(os, "environ", dict(os.environ))
    responses = iter(replies())
    endpoints = []

    def fake_post(url, key, payload):
        endpoints.append(url)
        if url.endswith("chat/completions"):
            assert key == "synthetic-openrouter-key"
            return next(responses)
        assert key == "synthetic-firecrawl-key"
        if url.endswith("/map"):
            return {"success": True, "links": [{"url": URL}]}
        return copy.deepcopy(CAPTURE)

    monkeypatch.setattr(providers, "post_json", fake_post)
    for key in ("OPENROUTER_API_KEY", "OPENROUTER_MODEL", "FIRECRAWL_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    env = tmp_path / "synthetic.env"
    env.write_text(
        "OPENROUTER_API_KEY=synthetic-openrouter-key\nOPENROUTER_MODEL=synthetic/tool-model\nFIRECRAWL_API_KEY=synthetic-firecrawl-key\n"
    )
    job = tmp_path / "config.json"
    job.write_text(config().model_dump_json())
    run = tmp_path / "run"
    assert (
        module.main(
            [
                "--config",
                str(job),
                "--run",
                "--run-dir",
                str(run),
                "--env-file",
                str(env),
            ]
        )
        == 0
    )
    bundle = CatalogV2.model_validate_json((run / "bundle.json").read_text())
    verify_artifacts(bundle, run)
    assert len(endpoints) == 7
    assert "synthetic-openrouter-key" not in capsys.readouterr().out
    assert module.main(["--config", str(job), "--status", "--run-dir", str(run)]) == 0
    assert len(endpoints) == 7


def test_unit_citation_and_locator_are_not_trusted_to_model(tmp_path):
    runner = prepared(tmp_path)
    proposal = extraction()["observations"][0]
    proposal["evidence_locator"] = "Invented PDF page 900"
    result = runner.observations([ObservationProposal.model_validate(proposal)])
    assert result[0]["evidence_locator"] == "markdown line 3"
    proposal.update(raw_unit="CV", value_min=68 * 0.73549875, value_max=68 * 0.73549875)
    with pytest.raises(ValueError, match="raw unit"):
        runner.observations([ObservationProposal.model_validate(proposal)])


def test_page_failures_are_cached_and_do_not_break_resume(tmp_path):
    class Blocked(Browser):
        def scrape(self, url):
            self.calls += 1
            return {"success": True, "data": {"metadata": {"statusCode": 403}}}

    browser = Blocked()
    runner = Collector(config(), tmp_path, Router([]), browser)
    runner.load()
    assert "error" in runner.scrape(Browse(url=URL))
    runner.load()
    assert "error" in runner.scrape(Browse(url=URL))
    assert browser.calls == 1 and len(runner.state["failures"]) == 1


def test_empty_results_produce_gap_report_not_fake_bundle(tmp_path):
    report = Collector(
        config(),
        tmp_path,
        Router(
            [
                response(
                    "finish_without_evidence",
                    {"reason": "No supported Italian identity found."},
                )
            ]
        ),
        Browser(),
    ).run()
    assert report["phase"] == "no_evidence" and report["variants"] == 0
    assert not (tmp_path / "bundle.json").exists()


def test_provider_request_contracts(monkeypatch):
    calls = []
    monkeypatch.setattr(providers, "post_json", lambda *args: calls.append(args) or {})
    providers.OpenRouter("synthetic-key", "chosen/model").complete([], [], 1000)
    providers.Firecrawl("synthetic-key").scrape(URL)
    providers.Firecrawl("synthetic-key").discover(URL, "Yaris")
    assert calls[0][0] == "https://openrouter.ai/api/v1/chat/completions"
    assert calls[0][2]["model"] == "chosen/model" and calls[0][2]["max_tokens"] == 1000
    assert calls[1][2]["proxy"] == "basic" and calls[1][2]["parsers"] == ["pdf"]
    assert calls[2][2]["includeSubdomains"] is False


@pytest.mark.parametrize(
    "raw,raw_unit,metric,unit,low,high",
    [
        ("70", "CV", "engine_power_kw", "kW", 51.4849125, 51.4849125),
        ("20-25", "km/l", "liquid_consumption_l_100km", "l/100km", 4, 5),
        ("140", "Wh/km", "electric_consumption_kwh_100km", "kWh/100km", 14, 14),
        ("3,94", "m", "length_mm", "mm", 3940, 3940),
    ],
)
def test_normalization_is_checked_not_trusted_to_llm(
    raw, raw_unit, metric, unit, low, high
):
    data = extraction()["observations"][0]
    data.update(
        raw_value=raw,
        raw_unit=raw_unit,
        metric=metric,
        unit=unit,
        value_min=float(low),
        value_max=float(high),
    )
    proposal = ObservationProposal.model_validate(data)
    assert proposal.value_min == low and proposal.value_max == high
    data["value_min"] += 10
    with pytest.raises(ValidationError, match="deterministic conversion"):
        ObservationProposal.model_validate(data)


def test_inverted_raw_range_and_ambiguous_hp_rejected():
    data = extraction()["observations"][0]
    data["raw_value"] = "85-68"
    with pytest.raises(ValidationError, match="inverted"):
        ObservationProposal.model_validate(data)
    data["raw_value"], data["raw_unit"] = "68", "hp"
    with pytest.raises(ValidationError, match="unsupported unit"):
        ObservationProposal.model_validate(data)


def test_provider_errors_do_not_echo_credentials_or_retry(monkeypatch):
    class Opener:
        def open(self, request, timeout):
            raise HTTPError(request.full_url, 401, "synthetic-secret", {}, None)

    monkeypatch.setattr(providers, "build_opener", lambda *args: Opener())
    with pytest.raises(providers.ProviderError, match="HTTP 401") as error:
        providers.post_json(
            "https://openrouter.ai/api/v1/chat/completions", "synthetic-secret", {}
        )
    assert "synthetic-secret" not in str(error.value)
    assert providers.NoRedirect().redirect_request(None, None, 302, "", {}, URL) is None


def script():
    spec = importlib.util.spec_from_file_location(
        "scrape_catalog", ROOT / "apps/api/scripts/scrape_catalog.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_plan_and_missing_credentials_never_call_providers(
    tmp_path, monkeypatch, capsys
):
    module = script()
    monkeypatch.setattr(
        module.Collector, "run", lambda *args: pytest.fail("Unexpected collection")
    )
    for key in ("OPENROUTER_API_KEY", "OPENROUTER_MODEL", "FIRECRAWL_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    args = [
        "--config",
        str(ROOT / "data/scraping.example.json"),
        "--env-file",
        str(tmp_path / "absent.env"),
    ]
    assert module.main(args) == 0
    assert "Plan only" in capsys.readouterr().out
    assert module.main(args + ["--run", "--run-dir", str(tmp_path / "run")]) == 1
    assert "Configure OPENROUTER_API_KEY" in capsys.readouterr().err
    assert not (tmp_path / "run").exists()
