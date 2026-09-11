"""
Outgoing mail for password resets.

Uses plain SMTP so there is no third-party service to sign up for —
a Gmail address plus an App Password is enough. When those are not
configured, is_configured() reports False and the reset flow closes
itself rather than falling back to something unverified.
"""
import os
import smtplib
import ssl
from email.message import EmailMessage

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def _secret(name):
    try:
        return st.secrets[name]
    except Exception:
        return os.getenv(name)


def sender_address():
    return _secret("EMAIL_ADDRESS")


def is_configured():
    return bool(sender_address() and _secret("EMAIL_APP_PASSWORD"))


def send_email(to_address, subject, body):
    """
    Returns True when the message was handed to the SMTP server.
    Never raises: a mail failure must not take down the page, and
    the caller shows the same message either way so that a failed
    send cannot be used to probe which addresses are registered.
    """
    if not is_configured():
        return False

    message = EmailMessage()
    message["From"] = sender_address()
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT,
                              context=context) as server:
            server.login(sender_address(),
                         _secret("EMAIL_APP_PASSWORD"))
            server.send_message(message)
        return True
    except Exception:
        return False


def send_password_reset(to_address, reset_url):
    return send_email(
        to_address,
        "Reset your VizGen password",
        "Someone asked to reset the password for this VizGen "
        "account.\n\n"
        f"Use this link within the next hour:\n{reset_url}\n\n"
        "The link can only be used once. If this wasn't you, you "
        "can ignore this email — nothing has changed.\n",
    )
