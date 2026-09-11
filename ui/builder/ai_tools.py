import plotly.graph_objects as go
import streamlit as st

from ai import (answer_data_question, generate_forecast_request,
                generate_optimization_request)
from forecasting import generate_forecast
from optimizer import optimize_budget_allocation
from ui.helpers import ai_budget_ok


def render():
    """Chat, forecasting and optimization over the loaded data."""
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

    # ── FORECAST ───────────────────────────────
    st.subheader("🔮 Forecast")
    st.caption(
        "Describe what to forecast — AI picks the columns "
        "and time horizon, then a statistical model does "
        "the actual math.")

    numeric_cols = st.session_state.df.select_dtypes(
        include="number").columns.tolist()

    if not numeric_cols:
        st.caption(
            "No numeric columns available to forecast.")
    else:
        fcol, fbtn = st.columns([4, 1])
        with fcol:
            forecast_prompt = st.text_input(
                "Describe what to forecast",
                placeholder=(
                    "e.g. forecast revenue for the next "
                    "6 months"
                ),
                label_visibility="collapsed",
                key="forecast_prompt_input"
            )
        with fbtn:
            fc_clicked = st.button(
                "Generate Forecast", use_container_width=True)

        if fc_clicked:
            if not forecast_prompt.strip():
                st.warning("Describe what to forecast first.")
            elif not ai_budget_ok():
                pass
            else:
                with st.spinner("AI is reading your request..."):
                    fc_request = generate_forecast_request(
                        st.session_state.df, forecast_prompt)

                if fc_request.get("status") == "error":
                    st.error(
                        f"🤔 {fc_request.get('message', 'Could not set up that forecast.')}"
                    )
                    st.session_state.forecast_result = None
                else:
                    with st.spinner(
                            "Fitting trend and forecasting..."):
                        fc_result = generate_forecast(
                            st.session_state.df,
                            fc_request["time_column"],
                            fc_request["value_column"],
                            int(fc_request.get("periods", 3))
                        )
                    fc_result["value_column"] = \
                        fc_request["value_column"]
                    fc_result["periods"] = \
                        fc_request.get("periods", 3)
                    fc_result["description"] = \
                        fc_request.get("description", "")
                    st.session_state.forecast_result = fc_result

        fc_result = st.session_state.get("forecast_result")
        if fc_result:
            if fc_result["status"] == "error":
                st.error(fc_result["message"])
            else:
                if fc_result.get("description"):
                    st.caption(f"🔮 {fc_result['description']}")

                fc_fig = go.Figure()
                fc_fig.add_trace(go.Scatter(
                    x=fc_result["actual_labels"],
                    y=fc_result["actual_values"],
                    name="Actual", mode="lines+markers",
                    line=dict(color="#6366f1", width=2)
                ))
                boundary_x = (
                    [fc_result["actual_labels"][-1]]
                    + fc_result["forecast_labels"]
                )
                boundary_y = (
                    [fc_result["actual_values"][-1]]
                    + fc_result["forecast_values"]
                )
                fc_fig.add_trace(go.Scatter(
                    x=boundary_x, y=boundary_y,
                    name="Forecast", mode="lines+markers",
                    line=dict(
                        color="#f59e0b", width=2, dash="dash")
                ))
                fc_fig.update_layout(
                    title=(
                        f"{fc_result['value_column']} forecast "
                        f"— next {fc_result['periods']} "
                        f"period(s)"
                    ),
                    paper_bgcolor="white",
                    plot_bgcolor="#f8fafc",
                    height=360,
                    margin=dict(t=40, l=10, r=10, b=10),
                )
                st.plotly_chart(
                    fc_fig, use_container_width=True)
                if not fc_result["used_real_dates"]:
                    st.caption(
                        "⚠️ Time column isn't a real date, so "
                        "forecast periods are shown as steps "
                        "ahead rather than calendar dates."
                    )

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

                alloc = opt_result["allocations"]
                opt_fig = go.Figure(go.Bar(
                    x=[a["category"] for a in alloc],
                    y=[a["amount"] for a in alloc],
                    marker_color="#6366f1",
                    text=[
                        f"${a['amount']:,.0f}" for a in alloc],
                    textposition="outside",
                ))
                opt_fig.update_layout(
                    title=(
                        f"Optimal allocation of "
                        f"${opt_result['total_budget']:,.0f} "
                        f"across {opt_result['category_column']}"
                    ),
                    paper_bgcolor="white",
                    plot_bgcolor="#f8fafc",
                    height=360,
                    margin=dict(t=40, l=10, r=10, b=10),
                )
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

    st.divider()

