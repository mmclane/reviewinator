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
refresh_interval: 600
""")
        config = load_config(config_file)

        assert config.github_token == "ghp_test123"
        assert config.refresh_interval == 600

    def test_load_config_default_refresh_interval(self, tmp_path: Path) -> None:
        """Should use default refresh_interval when not specified."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
github_token: ghp_test123
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


    def test_load_config_file_not_found_raises(self, tmp_path: Path) -> None:
        """Should raise ConfigError when file doesn't exist."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(ConfigError, match="not found"):
            load_config(config_file)


    def test_load_config_invalid_created_pr_filter_raises(self, tmp_path: Path) -> None:
        """Test invalid created_pr_filter raises error."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "github_token: test_token\n"
            "created_pr_filter: invalid\n"
        )
        with pytest.raises(ConfigError, match="created_pr_filter must be one of"):
            load_config(config_file)

    def test_load_config_with_excluded_repos(self, tmp_path: Path) -> None:
        """Test loading config with excluded_repos field."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
github_token: test_token
excluded_repos:
  - owner/repo1
  - owner/repo2
"""
        )
        config = load_config(config_file)
        assert config.excluded_repos == ["owner/repo1", "owner/repo2"]

    def test_load_config_excluded_repos_defaults_to_empty_list(self, tmp_path: Path) -> None:
        """Test excluded_repos defaults to empty list when not specified."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("github_token: test_token\n")
        config = load_config(config_file)
        assert config.excluded_repos == []

    def test_load_config_excluded_repos_must_be_list(self, tmp_path: Path) -> None:
        """Test excluded_repos must be a list."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
github_token: test_token
excluded_repos: "not-a-list"
"""
        )
        with pytest.raises(ConfigError, match="excluded_repos must be a list"):
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
