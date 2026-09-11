"""
The mailer must fail closed and fail quietly: a missing credential
disables password reset entirely rather than letting it fall back to
resetting without verification, and an SMTP outage must not surface
as a crash or leak which addresses are registered.
"""
import pytest

import mailer


@pytest.fixture(autouse=True)
def no_ambient_credentials(monkeypatch):
    """Ignore any real credentials in the developer's environment."""
    monkeypatch.setattr(mailer, "_secret", lambda name: None)


def test_missing_credentials_report_unconfigured():
    assert not mailer.is_configured()


def test_partial_credentials_report_unconfigured(monkeypatch):
    monkeypatch.setattr(
        mailer, "_secret",
        lambda name: "someone@gmail.com"
        if name == "EMAIL_ADDRESS" else None)
    assert not mailer.is_configured()


def test_full_credentials_report_configured(monkeypatch):
    monkeypatch.setattr(mailer, "_secret", lambda name: "set")
    assert mailer.is_configured()


def test_send_is_a_no_op_when_unconfigured():
    assert mailer.send_email("a@b.com", "subject", "body") is False


def test_smtp_failure_is_swallowed(monkeypatch):
    monkeypatch.setattr(mailer, "_secret", lambda name: "set")

    def boom(*args, **kwargs):
        raise OSError("network down")

    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", boom)

    # Must return False rather than propagating — a mail outage
    # should not take down the login page.
    assert mailer.send_password_reset(
        "a@b.com", "https://example.com/?reset=x") is False
