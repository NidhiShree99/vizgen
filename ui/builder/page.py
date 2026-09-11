import streamlit as st

from ui.builder import (ai_tools, canvas, data, generators, history,
                        refresh, topbar)


def render():
    """
    The dashboard builder.

    Order matters: data.render() is what populates
    st.session_state.df, so the AI tools and chart generators that
    depend on a loaded dataset run after it.
    """
    topbar.render()
    st.divider()

    refresh.render()
    history.render()
    data.render()

    if st.session_state.df is not None:
        st.divider()
        ai_tools.render()
        generators.render()

    canvas.render()
