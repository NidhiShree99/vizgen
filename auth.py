import bcrypt
from db import create_user, get_user_by_email
import streamlit as st

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

        # Card container
        st.markdown("""
        <div style='background:white; border:1px solid #e2e8f0;
             border-radius:16px; padding:32px; box-shadow:0 1px 3px rgba(0,0,0,0.06);'>
        """, unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["Login", "Sign Up"])

        with tab1:
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

        st.markdown("</div>", unsafe_allow_html=True)