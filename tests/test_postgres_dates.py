"""
Postgres hands back real datetime objects, while this code was
written against SQLite, which returned strings. Slicing a datetime
(`value[:10]`) raises TypeError.

It slipped through because every test dashboard was an unpublished
draft: only a published dashboard has versions with a published_at,
and the crash took out the sidebar and the public share page.
"""
from datetime import datetime

import pytest
from streamlit.testing.v1 import AppTest

from ui.helpers import version_list_html

PUBLISHED = datetime(2026, 10, 20, 14, 30, 5)


def test_version_list_accepts_datetime_objects():
    html = version_list_html(
        [{"version_num": 1, "published_at": PUBLISHED}])
    assert "2026-10-20" in html


def test_version_list_still_accepts_string_dates():
    html = version_list_html(
        [{"version_num": 1, "published_at": "2026-10-20 14:30:05"}])
    assert "2026-10-20" in html


@pytest.fixture
def published_dashboard(monkeypatch):
    import db
    import owner
    import quota
    from ui import home, sidebar

    user = {"id": 1, "name": "Owner", "email": "o@test.com"}
    dash = {"id": 5, "name": "Live dash", "status": "published",
            "share_token": "tok123", "created_at": PUBLISHED,
            "user_id": 1}
    versions = [{"version_num": 1, "published_at": PUBLISHED,
                 "tiles_snapshot": "[]"}]

    monkeypatch.setattr(db, "create_tables", lambda: None)
    monkeypatch.setattr(owner, "get_owner", lambda: user)
    monkeypatch.setattr(quota, "count_api_calls_today", lambda u: 0)
    monkeypatch.setattr(quota, "record_api_call", lambda u: None)
    for mod in (home, sidebar):
        monkeypatch.setattr(mod, "get_user_dashboards", lambda u: [dash])
        monkeypatch.setattr(mod, "get_versions", lambda d: versions)
    monkeypatch.setattr(db, "get_dashboard_by_token", lambda t: dash)
    monkeypatch.setattr(db, "get_versions", lambda d: versions)
    monkeypatch.setattr(db, "get_dashboard_tiles", lambda d: [])
    return dash


def test_sidebar_renders_a_published_dashboard(published_dashboard):
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception


def test_public_share_page_renders_a_published_dashboard(
        published_dashboard, monkeypatch):
    from ui import share

    # share.py imports these by name, so patch them where used.
    monkeypatch.setattr(
        share, "get_dashboard_by_token", lambda t: published_dashboard)
    monkeypatch.setattr(
        share, "get_versions",
        lambda d: [{"version_num": 1, "published_at": PUBLISHED}])
    monkeypatch.setattr(share, "get_dashboard_tiles", lambda d: [])

    at = AppTest.from_file("app.py", default_timeout=30)
    at.query_params["share"] = "tok123"
    at.run()
    assert not at.exception
