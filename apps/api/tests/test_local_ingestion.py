"""F-24: local ingestion stays inside its input directory and never inflates numbers."""

import pytest

from app.ingestion.local import (
    LocalDocument,
    UnsafeIngestionPathError,
    load_local_documents,
    normalize_vehicle_document,
)


def _document(price: str) -> LocalDocument:
    return LocalDocument(
        title="Synthetic",
        content=f"Make: Acme\nModel: Metro\nYear: 2024\nPrice EUR: {price}\n",
        document_type="listing_snapshot",
        file_name="synthetic-listing.txt",
        local_path="synthetic-listing.txt",
        metadata={},
    )


def test_file_symlink_outside_the_input_directory_is_rejected(tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_text("# Secret notes\n")
    root = tmp_path / "input"
    root.mkdir()
    (root / "vehicle.md").write_text("# Acme Metro\n")
    (root / "linked.md").symlink_to(outside)
    with pytest.raises(UnsafeIngestionPathError, match="linked.md"):
        load_local_documents(root)


def test_directory_symlink_outside_the_input_directory_is_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("# Secret notes\n")
    root = tmp_path / "input"
    root.mkdir()
    (root / "elsewhere").symlink_to(outside, target_is_directory=True)
    # Python 3.12 rglob may or may not descend into the link; either way no
    # file from outside the input directory may be loaded.
    try:
        documents = load_local_documents(root)
    except UnsafeIngestionPathError:
        return
    assert documents == []


def test_symlink_that_stays_inside_the_input_directory_is_loaded(tmp_path):
    root = tmp_path / "input"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "vehicle.md").write_text("# Acme Metro\n")
    (root / "alias.md").symlink_to(root / "docs" / "vehicle.md")
    documents = load_local_documents(root)
    assert [d.file_name for d in documents] == ["alias.md", "vehicle.md"]
    # Recorded paths keep the selected path, not the resolved target.
    assert documents[0].local_path == (root / "alias.md").as_posix()


@pytest.mark.parametrize(
    "price, parsed",
    [
        ("15500", 15500),
        ("19.990", 19990),
        ("1.234.567", 1234567),
        ("19.990,50", None),
        ("19990,50", None),
        ("19,990", None),
        ("1.5", None),
        ("19.99", None),
    ],
)
def test_integer_fields_never_drop_decimal_separators(price, parsed):
    normalized = normalize_vehicle_document(_document(price))
    if parsed is None:
        assert "price_eur" not in normalized.proposed_listing
        assert normalized.metadata["unparsed_fields"]["price_eur"] == price
    else:
        assert normalized.proposed_listing["price_eur"] == parsed
