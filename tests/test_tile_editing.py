"""
Direct tile editing.

Prompting is good at creating a chart and poor at correcting one, so
these controls change the stored config and rebuild the figure with
no AI involved. That means edits must be exact, instant, and must
not disturb anything else about the tile.
"""
import pandas as pd
import pytest

from streamlit.testing.v1 import AppTest

APP = "app.py"
TIMEOUT = 30
USER = {"id": 1, "name": "Test User", "email": "t@test.com"}


@pytest.fixture
def stub_backend(monkeypatch):
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
    monkeypatch.setattr(quota, "count_api_calls_today", lambda uid: 0)
    monkeypatch.setattr(quota, "record_api_call", lambda uid: None)


def sample_df():
    return pd.DataFrame({
        "region": ["North", "South", "East", "West"],
        "revenue": [45000, 32000, 67000, 28000],
        "units_sold": [120, 98, 145, 87],
        "month": ["2024-01-01", "2024-02-01",
                  "2024-03-01", "2024-04-01"],
    })


def bar_tile(df):
    from charts import build_chart
    config = {"chart_type": "bar", "x": "region", "y": "revenue",
              "y2": None, "color": None, "title": "Revenue by Region"}
    return {"prompt": "revenue by region", "config": config,
            "fig": build_chart(df, config, 0), "width": "half",
            "height": 320, "dataset_name": "sample.csv"}


def open_canvas(tile):
    df = sample_df()
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.session_state["user"] = USER
    at.session_state["page"] = "builder"
    at.session_state["df"] = df
    at.session_state["datasets"] = {"sample.csv": df}
    at.session_state["active_dataset"] = "sample.csv"
    at.session_state["active_dataset_analyzed"] = "sample.csv"
    at.session_state["schema_description"] = "A test dataset."
    at.session_state["tiles"] = [tile]
    return at.run()


def widget(at, cls, key):
    matches = [w for w in getattr(at, cls) if w.key == key]
    assert matches, f"no {cls} with key {key}"
    return matches[0]


def apply_changes(at):
    return widget(at, "button", "ap_0").click().run()


# --- the controls exist ---

def test_editor_offers_direct_controls(stub_backend):
    at = open_canvas(bar_tile(sample_df()))
    assert not at.exception

    keys = ([s.key for s in at.selectbox]
            + [t.key for t in at.text_input])
    for expected in ("ct_0", "x_0", "y_0", "c_0", "t_0"):
        assert expected in keys, f"missing control {expected}"


def test_controls_start_on_the_tiles_current_values(stub_backend):
    at = open_canvas(bar_tile(sample_df()))
    assert widget(at, "selectbox", "ct_0").value == "bar"
    assert widget(at, "selectbox", "x_0").value == "region"
    assert widget(at, "selectbox", "y_0").value == "revenue"
    assert widget(at, "text_input", "t_0").value == "Revenue by Region"


# --- edits take effect ---

def test_changing_chart_type_rebuilds_the_tile(stub_backend):
    at = open_canvas(bar_tile(sample_df()))
    at = widget(at, "selectbox", "ct_0").select("line").run()
    at = apply_changes(at)

    assert not at.exception
    assert at.session_state["tiles"][0]["config"]["chart_type"] == "line"


def test_changing_the_y_column_rebuilds_the_tile(stub_backend):
    at = open_canvas(bar_tile(sample_df()))
    at = widget(at, "selectbox", "y_0").select("units_sold").run()
    at = apply_changes(at)

    assert at.session_state["tiles"][0]["config"]["y"] == "units_sold"


def test_title_can_be_edited_directly(stub_backend):
    at = open_canvas(bar_tile(sample_df()))
    at = widget(at, "text_input", "t_0").set_value("My title").run()
    at = apply_changes(at)

    tile = at.session_state["tiles"][0]
    assert tile["config"]["title"] == "My title"
    assert tile["fig"].layout.title.text == "My title"


def test_group_by_can_be_set_and_cleared(stub_backend):
    at = open_canvas(bar_tile(sample_df()))
    at = widget(at, "selectbox", "c_0").select("month").run()
    at = apply_changes(at)
    assert at.session_state["tiles"][0]["config"]["color"] == "month"

    at = widget(at, "selectbox", "c_0").select("— none —").run()
    at = apply_changes(at)
    assert at.session_state["tiles"][0]["config"]["color"] is None


def test_editing_does_not_disturb_the_rest_of_the_tile(stub_backend):
    at = open_canvas(bar_tile(sample_df()))
    at = widget(at, "selectbox", "ct_0").select("area").run()
    at = apply_changes(at)

    tile = at.session_state["tiles"][0]
    assert tile["prompt"] == "revenue by region"
    assert tile["dataset_name"] == "sample.csv"
    assert tile["width"] == "half"


def test_editing_marks_the_summary_stale(stub_backend):
    at = open_canvas(bar_tile(sample_df()))
    at.session_state["dashboard_insight"] = {"holistic_summary": "old"}
    at.session_state["insight_stale"] = False
    at = at.run()

    at = widget(at, "selectbox", "ct_0").select("pie").run()
    at = apply_changes(at)
    assert at.session_state["insight_stale"] is True


def test_editing_costs_no_ai_calls(stub_backend, monkeypatch):
    """Direct edits are config changes, not model calls."""
    import quota
    calls = []
    monkeypatch.setattr(
        quota, "record_api_call", lambda uid: calls.append(uid))

    at = open_canvas(bar_tile(sample_df()))
    at = widget(at, "selectbox", "ct_0").select("box").run()
    at = apply_changes(at)

    assert calls == []


# --- dual-metric and analytical variants ---

def test_second_metric_appears_only_for_dual_charts(stub_backend):
    at = open_canvas(bar_tile(sample_df()))
    assert "y2_0" not in [s.key for s in at.selectbox]

    at = widget(at, "selectbox", "ct_0").select("dual_line").run()
    assert "y2_0" in [s.key for s in at.selectbox]


def test_allocation_tile_exposes_its_budget(stub_backend):
    from charts import build_chart
    config = {"chart_type": "allocation", "category_column": "region",
              "value_column": "revenue", "total_budget": 100000,
              "title": "allocation"}
    tile = {"prompt": "allocate", "config": config,
            "fig": build_chart(sample_df(), config), "width": "half",
            "height": 320, "dataset_name": "sample.csv"}

    at = open_canvas(tile)
    at = widget(at, "number_input", "bg_0").set_value(50000.0).run()
    at = apply_changes(at)

    tile_after = at.session_state["tiles"][0]
    assert tile_after["config"]["total_budget"] == 50000.0
    assert sum(tile_after["fig"].data[0].y) == pytest.approx(
        50000, abs=0.01)


# --- resilience ---

def test_editor_survives_a_config_pointing_at_missing_columns(
        stub_backend):
    """Data refreshed to a different shape must not crash the editor."""
    from charts import build_chart
    df = sample_df()
    config = {"chart_type": "bar", "x": "gone", "y": "revenue",
              "y2": None, "color": None, "title": "Stale"}
    tile = {"prompt": "p", "config": config,
            "fig": build_chart(df, {**config, "x": "region"}, 0),
            "width": "half", "height": 320,
            "dataset_name": "sample.csv"}

    at = open_canvas(tile)
    assert not at.exception
    # Falls back to a real column rather than blowing up.
    assert widget(at, "selectbox", "x_0").value in df.columns
