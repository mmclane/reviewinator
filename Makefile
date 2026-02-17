.PHONY: setup test test-cov lint format run clean build release _package _publish

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

release:
	@echo "Starting release process..."
	python scripts/bump_version.py
	$(MAKE) build
	$(MAKE) _package
	$(MAKE) _publish
	git add pyproject.toml setup.py
	git commit -m "chore: bump version to $$(python -c 'import tomli; print(tomli.load(open(\"pyproject.toml\", \"rb\"))[\"project\"][\"version\"])')"
	@echo "✓ Release complete"
	@echo "Push changes: git push && git push --tags"

_package:
	$(eval VERSION := $(shell python -c 'import tomli; print(tomli.load(open("pyproject.toml", "rb"))["project"]["version"])'))
	cd dist && zip -r ../Reviewinator-v$(VERSION).app.zip Reviewinator.app
	@echo "✓ Created Reviewinator-v$(VERSION).app.zip"

_publish:
	$(eval VERSION := $(shell python -c 'import tomli; print(tomli.load(open("pyproject.toml", "rb"))["project"]["version"])'))
	gh release create v$(VERSION) \
		--title "Release v$(VERSION)" \
		--notes "Release v$(VERSION)" \
		Reviewinator-v$(VERSION).app.zip
	@echo "✓ Published release v$(VERSION)"

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ .coverage dist build *.egg-info *.app.zip
