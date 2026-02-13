"""Tests for config module."""

from pathlib import Path

import pytest

from reviewinator.config import ConfigError, load_config


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, tmp_path: Path) -> None:
        """Should load a valid config file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
github_token: ghp_test123
repos:
  - owner/repo1
  - org/repo2
refresh_interval: 600
""")
        config = load_config(config_file)

        assert config.github_token == "ghp_test123"
        assert config.repos == ["owner/repo1", "org/repo2"]
        assert config.refresh_interval == 600

    def test_load_config_default_refresh_interval(self, tmp_path: Path) -> None:
        """Should use default refresh_interval when not specified."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
github_token: ghp_test123
repos:
  - owner/repo1
""")
        config = load_config(config_file)

        assert config.refresh_interval == 300

    def test_load_config_missing_token_raises(self, tmp_path: Path) -> None:
        """Should raise ConfigError when github_token is missing."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
repos:
  - owner/repo1
""")
        with pytest.raises(ConfigError, match="github_token"):
            load_config(config_file)

    def test_load_config_missing_repos_raises(self, tmp_path: Path) -> None:
        """Should raise ConfigError when repos is missing."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
github_token: ghp_test123
""")
        with pytest.raises(ConfigError, match="repos"):
            load_config(config_file)

    def test_load_config_empty_repos_raises(self, tmp_path: Path) -> None:
        """Should raise ConfigError when repos list is empty."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
github_token: ghp_test123
repos: []
""")
        with pytest.raises(ConfigError, match="repos"):
            load_config(config_file)

    def test_load_config_file_not_found_raises(self, tmp_path: Path) -> None:
        """Should raise ConfigError when file doesn't exist."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(ConfigError, match="not found"):
            load_config(config_file)


class TestConfigPaths:
    """Tests for config path utilities."""

    def test_default_config_dir(self) -> None:
        """Should return ~/.config/reviewinator as default."""
        from reviewinator.config import get_config_dir

        config_dir = get_config_dir()
        assert config_dir == Path.home() / ".config" / "reviewinator"

    def test_default_config_path(self) -> None:
        """Should return ~/.config/reviewinator/config.yaml as default."""
        from reviewinator.config import get_config_path

        config_path = get_config_path()
        assert config_path == Path.home() / ".config" / "reviewinator" / "config.yaml"
