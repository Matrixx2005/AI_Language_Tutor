# Duyệt bộ đánh giá truy xuất v2 (Tuần 5A)

File: `data/evaluation/rag_queries_v2.json`, manifest `split_manifest_v2.json`, script tạo `scripts/build_eval_v2.py` (tất định). Validator: `python scripts/validate_evaluation.py`.

**Thành phần:**
- 109 truy vấn: 30 truy vấn v1 **giữ nguyên** (file v1 và `split_manifest.json` không sửa) và 79 truy vấn mới (`author: claude-draft`).
- 78 dev / 31 test. Tiếng Việt 55 / tiếng Anh 54; thuật ngữ 53 / theo nghĩa 56.
- Mỗi bài trong 33 bài có 2–4 truy vấn: bài mới có 3; một số bài cũ chỉ có 2 vì bộ v1 phân bố không đều.
- 10 truy vấn `expected = none` (chủ đề không có trong corpus).

**Chống rò rỉ:**
- Truy vấn mới soạn **chỉ từ tiêu đề, chủ đề và cấp độ** của bài, không chép câu trong nội dung.
- Kiểu hỏi đa dạng: định nghĩa, tình huống, lỗi cần sửa, so sánh, câu chat ngắn.
- Hạn chế còn lại: người soạn (Claude) đã đọc nội dung bài khi soạn corpus ở Tuần 4, nên vẫn có thể vô tình dùng cách diễn đạt giống bài. Đây là lý do cần thêm truy vấn do người viết.

**Chia dev/test:**
- Thực hiện **trước** mọi lần đánh giá, theo quy tắc ghi trong manifest.
- Trong mỗi nhóm đáp án (document_id hoặc `none`), sắp các truy vấn theo `sha256("rag-v2-2026-11-28:" + query_id)`; `round(0,3 × k)` truy vấn đầu → test, còn lại → dev.
- 30 truy vấn v1 giữ split cũ.
- Test split **chưa chạy**: script đánh giá từ chối, giao diện không hiển thị.

## Truy vấn do người viết (cần tối thiểu 30) — chờ người dùng bổ sung

Thêm vào danh sách `NEW` trong `scripts/build_eval_v2.py`, hoặc gửi Claude theo mẫu: câu hỏi · document_id (hoặc none) · vi/en · terminology/semantic. Mỗi truy vấn mới có `author: "human"` và split tính theo cùng quy tắc băm. Viết **trước khi** xem kết quả đánh giá.

| # | Truy vấn | document_id | Ngôn ngữ | Loại | Ghi chú |
| --- | --- | --- | --- | --- | --- |
| 1 | | | | | |
| … | | | | | |
| 30 | | | | | |

## Truy vấn mới do Claude soạn (79) — trạng thái

| query_id | Truy vấn | Đáp án | Ngôn ngữ | Loại | Kiểu | Split | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `rag-q2-001` | Giới từ chỉ thời gian in, on, at khác nhau thế nào? | gram-en-a1-prepositions-time-016 | vi | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-002` | I'm writing about my birthday party. Do I put in, on or at before the date? | gram-en-a1-prepositions-time-016 | en | semantic | situation | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-003` | Câu 'I will meet you on next Friday' sai ở đâu? | gram-en-a1-prepositions-time-016 | vi | semantic | error_fix | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-004` | What are the prepositions of place in, on and at used for? | gram-en-a1-prepositions-place-017 | en | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-005` | Muốn nói cái điện thoại nằm trên mặt bàn thì dùng giới từ nào? | gram-en-a1-prepositions-place-017 | vi | semantic | situation | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-006` | in the airport or at the airport? | gram-en-a1-prepositions-place-017 | en | semantic | short_chat | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-007` | Tính từ sở hữu và sở hữu cách 's dùng thế nào? | gram-en-a1-possessives-018 | vi | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-008` | How do I say that the laptop belongs to my sister? | gram-en-a1-possessives-018 | en | semantic | situation | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-009` | Viết 'the house of Minh' có tự nhiên không? | gram-en-a1-possessives-018 | vi | semantic | error_fix | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-010` | How is the modal can used to talk about ability? | gram-en-a1-can-ability-019 | en | terminology | definition | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-011` | Muốn khoe 'Tôi biết chơi đàn guitar' bằng tiếng Anh thì dùng cấu trúc gì? | gram-en-a1-can-ability-019 | vi | semantic | situation | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-012` | Is 'She cans play piano' correct? | gram-en-a1-can-ability-019 | en | semantic | error_fix | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-013` | Phân biệt this, that, these và those. | gram-en-a1-demonstratives-020 | vi | terminology | comparison | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-014` | I'm pointing at some books far away from me. Which word should I use? | gram-en-a1-demonstratives-020 | en | semantic | situation | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-015` | Khi nhấc điện thoại, giới thiệu mình là ai thì nói thế nào? | gram-en-a1-demonstratives-020 | vi | semantic | situation | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-016` | Where do adverbs of frequency go in a sentence? | gram-en-a1-frequency-adverbs-021 | en | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-017` | Muốn nói 'tôi hiếm khi uống trà' thì đặt từ chỉ mức độ thường xuyên ở đâu? | gram-en-a1-frequency-adverbs-021 | vi | semantic | situation | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-018` | What's wrong with 'He goes usually to work by bus'? | gram-en-a1-frequency-adverbs-021 | en | semantic | error_fix | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-019` | So sánh nhất của tính từ được tạo như thế nào? | gram-en-a2-superlatives-022 | vi | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-020` | Can I say 'Lan is the most tall student in my class'? | gram-en-a2-superlatives-022 | en | semantic | error_fix | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-021` | Muốn nói 'hôm nay là ngày tệ nhất của tôi' thì dùng dạng nào của bad? | gram-en-a2-superlatives-022 | vi | semantic | situation | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-022` | How is the past continuous formed? | gram-en-a2-past-continuous-023 | en | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-023` | Muốn kể 'lúc 9 giờ tối qua tôi đang xem phim' thì dùng thì gì? | gram-en-a2-past-continuous-023 | vi | semantic | situation | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-024` | Một hành động đang kéo dài trong quá khứ thì bị một việc khác chen ngang, chia động từ thế nào? | gram-en-a2-past-continuous-023 | vi | semantic | situation | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-025` | Thì tương lai đơn với will dùng khi nào? | gram-en-a2-will-future-024 | vi | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-026` | Someone knocks on the door and I decide right now to open it. What do I say? | gram-en-a2-will-future-024 | en | semantic | situation | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-027` | Is 'I will to call you tomorrow' correct? | gram-en-a2-will-future-024 | en | semantic | error_fix | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-028` | Which verbs are followed by a gerund and which by a to-infinitive? | gram-en-a2-verb-patterns-025 | en | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-029` | Nói 'Tôi muốn học tiếng Anh' thì là want learning hay want to learn? | gram-en-a2-verb-patterns-025 | vi | semantic | short_chat | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-030` | Câu 'She enjoys to cook' có đúng không? | gram-en-a2-verb-patterns-025 | vi | semantic | error_fix | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-031` | Trạng từ chỉ cách thức được tạo thế nào? | gram-en-a2-adverbs-manner-026 | vi | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-032` | Is it 'she sings beautiful' or 'she sings beautifully'? | gram-en-a2-adverbs-manner-026 | en | semantic | error_fix | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-033` | adverb form of good? | gram-en-a2-adverbs-manner-026 | en | terminology | short_chat | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-034` | How do I form the second conditional? | gram-en-b1-second-conditional-027 | en | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-035` | Muốn khuyên bạn 'nếu tôi là bạn thì tôi sẽ đi khám bác sĩ' thì dùng cấu trúc gì? | gram-en-b1-second-conditional-027 | vi | semantic | situation | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-036` | Nói về một điều không có thật ở hiện tại, như tưởng tượng mình trúng xổ số, thì chia động từ thế nào? | gram-en-b1-second-conditional-027 | vi | semantic | situation | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-037` | Câu bị động ở thì hiện tại đơn có cấu trúc gì? | gram-en-b1-passive-voice-028 | vi | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-038` | How do I say that someone stole my bike yesterday without saying who did it? | gram-en-b1-passive-voice-028 | en | semantic | situation | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-039` | When should I add by plus the person in a passive sentence? | gram-en-b1-passive-voice-028 | en | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-040` | How do tenses change in reported speech? | gram-en-b1-reported-speech-029 | en | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-041` | Bạn tôi nói 'I am hungry'. Kể lại lời bạn ấy thì viết thế nào? | gram-en-b1-reported-speech-029 | vi | semantic | situation | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-042` | Khi kể lại lời người khác, khi nào dùng say và khi nào dùng tell? | gram-en-b1-reported-speech-029 | vi | terminology | comparison | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-043` | Cấu trúc used to diễn tả điều gì? | gram-en-b1-used-to-030 | vi | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-044` | I lived in Hue as a child but I don't now. How can I say this in one sentence? | gram-en-b1-used-to-030 | en | semantic | situation | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-045` | What's the difference between 'used to do' and 'be used to doing'? | gram-en-b1-used-to-030 | en | terminology | comparison | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-046` | When do we use the past perfect tense? | gram-en-b1-past-perfect-031 | en | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-047` | Khi tôi đến rạp thì phim đã bắt đầu rồi — vế 'phim đã bắt đầu' chia thì gì? | gram-en-b1-past-perfect-031 | vi | semantic | situation | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-048` | Thì quá khứ hoàn thành được tạo như thế nào? | gram-en-b1-past-perfect-031 | vi | terminology | definition | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-049` | Vị trí của too và enough trong câu? | gram-en-b1-too-enough-032 | vi | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-050` | The bag is so heavy that I can't carry it. How do I say this with 'too'? | gram-en-b1-too-enough-032 | en | semantic | situation | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-051` | Is 'He is enough old to drive' correct? | gram-en-b1-too-enough-032 | en | semantic | error_fix | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-052` | What is the zero conditional used for? | gram-en-b1-zero-conditional-033 | en | terminology | definition | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-053` | Nói một sự thật luôn đúng như 'nếu đun nước đủ nóng thì nước sôi' thì dùng cấu trúc gì? | gram-en-b1-zero-conditional-033 | vi | semantic | situation | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-054` | Câu điều kiện nói về điều luôn đúng khác câu điều kiện loại 1 thế nào? | gram-en-b1-zero-conditional-033 | vi | terminology | comparison | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-055` | Is 'They is my friends' correct? | gram-en-a1-be-001 | en | semantic | error_fix | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-056` | Câu 'My father work in a bank' sai chỗ nào? | gram-en-a1-present-simple-002 | vi | semantic | error_fix | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-057` | When do I use the definite article the? | gram-en-a1-articles-003 | en | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-058` | Danh từ tận cùng bằng -y đổi sang số nhiều thế nào? | gram-en-a1-plurals-004 | vi | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-059` | How do I tell a visitor that a park exists near my house? | gram-en-a1-there-be-005 | en | semantic | situation | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-060` | Động từ bất quy tắc ở thì quá khứ đơn là gì? | gram-en-a2-past-simple-006 | vi | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-061` | which tense for something happening right now? | gram-en-a2-present-continuous-007 | en | semantic | short_chat | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-062` | Hỏi lượng sữa còn lại thì dùng how much hay how many? | gram-en-a2-count-noncount-008 | vi | semantic | short_chat | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-063` | How do I form comparative adjectives? | gram-en-a2-comparatives-009 | en | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-064` | Tôi đã quyết định cuối tuần này sẽ đi Đà Lạt, nói thế nào bằng tiếng Anh? | gram-en-a2-going-to-010 | vi | semantic | situation | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-065` | How do I talk about my life experiences without saying when they happened? | gram-en-a2-present-perfect-011 | en | semantic | situation | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-066` | Phân biệt thì hiện tại hoàn thành và quá khứ đơn. | gram-en-b1-present-perfect-past-012 | vi | terminology | comparison | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-067` | What is the difference between must and have to? | gram-en-b1-modals-013 | en | terminology | comparison | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-068` | Nếu ngày mai trời mưa, chúng tôi sẽ ở nhà — câu này dùng cấu trúc gì? | gram-en-b1-first-conditional-014 | vi | semantic | situation | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-069` | When do I use who, which or that? | gram-en-b1-relative-clauses-015 | en | terminology | comparison | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-070` | Cách dùng mệnh đề phân từ (participle clauses) như thế nào? | — (none) | vi | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-071` | Câu điều kiện loại 3 dùng để làm gì? | — (none) | vi | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-072` | Phân biệt make và do. | — (none) | vi | terminology | comparison | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-073` | Đuôi -ed phát âm là /t/, /d/ hay /id/? | — (none) | vi | semantic | short_chat | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-074` | Đảo ngữ với never trong câu tiếng Anh dùng thế nào? | — (none) | vi | terminology | definition | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-075` | How do I use the future perfect continuous? | — (none) | en | terminology | definition | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-076` | phrasal verbs with get? | — (none) | en | semantic | short_chat | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-077` | How should I end a formal email to my teacher? | — (none) | en | semantic | situation | dev | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-078` | When do I use the subjunctive, as in 'I suggest that he go'? | — (none) | en | terminology | definition | test | CHƯA DUYỆT BỞI NGƯỜI |
| `rag-q2-079` | What is the difference between affect and effect? | — (none) | en | terminology | comparison | dev | CHƯA DUYỆT BỞI NGƯỜI |
