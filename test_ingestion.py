"""
Quick sanity check for the data ingestion layer — run this BEFORE building
the Streamlit UI, to confirm your 3 exported files load and validate
correctly against the real schema.

Usage:
    python test_ingestion.py
"""
from data.ingestion import load_all_data

if __name__ == "__main__":
    data = load_all_data()

    patents = data["patents"]
    cpc_counts = data["cpc_counts"]
    category_counts = data["category_counts"]

    print(f"Loaded {len(patents)} validated patent records")
    print(f"Loaded {len(cpc_counts)} CPC count rows")
    print(f"Loaded {len(category_counts)} category count rows")

    if patents:
        sample = patents[0]
        print("\nSample patent record:")
        print(f"  publication_number: {sample.publication_number}")
        print(f"  title: {sample.title}")
        print(f"  filing_date: {sample.filing_date}")
        print(f"  assignees: {sample.assignees}")
        print(f"  cpc_codes: {sample.cpc_codes[:3]}...")
        print(f"  primary_cpc_section: {sample.primary_cpc_section}")
        print(f"  years_remaining (as of 2026): {sample.years_remaining(2026)}")
        print(f"  is_active (as of 2026): {sample.is_active(2026)}")
