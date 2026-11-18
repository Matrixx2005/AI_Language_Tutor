from scripts.validate_dataset import validate_records


def make_record(**overrides: str) -> dict[str, str]:
    record = {
        "document_id": "gram-en-a1-example-001",
        "title": "Example lesson",
        "level": "A1",
        "topic": "example",
        "language": "English",
        "language_code": "en",
        "content": "An original lesson.",
        "source": "Original draft.",
        "license": "Pending approval.",
        "version": "v1.0-draft",
    }
    record.update(overrides)
    return record


def test_valid_record_passes():
    assert validate_records([make_record()]) == []


def test_missing_fields_and_invalid_level_are_reported():
    record = make_record(level="C2")
    del record["license"]

    errors = validate_records([record])

    assert any("missing required fields: license" in error for error in errors)
    assert any("level must be one of" in error for error in errors)


def test_duplicate_ids_and_normalized_content_are_reported():
    first = make_record()
    second = make_record(
        document_id=" GRAM-EN-A1-EXAMPLE-001 ",
        title="Another title",
        content="  AN ORIGINAL\nlesson. ",
    )

    errors = validate_records([first, second])

    assert any("duplicate document_id" in error for error in errors)
    assert any("duplicate content" in error for error in errors)


def test_non_array_root_is_rejected():
    assert validate_records({"document_id": "not-an-array"}) == [
        "dataset root must be a JSON array"
    ]
