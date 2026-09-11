import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from forecasting import generate_forecast
from optimizer import optimize_budget_allocation

COLORS = ["#6366f1", "#10b981", "#f59e0b",
          "#ef4444", "#3b82f6", "#8b5cf6"]


def _empty_chart(message):
    fig = go.Figure()
    fig.add_annotation(
        text=message, showarrow=False,
        font=dict(size=13, color="#94a3b8"))
    fig.update_layout(
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        paper_bgcolor="white", plot_bgcolor="#f8fafc", height=320)
    return fig


def build_forecast_chart(df, config):
    """
    Rebuild a forecast tile from its stored parameters.

    The AI call that chose these columns happened once, when the
    tile was created; recomputing here is pure statistics, so a
    saved forecast costs nothing to reload and re-forecasts
    automatically when the underlying data is refreshed.
    """
    result = generate_forecast(
        df, config["time_column"], config["value_column"],
        int(config.get("periods", 3)))

    if result["status"] != "ok":
        return _empty_chart(result.get("message", "Forecast failed"))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=result["actual_labels"], y=result["actual_values"],
        name="Actual", mode="lines+markers",
        line=dict(color="#6366f1", width=2)
    ))
    fig.add_trace(go.Scatter(
        x=[result["actual_labels"][-1]] + result["forecast_labels"],
        y=[result["actual_values"][-1]] + result["forecast_values"],
        name="Forecast", mode="lines+markers",
        line=dict(color="#f59e0b", width=2, dash="dash")
    ))
    fig.update_layout(
        title=config.get("title", "Forecast"),
        paper_bgcolor="white", plot_bgcolor="#f8fafc",
        height=360, margin=dict(t=40, l=10, r=10, b=10),
    )
    return fig


def build_allocation_chart(df, config):
    """Rebuild a budget-allocation tile by re-solving the LP."""
    result = optimize_budget_allocation(
        df, config["category_column"], config["value_column"],
        config.get("total_budget"))

    if result["status"] != "ok":
        return _empty_chart(
            result.get("message", "Optimization failed"))

    alloc = result["allocations"]
    fig = go.Figure(go.Bar(
        x=[a["category"] for a in alloc],
        y=[a["amount"] for a in alloc],
        marker_color="#6366f1",
        text=[f"${a['amount']:,.0f}" for a in alloc],
        textposition="outside",
    ))
    fig.update_layout(
        title=config.get("title", "Optimal allocation"),
        paper_bgcolor="white", plot_bgcolor="#f8fafc",
        height=360, margin=dict(t=40, l=10, r=10, b=10),
    )
    return fig


def build_chart(df, config, tile_index=0):
    chart_type = config["chart_type"]

    # Analytical tiles carry their own parameters rather than the
    # x/y/color shape the plotting types below expect.
    if chart_type == "forecast":
        return build_forecast_chart(df, config)
    if chart_type == "allocation":
        return build_allocation_chart(df, config)

    x = config["x"]
    y = config["y"]
    y2 = config.get("y2")
    color = config.get("color")
    title = config["title"]
    base_color = COLORS[tile_index % len(COLORS)]

    # Handle count-based charts
    use_count = (y == "count" or x == y)

    if use_count and chart_type != "histogram":
        if color:
            df_plot = df.groupby(
                [x, color]).size().reset_index(name="count")
        else:
            df_plot = df.groupby(
                x).size().reset_index(name="count")
        y = "count"
    else:
        df_plot = df.copy()
        try:
            if chart_type not in [
                    "scatter", "box", "histogram",
                    "dual_line", "dual_bar", "grouped_bar"]:
                if pd.api.types.is_numeric_dtype(df_plot[y]):
                    if color:
                        df_plot = df_plot.groupby(
                            [x, color],
                            as_index=False)[y].sum()
                    else:
                        df_plot = df_plot.groupby(
                            x, as_index=False)[y].sum()
        except Exception:
            pass

    # Dual line
    if chart_type == "dual_line" and y2:
        try:
            agg = df.groupby(x, as_index=False).agg(
                {y: "sum", y2: "sum"})
        except Exception:
            agg = df_plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=agg[x], y=agg[y], name=y,
            mode="lines+markers",
            line=dict(color=COLORS[0], width=2),
            marker=dict(size=7)
        ))
        fig.add_trace(go.Scatter(
            x=agg[x], y=agg[y2], name=y2,
            mode="lines+markers",
            line=dict(color=COLORS[1], width=2),
            marker=dict(size=7)
        ))
        fig.update_layout(title=title)

    # Dual bar
    elif chart_type == "dual_bar" and y2:
        try:
            agg = df.groupby(x, as_index=False).agg(
                {y: "sum", y2: "sum"})
        except Exception:
            agg = df_plot
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=agg[x], y=agg[y], name=y,
            marker_color=COLORS[0]
        ))
        fig.add_trace(go.Bar(
            x=agg[x], y=agg[y2], name=y2,
            marker_color=COLORS[1]
        ))
        fig.update_layout(title=title, barmode="group")

    elif chart_type == "bar":
        fig = px.bar(
            df_plot, x=x, y=y, title=title,
            color=color if color else None,
            color_discrete_sequence=COLORS
            if color else [base_color]
        )

    elif chart_type == "grouped_bar":
        fig = px.bar(
            df_plot, x=x, y=y, title=title,
            color=color if color else None,
            barmode="group",
            color_discrete_sequence=COLORS
        )

    elif chart_type == "line":
        fig = px.line(
            df_plot, x=x, y=y, title=title,
            color=color if color else None,
            color_discrete_sequence=COLORS
            if color else [base_color],
            markers=True
        )

    elif chart_type == "area":
        fig = px.area(
            df_plot, x=x, y=y, title=title,
            color=color if color else None,
            color_discrete_sequence=COLORS
            if color else [base_color]
        )

    elif chart_type == "pie":
        fig = px.pie(
            df_plot, names=x, values=y, title=title,
            color_discrete_sequence=
            px.colors.qualitative.Pastel
        )

    elif chart_type == "scatter":
        fig = px.scatter(
            df_plot, x=x, y=y, title=title,
            color=color if color else None,
            color_discrete_sequence=COLORS
            if color else [base_color]
        )

    elif chart_type == "histogram":
        fig = px.histogram(
            df_plot, x=x, title=title,
            color=color if color else None,
            color_discrete_sequence=COLORS
            if color else [base_color]
        )

    elif chart_type == "box":
        fig = px.box(
            df_plot, x=x, y=y, title=title,
            color=color if color else None,
            color_discrete_sequence=COLORS
            if color else [base_color]
        )

    elif chart_type == "funnel":
        fig = px.funnel(
            df_plot, x=y, y=x, title=title,
            color_discrete_sequence=[base_color]
        )

    else:
        fig = px.bar(
            df_plot, x=x, y=y, title=title,
            color_discrete_sequence=[base_color]
        )

    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="#f8fafc",
        font=dict(family="sans-serif", size=12,
                  color="#1e293b"),
        title_font=dict(size=14, color="#1e293b"),
        margin=dict(t=40, l=10, r=10, b=10),
        height=320,
        showlegend=chart_type in [
            "pie", "grouped_bar", "dual_line",
            "dual_bar"] or color is not None,
        xaxis=dict(
            showgrid=False,
            showline=True,
            linecolor="#e2e8f0"
        ) if chart_type != "pie" else {},
        yaxis=dict(
            showgrid=True,
            gridcolor="#f1f5f9",
            showline=False
        ) if chart_type != "pie" else {},
    )
    return fig