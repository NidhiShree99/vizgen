# 🎨 VizGen — AI-Powered Dashboard Builder

> Describe your chart in plain English. Get a live, interactive, shareable dashboard in seconds.

**Live Demo:** [vizgenanalytics.streamlit.app](https://vizgenanalytics.streamlit.app)  
**Built by:** Nidhi Shree | [GitHub](https://github.com/NidhiShree99)

---

## 🧠 The Problem

At ExxonMobil, I used Power BI daily. The pain wasn't building charts — it was **sharing them**.

- Sharing required IT tickets and licenses
- Stakeholders needed Power BI installed to view dashboards
- There was no version control — one wrong publish and the old version was gone
- Non-technical teammates couldn't build their own charts

**VizGen solves all of this.**

---

## ✨ What VizGen Does

Upload a CSV. Describe what you want to see in plain English. Get a live interactive dashboard with a shareable URL — no license, no IT ticket, no technical skills required.

---

## 🚀 Features

### 📊 AI Chart Generation
- Describe your chart in plain English — VizGen figures out the best visualization
- Supports: Bar, Grouped Bar, Line, Dual-Line, Area, Pie, Scatter, Histogram, Box, Funnel
- Dual-metric charts: plot two measures on the same chart (e.g. revenue AND units sold over time)
- Smart error handling: if your prompt is ambiguous, VizGen asks for clarification instead of guessing wrong

### 📁 Dashboard Management
- Build multi-tile dashboards with a 2-column grid layout
- Edit any tile's prompt and regenerate the chart
- Resize tiles (half width / full width)
- Save as draft or publish with a shareable URL

### 🔗 Live Shareable Dashboards
- Every published dashboard gets a unique public URL
- Anyone with the link can view live interactive charts — no login required
- Charts are stored with data so they render perfectly for viewers

### 🕐 Version Control
- Every publish creates a new version snapshot
- Keeps last 3 versions: Currently Published + 2 backups
- Preview older versions with actual live charts before restoring
- One-click restore to any backup version

### 🤖 AI Executive Summary
- Click "Generate Executive Summary" to get AI-written business insights
- Per-chart insights + one overall business narrative
- Reads your actual data, not generic text
- Available on both builder and public share view

---

## 🆚 How VizGen is Different

| Feature | VizGen | Julius AI | Power BI | ChatGPT ADA |
|---|---|---|---|---|
| Natural language charts | ✅ | ✅ | ❌ | ✅ |
| Live shareable URL | ✅ | ❌ | ✅ (license needed) | ❌ |
| Version control | ✅ | ❌ | ❌ | ❌ |
| AI executive summary | ✅ | ❌ | ❌ | ❌ |
| Free & open source | ✅ | ❌ | ❌ | ❌ |
| No login to view | ✅ | ❌ | ❌ | ❌ |

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend & App | Streamlit |
| AI / LLM | Anthropic Claude API (Haiku) |
| Charts | Plotly |
| Database | SQLite |
| Language | Python 3.13 |
| Deployment | Streamlit Cloud |

---

## 📂 Project Structure

```
vizgen/
├── app.py          # Main Streamlit app — all UI and page logic
├── db.py           # All SQLite database functions
├── ai.py           # All Claude API calls
├── charts.py       # Plotly chart rendering
├── requirements.txt
├── sample.csv      # Sample dataset to test with
└── .gitignore
```

---

## 🏃 Run Locally

**1. Clone the repo:**
```bash
git clone https://github.com/NidhiShree99/vizgen.git
cd vizgen
```

**2. Install dependencies:**
```bash
pip install -r requirements.txt
```

**3. Get your Anthropic API key:**
- Go to [console.anthropic.com](https://console.anthropic.com)
- Sign up for a free account ($5 free credits included)
- Create an API key

**4. Create a `.env` file:**
```
ANTHROPIC_API_KEY=your-key-here
```

**5. Run the app:**
```bash
streamlit run app.py
```

**6. Open your browser:**
```
http://localhost:8501
```

---

## 📖 How to Use

1. Click **New Dashboard** in the sidebar
2. Upload a **CSV file**
3. Describe your chart in plain English:
   - *"Show revenue by region as a bar chart"*
   - *"Show revenue AND units sold over months"*
   - *"Distribution of regions as a pie chart"*
4. Add multiple chart tiles to build your dashboard
5. Click **📝 Generate Executive Summary** for AI insights
6. Click **🚀 Publish** to get a shareable link
7. Share the URL — viewers see live interactive charts, no login needed

---

## 🗄 Database Schema

```sql
dashboards         — id, name, status, share_token, created_at
tiles              — id, dashboard_id, prompt, chart_type,
                     chart_config, position, width, height, data_json
dashboard_versions — id, dashboard_id, version_num,
                     tiles_snapshot, published_at
prompt_history     — id, tile_id, prompt_text, chart_config, created_at
```

---

## 🎯 Product Decisions & Tradeoffs

**Why Streamlit?** Fastest path from Python to interactive web app. Tradeoff: limited layout control compared to React.

**Why SQLite?** Zero setup, file-based, perfect for a single-user portfolio project. Tradeoff: doesn't scale to multi-user without switching to PostgreSQL.

**Why Claude Haiku?** Fastest and cheapest Anthropic model. Chart config generation needs speed, not deep reasoning. Tradeoff: occasionally needs clearer prompts for complex requests.

**Why keep last 3 versions?** Balances storage cost with safety net. Most rollbacks happen within 1-2 versions. More than 3 adds complexity without real benefit.

---

## 🔮 Future Roadmap (v2)

- [ ] User authentication and team accounts
- [ ] Live database connections (PostgreSQL, MySQL)
- [ ] Scheduled data refresh
- [ ] Embed dashboards in Notion/Confluence via iframe
- [ ] Export dashboard as PDF
- [ ] Prompt history and undo functionality
- [ ] Natural language filters ("show only Q1 data")

---

## 👩‍💻 About

Built by **Nidhi Shree** during Spring Break 2026 as a portfolio project for PM/TPM roles.

Background: Scrum Master + Data Integration Engineer at ExxonMobil (2020-2024). Currently pursuing MSIS at UW-Madison.

[LinkedIn](#) | [GitHub](https://github.com/NidhiShree99)

---

*VizGen is an open source project. Feel free to fork, star, and contribute!*
