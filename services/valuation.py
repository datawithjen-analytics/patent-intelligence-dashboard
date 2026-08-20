"""
Patent valuation & analysis logic.

This is where the raw, validated PatentRecord list becomes the actual
analysis your three project questions need:
  1. R&D Expiry & Generic-Entry Window
  2. Patent Asset Strength & Financial Risk
  3. Technology White-Space Analysis

Pure functions only (no Streamlit, no file I/O) so this is easy to test on
its own, separately from the UI.

IMPORTANT SCOPE NOTE: the source dataset is filtered to US-only patents, so
there is no real "number of jurisdictions" signal available (every patent
has country == 'United States'). The original scoring idea used jurisdiction
count as a strength factor; here it's replaced with CPC breadth (how many
distinct technology classification codes a patent touches) as a proxy for
how broad the patent's technical scope is. This is a deliberate, documented
substitution -- not a placeholder to fix later.
"""
from typing import List

import pandas as pd

from models import PatentRecord

# Named weights, not magic numbers, so the scoring formula is auditable.
YEARS_REMAINING_WEIGHT = 5
CPC_BREADTH_WEIGHT = 2


def records_to_dataframe(records: List[PatentRecord], as_of_year: int) -> pd.DataFrame:
    """Convert validated PatentRecords into an analysis-ready DataFrame.

    One row per patent (already de-duplicated upstream in SQL), with derived
    columns for years remaining, active/expired status, CPC breadth, and the
    asset strength score.

    Args:
        records: validated patent records from data/ingestion.py.
        as_of_year: reference year for expiry math (e.g. 2026).

    Returns:
        DataFrame with one row per patent.
    """
    rows = [
        {
            "Publication_Number": r.publication_number,
            "Title": r.title,
            "Filing_Date": pd.Timestamp(r.filing_date),
            "Filing_Year": r.filing_year,
            "Grant_Date": pd.Timestamp(r.grant_date),
            "Family_ID": r.family_id,
            "Assignee": r.assignees[0] if r.assignees else "Unknown",
            "Primary_CPC_Section": r.primary_cpc_section,
            "Primary_Domain": r.primary_domain,
            "Country": r.country,
            "CPC_Breadth": len(r.cpc_codes),
            "Years_Remaining": r.years_remaining(as_of_year),
            "Is_Active": r.is_active(as_of_year),
        }
        for r in records
    ]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return _add_asset_strength_score(df)


def _add_asset_strength_score(df: pd.DataFrame) -> pd.DataFrame:
    """Attach the Asset_Strength_Score column.

    Formula: (years remaining * YEARS_REMAINING_WEIGHT)
             + (CPC breadth * CPC_BREADTH_WEIGHT)
    Expired patents always score 0 -- an expired patent has no remaining
    exclusivity value, regardless of how technically broad it was.
    """
    df = df.copy()
    df["Asset_Strength_Score"] = (
        df["Years_Remaining"] * YEARS_REMAINING_WEIGHT + df["CPC_Breadth"] * CPC_BREADTH_WEIGHT
    )
    df.loc[~df["Is_Active"], "Asset_Strength_Score"] = 0
    return df


def expiry_window_analysis(df: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    """Answers Question 1: which active patents expire in a given window
    (e.g. 2026-2032), broken down by expiry year.

    Args:
        df: full patent DataFrame (from records_to_dataframe).
        start_year: first year of the expiry window, inclusive.
        end_year: last year of the expiry window, inclusive.

    Returns:
        DataFrame with one row per expiry year and a patent count, restricted
        to currently-active patents whose estimated expiry falls in range.
    """
    if df.empty:
        return df
    active = df[df["Is_Active"]].copy()
    active["Expiry_Year"] = active["Filing_Year"] + 20  # standard US utility term
    window = active[(active["Expiry_Year"] >= start_year) & (active["Expiry_Year"] <= end_year)]
    return (
        window.groupby("Expiry_Year")
        .size()
        .reset_index(name="Patent_Count")
        .sort_values("Expiry_Year")
    )


def asset_strength_by_company(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Answers Question 2: total asset strength score per assignee company.

    Args:
        df: full patent DataFrame.
        top_n: how many top companies to return.

    Returns:
        DataFrame of the top_n companies by summed Asset_Strength_Score.
    """
    if df.empty:
        return df
    return (
        df.groupby("Assignee")["Asset_Strength_Score"]
        .sum()
        .reset_index()
        .sort_values("Asset_Strength_Score", ascending=False)
        .head(top_n)
    )


def technology_white_space(df: pd.DataFrame, recent_years: int = 7) -> pd.DataFrame:
    """Answers Question 3: filing activity per CPC section over recent years,
    to help spot technology areas with relatively low activity ("white space").

    Args:
        df: full patent DataFrame.
        recent_years: how many years back from the max filing year to include.

    Returns:
        DataFrame of CPC section x filing year filing counts. Low counts in
        recent years, relative to a section's own history, are the signal to
        investigate further -- this function surfaces the counts; judging
        what counts as "white space" is an analytical call for the dashboard
        user, not something this function decides on its own.
    """
    if df.empty:
        return df
    max_year = df["Filing_Year"].max()
    recent = df[df["Filing_Year"] >= max_year - recent_years]
    return (
        recent.groupby(["Primary_CPC_Section", "Filing_Year"])
        .size()
        .reset_index(name="Patent_Count")
        .sort_values(["Primary_CPC_Section", "Filing_Year"])
    )
