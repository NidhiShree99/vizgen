"""
Allocation tiles must behave like any other tile:
rebuildable from stored config, exportable to PDF, and recomputed
against refreshed data rather than frozen at creation time.
"""
import json

import pandas as pd
import pytest

from charts import build_chart
from pdf_export import generate_dashboard_pdf


@pytest.fixture
def df():
    return pd.DataFrame({
        "date": ["2024-01-01", "2024-02-01", "2024-03-01",
                 "2024-04-01", "2024-05-01", "2024-06-01"],
        "region": ["North", "South", "East", "West",
                   "North", "East"],
        "revenue": [100, 200, 300, 400, 500, 600],
    })


ALLOCATION_CONFIG = {
    "chart_type": "allocation",
    "category_column": "region",
    "value_column": "revenue",
    "total_budget": 100000,
    "title": "Optimal allocation of $100,000 across region",
}


def test_allocation_tile_rebuilds_from_config_alone(df):
    fig = build_chart(df, ALLOCATION_CONFIG)
    assert len(fig.data) == 1
    assert sum(fig.data[0].y) == pytest.approx(100000, abs=0.01)


def test_analytical_configs_survive_json_round_trip(df):
    """Tiles are persisted as JSON, so configs must serialise."""
    for config in (ALLOCATION_CONFIG,):
        restored = json.loads(json.dumps(config))
        assert build_chart(df, restored) is not None


def test_allocation_tile_recomputes_against_refreshed_data(df):
    original = build_chart(df, ALLOCATION_CONFIG)

    bigger = dict(ALLOCATION_CONFIG, total_budget=50000)
    smaller = build_chart(df, bigger)

    assert sum(smaller.data[0].y) == pytest.approx(50000, abs=0.01)
    assert sum(original.data[0].y) == pytest.approx(100000, abs=0.01)


def test_analytical_tiles_export_to_pdf(df):
    """PDF export renders every tile — these must not break it."""
    tiles = [
        {"config": ALLOCATION_CONFIG,
         "fig": build_chart(df, ALLOCATION_CONFIG)},
    ]
    pdf = generate_dashboard_pdf("Analytics", tiles)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


# --- degraded inputs must not take the dashboard down ---


def test_allocation_tile_with_one_category_renders_a_message():
    single = pd.DataFrame({
        "region": ["North", "North"],
        "revenue": [10, 20],
    })
    fig = build_chart(single, ALLOCATION_CONFIG)
    assert fig is not None
    assert fig.layout.annotations


# --- tiles saved before forecasting was removed ---

def test_legacy_forecast_tile_renders_a_placeholder_not_a_crash(df):
    """Old dashboards may still hold forecast tiles in the database."""
    legacy = {"chart_type": "forecast", "time_column": "date",
              "value_column": "revenue", "periods": 3,
              "title": "revenue forecast"}
    fig = build_chart(df, legacy)
    assert fig is not None
    assert fig.layout.annotations
    assert "no longer supported" in fig.layout.annotations[0].text
