# Search

Drivewise currently exposes a read-only document search endpoint:

```text
POST /search/documents
```

The endpoint is intentionally shaped for future hybrid search. The default
implementation remains `text_only`; an explicit `vector_fake` mode is available
only for dev/test searches over fake embeddings already stored in PostgreSQL.

## Request

```json
{
  "query": "fiat panda",
  "document_type": "seed_note",
  "limit": 10,
  "include_content": false,
  "mode": "text_only"
}
```

- `query` is required and cannot be blank.
- `document_type` is optional and exact-match.
- `limit` defaults to `10` and is capped at `50`.
- `include_content` defaults to `false`; when enabled, full stored document
  content is returned in each result.
- `mode` defaults to `text_only`; allowed values are `text_only` and
  `vector_fake`.

## Text Scoring

`mode: "text_only"` score is deterministic:

- exact phrase matches in `title` score highest;
- exact phrase matches in `content` score lower than title phrase matches;
- token matches in `title` score higher than token matches in `content`;
- recent documents receive a small boost for tie-breaking;
- rows with no title/content match are excluded.

## Fake Vector Search

`mode: "vector_fake"` is read-only and explicit. It:

- creates the query embedding with the local deterministic
  `FakeEmbeddingProvider`;
- uses model `fake-embedding-1536`;
- searches only documents where `embedding IS NOT NULL`;
- orders by pgvector cosine distance with `<=>`;
- returns score as cosine similarity, `1 - cosine_distance`, where higher is
  better;
- returns `items: []` when no embedded documents are available.

The mode is useful after writing local fake embeddings:

```bash
python apps/api/scripts/ingest_local.py --path data/fixtures/ingestion
python apps/api/scripts/embed_documents.py --provider fake --write --limit 20
curl -X POST http://127.0.0.1:8000/search/documents \
  -H "Content-Type: application/json" \
  -d '{"query":"fiat panda","mode":"vector_fake","limit":10}'
```

## Safety

The search endpoint:

- does not expose `embedding` or `embedding_model`;
- does not call OpenAI or any other provider;
- does not write to PostgreSQL;
- does not change schema.

`vector_fake` does use pgvector operators, but only against already stored fake
embeddings and only when the request explicitly sets `mode: "vector_fake"`.

## Future Hybrid Search

To add production hybrid search later, generate real embeddings through a
provider boundary, keep the existing text score as one signal, and add explicit
score composition tests. Do not silently change `mode: "text_only"` semantics.
