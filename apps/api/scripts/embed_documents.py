import argparse
import os
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from app.core.config import PROJECT_ROOT, load_env_file  # noqa: E402
from app.core.database_url import contains_placeholder_database_url  # noqa: E402
from app.embeddings.pipeline import (  # noqa: E402
    EmbeddingExecutionResult,
    embed_document_batch,
)
from app.embeddings.planner import (  # noqa: E402
    DEFAULT_EMBEDDING_BATCH_LIMIT,
    EmbeddingPlanError,
    validate_document_type,
    validate_embedding_limit,
)
from app.embeddings.providers import (  # noqa: E402
    DEFAULT_FAKE_EMBEDDING_MODEL,
    EmbeddingProviderError,
    get_embedding_provider,
)


DATABASE_ENV_KEYS = frozenset({"DATABASE_URL"})


def main(argv: list[str] | None = None, env_path: Path = PROJECT_ROOT / ".env") -> int:
    args = parse_args(argv)

    try:
        provider = get_embedding_provider(args.provider)
        validate_embedding_limit(args.limit)
        validate_document_type(args.document_type)
        if not args.model.strip():
            raise EmbeddingPlanError("model must not be empty")
    except (EmbeddingPlanError, EmbeddingProviderError) as error:
        print(str(error), file=sys.stderr)
        return 1

    load_env_file(env_path, allowed_keys=DATABASE_ENV_KEYS)
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print(
            "DATABASE_URL is not set. Create .env from .env.example and set "
            "DATABASE_URL, or export DATABASE_URL in your shell.",
            file=sys.stderr,
        )
        return 1

    if contains_placeholder_database_url(database_url):
        print(
            "DATABASE_URL still contains placeholders. Replace .env values with "
            "your Neon connection string before embedding documents.",
            file=sys.stderr,
        )
        return 1

    try:
        with psycopg.connect(database_url, row_factory=dict_row) as conn:
            result = embed_document_batch(
                conn,
                provider=provider,
                provider_name=args.provider,
                model=args.model,
                limit=args.limit,
                document_type=args.document_type,
                write=args.write,
                force=args.force,
            )
    except psycopg.OperationalError:
        print(
            "Could not connect to the database configured by DATABASE_URL. "
            "Verify the Neon connection string, network access, and sslmode=require.",
            file=sys.stderr,
        )
        return 1
    except psycopg.Error as error:
        print(
            "Embedding execution failed while accessing PostgreSQL. Verify "
            f"migrations and privileges. Error type: {error.__class__.__name__}.",
            file=sys.stderr,
        )
        return 1
    except (EmbeddingPlanError, EmbeddingProviderError) as error:
        print(str(error), file=sys.stderr)
        return 1

    print_result(result)
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate fake deterministic document embeddings. Dry-run by default; "
            "pass --write to update PostgreSQL."
        )
    )
    parser.add_argument(
        "--provider",
        required=True,
        help="Embedding provider to use. Only 'fake' is currently available.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_FAKE_EMBEDDING_MODEL,
        help="Embedding model name to store with generated vectors.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_EMBEDDING_BATCH_LIMIT,
        help="Maximum documents to embed. Must be 1-100.",
    )
    parser.add_argument(
        "--document-type",
        default=None,
        help="Optional exact documents.document_type filter.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write fake embeddings to documents.embedding and embedding_model.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Include documents that already have embeddings and overwrite them.",
    )
    return parser.parse_args(argv)


def print_result(result: EmbeddingExecutionResult) -> None:
    print("Embedding write result" if result.write else "Embedding dry-run plan")
    print(f"Provider: {result.provider_name}")
    print(f"Model: {result.plan.model}")
    print(f"Limit: {result.plan.limit}")
    print(f"Document type filter: {result.plan.document_type or 'none'}")
    print(f"Force overwrite: {'yes' if result.force else 'no'}")
    print(f"Documents selected: {result.plan.total_documents}")
    print(f"Embedded: {result.embedded}")
    print(f"Skipped existing: {result.skipped_existing}")
    print(f"Total estimated chars: {result.plan.total_estimated_characters}")
    print(f"Total estimated tokens: {result.plan.total_estimated_tokens}")

    for document in result.plan.documents:
        print(f"- {document.id}")
        print(f"  Title: {document.title}")
        print(f"  Type: {document.document_type}")
        print(f"  Estimated chars: {document.estimated_characters}")
        print(f"  Estimated tokens: {document.estimated_tokens}")
        print(f"  Preview: {document.preview}")

    print("No real external provider calls were made.")
    if not result.write:
        print("No database writes were made.")


if __name__ == "__main__":
    raise SystemExit(main())
