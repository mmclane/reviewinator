"""Configuration loading and validation."""

from dataclasses import dataclass
from pathlib import Path

import yaml


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""


@dataclass
class Config:
    """Application configuration."""

    github_token: str
    excluded_repos: list[str]
    excluded_review_teams: list[str]
    created_pr_filter: str
    activity_lookback_days: int
    refresh_interval: int = 300


def get_config_dir() -> Path:
    """Return the default configuration directory."""
    return Path.home() / ".config" / "reviewinator"


def get_config_path() -> Path:
    """Return the default configuration file path."""
    return get_config_dir() / "config.yaml"


def load_config(config_path: Path) -> Config:
    """Load and validate configuration from a YAML file.

    Args:
        config_path: Path to the config.yaml file.

    Returns:
        Validated Config object.

    Raises:
        ConfigError: If config file is missing or invalid.
    """
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        with config_path.open() as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML: {e}")

    if not isinstance(data, dict):
        raise ConfigError("Config must be a YAML mapping")

    # Required fields
    if "github_token" not in data:
        raise ConfigError("Missing required field: github_token")

    # Default excluded_review_teams to empty list if not present
    if "excluded_review_teams" not in data:
        data["excluded_review_teams"] = []

    # Optional fields with defaults
    excluded_repos = data.get("excluded_repos", [])
    if not isinstance(excluded_repos, list):
        raise ConfigError("excluded_repos must be a list")

    created_pr_filter = data.get("created_pr_filter", "either")
    valid_filters = ["all", "waiting", "needs_attention", "either"]
    if created_pr_filter not in valid_filters:
        raise ConfigError(
            f"created_pr_filter must be one of: {', '.join(valid_filters)} "
            f"(got: {created_pr_filter})"
        )

    activity_lookback_days = data.get("activity_lookback_days", 14)
    if not isinstance(activity_lookback_days, int) or activity_lookback_days <= 0:
        raise ConfigError("activity_lookback_days must be a positive integer")

    refresh_interval = data.get("refresh_interval", 300)

    return Config(
        github_token=data["github_token"],
        excluded_repos=excluded_repos,
        excluded_review_teams=data["excluded_review_teams"],
        created_pr_filter=created_pr_filter,
        activity_lookback_days=activity_lookback_days,
        refresh_interval=refresh_interval,
    )
