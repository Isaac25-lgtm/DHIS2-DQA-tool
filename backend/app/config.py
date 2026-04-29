from functools import lru_cache
import json
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "UCMB HMIS 105 DQA Platform"
    environment: str = "development"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/ucmb_dqa"
    secret_key: str = "change-this-secret"
    access_token_expire_minutes: int = 60
    dhis2_base_url: str = "https://hmis.health.go.ug/api"
    dhis2_username: str = ""
    dhis2_password: str = ""
    ai_api_key: str = ""
    ai_provider: str = ""
    ai_model: str = ""
    app_version: str = "0.6.0"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    default_manager_name: str = "System Manager"
    default_manager_email: str = "admin@ucmb-dqa.local"
    default_manager_password: str = "ChangeMe123!"
    seed_default_manager: bool = False
    test_database_url: str = "postgresql://postgres:postgres@localhost:5432/ucmb_dqa_test"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if value.strip().startswith("["):
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(origin).strip() for origin in parsed if str(origin).strip()]
        return [origin.strip() for origin in value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
