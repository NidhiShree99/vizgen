import pandas as pd
import pytest

from forecasting import generate_forecast, MIN_POINTS


def dated(values, start="2024-01-01"):
    return pd.DataFrame({
        "date": pd.date_range(start, periods=len(values), freq="MS")
        .strftime("%Y-%m-%d"),
        "sales": values,
    })


def test_forecast_returns_requested_number_of_periods():
    res = generate_forecast(
        dated([100, 120, 130, 150, 170, 190]), "date", "sales",
        periods=3)
    assert res["status"] == "ok"
    assert len(res["forecast_values"]) == 3
    assert len(res["forecast_labels"]) == 3


def test_rising_series_forecasts_upward():
    res = generate_forecast(
        dated([100, 120, 140, 160, 180, 200]), "date", "sales",
        periods=2)
    assert res["forecast_values"][0] > res["actual_values"][-1]
    assert res["forecast_values"][1] > res["forecast_values"][0]


def test_falling_series_forecasts_downward():
    res = generate_forecast(
        dated([200, 180, 160, 140, 120, 100]), "date", "sales",
        periods=2)
    assert res["forecast_values"][0] < res["actual_values"][-1]


def test_real_dates_continue_the_calendar():
    res = generate_forecast(
        dated([10, 20, 30, 40, 50, 60]), "date", "sales", periods=2)
    assert res["used_real_dates"]
    assert res["actual_labels"][-1] == "2024-06-01"
    assert res["forecast_labels"] == ["2024-07-01", "2024-08-01"]


def test_rows_are_aggregated_per_time_point():
    # Two rows per month should collapse into one point each.
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-01", "2024-02-01",
                 "2024-02-01", "2024-03-01", "2024-03-01",
                 "2024-04-01", "2024-04-01"],
        "sales": [50, 50, 60, 60, 70, 70, 80, 80],
    })
    res = generate_forecast(df, "date", "sales", periods=1)
    assert res["actual_values"] == [100.0, 120.0, 140.0, 160.0]


def test_unsorted_dates_are_ordered_before_forecasting():
    df = pd.DataFrame({
        "date": ["2024-03-01", "2024-01-01", "2024-04-01",
                 "2024-02-01"],
        "sales": [30, 10, 40, 20],
    })
    res = generate_forecast(df, "date", "sales", periods=1)
    assert res["actual_values"] == [10.0, 20.0, 30.0, 40.0]


def test_non_date_column_falls_back_to_step_labels():
    df = pd.DataFrame({
        "stage": ["S1", "S2", "S3", "S4"],
        "sales": [10, 20, 30, 40],
    })
    res = generate_forecast(df, "stage", "sales", periods=2)
    assert res["status"] == "ok"
    assert not res["used_real_dates"]
    assert res["forecast_labels"] == ["Forecast 1", "Forecast 2"]


# --- guard rails ---

def test_too_few_points_is_a_clean_error():
    res = generate_forecast(
        dated([1, 2]), "date", "sales", periods=3)
    assert res["status"] == "error"
    assert str(MIN_POINTS) in res["message"]


def test_empty_data_is_a_clean_error():
    df = pd.DataFrame({"date": [], "sales": []})
    res = generate_forecast(df, "date", "sales", periods=3)
    assert res["status"] == "error"


def test_all_null_values_is_a_clean_error():
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-02-01", "2024-03-01",
                 "2024-04-01"],
        "sales": [None, None, None, None],
    })
    res = generate_forecast(df, "date", "sales", periods=2)
    assert res["status"] == "error"


def test_flat_series_does_not_crash():
    res = generate_forecast(
        dated([100, 100, 100, 100, 100]), "date", "sales",
        periods=2)
    assert res["status"] == "ok"
    assert len(res["forecast_values"]) == 2
