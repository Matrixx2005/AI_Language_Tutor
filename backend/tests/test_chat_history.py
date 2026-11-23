from app.services.chat_history import StoredMessage, build_history


def u(text):
    return StoredMessage("user", text)


def a(text, status="ok"):
    return StoredMessage("assistant", text, status)


def contents(history):
    return [(m.role, m.content) for m in history]


def test_empty_history():
    assert build_history([], max_turns=10) == ()


def test_keeps_complete_turns_in_order():
    history = build_history([u("q1"), a("r1"), u("q2"), a("r2")], max_turns=10)
    assert contents(history) == [("user", "q1"), ("assistant", "r1"), ("user", "q2"), ("assistant", "r2")]


def test_cuts_to_last_n_turns():
    messages = []
    for i in range(1, 16):
        messages += [u(f"q{i}"), a(f"r{i}")]

    history = build_history(messages, max_turns=10)

    assert len(history) == 20
    assert history[0].content == "q6" and history[-1].content == "r15"


def test_exactly_n_turns_is_not_cut():
    messages = [m for i in range(3) for m in (u(f"q{i}"), a(f"r{i}"))]
    assert len(build_history(messages, max_turns=3)) == 6


def test_failed_turn_is_dropped_including_user_message():
    history = build_history([u("q1"), a("r1"), u("q2"), a("", status="error"), u("q3"), a("r3")], max_turns=10)
    assert contents(history) == [("user", "q1"), ("assistant", "r1"), ("user", "q3"), ("assistant", "r3")]


def test_failed_turns_do_not_count_toward_limit():
    messages = [u("q1"), a("r1"), u("q2"), a("", "error"), u("q3"), a("", "error"), u("q4"), a("r4")]
    assert contents(build_history(messages, max_turns=2)) == [
        ("user", "q1"), ("assistant", "r1"), ("user", "q4"), ("assistant", "r4"),
    ]


def test_unanswered_trailing_user_message_is_excluded():
    # Tin mới đang chờ trả lời được service thêm riêng ở cuối, không lấy từ lịch sử.
    assert contents(build_history([u("q1"), a("r1"), u("q2")], max_turns=10)) == [("user", "q1"), ("assistant", "r1")]


def test_orphan_assistant_message_is_ignored():
    assert build_history([a("r0"), u("q1"), a("r1")], max_turns=10)[0].content == "q1"


def test_zero_turns_sends_no_history():
    assert build_history([u("q1"), a("r1")], max_turns=0) == ()
