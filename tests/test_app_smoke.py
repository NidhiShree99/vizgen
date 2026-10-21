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

    import owner
    monkeypatch.setattr(owner, "get_owner", lambda: USER)


def run_app(**session):
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    for key, value in session.items():
        at.session_state[key] = value
    return at.run()


def test_app_starts_without_error(stub_backend):
    at = run_app()
    assert not at.exception


def test_database_outage_shows_a_friendly_page_not_a_traceback(
        stub_backend, monkeypatch):
    """A paused free-tier database must not surface as a crash."""
    import db

    def down():
        raise OSError("connection refused")

    monkeypatch.setattr(db, "create_tables", down)

    at = run_app()
    assert not at.exception

    body = " ".join(str(m.value) for m in at.markdown)
    assert "can't reach the database" in body
    # Nothing past the outage page may render.
    assert not [b for b in at.button if "Login" in b.label]
    assert [b.label for b in at.button] == ["Try again"]


# --- logged-in surface ---

USER = {"id": 1, "name": "Test User", "email": "t@test.com"}


def test_app_opens_straight_to_the_home_page(stub_backend):
    """No login: a fresh session lands on the app, not a form."""
    at = run_app()
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
    """Chat and optimize only make sense once data is loaded."""
    at = run_app(user=USER, page="builder")
    headings = " ".join(s.value for s in at.subheader)
    assert "Ask Your Data" not in headings
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
    loaded — chat and optimize each live in their own
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
    for section in ("Ask Your Data", "Optimize",
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


# --- no login ---

def test_there_is_no_login_form_or_logout_button(stub_backend):
    at = run_app()
    assert not at.exception

    labels = [i.label for i in at.text_input]
    assert "Email address" not in labels
    assert "Password" not in labels

    buttons = [b.label for b in at.button] \
        + [b.label for b in at.sidebar.button]
    assert not any("Log out" in b or "Login" in b for b in buttons)


def test_every_session_runs_as_the_owner_account(stub_backend):
    at = run_app()
    assert at.session_state["user"] == USER


def test_dashboard_scoping_still_uses_the_owner_id(
        stub_backend, monkeypatch):
    """Data stays keyed to a user id even without a login."""
    # home and sidebar import the function by name, so it has to be
    # patched where it is used rather than where it is defined.
    from ui import home, sidebar
    seen = []
    spy = lambda uid: seen.append(uid) or []  # noqa: E731
    monkeypatch.setattr(home, "get_user_dashboards", spy)
    monkeypatch.setattr(sidebar, "get_user_dashboards", spy)

    run_app()
    assert seen and set(seen) == {USER["id"]}
