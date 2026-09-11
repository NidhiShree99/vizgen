import db
from auth import hash_password, verify_password


def test_password_is_never_stored_in_plain_text():
    stored = hash_password("hunter2")
    assert "hunter2" not in stored
    assert stored.startswith("$2b$")


def test_correct_password_verifies():
    assert verify_password("hunter2", hash_password("hunter2"))


def test_wrong_password_is_rejected():
    assert not verify_password("wrong", hash_password("hunter2"))


def test_same_password_hashes_differently_each_time():
    """Per-password salting: identical passwords must not collide."""
    assert hash_password("same") != hash_password("same")


def test_verification_is_case_sensitive():
    assert not verify_password("HUNTER2", hash_password("hunter2"))


def test_duplicate_signup_is_reported_not_raised(fake_db, monkeypatch):
    import psycopg2

    class Boom:
        def cursor(self):
            return self

        def execute(self, *a, **k):
            raise psycopg2.errors.UniqueViolation()

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(db, "get_connection", lambda: Boom())
    assert db.create_user("A", "taken@test.com", "hash") is False


def test_password_reset_updates_by_email(fake_db):
    db.update_user_password("user@test.com", "new-hash")

    sql, params = fake_db.calls[0]
    assert "UPDATE users SET password_hash" in sql
    assert "WHERE email = %s" in sql
    assert "new-hash" in params
