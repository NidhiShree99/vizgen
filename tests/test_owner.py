"""
With login removed, the whole app runs as one owner account. It has
to be created once, reused after, and carry no usable password.
"""
import owner


def _store(monkeypatch):
    users = {}

    def get(email):
        return users.get(email)

    def create(name, email, pw_hash):
        users[email] = {"id": 7, "name": name, "email": email,
                        "password_hash": pw_hash}
        return True

    monkeypatch.setattr(owner, "get_user_by_email", get)
    monkeypatch.setattr(owner, "create_user", create)
    return users


def test_owner_is_created_on_first_use(monkeypatch):
    users = _store(monkeypatch)
    user = owner.get_owner()
    assert user["email"] == owner.OWNER_EMAIL
    assert list(users) == [owner.OWNER_EMAIL]


def test_owner_is_reused_not_duplicated(monkeypatch):
    users = _store(monkeypatch)
    first = owner.get_owner()
    second = owner.get_owner()
    assert first is second
    assert len(users) == 1


def test_an_existing_account_is_adopted_not_recreated(monkeypatch):
    """The owner's existing dashboards must stay attached to them."""
    users = _store(monkeypatch)
    users[owner.OWNER_EMAIL] = {"id": 9, "name": "Existing",
                                "email": owner.OWNER_EMAIL,
                                "password_hash": "real-hash"}
    user = owner.get_owner()
    assert user["id"] == 9
    assert user["password_hash"] == "real-hash"
