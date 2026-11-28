"""Validate the Week 1 JSON dataset without requiring third-party packages."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = ROOT / "data" / "processed" / "grammar_lessons_v1.json"
DEFAULT_KEYWORDS = ROOT / "data" / "processed" / "keywords_vi_v1.json"
# Quy ước Tuần 4: gram-<language_code>-<level viết thường>-<slug>-<số 3 chữ số>, ví dụ gram-en-a1-be-001.
ID_PATTERN = re.compile(r"^gram-(?P<lang>[a-z]{2,3})-(?P<level>[a-z]\d)-[a-z0-9]+(?:-[a-z0-9]+)*-\d{3}$")
MAX_CONTENT_WORDS = 160  # bài ngắn (~150 từ): 1 bài = 1 chunk
NEAR_DUPLICATE_JACCARD = 0.6  # trùng ≥ 60% tập từ giữa hai bài → báo lỗi
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

    errors.extend(validate_conventions([r for r in records if isinstance(r, dict)]))
    return errors


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z']+", text.casefold()))


def validate_conventions(records: list[dict]) -> list[str]:
    """Quy ước id, độ dài nội dung và nội dung gần trùng (trùng hoàn toàn đã kiểm ở trên)."""
    errors: list[str] = []
    for r in records:
        did = r.get("document_id")
        if not isinstance(did, str):
            continue
        m = ID_PATTERN.match(did)
        if not m:
            errors.append(f"{did}: document_id không theo quy ước gram-<lang>-<level>-<slug>-<NNN>")
        elif m["lang"] != r.get("language_code") or m["level"] != str(r.get("level", "")).casefold():
            errors.append(f"{did}: document_id không khớp language_code/level của bài")
        content = r.get("content")
        if isinstance(content, str) and len(content.split()) > MAX_CONTENT_WORDS:
            errors.append(f"{did}: nội dung dài {len(content.split())} từ (> {MAX_CONTENT_WORDS})")
    bags = [(r.get("document_id"), _words(r["content"])) for r in records if isinstance(r.get("content"), str)]
    for i, (a, wa) in enumerate(bags):
        for b, wb in bags[i + 1:]:
            if wa and wb and len(wa & wb) / len(wa | wb) >= NEAR_DUPLICATE_JACCARD:
                errors.append(f"{a} và {b}: nội dung gần trùng (Jaccard ≥ {NEAR_DUPLICATE_JACCARD})")
    return errors


def validate_keywords(payload: object, document_ids: set[str]) -> list[str]:
    """File từ khóa tiếng Việt (tùy chọn): mỗi bài một danh sách chuỗi không rỗng, không id lạ."""
    if not isinstance(payload, dict) or not isinstance(payload.get("keywords"), dict):
        return ["keywords file: cần object có khóa 'keywords'"]
    errors = []
    keywords = payload["keywords"]
    for did, words in keywords.items():
        if did not in document_ids:
            errors.append(f"keywords: id lạ {did!r}")
        if not isinstance(words, list) or not words or not all(isinstance(w, str) and w.strip() for w in words):
            errors.append(f"keywords: {did} cần danh sách chuỗi không rỗng")
    missing = sorted(document_ids - set(keywords))
    if missing:
        errors.append(f"keywords: thiếu {len(missing)} bài: {', '.join(missing[:5])}")
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
    parser.add_argument("--keywords", type=Path, default=DEFAULT_KEYWORDS, help="file từ khóa tiếng Việt (bỏ qua nếu không có)")
    args = parser.parse_args()

    errors, record_count = validate_file(args.input)
    if not errors and args.keywords.exists():
        records = json.loads(args.input.read_text(encoding="utf-8"))
        errors = validate_keywords(json.loads(args.keywords.read_text(encoding="utf-8")),
                                   {r["document_id"] for r in records})
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1

    print(f"Validation passed: {record_count} records, 0 errors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
