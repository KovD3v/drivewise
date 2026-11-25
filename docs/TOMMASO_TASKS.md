# Tommaso: attività backend MVP

> **Documento storico, superato (aggiornato il 25/11/2026).** Descrive il piano
> di agosto 2026, prima della build unificata API-first (PR #22). Non usarlo
> come lista di lavoro: gli endpoint `/api/v1/health`, `/api/v1/version` e
> `POST /api/v1/decisions` non esistono. Le API reali sono `GET /health`,
> `GET /version` e le rotte `/guided-decisions`, servite sotto `/api` in
> produzione (vedi [`architecture.md`](./architecture.md)). Lo stato e i
> prossimi passi sono in:
>
> - [`CURRENT_STATUS.md`](./CURRENT_STATUS.md): stato attuale e gate prima del go-live;
> - [`f1-twelve-cars-curation.md`](./f1-twelve-cars-curation.md): curatela delle prime 12 auto (ADR-017);
> - [`snapshots/2026-11-24_PR_PROCESS_REVIEW_SECURITY_ROADMAP.md`](./snapshots/2026-11-24_PR_PROCESS_REVIEW_SECURITY_ROADMAP.md): finding aperti e roadmap.

Il piano operativo completo è mantenuto in:

**[`docs/TOMMASO_BACKLOG.md`](./TOMMASO_BACKLOG.md)**

## Priorità immediata

Costruire il primo vertical slice reale:

`Lovable /app/start → FastAPI → Advisor v3 → ranking JSON → Decision Report`

## Prima consegna attesa
1. verificare l'architettura backend già presente;
2. verificare l'integrazione esistente di Advisor v3 senza duplicare le formule;
3. esporre `GET /api/v1/health` e `GET /api/v1/version`;
4. esporre `POST /api/v1/decisions`;
5. restituire Decision Score, Decision Confidence, Pillars, trade-off ed Explainability;
6. configurare CORS per Lovable;
7. documentare avvio locale e OpenAPI;
8. mantenere verdi i test del Decision Engine.

Per dettaglio, acceptance criteria, API successive, dataset, persistenza, test e attività da NON anticipare, usare esclusivamente `TOMMASO_BACKLOG.md`.
