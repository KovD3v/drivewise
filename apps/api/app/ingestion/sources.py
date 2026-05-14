from dataclasses import dataclass
from typing import Literal


SourceKind = Literal["local_fixture", "firecrawl"]
PlannerDocumentType = Literal[
    "vehicle_profile",
    "listing_snapshot",
    "review_excerpt",
    "spec_sheet",
    "seed_note",
]


@dataclass(frozen=True)
class BaseSourceConfig:
    name: str
    source_type: SourceKind
    limit: int


@dataclass(frozen=True)
class LocalFixtureSourceConfig(BaseSourceConfig):
    path: str


@dataclass(frozen=True)
class FirecrawlSourceConfig(BaseSourceConfig):
    url: str
    document_type: PlannerDocumentType
    crawl_depth: int


DOCUMENT_TYPES: frozenset[str] = frozenset(
    {
        "vehicle_profile",
        "listing_snapshot",
        "review_excerpt",
        "spec_sheet",
        "seed_note",
    }
)
