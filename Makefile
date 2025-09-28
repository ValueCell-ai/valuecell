format:
	ruff format --config ./python/pyproject.toml ./python/ && uv run --directory ./python isort .

lint:
	ruff check --config ./python/pyproject.toml ./python/

test:
	uv run pytest ./python