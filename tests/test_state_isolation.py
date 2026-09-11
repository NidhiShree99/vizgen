"""
Session state must not leak between sessions.

DEFAULTS lives for the life of the process. If a mutable default
(tiles, datasets, chat_history) were handed out by reference, one
user appending a tile would mutate the shared default and every
session started afterwards would inherit their data.
"""
import ui.state as state

MUTABLE_KEYS = ["tiles", "datasets", "chat_history"]


class FakeSessionState(dict):
    """Minimal stand-in for st.session_state."""

    def __contains__(self, key):
        return dict.__contains__(self, key)


def _init(monkeypatch):
    session = FakeSessionState()
    monkeypatch.setattr(state.st, "session_state", session)
    state.init_session_state()
    return session


def test_mutating_one_session_does_not_touch_the_defaults(monkeypatch):
    session = _init(monkeypatch)

    session["tiles"].append({"config": {"chart_type": "bar"}})
    session["chat_history"].append({"role": "user", "content": "hi"})
    session["datasets"]["sales.csv"] = object()

    assert state.DEFAULTS["tiles"] == []
    assert state.DEFAULTS["chat_history"] == []
    assert state.DEFAULTS["datasets"] == {}


def test_a_later_session_starts_clean(monkeypatch):
    first = _init(monkeypatch)
    first["tiles"].append({"config": {"chart_type": "bar"}})
    first["chat_history"].append({"role": "user", "content": "hi"})

    second = _init(monkeypatch)

    assert second["tiles"] == []
    assert second["chat_history"] == []


def test_sessions_do_not_share_mutable_objects(monkeypatch):
    first = _init(monkeypatch)
    second = _init(monkeypatch)

    for key in MUTABLE_KEYS:
        assert first[key] is not second[key], (
            f"{key} is shared between sessions")


def test_existing_values_are_not_overwritten(monkeypatch):
    session = FakeSessionState()
    session["page"] = "builder"
    monkeypatch.setattr(state.st, "session_state", session)

    state.init_session_state()

    assert session["page"] == "builder"
