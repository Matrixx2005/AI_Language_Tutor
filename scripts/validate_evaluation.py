"""Validate the Week 1 placement and RAG evaluation draft."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALUATION_DIR = ROOT / "data" / "evaluation"
DATASET_PATH = ROOT / "data" / "processed" / "grammar_lessons_v1.json"
PLACEMENT_PATH = EVALUATION_DIR / "placement_v1.json"
RAG_QUERIES_PATH = EVALUATION_DIR / "rag_queries_v1.json"
SPLIT_MANIFEST_PATH = EVALUATION_DIR / "split_manifest.json"
EXPECTED_QUERY_COUNT = 30
EXPECTED_SPLIT_COUNTS = {"dev": 20, "test": 10}
ALLOWED_LEVELS = {"A1", "A2", "B1"}
MAX_SAME_ANSWER_POSITION = 10  # tối đa 1/3 số câu có đáp án đúng ở cùng một vị trí
EXPECTED_PLACEMENT_LEVEL_COUNTS = {"A1": 10, "A2": 10, "B1": 10}
EXPECTED_PLACEMENT_CATEGORY_COUNTS = {"grammar": 15, "vocabulary": 15}
EXPECTED_STRATIFICATION = {
    "all_queries": {
        "language": {"vi": 15, "en": 15},
        "query_type": {"terminology": 15, "semantic": 15},
    },
    "test_queries": {
        "language": {"vi": 5, "en": 5},
        "query_type": {"terminology": 5, "semantic": 5},
    },
}


def _read_json(path: Path) -> tuple[object | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"
    except json.JSONDecodeError as exc:
        return (
            None,
            f"invalid JSON in {path} at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}",
        )


def validate_placement(records: object) -> list[str]:
    if not isinstance(records, list):
        return ["placement root must be a JSON array"]

    errors: list[str] = []
    seen_ids: set[str] = set()
    level_counts = {level: 0 for level in EXPECTED_PLACEMENT_LEVEL_COUNTS}
    category_counts = {category: 0 for category in EXPECTED_PLACEMENT_CATEGORY_COUNTS}
    answer_positions: list[int] = []
    if len(records) != EXPECTED_QUERY_COUNT:
        errors.append(
            f"placement set must contain {EXPECTED_QUERY_COUNT} questions; got {len(records)}"
        )

    required = {
        "question_id",
        "language_code",
        "level_code",
        "category",
        "topic",
        "question_text",
        "options",
        "correct_answer",
        "explanation",
    }

    for index, record in enumerate(records, start=1):
        label = f"placement record {index}"
        if not isinstance(record, dict):
            errors.append(f"{label}: expected a JSON object")
            continue

        missing = sorted(required.difference(record))
        if missing:
            errors.append(f"{label}: missing required fields: {', '.join(missing)}")

        for field in sorted(required.difference({"options"})):
            value = record.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{label}: {field} must be a non-empty string")

        question_id = record.get("question_id")
        if isinstance(question_id, str) and question_id.strip():
            normalized_id = question_id.strip().casefold()
            if normalized_id in seen_ids:
                errors.append(f"{label}: duplicate question_id {question_id!r}")
            seen_ids.add(normalized_id)

        if record.get("language_code") != "en":
            errors.append(f"{label}: language_code must be 'en' in this placement set")
        level_code = record.get("level_code")
        if not isinstance(level_code, str) or level_code not in ALLOWED_LEVELS:
            errors.append(
                f"{label}: level_code must be one of {', '.join(sorted(ALLOWED_LEVELS))}"
            )
        else:
            level_counts[level_code] += 1

        category = record.get("category")
        if (
            not isinstance(category, str)
            or category not in EXPECTED_PLACEMENT_CATEGORY_COUNTS
        ):
            errors.append(f"{label}: category must be grammar or vocabulary")
        else:
            category_counts[category] += 1

        options = record.get("options")
        answer = record.get("correct_answer")
        if not isinstance(options, list) or len(options) < 2:
            errors.append(f"{label}: options must be a list with at least two choices")
        elif (
            any(not isinstance(option, str) or not option.strip() for option in options)
            or len({option.casefold() for option in options if isinstance(option, str)})
            != len(options)
        ):
            errors.append(f"{label}: options must be non-empty, unique strings")
        elif not isinstance(answer, str) or answer not in options:
            errors.append(f"{label}: correct_answer must match one of the options")
        else:
            answer_positions.append(options.index(answer))

    # Chống thiên lệch vị trí đáp án (đoán toàn đáp án A không được vượt ngưỡng xếp lớp).
    if len(answer_positions) == EXPECTED_QUERY_COUNT:
        most_common = max(answer_positions.count(p) for p in set(answer_positions))
        if most_common > MAX_SAME_ANSWER_POSITION:
            errors.append(
                f"correct answers are concentrated in one option position "
                f"({most_common}/{len(answer_positions)}); max allowed is {MAX_SAME_ANSWER_POSITION}"
            )

    if level_counts != EXPECTED_PLACEMENT_LEVEL_COUNTS:
        errors.append(
            f"placement level distribution must be {EXPECTED_PLACEMENT_LEVEL_COUNTS!r}; "
            f"got {level_counts!r}"
        )
    if category_counts != EXPECTED_PLACEMENT_CATEGORY_COUNTS:
        errors.append(
            f"placement category distribution must be {EXPECTED_PLACEMENT_CATEGORY_COUNTS!r}; "
            f"got {category_counts!r}"
        )

    return errors


def validate_rag_queries(
    records: object,
    document_ids: set[str],
    manifest: object,
) -> list[str]:
    if not isinstance(records, list):
        return ["RAG query root must be a JSON array"]
    if not isinstance(manifest, dict):
        return ["split manifest must be a JSON object"]

    errors: list[str] = []
    if len(records) != EXPECTED_QUERY_COUNT:
        errors.append(
            f"RAG query set must contain {EXPECTED_QUERY_COUNT} queries; got {len(records)}"
        )

    required = {"query_id", "query", "document_id", "language", "query_type", "split"}
    seen_ids: set[str] = set()
    actual_splits: dict[str, str] = {}
    split_counts = {"dev": 0, "test": 0}
    language_counts = {"vi": 0, "en": 0}
    query_type_counts = {"terminology": 0, "semantic": 0}
    test_language_counts = {"vi": 0, "en": 0}
    test_query_type_counts = {"terminology": 0, "semantic": 0}

    for index, record in enumerate(records, start=1):
        label = f"RAG query {index}"
        if not isinstance(record, dict):
            errors.append(f"{label}: expected a JSON object")
            continue

        missing = sorted(required.difference(record))
        if missing:
            errors.append(f"{label}: missing required fields: {', '.join(missing)}")
        for field in sorted(required):
            value = record.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{label}: {field} must be a non-empty string")

        query_id = record.get("query_id")
        if isinstance(query_id, str) and query_id.strip():
            normalized_id = query_id.strip().casefold()
            if normalized_id in seen_ids:
                errors.append(f"{label}: duplicate query_id {query_id!r}")
            seen_ids.add(normalized_id)
            actual_splits[query_id] = str(record.get("split", ""))

        language = record.get("language")
        if not isinstance(language, str) or language not in language_counts:
            errors.append(f"{label}: language must be vi or en")
        else:
            language_counts[language] += 1
            if record.get("split") == "test":
                test_language_counts[language] += 1

        query_type = record.get("query_type")
        if not isinstance(query_type, str) or query_type not in query_type_counts:
            errors.append(f"{label}: query_type must be terminology or semantic")
        else:
            query_type_counts[query_type] += 1
            if record.get("split") == "test":
                test_query_type_counts[query_type] += 1

        document_id = record.get("document_id")
        if isinstance(document_id, str) and document_id not in document_ids:
            errors.append(f"{label}: unknown document_id {document_id!r}")

        split = record.get("split")
        if not isinstance(split, str) or split not in split_counts:
            errors.append(f"{label}: split must be dev or test")
        else:
            split_counts[split] += 1

    expected_counts = manifest.get("expected_counts")
    if expected_counts != EXPECTED_SPLIT_COUNTS:
        errors.append(
            f"manifest expected_counts must be {EXPECTED_SPLIT_COUNTS!r}"
        )
    if split_counts != EXPECTED_SPLIT_COUNTS:
        errors.append(
            f"split counts must be {EXPECTED_SPLIT_COUNTS!r}; got {split_counts!r}"
        )

    ratio = manifest.get("ratio")
    if ratio != {"dev": 2, "test": 1}:
        errors.append("manifest ratio must remain locked at dev:test = 2:1")
    if manifest.get("stratification") != EXPECTED_STRATIFICATION:
        errors.append("manifest stratification does not match the locked distribution")
    if language_counts != EXPECTED_STRATIFICATION["all_queries"]["language"]:
        errors.append("RAG queries must contain 15 vi and 15 en queries")
    if query_type_counts != EXPECTED_STRATIFICATION["all_queries"]["query_type"]:
        errors.append("RAG queries must contain 15 terminology and 15 semantic queries")
    if test_language_counts != EXPECTED_STRATIFICATION["test_queries"]["language"]:
        errors.append("test split must contain 5 vi and 5 en queries")
    if test_query_type_counts != EXPECTED_STRATIFICATION["test_queries"]["query_type"]:
        errors.append("test split must contain 5 terminology and 5 semantic queries")

    manifest_dev = manifest.get("dev_query_ids")
    manifest_test = manifest.get("test_query_ids")
    if not isinstance(manifest_dev, list) or not all(
        isinstance(query_id, str) for query_id in manifest_dev
    ):
        errors.append("manifest dev_query_ids must be a list of strings")
        manifest_dev = []
    if not isinstance(manifest_test, list) or not all(
        isinstance(query_id, str) for query_id in manifest_test
    ):
        errors.append("manifest test_query_ids must be a list of strings")
        manifest_test = []

    if set(manifest_dev).intersection(manifest_test):
        errors.append("manifest dev and test IDs must be disjoint")
    if len(manifest_dev) != EXPECTED_SPLIT_COUNTS["dev"]:
        errors.append("manifest must list exactly 20 dev query IDs")
    if len(manifest_test) != EXPECTED_SPLIT_COUNTS["test"]:
        errors.append("manifest must list exactly 10 test query IDs")

    expected_ids = set(manifest_dev).union(manifest_test)
    if seen_ids != expected_ids:
        errors.append("query IDs must exactly match the locked IDs in the manifest")
    for query_id in manifest_dev:
        if actual_splits.get(query_id) != "dev":
            errors.append(f"manifest assigns {query_id!r} to dev but query label differs")
    for query_id in manifest_test:
        if actual_splits.get(query_id) != "test":
            errors.append(f"manifest assigns {query_id!r} to test but query label differs")

    return errors


def validate_files() -> list[str]:
    errors: list[str] = []
    placement, placement_error = _read_json(PLACEMENT_PATH)
    queries, queries_error = _read_json(RAG_QUERIES_PATH)
    manifest, manifest_error = _read_json(SPLIT_MANIFEST_PATH)
    dataset, dataset_error = _read_json(DATASET_PATH)

    for error in (
        placement_error,
        queries_error,
        manifest_error,
        dataset_error,
    ):
        if error is not None:
            errors.append(error)

    if placement_error is None:
        errors.extend(validate_placement(placement))
    if queries_error is None and manifest_error is None and dataset_error is None:
        document_ids: set[str] = set()
        if isinstance(dataset, list):
            for record in dataset:
                if isinstance(record, dict):
                    document_id = record.get("document_id")
                    if isinstance(document_id, str):
                        document_ids.add(document_id)
        errors.extend(validate_rag_queries(queries, document_ids, manifest))

    return errors


def main() -> int:
    errors = validate_files()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Evaluation validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1

    print("Evaluation validation passed: 30 placement questions, 30 RAG queries, 20 dev / 10 test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
