import streamlit as st

from ai import answer_data_question, generate_optimization_request
from charts import build_chart
from optimizer import optimize_budget_allocation
from ui.helpers import ai_budget_ok


def render():
    """Chat and optimization over the loaded data."""
    # ── ASK YOUR DATA (CHAT) ──────────────────
    st.subheader("💬 Ask Your Data")
    st.caption(
        "Chat with your dataset — ask questions in "
        "plain English and get real-number answers.")

    with st.container(height=320, border=True):
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"].replace("$", "\\$"))

    question = st.chat_input(
        "e.g. Which region grew the fastest?")

    if question:
        if ai_budget_ok():
            st.session_state.chat_history.append(
                {"role": "user", "content": question})
            with st.spinner("Thinking..."):
                answer = answer_data_question(
                    st.session_state.df, question,
                    st.session_state.chat_history)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": answer})
            st.rerun()

    st.divider()


    # ── OPTIMIZE ────────────────────────────────
    st.subheader("🧮 Optimize")
    st.caption(
        "Describe a budget to allocate — AI picks the "
        "category and metric, then a linear programming "
        "solver computes the actual split."
    )

    numeric_cols_opt = st.session_state.df.select_dtypes(
        include="number").columns.tolist()

    if not numeric_cols_opt:
        st.caption(
            "No numeric columns available to optimize.")
    else:
        ocol, obtn = st.columns([4, 1])
        with ocol:
            optimize_prompt = st.text_input(
                "Describe the budget to allocate",
                placeholder=(
                    "e.g. allocate $100,000 across regions "
                    "to maximize revenue"
                ),
                label_visibility="collapsed",
                key="optimize_prompt_input"
            )
        with obtn:
            opt_clicked = st.button(
                "Optimize", use_container_width=True,
                key="optimize_btn")

        if opt_clicked:
            if not optimize_prompt.strip():
                st.warning(
                    "Describe the budget to allocate first.")
            elif not ai_budget_ok():
                pass
            else:
                with st.spinner("AI is reading your request..."):
                    opt_request = generate_optimization_request(
                        st.session_state.df, optimize_prompt)

                if opt_request.get("status") == "error":
                    st.error(
                        f"🤔 {opt_request.get('message', 'Could not set up that optimization.')}"
                    )
                    st.session_state.optimize_result = None
                else:
                    with st.spinner("Solving..."):
                        opt_result = optimize_budget_allocation(
                            st.session_state.df,
                            opt_request["category_column"],
                            opt_request["value_column"],
                            opt_request.get("total_budget")
                        )
                    opt_result["description"] = \
                        opt_request.get("description", "")
                    st.session_state.optimize_result = opt_result

        opt_result = st.session_state.get("optimize_result")
        if opt_result:
            if opt_result["status"] == "error":
                st.error(opt_result["message"])
            else:
                if opt_result.get("description"):
                    st.caption(f"🧮 {opt_result['description']}")

                opt_config = {
                    "chart_type": "allocation",
                    "category_column":
                        opt_result["category_column"],
                    "value_column": opt_result["value_column"],
                    "total_budget": opt_result["total_budget"],
                    "title": (
                        f"Optimal allocation of "
                        f"${opt_result['total_budget']:,.0f} "
                        f"across {opt_result['category_column']}"
                    ),
                }
                opt_fig = build_chart(
                    st.session_state.df, opt_config)
                st.plotly_chart(
                    opt_fig, use_container_width=True)
                st.caption(
                    "No single category can receive more than "
                    "50% of the budget, so the solver has to "
                    "genuinely diversify rather than putting "
                    "everything into the top performer. "
                    "Allocation is weighted by each category's "
                    f"historical average {opt_result['value_column']}."
                )

                if st.button("➕ Add allocation to dashboard",
                             key="add_allocation_tile"):
                    st.session_state.tiles.append({
                        "prompt": opt_result.get(
                            "description", "Budget allocation"),
                        "config": opt_config,
                        "fig": opt_fig,
                        "width": "half",
                        "height": 320,
                        "dataset_name":
                            st.session_state.active_dataset,
                    })
                    st.session_state.insight_stale = True
                    st.success(
                        "Added — save or publish to keep it.")
                    st.rerun()

    st.divider()

