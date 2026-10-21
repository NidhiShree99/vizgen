"""
Ask Your Data.

The chat used st.chat_input, which docks to the bottom of the whole
page and was reported as "not working" because people couldn't tell
it was the input for that section. It is now a form with a visible
Ask button directly under the chat, and these tests drive it the way
a person would: type, press Ask, read the answer.
"""
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

USER = {"id": 1, "name": "Owner", "email": "o@test.com"}


@pytest.fixture
def chat_app(monkeypatch):
    import db
    import owner
    import quota
    from ui import home, sidebar
    from ui.builder import ai_tools

    spent = []
    monkeypatch.setattr(db, "create_tables", lambda: None)
    monkeypatch.setattr(owner, "get_owner", lambda: USER)
    # Anything that would reach the database is stubbed where it is used.
    for mod in (home, sidebar):
        monkeypatch.setattr(mod, "get_user_dashboards", lambda u: [])
    monkeypatch.setattr(db, "get_dashboard_tiles", lambda d: [])
    monkeypatch.setattr(db, "get_dashboard_by_token", lambda t: None)
    monkeypatch.setattr(quota, "count_api_calls_today", lambda u: 0)
    monkeypatch.setattr(quota, "record_api_call", lambda u: spent.append(u))

    calls = []

    def fake_answer(df, question, history):
        calls.append(question)
        return f"answer to: {question}"

    monkeypatch.setattr(ai_tools, "answer_data_question", fake_answer)

    df = pd.DataFrame({"region": ["N", "S"], "revenue": [1, 2]})
    at = AppTest.from_file("app.py", default_timeout=30)
    at.session_state["page"] = "builder"
    at.session_state["df"] = df
    at.session_state["datasets"] = {"s.csv": df}
    at.session_state["active_dataset"] = "s.csv"
    at.session_state["active_dataset_analyzed"] = "s.csv"
    at.session_state["schema_description"] = "A dataset."
    at.run()
    at.calls, at.spent = calls, spent
    return at


def ask(at, text):
    at.text_input(key="chat_question").set_value(text)
    return [b for b in at.button if b.label == "Ask"][0].click().run()


def test_chat_has_a_visible_ask_button_and_input(chat_app):
    assert not chat_app.exception
    assert [b for b in chat_app.button if b.label == "Ask"]
    assert "chat_question" in [t.key for t in chat_app.text_input]


def test_chat_no_longer_uses_the_page_pinned_chat_input(chat_app):
    assert len(chat_app.chat_input) == 0


def test_empty_chat_explains_what_to_do(chat_app):
    captions = " ".join(str(c.value) for c in chat_app.caption)
    assert "No questions yet" in captions


def test_asking_a_question_shows_the_answer(chat_app):
    at = ask(chat_app, "Which region is biggest?")
    assert not at.exception
    history = at.session_state["chat_history"]
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[1]["content"] == "answer to: Which region is biggest?"


def test_the_question_is_sent_to_the_model_once(chat_app):
    ask(chat_app, "Which region is biggest?")
    assert chat_app.calls == ["Which region is biggest?"]


def test_asking_spends_one_unit_of_quota(chat_app):
    ask(chat_app, "Which region is biggest?")
    assert len(chat_app.spent) == 1


def test_follow_up_questions_keep_the_conversation(chat_app):
    at = ask(chat_app, "first")
    at = ask(at, "second")
    roles = [m["role"] for m in at.session_state["chat_history"]]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_blank_question_is_refused_without_spending_quota(chat_app):
    at = ask(chat_app, "   ")
    assert at.session_state["chat_history"] == []
    assert chat_app.spent == []
    assert "Type a question first" in " ".join(
        str(w.value) for w in at.warning)


def test_a_model_failure_shows_an_error_and_keeps_history_paired(
        chat_app, monkeypatch):
    from ui.builder import ai_tools

    def boom(*a, **k):
        raise RuntimeError("api down")

    monkeypatch.setattr(ai_tools, "answer_data_question", boom)
    at = ask(chat_app, "anything")

    assert not at.exception
    assert at.session_state["chat_history"] == []
    assert "Couldn't get an answer" in " ".join(
        str(e.value) for e in at.error)


def test_over_quota_blocks_the_question(chat_app, monkeypatch):
    import quota
    monkeypatch.setattr(quota, "count_api_calls_today", lambda u: 100)

    at = ask(chat_app, "anything")
    assert chat_app.calls == []
    assert at.session_state["chat_history"] == []
    assert "Daily AI limit" in " ".join(str(e.value) for e in at.error)
