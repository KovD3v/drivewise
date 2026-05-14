import pytest

from app.embeddings.providers import (
    EMBEDDING_DIMENSION,
    EmbeddingProviderError,
    FakeEmbeddingProvider,
    get_embedding_provider,
)


def test_fake_embedding_provider_is_deterministic_and_1536_dimensional():
    provider = FakeEmbeddingProvider()

    first = provider.embed_texts(["Fiat Panda compact city car"], "fake-embedding-1536")
    second = provider.embed_texts(["Fiat Panda compact city car"], "fake-embedding-1536")
    different = provider.embed_texts(
        ["Toyota Yaris hybrid hatchback"],
        "fake-embedding-1536",
    )

    assert first == second
    assert first != different
    assert len(first) == 1
    assert len(first[0]) == EMBEDDING_DIMENSION
    assert all(isinstance(value, float) for value in first[0])


def test_only_fake_embedding_provider_is_available():
    assert isinstance(get_embedding_provider("fake"), FakeEmbeddingProvider)

    with pytest.raises(EmbeddingProviderError, match="Only the fake provider"):
        get_embedding_provider("openai")
