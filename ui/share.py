import io
import json

import pandas as pd
import streamlit as st

from ai import generate_dashboard_insights
from charts import build_chart
from db import get_dashboard_by_token, get_dashboard_tiles, get_versions
from ui.helpers import ai_budget_ok, render_insight


def render_if_share_link():
    """Public read-only view. Runs before the auth gate."""
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
                        f"{str(latest_v['published_at'])[:10]}"
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
                        # No logged-in user here — this page is public,
                        # so the cost is billed to the dashboard owner.
                        if ai_budget_ok(dashboard.get("user_id")):
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
