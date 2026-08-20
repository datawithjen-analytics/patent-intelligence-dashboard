"""Dashboard styling: dark-mode CSS overlay for the Streamlit app."""
import streamlit as st

_DASHBOARD_CSS = """
<style>
    .stApp { background-color: #0d1117; color: #f0f6fc; }
    div[data-testid="stMetricLabel"] { color: #ffffff !important; font-size: 1rem !important; font-weight: 500; }
    div[data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: bold; }
    .stTabs [data-baseweb="tab"] { color: #8b949e !important; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: #58a6ff !important; border-bottom-color: #58a6ff !important; }
</style>
"""


def inject_dashboard_theme() -> None:
    """Apply the app's dark-mode CSS. Call once per page load."""
    st.markdown(_DASHBOARD_CSS, unsafe_allow_html=True)
