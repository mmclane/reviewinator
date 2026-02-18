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
        config_file.write_text("github_token: test_token\ncreated_pr_filter: invalid\n")
        with pytest.raises(ConfigError, match="created_pr_filter must be one of"):
            load_config(config_file)

    def test_load_config_created_pr_filter_any(self, tmp_path: Path) -> None:
        """Test created_pr_filter accepts 'any' option."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
github_token: test_token
created_pr_filter: any
"""
        )
        config = load_config(config_file)
        assert config.created_pr_filter == "any"

    def test_load_config_created_pr_filter_defaults_to_any(self, tmp_path: Path) -> None:
        """Test created_pr_filter defaults to 'any'."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("github_token: test_token\n")
        config = load_config(config_file)
        assert config.created_pr_filter == "any"

    def test_load_config_created_pr_filter_either_rejected(self, tmp_path: Path) -> None:
        """Test created_pr_filter rejects old 'either' value."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("github_token: test_token\ncreated_pr_filter: either\n")
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

    def test_load_config_activity_lookback_days_defaults_to_14(self, tmp_path: Path) -> None:
        """Test activity_lookback_days defaults to 14."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("github_token: test_token\n")
        config = load_config(config_file)
        assert config.activity_lookback_days == 14

    def test_load_config_activity_lookback_days_custom_value(self, tmp_path: Path) -> None:
        """Test activity_lookback_days accepts custom positive integer."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
github_token: test_token
activity_lookback_days: 30
"""
        )
        config = load_config(config_file)
        assert config.activity_lookback_days == 30

    def test_load_config_activity_lookback_days_rejects_negative(self, tmp_path: Path) -> None:
        """Test activity_lookback_days rejects negative values."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
github_token: test_token
activity_lookback_days: -5
"""
        )
        with pytest.raises(ConfigError, match="activity_lookback_days must be a positive integer"):
            load_config(config_file)

    def test_load_config_activity_lookback_days_rejects_zero(self, tmp_path: Path) -> None:
        """Test activity_lookback_days rejects zero."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
github_token: test_token
activity_lookback_days: 0
"""
        )
        with pytest.raises(ConfigError, match="activity_lookback_days must be a positive integer"):
            load_config(config_file)

    def test_excluded_review_teams_defaults_to_empty_list(self, tmp_path: Path) -> None:
        """Test that excluded_review_teams defaults to empty list if not specified."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
github_token: test_token
excluded_repos: []
created_pr_filter: all
activity_lookback_days: 14
"""
        )
        config = load_config(config_file)
        assert config.excluded_review_teams == []

    def test_excluded_review_teams_accepts_valid_format(self, tmp_path: Path) -> None:
        """Test that excluded_review_teams accepts valid 'org/team' format."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
github_token: test_token
excluded_repos: []
excluded_review_teams:
  - snapptinc/all-engineers
  - myorg/team-foo
created_pr_filter: all
activity_lookback_days: 14
"""
        )
        config = load_config(config_file)
        assert config.excluded_review_teams == ["snapptinc/all-engineers", "myorg/team-foo"]

    def test_excluded_review_teams_accepts_underscores(self, tmp_path: Path) -> None:
        """Test that excluded_review_teams accepts underscores in org and team names."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
github_token: test_token
excluded_repos: []
excluded_review_teams:
  - my_org/team_foo
  - org_name/team-name_123
created_pr_filter: all
activity_lookback_days: 14
"""
        )
        config = load_config(config_file)
        assert config.excluded_review_teams == ["my_org/team_foo", "org_name/team-name_123"]

    def test_excluded_review_teams_rejects_no_slash(self, tmp_path: Path) -> None:
        """Test that excluded_review_teams rejects entries without slash."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
github_token: test_token
excluded_repos: []
excluded_review_teams:
  - invalidteam
created_pr_filter: all
activity_lookback_days: 14
"""
        )
        with pytest.raises(
            ConfigError, match="excluded_review_teams entries must be in format 'org/team'"
        ):
            load_config(config_file)

    def test_excluded_review_teams_rejects_empty_org(self, tmp_path: Path) -> None:
        """Test that excluded_review_teams rejects entries with empty org."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
github_token: test_token
excluded_repos: []
excluded_review_teams:
  - /team
created_pr_filter: all
activity_lookback_days: 14
"""
        )
        with pytest.raises(
            ConfigError, match="excluded_review_teams entries must be in format 'org/team'"
        ):
            load_config(config_file)

    def test_excluded_review_teams_rejects_empty_team(self, tmp_path: Path) -> None:
        """Test that excluded_review_teams rejects entries with empty team."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
github_token: test_token
excluded_repos: []
excluded_review_teams:
  - org/
created_pr_filter: all
activity_lookback_days: 14
"""
        )
        with pytest.raises(
            ConfigError, match="excluded_review_teams entries must be in format 'org/team'"
        ):
            load_config(config_file)

    def test_excluded_review_teams_rejects_non_list(self, tmp_path: Path) -> None:
        """Test that excluded_review_teams rejects non-list values."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
github_token: test_token
excluded_repos: []
excluded_review_teams: "not-a-list"
created_pr_filter: all
activity_lookback_days: 14
"""
        )
        with pytest.raises(ConfigError, match="excluded_review_teams must be a list"):
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
