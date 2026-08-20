"""
Chart builders for the Patent Intelligence dashboard.

Each function takes a DataFrame (already produced by services/valuation.py)
and returns a Plotly Figure only — no st.plotly_chart() calls here — so
charts stay easy to test or reuse outside Streamlit.
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

_TRANSPARENT_LAYOUT = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")


def build_expiry_timeline(expiry_df: pd.DataFrame) -> go.Figure:
    """Line chart for Question 1: patents expiring per year."""
    if expiry_df.empty:
        return go.Figure()
    fig = px.line(
        expiry_df, x="Expiry_Year", y="Patent_Count", markers=True, template="plotly_dark"
    )
    fig.update_traces(line_color="#58a6ff", marker=dict(size=9, color="#ff7b72"))
    fig.update_layout(**_TRANSPARENT_LAYOUT)
    return fig


def build_company_strength_bar(company_df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart for Question 2: top companies by asset strength."""
    if company_df.empty:
        return go.Figure()
    df_sorted = company_df.sort_values("Asset_Strength_Score", ascending=True)
    fig = px.bar(
        df_sorted,
        x="Asset_Strength_Score",
        y="Assignee",
        orientation="h",
        color="Asset_Strength_Score",
        color_continuous_scale="Blues",
        template="plotly_dark",
    )
    fig.update_layout(**_TRANSPARENT_LAYOUT)
    return fig


def build_white_space_heatmap(white_space_df: pd.DataFrame) -> go.Figure:
    """Heatmap for Question 3: filing activity by CPC section x year.

    Low/blank cells are the visual signal for potential white space —
    the dashboard surfaces the pattern; judging what counts as a real
    opportunity is an analytical call for the viewer.
    """
    if white_space_df.empty:
        return go.Figure()
    pivot = white_space_df.pivot(
        index="Primary_CPC_Section", columns="Filing_Year", values="Patent_Count"
    ).fillna(0)
    fig = px.imshow(
        pivot,
        color_continuous_scale="Blues",
        aspect="auto",
        labels=dict(x="Filing Year", y="CPC Section", color="Patents"),
        template="plotly_dark",
    )
    fig.update_layout(**_TRANSPARENT_LAYOUT)
    return fig


def build_domain_country_bar(df: pd.DataFrame) -> go.Figure:
    """Grouped bar chart: patent count by domain, split by country.

    Uses the full patent DataFrame directly (not a pre-aggregated one) so
    it can group by two dimensions at once.
    """
    if df.empty:
        return go.Figure()
    grouped = (
        df.groupby(["Primary_Domain", "Country"]).size().reset_index(name="Patent_Count")
    )
    fig = px.bar(
        grouped,
        x="Primary_Domain",
        y="Patent_Count",
        color="Country",
        barmode="group",
        template="plotly_dark",
    )
    fig.update_layout(**_TRANSPARENT_LAYOUT)
    return fig
