# Embeddings

Drivewise stores optional pgvector embeddings on `documents`. Real external
providers are not configured yet. The only executable provider is a local
deterministic fake provider for tests and controlled development writes.

## Planning Command

Run the planner against the database configured by `DATABASE_URL`:

```bash
python apps/api/scripts/plan_embeddings.py
```

Options:

- `--limit`: maximum documents to include, default `20`, valid range `1..100`.
- `--document-type`: optional exact `documents.document_type` filter.
- `--model`: model name to include in the plan, default `text-embedding-3-small`.

Example:

```bash
python apps/api/scripts/plan_embeddings.py \
  --limit 10 \
  --document-type vehicle_profile \
  --model text-embedding-3-small
```

## Behavior

The planner reads documents where `embedding IS NULL`, ordered by oldest
`created_at` first. For each candidate it prints:

- `id`
- `title`
- `document_type`
- estimated character count
- rough token estimate
- short preview

It does not print full document content.

## Fake Provider Command

Use `embed_documents.py` for the controlled fake-provider pipeline:

```bash
python apps/api/scripts/embed_documents.py --provider fake
```

The command is dry-run by default. It selects documents missing embeddings,
prints the same short plan shape, and does not generate vectors or write to the
database unless `--write` is provided.

Options:

- `--provider fake`: required; no other provider is available.
- `--model`: model name stored in `documents.embedding_model`, default
  `fake-embedding-1536`.
- `--limit`: maximum documents to embed, default `20`, valid range `1..100`.
- `--document-type`: optional exact `documents.document_type` filter.
- `--write`: generate deterministic fake vectors and update PostgreSQL.
- `--force`: include documents that already have embeddings and overwrite them.

Dry-run example:

```bash
python apps/api/scripts/embed_documents.py \
  --provider fake \
  --limit 10 \
  --document-type seed_note
```

Write example:

```bash
python apps/api/scripts/embed_documents.py \
  --provider fake \
  --write \
  --limit 10 \
  --document-type seed_note
```

Overwrite existing fake embeddings explicitly:

```bash
python apps/api/scripts/embed_documents.py \
  --provider fake \
  --write \
  --force \
  --limit 10
```

`FakeEmbeddingProvider` returns deterministic `1536`-dimension vectors derived
from the requested model and document content. It uses no network and no
non-deterministic random source.

## Safety

The planner and fake-provider pipeline:

- does not call OpenAI or any other provider;
- does not require API keys;
- does not import or configure real provider SDKs;
- does not modify `documents.metadata`;
- does not change schema.

`embed_documents.py --provider fake --write` is the only command that writes
embeddings. It updates `documents.embedding` and `documents.embedding_model`,
and it does not overwrite existing embeddings unless `--force` is provided.

## Activation Later

To generate real embeddings later, add a new provider implementation behind the
existing `EmbeddingProvider` interface, configure explicit provider selection,
add API-key handling through environment variables, and test the provider with
mocked network calls. Do not enable provider calls from app startup or CI.
