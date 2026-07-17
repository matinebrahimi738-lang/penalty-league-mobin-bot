"""
Configuration module for Penalty League Mobin (PLM) Telegram Bot.
Loads all settings from environment variables using python-dotenv.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Central configuration for the PLM bot."""

    # ── Bot credentials ──────────────────────────────────────────────────────
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))

    # ── Channel ──────────────────────────────────────────────────────────────
    channel_id: str = field(default_factory=lambda: os.getenv("CHANNEL_ID", ""))

    # ── Admins ───────────────────────────────────────────────────────────────
    admin_ids: List[int] = field(default_factory=list)

    # ── Database ─────────────────────────────────────────────────────────────
    database_path: str = field(
        default_factory=lambda: os.getenv("DATABASE_PATH", "plm_database.db")
    )

    # ── Match settings ───────────────────────────────────────────────────────
    match_timeout: int = field(
        default_factory=lambda: int(os.getenv("MATCH_TIMEOUT", "60"))
    )
    default_rounds: int = field(
        default_factory=lambda: int(os.getenv("DEFAULT_ROUNDS", "5"))
    )

    # ── Deployment ───────────────────────────────────────────────────────────
    bot_mode: str = field(default_factory=lambda: os.getenv("BOT_MODE", "polling"))
    webhook_host: str = field(default_factory=lambda: os.getenv("WEBHOOK_HOST", ""))
    webhook_path: str = field(
        default_factory=lambda: os.getenv("WEBHOOK_PATH", "/webhook")
    )
    webhook_port: int = field(
        default_factory=lambda: int(os.getenv("WEBHOOK_PORT", "10000"))
    )

    def __post_init__(self):
        # Parse admin IDs from comma-separated env var
        raw_admins = os.getenv("ADMIN_IDS", "")
        if raw_admins:
            try:
                self.admin_ids = [
                    int(uid.strip())
                    for uid in raw_admins.split(",")
                    if uid.strip().isdigit()
                ]
            except ValueError:
                logger.error("Invalid ADMIN_IDS format. Expected comma-separated integers.")
                self.admin_ids = []

        # Validate required settings
        if not self.bot_token:
            raise ValueError("BOT_TOKEN environment variable is required.")
        if not self.channel_id:
            logger.warning("CHANNEL_ID is not set. Channel publishing will be disabled.")

    @property
    def webhook_url(self) -> str:
        """Full webhook URL for Telegram."""
        return f"{self.webhook_host}{self.webhook_path}"

    def is_admin(self, user_id: int) -> bool:
        """Check if a Telegram user ID is an admin."""
        return user_id in self.admin_ids


# Singleton config instance
config = Config()
