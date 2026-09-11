"""
VizGen — AI-powered dashboard builder.

Entry point only: bootstrap, routing, and nothing else. The screens
themselves live in the `ui` package.
"""
import streamlit as st

from db import create_tables
from auth import show_auth
from ui import home, share, sidebar, styles, state
from ui.builder import page as builder

create_tables()

st.set_page_config(page_title="VizGen", layout="wide")
styles.inject_global_css()
state.init_session_state()

# Public share links render read-only and never reach the auth gate.
share.render_if_share_link()

if st.session_state.user is None:
    show_auth()
    st.stop()

sidebar.render()

if st.session_state.page == "home":
    home.render()
elif st.session_state.page == "builder":
    builder.render()
