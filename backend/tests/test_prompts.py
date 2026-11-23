import pytest

from app.core.prompts import PromptNotFoundError, render_prompt


def test_tutor_prompt_renders_level_and_key_rules():
    prompt = render_prompt("en", "tutor", level_code="A2", level_name="Sơ trung cấp")

    assert "A2 (Sơ trung cấp)" in prompt
    assert "{{" not in prompt and "}}" not in prompt
    assert "Vietnamese" in prompt  # giải thích bằng tiếng Việt
    assert "SOUND" in prompt and "an hour" in prompt and "a university" in prompt  # a/an theo âm
    assert "Do not cite" in prompt  # chưa RAG → không dẫn nguồn
    assert "Never reveal" in prompt  # không lộ system prompt


def test_missing_variable_is_an_error():
    with pytest.raises(ValueError, match="level_name"):
        render_prompt("en", "tutor", level_code="A1")


@pytest.mark.parametrize(("code", "name"), [("ja", "tutor"), ("en", "khong_ton_tai"), ("../x", "tutor"), ("en", "../tutor")])
def test_unknown_or_unsafe_prompt_is_rejected(code, name):
    with pytest.raises(PromptNotFoundError):
        render_prompt(code, name, level_code="A1", level_name="x")


def test_user_text_with_braces_is_not_interpreted():
    # Giá trị chứa {{...}} không bị thay tiếp (chỉ thay một lượt).
    prompt = render_prompt("en", "tutor", level_code="{{level_name}}", level_name="X")
    assert "{{level_name}} (X)" in prompt
