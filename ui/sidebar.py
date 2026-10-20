import streamlit as st

from db import delete_dashboard, get_user_dashboards, get_versions
from quota import usage
from ui.config import BASE_URL
from ui.helpers import open_dashboard, version_list_html


def render():
    with st.sidebar:
        st.title("🎨 VizGen")
        st.caption("AI Dashboard Builder")
        st.caption(f"👤 {st.session_state.user['name']}")
        if st.button("🚪 Log out", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = "home"
            st.rerun()

        ai_used, ai_limit = usage(st.session_state.user["id"])
        st.caption(f"⚡ AI usage: {ai_used}/{ai_limit} today")

        st.divider()

        if st.button("🏠 Home", use_container_width=True):
            st.session_state.page = "home"
            st.session_state.tiles = []
            st.session_state.df = None
            st.session_state.datasets = {}
            st.session_state.active_dataset = None
            st.session_state.schema_description = None
            st.session_state.dashboard_insight = None
            st.session_state.insight_stale = False
            st.session_state.renaming = False
            st.session_state.active_filter = None
            st.session_state.chat_history = []
            st.session_state.optimize_result = None
            st.rerun()

        if st.button("➕ New Dashboard",
                      use_container_width=True,
                      type="primary"):
            st.session_state.page = "builder"
            st.session_state.tiles = []
            st.session_state.df = None
            st.session_state.datasets = {}
            st.session_state.active_dataset = None
            st.session_state.current_dashboard_name = ""
            st.session_state.current_dashboard_id = None
            st.session_state.schema_description = None
            st.session_state.dashboard_insight = None
            st.session_state.insight_stale = False
            st.session_state.renaming = False
            st.session_state.active_filter = None
            st.session_state.chat_history = []
            st.session_state.optimize_result = None
            st.rerun()

        st.divider()

        col_title, col_refresh = st.columns([3, 1])
        with col_title:
            st.markdown("**My Dashboards**")
        with col_refresh:
            if st.button("🔄", help="Refresh list"):
                st.rerun()

        dashboards = get_user_dashboards(st.session_state.user["id"])
        published_list = [d for d in dashboards
                          if d["status"] == "published"]
        draft_list = [d for d in dashboards
                      if d["status"] == "draft"]

        if published_list:
            st.markdown(
                "<p style='color:#10b981;font-size:11px;"
                "font-weight:700;text-transform:uppercase;"
                "letter-spacing:0.05em;margin:8px 0 4px;'>"
                "🟢 Published</p>",
                unsafe_allow_html=True
            )
            for dash in published_list:
                versions = get_versions(dash["id"])
                st.markdown(
                    f"<p style='margin:0;font-weight:600;"
                    f"font-size:14px;'>"
                    f"{dash['name'][:22]}</p>",
                    unsafe_allow_html=True
                )
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
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("Open",
                                  key=f"sb_open_{dash['id']}",
                                  use_container_width=True):
                        open_dashboard(dash)
                        st.rerun()
                with b2:
                    if st.button("Delete",
                                  key=f"sb_del_{dash['id']}",
                                  use_container_width=True):
                        delete_dashboard(dash["id"], st.session_state.user["id"])
                        st.rerun()
                st.markdown("---")

        if draft_list:
            st.markdown(
                "<p style='color:#f59e0b;font-size:11px;"
                "font-weight:700;text-transform:uppercase;"
                "letter-spacing:0.05em;margin:8px 0 4px;'>"
                "📝 Drafts</p>",
                unsafe_allow_html=True
            )
            for dash in draft_list:
                st.markdown(f"**{dash['name'][:22]}**")
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("Open",
                                  key=f"sb_open_{dash['id']}",
                                  use_container_width=True):
                        open_dashboard(dash)
                        st.rerun()
                with b2:
                    if st.button("Delete",
                                  key=f"sb_del_{dash['id']}",
                                  use_container_width=True):
                        delete_dashboard(dash["id"], st.session_state.user["id"])
                        st.rerun()
                st.markdown("---")

        if not dashboards:
            st.caption("No dashboards yet.")

        st.divider()
        st.caption("📚 Documentation")
        st.caption("💬 Help & Support")
        st.caption("⚙️ Settings")
