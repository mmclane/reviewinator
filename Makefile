.PHONY: setup test test-cov lint format run clean build

setup:
	uv sync --all-extras

test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ -v --cov=src/reviewinator --cov-report=term-missing

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

run:
	uv run python -m reviewinator

build:
	python setup.py py2app
	@echo "✓ Built dist/Reviewinator.app"

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ .coverage dist build *.egg-info *.app.zip
