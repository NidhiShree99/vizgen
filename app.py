import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import uuid
import json
import io
from db import (create_tables, save_dashboard, get_user_dashboards,
                save_tile, get_dashboard_tiles, delete_dashboard,
                delete_dashboard_tiles, get_dashboard_by_token,
                get_dashboard_by_id, update_dashboard_name,
                update_dashboard_publish, save_version,
                get_versions, save_prompt_history,
                get_dashboard_prompt_history)
from ai import (analyze_schema, generate_chart_config,
                generate_dashboard_insights,
                generate_use_case_dashboard,
                generate_filter_config,
                answer_data_question,
                generate_forecast_request,
                generate_optimization_request)
from charts import build_chart
from auth import show_auth
from filters import apply_filters
from pdf_export import generate_dashboard_pdf
from forecasting import generate_forecast
from optimizer import optimize_budget_allocation

create_tables()

st.set_page_config(page_title="VizGen", layout="wide")

BASE_URL = "https://vizgenanalytics.streamlit.app"

# ── Sticky top bar CSS ────────────────────────────
st.markdown("""
<style>
    .stApp { background: #f8fafc; }
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    [data-testid="stAppViewBlockContainer"] > div:first-child {
        position: sticky !important;
        top: 0 !important;
        z-index: 999 !important;
        background: white !important;
        border-bottom: 1px solid #e2e8f0 !important;
        padding: 12px 0 8px !important;
    }

    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
    }
    .stButton > button[kind="primary"] {
        background: #6366f1 !important;
        border: none !important;
        color: white !important;
        border-radius: 8px !important;
    }
    .stButton > button {
        border-radius: 8px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }
</style>
""", unsafe_allow_html=True)


def load_dashboard_tiles(dashboard_id):
    saved_tiles = get_dashboard_tiles(dashboard_id)
    tiles = []
    for tile in saved_tiles:
        config = json.loads(tile["chart_config"])
        if tile.get("data_json"):
            df = pd.read_json(io.StringIO(tile["data_json"]))
            fig = build_chart(df, config,
                               tile.get("position", 0))
            tiles.append({
                "prompt": tile["prompt"],
                "config": config,
                "fig": fig,
                "width": tile.get("width", "half"),
                "height": tile.get("height", 320),
                "dataset_name": tile.get("dataset_name", "")
            })
            st.session_state.df = df
            st.session_state.schema_description = None
    return tiles


def restore_version(version):
    snapshot = json.loads(version["tiles_snapshot"])
    tiles = []
    for tile_data in snapshot:
        config = tile_data["config"]
        if st.session_state.df is not None:
            fig = build_chart(
                st.session_state.df, config, len(tiles))
            tiles.append({
                "prompt": tile_data["prompt"],
                "config": config,
                "fig": fig,
                "width": tile_data.get("width", "half"),
                "height": tile_data.get("height", 320)
            })
    return tiles


def open_dashboard(dash):
    st.session_state.page = "builder"
    st.session_state.current_dashboard_name = dash["name"]
    st.session_state.current_dashboard_id = dash["id"]
    st.session_state.schema_description = None
    st.session_state.dashboard_insight = None
    st.session_state.insight_stale = False
    st.session_state.renaming = False
    st.session_state.active_filter = None
    st.session_state.chat_history = []
    st.session_state.forecast_result = None
    st.session_state.optimize_result = None
    st.session_state.tiles = load_dashboard_tiles(dash["id"])


def version_labels(versions):
    labels = [
        "Currently Published",
        "Backup 1 — Last Published",
        "Backup 2 — Previous"
    ]
    return [
        labels[i] if i < len(labels)
        else f"Version {v['version_num']}"
        for i, v in enumerate(versions)
    ]


def version_list_html(versions):
    labels = version_labels(versions)
    html = (
        "<div style='padding-left:12px;"
        "border-left:2px solid #e2e8f0;"
        "margin:4px 0 8px;'>"
    )
    for idx, v in enumerate(versions):
        label = labels[idx]
        date = v['published_at'][:10]
        color = "#6366f1" if idx == 0 else "#94a3b8"
        weight = "600" if idx == 0 else "400"
        html += (
            f"<p style='margin:3px 0;font-size:12px;"
            f"color:{color};font-weight:{weight};'>"
            f"&#8627; {label} "
            f"<span style='color:#94a3b8;font-weight:400;'>"
            f"&middot; {date}</span></p>"
        )
    html += "</div>"
    return html


def render_insight(insight):
    if not insight:
        return

    holistic = insight.get("holistic_summary", "")
    if holistic:
        st.markdown("""
        <div style='background:#f0fdf4;
        border:2px solid #86efac;
        border-radius:12px;padding:20px;
        margin:8px 0 16px;'>
            <p style='color:#166534;font-size:11px;
            font-weight:700;text-transform:uppercase;
            letter-spacing:0.08em;margin:0 0 10px;'>
            🧠 HOLISTIC BUSINESS SUMMARY</p>
        """, unsafe_allow_html=True)
        st.markdown(
            f"<p style='color:#1e293b;font-size:15px;"
            f"line-height:1.8;margin:0;font-weight:400;'>"
            f"{holistic}</p>",
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

    chart_insights = insight.get("chart_insights", [])
    if chart_insights:
        st.markdown(
            "<p style='font-size:12px;font-weight:700;"
            "color:#475569;text-transform:uppercase;"
            "letter-spacing:0.05em;margin:12px 0 8px;'>"
            "📈 Per-Chart Insights</p>",
            unsafe_allow_html=True
        )
        cols = st.columns(2)
        for i, ci in enumerate(chart_insights):
            with cols[i % 2]:
                st.markdown(
                    f"<div style='background:#f8fafc;"
                    f"border:1px solid #e2e8f0;"
                    f"border-radius:8px;"
                    f"padding:10px 14px;"
                    f"margin-bottom:8px;'>"
                    f"<p style='color:#6366f1;"
                    f"font-size:12px;font-weight:600;"
                    f"margin:0 0 4px;'>"
                    f"{ci.get('chart', '')}</p>"
                    f"<p style='color:#1e293b;"
                    f"font-size:13px;margin:0;"
                    f"line-height:1.5;'>"
                    f"{ci.get('insight', '')}</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )


# ── Session state ─────────────────────────────────
defaults = {
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
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Public share view ─────────────────────────────
params = st.query_params
if "share" in params:
    token = params["share"]
    dashboard = get_dashboard_by_token(token)
    if dashboard:
        versions = get_versions(dashboard["id"])
        latest_v = versions[0] if versions else None

        col_t, col_v = st.columns([4, 1])
        with col_t:
            st.title(f"📊 {dashboard['name']}")
            st.caption("Public dashboard · view only")
        with col_v:
            if latest_v:
                st.markdown(
                    f"<div style='margin-top:24px;"
                    f"background:#e0e7ff;border-radius:6px;"
                    f"padding:4px 12px;text-align:center;"
                    f"font-size:12px;font-weight:600;"
                    f"color:#4338ca;'>"
                    f"Currently Published · "
                    f"{latest_v['published_at'][:10]}"
                    f"</div>",
                    unsafe_allow_html=True
                )
        st.divider()

        tiles = get_dashboard_tiles(dashboard["id"])
        if tiles:
            first_tile = tiles[0]
            if first_tile.get("data_json"):
                df_pub = pd.read_json(
                    io.StringIO(first_tile["data_json"]))
                tile_objs = [
                    {"config": json.loads(t["chart_config"])}
                    for t in tiles
                ]
                if st.button("📝 Generate Executive Summary"):
                    with st.spinner("Analyzing dashboard..."):
                        insight = generate_dashboard_insights(
                            tile_objs, df_pub)
                    st.session_state.pub_insight = insight

                if ("pub_insight" in st.session_state
                        and st.session_state.pub_insight):
                    render_insight(st.session_state.pub_insight)

            st.divider()
            cols = st.columns(2)
            for i, tile in enumerate(tiles):
                config = json.loads(tile["chart_config"])
                with cols[i % 2]:
                    if tile.get("data_json"):
                        df = pd.read_json(
                            io.StringIO(tile["data_json"]))
                        fig = build_chart(df, config, i)
                        with st.container(border=True):
                            st.plotly_chart(
                                fig,
                                use_container_width=True,
                                key=f"pub_tile_{i}"
                            )
                    else:
                        st.info(
                            f"**{config['title']}** · "
                            f"{config['chart_type']}"
                        )
        else:
            st.info("No tiles on this dashboard yet.")
    else:
        st.error("Dashboard not found or link is invalid.")
    st.stop()

# ── Auth gate ──────────────────────────────────────
if st.session_state.user is None:
    show_auth()
    st.stop()

# ─────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────
with st.sidebar:
    st.title("🎨 VizGen")
    st.caption("AI Dashboard Builder")
    st.caption(f"👤 {st.session_state.user['name']}")
    if st.button("🚪 Log out", use_container_width=True):
        st.session_state.user = None
        st.session_state.page = "home"
        st.rerun()
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
        st.session_state.forecast_result = None
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
        st.session_state.forecast_result = None
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

# ─────────────────────────────────────────────────
# HOME PAGE
# ─────────────────────────────────────────────────
if st.session_state.page == "home":
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

# ─────────────────────────────────────────────────
# BUILDER PAGE
# ─────────────────────────────────────────────────
elif st.session_state.page == "builder":

    # ── STICKY TOP BAR ────────────────────────────
    with st.container():
        col_title, col_save, col_pub, col_pdf = st.columns(
            [3.3, 1, 1, 1.2])

        with col_title:
            dash_name = (
                st.session_state.current_dashboard_name
                or "Untitled Dashboard"
            )

            if st.session_state.renaming:
                new_name = st.text_input(
                    "Rename",
                    value=dash_name,
                    key="rename_input",
                    label_visibility="collapsed"
                )
                rc1, rc2 = st.columns([1, 1])
                with rc1:
                    if st.button("✅ Save name",
                                  use_container_width=True,
                                  key="save_name_btn"):
                        st.session_state\
                            .current_dashboard_name = new_name
                        if st.session_state\
                                .current_dashboard_id:
                            update_dashboard_name(
                                st.session_state
                                .current_dashboard_id,
                                new_name,
                                st.session_state.user["id"]
                            )
                        st.session_state.renaming = False
                        st.rerun()
                with rc2:
                    if st.button("✕ Cancel",
                                  use_container_width=True,
                                  key="cancel_name_btn"):
                        st.session_state.renaming = False
                        st.rerun()
            else:
                st.markdown(
                    f"<p style='font-size:22px;"
                    f"font-weight:700;color:#1e293b;"
                    f"margin:4px 0 0;'>"
                    f"📊 {dash_name}</p>",
                    unsafe_allow_html=True
                )
                if st.button("✏️ Rename",
                              key="rename_btn",
                              help="Rename this dashboard"):
                    st.session_state.renaming = True
                    st.rerun()

        with col_save:
            if st.button("💾 Save",
                          use_container_width=True,
                          key="save_btn"):
                name = (
                    st.session_state.current_dashboard_name
                    or "Untitled"
                )
                if st.session_state.current_dashboard_id:
                    did = st.session_state\
                        .current_dashboard_id
                    update_dashboard_name(
                        did, name, st.session_state.user["id"])
                    delete_dashboard_tiles(did)
                else:
                    did = save_dashboard(
                        name, st.session_state.user["id"], "draft")
                    st.session_state\
                        .current_dashboard_id = did
                for idx, tile in enumerate(
                        st.session_state.tiles):
                    tile_id = save_tile(
                        did, tile["prompt"], tile["config"],
                        idx, tile.get("width", "half"),
                        tile.get("height", 320),
                        st.session_state.df.to_json()
                        if st.session_state.df is not None
                        else None
                    )
                    save_prompt_history(
                        tile_id, tile["prompt"], tile["config"])
                st.success(
                    "Saved! Click 🔄 to refresh sidebar.")

        with col_pub:
            if st.button("🚀 Publish",
                          use_container_width=True,
                          type="primary",
                          key="publish_btn"):
                name = (
                    st.session_state.current_dashboard_name
                    or "Untitled"
                )
                if st.session_state.current_dashboard_id:
                    did = st.session_state\
                        .current_dashboard_id
                    existing = get_dashboard_by_id(did)
                    token = (
                        existing["share_token"]
                        if existing
                        and existing["share_token"]
                        else str(uuid.uuid4())[:8]
                    )
                    update_dashboard_publish(
                        did, token, st.session_state.user["id"])
                    delete_dashboard_tiles(did)
                else:
                    token = str(uuid.uuid4())[:8]
                    did = save_dashboard(
                        name, st.session_state.user["id"],
                        "published", token)
                    st.session_state\
                        .current_dashboard_id = did

                tiles_data = []
                for idx, tile in enumerate(
                        st.session_state.tiles):
                    tile_id = save_tile(
                        did, tile["prompt"], tile["config"],
                        idx, tile.get("width", "half"),
                        tile.get("height", 320),
                        st.session_state.df.to_json()
                        if st.session_state.df is not None
                        else None
                    )
                    save_prompt_history(
                        tile_id, tile["prompt"], tile["config"])
                    tiles_data.append({
                        "prompt": tile["prompt"],
                        "config": tile["config"],
                        "width": tile.get("width", "half"),
                        "height": tile.get("height", 320)
                    })
                version_num = save_version(
                    did, json.dumps(tiles_data))
                url = f"{BASE_URL}/?share={token}"
                st.success(
                    f"Published as "
                    f"**Version {version_num}**!")
                st.code(url, language=None)

        with col_pdf:
            if st.session_state.tiles:
                if st.button("📄 Export PDF",
                              use_container_width=True,
                              key="export_pdf_btn"):
                    with st.spinner("Rendering PDF..."):
                        name = (
                            st.session_state
                            .current_dashboard_name
                            or "Untitled Dashboard"
                        )
                        pdf_bytes = generate_dashboard_pdf(
                            name,
                            st.session_state.tiles,
                            st.session_state.dashboard_insight
                        )
                    st.download_button(
                        "⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name=(
                            f"{name.replace(' ', '_')}.pdf"
                        ),
                        mime="application/pdf",
                        use_container_width=True,
                        key="download_pdf_btn"
                    )

    st.divider()

    # ── REFRESH DATA ───────────────────────────────
    if st.session_state.tiles:
        with st.expander("🔄 Refresh Data", expanded=False):
            st.caption(
                "Upload a new CSV with the same columns to "
                "update every chart's numbers without "
                "rebuilding them."
            )
            refresh_file = st.file_uploader(
                "New data for this dashboard",
                type=["csv"],
                key="refresh_uploader",
                label_visibility="collapsed"
            )
            if refresh_file is not None:
                new_df = pd.read_csv(refresh_file)
                needed_cols = set()
                for t in st.session_state.tiles:
                    for field in ("x", "y", "y2", "color"):
                        val = t["config"].get(field)
                        if val and val != "count":
                            needed_cols.add(val)
                missing = needed_cols - set(new_df.columns)

                if missing:
                    st.error(
                        f"New CSV is missing column(s) used "
                        f"by your charts: {', '.join(missing)}. "
                        f"Refresh cancelled."
                    )
                else:
                    if st.button(
                            "✅ Apply Refresh",
                            type="primary",
                            use_container_width=True):
                        for i, t in enumerate(
                                st.session_state.tiles):
                            t["fig"] = build_chart(
                                new_df, t["config"], i)
                        st.session_state.df = new_df
                        st.session_state.datasets[
                            st.session_state.active_dataset
                        ] = new_df
                        st.session_state.schema_description = \
                            None
                        st.session_state.insight_stale = True
                        st.success(
                            "✅ Data refreshed! Click "
                            "💾 Save or 🚀 Publish to persist "
                            "it."
                        )
                        st.rerun()

    # ── Version history ───────────────────────────
    if st.session_state.current_dashboard_id:
        versions = get_versions(
            st.session_state.current_dashboard_id)
        older_versions = versions[1:] \
            if len(versions) > 1 else []
        if older_versions:
            labels = version_labels(versions)
            with st.expander(
                    f"🕐 Backup Versions · "
                    f"{len(older_versions)} backup(s) "
                    f"available",
                    expanded=False):
                for idx_v, v in enumerate(older_versions):
                    label = labels[idx_v + 1]
                    date = v['published_at'][:16]
                    st.markdown(
                        f"<p style='font-weight:600;"
                        f"font-size:13px;color:#475569;"
                        f"margin:8px 0 4px;'>"
                        f"&#8627; {label} "
                        f"<span style='color:#94a3b8;"
                        f"font-weight:400;font-size:12px;'>"
                        f"· {date}</span></p>",
                        unsafe_allow_html=True
                    )
                    snapshot = json.loads(
                        v["tiles_snapshot"])
                    with st.expander(
                            f"👁 Preview · "
                            f"{len(snapshot)} tile(s)",
                            expanded=False):
                        if st.session_state.df is not None:
                            prev_cols = st.columns(2)
                            for t_idx, t in enumerate(
                                    snapshot):
                                cfg = t["config"]
                                with prev_cols[t_idx % 2]:
                                    try:
                                        prev_fig = \
                                            build_chart(
                                                st.session_state.df,
                                                cfg, t_idx)
                                        st.plotly_chart(
                                            prev_fig,
                                            use_container_width=True,
                                            key=f"prev_{v['id']}_{t_idx}"
                                        )
                                        st.caption(
                                            cfg['title'])
                                    except Exception:
                                        st.info(
                                            f"**{cfg['title']}**"
                                        )
                        else:
                            for t in snapshot:
                                st.caption(
                                    t["config"]["title"])
                            st.caption(
                                "Upload CSV to preview.")

                    if st.button(
                            f"⏮ Restore {label}",
                            key=f"restore_{v['id']}",
                            use_container_width=True):
                        if st.session_state.df is not None:
                            restored = restore_version(v)
                            if restored:
                                st.session_state.tiles = \
                                    restored
                                st.session_state\
                                    .dashboard_insight = None
                                st.session_state\
                                    .insight_stale = False
                                st.success(
                                    f"✅ Restored! "
                                    f"Review then publish.")
                                st.rerun()
                        else:
                            st.warning(
                                "Upload your CSV first.")

                    if idx_v < len(older_versions) - 1:
                        st.markdown(
                            "<hr style='border:none;"
                            "border-top:1px solid #f1f5f9;"
                            "margin:8px 0;'>",
                            unsafe_allow_html=True
                        )

    # ── PROMPT HISTORY ─────────────────────────────
    if st.session_state.current_dashboard_id:
        history = get_dashboard_prompt_history(
            st.session_state.current_dashboard_id)
        if history:
            with st.expander(
                    f"📜 Prompt History · {len(history)} entries",
                    expanded=False):
                for h in history:
                    cfg = json.loads(h["chart_config"])
                    st.markdown(
                        f"<p style='margin:6px 0 0;"
                        f"font-size:13px;color:#1e293b;'>"
                        f"<b>{h['prompt_text']}</b></p>"
                        f"<p style='margin:0 0 8px;"
                        f"font-size:12px;color:#94a3b8;'>"
                        f"{cfg.get('chart_type', '')} · "
                        f"{str(h['created_at'])[:16]}</p>",
                        unsafe_allow_html=True
                    )

    # ── DATA SOURCE ───────────────────────────────
    st.subheader("📁 Data Source")
    st.caption(
        "Upload one or more CSV files. "
        "Switch between datasets per chart tile.")

    try:
        with open("sample.csv", "rb") as f:
            sample_bytes = f.read()
        st.download_button(
            label="📥 Download sample CSV to test",
            data=sample_bytes,
            file_name="sample.csv",
            mime="text/csv",
            help=(
                "Contains: region, revenue, "
                "units_sold, month — "
                "12 rows across 4 regions & 3 months"
            )
        )
    except Exception:
        pass

    uploaded_files = st.file_uploader(
        "Upload CSV files",
        type=["csv"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        for f in uploaded_files:
            if f.name not in st.session_state.datasets:
                df_new = pd.read_csv(f)
                st.session_state.datasets[f.name] = df_new
                st.success(
                    f"✓ {f.name} · "
                    f"{len(df_new)} rows · "
                    f"{len(df_new.columns)} columns")

    if st.session_state.datasets:
        dataset_names = list(
            st.session_state.datasets.keys())
        if len(dataset_names) == 1:
            st.session_state.active_dataset = \
                dataset_names[0]
        else:
            st.session_state.active_dataset = \
                st.selectbox(
                    "Active dataset:",
                    dataset_names,
                    key="dataset_selector"
                )

        raw_df = st.session_state.datasets[
            st.session_state.active_dataset]

        if len(dataset_names) > 1:
            st.markdown(
                f"<p style='font-size:12px;"
                f"color:#6366f1;font-weight:600;'>"
                f"📂 {len(dataset_names)} datasets loaded: "
                f"{', '.join(dataset_names)}</p>",
                unsafe_allow_html=True
            )

        if (st.session_state.schema_description is None
                or st.session_state.get(
                    "active_dataset_analyzed")
                != st.session_state.active_dataset):
            with st.spinner("Analyzing dataset..."):
                st.session_state.schema_description = \
                    analyze_schema(raw_df)
                st.session_state.active_dataset_analyzed \
                    = st.session_state.active_dataset
            st.session_state.active_filter = None
            st.session_state.chat_history = []
            st.session_state.forecast_result = None
            st.session_state.optimize_result = None

        if st.session_state.schema_description:
            st.info(st.session_state.schema_description)

        # ── NATURAL LANGUAGE FILTER ───────────────
        st.markdown(
            "<p style='font-size:13px;font-weight:700;"
            "color:#475569;margin:12px 0 4px;'>"
            "🔍 Filter Data</p>",
            unsafe_allow_html=True
        )
        filt_col, filt_btn_col = st.columns([4, 1])
        with filt_col:
            filter_prompt = st.text_input(
                "Describe a filter",
                placeholder=(
                    "e.g. only Q4 · exclude region West · "
                    "revenue over 5000"
                ),
                label_visibility="collapsed",
                key="filter_prompt_input"
            )
        with filt_btn_col:
            apply_filter_clicked = st.button(
                "Apply Filter", use_container_width=True)

        if apply_filter_clicked:
            if not filter_prompt.strip():
                st.warning("Describe a filter first.")
            else:
                with st.spinner("AI is applying your filter..."):
                    filter_config = generate_filter_config(
                        raw_df, filter_prompt)
                if filter_config.get("status") == "error":
                    st.error(
                        f"🤔 {filter_config.get('message', 'Could not apply filter.')}"
                    )
                else:
                    st.session_state.active_filter = filter_config
                    st.rerun()

        if st.session_state.active_filter:
            desc = st.session_state.active_filter.get(
                "description", "Filter active")
            chip_col, clear_col = st.columns([4, 1])
            with chip_col:
                st.markdown(
                    f"<div style='background:#eef2ff;"
                    f"border:1px solid #c7d2fe;"
                    f"border-radius:8px;padding:6px 12px;"
                    f"font-size:13px;color:#4338ca;"
                    f"font-weight:600;margin-top:4px;'>"
                    f"🔍 {desc}</div>",
                    unsafe_allow_html=True
                )
            with clear_col:
                if st.button("✕ Clear", use_container_width=True):
                    st.session_state.active_filter = None
                    st.rerun()

        st.session_state.df = apply_filters(
            raw_df, st.session_state.active_filter)

        if (st.session_state.active_filter
                and len(st.session_state.df) == 0):
            st.warning(
                "This filter matched 0 rows. "
                "Try a different filter or clear it.")

    # ── CHART BUILDER ─────────────────────────────
    if st.session_state.df is not None:
        st.divider()

        # ── ASK YOUR DATA (CHAT) ──────────────────
        st.subheader("💬 Ask Your Data")
        st.caption(
            "Chat with your dataset — ask questions in "
            "plain English and get real-number answers.")

        with st.container(height=320, border=True):
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"].replace("$", "\\$"))

        question = st.chat_input(
            "e.g. Which region grew the fastest?")

        if question:
            st.session_state.chat_history.append(
                {"role": "user", "content": question})
            with st.spinner("Thinking..."):
                answer = answer_data_question(
                    st.session_state.df, question,
                    st.session_state.chat_history)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": answer})
            st.rerun()

        st.divider()

        # ── FORECAST ───────────────────────────────
        st.subheader("🔮 Forecast")
        st.caption(
            "Describe what to forecast — AI picks the columns "
            "and time horizon, then a statistical model does "
            "the actual math.")

        numeric_cols = st.session_state.df.select_dtypes(
            include="number").columns.tolist()

        if not numeric_cols:
            st.caption(
                "No numeric columns available to forecast.")
        else:
            fcol, fbtn = st.columns([4, 1])
            with fcol:
                forecast_prompt = st.text_input(
                    "Describe what to forecast",
                    placeholder=(
                        "e.g. forecast revenue for the next "
                        "6 months"
                    ),
                    label_visibility="collapsed",
                    key="forecast_prompt_input"
                )
            with fbtn:
                fc_clicked = st.button(
                    "Generate Forecast", use_container_width=True)

            if fc_clicked:
                if not forecast_prompt.strip():
                    st.warning("Describe what to forecast first.")
                else:
                    with st.spinner("AI is reading your request..."):
                        fc_request = generate_forecast_request(
                            st.session_state.df, forecast_prompt)

                    if fc_request.get("status") == "error":
                        st.error(
                            f"🤔 {fc_request.get('message', 'Could not set up that forecast.')}"
                        )
                        st.session_state.forecast_result = None
                    else:
                        with st.spinner(
                                "Fitting trend and forecasting..."):
                            fc_result = generate_forecast(
                                st.session_state.df,
                                fc_request["time_column"],
                                fc_request["value_column"],
                                int(fc_request.get("periods", 3))
                            )
                        fc_result["value_column"] = \
                            fc_request["value_column"]
                        fc_result["periods"] = \
                            fc_request.get("periods", 3)
                        fc_result["description"] = \
                            fc_request.get("description", "")
                        st.session_state.forecast_result = fc_result

            fc_result = st.session_state.get("forecast_result")
            if fc_result:
                if fc_result["status"] == "error":
                    st.error(fc_result["message"])
                else:
                    if fc_result.get("description"):
                        st.caption(f"🔮 {fc_result['description']}")

                    fc_fig = go.Figure()
                    fc_fig.add_trace(go.Scatter(
                        x=fc_result["actual_labels"],
                        y=fc_result["actual_values"],
                        name="Actual", mode="lines+markers",
                        line=dict(color="#6366f1", width=2)
                    ))
                    boundary_x = (
                        [fc_result["actual_labels"][-1]]
                        + fc_result["forecast_labels"]
                    )
                    boundary_y = (
                        [fc_result["actual_values"][-1]]
                        + fc_result["forecast_values"]
                    )
                    fc_fig.add_trace(go.Scatter(
                        x=boundary_x, y=boundary_y,
                        name="Forecast", mode="lines+markers",
                        line=dict(
                            color="#f59e0b", width=2, dash="dash")
                    ))
                    fc_fig.update_layout(
                        title=(
                            f"{fc_result['value_column']} forecast "
                            f"— next {fc_result['periods']} "
                            f"period(s)"
                        ),
                        paper_bgcolor="white",
                        plot_bgcolor="#f8fafc",
                        height=360,
                        margin=dict(t=40, l=10, r=10, b=10),
                    )
                    st.plotly_chart(
                        fc_fig, use_container_width=True)
                    if not fc_result["used_real_dates"]:
                        st.caption(
                            "⚠️ Time column isn't a real date, so "
                            "forecast periods are shown as steps "
                            "ahead rather than calendar dates."
                        )

        st.divider()

        # ── OPTIMIZE ────────────────────────────────
        st.subheader("🧮 Optimize")
        st.caption(
            "Describe a budget to allocate — AI picks the "
            "category and metric, then a linear programming "
            "solver computes the actual split."
        )

        numeric_cols_opt = st.session_state.df.select_dtypes(
            include="number").columns.tolist()

        if not numeric_cols_opt:
            st.caption(
                "No numeric columns available to optimize.")
        else:
            ocol, obtn = st.columns([4, 1])
            with ocol:
                optimize_prompt = st.text_input(
                    "Describe the budget to allocate",
                    placeholder=(
                        "e.g. allocate $100,000 across regions "
                        "to maximize revenue"
                    ),
                    label_visibility="collapsed",
                    key="optimize_prompt_input"
                )
            with obtn:
                opt_clicked = st.button(
                    "Optimize", use_container_width=True,
                    key="optimize_btn")

            if opt_clicked:
                if not optimize_prompt.strip():
                    st.warning(
                        "Describe the budget to allocate first.")
                else:
                    with st.spinner("AI is reading your request..."):
                        opt_request = generate_optimization_request(
                            st.session_state.df, optimize_prompt)

                    if opt_request.get("status") == "error":
                        st.error(
                            f"🤔 {opt_request.get('message', 'Could not set up that optimization.')}"
                        )
                        st.session_state.optimize_result = None
                    else:
                        with st.spinner("Solving..."):
                            opt_result = optimize_budget_allocation(
                                st.session_state.df,
                                opt_request["category_column"],
                                opt_request["value_column"],
                                opt_request.get("total_budget")
                            )
                        opt_result["description"] = \
                            opt_request.get("description", "")
                        st.session_state.optimize_result = opt_result

            opt_result = st.session_state.get("optimize_result")
            if opt_result:
                if opt_result["status"] == "error":
                    st.error(opt_result["message"])
                else:
                    if opt_result.get("description"):
                        st.caption(f"🧮 {opt_result['description']}")

                    alloc = opt_result["allocations"]
                    opt_fig = go.Figure(go.Bar(
                        x=[a["category"] for a in alloc],
                        y=[a["amount"] for a in alloc],
                        marker_color="#6366f1",
                        text=[
                            f"${a['amount']:,.0f}" for a in alloc],
                        textposition="outside",
                    ))
                    opt_fig.update_layout(
                        title=(
                            f"Optimal allocation of "
                            f"${opt_result['total_budget']:,.0f} "
                            f"across {opt_result['category_column']}"
                        ),
                        paper_bgcolor="white",
                        plot_bgcolor="#f8fafc",
                        height=360,
                        margin=dict(t=40, l=10, r=10, b=10),
                    )
                    st.plotly_chart(
                        opt_fig, use_container_width=True)
                    st.caption(
                        "No single category can receive more than "
                        "50% of the budget, so the solver has to "
                        "genuinely diversify rather than putting "
                        "everything into the top performer. "
                        "Allocation is weighted by each category's "
                        f"historical average {opt_result['value_column']}."
                    )

        st.divider()

        # ── BUSINESS USE CASE MODE ────────────────
        st.subheader("🎯 Business Use Case Mode")
        st.caption(
            "Tell VizGen what you want to understand — "
            "AI auto-generates a full relevant dashboard.")

        use_case_col, mode_col, btn_col = st.columns(
            [3, 1, 1])
        with use_case_col:
            use_case = st.selectbox(
                "What do you want to understand?",
                [
                    "— Pick a use case —",
                    "Trend Analysis",
                    "Segment Analysis",
                    "Performance Overview",
                    "Correlation Analysis",
                    "Distribution Analysis",
                ],
                key="use_case_select"
            )
        with mode_col:
            st.markdown(
                "<div style='padding-top:24px;'>",
                unsafe_allow_html=True)
            replace_mode = st.radio(
                "Mode",
                ["Add", "Replace"],
                horizontal=True,
                key="use_case_mode"
            )
            st.markdown("</div>", unsafe_allow_html=True)
        with btn_col:
            st.markdown(
                "<div style='padding-top:24px;'>",
                unsafe_allow_html=True)
            gen_dashboard = st.button(
                "✨ Auto-Generate",
                type="primary",
                use_container_width=True,
                key="gen_dashboard_btn"
            )
            st.markdown("</div>", unsafe_allow_html=True)

        if gen_dashboard:
            if use_case == "— Pick a use case —":
                st.warning(
                    "Please pick a business use case.")
            else:
                with st.spinner(
                        f"AI is building a {use_case} "
                        f"dashboard..."):
                    configs = generate_use_case_dashboard(
                        st.session_state.df, use_case)

                if replace_mode == "Replace":
                    st.session_state.tiles = []
                    st.session_state.dashboard_insight \
                        = None
                    st.session_state.insight_stale = False

                added = 0
                for i, config in enumerate(configs):
                    if config.get("status") == "ok":
                        try:
                            fig = build_chart(
                                st.session_state.df,
                                config,
                                len(st.session_state.tiles)
                                + i
                            )
                            st.session_state.tiles.append({
                                "prompt": (
                                    f"Auto: {use_case} — "
                                    f"{config['title']}"
                                ),
                                "config": config,
                                "fig": fig,
                                "width": "half",
                                "height": 320,
                                "dataset_name":
                                    st.session_state
                                    .active_dataset
                            })
                            added += 1
                        except Exception:
                            pass

                if added > 0:
                    st.session_state.insight_stale = True
                    st.success(
                        f"✅ {added} charts added for "
                        f"**{use_case}**! "
                        f"({'Replaced' if replace_mode == 'Replace' else 'Added to canvas'})"
                    )
                    st.rerun()
                else:
                    st.error(
                        "Could not generate charts. "
                        "Try a different use case.")

        st.divider()

        # ── MANUAL CHART BUILDER ──────────────────
        st.subheader("📊 Add a Chart")
        st.caption(
            "Describe what you want — AI picks the best "
            "chart type automatically.")

        if len(st.session_state.datasets) > 1:
            tile_dataset = st.selectbox(
                "Dataset for this chart:",
                list(st.session_state.datasets.keys()),
                key="tile_dataset_select"
            )
            tile_df = st.session_state.datasets[
                tile_dataset]
        else:
            tile_df = st.session_state.df
            tile_dataset = st.session_state.active_dataset

        prompt = st.text_area(
            "Describe what you want",
            placeholder=(
                "e.g. Show revenue by region\n"
                "e.g. Show revenue AND units sold "
                "over months\n"
                "e.g. Which region has highest sales?"
            ),
            height=90,
            key="prompt_input"
        )

        if st.button("➕ Add Chart Tile", type="primary"):
            if not prompt.strip():
                st.warning(
                    "Please describe what you want.")
            else:
                with st.spinner(
                        "AI is building your chart..."):
                    config = generate_chart_config(
                        tile_df, prompt)

                if config.get("status") == "error":
                    st.error(
                        f"🤔 {config.get('message', 'Could not build.')}\n\n"
                        f"Try: 'Show revenue by region'"
                    )
                else:
                    try:
                        fig = build_chart(
                            tile_df, config,
                            len(st.session_state.tiles))
                        st.session_state.tiles.append({
                            "prompt": prompt,
                            "config": config,
                            "fig": fig,
                            "width": "half",
                            "height": 320,
                            "dataset_name": tile_dataset
                        })
                        st.session_state.insight_stale = \
                            True
                        st.rerun()
                    except Exception as e:
                        st.error(
                            f"Chart failed: {e}\n\n"
                            f"Try rephrasing.")

    # ── DASHBOARD CANVAS ──────────────────────────
    if st.session_state.tiles:
        st.divider()
        st.caption(
            f"{len(st.session_state.tiles)} tile(s) "
            f"on canvas")

        if st.session_state.df is not None:

            if (st.session_state.dashboard_insight
                    and st.session_state.insight_stale):
                st.warning(
                    "⚠️ Dashboard changed since summary "
                    "was generated. Click "
                    "**Refresh Summary** to update."
                )

            btn_label = (
                "🔄 Refresh Summary"
                if st.session_state.dashboard_insight
                else "📝 Generate Executive Summary"
            )

            if st.button(btn_label,
                          use_container_width=True):
                with st.spinner("AI is analyzing..."):
                    insight = generate_dashboard_insights(
                        st.session_state.tiles,
                        st.session_state.df
                    )
                st.session_state.dashboard_insight = insight
                st.session_state.insight_stale = False

            if st.session_state.dashboard_insight:
                render_insight(
                    st.session_state.dashboard_insight)

        st.divider()

        i = 0
        while i < len(st.session_state.tiles):
            tile = st.session_state.tiles[i]
            width = tile.get("width", "half")

            if width == "full":
                with st.container(border=True):
                    if tile.get("dataset_name"):
                        st.caption(
                            f"📂 {tile['dataset_name']}")
                    st.plotly_chart(
                        tile["fig"],
                        use_container_width=True,
                        key=f"tile_{i}")
                    with st.expander("⚙️ Edit tile"):
                        np_ = st.text_area(
                            "Prompt",
                            value=tile["prompt"],
                            key=f"ep_{i}",
                            height=60)
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            if st.button(
                                    "🔄 Regen",
                                    key=f"rg_{i}",
                                    use_container_width=True):
                                regen_df = (
                                    st.session_state
                                    .datasets.get(
                                        tile.get(
                                            "dataset_name"),
                                        st.session_state.df)
                                    if st.session_state
                                    .datasets
                                    else st.session_state.df
                                )
                                with st.spinner("..."):
                                    nc = \
                                        generate_chart_config(
                                            regen_df, np_)
                                    nf = build_chart(
                                        regen_df, nc, i)
                                st.session_state.tiles[
                                    i].update(
                                    {"prompt": np_,
                                     "config": nc,
                                     "fig": nf})
                                st.session_state\
                                    .insight_stale = True
                                st.rerun()
                        with c2:
                            w = st.selectbox(
                                "Width", ["full", "half"],
                                key=f"w_{i}")
                            if st.button(
                                    "Apply",
                                    key=f"aw_{i}",
                                    use_container_width=True):
                                st.session_state.tiles[i][
                                    "width"] = w
                                st.rerun()
                        with c3:
                            st.write("")
                            if st.button(
                                    "🗑️ Delete",
                                    key=f"dl_{i}",
                                    use_container_width=True):
                                st.session_state.tiles.pop(i)
                                st.session_state\
                                    .insight_stale = True
                                st.rerun()
                i += 1
            else:
                c1, c2 = st.columns(2)
                for col, idx in zip([c1, c2], [i, i + 1]):
                    if idx >= len(st.session_state.tiles):
                        break
                    t = st.session_state.tiles[idx]
                    with col:
                        with st.container(border=True):
                            if t.get("dataset_name"):
                                st.caption(
                                    f"📂 {t['dataset_name']}"
                                )
                            st.plotly_chart(
                                t["fig"],
                                use_container_width=True,
                                key=f"tile_{idx}")
                            with st.expander(
                                    "⚙️ Edit tile"):
                                np_ = st.text_area(
                                    "Prompt",
                                    value=t["prompt"],
                                    key=f"ep_{idx}",
                                    height=60)
                                c1b, c2b, c3b = \
                                    st.columns(3)
                                with c1b:
                                    if st.button(
                                            "🔄 Regen",
                                            key=f"rg_{idx}",
                                            use_container_width=True):
                                        regen_df = (
                                            st.session_state
                                            .datasets.get(
                                                t.get(
                                                    "dataset_name"),
                                                st.session_state.df)
                                            if st.session_state
                                            .datasets
                                            else
                                            st.session_state.df
                                        )
                                        with st.spinner(
                                                "..."):
                                            nc = \
                                                generate_chart_config(
                                                    regen_df,
                                                    np_)
                                            nf = \
                                                build_chart(
                                                    regen_df,
                                                    nc, idx)
                                        st.session_state\
                                            .tiles[idx]\
                                            .update(
                                            {"prompt": np_,
                                             "config": nc,
                                             "fig": nf})
                                        st.session_state\
                                            .insight_stale \
                                            = True
                                        st.rerun()
                                with c2b:
                                    w = st.selectbox(
                                        "Width",
                                        ["half", "full"],
                                        key=f"w_{idx}")
                                    if st.button(
                                            "Apply",
                                            key=f"aw_{idx}",
                                            use_container_width=True):
                                        st.session_state\
                                            .tiles[idx][
                                            "width"] = w
                                        st.rerun()
                                with c3b:
                                    st.write("")
                                    if st.button(
                                            "🗑️",
                                            key=f"dl_{idx}",
                                            use_container_width=True):
                                        st.session_state\
                                            .tiles.pop(idx)
                                        st.session_state\
                                            .insight_stale \
                                            = True
                                        st.rerun()
                i += 2