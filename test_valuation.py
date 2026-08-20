"""
Quick sanity check for services/valuation.py — confirms the scoring and
analysis logic works correctly against your real loaded data.

Usage:
    python test_valuation.py
"""
from data.ingestion import load_all_data
from services.valuation import (
    asset_strength_by_company,
    expiry_window_analysis,
    records_to_dataframe,
    technology_white_space,
)

if __name__ == "__main__":
    data = load_all_data()
    df = records_to_dataframe(data["patents"], as_of_year=2026)

    print(f"Total patents: {len(df)}")
    print(f"Active patents: {int(df['Is_Active'].sum())}")
    print()

    print("Q1 - Expiry window 2026-2032:")
    print(expiry_window_analysis(df, 2026, 2032))
    print()

    print("Q2 - Top 10 companies by asset strength:")
    print(asset_strength_by_company(df, top_n=10))
    print()

    print("Q3 - Recent white-space activity by CPC section:")
    print(technology_white_space(df))
