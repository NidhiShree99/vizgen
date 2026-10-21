import io
import json

import pandas as pd
import streamlit as st

from charts import build_chart
from db import get_dashboard_tiles
from quota import try_consume


def ai_budget_ok(user_id=None, quiet=False):
    """
    Reserve one AI call against a user's daily quota before calling
    the Claude API. Returns False (and surfaces an error) when the
    user is out of budget, so the caller must skip the API call.

    user_id is passed explicitly for the public share view, where
    there is no logged-in user and usage is billed to the dashboard
    owner instead.
    """
    uid = user_id
    if uid is None:
        current = st.session_state.get("user")
        uid = current["id"] if current else None

    allowed, used, limit = try_consume(uid)
    if not allowed and not quiet:
        st.error(
            f"Daily AI limit reached ({limit} requests per 24 "
            f"hours). This resets on a rolling basis — try again "
            f"later."
        )
    return allowed


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
        date = str(v['published_at'])[:10]
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
