# DriveWise current status

_Last updated: 2026-11-25_

> Full PR history, 5-agent code review & security audit consolidated table, 3-model Architectural Council (A–F) verdict, and operational roadmap:
> [`snapshots/2026-11-24_PR_PROCESS_REVIEW_SECURITY_ROADMAP.md`](snapshots/2026-11-24_PR_PROCESS_REVIEW_SECURITY_ROADMAP.md)
>
> 12-car curation playbook (ADR-017): [`f1-twelve-cars-curation.md`](f1-twelve-cars-curation.md)

## Overall phase

**Unified API-first build landed on `main` (PR #22) and hardened via Architectural Council decisions A–F on `docs/pr-review-security-roadmap`; next gate is production ops verification and real Catalog v2 publication for the first 12 cars (ADR-017).**

### Completed in the November 2026 wave (PRs #5, #11–#22)
- **Unified Advisor runtime (`advisor-v3.0`, PR #5):** deterministic scoring (65% Structural Fit + 35% Preference Fit), Guided Decision persistence (`0005`–`0007`), and retirement of standalone `decision_engine/`.
- **Catalog v2 evidence & publication (PR #12, #13, #19, #22):** append-only snapshots, observations, and reviewed decisions (`0008`–`0014`), `GET /vehicles/{id}/facts`, two-wheel metrics (`0010`), list-price ranking fallback (ADR-013, `0011`–`0012`), plug-in hybrid fuel alignment (`0013`), and body-style provenance (`0014`).
- **Data acquisition pipelines (PR #14, #22):** on-demand OpenRouter manufacturer collector (`scrape_catalog.py`) and zero-cost open-data builder (`build_open_data_catalog.py`: EEA + RDW + MotoSpecDB, fail-closed as `manual_validation_only`).
- **Deployment & redesigned API-only web app (PR #11, #15–#18, #21, #22):** patched TanStack Start XSS (`CVE-2026-102989`), Vercel Services unified routing (`vercel.json`), OpenAPI-generated web types in CI, `GET /version`, removal of local mock vehicle datasets/scoring and legacy MVP routes.

### Applied from the Multi-Model Review, Security Audit & Council A–F (`docs/pr-review-security-roadmap`)
- **Council A (Catalog Views & v1 Freeze):** `_upsert_sources` in v1 switched to `DO NOTHING` (prevents restoring revoked `ranking_permission`), `import_catalog.py --write` blocked outside `local`/`test`, and migration `0015_catalog_v2_read_view_pivot.sql` rewrote `catalog_scalar_facts` + `catalog_read_specs` with a single `LATERAL` pivot projecting v2 dimensions, power, and provenance into Advisor.
- **Council B (Runtime Hardening):** `ConnectionDep = Depends(get_connection, scope="function")` ensures DB commit completes before HTTP 2xx; `DatabaseConnectionPool` rewritten with `threading.Condition`, `acquire_timeout=5s`, `SET LOCAL` timeouts compatible with Neon `-pooler`, and `conn.broken` handling; production web builds default to `/api` (never `127.0.0.1:8000`) with 8s SSR timeout; HTTP security headers added to `vercel.json` (`web` + `api`); CORS fails closed outside `local`.
- **Council C (URL-Driven Guided Decision & Live Revocation):** `GET /guided-decisions/{id}` recomputes live against current catalog/source permissions; `/app/report?s=` loads directly from the API without requiring `localStorage`; both report CTA buttons re-enabled; `?spec=` propagated across Vehicle, Compare, and Ask; 40-turn cap enforced (`409 max_turns_reached`).
- **Council D (Italian Advisor Copy):** user-facing Advisor messages centralized in `apps/api/app/services/advisor/messages_it.py` with identical scores/rankings.
- **Council E (Public API Surface Gating):** `ENABLE_INTERNAL_ROUTES` (default `False` outside `local`/`test`) disables `/docs`, `/redoc`, `/openapi.json`, `/listings*`, `/documents*`, `/search/documents` (`vector_fake`), `POST /vehicles/resolve`, and `POST /advisor/recommendations`.
- **Security & Correctness Fixes:** fixed High ReDoS in `interpreter.py` (4.6s → <5 ms), `allow_inf_nan=False` + 422 sanitization handler in `main.py`, `ILIKE` wildcard escaping + query `max_length`, migration runner advisory lock, `vehicle_exists()` fast check, garage hard-constraint/negative-margin fixes, `safeHttpsUrl()`, and CI `permissions: contents: read` + rule-scoped `.gitleaks.toml`.
- **Council F (12-Car Curation Playbook):** documented in [`f1-twelve-cars-curation.md`](f1-twelve-cars-curation.md).

## Remaining pre-go-live gates (ADR-017)

1. **Production DB & Vercel Ops:** apply migrations `0010`–`0015` on production Neon, verify Preview `DATABASE_URL` does not target production, configure Vercel WAF rate limiting on `POST /api/guided-decisions*` and `/api/advisor/*`, and self-host Google Fonts (`styles.css:1`, GDPR).
2. **Real 12-Car Catalog v2 Bundle (F1):** complete source reviews (`docs/source-reviews/`), curate and publish the 12 target cars with `list_price_eur`, `cargo_volume_liters`, and `body_style`, and align with Andrea on the `width_with_mirrors_mm` vs `width_mirrors_folded_mm` interval rule.
3. **Key Open Technical Follow-ups** (full list in the consolidated audit table):
   - Before live open-data imports: fix RDW cross-manufacturer make filter (`open_data.py`), two-wheeler `slug` path validation, and `catalog_status.py` `offer=None` crash.
   - Before live `scrape_catalog.py` runs: tighten excerpt value/unit co-occurrence and require human sign-off for `actor_kind="agent"` facts.
   - Before authorized used offers: preserve separate `new`/`used` groups in `apps/web/src/lib/decision-engine.ts` and unify offer vs list-price snapshot consistency (`READ COMMITTED` race).
   - Stage 1 / Phase 2: 30-day GDPR retention for anonymous decisions, read-only vs write token separation on shared URLs, CI `gitleaks`/`osv-scanner` + action SHA pinning, dead-code/docs cleanup, and private-buyer beta validation (`docs/product-beta.md`).
