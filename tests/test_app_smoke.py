"""
End-to-end smoke tests that actually execute app.py headlessly via
Streamlit's AppTest, with the database and Claude API stubbed out.

These are the safety net for refactoring app.py: they catch broken
imports, bad session-state wiring, and pages that stop rendering —
the kinds of breakage unit tests on the helper modules cannot see.
"""
import pytest

from streamlit.testing.v1 import AppTest

APP = "app.py"
TIMEOUT = 30


@pytest.fixture
def stub_backend(monkeypatch):
    """Neutralise every external dependency app.py touches."""
    import db
    import quota

    monkeypatch.setattr(db, "create_tables", lambda: None)
    monkeypatch.setattr(db, "get_user_dashboards", lambda uid: [])
    monkeypatch.setattr(db, "get_versions", lambda did: [])
    monkeypatch.setattr(db, "get_dashboard_tiles", lambda did: [])
    monkeypatch.setattr(
        db, "get_dashboard_prompt_history", lambda did, limit=30: [])
    monkeypatch.setattr(db, "get_dashboard_by_token", lambda t: None)
    monkeypatch.setattr(db, "get_dashboard_by_id", lambda d: None)
    monkeypatch.setattr(db, "count_api_calls_today", lambda uid: 0)
    monkeypatch.setattr(db, "record_api_call", lambda uid: None)
    monkeypatch.setattr(quota, "count_api_calls_today", lambda uid: 0)
    monkeypatch.setattr(quota, "record_api_call", lambda uid: None)


def run_app(**session):
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    for key, value in session.items():
        at.session_state[key] = value
    return at.run()


def test_app_starts_without_error(stub_backend):
    at = run_app()
    assert not at.exception


def test_logged_out_user_sees_the_login_form(stub_backend):
    at = run_app()
    labels = [i.label for i in at.text_input]
    assert "Email address" in labels
    assert "Password" in labels


def test_logged_out_user_cannot_see_the_dashboard_ui(stub_backend):
    """The auth gate must stop the app before any dashboard chrome."""
    at = run_app()
    assert [s.value for s in at.subheader] == []
    assert not [b for b in at.button if "New Dashboard" in b.label]


def test_login_and_signup_tabs_are_both_offered(stub_backend):
    at = run_app()
    assert len(at.tabs) >= 2


def test_forgot_password_is_reachable_from_login(stub_backend):
    at = run_app()
    labels = [b.label for b in at.button]
    assert any("Forgot password" in label for label in labels)


# --- logged-in surface ---

USER = {"id": 1, "name": "Test User", "email": "t@test.com"}


def test_logged_in_user_reaches_the_home_page(stub_backend):
    at = run_app(user=USER)
    assert not at.exception
    assert any("Welcome to VizGen" in t.value for t in at.title)


def test_sidebar_shows_the_signed_in_user(stub_backend):
    at = run_app(user=USER)
    captions = " ".join(str(c.value) for c in at.sidebar.caption)
    assert "Test User" in captions


def test_sidebar_reports_ai_quota_usage(stub_backend):
    at = run_app(user=USER)
    captions = " ".join(str(c.value) for c in at.sidebar.caption)
    assert "AI usage" in captions
    assert "0/100" in captions


def test_builder_page_renders_the_data_source_step(stub_backend):
    at = run_app(user=USER, page="builder")
    assert not at.exception
    assert any("Data Source" in s.value for s in at.subheader)


def test_builder_without_data_hides_the_ai_tools(stub_backend):
    """Chat/forecast/optimize only make sense once data is loaded."""
    at = run_app(user=USER, page="builder")
    headings = " ".join(s.value for s in at.subheader)
    assert "Ask Your Data" not in headings
    assert "Forecast" not in headings
    assert "Optimize" not in headings


def _loaded_dataset():
    import pandas as pd
    return pd.DataFrame({
        "region": ["North", "South", "East", "West"],
        "revenue": [45000, 32000, 67000, 28000],
        "month": ["2024-01-01", "2024-02-01",
                  "2024-03-01", "2024-04-01"],
    })


def test_builder_with_data_renders_every_ai_tool(stub_backend):
    """
    Exercises the builder modules that only appear once a dataset is
    loaded — chat, forecast and optimize each live in their own
    module, so this is what catches a broken split.
    """
    df = _loaded_dataset()
    at = run_app(
        user=USER,
        page="builder",
        df=df,
        datasets={"sample.csv": df},
        active_dataset="sample.csv",
        active_dataset_analyzed="sample.csv",
        schema_description="A test dataset.",
    )
    assert not at.exception

    headings = " ".join(s.value for s in at.subheader)
    for section in ("Ask Your Data", "Forecast", "Optimize",
                    "Business Use Case Mode", "Add a Chart"):
        assert section in headings, f"{section} did not render"


def test_builder_with_data_renders_the_tile_canvas(stub_backend):
    """Canvas lives in its own module and only shows with tiles."""
    df = _loaded_dataset()
    from charts import build_chart

    config = {"chart_type": "bar", "x": "region", "y": "revenue",
              "title": "Revenue by Region"}
    tile = {"prompt": "revenue by region", "config": config,
            "fig": build_chart(df, config, 0), "width": "half",
            "height": 320, "dataset_name": "sample.csv"}

    at = run_app(
        user=USER,
        page="builder",
        df=df,
        datasets={"sample.csv": df},
        active_dataset="sample.csv",
        active_dataset_analyzed="sample.csv",
        schema_description="A test dataset.",
        tiles=[tile],
    )
    assert not at.exception
    captions = " ".join(str(c.value) for c in at.caption)
    assert "tile(s) on canvas" in captions


def test_logging_out_returns_to_the_login_form(stub_backend):
    at = run_app(user=USER)
    logout = [b for b in at.sidebar.button if "Log out" in b.label]
    assert logout, "no log out control in the sidebar"

    at = logout[0].click().run()
    assert not at.exception
    assert at.session_state["user"] is None
