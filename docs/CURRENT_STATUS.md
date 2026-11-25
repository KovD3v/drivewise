# DriveWise current status

_Last updated: 2026-11-25_

> Full PR history, 5-agent code review & security audit consolidated table, 3-model Architectural Council (A–F) verdict, and operational roadmap:
> [`snapshots/2026-11-24_PR_PROCESS_REVIEW_SECURITY_ROADMAP.md`](snapshots/2026-11-24_PR_PROCESS_REVIEW_SECURITY_ROADMAP.md)
>
> Vehicle identity and fact design (ADR-020): [`catalog-identity-and-facts-design.md`](catalog-identity-and-facts-design.md)
>
> First real cars curation playbook (ADR-019): [`first-cars-curation.md`](first-cars-curation.md)

## Overall phase

**Unified API-first build landed on `main` (PR #22) and hardened via Architectural Council decisions A–F on `docs/pr-review-security-roadmap`; next gates are production ops verification, the vehicle identity design (ADR-020), and real Catalog v2 publication for the first cars (ADR-019).**

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
- **Council F (Curation Playbook):** documented in [`first-cars-curation.md`](first-cars-curation.md). ADR-019 removed its fixed count of twelve cars.

## Remaining pre-go-live gates (ADR-017)

1. **Production DB & Vercel Ops:** apply migrations `0010`–`0016` on production Neon, verify Preview `DATABASE_URL` does not target production, configure Vercel WAF rate limiting on `POST /api/guided-decisions*` and `/api/advisor/*`, and schedule `apps/api/scripts/purge_expired_sessions.py --days 30 --execute` for GDPR retention.
2. **Vehicle identity and facts (ADR-020):** review [`catalog-identity-and-facts-design.md`](catalog-identity-and-facts-design.md) and deliver its steps 1 to 5 before any real car is published. A generation cannot be filled after publication.
3. **First real Catalog v2 bundle (ADR-019):** follow [`first-cars-curation.md`](first-cars-curation.md) — sign the source reviews (`docs/source-reviews/`), choose the models, then curate and publish them with `list_price_eur`, `cargo_volume_liters`, and `body_style`. Align with Andrea on the `width_with_mirrors_mm` vs `width_mirrors_folded_mm` interval rule.
4. **Post-go-live follow-ups:** upgrade `uv.lock` (`starlette`, `anyio`, `certifi`) and `bun.lock` so CI `dependency-audit` can become blocking; separate read-only vs write token on shared decision URLs (Stage 1, `F-27`); run private-buyer beta validation (`docs/product-beta.md`).
