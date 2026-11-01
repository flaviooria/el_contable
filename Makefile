.PHONY: dev lint format format-check typecheck test checks db-up db-down migrate revision downgrade clean install api-up api-down api-logs

# Targeted Python interpreter is required. Use uv which already manages the venv.
PY := uv run

install:
	uv sync --group dev

dev:
	$(PY) fastapi dev

lint:
	$(PY) ruff check .

format:
	$(PY) ruff format .

format-check:
	$(PY) ruff format --check .

typecheck:
	$(PY) mypy src

test:
	$(PY) pytest

checks: lint format-check typecheck test

db-up:
	docker compose up -d

db-down:
	docker compose down

api-up:
	docker compose up -d --build

api-down:
	docker compose down

api-logs:
	docker compose logs -f api

migrate:
	$(PY) alembic upgrade head

revision:
	$(PY) alembic revision --autogenerate -m "$(m)"

downgrade:
	$(PY) alembic downgrade -1

clean:
	rm -rf .ruff_cache .mypy_cache __pycache__ src/el_contable/features/**/__pycache__
