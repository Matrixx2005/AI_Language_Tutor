"""Validate the Week 1 JSON dataset without requiring third-party packages."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = ROOT / "data" / "processed" / "grammar_lessons_v1.json"
REQUIRED_FIELDS = {
    "document_id",
    "title",
    "level",
    "topic",
    "language",
    "language_code",
    "content",
    "source",
    "license",
    "version",
}
ALLOWED_LEVELS = {"A1", "A2", "B1"}


def _normalized_content(value: str) -> str:
    return " ".join(value.casefold().split())


def validate_records(records: object) -> list[str]:
    if not isinstance(records, list):
        return ["dataset root must be a JSON array"]

    errors: list[str] = []
    seen_ids: dict[str, int] = {}
    seen_content: dict[tuple[str, str], int] = {}

    for index, record in enumerate(records, start=1):
        label = f"record {index}"
        if not isinstance(record, dict):
            errors.append(f"{label}: expected a JSON object")
            continue

        missing_fields = sorted(REQUIRED_FIELDS.difference(record))
        if missing_fields:
            errors.append(
                f"{label}: missing required fields: {', '.join(missing_fields)}"
            )

        for field in sorted(REQUIRED_FIELDS):
            if field in record and (
                not isinstance(record[field], str) or not record[field].strip()
            ):
                errors.append(f"{label}: {field} must be a non-empty string")

        document_id = record.get("document_id")
        if isinstance(document_id, str) and document_id.strip():
            normalized_id = document_id.strip().casefold()
            if normalized_id in seen_ids:
                errors.append(
                    f"{label}: duplicate document_id {document_id!r} "
                    f"(also record {seen_ids[normalized_id]})"
                )
            else:
                seen_ids[normalized_id] = index

        level = record.get("level")
        if isinstance(level, str) and level not in ALLOWED_LEVELS:
            errors.append(
                f"{label}: level must be one of {', '.join(sorted(ALLOWED_LEVELS))}"
            )

        language_code = record.get("language_code")
        content = record.get("content")
        if (
            isinstance(language_code, str)
            and language_code.strip()
            and isinstance(content, str)
            and content.strip()
        ):
            content_key = (
                language_code.strip().casefold(),
                _normalized_content(content),
            )
            if content_key in seen_content:
                errors.append(
                    f"{label}: duplicate content for language_code "
                    f"{language_code!r} (also record {seen_content[content_key]})"
                )
            else:
                seen_content[content_key] = index

    return errors


def validate_file(path: Path) -> tuple[list[str], int | None]:
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"cannot read {path}: {exc}"], None
    except json.JSONDecodeError as exc:
        return [f"invalid JSON in {path} at line {exc.lineno}, column {exc.colno}: {exc.msg}"], None

    errors = validate_records(records)
    record_count = len(records) if isinstance(records, list) else None
    return errors, record_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a grammar dataset JSON file.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"dataset path (default: {DEFAULT_DATASET})",
    )
    args = parser.parse_args()

    errors, record_count = validate_file(args.input)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1

    print(f"Validation passed: {record_count} records, 0 errors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
