# AGENTS.md

Operational rules for Codex and other coding agents working on Drivewise.

## Project Scope

- Keep the MVP scaffold simple and locally runnable.
- Do not add recommendation logic until explicitly requested.
- Do not integrate Firecrawl until explicitly requested.
- Do not add Redis runtime dependencies until the cache layer is designed.
- Treat Neon PostgreSQL and pgvector as planned infrastructure unless a task asks for database implementation.

## Secrets

- Never commit real secrets, tokens, database URLs, API keys, cookies, or credentials.
- Use `.env.example` for placeholders only.
- Keep `.env` and local virtual environments ignored.

## Code Style

- Prefer small files with clear ownership.
- Follow existing project patterns once they exist.
- Use Bun for frontend package management and scripts.
- Keep dependencies minimal and justified.
- Add tests for new runtime behavior.

## Verification

- Run the smallest relevant checks before reporting completion.
- If a check cannot run, report the exact command and failure.
- Do not claim a build, test suite, or integration works without fresh command output.
