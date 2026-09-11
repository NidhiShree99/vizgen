from db import count_api_calls_today, record_api_call

DAILY_LIMIT = 100


def usage(user_id):
    """Return (used, limit) for this user's rolling 24h window."""
    return count_api_calls_today(user_id), DAILY_LIMIT


def try_consume(user_id):
    """
    Reserve one AI call against the user's daily quota.

    Returns (allowed, used, limit). When allowed is False the caller
    must not make the API call — the user is over their limit.
    """
    if user_id is None:
        return False, 0, DAILY_LIMIT

    used = count_api_calls_today(user_id)
    if used >= DAILY_LIMIT:
        return False, used, DAILY_LIMIT

    record_api_call(user_id)
    return True, used + 1, DAILY_LIMIT
