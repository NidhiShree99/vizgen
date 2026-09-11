import streamlit as st


def inject_global_css():
    st.markdown("""
    <style>
        .stApp { background: #f8fafc; }
        #MainMenu, footer, header { visibility: hidden; }
        .stDeployButton { display: none; }

        [data-testid="stAppViewBlockContainer"] > div:first-child {
            position: sticky !important;
            top: 0 !important;
            z-index: 999 !important;
            background: white !important;
            border-bottom: 1px solid #e2e8f0 !important;
            padding: 12px 0 8px !important;
        }

        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 16px 20px;
        }
        .stButton > button[kind="primary"] {
            background: #6366f1 !important;
            border: none !important;
            color: white !important;
            border-radius: 8px !important;
        }
        .stButton > button {
            border-radius: 8px !important;
            font-size: 13px !important;
            font-weight: 500 !important;
        }
    </style>
    """, unsafe_allow_html=True)
