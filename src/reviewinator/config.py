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
    review_request_repos: list[str]
    created_pr_repos: list[str]
    created_pr_filter: str
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

    # Handle backward compatibility: repos -> review_request_repos
    if "review_request_repos" in data:
        review_request_repos = data["review_request_repos"]
    elif "repos" in data:
        review_request_repos = data["repos"]
    else:
        raise ConfigError("Missing required field: review_request_repos (or repos)")

    if not isinstance(review_request_repos, list) or not review_request_repos:
        raise ConfigError("review_request_repos must be a non-empty list")

    # Optional fields with defaults
    created_pr_repos = data.get("created_pr_repos", [])
    if not isinstance(created_pr_repos, list):
        raise ConfigError("created_pr_repos must be a list")

    created_pr_filter = data.get("created_pr_filter", "waiting")
    valid_filters = ["all", "waiting", "needs_attention"]
    if created_pr_filter not in valid_filters:
        raise ConfigError(
            f"created_pr_filter must be one of: {', '.join(valid_filters)} "
            f"(got: {created_pr_filter})"
        )

    refresh_interval = data.get("refresh_interval", 300)

    return Config(
        github_token=data["github_token"],
        review_request_repos=review_request_repos,
        created_pr_repos=created_pr_repos,
        created_pr_filter=created_pr_filter,
        refresh_interval=refresh_interval,
    )
