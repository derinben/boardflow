"""Application configuration using Pydantic settings."""

import os
from enum import Enum
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/boardflow",
        alias="DATABASE_URL",
    )

    # LLM Configuration
    llm_provider: LLMProvider = Field(
        default=LLMProvider.ANTHROPIC,
        alias="LLM_PROVIDER",
        description="LLM provider to use: 'anthropic' or 'bedrock'",
    )

    # Anthropic Native API settings
    anthropic_api_key: Optional[str] = Field(
        default=None,
        alias="ANTHROPIC_API_KEY",
        description="Anthropic API key for native API",
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        alias="ANTHROPIC_MODEL",
        description="Claude model name for Anthropic native API",
    )

    # AWS Bedrock settings
    aws_region: str = Field(
        default="us-east-1",
        alias="AWS_REGION",
        description="AWS region for Bedrock",
    )
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0",
        alias="BEDROCK_MODEL_ID",
        description="Bedrock model ID (e.g., anthropic.claude-3-5-sonnet-20241022-v2:0)",
    )

    # BGG API settings
    bgg_base_url: str = Field(
        default="https://boardgamegeek.com/xmlapi2",
        alias="BGG_BASE_URL",
    )
    bgg_request_delay_seconds: int = Field(default=2, alias="BGG_REQUEST_DELAY_SECONDS")
    bgg_num_workers: int = Field(default=5, alias="BGG_NUM_WORKERS")
    bgg_ingest_limit: int = Field(default=1000, alias="BGG_INGEST_LIMIT")
    bgg_stats_max_age_days: int = Field(default=7, alias="BGG_STATS_MAX_AGE_DAYS")
    bgg_csv_dump_url: str = Field(
        default="https://boardgamegeek.com/data_dumps/bg_ranks",
        alias="BGG_CSV_DUMP_URL",
    )
    bgg_csv_local_path: Optional[str] = Field(
        default="./data/boardgames_ranks.csv",
        alias="BGG_CSV_LOCAL_PATH",
    )
    bgg_csv_max_age_hours: int = Field(default=24, alias="BGG_CSV_MAX_AGE_HOURS")
    bgg_api_token: Optional[str] = Field(default=None, alias="BGG_API_TOKEN")

    # IDF Configuration for Recommendation Weighting
    idf_enabled: bool = Field(
        default=True,
        alias="IDF_ENABLED",
        description="Enable IDF weighting for mechanics/categories in recommendations",
    )
    idf_smoothing: float = Field(
        default=1.0,
        alias="IDF_SMOOTHING",
        description="Smoothing factor for IDF computation: log((N+s)/(df+s))",
    )

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env


# Global settings instance
settings = Settings()
