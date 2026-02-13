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
    repos: list[str]
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

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if not data:
        data = {}

    if "github_token" not in data:
        raise ConfigError("Missing required field: github_token")

    if "repos" not in data or not data["repos"]:
        raise ConfigError("Missing or empty required field: repos")

    return Config(
        github_token=data["github_token"],
        repos=data["repos"],
        refresh_interval=data.get("refresh_interval", 300),
    )
