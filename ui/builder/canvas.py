import streamlit as st

from ai import generate_chart_config, generate_dashboard_insights
from charts import build_chart
from ui.helpers import ai_budget_ok, render_insight

# Tiles rebuilt from their own parameters rather than from a prompt.
# Regenerating one from its prompt would silently turn it into an
# ordinary chart, so that control is disabled for them.
ANALYTICAL_TYPES = ("forecast", "allocation")
REGEN_BLOCKED_HELP = (
    "Forecast and allocation tiles rebuild from their own settings, "
    "not from a prompt."
)


def render():
    """Tile grid, per-tile editing, and the executive summary."""
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
                if ai_budget_ok():
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
                            blocked = tile["config"][
                                "chart_type"] in ANALYTICAL_TYPES
                            if st.button(
                                    "🔄 Regen",
                                    key=f"rg_{i}",
                                    use_container_width=True,
                                    disabled=blocked,
                                    help=REGEN_BLOCKED_HELP
                                    if blocked else None) \
                                    and ai_budget_ok():
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
                                    blocked = t["config"][
                                        "chart_type"] \
                                        in ANALYTICAL_TYPES
                                    if st.button(
                                            "🔄 Regen",
                                            key=f"rg_{idx}",
                                            use_container_width=True,
                                            disabled=blocked,
                                            help=REGEN_BLOCKED_HELP
                                            if blocked else None) \
                                            and ai_budget_ok():
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
