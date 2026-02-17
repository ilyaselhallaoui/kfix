"""Configuration management for kfix."""

import os
from contextlib import suppress
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class Config:
    """Manages kfix configuration stored in ~/.kfix/config.yaml.

    Configuration can also be provided via environment variables.
    Environment variables take precedence over config file values.

    Attributes:
        config_dir: Path to the configuration directory (~/.kfix).
        config_file: Path to the configuration file (~/.kfix/config.yaml).
    """

    def __init__(self) -> None:
        """Initialize configuration manager and ensure config directory exists."""
        self.config_dir = Path.home() / ".kfix"
        self.config_file = self.config_dir / "config.yaml"
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """Create configuration directory if it doesn't exist.

        The directory is created with default permissions (0o755).
        """
        self.config_dir.mkdir(mode=0o700, exist_ok=True)
        with suppress(OSError):
            os.chmod(self.config_dir, 0o700)

    def _write_config(self, config: Dict[str, Any]) -> None:
        """Write config with restrictive file permissions when possible."""
        payload = yaml.safe_dump(config, default_flow_style=False)

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        try:
            fd = os.open(self.config_file, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
        except OSError:
            with open(self.config_file, "w", encoding="utf-8") as f:
                f.write(payload)
            with suppress(OSError):
                os.chmod(self.config_file, 0o600)

    def get_api_key(self) -> Optional[str]:
        """Get the Anthropic API key from config or environment.

        The API key is retrieved in the following order of precedence:
        1. ANTHROPIC_API_KEY environment variable
        2. api_key in config file

        Returns:
            The API key string, or None if not configured.

        Example:
            >>> config = Config()
            >>> api_key = config.get_api_key()
            >>> if api_key:
            ...     print("API key is configured")
        """
        # Check environment first
        if api_key := os.environ.get("ANTHROPIC_API_KEY"):
            return api_key

        # Check config file
        if self.config_file.exists():
            with open(self.config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                return config.get("api_key")

        return None

    def set_api_key(self, api_key: str) -> None:
        """Save API key to config file.

        Args:
            api_key: The Anthropic API key to save.

        Example:
            >>> config = Config()
            >>> config.set_api_key("sk-ant-api03-...")
        """
        config: Dict[str, Any] = {}
        if self.config_file.exists():
            with open(self.config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

        config["api_key"] = api_key
        self._write_config(config)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: The configuration key to retrieve.
            default: Default value if key doesn't exist.

        Returns:
            The configuration value, or default if not found.

        Example:
            >>> config = Config()
            >>> timeout = config.get("timeout", 30)
        """
        if not self.config_file.exists():
            return default

        with open(self.config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
            return config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: The configuration key to set.
            value: The value to store.

        Example:
            >>> config = Config()
            >>> config.set("timeout", 60)
        """
        config: Dict[str, Any] = {}
        if self.config_file.exists():
            with open(self.config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

        config[key] = value
        self._write_config(config)
