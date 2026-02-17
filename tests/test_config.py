"""Tests for config module."""

import os
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from kfix.config import Config


class TestConfig:
    """Test suite for Config class."""

    def test_init_creates_config_dir(self, tmp_path, monkeypatch):
        """Test that config directory is created on init."""
        config_dir = tmp_path / ".kfix"
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config()

        assert config.config_dir == config_dir
        assert config_dir.exists()

    def test_get_api_key_from_env(self, tmp_path, monkeypatch):
        """Test getting API key from environment variable."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-from-env")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config()
        api_key = config.get_api_key()

        assert api_key == "test-key-from-env"

    def test_get_api_key_from_config_file(self, tmp_path, monkeypatch):
        """Test getting API key from config file."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config()
        config_file = config.config_dir / "config.yaml"
        config_file.write_text("api_key: test-key-from-file\n")

        api_key = config.get_api_key()

        assert api_key == "test-key-from-file"

    def test_get_api_key_none_when_not_configured(self, tmp_path, monkeypatch):
        """Test getting API key returns None when not configured."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config()
        api_key = config.get_api_key()

        assert api_key is None

    def test_set_api_key(self, tmp_path, monkeypatch):
        """Test setting API key."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config()
        config.set_api_key("new-test-key")

        # Read back the key
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert config.get_api_key() == "new-test-key"

    def test_set_api_key_updates_existing_config(self, tmp_path, monkeypatch):
        """Test updating API key in existing config."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config()
        config.set("other_key", "other_value")
        config.set_api_key("new-api-key")

        # Both keys should exist
        assert config.get("other_key") == "other_value"
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert config.get_api_key() == "new-api-key"

    def test_get_config_value(self, tmp_path, monkeypatch):
        """Test getting a config value."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config()
        config.set("timeout", 60)

        assert config.get("timeout") == 60

    def test_get_config_value_with_default(self, tmp_path, monkeypatch):
        """Test getting config value with default."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config()

        assert config.get("non_existent_key", "default_value") == "default_value"

    def test_set_config_value(self, tmp_path, monkeypatch):
        """Test setting a config value."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config()
        config.set("custom_key", "custom_value")

        assert config.get("custom_key") == "custom_value"

    def test_env_takes_precedence_over_file(self, tmp_path, monkeypatch):
        """Test environment variable takes precedence over config file."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")

        config = Config()
        config.set_api_key("file-key")

        # Environment should take precedence
        assert config.get_api_key() == "env-key"
