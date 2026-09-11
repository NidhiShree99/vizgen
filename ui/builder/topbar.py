import uuid

import streamlit as st

from db import (delete_dashboard_tiles, get_dashboard_by_id,
                save_dashboard, save_prompt_history, save_tile,
                save_version, update_dashboard_name,
                update_dashboard_publish)
import json
from pdf_export import generate_dashboard_pdf
from ui.config import BASE_URL


def render():
    """Sticky bar: title, rename, save, publish, PDF export."""
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

