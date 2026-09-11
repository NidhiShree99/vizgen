import pandas as pd
import pytest

from optimizer import optimize_budget_allocation, MAX_SHARE_PER_CATEGORY


@pytest.fixture
def df():
    # East is the clear top performer, then North, South, West.
    return pd.DataFrame({
        "region": ["North", "South", "East", "West"] * 3,
        "revenue": [45000, 32000, 67000, 28000,
                    51000, 38000, 72000, 31000,
                    48000, 41000, 69000, 35000],
    })


def test_allocation_sums_to_the_full_budget(df):
    res = optimize_budget_allocation(df, "region", "revenue", 100000)
    assert res["status"] == "ok"
    total = sum(a["amount"] for a in res["allocations"])
    assert total == pytest.approx(100000, abs=0.01)


def test_no_category_exceeds_the_share_cap(df):
    budget = 100000
    res = optimize_budget_allocation(df, "region", "revenue", budget)
    cap = budget * MAX_SHARE_PER_CATEGORY
    for a in res["allocations"]:
        assert a["amount"] <= cap + 0.01


def test_budget_goes_to_the_strongest_performers(df):
    res = optimize_budget_allocation(df, "region", "revenue", 100000)
    funded = {a["category"]: a["amount"]
              for a in res["allocations"] if a["amount"] > 0}
    # East and North have the highest average revenue.
    assert set(funded) == {"East", "North"}


def test_allocations_are_returned_largest_first(df):
    res = optimize_budget_allocation(df, "region", "revenue", 100000)
    amounts = [a["amount"] for a in res["allocations"]]
    assert amounts == sorted(amounts, reverse=True)


def test_priority_score_is_normalised_to_the_best_category(df):
    res = optimize_budget_allocation(df, "region", "revenue", 100000)
    scores = {a["category"]: a["priority_score"]
              for a in res["allocations"]}
    assert scores["East"] == 1.0
    assert all(0 < s <= 1.0 for s in scores.values())


def test_cap_forces_diversification_across_many_categories():
    # With a 50% cap, a budget always needs at least two categories.
    df = pd.DataFrame({
        "channel": ["A", "B", "C"],
        "roi": [100, 10, 1],
    })
    res = optimize_budget_allocation(df, "channel", "roi", 90)
    funded = [a for a in res["allocations"] if a["amount"] > 0]
    assert len(funded) >= 2


# --- guard rails ---

def test_single_category_is_rejected():
    df = pd.DataFrame({"region": ["North"], "revenue": [100]})
    res = optimize_budget_allocation(df, "region", "revenue", 1000)
    assert res["status"] == "error"
    assert "at least 2" in res["message"]


def test_zero_budget_is_rejected(df):
    res = optimize_budget_allocation(df, "region", "revenue", 0)
    assert res["status"] == "error"


def test_negative_budget_is_rejected(df):
    res = optimize_budget_allocation(df, "region", "revenue", -500)
    assert res["status"] == "error"


def test_missing_budget_is_rejected(df):
    res = optimize_budget_allocation(df, "region", "revenue", None)
    assert res["status"] == "error"
