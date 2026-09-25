# Common workflows across both toolchains, so a fresh clone needs one command
# per action instead of memorising `uv run` here and `npm run` there (F0.4.2).
# `test`, `lint` and `typecheck` run the backend step before the frontend
# step and stop at the first failure, matching the order CI checks them in.
#
# `migrate` runs on the host (`uv run alembic`) against postgres's port
# exposed by docker-compose.yml, rather than inside the container — see
# backend/.env.example. That means it works whether the stack was started
# with `make up` or the app processes are running on the host instead.
#
# `seed` recreates the demo account (demo@budget-agent.local / demo-budget-agent)
# from real receipts in backend/scripts/seed_data/, dated so the newest falls in
# the current month (F5.8). Run `migrate` first. `seed-export EMAIL=...`
# rewrites that data from an account's stored receipts.

.PHONY: up down migrate seed seed-export test lint typecheck

up:
	docker compose up

down:
	docker compose down

migrate:
	cd backend && uv run alembic upgrade head

seed:
	cd backend && uv run python scripts/seed_demo_data.py

seed-export:
	cd backend && uv run python scripts/seed_demo_data.py export --email $(EMAIL)

test:
	cd backend && uv run pytest
	cd frontend && npm run test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npm run lint && npm run format

typecheck:
	cd backend && uv run mypy .
	cd frontend && npm run typecheck
