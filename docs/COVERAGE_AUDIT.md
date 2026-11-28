# Đối chiếu độ phủ corpus với CEFR-J Grammar Profile (Tuần 5B)

**Nguồn:** CEFR-J Grammar Profile, phiên bản 20180315. Bản quyền: Tono Laboratory, Tokyo University of Foreign Studies (TUFS).
Lấy từ Open Language Profiles: https://github.com/openlanguageprofiles/olp-en-cefrj (file `cefrj-grammar-profile-20180315.csv`).
**Điều khoản (theo README của kho):** dùng miễn phí cho nghiên cứu và thương mại, **phải trích dẫn**; CEFR-J và Open Language Profiles
không chịu trách nhiệm về sai sót. Bản grammar profile chỉ được dịch một phần từ bản tiếng Nhật.
Trích dẫn: *The CEFR-J Grammar Profile Version 20180315. Tono Laboratory, TUFS. Distributed by Open Language Profiles.*

**Cách dùng ở dự án:** CHỈ để đối chiếu độ phủ chủ đề và gợi ý mở rộng corpus. Không chép nội dung CEFR-J vào corpus. File CSV không
được commit (thư mục `data/external/` nằm trong `.gitignore`).

**Phương pháp:** 136 mục CEFR-J có cấp A1–B1 được ánh xạ sang bài học bằng 29 luật từ khóa trên mã và tên mục
(do Claude đặt; gần đúng — có thể khớp nhầm hoặc sót). Đây là GỢI Ý, chưa phải đánh giá của chuyên gia.

**Kết quả:** 106/136 mục khớp với ít nhất một bài học; **30 mục chưa phủ** (gợi ý mở rộng).

**Hạn chế đã biết:** 5 bài học có 0 mục khớp (there is/are, present perfect vs past simple, giới từ thời gian, câu điều kiện loại 2 và loại 0). Lý do là luật từ khóa được áp theo thứ tự và luật đứng trước (ví dụ luật về "be" hay "if") đã nhận mục đó trước. Con số 0 **không** có nghĩa là CEFR-J thiếu chủ đề này.

## Số mục CEFR-J khớp với từng bài học

| Bài học | Cấp | Số mục CEFR-J | Ví dụ mục |
| --- | --- | --- | --- |
| gram-en-a1-articles-003 | A1 | 5 | DEFINITE ARTICLES; INDEFINITE ARTICLES |
| gram-en-a1-be-001 | A1 | 16 | Are you ...?; BE to DO |
| gram-en-a1-can-ability-019 | A1 | 3 | FUNCTIONAL QUESTION: Can you ...?; MODAL/AUX: can |
| gram-en-a1-demonstratives-020 | A1 | 5 | These/Those N; This/That N |
| gram-en-a1-frequency-adverbs-021 | A1 | 1 | ADVERBS OF FREQUENCY: always/usually/oft |
| gram-en-a1-plurals-004 | A1 | 1 | -thing ADJ |
| gram-en-a1-possessives-018 | A1 | 3 | POSSESSIVE PRONOUNS (except for 'his' an; let's (not followed by 'not') |
| gram-en-a1-prepositions-place-017 | A1 | 2 | PREPOSITION STRANDING; PREPOSITIONS |
| gram-en-a1-prepositions-time-016 | A1 | 0 |  |
| gram-en-a1-present-simple-002 | A1 | 5 | TENSE/ASPECT: PRESENT (lexical verbs); TENSE/ASPECT: PRESENT (lexical verbs; th |
| gram-en-a1-there-be-005 | A1 | 0 |  |
| gram-en-a2-adverbs-manner-026 | A2 | 4 | ADVERBIAL CLAUSE: as; ADVERBIAL CLAUSE: when |
| gram-en-a2-comparatives-009 | A2 | 3 | COMPARATIVE OF SUPERIORITY: -er; COMPARATIVE OF SUPERIORITY: more+ADJ/ADV |
| gram-en-a2-count-noncount-008 | A2 | 1 | much UNCOUNTABLE NOUN |
| gram-en-a2-going-to-010 | A2 | 1 | MODAL/AUX: be going to |
| gram-en-a2-past-continuous-023 | A2 | 1 | TENSE/ASPECT: PAST PROGRESSIVE |
| gram-en-a2-past-simple-006 | A2 | 3 | TENSE/ASPECT: PRESENT (lexical verbs) |
| gram-en-a2-present-continuous-007 | A2 | 2 | TENSE/ASPECT: PRESENT PROGRESSIVE |
| gram-en-a2-present-perfect-011 | A2 | 2 | TENSE/ASPECT: PRESENT PERFECT |
| gram-en-a2-superlatives-022 | A2 | 2 | SUPERLATIVE OF SUPERIORITY: -est; SUPERLATIVE OF SUPERIORITY: most+ADJ/ADV |
| gram-en-a2-verb-patterns-025 | A2 | 13 | PARTICIPIAL CONSTRUCTION: PRESENT PARTIC; POSTMODIFYING PRESENT |
| gram-en-a2-will-future-024 | A2 | 4 | MODAL/AUX: will; TENSE/ASPECT: FUTURE |
| gram-en-b1-first-conditional-014 | B1 | 2 | ADVERBIAL CLAUSE: if; CONDITIONAL: SECOND |
| gram-en-b1-modals-013 | B1 | 11 | MODAL/AUX: could; MODAL/AUX: have to |
| gram-en-b1-passive-voice-028 | B1 | 4 | GET+PAST PARTICIPLE; PASSIVE: AUX |
| gram-en-b1-past-perfect-031 | B1 | 1 | TENSE/ASPECT: PAST PERFECT |
| gram-en-b1-present-perfect-past-012 | B1 | 0 |  |
| gram-en-b1-relative-clauses-015 | B1 | 7 | COMPOUND RELATIVE PRONOUN:; ELLIPTICAL ACCUSATIVE RELATIVE PRONOUN |
| gram-en-b1-reported-speech-029 | B1 | 2 | INDIRECT SPEECH: SAY/EXPLAIN/REPORT; INDIRECT SPEECH: TELL |
| gram-en-b1-second-conditional-027 | B1 | 0 |  |
| gram-en-b1-too-enough-032 | B1 | 1 | ADVERBS: INTENSIFIERS: extremely/greatly |
| gram-en-b1-used-to-030 | B1 | 1 | MODAL/AUX: used to |
| gram-en-b1-zero-conditional-033 | B1 | 0 |  |

## Mục CEFR-J A1–B1 chưa phủ (gợi ý mở rộng corpus)

| Mã | Mục ngữ pháp | Cấp CEFR-J |
| --- | --- | --- |
| `CC` | COORDINATING CONJUNCTIONS | A1.1 |
| `CL_after.etc` | SUBORDINATE CLAUSE: after/albeit/although/because/before/despite/except/for/lest/like/once/since/so/than/though/till/unless/until/where/whereas/wheresoever/whether/while/whilst tagged as IN | A1.1 |
| `DT.some.any` | DETERMINERS: some/any | A1.1 |
| `IMP.V.AFF` | IMPERATIVE: AFFIRMATIVE (lexical verbs) | A1.1 |
| `INT.how` | WH- QUESTION: How ...? | A1.1 |
| `INT.how_JJ.RB` | WH- QUESTION: How ADJ/ADV ...? | A1.1 |
| `INT.what` | WH- QUESTION: What ...? | A1.1 |
| `PPO` | me/us/him/her/them (except for 'you' and 'it') | A1.1 |
| `VP.SVO.AFF` | SENTENCE PATTERN: SUBJECT+V+OBJECT | A1.1 |
| `DT.no` | DETERMINER: no | A1.2 |
| `INT.why` | WH- QUESTION: Why ...? | A1.2 |
| `PIND.nobody.anything.etc` | INDEFINITE PRONOUNS | A1.2 |
| `VP.SVO.INT.AFF` | SENTENCE PATTERN: SUBJECT+V+OBJECT | A1.2 |
| `INT.where` | WH- QUESTION: Where ...? | A1.3 |
| `VN.N_VN` | POSTMODIFYING PAST PARTICIPLE | A1.3 |
| `VN.VN_N` | PREMODIFYING PAST PARTICIPLE | A1.3 |
| `CAUS.have.let.make` | HAVE/LET/MAKE+NP+INFINITIVE | A2.1 |
| `DT.another` | DETERMINER: another | A2.1 |
| `INDQ.know.etc` | INDIRECT QUESTION: DECIDE/EXPLAIN/KNOW/LEARN/SEE/UNDERSTAND/WONDER | A2.1 |
| `PIND.ones` | INDEFINITE PRONOUN/PROP-WORDS: ones (except for 'one') | A2.1 |
| `VP.SVO.NEG` | SENTENCE PATTERN: SUBJECT+V+OBJECT | A2.1 |
| `CAUS.ask.tell_NP_to_do` | ASK/TELL+NP+to+INFINITIVE | B1.1 |
| `CL.WH.OBJ` | know/wonder+WH-(CLAUSE) (except for 'whether') | B1.1 |
| `EX.here.AFF` | here is/are | B1.1 |
| `IMP.V.NEG` | IMPERATIVE: AFFIRMATIVE (lexical verbs) | B1.1 |
| `INDQ.ask.etc` | INDIRECT QUESTION: ASK/REMIND/SHOW/TEACH/TELL | B1.1 |
| `P.others` | PRONOUN: others (excluding 'the | B1.1 |
| `PREFL.oneself.etc` | REFLEXIVE PRONOUNS | B1.1 |
| `PREF.each_other` | RECIPROCAL PRONOUN: each other | B1.2 |
| `VP.SV.AFF` | SENTENCE PATTERN: SUBJECT+V | B1.2 |
