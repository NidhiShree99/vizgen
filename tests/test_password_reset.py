"""
Password reset is an account-takeover path if it goes wrong, so the
boundaries get tested directly: tokens must be single-use, expiring,
unguessable, stored hashed, and useless once a reset has happened.
"""
from datetime import datetime, timedelta, timezone

import pytest

import password_reset as pr


class FakeStore:
    """In-memory stand-in for the password_resets table."""

    def __init__(self):
        self.users = {}
        self.resets = []
        self.passwords = {}

    # --- db shims -------------------------------------------------
    def get_user_by_email(self, email):
        return self.users.get(email)

    def create_password_reset(self, user_id, token_hash, expires_at):
        self.resets.append({
            "user_id": user_id, "token_hash": token_hash,
            "expires_at": expires_at, "used_at": None,
            "email": self._email_for(user_id),
        })

    def get_valid_password_reset(self, token_hash):
        now = datetime.now(timezone.utc)
        for row in self.resets:
            if (row["token_hash"] == token_hash
                    and row["used_at"] is None
                    and row["expires_at"] > now):
                return row
        return None

    def consume_password_reset(self, token_hash):
        for row in self.resets:
            if row["token_hash"] == token_hash:
                row["used_at"] = datetime.now(timezone.utc)

    def invalidate_password_resets(self, user_id):
        for row in self.resets:
            if row["user_id"] == user_id and row["used_at"] is None:
                row["used_at"] = datetime.now(timezone.utc)

    def update_user_password(self, email, password_hash):
        self.passwords[email] = password_hash

    def _email_for(self, user_id):
        for email, user in self.users.items():
            if user["id"] == user_id:
                return email
        return None


@pytest.fixture
def store(monkeypatch):
    s = FakeStore()
    s.users["real@test.com"] = {"id": 1, "email": "real@test.com"}

    for name in ("get_user_by_email", "create_password_reset",
                 "get_valid_password_reset", "consume_password_reset",
                 "invalidate_password_resets", "update_user_password"):
        monkeypatch.setattr(pr, name, getattr(s, name))
    return s


# --- issuing ------------------------------------------------------

def test_known_address_gets_a_token(store):
    assert pr.issue_token("real@test.com")


def test_unknown_address_gets_no_token(store):
    assert pr.issue_token("nobody@test.com") is None
    assert store.resets == []


def test_tokens_are_unguessable_and_unique(store):
    tokens = {pr.issue_token("real@test.com") for _ in range(20)}
    assert len(tokens) == 20
    assert all(len(t) >= 32 for t in tokens)


def test_raw_token_is_never_stored(store):
    token = pr.issue_token("real@test.com")
    stored = [row["token_hash"] for row in store.resets]
    assert token not in stored
    assert stored == [pr.hash_token(token)]


# --- verifying ----------------------------------------------------

def test_valid_token_verifies(store):
    token = pr.issue_token("real@test.com")
    assert pr.verify_token(token)


def test_unknown_token_is_rejected(store):
    pr.issue_token("real@test.com")
    assert pr.verify_token("not-a-real-token") is None


def test_empty_token_is_rejected(store):
    assert pr.verify_token("") is None
    assert pr.verify_token(None) is None


def test_expired_token_is_rejected(store):
    token = pr.issue_token("real@test.com")
    store.resets[0]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(minutes=1))
    assert pr.verify_token(token) is None


# --- completing ---------------------------------------------------

def test_completing_a_reset_sets_the_new_password(store):
    token = pr.issue_token("real@test.com")
    assert pr.complete_reset(token, "new-hash")
    assert store.passwords["real@test.com"] == "new-hash"


def test_token_cannot_be_reused(store):
    token = pr.issue_token("real@test.com")
    assert pr.complete_reset(token, "first-hash")
    assert not pr.complete_reset(token, "second-hash")
    assert store.passwords["real@test.com"] == "first-hash"


def test_expired_token_cannot_complete_a_reset(store):
    token = pr.issue_token("real@test.com")
    store.resets[0]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(hours=2))
    assert not pr.complete_reset(token, "new-hash")
    assert "real@test.com" not in store.passwords


def test_other_outstanding_links_die_with_the_reset(store):
    """An older link left in an inbox must not still work."""
    first = pr.issue_token("real@test.com")
    second = pr.issue_token("real@test.com")

    assert pr.complete_reset(second, "new-hash")
    assert not pr.complete_reset(first, "attacker-hash")
    assert store.passwords["real@test.com"] == "new-hash"


def test_garbage_token_cannot_complete_a_reset(store):
    pr.issue_token("real@test.com")
    assert not pr.complete_reset("garbage", "new-hash")
    assert store.passwords == {}
