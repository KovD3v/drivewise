# Manufacturer collection agent

An on-demand OpenRouter agent uses Firecrawl to discover and read trusted sites,
with optional Tinyfish navigation for menus and filters. It extracts the requested
vehicle specifications, then starts a separate investigation pass. It produces a
catalog v2 bundle and a gap report for explicit review and publication. Nothing
runs on API startup, in CI, or on a schedule.

## Start later, when credentials are configured

From the repository root, first inspect the plan; this command needs no keys or
database and makes no HTTP requests:

```sh
uv run --frozen --project apps/api --extra dev python apps/api/scripts/scrape_catalog.py \
  --config data/scraping.example.json
```

Copy `.env.example` to the ignored `.env` and set `OPENROUTER_API_KEY`,
`OPENROUTER_MODEL` (an explicit model ID supporting tool calling) and
`FIRECRAWL_API_KEY`. Existing process environment variables take precedence.
`--model` overrides the model setting; `--env-file` selects another local env file.
Never put credentials in the job configuration, source URLs or Git.

```sh
uv run --frozen --project apps/api --extra dev python apps/api/scripts/scrape_catalog.py \
  --config data/scraping.example.json \
  --run-dir data/private/catalog/yaris-pilot --run
```

Repeat that command to resume the same job. Use `--status` instead of `--run` to
read progress without keys or network access. Exit 2 means a budget/context limit
or another process paused the run; exit 1 means an error. Complete jobs exit 0,
including an explicit `no_evidence` outcome with a gap report and no bundle.

### Optional Tinyfish navigation

Set `TINYFISH_API_KEY` in the ignored `.env` later and add `--tinyfish` to enable
the `browse` tool in both passes. An API key alone does not enable the tool.
OpenRouter can delegate document discovery through menus, search and filters to
Tinyfish. Returned URLs are filtered to the configured trusted hosts; OpenRouter
then uses Firecrawl's `scrape` tool to capture evidence at those URLs. Firecrawl
remains required. Tinyfish's generated JSON is a navigation receipt, never a
source snapshot or proof of a vehicle fact. Content requiring browser state that
Firecrawl cannot reproduce remains an evidence gap.

```sh
uv run --frozen --project apps/api --extra dev python apps/api/scripts/scrape_catalog.py \
  --config data/scraping.example.json --tinyfish \
  --run-dir data/private/catalog/yaris-tinyfish-pilot --run
```

Omit `--run` and `--run-dir` to preview this configuration without credentials or
network access. Repeat the same flags to resume; changing whether Tinyfish is
enabled requires a new run directory.

## What the operator controls

`data/scraping.example.json` is an editable job, not a fixed five-model dataset.
Each run targets one make/model family and national market, with a sales-period
cutoff, instructions, requested metrics, trusted source records, exact hosts and
starting URLs. Older generations still sold after the cutoff remain in scope.
Change these inputs and use a new run directory to collect another family or
period. Keep jobs small enough to inspect before expanding collection.

The metrics reuse the [catalog v2 contract](catalog-v2.md): powertrain and variant
identity; dimensions, seats and luggage for suitability; consumption/range for
running-cost inputs; and precise power, battery and charging facts. Missing data
remain visible. Manufacturer specifications do not establish used-car asking
prices, actual condition, reliability, maintenance costs or fleet weights; this
agent does not invent those or modify recommendation logic.

The model cannot add trusted hosts, change source permissions, increase limits,
write arbitrary files, call arbitrary APIs, stage or publish records. Seeded
source records are copied from configuration into the bundle. The example uses
`manual_validation_only`; apply [source review](source-review.md) before changing
eligibility for rankings. Same-publisher documents and mirrors are not independent
corroboration.

## Evidence and decisions

- Pass 1 uses `discover`, `scrape` and paginated `read_evidence`, then submits
  identities, observations and gaps. Proposed quotes must occur verbatim in their
  captured document, and raw values/units must occur in those quotes. Markdown
  line locators are derived from the capture rather than trusted to the model.
  When enabled, `browse` adds Tinyfish document discovery before scraping.
- Canonical units, common numerical conversions, ascending ranges, family/market,
  dates and all v2 references are checked in code. Ambiguous units such as `hp`
  and unsupported number formats are rejected for investigation, not guessed.
- Pass 2 receives the extraction in a fresh conversation. It can read more sources
  and add observations, but cannot rewrite the first pass or change identities.
  A `verified` proposal requires re-reading the text containing every cited quote
  in this pass. Conflicts and unknowns remain explicit decisions or gaps.
- Structural checks and a second LLM pass do not prove factual truth. In particular,
  correct table-column interpretation and identity applicability still need review.
  A verified proposal remains subject to the existing source/publication gates.

Each successful scrape archives the full Firecrawl JSON response, including
markdown and raw HTML when supplied, with its SHA-256 and retrieval time. The
snapshot hash identifies **that provider capture**, not the original PDF bytes.
PDF extraction can lose headers or layout; the agent must abstain when the captured
representation cannot establish a fact. Publication dates stay unknown rather than
being inferred from filenames or retrieval time. Per-run snapshot/decision IDs
keep repeated acquisitions distinct, while retries reuse saved captures.

Files in the ignored run directory:

| File | Purpose |
| --- | --- |
| `state.json` | Scope/model fingerprint, phase, conversation, usage, captures and failures; atomic checkpoints. |
| `artifacts/<sha256>.json` | Immutable captured evidence, hash-checked when read/resumed. |
| `model-responses/` | Provider receipts for debugging; local only. |
| `navigation/<sha256>.json` | Tinyfish responses for debugging; excluded from factual evidence. |
| `bundle.json` | Completed, validated v2 identities, observations and agent decisions. |
| `report.json` | Missing/unverified metrics, gaps, failures and usage; no fleet-coverage claim. |

## Bounds and failure handling

Model calls, browser calls, output tokens, context bytes and document characters
are bounded. Firecrawl requests and Tinyfish runs share `max_browser_calls`.
Attempts are charged against local call limits **before** sending;
there is no hidden request retry. Reported OpenRouter costs are summed and calls
with unknown cost are counted separately. These are invocation/token limits, not
a guaranteed currency cap: model input pricing, Firecrawl PDF/page charges and
Tinyfish agent-step charges vary. Tinyfish charges are not included in the
`reported_model_cost_usd` total, which covers only OpenRouter.
Use provider-account spending limits for a hard financial cap.

Tinyfish uses the synchronous Agent API with a 60-second server-side duration
limit and the shared 75-second HTTP timeout. It does not request beta step limits,
account-gated HTML captures, vault access, saved profiles or enhanced proxies.
Longer navigation needs a future async adapter; a local timeout cannot cancel a
synchronous provider run. The configured server duration still applies.

Successful discovery and captures are cached within the run, as are failed pages
and Tinyfish runs. Changing a navigation goal creates a new budgeted attempt.
Blocked/error pages are reported; no enhanced proxy escalation is enabled.
Returned links and redirect metadata are checked against the trusted hosts before
being admitted as evidence. Tinyfish receives a read-only, trusted-host navigation
instruction, but providers control their remote browsers and redirect requests;
this application does not provide a network-level egress guarantee for either
service. API credentials are sent only to fixed provider endpoints and
API redirects are disabled.

Only one process may own a run directory. An interrupted provider request can have
been billed without a response being saved; resume may request it again, consuming
another attempt. Completed checkpoints do not repeat completed work. Limits may
be increased when resuming, but scope, source records, model and Tinyfish enablement
changes require a new directory. There is no distributed queue or automatic cross-run
identity merge.

## Validate and publish separately

```sh
uv run --frozen --project apps/api python apps/api/scripts/import_catalog_v2.py \
  --check data/private/catalog/yaris-pilot/bundle.json \
  --artifact-root data/private/catalog/yaris-pilot
```

After reviewing the bundle, use the existing `--stage` and `--publish` commands
described in [catalog v2](catalog-v2.md). The scraper itself never connects to a
database. The 80% target needs fleet-weighted coverage data and is not inferred
from records, model names or document counts.

## Verification and provider references

`uv run --frozen --project apps/api --extra dev pytest apps/api/tests/test_scraping.py -q`
exercises the real CLI/clients with simulated HTTP responses, two-pass completion,
resume, budgets, source restrictions, conversions, evidence integrity, conflict
retention and v2 artifact validation. No live calls or real data collection were
requested for this PR; credentials and the live model will be configured later.

API contracts checked on 17 September 2026:
[OpenRouter tool calling](https://openrouter.ai/docs/guides/features/tool-calling),
[Firecrawl scrape](https://docs.firecrawl.dev/api-reference/endpoint/scrape),
[Firecrawl map](https://docs.firecrawl.dev/api-reference/endpoint/map),
[Tinyfish Agent API](https://docs.tinyfish.ai/agent-api/reference).
