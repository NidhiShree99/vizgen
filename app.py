"""
VizGen — AI-powered dashboard builder.

Entry point only: bootstrap, routing, and nothing else. The screens
themselves live in the `ui` package.
"""
import streamlit as st

from db import create_tables
from auth import show_auth, show_reset_page
from ui import home, share, sidebar, styles, state
from ui.builder import page as builder

st.set_page_config(page_title="VizGen", layout="wide")
styles.inject_global_css()

try:
    create_tables()
except Exception:
    # Usually the free-tier database waking from a pause. Show a
    # plain message instead of a raw traceback, and stop: nothing
    # past this point works without the database.
    st.markdown(
        "<div style='max-width:520px;margin:120px auto;"
        "text-align:center;font-family:sans-serif;'>"
        "<h1 style='color:#6366f1;margin:0 0 8px;'>VizGen</h1>"
        "<p style='color:#475569;font-size:16px;'>"
        "We can't reach the database right now. It's usually back "
        "within a couple of minutes.</p></div>",
        unsafe_allow_html=True)
    if st.button("Try again", key="db_retry"):
        st.rerun()
    st.stop()

state.init_session_state()

# Public share links render read-only and never reach the auth gate.
share.render_if_share_link()

# Emailed reset links land here — the visitor cannot log in, so this
# also has to run ahead of the auth gate.
if "reset" in st.query_params:
    show_reset_page(st.query_params["reset"])
    st.stop()

if st.session_state.user is None:
    show_auth()
    st.stop()

sidebar.render()

if st.session_state.page == "home":
    home.render()
elif st.session_state.page == "builder":
    builder.render()
