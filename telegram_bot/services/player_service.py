"""
Player business logic layer.
Handles registration, profile retrieval, and stat management.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from telegram_bot.database import (
    db_create_player,
    db_delete_player,
    db_get_all_players,
    db_get_player,
    db_get_statistics,
    db_player_exists,
    db_team_taken,
)
from telegram_bot.models import Player, Statistics

logger = logging.getLogger(__name__)


async def register_player(
    user_id: int,
    username: str,
    full_name: str,
    team_name: str,
    team_flag: str,
) -> Tuple[bool, str]:
    """
    Register a new player.
    Returns (success, message).
    """
    if await db_player_exists(user_id):
        player = await db_get_player(user_id)
        return False, f"already_registered:{player.team_name}:{player.team_flag}"

    if await db_team_taken(team_name):
        return False, "team_taken"

    player = await db_create_player(user_id, username, full_name, team_name, team_flag)
    logger.info("New player registered: %s — %s %s", user_id, team_flag, team_name)
    return True, "success"


async def get_player(user_id: int) -> Optional[Player]:
    return await db_get_player(user_id)


async def get_all_players() -> List[Player]:
    return await db_get_all_players()


async def is_registered(user_id: int) -> bool:
    return await db_player_exists(user_id)


async def get_taken_teams() -> List[str]:
    players = await db_get_all_players()
    return [p.team_name for p in players]


async def deactivate_player(player_id: int) -> bool:
    """Soft-delete a player (set is_active=0)."""
    player = await db_get_player(player_id)
    if not player:
        return False
    await db_delete_player(player_id)
    logger.info("Player deactivated: %s", player_id)
    return True


async def get_player_statistics(player_id: int) -> Optional[Statistics]:
    return await db_get_statistics(player_id)


async def build_player_profile_text(player: Player) -> str:
    """
    Build a formatted profile text for a player.
    Used in both admin and player panels.
    """
    stats = await get_player_statistics(player.id) or Statistics(player_id=player.id)
    return (
        f"👤 <b>پروفایل بازیکن</b>\n\n"
        f"🆔 آی‌دی: <code>{player.id}</code>\n"
        f"👤 نام: <b>{player.full_name}</b>\n"
        f"🏳️ تیم: <b>{player.team_flag} {player.team_name}</b>\n\n"
        f"🎮 مسابقات: <b>{player.matches_played}</b>\n"
        f"✅ برد: <b>{player.wins}</b>\n"
        f"❌ باخت: <b>{player.losses}</b>\n"
        f"🤝 مساوی: <b>{player.draws}</b>\n\n"
        f"⚽ گل زده: <b>{player.goals_scored}</b>\n"
        f"😔 گل خورده: <b>{player.goals_missed}</b>\n"
        f"🧤 سیو: <b>{player.saves_made}</b>\n\n"
        f"📈 درصد برد: <b>{player.win_rate}%</b>\n"
        f"🔥 بهترین سری برد: <b>{player.win_streak}</b>\n"
        f"⚡ سری برد فعلی: <b>{player.current_streak}</b>"
    )
