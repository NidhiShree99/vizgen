import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

COLORS = ["#6366f1", "#10b981", "#f59e0b",
          "#ef4444", "#3b82f6", "#8b5cf6"]


def build_chart(df, config, tile_index=0):
    chart_type = config["chart_type"]
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
                    "dual_line", "dual_bar",
                    "grouped_bar"]:
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

    # ── Dual line chart ───────────────────────────
    if chart_type == "dual_line" and y2:
        try:
            agg = df.groupby(x, as_index=False).agg(
                {y: "sum", y2: "sum"})
        except Exception:
            agg = df_plot

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=agg[x], y=agg[y],
            name=y,
            mode="lines+markers",
            line=dict(color=COLORS[0], width=2),
            marker=dict(size=7)
        ))
        fig.add_trace(go.Scatter(
            x=agg[x], y=agg[y2],
            name=y2,
            mode="lines+markers",
            line=dict(color=COLORS[1], width=2),
            marker=dict(size=7)
        ))
        fig.update_layout(title=title)

    # ── Dual bar chart ────────────────────────────
    elif chart_type == "dual_bar" and y2:
        try:
            agg = df.groupby(x, as_index=False).agg(
                {y: "sum", y2: "sum"})
        except Exception:
            agg = df_plot

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=agg[x], y=agg[y],
            name=y,
            marker_color=COLORS[0]
        ))
        fig.add_trace(go.Bar(
            x=agg[x], y=agg[y2],
            name=y2,
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