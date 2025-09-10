format:
	ruff format --config ./python/pyproject.toml ./python/

lint:
	ruff check --config ./python/pyproject.toml ./python/

test:
	uv run pytest ./python