"""Production-mode config validation must refuse the scaffolding defaults.

`validate_production_config` runs at startup. These tests exercise the
validator directly so they do not need a real database; they just confirm the
guard rails fire when ENVIRONMENT is anything other than "development".
"""
from __future__ import annotations

import pytest

from app.config import Settings
from app.main import validate_production_config


def _settings(**overrides) -> Settings:
    base = dict(
        environment="production",
        secret_key="a-very-long-random-production-secret-key-please",
        database_url="postgresql://user:pass@db.example.com:5432/ucmb_dqa?sslmode=require",
        seed_default_manager=False,
        default_manager_password="ChangeMe123!",
    )
    base.update(overrides)
    return Settings(**base)


def test_development_config_is_never_rejected() -> None:
    config = _settings(
        environment="development",
        secret_key="change-this-secret",
        database_url="postgresql://postgres:postgres@localhost:5432/ucmb_dqa",
        seed_default_manager=True,
        default_manager_password="ChangeMe123!",
    )
    # Must not raise; local dev defaults are intentional in development mode.
    validate_production_config(config)


def test_production_rejects_scaffold_secret_key() -> None:
    config = _settings(secret_key="change-this-secret")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_config(config)


def test_production_rejects_empty_secret_key() -> None:
    config = _settings(secret_key="")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_config(config)


def test_production_rejects_localhost_database_url() -> None:
    config = _settings(database_url="postgresql://postgres:postgres@localhost:5432/ucmb_dqa")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        validate_production_config(config)


def test_production_rejects_loopback_database_url() -> None:
    config = _settings(database_url="postgresql://postgres:postgres@127.0.0.1:5432/ucmb_dqa")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        validate_production_config(config)


def test_production_rejects_seed_with_default_password() -> None:
    config = _settings(seed_default_manager=True, default_manager_password="ChangeMe123!")
    with pytest.raises(RuntimeError, match="SEED_DEFAULT_MANAGER"):
        validate_production_config(config)


def test_production_accepts_strong_settings() -> None:
    config = _settings(
        secret_key="9d7f1a2b3c4d5e6f9d7f1a2b3c4d5e6f9d7f1a2b3c4d5e6f9d7f1a2b3c4d5e6f",
        database_url="postgresql://user:pass@ep-cool-1.us-east-1.aws.neon.tech/ucmb_dqa?sslmode=require",
        seed_default_manager=False,
    )
    validate_production_config(config)


def test_staging_environment_is_validated() -> None:
    config = _settings(environment="staging", secret_key="change-this-secret")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_config(config)
