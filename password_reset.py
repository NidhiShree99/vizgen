"""
Token-based password reset.

Tokens are random, stored only as a hash, single-use, and expire
after an hour. The request step deliberately reports the same thing
whether or not the address is registered, so the form cannot be used
to enumerate accounts.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from db import (consume_password_reset, create_password_reset,
                get_user_by_email, get_valid_password_reset,
                invalidate_password_resets, update_user_password)

TOKEN_TTL = timedelta(hours=1)


def hash_token(token):
    """
    Stored hashed so a leaked database does not hand over live reset
    links. Tokens are high-entropy, so a plain digest is enough —
    there is nothing to brute-force.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(email):
    """
    Create a reset token for this address.

    Returns the raw token, or None when no such account exists. The
    caller must show the same message either way.
    """
    user = get_user_by_email(email)
    if not user:
        return None

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + TOKEN_TTL
    create_password_reset(user["id"], hash_token(token), expires_at)
    return token


def verify_token(token):
    """Return the reset record for a usable token, else None."""
    if not token:
        return None
    return get_valid_password_reset(hash_token(token))


def complete_reset(token, new_password_hash):
    """
    Set the new password and spend the token.

    Every other outstanding token for that user is spent too, so a
    second reset link sitting in an inbox cannot be replayed later.
    """
    record = verify_token(token)
    if not record:
        return False

    update_user_password(record["email"], new_password_hash)
    consume_password_reset(hash_token(token))
    invalidate_password_resets(record["user_id"])
    return True
