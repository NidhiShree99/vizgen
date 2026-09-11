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


def _builder_with_data(**extra):
    df = _loaded_dataset()
    return run_app(
        user=USER,
        page="builder",
        df=df,
        datasets={"sample.csv": df},
        active_dataset="sample.csv",
        active_dataset_analyzed="sample.csv",
        schema_description="A test dataset.",
        **extra,
    )


def test_forecast_result_can_be_added_to_the_dashboard(stub_backend):
    """
    A forecast used to render and vanish. It must now be promotable
    to a real tile so it survives save, publish and PDF export.
    """
    from forecasting import generate_forecast

    result = generate_forecast(
        _loaded_dataset(), "month", "revenue", 2)
    result.update({"time_column": "month",
                   "value_column": "revenue",
                   "periods": 2,
                   "description": "revenue forecast"})

    at = _builder_with_data(forecast_result=result)
    assert not at.exception
    assert at.session_state["tiles"] == []

    add = [b for b in at.button
           if "Add forecast to dashboard" in b.label]
    assert add, "no control to keep the forecast"

    at = add[0].click().run()
    assert not at.exception

    tiles = at.session_state["tiles"]
    assert len(tiles) == 1
    assert tiles[0]["config"]["chart_type"] == "forecast"
    assert tiles[0]["config"]["time_column"] == "month"
    assert tiles[0]["config"]["periods"] == 2


def test_allocation_result_can_be_added_to_the_dashboard(stub_backend):
    from optimizer import optimize_budget_allocation

    result = optimize_budget_allocation(
        _loaded_dataset(), "region", "revenue", 80000)
    result["description"] = "allocate $80,000 across regions"

    at = _builder_with_data(optimize_result=result)
    assert not at.exception

    add = [b for b in at.button
           if "Add allocation to dashboard" in b.label]
    assert add, "no control to keep the allocation"

    at = add[0].click().run()
    assert not at.exception

    tiles = at.session_state["tiles"]
    assert len(tiles) == 1
    assert tiles[0]["config"]["chart_type"] == "allocation"
    assert tiles[0]["config"]["total_budget"] == 80000


def test_adding_an_analytical_tile_marks_the_summary_stale(stub_backend):
    """Adding a tile changes the dashboard, so the AI summary ages."""
    from optimizer import optimize_budget_allocation

    result = optimize_budget_allocation(
        _loaded_dataset(), "region", "revenue", 80000)
    at = _builder_with_data(
        optimize_result=result,
        dashboard_insight={"holistic_summary": "old"},
    )
    add = [b for b in at.button
           if "Add allocation to dashboard" in b.label]
    at = add[0].click().run()
    assert at.session_state["insight_stale"] is True


def test_reset_flow_is_closed_without_mail_credentials(
        stub_backend, monkeypatch):
    """
    With no email sender configured the reset form must refuse to
    reset anything, rather than falling back to the old flow where
    knowing an address was enough to take over the account.
    """
    import mailer
    monkeypatch.setattr(mailer, "_secret", lambda name: None)

    at = run_app(show_reset=True)
    assert not at.exception

    warnings = " ".join(str(w.value) for w in at.warning)
    assert "isn't available" in warnings

    labels = [b.label for b in at.button]
    assert not any("Send reset link" in label for label in labels)


def test_reset_form_is_offered_when_mail_is_configured(
        stub_backend, monkeypatch):
    import mailer
    monkeypatch.setattr(mailer, "_secret", lambda name: "configured")

    at = run_app(show_reset=True)
    assert not at.exception

    labels = [b.label for b in at.button]
    assert any("Send reset link" in label for label in labels)


def test_invalid_reset_link_is_refused(stub_backend, monkeypatch):
    # auth.py did `from password_reset import verify_token`, so the
    # name has to be patched where it is used, not where it is defined.
    import auth
    monkeypatch.setattr(auth, "verify_token", lambda token: None)

    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.query_params["reset"] = "bogus-token"
    at.run()

    assert not at.exception
    errors = " ".join(str(e.value) for e in at.error)
    assert "invalid" in errors or "expired" in errors


def test_valid_reset_link_offers_a_new_password_form(
        stub_backend, monkeypatch):
    import auth
    monkeypatch.setattr(
        auth, "verify_token",
        lambda token: {"user_id": 1, "email": "user@test.com"})

    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.query_params["reset"] = "good-token"
    at.run()

    assert not at.exception
    labels = [i.label for i in at.text_input]
    assert "New password" in labels
    assert "Confirm new password" in labels


def test_logging_out_returns_to_the_login_form(stub_backend):
    at = run_app(user=USER)
    logout = [b for b in at.sidebar.button if "Log out" in b.label]
    assert logout, "no log out control in the sidebar"

    at = logout[0].click().run()
    assert not at.exception
    assert at.session_state["user"] is None
