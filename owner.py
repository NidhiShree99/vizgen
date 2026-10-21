"""
The single account the app runs as.

There is no login. Dashboards and the AI quota are still keyed to a
user id, so every session simply uses this one owner account. The
full multi-user system (login, sign up, password reset, email) is
preserved on the `archive/auth-system` branch.
"""
from db import create_user, get_user_by_email

OWNER_EMAIL = "nshree@gmail.com"
OWNER_NAME = "Nidhi"


def get_owner():
    """The owner account, created on first use."""
    user = get_user_by_email(OWNER_EMAIL)
    if not user:
        # No password exists to guess: there is no login to use it on.
        create_user(OWNER_NAME, OWNER_EMAIL, "!disabled")
        user = get_user_by_email(OWNER_EMAIL)
    return user
