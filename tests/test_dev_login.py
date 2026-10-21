"""
The dev login bypass is a hole in the auth gate by design, so the
guarantees that matter are: it is OFF unless explicitly enabled, it
creates one fixed account, and that account cannot be logged into
through the real form.
"""
import pytest

from streamlit.testing.v1 import AppTest

import auth
import dev_login

DEV_USER = {"id": 99, "name": "Dev User", "email": "dev@vizgen.local"}


@pytest.fixture
def stub_backend(monkeypatch):
    import db
    import quota

    monkeypatch.setattr(db, "create_tables", lambda: None)
    monkeypatch.setattr(db, "get_user_dashboards", lambda uid: [])
    monkeypatch.setattr(db, "get_dashboard_by_token", lambda t: None)
    monkeypatch.setattr(quota, "count_api_calls_today", lambda uid: 0)
    monkeypatch.setattr(quota, "record_api_call", lambda uid: None)
    monkeypatch.setattr(dev_login, "get_dev_user", lambda: DEV_USER)


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " 1 "])
def test_enabled_by_truthy_values(monkeypatch, value):
    monkeypatch.setenv("VIZGEN_DEV_LOGIN", value)
    assert dev_login.enabled()


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "nope"])
def test_not_enabled_by_anything_else(monkeypatch, value):
    monkeypatch.setenv("VIZGEN_DEV_LOGIN", value)
    assert not dev_login.enabled()


def test_off_when_the_variable_is_absent():
    assert not dev_login.enabled()


def test_without_the_flag_the_login_gate_still_holds(stub_backend):
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception
    assert at.session_state["user"] is None
    assert "Email address" in [i.label for i in at.text_input]


def test_with_the_flag_the_login_form_is_skipped(
        stub_backend, monkeypatch):
    monkeypatch.setenv("VIZGEN_DEV_LOGIN", "1")
    at = AppTest.from_file("app.py", default_timeout=30).run()

    assert not at.exception
    assert at.session_state["user"]["email"] == "dev@vizgen.local"
    assert "Email address" not in [i.label for i in at.text_input]
    assert any("Welcome to VizGen" in t.value for t in at.title)


def test_dev_account_is_created_once_and_reused(monkeypatch):
    store = {}

    def get(email):
        return store.get(email)

    def create(name, email, pw_hash):
        store[email] = {"id": 1, "name": name, "email": email,
                        "password_hash": pw_hash}
        return True

    monkeypatch.setattr(dev_login, "get_user_by_email", get)
    monkeypatch.setattr(dev_login, "create_user", create)

    first = dev_login.get_dev_user()
    second = dev_login.get_dev_user()
    assert first is second
    assert len(store) == 1


def test_dev_account_cannot_be_logged_into_with_any_password():
    """No password may ever match the locked dev account."""
    locked = "!disabled"
    for attempt in ("", "!disabled", "password", "dev"):
        assert auth.verify_password(attempt, locked) is False


def test_malformed_hash_is_rejected_not_a_crash():
    assert auth.verify_password("x", "not-a-bcrypt-hash") is False
