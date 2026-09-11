"""
The quota is what stands between a public signup page and an
unbounded Anthropic bill, so it gets tested on the boundary.
"""
import pytest

import quota


@pytest.fixture
def counter(monkeypatch):
    """In-memory stand-in for the api_usage table."""
    state = {"count": 0, "recorded": 0}

    monkeypatch.setattr(
        quota, "count_api_calls_today", lambda uid: state["count"])

    def record(uid):
        state["recorded"] += 1
        state["count"] += 1

    monkeypatch.setattr(quota, "record_api_call", record)
    return state


def test_call_under_the_limit_is_allowed(counter):
    counter["count"] = 0
    allowed, used, limit = quota.try_consume(1)
    assert allowed
    assert used == 1
    assert limit == quota.DAILY_LIMIT


def test_allowed_call_is_recorded(counter):
    quota.try_consume(1)
    assert counter["recorded"] == 1


def test_call_at_one_below_the_limit_is_allowed(counter):
    counter["count"] = quota.DAILY_LIMIT - 1
    allowed, _, _ = quota.try_consume(1)
    assert allowed


def test_call_exactly_at_the_limit_is_blocked(counter):
    counter["count"] = quota.DAILY_LIMIT
    allowed, _, _ = quota.try_consume(1)
    assert not allowed


def test_blocked_call_is_not_recorded(counter):
    counter["count"] = quota.DAILY_LIMIT
    quota.try_consume(1)
    assert counter["recorded"] == 0, (
        "a blocked request still consumed quota")


def test_call_over_the_limit_stays_blocked(counter):
    counter["count"] = quota.DAILY_LIMIT * 10
    allowed, _, _ = quota.try_consume(1)
    assert not allowed


def test_anonymous_user_is_always_blocked(counter):
    """Public share pages must bill a real owner, never nobody."""
    allowed, _, _ = quota.try_consume(None)
    assert not allowed
    assert counter["recorded"] == 0


def test_usage_reports_current_count_and_limit(counter):
    counter["count"] = 12
    used, limit = quota.usage(1)
    assert used == 12
    assert limit == quota.DAILY_LIMIT


def test_repeated_calls_accumulate_until_blocked(monkeypatch):
    state = {"count": 0}
    monkeypatch.setattr(
        quota, "count_api_calls_today", lambda uid: state["count"])
    monkeypatch.setattr(
        quota, "record_api_call",
        lambda uid: state.__setitem__("count", state["count"] + 1))
    monkeypatch.setattr(quota, "DAILY_LIMIT", 3)

    results = [quota.try_consume(1)[0] for _ in range(5)]
    assert results == [True, True, True, False, False]
