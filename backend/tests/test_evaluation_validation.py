from scripts.validate_evaluation import validate_placement, validate_rag_queries


def make_placement(**overrides):
    record = {
        "question_id": "placement-001",
        "language_code": "en",
        "level_code": "A1",
        "category": "grammar",
        "topic": "verb be",
        "question_text": "They ___ ready.",
        "options": ["is", "are"],
        "correct_answer": "are",
        "explanation": "Use are with they.",
    }
    record.update(overrides)
    return record


def make_query(**overrides):
    record = {
        "query_id": "rag-q-001",
        "query": "How do I use the verb be?",
        "document_id": "doc-1",
        "language": "en",
        "query_type": "terminology",
        "split": "dev",
    }
    record.update(overrides)
    return record


def make_manifest(dev_ids, test_ids):
    return {
        "ratio": {"dev": 2, "test": 1},
        "expected_counts": {"dev": 20, "test": 10},
        "stratification": {
            "all_queries": {
                "language": {"vi": 15, "en": 15},
                "query_type": {"terminology": 15, "semantic": 15},
            },
            "test_queries": {
                "language": {"vi": 5, "en": 5},
                "query_type": {"terminology": 5, "semantic": 5},
            },
        },
        "dev_query_ids": dev_ids,
        "test_query_ids": test_ids,
    }


def test_placement_rejects_answer_outside_choices():
    errors = validate_placement(
        [make_placement(correct_answer="am", level_code=[])]
    )

    assert any("correct_answer must match" in error for error in errors)
    assert any("level_code must be one of" in error for error in errors)
    assert any("must contain 30 questions" in error for error in errors)


def test_placement_rejects_answers_concentrated_in_one_position():
    records = [
        make_placement(question_id=f"placement-{index:03d}", options=["are", "is"])
        for index in range(30)
    ]

    errors = validate_placement(records)

    assert any("concentrated in one option position" in error for error in errors)


def test_rag_validation_checks_document_reference_and_locked_split():
    query = make_query(document_id="missing-document")
    manifest = make_manifest(["rag-q-001"], [])

    errors = validate_rag_queries([query], {"doc-1"}, manifest)

    assert any("unknown document_id" in error for error in errors)
    assert any("split counts must be" in error for error in errors)


def test_rag_validation_rejects_manifest_label_mismatch():
    dev_ids = [f"dev-{index}" for index in range(20)]
    test_ids = [f"test-{index}" for index in range(10)]
    records = [make_query(query_id=query_id, split="dev") for query_id in dev_ids]
    records.extend(
        make_query(query_id=query_id, split="test") for query_id in test_ids
    )
    manifest = make_manifest(dev_ids, test_ids)
    records[0]["split"] = "test"

    errors = validate_rag_queries(records, {"doc-1"}, manifest)

    assert any(
        "manifest assigns 'dev-0' to dev but query label differs" in error
        for error in errors
    )
