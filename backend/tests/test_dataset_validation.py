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


def test_week4_conventions_id_length_and_near_duplicate():
    from scripts.validate_dataset import validate_conventions

    good = make_record(document_id="gram-en-a1-be-001", content="Use am with I and is with she.")
    assert validate_conventions([good]) == []
    bad_id = make_record(document_id="lesson-1")
    wrong_level = make_record(document_id="gram-en-b1-be-002")  # bài A1
    too_long = make_record(document_id="gram-en-a1-long-003", content="word " * 161)
    errors = validate_conventions([bad_id, wrong_level, too_long])
    assert any("quy ước" in e for e in errors)
    assert any("không khớp" in e for e in errors)
    assert any("161 từ" in e for e in errors)
    a = make_record(document_id="gram-en-a1-a-004", content="Use at for times and on for days in English sentences.")
    b = make_record(document_id="gram-en-a1-b-005", content="Use at for times and on for days in English sentences today.")
    assert any("gần trùng" in e for e in validate_conventions([a, b]))


def test_keywords_file_must_cover_every_lesson_with_non_empty_lists():
    from scripts.validate_dataset import validate_keywords

    ids = {"gram-en-a1-be-001", "gram-en-a1-be-002"}
    assert validate_keywords({"keywords": {i: ["động từ be"] for i in ids}}, ids) == []
    errors = validate_keywords({"keywords": {"gram-en-a1-be-001": [], "la": ["x"]}}, ids)
    assert len(errors) == 3  # danh sách rỗng, id lạ, thiếu bài
