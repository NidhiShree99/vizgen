import bcrypt
from db import create_user, get_user_by_email
import streamlit as st

from mailer import is_configured, send_password_reset
from password_reset import complete_reset, issue_token, verify_token
from ui.config import BASE_URL

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def show_auth():
    st.markdown("""
    <style>
    .stApp { background: #ffffff !important; }
    .stTabs [data-baseweb="tab-list"] {
        background: #f8fafc;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #64748b;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: white !important;
        color: #6366f1 !important;
    }
    div[data-testid="stTextInput"] label {
        color: #1e293b !important;
        font-size: 14px !important;
        font-weight: 500 !important;
    }
    div[data-testid="stTextInput"] input {
        background: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        color: #1e293b !important;
        font-size: 14px !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99,102,241,0.15) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Centered layout
    _, center, _ = st.columns([1, 1.2, 1])

    with center:
        st.markdown("<br><br>", unsafe_allow_html=True)

        # Logo
        st.markdown("""
        <div style='text-align:center; margin-bottom:32px;'>
            <h1 style='color:#6366f1; font-size:42px; font-weight:700;
                       margin:0; font-family:sans-serif;'>VizGen</h1>
            <p style='color:#64748b; font-size:15px; margin:6px 0 0;'>
                AI-powered dashboard builder
            </p>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["Login", "Sign Up"])

        with tab1:
            if "show_reset" not in st.session_state:
                st.session_state.show_reset = False

            if not st.session_state.show_reset:
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                email = st.text_input("Email address", key="login_email",
                                       placeholder="you@example.com")
                password = st.text_input("Password", type="password",
                                          key="login_pass",
                                          placeholder="Enter your password")
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                if st.button("Login →", use_container_width=True, type="primary",
                              key="login_btn"):
                    if email and password:
                        user = get_user_by_email(email)
                        if user and verify_password(password, user["password_hash"]):
                            st.session_state.user = user
                            st.rerun()
                        else:
                            st.error("Invalid email or password.")
                    else:
                        st.warning("Please fill in all fields.")

                if st.button("Forgot password?", key="forgot_pw_link"):
                    st.session_state.show_reset = True
                    st.rerun()

            else:
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

                if not is_configured():
                    # No mail credentials: close the flow rather than
                    # fall back to resetting without any verification,
                    # which would let anyone who knows an address take
                    # over the account.
                    st.warning(
                        "Password reset isn't available on this "
                        "deployment yet — it needs an email sender "
                        "configured. Contact the site owner."
                    )
                    if st.button("Back to login",
                                  use_container_width=True,
                                  key="cancel_reset_btn"):
                        st.session_state.show_reset = False
                        st.rerun()
                else:
                    st.caption(
                        "Enter your email and we'll send you a "
                        "reset link.")
                    reset_email = st.text_input(
                        "Email address", key="reset_email",
                        placeholder="you@example.com")
                    st.markdown("<div style='height:8px'></div>",
                                unsafe_allow_html=True)

                    rc1, rc2 = st.columns(2)
                    with rc1:
                        if st.button("Send reset link",
                                      use_container_width=True,
                                      type="primary",
                                      key="reset_pw_btn"):
                            if not reset_email:
                                st.warning("Enter your email address.")
                            else:
                                token = issue_token(reset_email)
                                if token:
                                    send_password_reset(
                                        reset_email,
                                        f"{BASE_URL}/?reset={token}")
                                # Same response either way, so this
                                # form can't be used to discover
                                # which addresses have accounts.
                                st.success(
                                    "If that email has an account, "
                                    "a reset link is on its way. "
                                    "It expires in an hour."
                                )
                    with rc2:
                        if st.button("Back to login",
                                      use_container_width=True,
                                      key="cancel_reset_btn"):
                            st.session_state.show_reset = False
                            st.rerun()

        with tab2:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            name = st.text_input("Full name", key="signup_name",
                                  placeholder="Nidhi Shree")
            email = st.text_input("Email address", key="signup_email",
                                   placeholder="you@example.com")
            password = st.text_input("Password", type="password",
                                      key="signup_pass",
                                      placeholder="Create a password")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            if st.button("Create Account →", use_container_width=True,
                          type="primary", key="signup_btn"):
                if name and email and password:
                    success = create_user(name, email, hash_password(password))
                    if success:
                        user = get_user_by_email(email)
                        st.session_state.user = user
                        st.rerun()
                    else:
                        st.error("An account with this email already exists.")
                else:
                    st.warning("Please fill in all fields.")

def show_reset_page(token):
    """
    Landing page for an emailed reset link (?reset=TOKEN).

    Rendered before the auth gate, since the whole point is that the
    visitor cannot log in.
    """
    _, center, _ = st.columns([1, 1.2, 1])

    with center:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center; margin-bottom:32px;'>
            <h1 style='color:#6366f1; font-size:42px; font-weight:700;
                       margin:0; font-family:sans-serif;'>VizGen</h1>
            <p style='color:#64748b; font-size:15px; margin:6px 0 0;'>
                Choose a new password
            </p>
        </div>
        """, unsafe_allow_html=True)

        record = verify_token(token)
        if not record:
            st.error(
                "This reset link is invalid, already used, or has "
                "expired. Request a new one from the login page."
            )
            if st.button("Back to login", use_container_width=True,
                          key="expired_back_btn"):
                st.query_params.clear()
                st.rerun()
            return

        st.caption(f"Resetting the password for {record['email']}.")
        new_password = st.text_input(
            "New password", type="password", key="new_pw",
            placeholder="Enter a new password")
        confirm = st.text_input(
            "Confirm new password", type="password", key="confirm_pw",
            placeholder="Enter it again")

        if st.button("Set new password", use_container_width=True,
                      type="primary", key="set_pw_btn"):
            if not new_password or not confirm:
                st.warning("Fill in both fields.")
            elif new_password != confirm:
                st.error("Those passwords don't match.")
            elif len(new_password) < 8:
                st.error("Use at least 8 characters.")
            elif complete_reset(token, hash_password(new_password)):
                st.success(
                    "Password updated. You can log in with it now.")
                st.query_params.clear()
            else:
                st.error(
                    "That link is no longer valid. Request a new "
                    "one from the login page."
                )
