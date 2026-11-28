"""Đối chiếu độ phủ chủ đề corpus (33 bài) với CEFR-J Grammar Profile (A1–B1) → docs/COVERAGE_AUDIT.md.

Nguồn: CEFR-J Grammar Profile ver. 20180315 (Tono Laboratory, TUFS), qua Open Language Profiles
(github.com/openlanguageprofiles/olp-en-cefrj). Điều khoản: dùng miễn phí cho nghiên cứu và thương mại, phải trích dẫn.
File CSV KHÔNG được commit (data/external/ trong .gitignore); tải lại: xem README. KHÔNG chép nội dung vào corpus.
Ánh xạ mục CEFR-J → bài học là luật từ khóa do Claude đặt (gần đúng) — chỉ để GỢI Ý mở rộng corpus.
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "external" / "cefrj" / "cefrj-grammar-profile-20180315.csv"
LESSONS = ROOT / "data" / "processed" / "grammar_lessons_v1.json"
OUT = ROOT / "docs" / "COVERAGE_AUDIT.md"

# (mẫu regex trên "mã | mục ngữ pháp" viết hoa, document_id). Mục đầu tiên khớp được dùng.
RULES = [
    (r"^PP\.I_AM|\bBE\b(?!.*GOING)|^PP\.", "gram-en-a1-be-001"),
    (r"PASTPF|PAST PERFECT", "gram-en-b1-past-perfect-031"),
    (r"PRPF|PRESENT PERFECT", "gram-en-a2-present-perfect-011"),
    (r"PASTPRG|PAST PROGRESSIVE", "gram-en-a2-past-continuous-023"),
    (r"PRSPRG|PRESENT PROGRESSIVE", "gram-en-a2-present-continuous-007"),
    (r"^PASS|PASSIVE", "gram-en-b1-passive-voice-028"),
    (r"TA\.PAST|PAST SIMPLE|TENSE/ASPECT: PAST\b", "gram-en-a2-past-simple-006"),
    (r"TA\.PRS|PRESENT SIMPLE|TENSE/ASPECT: PRESENT\b", "gram-en-a1-present-simple-002"),
    (r"GOING TO|BE_GOING_TO", "gram-en-a2-going-to-010"),
    (r"\bWILL\b|TA\.FUT", "gram-en-a2-will-future-024"),
    (r"USED TO|USED_TO", "gram-en-b1-used-to-030"),
    (r"\bCAN\b|MD\.CAN|BE ABLE TO", "gram-en-a1-can-ability-019"),
    (r"^MD|MODAL", "gram-en-b1-modals-013"),
    (r"\bIF\b|CONDITIONAL", "gram-en-b1-first-conditional-014"),
    (r"^PREL|^RBREL|RELATIVE", "gram-en-b1-relative-clauses-015"),
    (r"^INDSP|REPORTED|INDIRECT SPEECH", "gram-en-b1-reported-speech-029"),
    (r"SUPERLATIVE|COMP\.SUP", "gram-en-a2-superlatives-022"),
    (r"^COMP|COMPARATIVE", "gram-en-a2-comparatives-009"),
    (r"\bTOO\b|ENOUGH", "gram-en-b1-too-enough-032"),
    (r"^EX\.THERE|THERE\+", "gram-en-a1-there-be-005"),
    (r"^PGEN|^PPOS|POSSESSIVE|'S\b", "gram-en-a1-possessives-018"),
    (r"THIS|THAT|THESE|THOSE", "gram-en-a1-demonstratives-020"),
    (r"\bA/AN\b|ARTICLE|DT\.(A|THE)\b", "gram-en-a1-articles-003"),
    (r"MUCH|MANY|^QUANT|UNCOUNTABLE|COUNTABLE", "gram-en-a2-count-noncount-008"),
    (r"PLURAL|^NN", "gram-en-a1-plurals-004"),
    (r"^TO\.|TO-INFINITIVE|GERUND|^VG", "gram-en-a2-verb-patterns-025"),
    (r"FREQUENCY|ALWAYS|USUALLY|OFTEN", "gram-en-a1-frequency-adverbs-021"),
    (r"^RB|ADVERB", "gram-en-a2-adverbs-manner-026"),
    (r"^PREP|PREPOSITION|^IN\b", "gram-en-a1-prepositions-place-017"),
]


def main() -> int:
    rows = [r for r in csv.DictReader(CSV.open(encoding="utf-8")) if r["CEFR-J Level"][:2] in ("A1", "A2", "B1")]
    lessons = {x["document_id"]: x for x in json.loads(LESSONS.read_text(encoding="utf-8"))}
    covered: dict[str, list] = defaultdict(list)
    gaps = []
    for r in rows:
        text = f"{r['Shorthand Code']} | {r['Grammatical Item']}".upper()
        doc = next((d for pattern, d in RULES if re.search(pattern, text)), None)
        (covered[doc].append(r) if doc else gaps.append(r))
    lines = [
        "# Đối chiếu độ phủ corpus với CEFR-J Grammar Profile (Tuần 5B)", "",
        "**Nguồn:** CEFR-J Grammar Profile, phiên bản 20180315. Bản quyền: Tono Laboratory, Tokyo University of Foreign Studies (TUFS).",
        "Lấy từ Open Language Profiles: https://github.com/openlanguageprofiles/olp-en-cefrj (file `cefrj-grammar-profile-20180315.csv`).",
        "**Điều khoản (theo README của kho):** dùng miễn phí cho nghiên cứu và thương mại, **phải trích dẫn**; CEFR-J và Open Language Profiles",
        "không chịu trách nhiệm về sai sót. Bản grammar profile chỉ được dịch một phần từ bản tiếng Nhật.",
        "Trích dẫn: *The CEFR-J Grammar Profile Version 20180315. Tono Laboratory, TUFS. Distributed by Open Language Profiles.*", "",
        "**Cách dùng ở dự án:** CHỈ để đối chiếu độ phủ chủ đề và gợi ý mở rộng corpus. Không chép nội dung CEFR-J vào corpus. File CSV không",
        "được commit (thư mục `data/external/` nằm trong `.gitignore`).", "",
        f"**Phương pháp:** {len(rows)} mục CEFR-J có cấp A1–B1 được ánh xạ sang bài học bằng {len(RULES)} luật từ khóa trên mã và tên mục",
        "(do Claude đặt; gần đúng — có thể khớp nhầm hoặc sót). Đây là GỢI Ý, chưa phải đánh giá của chuyên gia.", "",
        f"**Kết quả:** {len(rows) - len(gaps)}/{len(rows)} mục khớp với ít nhất một bài học; **{len(gaps)} mục chưa phủ** (gợi ý mở rộng).", "",
        "## Số mục CEFR-J khớp với từng bài học", "", "| Bài học | Cấp | Số mục CEFR-J | Ví dụ mục |", "| --- | --- | --- | --- |",
    ]
    for doc in sorted(lessons):
        items = covered.get(doc, [])
        example = "; ".join(sorted({i["Grammatical Item"].strip()[:40] for i in items})[:2]).replace("|", "/")
        lines.append(f"| {doc} | {lessons[doc]['level']} | {len(items)} | {example} |")
    lines += ["", "## Mục CEFR-J A1–B1 chưa phủ (gợi ý mở rộng corpus)", "", "| Mã | Mục ngữ pháp | Cấp CEFR-J |", "| --- | --- | --- |"]
    for r in sorted(gaps, key=lambda r: (r["CEFR-J Level"], r["Shorthand Code"])):
        lines.append(f"| `{r['Shorthand Code']}` | {r['Grammatical Item'].strip().replace('|', '/')} | {r['CEFR-J Level']} |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(rows)} mục A1–B1; khớp {len(rows) - len(gaps)}; chưa phủ {len(gaps)}; bài không khớp mục nào: "
          f"{[d for d in lessons if not covered.get(d)]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
