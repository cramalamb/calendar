"""Application configuration handling."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
    """Strongly-typed settings loaded from environment variables."""

    calendar_id: str = Field(default="primary", alias="GCAL_CALENDAR_ID")
    default_duration_min: int = Field(default=60, alias="DEFAULT_DURATION_MIN")
    default_add_google_meet: bool = Field(default=False, alias="DEFAULT_ADD_GOOGLE_MEET")
    default_timezone: str = Field(default="UTC", alias="DEFAULT_TIMEZONE")
    api_key: str = Field(alias="CAL_API_KEY")
    api_base: str = Field(default="http://127.0.0.1:8010", alias="CAL_API_BASE")
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

    @property
    def google_scopes(self) -> List[str]:
        """Return the OAuth scopes required for the service."""

        return ["https://www.googleapis.com/auth/calendar"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings."""

    settings = Settings()
    logging.getLogger().setLevel(settings.log_level.upper())
    return settings


def require_api_key() -> str:
    """Return the API key, raising if it is missing."""

    api_key = get_settings().api_key
    if not api_key:
        raise RuntimeError(
            "CAL_API_KEY is not configured. Please set it in your environment or .env file."
        )
    return api_key
