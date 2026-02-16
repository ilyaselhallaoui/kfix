"""Configuration management for kfix."""

import os
import yaml
from pathlib import Path
from typing import Optional


class Config:
    """Manages kfix configuration."""

    def __init__(self):
        self.config_dir = Path.home() / ".kfix"
        self.config_file = self.config_dir / "config.yaml"
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(exist_ok=True)

    def get_api_key(self) -> Optional[str]:
        """Get the Anthropic API key from config or environment."""
        # Check environment first
        if api_key := os.environ.get("ANTHROPIC_API_KEY"):
            return api_key

        # Check config file
        if self.config_file.exists():
            with open(self.config_file) as f:
                config = yaml.safe_load(f) or {}
                return config.get("api_key")

        return None

    def set_api_key(self, api_key: str):
        """Save API key to config file."""
        config = {}
        if self.config_file.exists():
            with open(self.config_file) as f:
                config = yaml.safe_load(f) or {}

        config["api_key"] = api_key

        with open(self.config_file, "w") as f:
            yaml.dump(config, f)

    def get(self, key: str, default=None):
        """Get a config value."""
        if not self.config_file.exists():
            return default

        with open(self.config_file) as f:
            config = yaml.safe_load(f) or {}
            return config.get(key, default)
