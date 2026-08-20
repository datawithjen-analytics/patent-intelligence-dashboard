"""
Multi-Jurisdiction Patent Classification & Technology Intelligence Dashboard.

Streamlit entry point. Layout only — data loading lives in data/ingestion.py,
scoring/analysis logic lives in services/valuation.py, charts live in ui/charts.py.

Run with: streamlit run app.py
"""
import streamlit as st

from config import get_settings
from data.ingestion import DataFileNotFoundError, clear_data_cache, load_all_data
from services.valuation import (
    asset_strength_by_company,
    expiry_window_analysis,
    records_to_dataframe,
    technology_white_space,
)
from ui.charts import (
    build_company_strength_bar,
    build_domain_country_bar,
    build_expiry_timeline,
    build_white_space_heatmap,
)
from ui.styles import inject_dashboard_theme

st.set_page_config(page_title="Patent Intelligence Dashboard", layout="wide")
inject_dashboard_theme()

st.markdown("# \U0001F310 Multi-Jurisdiction Patent Classification & Technology Intelligence Dashboard")
st.markdown("### `Expiry Risk · Asset Strength · Technology White Space`")
st.markdown("---")

settings = get_settings()

# --- Load data (cached; validated via Pydantic) ---------------------------
try:
    raw_data = load_all_data()
except DataFileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

full_df = records_to_dataframe(raw_data["patents"], as_of_year=settings.current_analysis_year)

if full_df.empty:
    st.error("No patent records available to display.")
    st.stop()

# --- Sidebar filters --------------------------------------------------------
st.sidebar.header("\U0001F579\ufe0f Filters")
if st.sidebar.button("\U0001F504 Refresh data"):
    clear_data_cache()
    st.rerun()

domain_options = sorted(full_df["Primary_Domain"].unique())
country_options = sorted(full_df["Country"].unique())

selected_domains = st.sidebar.multiselect("Domain:", options=domain_options, default=domain_options)
selected_countries = st.sidebar.multiselect("Country:", options=country_options, default=country_options)

filtered_df = full_df[
    full_df["Primary_Domain"].isin(selected_domains) & full_df["Country"].isin(selected_countries)
]

if filtered_df.empty:
    st.warning("No patents match the current filter selection.")
    st.stop()

# --- KPI row -----------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Total Patents", f"{len(filtered_df):,}")
with k2:
    st.metric("Active Patents", f"{int(filtered_df['Is_Active'].sum()):,}")
with k3:
    mean_score = round(filtered_df["Asset_Strength_Score"].mean(), 1)
    st.metric("Mean Asset Strength", f"{mean_score} pts")
with k4:
    st.metric("Countries Covered", filtered_df["Country"].nunique())

st.markdown("---")

tab1, tab2, tab3 = st.tabs(
    [
        "\U0001F4C5 Q1: Expiry & Generic-Entry Window",
        "\U0001F4B0 Q2: Asset Strength & Risk",
        "\U0001F52C Q3: Technology White Space",
    ]
)

with tab1:
    st.markdown("#### Active Patents Expiring, by Year")
    start_year = settings.current_analysis_year
    end_year = start_year + 10
    expiry_df = expiry_window_analysis(filtered_df, start_year, end_year)
    st.plotly_chart(build_expiry_timeline(expiry_df), use_container_width=True)

    st.markdown("#### Filing Activity by Domain & Country")
    st.plotly_chart(build_domain_country_bar(filtered_df), use_container_width=True)

with tab2:
    st.markdown("#### Top Companies by Asset Strength Score")
    st.caption(
        "Score = (years remaining x 5) + (CPC code breadth x 2). "
        "Expired patents always score 0."
    )
    company_df = asset_strength_by_company(filtered_df, top_n=15)
    st.plotly_chart(build_company_strength_bar(company_df), use_container_width=True)

    st.markdown("#### Highest-Value Active Patents")
    top_patents_cols = ["Publication_Number", "Title", "Assignee", "Country", "Years_Remaining", "Asset_Strength_Score"]
    st.dataframe(
        filtered_df[filtered_df["Is_Active"]][top_patents_cols]
        .sort_values("Asset_Strength_Score", ascending=False)
        .head(15),
        use_container_width=True,
    )

with tab3:
    st.markdown("#### Filing Activity Heatmap (CPC Section x Year)")
    st.caption(
        "Sparse or low-count cells relative to a section's own history are worth "
        "investigating as potential technology white space."
    )
    white_space_df = technology_white_space(filtered_df, recent_years=7)
    st.plotly_chart(build_white_space_heatmap(white_space_df), use_container_width=True)
