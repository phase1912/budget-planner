"""Typed application settings (F0.2.2).

The single place the service reads configuration from. A value that is not a
field on `Settings` is not configurable — nothing else in the codebase should
read `os.environ` or `os.getenv` directly, so a missing or malformed variable
fails here, at boot, instead of wherever the untyped read happens to be.
"""

from functools import lru_cache

from pydantic import Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration layered environment variables > `.env` file > defaults.

    `database_url` and `anthropic_api_key` have no default: constructing
    `Settings` without them set raises `pydantic.ValidationError` immediately,
    which is the fail-fast behaviour this module exists to provide.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    environment: str = "development"
    database_url: PostgresDsn = Field(
        description="Must use an async driver scheme, e.g. postgresql+asyncpg://."
    )
    database_pool_size: int = Field(
        default=5, description="Persistent connections kept open per process (F0.3.1)."
    )
    database_max_overflow: int = Field(
        default=10, description="Extra connections allowed above the pool under load (F0.3.1)."
    )
    anthropic_api_key: SecretStr
    build_sha: str = Field(
        default="dev",
        description="Set by CI/CD at deploy time; 'dev' outside a built image.",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide `Settings`, built and validated once.

    Cached so the environment is parsed and validated a single time per
    process rather than on every call site that needs configuration.
    """
    return Settings()
