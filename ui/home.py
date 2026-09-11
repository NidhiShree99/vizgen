import streamlit as st

from db import delete_dashboard, get_user_dashboards, get_versions
from ui.config import BASE_URL
from ui.helpers import open_dashboard, version_list_html


def render():
    st.title("Welcome to VizGen 👋")
    st.markdown(
        "Build AI-powered dashboards from your data in minutes.")
    st.divider()

    dashboards = get_user_dashboards(st.session_state.user["id"])
    total = len(dashboards)
    pub_count = sum(
        1 for d in dashboards if d["status"] == "published")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Dashboards", total)
    c2.metric("Published", pub_count)
    c3.metric("Drafts", total - pub_count)

    st.divider()

    pub_list = [d for d in dashboards
                if d["status"] == "published"]
    dft_list = [d for d in dashboards
                if d["status"] == "draft"]

    if pub_list:
        st.subheader("🟢 Published")
        for dash in pub_list:
            versions = get_versions(dash["id"])
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1:
                st.markdown(f"**{dash['name']}**")
                if versions:
                    st.markdown(
                        version_list_html(versions),
                        unsafe_allow_html=True
                    )
                if dash["share_token"]:
                    st.code(
                        f"{BASE_URL}/?share="
                        f"{dash['share_token']}",
                        language=None
                    )
            with c2:
                if st.button("Open",
                              key=f"home_open_{dash['id']}",
                              use_container_width=True):
                    open_dashboard(dash)
                    st.rerun()
            with c3:
                if st.button("Delete",
                              key=f"home_del_{dash['id']}",
                              use_container_width=True):
                    delete_dashboard(dash["id"], st.session_state.user["id"])
                    st.rerun()
            st.divider()

    if dft_list:
        st.subheader("📝 Drafts")
        for dash in dft_list:
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1:
                st.markdown(f"**{dash['name']}**")
            with c2:
                if st.button("Open",
                              key=f"home_dft_open_{dash['id']}",
                              use_container_width=True):
                    open_dashboard(dash)
                    st.rerun()
            with c3:
                if st.button("Delete",
                              key=f"home_dft_del_{dash['id']}",
                              use_container_width=True):
                    delete_dashboard(dash["id"], st.session_state.user["id"])
                    st.rerun()
            st.divider()

    if not dashboards:
        st.info(
            "No dashboards yet. "
            "Click **➕ New Dashboard** in the sidebar!")

    st.subheader("🚀 Getting Started")
    st.markdown("""
    1. Click **New Dashboard** in the sidebar
    2. Upload one or more **CSV files**
    3. Pick a **Business Use Case** for auto-dashboard OR
       describe individual charts in plain English
    4. Click **📝 Generate Executive Summary** for AI insights
    5. **Publish** → get a shareable link
    """)

