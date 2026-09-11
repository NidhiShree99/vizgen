"""
Guards the multi-tenant boundary: one user must never be able to
read, rename, publish, or delete another user's dashboard.

These assert on the SQL actually issued, so dropping a `user_id`
clause during a refactor fails loudly instead of silently exposing
every user's data to everyone.
"""
import db

OWNER = 7
ATTACKER = 99
DASHBOARD = 42


def test_dashboard_listing_is_scoped_to_the_user(fake_db):
    fake_db.queue([])
    db.get_user_dashboards(OWNER)

    sql, params = fake_db.calls[0]
    assert "WHERE user_id = %s" in sql
    assert OWNER in params


def test_rename_is_scoped_to_the_owner(fake_db):
    db.update_dashboard_name(DASHBOARD, "New name", OWNER)

    sql, params = fake_db.calls[0]
    assert "user_id = %s" in sql
    assert OWNER in params
    assert DASHBOARD in params


def test_publish_is_scoped_to_the_owner(fake_db):
    db.update_dashboard_publish(DASHBOARD, "tok123", OWNER)

    sql, params = fake_db.calls[0]
    assert "user_id = %s" in sql
    assert OWNER in params


def test_delete_checks_ownership_before_touching_anything(fake_db):
    # First statement must be the ownership lookup.
    fake_db.queue({"id": DASHBOARD})
    db.delete_dashboard(DASHBOARD, OWNER)

    first_sql, first_params = fake_db.calls[0]
    assert first_sql.startswith("SELECT")
    assert "user_id = %s" in first_sql
    assert OWNER in first_params


def test_delete_by_a_non_owner_deletes_nothing(fake_db):
    # No row comes back from the ownership check -> not the owner.
    fake_db.queue(None)
    db.delete_dashboard(DASHBOARD, ATTACKER)

    deletes = fake_db.sql_containing("DELETE")
    assert deletes == [], (
        "a non-owner triggered DELETE statements: " + str(deletes))


def test_delete_by_the_owner_removes_dashboard_and_children(fake_db):
    fake_db.queue({"id": DASHBOARD})
    db.delete_dashboard(DASHBOARD, OWNER)

    deleted_from = " ".join(fake_db.sql_containing("DELETE"))
    for table in ("prompt_history", "tiles",
                  "dashboard_versions", "dashboards"):
        assert table in deleted_from, f"{table} rows were orphaned"


def test_new_dashboards_are_stamped_with_their_owner(fake_db):
    fake_db.queue({"id": 1})
    db.save_dashboard("My dash", OWNER)

    sql, params = fake_db.calls[0]
    assert "user_id" in sql
    assert OWNER in params


def test_share_token_lookup_is_public_by_design(fake_db):
    """Published dashboards are viewable without a login."""
    fake_db.queue({"id": DASHBOARD})
    db.get_dashboard_by_token("tok123")

    sql, _ = fake_db.calls[0]
    assert "share_token = %s" in sql
    assert "user_id" not in sql
