import streamlit as st

DEFAULTS = {
    "page": "home",
    "tiles": [],
    "df": None,
    "datasets": {},
    "active_dataset": None,
    "current_dashboard_name": "",
    "current_dashboard_id": None,
    "schema_description": None,
    "dashboard_insight": None,
    "insight_stale": False,
    "insight_tile_count": 0,
    "renaming": False,
    "user": None,
    "active_filter": None,
    "chat_history": [],
    "forecast_result": None,
    "optimize_result": None,
}


def init_session_state():
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value
