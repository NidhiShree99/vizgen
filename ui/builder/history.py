import json

import streamlit as st

from charts import build_chart
from db import get_dashboard_prompt_history, get_versions
from ui.helpers import restore_version, version_labels


def render():
    """Version backups and the prompt log for this dashboard."""
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

