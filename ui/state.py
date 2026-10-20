import copy

import streamlit as st

# Mutable entries here (tiles, datasets, chat_history) must never be
# handed out by reference: DEFAULTS lives for the life of the
# process, so a session appending to the same list object would leak
# its contents into every session initialised afterwards.
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
    "optimize_result": None,
}


def init_session_state():
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = copy.deepcopy(value)
