"""
Application configuration.

This project runs on static, pre-exported BigQuery data (see /sql/ for the
source queries) rather than a live API — so config is just file paths, kept
in one place and overridable via environment variables so the app isn't
hardcoded to one person's folder structure.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """File-path configuration for the three data exports."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    data_dir: Path = Field(default=Path("data_files"))
    patents_csv_filename: str = Field(default="patents_multidomain_global.csv")
    cpc_counts_filename: str = Field(default="cpc_patent_counts.xlsx")
    category_counts_filename: str = Field(default="patent_category_counts.xlsx")

    cache_ttl_seconds: int = Field(default=3600, ge=0)
    current_analysis_year: int = Field(default=2026, ge=1900, le=2100)
    patent_term_years: int = Field(default=20, ge=1, le=50)

    @field_validator("data_dir", mode="before")
    @classmethod
    def _coerce_path(cls, v):
        return Path(v)

    @property
    def patents_csv_path(self) -> Path:
        return self.data_dir / self.patents_csv_filename

    @property
    def cpc_counts_path(self) -> Path:
        return self.data_dir / self.cpc_counts_filename

    @property
    def category_counts_path(self) -> Path:
        return self.data_dir / self.category_counts_filename


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached, process-wide Settings instance."""
    return Settings()
