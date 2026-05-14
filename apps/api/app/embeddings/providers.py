import hashlib
from typing import Protocol


EMBEDDING_DIMENSION = 1536
DEFAULT_FAKE_EMBEDDING_MODEL = "fake-embedding-1536"


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str], model: str) -> list[list[float]]:
        """Return one embedding vector per input text."""


class EmbeddingProviderError(ValueError):
    pass


class FakeEmbeddingProvider:
    """Deterministic local provider for tests and controlled development writes."""

    dimension = EMBEDDING_DIMENSION

    def embed_texts(self, texts: list[str], model: str) -> list[list[float]]:
        model_name = model.strip()
        if not model_name:
            raise EmbeddingProviderError("model must not be empty")

        return [self._embed_one(text, model_name) for text in texts]

    def _embed_one(self, text: str, model: str) -> list[float]:
        seed = f"{model}\0{text}".encode("utf-8")
        values: list[float] = []
        counter = 0

        while len(values) < self.dimension:
            digest = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            counter += 1
            for offset in range(0, len(digest), 4):
                integer = int.from_bytes(digest[offset : offset + 4], "big")
                values.append(round((integer / 0xFFFFFFFF) * 2 - 1, 8))
                if len(values) == self.dimension:
                    break

        return values


def get_embedding_provider(provider_name: str) -> EmbeddingProvider:
    normalized_name = provider_name.strip().lower()
    if normalized_name == "fake":
        return FakeEmbeddingProvider()

    raise EmbeddingProviderError(
        "Only the fake provider is available. Pass --provider fake; real "
        "embedding providers are intentionally not configured."
    )
