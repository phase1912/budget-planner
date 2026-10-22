# Configuration

Every setting the backend reads, in one place. `app.config.Settings`
(`backend/app/config.py`) is the single source — nothing else in the codebase reads
`os.environ`/`os.getenv` directly (enforced by
`backend/tests/test_config.py::test_no_direct_os_environ_reads_outside_the_config_module`),
so a value that is not a field on `Settings` is not configurable.

**Keep this table current.** Adding, renaming or re-defaulting a field on `Settings` is
not done until this file reflects it — see `CLAUDE.md`.

## How values are resolved

Pydantic-settings layers three sources, highest priority first:

1. An actual environment variable (`ENVIRONMENT`, `DATABASE_URL`, ...) — case-insensitive.
2. The same key in a `.env` file next to the process's working directory (see
   [`environments.md`](environments.md) for which `.env` file that is, per environment).
3. The field's default below, if it has one.

A field with no default (`database_url`, `anthropic_api_key`) makes `Settings()` raise
`pydantic.ValidationError` immediately if unset — fail-fast at boot, not at first use.

## Settings

| Field | Env var | Required | Default | Purpose |
|---|---|---|---|---|
| `environment` | `ENVIRONMENT` | No | `local` | Which deployment tier this process is (`local` / `staging` / `production`, `app.config.Environment`). See [`environments.md`](environments.md) for what each implies. |
| `database_url` | `DATABASE_URL` | **Yes** | — | PostgreSQL connection string. Must use an async driver scheme (`postgresql+asyncpg://`) — SQLAlchemy 2's async engine cannot use the sync `psycopg2` scheme (ADR-0001). |
| `database_pool_size` | `DATABASE_POOL_SIZE` | No | `5` | Persistent connections kept open per process (F0.3.1). |
| `database_max_overflow` | `DATABASE_MAX_OVERFLOW` | No | `10` | Extra connections allowed above the pool under load (F0.3.1). |
| `anthropic_api_key` | `ANTHROPIC_API_KEY` | No | — | Anthropic credential, needed only when `llm_model` is an Anthropic model; production uses Vertex AI and sets none (ADR-0014). A `SecretStr` — never logged or included in a repr. See [secret handling](#secret-handling) below. |
| `anthropic_model` | `ANTHROPIC_MODEL` | No | `claude-haiku-4-5-20251001` | Claude model id used for extraction, categorisation and advice. The default is the local/staging tier; production sets this explicitly. See ADR-0005 and [`environments.md`](environments.md#the-matrix). |
| `llm_model` | `LLM_MODEL` | No | `gemini/gemini-3.6-flash` | litellm model string for the universal agent (ADR-0006). Prefix determines the provider (`gemini/`, `openai/`, etc.). |
| `llm_api_key` | `LLM_API_KEY` | No | — | Provider API key. If missing, litellm uses provider-specific defaults. |
| `llm_api_base` | `LLM_API_BASE` | No | — | Optional base URL. Required for proxies, OpenAI-compatible APIs (like Z-AI), or self-hosted models. |
| `vertex_project` | `VERTEX_PROJECT` | No | — | Google Cloud project for `vertex_ai/` models. Credentials come from the runtime's service account, so there is no key (ADR-0014). |
| `vertex_location` | `VERTEX_LOCATION` | No | — | Vertex AI region for `vertex_ai/` models, e.g. `us-central1`. |
| `llm_disable_reasoning` | `LLM_DISABLE_REASONING` | No | `false` | Ask the provider to answer without a reasoning pass. Required for local hybrid-reasoning models (Qwen3 and kin via LM Studio/Ollama), which otherwise put the whole answer in the reasoning channel and return empty `content`. Hosted providers reject the parameter — leave it false. |
| `llm_disable_json_schema` | `LLM_DISABLE_JSON_SCHEMA` | No | `false` | Stop sending `response_format` to the provider. Required for LM Studio, whose constrained decoding corrupts the key names it emits, so extractions come back empty; the prompt and `Agent._parse_response` cover it instead. |
| `llm_max_concurrency` | `LLM_MAX_CONCURRENCY` | No | `2` | How many receipts one upload job extracts in parallel. Keep at 1 for a locally served model — a single instance serialises the calls anyway and they evict each other's prompt cache. |
| `upload_job_timeout_seconds` | `UPLOAD_JOB_TIMEOUT_SECONDS` | No | `900` | How long one upload job may spend extracting before it is abandoned and marked failed, so a wedged provider call cannot leave it in PROCESSING forever. |
| `ocr_confidence_threshold` | `OCR_CONFIDENCE_THRESHOLD` | No | `0.80` | Below this, an extracted required field is flagged "low confidence" instead of accepted silently (BRD A10). Must be within `[0.0, 1.0]`. See ADR-0005. |
| `categorization_confidence_threshold` | `CATEGORIZATION_CONFIDENCE_THRESHOLD` | No | `0.70` | Below this, a line item is `Uncategorized` and flagged for review instead of guessed (BRD C3). Must be within `[0.0, 1.0]`. See ADR-0005. |
| `price_freshness_days` | `PRICE_FRESHNESS_DAYS` | No | `90` | How recent a shop's price must be to say another shop is cheaper (F16.3); older prices may no longer hold. At least 1. |
| `storage_backend` | `STORAGE_BACKEND` | No | `s3` | `s3` for an S3-compatible store (MinIO locally), `gcs` for Cloud Storage as the runtime's service account, keyless (ADR-0014). `S3_BUCKET_NAME` names the bucket either way. |
| `exchange_rate_source` | `EXCHANGE_RATE_SOURCE` | No | `nbp` | `nbp` converts foreign receipts at the National Bank of Poland's rates, the ECB's as fallback (ADR-0016); `off` stores them unconverted. The test suite runs with `off`, so it never reaches the network. |
| `free_monthly_credits` | `FREE_MONTHLY_CREDITS` | No | `150` | AI credits (one is 0.001 USD of model cost) the free plan may spend per calendar month (F21.9, ADR-0030). Set from Terraform's `free_monthly_credits`. |
| `paid_monthly_credits` | `PAID_MONTHLY_CREDITS` | No | `2500` | AI credits the paid plan may spend per calendar month (F18.4, F21.9). |
| `credits_per_receipt` | `CREDITS_PER_RECEIPT` | No | `10` | What a receipt read is taken to cost until 20 reads in 30 days were recorded; then the measured average (F21.9.3). |
| `credits_per_message` | `CREDITS_PER_MESSAGE` | No | `4` | What a message to the assistant is taken to cost until measured the same way. |
| `free_receipts_per_upload` | `FREE_RECEIPTS_PER_UPLOAD` | No | `5` | Receipts one upload may hold on the free plan, so one request cannot spend the month. |
| `free_assistant_rounds` | `FREE_ASSISTANT_ROUNDS` | No | `4` | Rounds of tool use one message to the assistant may take on the free plan. |
| `admin_second_factor_required` | `ADMIN_SECOND_FACTOR_REQUIRED` | No | unset | Whether admin pages need a session opened with two-factor sign-in (F18.6.1); unset means yes everywhere but `local`. |
| `daily_credit_ceiling` | `DAILY_CREDIT_CEILING` | No | `3000` | AI credits charged per UTC day across every non-admin account (F21.9): bounds the bill. Set from Terraform's `daily_credit_ceiling`. |
| `admin_emails` | `ADMIN_EMAILS` | No | `[]` | JSON list of the super admins' emails (ADR-0021): admins with no AI credit limits who alone appoint admins (accounts with role `admin`) and read the admin log. Set from `terraform.tfvars`, which is kept out of git. |
| `build_sha` | `BUILD_SHA` | No | `dev` | Set by CI/CD at deploy time; stays `dev` outside a built image. Surfaced for support/debugging, not read by any business logic. |

## Where each environment's values actually come from

`.env.example` files hold placeholders, never real credentials — copy to `.env` (gitignored)
and fill in:

| File | Consumed by |
|---|---|
| [`/.env.example`](../../.env.example) | `docker-compose.yml` — Postgres/MinIO container credentials and ports, plus `ANTHROPIC_API_KEY` passed through to the `backend` container |
| [`backend/.env.example`](../../backend/.env.example) | `app.config.Settings` directly, when running the API on the host (`uv run`) or inside the `backend` container (bind-mounted to the same path `Settings`' `env_file=".env"` reads) |
| [`frontend/.env.example`](../../frontend/.env.example) | Vite, for `VITE_API_BASE_URL` — unrelated to backend `Settings` |

Staging and production do not use a `.env` file at all — see
[`environments.md`](environments.md) for where their values come from instead.

## Secret handling

`anthropic_api_key` and `database_url` (which embeds the database credential) are the
only secrets `Settings` reads. How each is stored, rotated, and how a leak is caught is
[`secrets.md`](secrets.md) — this file only says which settings they are.
