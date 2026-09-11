import pandas as pd
import pytest

from filters import apply_filters


@pytest.fixture
def df():
    return pd.DataFrame({
        "region": ["North", "South", "East", "West"],
        "revenue": [45000, 32000, 67000, 28000],
        "month": ["January", "January", "February", "February"],
    })


def ok(conditions, logic="AND"):
    return {"status": "ok", "conditions": conditions, "logic": logic}


def test_equality_filter(df):
    out = apply_filters(df, ok([
        {"column": "region", "operator": "==", "value": "West"}]))
    assert list(out["region"]) == ["West"]


def test_numeric_comparison(df):
    out = apply_filters(df, ok([
        {"column": "revenue", "operator": ">", "value": 40000}]))
    assert sorted(out["region"]) == ["East", "North"]


def test_in_operator_with_list(df):
    out = apply_filters(df, ok([
        {"column": "region", "operator": "in",
         "value": ["North", "East"]}]))
    assert sorted(out["region"]) == ["East", "North"]


def test_and_logic_narrows_results(df):
    out = apply_filters(df, ok([
        {"column": "month", "operator": "==", "value": "January"},
        {"column": "revenue", "operator": ">", "value": 40000},
    ], logic="AND"))
    assert list(out["region"]) == ["North"]


def test_or_logic_widens_results(df):
    out = apply_filters(df, ok([
        {"column": "region", "operator": "==", "value": "North"},
        {"column": "region", "operator": "==", "value": "West"},
    ], logic="OR"))
    assert sorted(out["region"]) == ["North", "West"]


def test_contains_is_case_insensitive(df):
    out = apply_filters(df, ok([
        {"column": "region", "operator": "contains",
         "value": "nor"}]))
    assert list(out["region"]) == ["North"]


def test_not_contains_excludes(df):
    out = apply_filters(df, ok([
        {"column": "month", "operator": "not_contains",
         "value": "Jan"}]))
    assert sorted(out["region"]) == ["East", "West"]


# --- the cases that matter for not silently mangling data ---

def test_error_status_returns_data_untouched(df):
    out = apply_filters(df, {"status": "error", "message": "nope"})
    pd.testing.assert_frame_equal(out, df)


def test_none_config_returns_data_untouched(df):
    pd.testing.assert_frame_equal(apply_filters(df, None), df)


def test_unknown_column_is_ignored_not_crashed(df):
    out = apply_filters(df, ok([
        {"column": "does_not_exist", "operator": "==",
         "value": "x"}]))
    pd.testing.assert_frame_equal(out, df)


def test_unknown_operator_is_ignored_not_crashed(df):
    out = apply_filters(df, ok([
        {"column": "region", "operator": "REGEX",
         "value": ".*"}]))
    pd.testing.assert_frame_equal(out, df)


def test_partially_valid_conditions_still_apply_valid_ones(df):
    out = apply_filters(df, ok([
        {"column": "nope", "operator": "==", "value": 1},
        {"column": "region", "operator": "==", "value": "East"},
    ]))
    assert list(out["region"]) == ["East"]


def test_filter_matching_nothing_returns_empty_not_error(df):
    out = apply_filters(df, ok([
        {"column": "region", "operator": "==",
         "value": "Atlantis"}]))
    assert len(out) == 0


def test_original_dataframe_is_never_mutated(df):
    before = df.copy()
    apply_filters(df, ok([
        {"column": "revenue", "operator": ">", "value": 1}]))
    pd.testing.assert_frame_equal(df, before)
