import anthropic
import os
import json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Use Streamlit secrets if available (deployed), else use .env (local)
try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    api_key = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=api_key)


def analyze_schema(df):
    columns = df.columns.tolist()
    dtypes = df.dtypes.astype(str).to_dict()
    sample = df.head(3).to_string()

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": f"""
            Dataset columns: {columns}
            Column types: {dtypes}
            Sample:
            {sample}

            Describe in 2 sentences what this dataset is about.
            """
        }]
    )
    return message.content[0].text


def generate_chart_config(df, user_prompt):
    columns = df.columns.tolist()
    dtypes = df.dtypes.astype(str).to_dict()
    sample = df.head(10).to_string()

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": f"""
You are a data visualization expert.

Dataset columns: {columns}
Column types: {dtypes}
Sample data:
{sample}

User request: "{user_prompt}"

RULES:
1. x = primary category/dimension (usually categorical or date)
2. y = first numeric measure
3. y2 = second numeric measure (ONLY when user wants to
   compare two metrics on same chart). Set to null otherwise.
4. color = grouping column for multi-series. null if not needed.
5. If user wants count/distribution of one column,
   set y = "count". Do NOT pick another column as y.
6. If request is ambiguous and you cannot determine
   x or y with confidence, return error object.
7. For dual-metric charts (e.g. revenue AND units sold
   over time): use chart_type "dual_line" or "dual_bar",
   set y = first metric, y2 = second metric.
8. For pie: x = category, y = numeric or "count"

CHART TYPES:
- bar: x=category, y=numeric
- grouped_bar: x=category, y=numeric, color=group
- line: x=ordered, y=numeric, color=optional group
- dual_line: x=ordered, y=metric1, y2=metric2
  (two lines, different colors, same chart)
- dual_bar: x=category, y=metric1, y2=metric2
  (grouped bars for two metrics)
- area: x=ordered, y=numeric
- pie: x=category, y=numeric or count
- scatter: x=numeric, y=numeric, color=optional
- histogram: x=numeric
- box: x=category, y=numeric
- funnel: x=category, y=numeric

Return ONLY one of these JSON formats:

SUCCESS:
{{
    "status": "ok",
    "chart_type": "line",
    "x": "column_name",
    "y": "column_name or count",
    "y2": null,
    "color": null,
    "title": "chart title"
}}

ERROR:
{{
    "status": "error",
    "message": "what is unclear and what user should specify"
}}

No markdown. No explanation. Raw JSON only.
            """
        }]
    )

    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def generate_dashboard_insights(tiles, df):
    charts_context = ""
    for i, tile in enumerate(tiles):
        config = tile["config"]
        charts_context += (
            f"Chart {i+1}: {config['title']} — "
            f"{config['chart_type']} chart, "
            f"X: {config['x']}, Y: {config['y']}\n"
        )

    data_summary = df.describe().to_string()
    sample = df.head(20).to_string()

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": f"""
            I have a dashboard with these charts:
            {charts_context}

            Dataset summary:
            {data_summary}

            Sample data:
            {sample}

            Return ONLY a JSON object like this:
            {{
                "chart_insights": [
                    {{"chart": "Chart title here",
                      "insight": "1 sentence insight"}},
                    {{"chart": "Chart title here",
                      "insight": "1 sentence insight"}}
                ],
                "overall": "2-3 sentence executive summary"
            }}

            No markdown. No explanation. Raw JSON only.
            Be specific with numbers from the data.
            """
        }]
    )

    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)