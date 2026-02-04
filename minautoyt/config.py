"""Configuration management for 1MinAutoYT."""

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_config_dir() -> Path:
    """Get the configuration directory (same as script location)."""
    return Path(__file__).parent.parent


def get_default_watch_folder() -> str:
    """Get default iCloud Documents/Upload path for current user."""
    username = os.environ.get("USER", "user")
    return f"/Users/{username}/Library/Mobile Documents/com~apple~CloudDocs/Documents/Upload"


class Settings(BaseSettings):
    """Application settings loaded from environment and config file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Watch folder
    watch_folder: str = Field(default_factory=get_default_watch_folder)

    # YouTube settings
    youtube_channel: str = "minhsao"
    default_privacy: str = "unlisted"  # unlisted, private, public

    # Thumbnail settings
    thumbnail_style: str = "mrbeast"  # mrbeast, minimal, custom

    # Telegram settings (for approval workflow)
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # API Keys
    youtube_client_id: Optional[str] = None
    youtube_client_secret: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # AI settings
    ai_provider: str = "anthropic"  # anthropic, openai
    ai_model: str = "claude-sonnet-4-20250514"

    # Processing settings
    max_frames: int = 10
    transcribe_model: str = "base"  # tiny, base, small, medium, large

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Settings":
        """Load settings from config file and environment."""
        config_dir = get_config_dir()

        # Load .env file if exists
        env_file = config_dir / ".env"

        # Load config.json if exists
        config_file = config_path or config_dir / "config.json"
        config_data = {}

        if config_file.exists():
            with open(config_file) as f:
                config_data = json.load(f)

        # Create settings with config file values as defaults
        return cls(
            _env_file=env_file if env_file.exists() else None,
            **config_data,
        )

    def save(self, config_path: Optional[Path] = None) -> None:
        """Save settings to config file."""
        config_dir = get_config_dir()
        config_file = config_path or config_dir / "config.json"

        # Only save non-sensitive settings to config.json
        config_data = {
            "watch_folder": self.watch_folder,
            "youtube_channel": self.youtube_channel,
            "default_privacy": self.default_privacy,
            "thumbnail_style": self.thumbnail_style,
            "telegram_bot_token": self.telegram_bot_token,
            "telegram_chat_id": self.telegram_chat_id,
            "ai_provider": self.ai_provider,
            "ai_model": self.ai_model,
            "max_frames": self.max_frames,
            "transcribe_model": self.transcribe_model,
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f, indent=2)

    def save_env(self, env_path: Optional[Path] = None) -> None:
        """Save API keys to .env file."""
        config_dir = get_config_dir()
        env_file = env_path or config_dir / ".env"

        lines = []
        if self.youtube_client_id:
            lines.append(f"YOUTUBE_CLIENT_ID={self.youtube_client_id}")
        if self.youtube_client_secret:
            lines.append(f"YOUTUBE_CLIENT_SECRET={self.youtube_client_secret}")
        if self.openai_api_key:
            lines.append(f"OPENAI_API_KEY={self.openai_api_key}")
        if self.anthropic_api_key:
            lines.append(f"ANTHROPIC_API_KEY={self.anthropic_api_key}")

        with open(env_file, "w") as f:
            f.write("\n".join(lines) + "\n")


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings.load()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from disk."""
    global _settings
    _settings = Settings.load()
    return _settings
