"""
Data ingestion layer.

Loads the three pre-exported files (row-level patents CSV + two aggregate
Excel summaries) from disk, validates every row through the Pydantic models
in models.py, and caches the result so Streamlit reruns (triggered by every
sidebar interaction) don't re-read and re-validate the files each time.

Malformed rows are logged and skipped rather than crashing the whole load —
real exported data (especially from a keyword-filtered BigQuery query) will
usually have a few edge cases, and one bad row shouldn't take down the app.
"""
import logging
from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from config import Settings, get_settings
from models import CategoryCountRecord, CpcCountRecord, PatentRecord

logger = logging.getLogger(__name__)


class DataFileNotFoundError(Exception):
    """Raised when an expected data export is missing from disk."""


def _require_file(path: Path) -> None:
    if not path.exists():
        raise DataFileNotFoundError(
            f"Expected data file not found: {path}. "
            f"Place your exported files in the configured data_dir, "
            f"or set DATA_DIR in .env to point at them."
        )


def _load_patent_records(path: Path) -> List[PatentRecord]:
    """Read the row-level patents CSV and validate each row."""
    _require_file(path)
    df = pd.read_csv(path, dtype={"filing_date": "Int64", "grant_date": "Int64"})

    records: List[PatentRecord] = []
    skipped = 0
    for row in df.to_dict(orient="records"):
        try:
            records.append(
                PatentRecord(
                    publication_number=row["publication_number"],
                    title=row["title"],
                    filing_date=_parse_yyyymmdd(row["filing_date"]),
                    grant_date=_parse_yyyymmdd(row["grant_date"]),
                    family_id=row["family_id"],
                    assignees=row.get("assignees", ""),
                    cpc_codes=row.get("cpc_codes", ""),
                    domains=row.get("domains", ""),
                    country=row["country"],
                    filing_year=row["filing_year"],
                )
            )
        except (ValidationError, ValueError, KeyError) as exc:
            skipped += 1
            logger.warning(
                "Skipping malformed patent row (publication_number=%s): %s",
                row.get("publication_number", "unknown"),
                exc,
            )

    if skipped:
        logger.info("Loaded %d patent records, skipped %d malformed rows.", len(records), skipped)
    return records


def _parse_yyyymmdd(value) -> str:
    """Convert an int/str like 20000125 into an ISO date string '2000-01-25'
    that Pydantic's `date` type can parse. Raises ValueError on bad input
    (e.g. 0), which the caller catches and treats as a skip."""
    s = str(int(value))
    if len(s) != 8 or s == "00000000":
        raise ValueError(f"Not a valid YYYYMMDD date: {value}")
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"


def _load_cpc_counts(path: Path) -> List[CpcCountRecord]:
    _require_file(path)
    df = pd.read_excel(path)
    records = []
    for row in df.to_dict(orient="records"):
        try:
            records.append(CpcCountRecord(cpc_code=row["cpc_code"], patent_count=row["patent_count"]))
        except ValidationError as exc:
            logger.warning("Skipping malformed CPC count row: %s", exc)
    return records


def _load_category_counts(path: Path) -> List[CategoryCountRecord]:
    _require_file(path)
    df = pd.read_excel(path)
    records = []
    for row in df.to_dict(orient="records"):
        try:
            records.append(
                CategoryCountRecord(
                    patent_category=row["patent_category"], patent_count=row["patent_count"]
                )
            )
        except ValidationError as exc:
            logger.warning("Skipping malformed category count row: %s", exc)
    return records


@st.cache_data(ttl=get_settings().cache_ttl_seconds, show_spinner="Loading patent portfolio…")
def load_all_data() -> dict:
    """Load and validate all three data sources.

    Returns:
        dict with keys 'patents', 'cpc_counts', 'category_counts', each a
        list of validated Pydantic model instances.

    Raises:
        DataFileNotFoundError: if any expected file is missing.
    """
    settings: Settings = get_settings()
    return {
        "patents": _load_patent_records(settings.patents_csv_path),
        "cpc_counts": _load_cpc_counts(settings.cpc_counts_path),
        "category_counts": _load_category_counts(settings.category_counts_path),
    }


def clear_data_cache() -> None:
    """Manually invalidate the cached dataset (e.g. after replacing a file)."""
    load_all_data.clear()
