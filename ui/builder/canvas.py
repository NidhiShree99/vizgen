import streamlit as st

from ai import generate_chart_config, generate_dashboard_insights
from charts import build_chart
from ui.helpers import ai_budget_ok, render_insight

# Tiles rebuilt from their own parameters rather than from a prompt.
# Regenerating one from its prompt would silently turn it into an
# ordinary chart, so that control is disabled for them.
ANALYTICAL_TYPES = ("allocation",)
REGEN_BLOCKED_HELP = (
    "Allocation tiles rebuild from their own settings, "
    "not from a prompt."
)

CHART_TYPES = [
    "bar", "grouped_bar", "line", "dual_line", "dual_bar",
    "area", "pie", "scatter", "histogram", "box", "funnel",
]
DUAL_TYPES = ("dual_line", "dual_bar")
NONE_LABEL = "— none —"


def _tile_dataframe(tile):
    """The dataset this tile was built from."""
    datasets = st.session_state.datasets or {}
    return datasets.get(
        tile.get("dataset_name"), st.session_state.df)


def _option_index(options, current):
    """Preselect the current value, tolerating stale config."""
    try:
        return options.index(current)
    except ValueError:
        return 0


def _apply_config(index, config):
    """Rebuild a tile from an edited config. No AI call involved."""
    tile = st.session_state.tiles[index]
    df = _tile_dataframe(tile)
    tile["config"] = config
    tile["fig"] = build_chart(df, config, index)
    st.session_state.insight_stale = True


def _render_chart_editor(index, tile):
    """
    Direct controls for an ordinary chart.

    Prompting is good at creating a chart and poor at correcting one,
    so the last-mile fixes — wrong chart type, wrong column, clumsy
    title — happen here instead of by re-rolling the prompt. It is
    pure config manipulation, so it costs nothing and is instant.
    """
    config = dict(tile["config"])
    df = _tile_dataframe(tile)
    columns = list(df.columns) if df is not None else []
    optional = [NONE_LABEL] + columns

    title = st.text_input(
        "Title", value=config.get("title", ""), key=f"t_{index}")

    e1, e2 = st.columns(2)
    with e1:
        chart_type = st.selectbox(
            "Chart type", CHART_TYPES,
            index=_option_index(
                CHART_TYPES, config.get("chart_type")),
            key=f"ct_{index}")
    with e2:
        x = st.selectbox(
            "X axis", columns,
            index=_option_index(columns, config.get("x")),
            key=f"x_{index}")

    e3, e4 = st.columns(2)
    with e3:
        y_options = ["count"] + columns
        y = st.selectbox(
            "Y axis", y_options,
            index=_option_index(y_options, config.get("y")),
            key=f"y_{index}")
    with e4:
        color = st.selectbox(
            "Group by", optional,
            index=_option_index(
                optional, config.get("color") or NONE_LABEL),
            key=f"c_{index}")

    y2 = config.get("y2")
    if chart_type in DUAL_TYPES:
        y2 = st.selectbox(
            "Second metric", optional,
            index=_option_index(optional, y2 or NONE_LABEL),
            key=f"y2_{index}")
        y2 = None if y2 == NONE_LABEL else y2

    if st.button("Apply changes", key=f"ap_{index}",
                 type="primary", use_container_width=True):
        config.update({
            "title": title,
            "chart_type": chart_type,
            "x": x,
            "y": y,
            "color": None if color == NONE_LABEL else color,
            "y2": y2 if chart_type in DUAL_TYPES else None,
        })
        _apply_config(index, config)
        st.rerun()


def _render_analytical_editor(index, tile):
    """Direct controls for an allocation tile: title and budget."""
    config = dict(tile["config"])

    title = st.text_input(
        "Title", value=config.get("title", ""), key=f"t_{index}")
    budget = st.number_input(
        "Budget", min_value=1.0,
        value=float(config.get("total_budget", 1000)),
        step=1000.0, key=f"bg_{index}")

    if st.button("Apply changes", key=f"ap_{index}",
                 type="primary", use_container_width=True):
        config.update(
            {"title": title, "total_budget": float(budget)})
        _apply_config(index, config)
        st.rerun()


def _render_regen(index, tile):
    """Prompt-based regeneration, for charts the AI created."""
    blocked = tile["config"]["chart_type"] in ANALYTICAL_TYPES
    prompt = st.text_area(
        "Describe it differently", value=tile["prompt"],
        key=f"ep_{index}", height=68, disabled=blocked)

    if st.button("🔄 Regenerate with AI", key=f"rg_{index}",
                 use_container_width=True, disabled=blocked,
                 help=REGEN_BLOCKED_HELP if blocked else None) \
            and ai_budget_ok():
        df = _tile_dataframe(tile)
        with st.spinner("Rebuilding..."):
            config = generate_chart_config(df, prompt)
            fig = build_chart(df, config, index)
        st.session_state.tiles[index].update(
            {"prompt": prompt, "config": config, "fig": fig})
        st.session_state.insight_stale = True
        st.rerun()


def _render_tile(index):
    """One tile: the chart plus its editor."""
    tile = st.session_state.tiles[index]

    with st.container(border=True):
        if tile.get("dataset_name"):
            st.caption(f"📂 {tile['dataset_name']}")
        st.plotly_chart(
            tile["fig"], use_container_width=True,
            key=f"tile_{index}")

        with st.expander("⚙️ Edit tile"):
            if tile["config"]["chart_type"] in ANALYTICAL_TYPES:
                _render_analytical_editor(index, tile)
            else:
                _render_chart_editor(index, tile)

            st.divider()
            _render_regen(index, tile)

            st.divider()
            w1, w2 = st.columns(2)
            with w1:
                width = st.selectbox(
                    "Width", ["half", "full"],
                    index=_option_index(
                        ["half", "full"],
                        tile.get("width", "half")),
                    key=f"w_{index}")
                if width != tile.get("width", "half"):
                    st.session_state.tiles[index]["width"] = width
                    st.rerun()
            with w2:
                st.write("")
                if st.button("🗑️ Delete tile", key=f"dl_{index}",
                             use_container_width=True):
                    st.session_state.tiles.pop(index)
                    st.session_state.insight_stale = True
                    st.rerun()


def render():
    """Tile grid, per-tile editing, and the executive summary."""
    if not st.session_state.tiles:
        return

    st.divider()
    st.caption(
        f"{len(st.session_state.tiles)} tile(s) on canvas")

    if st.session_state.df is not None:
        if (st.session_state.dashboard_insight
                and st.session_state.insight_stale):
            st.warning(
                "⚠️ Dashboard changed since summary was "
                "generated. Click **Refresh Summary** to update."
            )

        btn_label = (
            "🔄 Refresh Summary"
            if st.session_state.dashboard_insight
            else "📝 Generate Executive Summary"
        )

        if st.button(btn_label, use_container_width=True):
            if ai_budget_ok():
                with st.spinner("AI is analyzing..."):
                    insight = generate_dashboard_insights(
                        st.session_state.tiles,
                        st.session_state.df
                    )
                st.session_state.dashboard_insight = insight
                st.session_state.insight_stale = False

        if st.session_state.dashboard_insight:
            render_insight(st.session_state.dashboard_insight)

    st.divider()

    i = 0
    while i < len(st.session_state.tiles):
        if st.session_state.tiles[i].get("width") == "full":
            _render_tile(i)
            i += 1
        else:
            left, right = st.columns(2)
            for col, idx in zip([left, right], [i, i + 1]):
                if idx >= len(st.session_state.tiles):
                    break
                with col:
                    _render_tile(idx)
            i += 2
