"""
League management service.
Handles ranking calculations and league table generation.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from telegram_bot.database import (
    db_get_league_table,
    db_sync_league_player_info,
    db_update_league,
)
from telegram_bot.models import LeagueEntry, Match

logger = logging.getLogger(__name__)


async def get_league_table() -> List[LeagueEntry]:
    """Fetch the sorted league table from DB."""
    entries = await db_get_league_table()
    # Sort by ranking key descending
    entries.sort(key=lambda e: e.rank_key, reverse=True)
    return entries


async def format_league_table() -> str:
    """Build the full Persian league table text."""
    entries = await get_league_table()
    if not entries:
        return "📭 جدول لیگ خالی است. هنوز مسابقه‌ای ثبت نشده."

    lines = ["🏆 <b>جدول لیگ Penalty League Mobin</b>\n"]
    lines.append(
        "<code>رتبه  تیم             P  W  D  L  GF GA GD  Pts</code>"
    )
    lines.append("<code>" + "─" * 50 + "</code>")

    for rank, e in enumerate(entries, 1):
        medal = ""
        if rank == 1:
            medal = "🥇"
        elif rank == 2:
            medal = "🥈"
        elif rank == 3:
            medal = "🥉"
        else:
            medal = f" {rank}."

        gd_str = f"+{e.goal_difference}" if e.goal_difference >= 0 else str(e.goal_difference)

        line = (
            f"<code>{medal:<4} {e.team_flag} {e.team_name:<12} "
            f"{e.played:<3}{e.wins:<3}{e.draws:<3}{e.losses:<3}"
            f"{e.goals_for:<3}{e.goals_against:<3}{gd_str:<4}{e.points}</code>"
        )
        lines.append(line)

    return "\n".join(lines)


async def update_league_after_match(match: Match) -> None:
    """
    Called after a match finishes.
    Updates league stats for both players.
    """
    winner_id = match.winner_id
    p1 = match.player1_id
    p2 = match.player2_id

    if winner_id == p1:
        # Player 1 wins
        await db_update_league(
            p1,
            win=True,
            goals_for=match.player1_score,
            goals_against=match.player2_score,
        )
        await db_update_league(
            p2,
            loss=True,
            goals_for=match.player2_score,
            goals_against=match.player1_score,
        )
        logger.info("League updated: P1(%s) WIN over P2(%s)", p1, p2)

    elif winner_id == p2:
        # Player 2 wins
        await db_update_league(
            p2,
            win=True,
            goals_for=match.player2_score,
            goals_against=match.player1_score,
        )
        await db_update_league(
            p1,
            loss=True,
            goals_for=match.player1_score,
            goals_against=match.player2_score,
        )
        logger.info("League updated: P2(%s) WIN over P1(%s)", p2, p1)

    else:
        # Draw
        await db_update_league(
            p1,
            draw=True,
            goals_for=match.player1_score,
            goals_against=match.player2_score,
        )
        await db_update_league(
            p2,
            draw=True,
            goals_for=match.player2_score,
            goals_against=match.player1_score,
        )
        logger.info("League updated: DRAW between P1(%s) and P2(%s)", p1, p2)


async def sync_player_in_league(player_id: int) -> None:
    """Keep league entry in sync with player's current team info."""
    await db_sync_league_player_info(player_id)


async def get_player_rank(player_id: int) -> Optional[int]:
    """Return the current rank of a player (1-indexed)."""
    table = await get_league_table()
    for rank, entry in enumerate(table, 1):
        if entry.player_id == player_id:
            return rank
    return None
