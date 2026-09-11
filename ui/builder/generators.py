import streamlit as st

from ai import generate_chart_config, generate_use_case_dashboard
from charts import build_chart
from ui.helpers import ai_budget_ok


def render():
    """Business-use-case autogeneration and the manual builder."""
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
        elif not ai_budget_ok():
            pass
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
        elif not ai_budget_ok():
            pass
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

