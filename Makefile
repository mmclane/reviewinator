.PHONY: setup test test-cov lint format run clean install uninstall

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

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ .coverage dist build *.egg-info

install:
	mkdir -p ~/Library/Logs/reviewinator
	cp launchd/com.reviewinator.plist ~/Library/LaunchAgents/com.reviewinator.plist
	launchctl load ~/Library/LaunchAgents/com.reviewinator.plist
	@echo "Reviewinator installed and started. It will now launch at login."

uninstall:
	launchctl unload ~/Library/LaunchAgents/com.reviewinator.plist
	rm ~/Library/LaunchAgents/com.reviewinator.plist
	@echo "Reviewinator removed from login items."
