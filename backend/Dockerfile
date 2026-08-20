# Backend dev image: installs dependencies with uv and serves the API with
# autoreload. docker-compose.yml bind-mounts the source over /app, so editing
# a file on the host is picked up without rebuilding the image (F0.4.1).

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Dependencies first so the layer is cached until pyproject.toml/uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

EXPOSE 8000

# `/app/.venv` is a named volume (see docker-compose.yml), so it can still
# hold whatever was installed the last time the image was built. Syncing
# again at startup — fast and a no-op when nothing changed — keeps it
# current with the bind-mounted pyproject.toml/uv.lock instead of silently
# shadowing a dependency added since the volume was first populated.
CMD ["sh", "-c", "uv sync --frozen && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
