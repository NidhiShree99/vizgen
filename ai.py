import anthropic
import os
import json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    api_key = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=api_key)


def analyze_schema(df):
    columns = df.columns.tolist()
    dtypes = df.dtypes.astype(str).to_dict()
    sample = df.head(5).to_string()

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": f"""
            Dataset columns: {columns}
            Column types: {dtypes}
            Sample:
            {sample}

            Describe in 2 sentences what this dataset is about.
            Mention what kind of analysis it is best suited for.
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
1. x = primary category/dimension (categorical or date)
2. y = first numeric measure
3. y2 = second numeric measure ONLY when user wants to
   compare two metrics on same chart. null otherwise.
4. color = grouping column for multi-series. null if not needed.
5. If user wants count/distribution of one column,
   set y = "count".
6. If request is ambiguous, infer the BEST chart from the data.
   Never return an error if you can make a reasonable guess.
7. For dual-metric charts use chart_type "dual_line" or
   "dual_bar", set y = first metric, y2 = second metric.
8. For pie: x = category, y = numeric or "count"
9. ALWAYS pick the most insightful chart_type automatically
   based on data types and user intent — do not default to bar
   unless it is truly the best choice.

CHART TYPE SELECTION GUIDE:
- Trends over time → line or dual_line
- Part of whole / distribution → pie
- Comparison across categories → bar or grouped_bar
- Two metrics together → dual_line or dual_bar
- Relationship between numbers → scatter
- Frequency distribution → histogram
- Spread and outliers → box
- Sequential stages → funnel

CHART TYPES AVAILABLE:
bar, grouped_bar, line, dual_line, dual_bar,
area, pie, scatter, histogram, box, funnel

Return ONLY this JSON:

{{
    "status": "ok",
    "chart_type": "line",
    "x": "column_name",
    "y": "column_name or count",
    "y2": null,
    "color": null,
    "title": "chart title"
}}

No markdown. No explanation. Raw JSON only.
            """
        }]
    )

    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def generate_filter_config(df, filter_prompt):
    columns = df.columns.tolist()
    dtypes = df.dtypes.astype(str).to_dict()
    sample = df.head(10).to_string()

    uniques = {}
    for col in df.columns:
        if df[col].dtype == "object" and df[col].nunique() <= 25:
            uniques[col] = df[col].unique().tolist()

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": f"""
You are a data filtering expert.

Dataset columns: {columns}
Column types: {dtypes}
Sample data:
{sample}
Known category values (for text columns): {uniques}

User filter request: "{filter_prompt}"

RULES:
1. Translate the request into one or more filter conditions
   using ONLY real column names and real values seen above.
2. For things like "Q4" or "last quarter", map to the actual
   matching category values from "Known category values"
   (e.g. months Oct/Nov/Dec) if a matching column exists.
3. Supported operators: ==, !=, >, <, >=, <=, contains,
   not_contains, in
4. Use "in" with a list value when multiple values should match
   the same column (e.g. Q4 months).
5. logic is "AND" or "OR" across all conditions.
6. If the request cannot be mapped to real columns/values,
   return {{"status": "error", "message": "short reason"}}.

Return ONLY this JSON:
{{
    "status": "ok",
    "conditions": [
        {{"column": "column_name", "operator": "==", "value": "value"}}
    ],
    "logic": "AND",
    "description": "short human-readable summary of the filter"
}}

No markdown. No explanation. Raw JSON only.
            """
        }]
    )

    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def generate_use_case_dashboard(df, use_case):
    """
    Given a business use case, auto-generate a full set
    of chart configs that best address that use case.
    """
    columns = df.columns.tolist()
    dtypes = df.dtypes.astype(str).to_dict()
    sample = df.head(10).to_string()
    stats = df.describe().to_string()

    use_case_guides = {
        "Trend Analysis": "Focus on how metrics change over time. Use line charts, area charts, and dual-line charts to show trends, momentum, and comparisons over a time dimension.",
        "Segment Analysis": "Focus on comparing performance across categories/segments. Use bar charts, grouped bars, and pie charts to show which segments dominate, underperform, or differ.",
        "Performance Overview": "Give a comprehensive overview of all key metrics. Mix chart types — use bar for totals, pie for share, line for trends — to tell the full story.",
        "Correlation Analysis": "Focus on relationships between numeric variables. Use scatter plots, dual-line charts, and histograms to show how variables relate to each other.",
        "Distribution Analysis": "Focus on how data is distributed. Use histograms, box plots, and pie charts to show spread, outliers, and proportions.",
    }

    guide = use_case_guides.get(
        use_case,
        "Generate the most insightful charts for this dataset."
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": f"""
You are a senior data analyst and visualization expert.

Dataset columns: {columns}
Column types: {dtypes}
Sample data:
{sample}
Statistics:
{stats}

Business use case requested: "{use_case}"
Guidance: {guide}

Generate exactly 4 chart configurations that best serve
this use case for this specific dataset.

Each chart must use different columns or chart types to
provide complementary insights — not repeat the same view.

CHART TYPES AVAILABLE:
bar, grouped_bar, line, dual_line, dual_bar,
area, pie, scatter, histogram, box, funnel

Return ONLY this JSON — an array of 4 chart configs:
[
  {{
    "status": "ok",
    "chart_type": "line",
    "x": "column_name",
    "y": "column_name or count",
    "y2": null,
    "color": null,
    "title": "descriptive chart title"
  }},
  ...
]

No markdown. No explanation. Raw JSON array only.
            """
        }]
    )

    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def generate_dashboard_insights(tiles, df):
    """
    Generate per-chart insights + strong holistic summary.
    """
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
        max_tokens=1200,
        messages=[{
            "role": "user",
            "content": f"""
You are a senior business analyst presenting to a C-suite audience.

Dashboard charts:
{charts_context}

Dataset statistics:
{data_summary}

Sample data:
{sample}

Return ONLY this JSON:
{{
    "holistic_summary": "Write 4-6 sentences as if presenting to a CEO. Start with the single most important finding. Then connect patterns across ALL charts into one coherent business story. End with one specific, data-backed recommendation. Use actual numbers from the data. This should read like a McKinsey executive summary — sharp, direct, insightful.",
    "chart_insights": [
        {{"chart": "exact chart title", "insight": "1 sharp sentence with a specific number or percentage from the data"}},
        {{"chart": "exact chart title", "insight": "1 sharp sentence with a specific number or percentage from the data"}}
    ]
}}

No markdown. No explanation. Raw JSON only.
Be specific with real numbers. Never use vague language.
            """
        }]
    )

    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def generate_forecast_request(df, forecast_prompt):
    """
    Parse a natural-language forecasting request into a concrete
    time column, value column, and number of periods. The actual
    forecasting math is done separately by forecasting.py — this
    only interprets intent, never computes numbers itself.
    """
    columns = df.columns.tolist()
    dtypes = df.dtypes.astype(str).to_dict()
    sample = df.head(5).to_string()
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=250,
        messages=[{
            "role": "user",
            "content": f"""
You are helping configure a time-series forecast.

Dataset columns: {columns}
Column types: {dtypes}
Numeric columns (only these can be forecasted): {numeric_cols}
Sample data:
{sample}

User request: "{forecast_prompt}"

RULES:
1. time_column must be a real column name that represents time
   (a date, month, year, or similar sequential column).
2. value_column must be one of the numeric columns listed above —
   the metric the user wants to forecast.
3. periods is how many future steps to forecast. Infer a
   reasonable number from the request (e.g. "next 6 months" -> 6,
   "next quarter" -> 3). Default to 3 if not specified.
4. If no plausible time column or numeric value column exists,
   return {{"status": "error", "message": "short reason"}}.

Return ONLY this JSON:
{{
    "status": "ok",
    "time_column": "column_name",
    "value_column": "column_name",
    "periods": 3,
    "description": "short human-readable summary of the forecast"
}}

No markdown. No explanation. Raw JSON only.
            """
        }]
    )

    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def answer_data_question(df, question, history=None):
    """
    Answer a natural-language question about the dataset,
    conversationally, using recent chat history for context.
    """
    columns = df.columns.tolist()
    dtypes = df.dtypes.astype(str).to_dict()
    sample = df.head(10).to_string()
    stats = df.describe().to_string()

    history_text = "\n".join(
        f"{h['role']}: {h['content']}"
        for h in (history or [])[-6:]
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": f"""
You are a sharp data analyst chatting with a business user about
their dataset.

Dataset columns: {columns}
Column types: {dtypes}
Sample data:
{sample}
Statistics:
{stats}

Conversation so far:
{history_text}

New question: "{question}"

Answer directly and conversationally in 2-4 sentences, using real
numbers from the data whenever possible. If the question can't be
answered from this dataset, say so honestly and suggest what data
would be needed instead of guessing.

Plain conversational text only. No markdown headers, no JSON.
            """
        }]
    )

    return message.content[0].text.strip()