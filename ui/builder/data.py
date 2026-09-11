import pandas as pd
import streamlit as st

from ai import analyze_schema, generate_filter_config
from filters import apply_filters
from ui.helpers import ai_budget_ok


def render():
    """Upload CSVs, pick the active dataset, apply NL filters."""
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
            # Fires automatically on upload, so stay quiet when out
            # of quota rather than showing an error on every rerun.
            if ai_budget_ok(quiet=True):
                with st.spinner("Analyzing dataset..."):
                    st.session_state.schema_description = \
                        analyze_schema(raw_df)
            else:
                st.session_state.schema_description = (
                    "Daily AI limit reached — dataset loaded, but "
                    "the AI summary is unavailable right now."
                )
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
            elif not ai_budget_ok():
                pass
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

