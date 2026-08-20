"""
Data contracts for the Patent Portfolio Analytics app.

Schema matches the actual CSV/XLSX exports pulled from BigQuery's
`patents-public-data.patents.publications` and
`patents-public-data.google_patents_research.publications`, filtered to
US pharma/chemical/drug/compound patents (see /sql/ for the source queries).

`PatentRecord` is the row-level unit (one granted patent, 2000-2025).
`CpcCountRecord` / `CategoryCountRecord` back the two supplementary
aggregate summary tables.
"""
from datetime import date
from typing import List

from pydantic import BaseModel, Field, field_validator


class PatentRecord(BaseModel):
    """A single validated, granted US pharma/chemical-domain patent.

    Source: patents_pharma_chem_us_raw.csv (one row per publication_number,
    already de-duplicated in SQL via STRING_AGG — assignees/cpc_codes arrive
    as pipe-delimited strings and are parsed into lists here).
    """

    model_config = {"str_strip_whitespace": True}

    publication_number: str = Field(..., min_length=4, max_length=32)
    title: str = Field(..., min_length=1, max_length=1000)
    filing_date: date
    grant_date: date
    family_id: int = Field(..., ge=0)
    assignees: List[str] = Field(default_factory=list)
    cpc_codes: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    country: str = Field(..., min_length=2, max_length=100)
    filing_year: int = Field(..., ge=1900, le=2100)

    @field_validator("assignees", "cpc_codes", "domains", mode="before")
    @classmethod
    def _split_pipe_delimited(cls, v):
        """CSV stores these as 'A | B | C' strings; split + dedupe here."""
        if isinstance(v, str):
            parts = [p.strip() for p in v.split("|") if p.strip()]
            # preserve order, drop duplicates
            seen = set()
            out = []
            for p in parts:
                if p not in seen:
                    seen.add(p)
                    out.append(p)
            return out
        return v

    @property
    def primary_cpc_section(self) -> str:
        """First letter of the most specific (longest) CPC code, e.g. 'A' or 'C'.
        Used to bucket a patent into a broad technology section for charts."""
        if not self.cpc_codes:
            return "Unknown"
        longest = max(self.cpc_codes, key=len)
        return longest[0] if longest else "Unknown"

    @property
    def primary_domain(self) -> str:
        """The first classified domain for this patent (e.g. 'Pharmaceutical').

        A small number of patents genuinely span more than one domain (e.g.
        a battery-electrode alloy touches both Metallurgy & Alloys and
        Electrochemical) — that's realistic, not a data error. This picks
        one for charts that need a single category per patent; the full
        list stays available in `domains` for anyone who wants to see
        cross-domain patents specifically.
        """
        return self.domains[0] if self.domains else "Unclassified"

    def years_remaining(self, as_of_year: int, term_years: int = 20) -> int:
        """Years left before expiry, assuming a standard `term_years`-year
        utility patent term from filing (US default: 20 years). Floored at 0.

        Note: this is an estimate, not an authoritative legal expiry date —
        real terms can be adjusted (Patent Term Adjustment, terminal
        disclaimers, maintenance-fee lapses). Flagged clearly in the UI/README.
        """
        expiry_year = self.filing_year + term_years
        return max(0, expiry_year - as_of_year)

    def is_active(self, as_of_year: int, term_years: int = 20) -> bool:
        """True if the estimated term has not yet lapsed as of `as_of_year`."""
        return self.years_remaining(as_of_year, term_years) > 0


class CpcCountRecord(BaseModel):
    """One row of the supplementary CPC-code aggregate summary table."""

    cpc_code: str = Field(..., min_length=1, max_length=20)
    patent_count: int = Field(..., ge=0)


class CategoryCountRecord(BaseModel):
    """One row of the supplementary category aggregate summary table."""

    patent_category: str = Field(..., min_length=1, max_length=100)
    patent_count: int = Field(..., ge=0)


class FilterParams(BaseModel):
    """Validated shape of the sidebar filter controls."""

    filing_year_range: tuple[int, int] = (2000, 2025)
    assignees: List[str] = Field(default_factory=list)
    cpc_sections: List[str] = Field(default_factory=list)

    @field_validator("filing_year_range")
    @classmethod
    def _valid_range(cls, v: tuple[int, int]) -> tuple[int, int]:
        start, end = v
        if start > end:
            raise ValueError(f"filing_year_range start ({start}) is after end ({end})")
        return v
