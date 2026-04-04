import streamlit as st
import pandas as pd
import uuid
import json
import io
from db import (create_tables, save_dashboard, get_user_dashboards,
                save_tile, get_dashboard_tiles, delete_dashboard,
                delete_dashboard_tiles, get_dashboard_by_token,
                get_dashboard_by_id, update_dashboard_name,
                update_dashboard_publish, save_version,
                get_versions)
from ai import (analyze_schema, generate_chart_config,
                generate_dashboard_insights)
from charts import build_chart

create_tables()

st.set_page_config(page_title="VizGen", layout="wide")


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
                "height": tile.get("height", 320)
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
    st.markdown("""
    <div style='background:#f0fdf4;
    border:1px solid #86efac;
    border-radius:10px;padding:16px;
    margin:8px 0 12px;'>
        <p style='color:#166534;font-size:12px;
        font-weight:700;text-transform:uppercase;
        letter-spacing:0.05em;margin:0 0 8px;'>
        📊 Overall Executive Summary</p>
    """, unsafe_allow_html=True)
    st.markdown(
        f"<p style='color:#1e293b;font-size:14px;"
        f"line-height:1.7;margin:0;'>"
        f"{insight.get('overall', '')}"
        f"</p>",
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
        for ci in chart_insights:
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
    "current_dashboard_name": "",
    "current_dashboard_id": None,
    "schema_description": None,
    "dashboard_insight": None,
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

# ─────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────
with st.sidebar:
    st.title("🎨 VizGen")
    st.caption("AI Dashboard Builder")
    st.divider()

    if st.button("🏠 Home", use_container_width=True):
        st.session_state.page = "home"
        st.session_state.tiles = []
        st.session_state.df = None
        st.session_state.schema_description = None
        st.session_state.dashboard_insight = None
        st.rerun()

    if st.button("➕ New Dashboard",
                  use_container_width=True,
                  type="primary"):
        st.session_state.page = "builder"
        st.session_state.tiles = []
        st.session_state.df = None
        st.session_state.current_dashboard_name = ""
        st.session_state.current_dashboard_id = None
        st.session_state.schema_description = None
        st.session_state.dashboard_insight = None
        st.rerun()

    st.divider()

    col_title, col_refresh = st.columns([3, 1])
    with col_title:
        st.markdown("**My Dashboards**")
    with col_refresh:
        if st.button("🔄", help="Refresh list"):
            st.rerun()

    dashboards = get_user_dashboards()
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
                    f"http://localhost:8501"
                    f"/?share={dash['share_token']}",
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
                    delete_dashboard(dash["id"])
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
                    delete_dashboard(dash["id"])
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

    dashboards = get_user_dashboards()
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
                        f"http://localhost:8501"
                        f"/?share={dash['share_token']}",
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
                    delete_dashboard(dash["id"])
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
                    delete_dashboard(dash["id"])
                    st.rerun()
            st.divider()

    if not dashboards:
        st.info(
            "No dashboards yet. "
            "Click **➕ New Dashboard** in the sidebar!")

    st.subheader("🚀 Getting Started")
    st.markdown("""
    1. Click **New Dashboard** in the sidebar
    2. Upload a **CSV file**
    3. Describe your chart in plain English
    4. Add multiple chart tiles
    5. Click **📝 Generate Executive Summary**
    6. **Publish** → get a shareable link
    """)

# ─────────────────────────────────────────────────
# BUILDER PAGE
# ─────────────────────────────────────────────────
elif st.session_state.page == "builder":

    col_name, col_save, col_pub = st.columns([4, 1, 1])
    with col_name:
        st.session_state.current_dashboard_name = st.text_input(
            "name",
            value=st.session_state.current_dashboard_name,
            placeholder="Untitled Dashboard",
            label_visibility="collapsed"
        )

    with col_save:
        if st.button("💾 Save", use_container_width=True):
            name = (st.session_state.current_dashboard_name
                    or "Untitled")
            if st.session_state.current_dashboard_id:
                did = st.session_state.current_dashboard_id
                update_dashboard_name(did, name)
                delete_dashboard_tiles(did)
            else:
                did = save_dashboard(name, "draft")
                st.session_state.current_dashboard_id = did
            for idx, tile in enumerate(st.session_state.tiles):
                save_tile(
                    did, tile["prompt"], tile["config"],
                    idx, tile.get("width", "half"),
                    tile.get("height", 320),
                    st.session_state.df.to_json()
                    if st.session_state.df is not None else None
                )
            st.success("Saved! Click 🔄 to refresh sidebar.")

    with col_pub:
        if st.button("🚀 Publish",
                      use_container_width=True,
                      type="primary"):
            name = (st.session_state.current_dashboard_name
                    or "Untitled")
            if st.session_state.current_dashboard_id:
                did = st.session_state.current_dashboard_id
                existing = get_dashboard_by_id(did)
                token = (existing["share_token"]
                         if existing and existing["share_token"]
                         else str(uuid.uuid4())[:8])
                update_dashboard_publish(did, token)
                delete_dashboard_tiles(did)
            else:
                token = str(uuid.uuid4())[:8]
                did = save_dashboard(name, "published", token)
                st.session_state.current_dashboard_id = did

            tiles_data = []
            for idx, tile in enumerate(st.session_state.tiles):
                save_tile(
                    did, tile["prompt"], tile["config"],
                    idx, tile.get("width", "half"),
                    tile.get("height", 320),
                    st.session_state.df.to_json()
                    if st.session_state.df is not None else None
                )
                tiles_data.append({
                    "prompt": tile["prompt"],
                    "config": tile["config"],
                    "width": tile.get("width", "half"),
                    "height": tile.get("height", 320)
                })
            version_num = save_version(
                did, json.dumps(tiles_data))
            url = f"http://localhost:8501/?share={token}"
            st.success(
                f"Published as **Version {version_num}**!")
            st.code(url, language=None)

    st.divider()

    # ── Version history ───────────────────────────
    if st.session_state.current_dashboard_id:
        versions = get_versions(
            st.session_state.current_dashboard_id)
        older_versions = versions[1:] if len(versions) > 1 \
            else []
        if older_versions:
            labels = version_labels(versions)
            with st.expander(
                    f"🕐 Backup Versions · "
                    f"{len(older_versions)} backup(s) available",
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

                    snapshot = json.loads(v["tiles_snapshot"])
                    with st.expander(
                            f"👁 Preview · "
                            f"{len(snapshot)} tile(s)",
                            expanded=False):
                        if st.session_state.df is not None:
                            prev_cols = st.columns(2)
                            for t_idx, t in enumerate(snapshot):
                                cfg = t["config"]
                                with prev_cols[t_idx % 2]:
                                    try:
                                        prev_fig = build_chart(
                                            st.session_state.df,
                                            cfg, t_idx)
                                        st.plotly_chart(
                                            prev_fig,
                                            use_container_width=True,
                                            key=f"prev_{v['id']}_{t_idx}"
                                        )
                                        st.caption(cfg['title'])
                                    except Exception:
                                        st.info(
                                            f"**{cfg['title']}**"
                                            f" · {cfg['chart_type']}"
                                        )
                        else:
                            for t in snapshot:
                                cfg = t["config"]
                                st.markdown(
                                    f"<div style='background:#f8fafc;"
                                    f"border:1px solid #e2e8f0;"
                                    f"border-radius:6px;"
                                    f"padding:6px 10px;"
                                    f"margin-bottom:4px;'>"
                                    f"<p style='color:#6366f1;"
                                    f"font-size:12px;"
                                    f"font-weight:600;"
                                    f"margin:0 0 1px;'>"
                                    f"{cfg['title']}</p>"
                                    f"<p style='color:#64748b;"
                                    f"font-size:11px;margin:0;'>"
                                    f"{cfg['chart_type'].upper()}"
                                    f" · X: {cfg['x']}"
                                    f" · Y: {cfg['y']}</p>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )
                            st.caption(
                                "Upload CSV to see previews.")

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
                                st.success(
                                    f"✅ Restored to {label}!"
                                    f" Review then publish.")
                                st.rerun()
                        else:
                            st.warning(
                                "Upload your CSV first "
                                "to restore a version.")

                    if idx_v < len(older_versions) - 1:
                        st.markdown(
                            "<hr style='border:none;"
                            "border-top:1px solid #f1f5f9;"
                            "margin:8px 0;'>",
                            unsafe_allow_html=True
                        )

    # ── Upload ────────────────────────────────────
    st.subheader("📁 Data Source")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        st.session_state.df = pd.read_csv(uploaded_file)
        st.success(
            f"✓ {uploaded_file.name} · "
            f"{len(st.session_state.df)} rows · "
            f"{len(st.session_state.df.columns)} columns")
        if st.session_state.schema_description is None:
            with st.spinner("Analyzing your data..."):
                st.session_state.schema_description = \
                    analyze_schema(st.session_state.df)

    if st.session_state.schema_description:
        st.info(st.session_state.schema_description)

    # ── Chart builder ─────────────────────────────
    if st.session_state.df is not None:
        st.divider()
        st.subheader("📊 Add a Chart")
        st.caption(
            "Describe your chart in plain English. "
            "Dropdowns are optional hints.")

        c1, c2, c3 = st.columns(3)
        with c1:
            x_col = st.selectbox(
                "X axis (optional hint)",
                ["Let AI decide"] +
                st.session_state.df.columns.tolist(),
                key="x_col")
        with c2:
            y_col = st.selectbox(
                "Y axis (optional hint)",
                ["Let AI decide"] +
                st.session_state.df.columns.tolist(),
                key="y_col")
        with c3:
            chart_hint = st.selectbox(
                "Chart type (optional hint)",
                ["Let AI decide", "bar", "grouped_bar",
                 "line", "dual_line", "dual_bar",
                 "area", "pie", "scatter",
                 "histogram", "box", "funnel"],
                key="chart_hint")

        hint_parts = []
        if x_col != "Let AI decide":
            hint_parts.append(f"X axis: {x_col}")
        if y_col != "Let AI decide":
            hint_parts.append(f"Y axis: {y_col}")
        if chart_hint != "Let AI decide":
            hint_parts.append(f"chart type: {chart_hint}")
        hint_str = (
            f" (hints: {', '.join(hint_parts)})"
            if hint_parts else ""
        )

        prompt = st.text_area(
            "Describe what you want",
            placeholder=(
                "e.g. Show revenue by region as a bar chart\n"
                "e.g. Show distribution of regions\n"
                "e.g. Show revenue AND units sold over months\n"
                "e.g. Compare revenue and units sold by region"
            ),
            height=90,
            key="prompt_input"
        )

        if st.button("➕ Add Chart Tile", type="primary"):
            if not prompt.strip():
                st.warning(
                    "Please describe what you want to see.")
            else:
                full_prompt = prompt + hint_str
                with st.spinner(
                        "AI is building your chart..."):
                    config = generate_chart_config(
                        st.session_state.df, full_prompt)

                if config.get("status") == "error":
                    st.error(
                        f"🤔 {config.get('message', 'Could not build chart.')}\n\n"
                        f"**Try being more specific**, e.g.:\n"
                        f"- 'Show revenue AND units_sold over month'\n"
                        f"- 'Show revenue by region'\n"
                        f"- 'Show count of rows per region'"
                    )
                else:
                    try:
                        fig = build_chart(
                            st.session_state.df, config,
                            len(st.session_state.tiles))
                        st.session_state.tiles.append({
                            "prompt": prompt,
                            "config": config,
                            "fig": fig,
                            "width": "half",
                            "height": 320
                        })
                        st.rerun()
                    except Exception as e:
                        st.error(
                            f"Chart could not be built: {e}\n\n"
                            f"Try rephrasing your request."
                        )

    # ── Dashboard canvas ──────────────────────────
    if st.session_state.tiles:
        st.divider()
        canvas_name = (
            st.session_state.current_dashboard_name
            or "Untitled Dashboard"
        )
        st.subheader(f"📊 {canvas_name}")
        st.caption(f"{len(st.session_state.tiles)} tile(s)")

        if st.session_state.df is not None:
            if st.button("📝 Generate Executive Summary",
                          use_container_width=True):
                with st.spinner(
                        "AI is analyzing your dashboard..."):
                    insight = generate_dashboard_insights(
                        st.session_state.tiles,
                        st.session_state.df
                    )
                st.session_state.dashboard_insight = insight

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
                                with st.spinner("..."):
                                    nc = generate_chart_config(
                                        st.session_state.df,
                                        np_)
                                    nf = build_chart(
                                        st.session_state.df,
                                        nc, i)
                                st.session_state.tiles[i].update(
                                    {"prompt": np_,
                                     "config": nc,
                                     "fig": nf})
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
                            st.plotly_chart(
                                t["fig"],
                                use_container_width=True,
                                key=f"tile_{idx}")
                            with st.expander("⚙️ Edit tile"):
                                np_ = st.text_area(
                                    "Prompt",
                                    value=t["prompt"],
                                    key=f"ep_{idx}",
                                    height=60)
                                c1b, c2b, c3b = st.columns(3)
                                with c1b:
                                    if st.button(
                                            "🔄 Regen",
                                            key=f"rg_{idx}",
                                            use_container_width=True):
                                        with st.spinner("..."):
                                            nc = generate_chart_config(
                                                st.session_state.df,
                                                np_)
                                            nf = build_chart(
                                                st.session_state.df,
                                                nc, idx)
                                        st.session_state.tiles[
                                            idx].update(
                                            {"prompt": np_,
                                             "config": nc,
                                             "fig": nf})
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
                                        st.session_state.tiles[
                                            idx]["width"] = w
                                        st.rerun()
                                with c3b:
                                    st.write("")
                                    if st.button(
                                            "🗑️",
                                            key=f"dl_{idx}",
                                            use_container_width=True):
                                        st.session_state.tiles.pop(
                                            idx)
                                        st.rerun()
                i += 2