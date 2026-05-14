PLACEHOLDER_TOKENS = (
    "your-user",
    "your-password",
    "***",
    "your-neon-host",
    "your-test-host",
    "your-database",
    "your-test-database",
)


def contains_placeholder_database_url(database_url: str) -> bool:
    return any(token in database_url for token in PLACEHOLDER_TOKENS)
