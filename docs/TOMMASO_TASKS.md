# Tommaso — Attività Backend MVP

Il piano operativo completo è mantenuto in:

**[`docs/TOMMASO_BACKLOG.md`](./TOMMASO_BACKLOG.md)**

## Priorità immediata

Costruire il primo vertical slice reale:

`Lovable /app/start → FastAPI → Decision Engine v1.0 → ranking JSON → Decision Report`

## Prima consegna attesa
1. verificare l'architettura backend già presente;
2. integrare `decision_engine/` senza riscrivere le formule;
3. esporre `GET /api/v1/health` e `GET /api/v1/version`;
4. esporre `POST /api/v1/decisions`;
5. restituire Decision Score, Decision Confidence, Pillars, trade-off ed Explainability;
6. configurare CORS per Lovable;
7. documentare avvio locale e OpenAPI;
8. mantenere verdi i test del Decision Engine.

Per dettaglio, acceptance criteria, API successive, dataset, persistenza, test e attività da NON anticipare, usare esclusivamente `TOMMASO_BACKLOG.md`.
