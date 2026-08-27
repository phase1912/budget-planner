"""Typed application settings (F0.2.2, F0.7.1).

The single place the service reads configuration from. A value that is not a
field on `Settings` is not configurable — nothing else in the codebase should
read `os.environ` or `os.getenv` directly, so a missing or malformed variable
fails here, at boot, instead of wherever the untyped read happens to be.

Every setting here, its purpose, default and whether it is required is also
listed in `docs/architecture/configuration.md` — update that table in the same
commit as a change here. Which value each environment sets is
`docs/architecture/environments.md`'s job, not this module's: this file fixes
defaults for local development only.
"""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, PostgresDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """The three deployment tiers this system runs in (F0.7.3).

    See `docs/architecture/environments.md` for what differs between them —
    this enum only fixes the vocabulary so a typo'd tier name fails at boot
    rather than silently falling through to local-development behaviour.
    """

    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


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

    environment: Environment = Environment.LOCAL
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
    anthropic_model: str = Field(
        default="claude-haiku-4-5-20251001",
        description=(
            "Claude model id used for extraction, categorisation and advice calls. "
            "The default is the local/staging tier; production sets its own tier "
            "explicitly (ADR-0005, F0.7.3) rather than having this module branch on "
            "`environment`, so the deployed model is a visible env var, not implicit."
        ),
    )
    llm_model: str = Field(
        default="gemini/gemini-2.0-flash",
        description=(
            "litellm model string for the universal agent (ADR-0006). "
            "The prefix determines the provider: 'gemini/' → Google AI Studio, "
            "'anthropic/' → Anthropic, 'openai/' → OpenAI. Any litellm-supported "
            "model works without code changes."
        ),
    )
    llm_api_key: SecretStr | None = Field(
        default=None,
        description=(
            "API key for the LLM provider chosen by llm_model. When None, "
            "litellm falls back to provider-specific env vars "
            "(GEMINI_API_KEY, ANTHROPIC_API_KEY, etc.)."
        ),
    )
    ocr_confidence_threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        description=(
            "Below this, an extracted required field is flagged 'low confidence' "
            "instead of accepted silently (BRD A10). Initial value per ADR-0005, "
            "answering BRD open question 14.5 — revisit once real extraction "
            "accuracy data exists."
        ),
    )
    categorization_confidence_threshold: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description=(
            "Below this, a line item is assigned 'Uncategorized' and flagged for "
            "review instead of guessed (BRD C3). Initial value per ADR-0005, "
            "answering BRD open question 14.5 — revisit once real categorisation "
            "accuracy data exists."
        ),
    )
    build_sha: str = Field(
        default="dev",
        description="Set by CI/CD at deploy time; 'dev' outside a built image.",
    )
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("dev-secret-key-do-not-use-in-prod"),
        description="Used to sign access tokens.",
    )
    access_token_expire_minutes: int = Field(
        default=240, ge=1, description="Lifespan of a JWT access token (F1.2.1), default 4 hours."
    )
    refresh_token_expire_days: int = Field(
        default=30, ge=1, description="Lifespan of a refresh token family (F1.2.2)."
    )
    argon2_time_cost: int = Field(
        default=2,
        description="Number of iterations for Argon2id hashing.",
    )
    argon2_memory_cost: int = Field(
        default=19456,  # ~19 MB, a common OWASP recommendation
        description="Memory cost (in KiB) for Argon2id hashing.",
    )
    argon2_parallelism: int = Field(
        default=1,
        description="Degree of parallelism for Argon2id hashing.",
    )

    s3_bucket_name: str = Field(description="Name of the S3-compatible bucket for receipt images.")
    aws_region: str = Field(default="us-east-1", description="AWS region for the S3 bucket.")
    aws_access_key_id: SecretStr | None = Field(
        default=None, description="AWS access key ID. If None, boto3 uses environment/IAM roles."
    )
    aws_secret_access_key: SecretStr | None = Field(
        default=None, description="AWS secret access key."
    )
    s3_endpoint_url: str | None = Field(
        default=None, description="Custom S3 endpoint URL (e.g., for MinIO or LocalStack)."
    )

    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="List of origins allowed to make cross-origin requests.",
    )

    @model_validator(mode="after")
    def validate_jwt_secret_for_env(self) -> "Settings":
        if (
            self.environment != Environment.LOCAL
            and self.jwt_secret_key.get_secret_value() == "dev-secret-key-do-not-use-in-prod"
        ):
            raise ValueError(
                "The default dev-secret-key-do-not-use-in-prod is not permitted "
                "in staging or production environments."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide `Settings`, built and validated once.

    Cached so the environment is parsed and validated a single time per
    process rather than on every call site that needs configuration.
    """
    return Settings()
