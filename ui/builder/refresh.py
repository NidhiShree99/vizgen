import pandas as pd
import streamlit as st

from charts import build_chart


def render():
    """Swap in a new CSV and re-render every tile against it."""
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

