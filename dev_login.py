"""
Optional login bypass for local development.

Signing in on every restart gets old while building, so setting
VIZGEN_DEV_LOGIN=1 in your local .env signs you in automatically as
a fixed dev account. It is off unless that variable is set, so the
deployed app keeps its login — never set it in Streamlit Cloud, or
every visitor would share one account.
"""
import os

from db import create_user, get_user_by_email

DEV_EMAIL = "dev@vizgen.local"
DEV_NAME = "Dev User"


def enabled():
    return os.getenv("VIZGEN_DEV_LOGIN", "").strip().lower() in (
        "1", "true", "yes", "on")


def get_dev_user():
    """The dev account, created on first use."""
    user = get_user_by_email(DEV_EMAIL)
    if not user:
        # The password hash is unusable on purpose: nothing can ever
        # log in to this account through the real login form.
        create_user(DEV_NAME, DEV_EMAIL, "!disabled")
        user = get_user_by_email(DEV_EMAIL)
    return user
