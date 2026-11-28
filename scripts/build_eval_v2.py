"""Tạo bộ đánh giá truy xuất v2 (Tuần 5A): data/evaluation/rag_queries_v2.json + split_manifest_v2.json.

- 30 truy vấn v1 giữ NGUYÊN (query_id, câu, đáp án, split). File v1 và split_manifest.json không bị sửa.
- Truy vấn mới (author "claude-draft") soạn CHỈ từ (title, topic, level) của bài — không chép câu trong nội dung bài.
  Kiểu hỏi đa dạng (style): definition, situation, error_fix, comparison, short_chat.
- Nhóm expected="none": chủ đề KHÔNG có trong corpus, để đo trường hợp phải từ chối.
- Chia dev/test cho truy vấn MỚI bằng băm cố định, phân tầng theo đáp án: trong mỗi nhóm (document_id hoặc "none"),
  sắp theo sha256(SEED + ":" + query_id); round(0.3 × k) truy vấn đầu → test, còn lại → dev. Chạy TRƯỚC mọi đánh giá.
Chạy lại cho cùng kết quả (tất định).
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "data" / "evaluation"
SEED = "rag-v2-2026-11-28"
TEST_FRACTION = 0.3

# (document_id hoặc None, language, query_type, style, query)
NEW = [
    ("gram-en-a1-prepositions-time-016", "vi", "terminology", "definition", "Giới từ chỉ thời gian in, on, at khác nhau thế nào?"),
    ("gram-en-a1-prepositions-time-016", "en", "semantic", "situation", "I'm writing about my birthday party. Do I put in, on or at before the date?"),
    ("gram-en-a1-prepositions-time-016", "vi", "semantic", "error_fix", "Câu 'I will meet you on next Friday' sai ở đâu?"),
    ("gram-en-a1-prepositions-place-017", "en", "terminology", "definition", "What are the prepositions of place in, on and at used for?"),
    ("gram-en-a1-prepositions-place-017", "vi", "semantic", "situation", "Muốn nói cái điện thoại nằm trên mặt bàn thì dùng giới từ nào?"),
    ("gram-en-a1-prepositions-place-017", "en", "semantic", "short_chat", "in the airport or at the airport?"),
    ("gram-en-a1-possessives-018", "vi", "terminology", "definition", "Tính từ sở hữu và sở hữu cách 's dùng thế nào?"),
    ("gram-en-a1-possessives-018", "en", "semantic", "situation", "How do I say that the laptop belongs to my sister?"),
    ("gram-en-a1-possessives-018", "vi", "semantic", "error_fix", "Viết 'the house of Minh' có tự nhiên không?"),
    ("gram-en-a1-can-ability-019", "en", "terminology", "definition", "How is the modal can used to talk about ability?"),
    ("gram-en-a1-can-ability-019", "vi", "semantic", "situation", "Muốn khoe 'Tôi biết chơi đàn guitar' bằng tiếng Anh thì dùng cấu trúc gì?"),
    ("gram-en-a1-can-ability-019", "en", "semantic", "error_fix", "Is 'She cans play piano' correct?"),
    ("gram-en-a1-demonstratives-020", "vi", "terminology", "comparison", "Phân biệt this, that, these và those."),
    ("gram-en-a1-demonstratives-020", "en", "semantic", "situation", "I'm pointing at some books far away from me. Which word should I use?"),
    ("gram-en-a1-demonstratives-020", "vi", "semantic", "situation", "Khi nhấc điện thoại, giới thiệu mình là ai thì nói thế nào?"),
    ("gram-en-a1-frequency-adverbs-021", "en", "terminology", "definition", "Where do adverbs of frequency go in a sentence?"),
    ("gram-en-a1-frequency-adverbs-021", "vi", "semantic", "situation", "Muốn nói 'tôi hiếm khi uống trà' thì đặt từ chỉ mức độ thường xuyên ở đâu?"),
    ("gram-en-a1-frequency-adverbs-021", "en", "semantic", "error_fix", "What's wrong with 'He goes usually to work by bus'?"),
    ("gram-en-a2-superlatives-022", "vi", "terminology", "definition", "So sánh nhất của tính từ được tạo như thế nào?"),
    ("gram-en-a2-superlatives-022", "en", "semantic", "error_fix", "Can I say 'Lan is the most tall student in my class'?"),
    ("gram-en-a2-superlatives-022", "vi", "semantic", "situation", "Muốn nói 'hôm nay là ngày tệ nhất của tôi' thì dùng dạng nào của bad?"),
    ("gram-en-a2-past-continuous-023", "en", "terminology", "definition", "How is the past continuous formed?"),
    ("gram-en-a2-past-continuous-023", "vi", "semantic", "situation", "Muốn kể 'lúc 9 giờ tối qua tôi đang xem phim' thì dùng thì gì?"),
    ("gram-en-a2-past-continuous-023", "vi", "semantic", "situation", "Một hành động đang kéo dài trong quá khứ thì bị một việc khác chen ngang, chia động từ thế nào?"),
    ("gram-en-a2-will-future-024", "vi", "terminology", "definition", "Thì tương lai đơn với will dùng khi nào?"),
    ("gram-en-a2-will-future-024", "en", "semantic", "situation", "Someone knocks on the door and I decide right now to open it. What do I say?"),
    ("gram-en-a2-will-future-024", "en", "semantic", "error_fix", "Is 'I will to call you tomorrow' correct?"),
    ("gram-en-a2-verb-patterns-025", "en", "terminology", "definition", "Which verbs are followed by a gerund and which by a to-infinitive?"),
    ("gram-en-a2-verb-patterns-025", "vi", "semantic", "short_chat", "Nói 'Tôi muốn học tiếng Anh' thì là want learning hay want to learn?"),
    ("gram-en-a2-verb-patterns-025", "vi", "semantic", "error_fix", "Câu 'She enjoys to cook' có đúng không?"),
    ("gram-en-a2-adverbs-manner-026", "vi", "terminology", "definition", "Trạng từ chỉ cách thức được tạo thế nào?"),
    ("gram-en-a2-adverbs-manner-026", "en", "semantic", "error_fix", "Is it 'she sings beautiful' or 'she sings beautifully'?"),
    ("gram-en-a2-adverbs-manner-026", "en", "terminology", "short_chat", "adverb form of good?"),
    ("gram-en-b1-second-conditional-027", "en", "terminology", "definition", "How do I form the second conditional?"),
    ("gram-en-b1-second-conditional-027", "vi", "semantic", "situation", "Muốn khuyên bạn 'nếu tôi là bạn thì tôi sẽ đi khám bác sĩ' thì dùng cấu trúc gì?"),
    ("gram-en-b1-second-conditional-027", "vi", "semantic", "situation", "Nói về một điều không có thật ở hiện tại, như tưởng tượng mình trúng xổ số, thì chia động từ thế nào?"),
    ("gram-en-b1-passive-voice-028", "vi", "terminology", "definition", "Câu bị động ở thì hiện tại đơn có cấu trúc gì?"),
    ("gram-en-b1-passive-voice-028", "en", "semantic", "situation", "How do I say that someone stole my bike yesterday without saying who did it?"),
    ("gram-en-b1-passive-voice-028", "en", "terminology", "definition", "When should I add by plus the person in a passive sentence?"),
    ("gram-en-b1-reported-speech-029", "en", "terminology", "definition", "How do tenses change in reported speech?"),
    ("gram-en-b1-reported-speech-029", "vi", "semantic", "situation", "Bạn tôi nói 'I am hungry'. Kể lại lời bạn ấy thì viết thế nào?"),
    ("gram-en-b1-reported-speech-029", "vi", "terminology", "comparison", "Khi kể lại lời người khác, khi nào dùng say và khi nào dùng tell?"),
    ("gram-en-b1-used-to-030", "vi", "terminology", "definition", "Cấu trúc used to diễn tả điều gì?"),
    ("gram-en-b1-used-to-030", "en", "semantic", "situation", "I lived in Hue as a child but I don't now. How can I say this in one sentence?"),
    ("gram-en-b1-used-to-030", "en", "terminology", "comparison", "What's the difference between 'used to do' and 'be used to doing'?"),
    ("gram-en-b1-past-perfect-031", "en", "terminology", "definition", "When do we use the past perfect tense?"),
    ("gram-en-b1-past-perfect-031", "vi", "semantic", "situation", "Khi tôi đến rạp thì phim đã bắt đầu rồi — vế 'phim đã bắt đầu' chia thì gì?"),
    ("gram-en-b1-past-perfect-031", "vi", "terminology", "definition", "Thì quá khứ hoàn thành được tạo như thế nào?"),
    ("gram-en-b1-too-enough-032", "vi", "terminology", "definition", "Vị trí của too và enough trong câu?"),
    ("gram-en-b1-too-enough-032", "en", "semantic", "situation", "The bag is so heavy that I can't carry it. How do I say this with 'too'?"),
    ("gram-en-b1-too-enough-032", "en", "semantic", "error_fix", "Is 'He is enough old to drive' correct?"),
    ("gram-en-b1-zero-conditional-033", "en", "terminology", "definition", "What is the zero conditional used for?"),
    ("gram-en-b1-zero-conditional-033", "vi", "semantic", "situation", "Nói một sự thật luôn đúng như 'nếu đun nước đủ nóng thì nước sôi' thì dùng cấu trúc gì?"),
    ("gram-en-b1-zero-conditional-033", "vi", "terminology", "comparison", "Câu điều kiện nói về điều luôn đúng khác câu điều kiện loại 1 thế nào?"),
    # Thêm 1 truy vấn cho mỗi bài cũ (để mỗi bài có 3)
    ("gram-en-a1-be-001", "en", "semantic", "error_fix", "Is 'They is my friends' correct?"),
    ("gram-en-a1-present-simple-002", "vi", "semantic", "error_fix", "Câu 'My father work in a bank' sai chỗ nào?"),
    ("gram-en-a1-articles-003", "en", "terminology", "definition", "When do I use the definite article the?"),
    ("gram-en-a1-plurals-004", "vi", "terminology", "definition", "Danh từ tận cùng bằng -y đổi sang số nhiều thế nào?"),
    ("gram-en-a1-there-be-005", "en", "semantic", "situation", "How do I tell a visitor that a park exists near my house?"),
    ("gram-en-a2-past-simple-006", "vi", "terminology", "definition", "Động từ bất quy tắc ở thì quá khứ đơn là gì?"),
    ("gram-en-a2-present-continuous-007", "en", "semantic", "short_chat", "which tense for something happening right now?"),
    ("gram-en-a2-count-noncount-008", "vi", "semantic", "short_chat", "Hỏi lượng sữa còn lại thì dùng how much hay how many?"),
    ("gram-en-a2-comparatives-009", "en", "terminology", "definition", "How do I form comparative adjectives?"),
    ("gram-en-a2-going-to-010", "vi", "semantic", "situation", "Tôi đã quyết định cuối tuần này sẽ đi Đà Lạt, nói thế nào bằng tiếng Anh?"),
    ("gram-en-a2-present-perfect-011", "en", "semantic", "situation", "How do I talk about my life experiences without saying when they happened?"),
    ("gram-en-b1-present-perfect-past-012", "vi", "terminology", "comparison", "Phân biệt thì hiện tại hoàn thành và quá khứ đơn."),
    ("gram-en-b1-modals-013", "en", "terminology", "comparison", "What is the difference between must and have to?"),
    ("gram-en-b1-first-conditional-014", "vi", "semantic", "situation", "Nếu ngày mai trời mưa, chúng tôi sẽ ở nhà — câu này dùng cấu trúc gì?"),
    ("gram-en-b1-relative-clauses-015", "en", "terminology", "comparison", "When do I use who, which or that?"),
    # expected = none: chủ đề không có trong corpus 33 bài
    (None, "vi", "terminology", "definition", "Cách dùng mệnh đề phân từ (participle clauses) như thế nào?"),
    (None, "vi", "terminology", "definition", "Câu điều kiện loại 3 dùng để làm gì?"),
    (None, "vi", "terminology", "comparison", "Phân biệt make và do."),
    (None, "vi", "semantic", "short_chat", "Đuôi -ed phát âm là /t/, /d/ hay /id/?"),
    (None, "vi", "terminology", "definition", "Đảo ngữ với never trong câu tiếng Anh dùng thế nào?"),
    (None, "en", "terminology", "definition", "How do I use the future perfect continuous?"),
    (None, "en", "semantic", "short_chat", "phrasal verbs with get?"),
    (None, "en", "semantic", "situation", "How should I end a formal email to my teacher?"),
    (None, "en", "terminology", "definition", "When do I use the subjunctive, as in 'I suggest that he go'?"),
    (None, "en", "terminology", "comparison", "What is the difference between affect and effect?"),
]


def stratified_split(queries: list[dict]) -> None:
    groups: dict[str, list[dict]] = defaultdict(list)
    for q in queries:
        groups[q["document_id"] or "none"].append(q)
    for items in groups.values():
        items.sort(key=lambda q: hashlib.sha256(f"{SEED}:{q['query_id']}".encode()).hexdigest())
        n_test = round(TEST_FRACTION * len(items))
        for i, q in enumerate(items):
            q["split"] = "test" if i < n_test else "dev"


def build() -> tuple[dict, dict]:
    v1 = json.loads((EVAL / "rag_queries_v1.json").read_text(encoding="utf-8"))
    old = [{**q, "expected": "document", "style": None, "author": "claude-week1", "from_v1": True} for q in v1]
    new = [{"query_id": f"rag-q2-{i:03d}", "query": text, "document_id": did, "expected": "document" if did else "none",
            "language": lang, "query_type": qtype, "style": style, "author": "claude-draft", "from_v1": False}
           for i, (did, lang, qtype, style, text) in enumerate(NEW, start=1)]
    stratified_split(new)
    queries = old + new
    counts = defaultdict(int)
    for q in queries:
        counts[q["split"]] += 1
    payload = {"version": "rag-queries-v2", "created": "2026-11-28", "status": "CHƯA DUYỆT BỞI NGƯỜI (truy vấn mới)",
               "queries": queries}
    manifest = {
        "version": "rag-queries-v2", "locked_at": "2026-11-28",
        "v1_queries": "Giữ nguyên query_id, câu, đáp án và split của rag_queries_v1.json (20 dev / 10 test).",
        "new_query_rule": (f"Trong mỗi nhóm đáp án (document_id hoặc 'none'), sắp theo sha256('{SEED}:' + query_id); "
                           f"round({TEST_FRACTION} × k) truy vấn đầu → test, còn lại → dev."),
        "seed": SEED, "test_fraction": TEST_FRACTION,
        "counts": dict(counts), "total": len(queries),
        "assigned_before_any_evaluation": True,
    }
    return payload, manifest


def main() -> None:
    payload, manifest = build()
    (EVAL / "rag_queries_v2.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (EVAL / "split_manifest_v2.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{manifest['total']} truy vấn: {manifest['counts']}")


if __name__ == "__main__":
    main()
