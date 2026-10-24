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
from typing import Literal

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


StorageBackend = Literal["s3", "gcs"]
ExchangeRateSource = Literal["nbp", "off"]


class Settings(BaseSettings):
    """Configuration layered environment variables > `.env` file > defaults.

    `database_url` has no default: constructing `Settings` without it raises
    `pydantic.ValidationError` immediately, which is the fail-fast behaviour this
    module exists to provide. Model credentials are optional, because which ones a
    deployment needs depends on `llm_model` (ADR-0006).
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
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        description="Anthropic key, read by litellm only when `llm_model` is an Anthropic model.",
    )
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
        default="gemini/gemini-3.6-flash",
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
    llm_api_base: str | None = Field(
        default=None,
        description=(
            "Optional custom base URL for the LLM provider. Required for "
            "proxies, OpenAI-compatible APIs (like Z-AI), or self-hosted models."
        ),
    )
    vertex_project: str | None = Field(
        default=None,
        description=(
            "Google Cloud project for `vertex_ai/` models; credentials come from the "
            "runtime service account, so no key is needed (ADR-0014)."
        ),
    )
    vertex_location: str | None = Field(
        default=None, description="Vertex AI region for `vertex_ai/` models, e.g. us-central1."
    )
    speech_engine: Literal["speech_to_text", "model"] = Field(
        default="model",
        description=(
            "What turns the assistant's recordings into words (F21.2.2, ADR-0031): "
            "`speech_to_text` is Google Cloud Speech-to-Text v2 with Chirp, which needs its "
            "API enabled; `model` is the configured Gemini model hearing the recording."
        ),
    )
    speech_location: str = Field(
        default="eu",
        description="Where Speech-to-Text's Chirp 3 model runs: `eu` or `us`, multi-regions.",
    )
    llm_disable_json_schema: bool = Field(
        default=False,
        description=(
            "Stop asking the provider to enforce the response JSON schema natively. "
            "LM Studio's constrained decoding corrupts the key names it emits, "
            "producing JSON that parses but matches no field, so every extraction "
            "comes back empty. With this set the model follows the prompt instead and "
            "`Agent._parse_response` reads what it returns. Leave False for hosted "
            "providers, whose structured output works."
        ),
    )
    llm_max_concurrency: int = Field(
        default=2,
        ge=1,
        description=(
            "How many receipts are extracted in parallel in one upload job. Keep "
            "this at 1 for a locally served model: a single model instance "
            "serialises the requests anyway, and concurrent calls evict each "
            "other's prompt cache, which makes the batch slower rather than faster."
        ),
    )
    upload_job_timeout_seconds: int = Field(
        default=900,
        ge=1,
        description=(
            "How long one upload job may spend extracting before it is abandoned "
            "and marked failed. Without it a wedged provider call leaves the job "
            "in PROCESSING forever and the client polling forever."
        ),
    )
    llm_disable_reasoning: bool = Field(
        default=False,
        description=(
            "Ask the provider to answer without a reasoning pass. Needed for local "
            "hybrid-reasoning models served by LM Studio or Ollama (Qwen3 and kin), "
            "which otherwise emit the whole answer into the reasoning channel and "
            "leave `content` empty, breaking every structured extraction. Leave "
            "False for hosted providers, which do not accept the parameter."
        ),
    )
    min_receipts_for_advice: int = Field(
        default=4,
        ge=1,
        description=(
            "Parsed receipts a user needs before advice is generated; below it the "
            "user is told more history is needed (BRD F5)."
        ),
    )
    min_history_days_for_advice: int = Field(
        default=30,
        ge=1,
        description=(
            "Days of history, from the first parsed receipt, a user needs before "
            "advice is generated: BRD F5's 'one full month' (BRD F5)."
        ),
    )
    proactive_advice_interval_minutes: int = Field(
        default=360,
        ge=0,
        description=(
            "How often the background pass prepares advice for goals heading over their "
            "cap (BRD F7); 0 turns it off."
        ),
    )
    admin_second_factor_required: bool | None = Field(
        default=None,
        description=(
            "Whether admins must sign in with a second factor (F18.6.1). Unset: required "
            "everywhere but local work."
        ),
    )
    free_monthly_credits: int = Field(
        default=150,
        ge=0,
        description=(
            "AI credits the free plan may spend a calendar month (F21.9, ADR-0030): one "
            "credit is 0.001 USD of what the model calls cost."
        ),
    )
    paid_monthly_credits: int = Field(
        default=2500, ge=0, description="AI credits the paid plan may spend a month (F21.9)."
    )
    daily_credit_ceiling: int = Field(
        default=3000,
        ge=0,
        description=(
            "Credits charged per UTC day across every non-admin account: bounds the bill "
            "whatever happens to each wallet."
        ),
    )
    credits_per_receipt: float = Field(
        default=10.0,
        gt=0,
        description=(
            "What a receipt read is taken to cost until enough reads were recorded to tell "
            "(F21.9.3); the measured average replaces it."
        ),
    )
    credits_per_message: float = Field(
        default=4.0,
        gt=0,
        description="What a message to the assistant is taken to cost until measured.",
    )
    free_receipts_per_upload: int = Field(
        default=5,
        ge=1,
        description="Receipts one upload may hold on the free plan, so one cannot spend the month.",
    )
    free_assistant_rounds: int = Field(
        default=4,
        ge=1,
        description="Rounds of tool use one message may take on the free plan (F21.9.2).",
    )
    admin_emails: list[str] = Field(
        default_factory=list,
        description=(
            "Accounts treated as admins besides those with role 'admin': no receipt quota, "
            "no service-wide ceiling, and no access to other users' data (F10.6, BRD N2)."
        ),
    )
    support_email: str | None = Field(
        default=None,
        description=(
            "The support mailbox (F22.1.2): the public contact in the store listing and where "
            "the contact form's messages go. Unset, they go to admin_emails."
        ),
    )
    inbound_email_domain: str = Field(
        default="inbound.localhost",
        description=(
            "Domain of every user's receipt forwarding address (F11.2): in production the "
            "App Engine inbound mail domain, `<project>.appspotmail.com` (ADR-0013)."
        ),
    )
    inbound_email_secret: SecretStr | None = Field(
        default=None,
        description=(
            "Shared secret the inbound mail relay sends with every message (F11.2). Unset, "
            "the intake endpoint answers 404: no deployment accepts mail by accident."
        ),
    )
    google_client_ids: list[str] = Field(
        default_factory=list,
        description=(
            "OAuth client ids whose Google ID tokens sign in (F1.6): the web client first — the "
            "one the sign-in page opens Google with — then the apps'. Empty, Google is off."
        ),
    )
    apple_client_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Audiences of Apple ID tokens that sign in (F1.6): the Services ID the web opens "
            "Apple with first, then the iOS bundle id. Empty, Apple is off."
        ),
    )
    apple_team_id: str | None = Field(
        default=None, description="Apple Developer team that signs the client secret (F1.6.3)."
    )
    apple_key_id: str | None = Field(
        default=None, description="Id of the Sign in with Apple key in that team (F1.6.3)."
    )
    apple_private_key: SecretStr | None = Field(
        default=None,
        description=(
            "The Sign in with Apple key (.p8, PEM), from Secret Manager (F1.6.3): signs the "
            "client secret that exchanges codes and revokes tokens. Unset, tokens are not kept "
            "and nothing can be revoked at Apple."
        ),
    )
    app_url: str | None = Field(
        default=None,
        description=(
            "Where the web app is opened, for links in letters (F17.8); unset, the first "
            "CORS origin, which is the app's own address in every deployment."
        ),
    )
    outgoing_mail: Literal["log", "appengine"] | None = Field(
        default=None,
        description=(
            "How letters go out (F17.8, ADR-0019): `appengine` through the mail relay's send "
            "endpoint, `log` written to the log for local work. Unset, `appengine` wherever "
            "inbound mail is App Engine's, else `log`."
        ),
    )
    email_domain_dns_check: bool = Field(
        default=True,
        description=(
            "Ask DNS whether an address's domain receives mail before accepting it "
            "(F17.8.4); off in tests, which never touch the network."
        ),
    )
    inbound_email_max_bytes: int = Field(
        default=10 * 1024 * 1024,
        ge=1,
        description="Largest inbound message accepted, body and attachments together (F11.2).",
    )
    inbound_email_daily_limit: int = Field(
        default=20,
        ge=1,
        description="Emailed receipts accepted per user per UTC day (F11.2).",
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
    price_freshness_days: int = Field(
        default=90,
        ge=1,
        description=(
            "How recent a shop's price must be to say another shop is cheaper (F16.3): an "
            "older price may no longer hold."
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
        default=30,
        ge=1,
        description="How long a session lasts unused: each refresh extends it this far (F1.2.2).",
    )
    refresh_token_absolute_days: int = Field(
        default=90,
        ge=1,
        description="The longest a session lasts however often it is used; then sign in again.",
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

    exchange_rate_source: ExchangeRateSource = Field(
        default="nbp",
        description=(
            "Where foreign receipts get their rate: `nbp`, the National Bank of Poland with "
            "the ECB as fallback (ADR-0016); `off` stores them unconverted, as before F11.7 — "
            "for the test suite, which never reaches the network."
        ),
    )

    storage_backend: StorageBackend = Field(
        default="s3",
        description=(
            "Where receipt photos live: `s3` for any S3-compatible store (MinIO locally), "
            "`gcs` for Cloud Storage as the runtime's service account, keyless (ADR-0014)."
        ),
    )
    s3_bucket_name: str = Field(
        description="Bucket for receipt images, whichever `storage_backend` holds it."
    )
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
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            # The store apps serve the client from the device (F22.2.1, F25.2.1).
            "https://localhost",
            "capacitor://localhost",
        ],
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

    @property
    def requires_admin_second_factor(self) -> bool:
        """Whether an admin needs a second factor: always, unless switched off or local."""
        if self.admin_second_factor_required is not None:
            return self.admin_second_factor_required
        return self.environment != Environment.LOCAL

    @property
    def link_base(self) -> str:
        """The web app's address that links in letters open (F17.8)."""
        return (self.app_url or self.cors_origins[0]).rstrip("/")

    @property
    def mail_relay_send_url(self) -> str | None:
        """The App Engine relay's send endpoint, when letters go out through it (ADR-0019).

        Derived from the inbound domain `<project>.appspotmail.com`, so the deployment
        needs no setting of its own: the same App Engine app receives and sends.
        """
        appspot = ".appspotmail.com"
        sending = self.outgoing_mail or (
            "appengine" if self.inbound_email_domain.endswith(appspot) else "log"
        )
        if sending != "appengine":
            return None
        project = self.inbound_email_domain.removesuffix(appspot)
        return f"https://{project}.appspot.com/send"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide `Settings`, built and validated once.

    Cached so the environment is parsed and validated a single time per
    process rather than on every call site that needs configuration.
    """
    return Settings()
