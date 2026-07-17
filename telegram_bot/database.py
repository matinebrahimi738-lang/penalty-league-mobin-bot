"""
Async SQLite database layer for PLM.
Handles schema creation, migrations, and all raw SQL queries.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import aiosqlite

from telegram_bot.config import config
from telegram_bot.models import (
    Admin,
    Direction,
    LeagueEntry,
    Match,
    MatchStatus,
    Player,
    Round,
    RoundResult,
    RPSChoice,
    Setting,
    Statistics,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# DDL — CREATE TABLES
# ─────────────────────────────────────────────────────────────────────────────

_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS players (
    id              INTEGER PRIMARY KEY,   -- Telegram user ID
    username        TEXT    NOT NULL DEFAULT '',
    full_name       TEXT    NOT NULL DEFAULT '',
    team_name       TEXT    NOT NULL DEFAULT '',
    team_flag       TEXT    NOT NULL DEFAULT '',
    matches_played  INTEGER NOT NULL DEFAULT 0,
    wins            INTEGER NOT NULL DEFAULT 0,
    losses          INTEGER NOT NULL DEFAULT 0,
    draws           INTEGER NOT NULL DEFAULT 0,
    goals_scored    INTEGER NOT NULL DEFAULT 0,
    goals_missed    INTEGER NOT NULL DEFAULT 0,
    saves_made      INTEGER NOT NULL DEFAULT 0,
    win_streak      INTEGER NOT NULL DEFAULT 0,
    current_streak  INTEGER NOT NULL DEFAULT 0,
    is_active       INTEGER NOT NULL DEFAULT 1,
    registered_at   REAL    NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS admins (
    id          INTEGER PRIMARY KEY,   -- Telegram user ID
    username    TEXT    NOT NULL DEFAULT '',
    full_name   TEXT    NOT NULL DEFAULT '',
    is_super    INTEGER NOT NULL DEFAULT 0,
    added_at    REAL    NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS matches (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    player1_id          INTEGER NOT NULL REFERENCES players(id),
    player2_id          INTEGER NOT NULL REFERENCES players(id),
    player1_team        TEXT    NOT NULL,
    player2_team        TEXT    NOT NULL,
    player1_flag        TEXT    NOT NULL,
    player2_flag        TEXT    NOT NULL,
    channel_id          TEXT    NOT NULL DEFAULT '',
    status              TEXT    NOT NULL DEFAULT 'pending',
    max_rounds          INTEGER NOT NULL DEFAULT 5,
    player1_rps         TEXT,
    player2_rps         TEXT,
    rps_winner_id       INTEGER,
    current_round       INTEGER NOT NULL DEFAULT 0,
    player1_score       INTEGER NOT NULL DEFAULT 0,
    player2_score       INTEGER NOT NULL DEFAULT 0,
    winner_id           INTEGER,
    channel_message_id  INTEGER,
    player1_message_id  INTEGER,
    player2_message_id  INTEGER,
    created_at          REAL    NOT NULL DEFAULT (unixepoch()),
    started_at          REAL,
    finished_at         REAL
);

CREATE TABLE IF NOT EXISTS rounds (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id            INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    round_number        INTEGER NOT NULL,
    shooter_id          INTEGER NOT NULL,
    goalkeeper_id       INTEGER NOT NULL,
    shooter_direction   TEXT,
    goalkeeper_direction TEXT,
    result              TEXT    NOT NULL DEFAULT 'pending',
    is_sudden_death     INTEGER NOT NULL DEFAULT 0,
    completed_at        REAL,
    UNIQUE(match_id, round_number)
);

CREATE TABLE IF NOT EXISTS league (
    player_id       INTEGER PRIMARY KEY REFERENCES players(id),
    team_name       TEXT    NOT NULL DEFAULT '',
    team_flag       TEXT    NOT NULL DEFAULT '',
    full_name       TEXT    NOT NULL DEFAULT '',
    played          INTEGER NOT NULL DEFAULT 0,
    wins            INTEGER NOT NULL DEFAULT 0,
    draws           INTEGER NOT NULL DEFAULT 0,
    losses          INTEGER NOT NULL DEFAULT 0,
    goals_for       INTEGER NOT NULL DEFAULT 0,
    goals_against   INTEGER NOT NULL DEFAULT 0,
    points          INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS statistics (
    player_id               INTEGER PRIMARY KEY REFERENCES players(id),
    total_matches           INTEGER NOT NULL DEFAULT 0,
    total_wins              INTEGER NOT NULL DEFAULT 0,
    total_losses            INTEGER NOT NULL DEFAULT 0,
    total_draws             INTEGER NOT NULL DEFAULT 0,
    total_goals_scored      INTEGER NOT NULL DEFAULT 0,
    total_goals_conceded    INTEGER NOT NULL DEFAULT 0,
    total_saves             INTEGER NOT NULL DEFAULT 0,
    total_shots             INTEGER NOT NULL DEFAULT 0,
    best_win_streak         INTEGER NOT NULL DEFAULT 0,
    current_win_streak      INTEGER NOT NULL DEFAULT 0,
    last_match_result       TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL DEFAULT '',
    updated_at  REAL NOT NULL DEFAULT (unixepoch())
);

-- Default settings
INSERT OR IGNORE INTO settings (key, value) VALUES
    ('league_name', 'Penalty League Mobin'),
    ('season', '1'),
    ('max_rounds', '5'),
    ('rps_timeout', '60'),
    ('round_timeout', '60'),
    ('maintenance_mode', '0');
"""

# ─────────────────────────────────────────────────────────────────────────────
# CONNECTION POOL (simple singleton)
# ─────────────────────────────────────────────────────────────────────────────

_db_connection: Optional[aiosqlite.Connection] = None


async def get_db() -> aiosqlite.Connection:
    """Return (and lazily open) the singleton DB connection."""
    global _db_connection
    if _db_connection is None:
        _db_connection = await aiosqlite.connect(config.database_path)
        _db_connection.row_factory = aiosqlite.Row
        await _db_connection.executescript(_SCHEMA_SQL)
        await _db_connection.commit()
        logger.info("Database connection established: %s", config.database_path)
    return _db_connection


async def close_db() -> None:
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None
        logger.info("Database connection closed.")


@asynccontextmanager
async def db_cursor() -> AsyncGenerator[aiosqlite.Cursor, None]:
    """Async context manager that yields a cursor and auto-commits."""
    conn = await get_db()
    async with conn.cursor() as cur:
        yield cur
    await conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — row → dict
# ─────────────────────────────────────────────────────────────────────────────

def _row_to_dict(row: Optional[aiosqlite.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return dict(row)


# ═══════════════════════════════════════════════════════════════════════════════
# PLAYER QUERIES
# ═══════════════════════════════════════════════════════════════════════════════

async def db_get_player(user_id: int) -> Optional[Player]:
    async with db_cursor() as cur:
        await cur.execute("SELECT * FROM players WHERE id = ?", (user_id,))
        row = _row_to_dict(await cur.fetchone())
    if not row:
        return None
    return _dict_to_player(row)


async def db_get_all_players() -> List[Player]:
    async with db_cursor() as cur:
        await cur.execute("SELECT * FROM players WHERE is_active = 1 ORDER BY wins DESC")
        rows = await cur.fetchall()
    return [_dict_to_player(dict(r)) for r in rows]


async def db_player_exists(user_id: int) -> bool:
    async with db_cursor() as cur:
        await cur.execute("SELECT 1 FROM players WHERE id = ?", (user_id,))
        return await cur.fetchone() is not None


async def db_team_taken(team_name: str, exclude_id: Optional[int] = None) -> bool:
    async with db_cursor() as cur:
        if exclude_id:
            await cur.execute(
                "SELECT 1 FROM players WHERE team_name = ? AND id != ?",
                (team_name, exclude_id),
            )
        else:
            await cur.execute(
                "SELECT 1 FROM players WHERE team_name = ?", (team_name,)
            )
        return await cur.fetchone() is not None


async def db_create_player(
    user_id: int, username: str, full_name: str, team_name: str, team_flag: str
) -> Player:
    async with db_cursor() as cur:
        await cur.execute(
            """INSERT OR IGNORE INTO players
               (id, username, full_name, team_name, team_flag, registered_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, username, full_name, team_name, team_flag, time.time()),
        )
        await cur.execute(
            """INSERT OR IGNORE INTO statistics (player_id) VALUES (?)""",
            (user_id,),
        )
        await cur.execute(
            """INSERT OR IGNORE INTO league
               (player_id, team_name, team_flag, full_name)
               VALUES (?, ?, ?, ?)""",
            (user_id, team_name, team_flag, full_name),
        )
    player = await db_get_player(user_id)
    return player  # type: ignore


async def db_update_player_stats(
    player_id: int,
    *,
    wins: int = 0,
    losses: int = 0,
    draws: int = 0,
    goals_scored: int = 0,
    goals_missed: int = 0,
    saves_made: int = 0,
    streak_reset: bool = False,
) -> None:
    async with db_cursor() as cur:
        await cur.execute(
            """UPDATE players SET
               matches_played = matches_played + 1,
               wins           = wins           + ?,
               losses         = losses         + ?,
               draws          = draws          + ?,
               goals_scored   = goals_scored   + ?,
               goals_missed   = goals_missed   + ?,
               saves_made     = saves_made     + ?,
               current_streak = CASE WHEN ? THEN 0 ELSE current_streak + ? END,
               win_streak     = MAX(win_streak, CASE WHEN ? THEN current_streak + ? ELSE win_streak END)
               WHERE id = ?""",
            (
                wins, losses, draws, goals_scored, goals_missed, saves_made,
                streak_reset, wins,
                wins, wins,
                player_id,
            ),
        )


async def db_delete_player(player_id: int) -> None:
    async with db_cursor() as cur:
        await cur.execute("UPDATE players SET is_active = 0 WHERE id = ?", (player_id,))


def _dict_to_player(d: Dict[str, Any]) -> Player:
    return Player(
        id=d["id"],
        username=d.get("username", ""),
        full_name=d.get("full_name", ""),
        team_name=d.get("team_name", ""),
        team_flag=d.get("team_flag", ""),
        matches_played=d.get("matches_played", 0),
        wins=d.get("wins", 0),
        losses=d.get("losses", 0),
        draws=d.get("draws", 0),
        goals_scored=d.get("goals_scored", 0),
        goals_missed=d.get("goals_missed", 0),
        saves_made=d.get("saves_made", 0),
        win_streak=d.get("win_streak", 0),
        current_streak=d.get("current_streak", 0),
        registered_at=d.get("registered_at", 0.0),
        is_active=bool(d.get("is_active", 1)),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN QUERIES
# ═══════════════════════════════════════════════════════════════════════════════

async def db_get_admin(user_id: int) -> Optional[Admin]:
    async with db_cursor() as cur:
        await cur.execute("SELECT * FROM admins WHERE id = ?", (user_id,))
        row = _row_to_dict(await cur.fetchone())
    if not row:
        return None
    return Admin(
        id=row["id"],
        username=row.get("username", ""),
        full_name=row.get("full_name", ""),
        added_at=row.get("added_at", 0.0),
        is_super=bool(row.get("is_super", 0)),
    )


async def db_get_all_admins() -> List[Admin]:
    async with db_cursor() as cur:
        await cur.execute("SELECT * FROM admins")
        rows = await cur.fetchall()
    return [
        Admin(
            id=r["id"],
            username=r["username"],
            full_name=r["full_name"],
            added_at=r["added_at"],
            is_super=bool(r["is_super"]),
        )
        for r in rows
    ]


async def db_add_admin(user_id: int, username: str, full_name: str, is_super: bool = False) -> None:
    async with db_cursor() as cur:
        await cur.execute(
            """INSERT OR REPLACE INTO admins (id, username, full_name, is_super, added_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, username, full_name, int(is_super), time.time()),
        )


async def db_remove_admin(user_id: int) -> None:
    async with db_cursor() as cur:
        await cur.execute("DELETE FROM admins WHERE id = ?", (user_id,))


# ═══════════════════════════════════════════════════════════════════════════════
# MATCH QUERIES
# ═══════════════════════════════════════════════════════════════════════════════

async def db_create_match(
    player1_id: int,
    player2_id: int,
    player1_team: str,
    player2_team: str,
    player1_flag: str,
    player2_flag: str,
    channel_id: str,
    max_rounds: int = 5,
) -> int:
    """Create a new match and return its ID."""
    async with db_cursor() as cur:
        await cur.execute(
            """INSERT INTO matches
               (player1_id, player2_id, player1_team, player2_team,
                player1_flag, player2_flag, channel_id, status, max_rounds, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
            (
                player1_id, player2_id, player1_team, player2_team,
                player1_flag, player2_flag, channel_id, max_rounds, time.time(),
            ),
        )
        return cur.lastrowid  # type: ignore


async def db_get_match(match_id: int) -> Optional[Match]:
    async with db_cursor() as cur:
        await cur.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
        row = _row_to_dict(await cur.fetchone())
    if not row:
        return None
    match = _dict_to_match(row)
    match.rounds = await db_get_rounds(match_id)
    return match


async def db_get_active_match_for_player(player_id: int) -> Optional[Match]:
    """Return the active match (if any) involving this player."""
    async with db_cursor() as cur:
        await cur.execute(
            """SELECT * FROM matches
               WHERE (player1_id = ? OR player2_id = ?)
               AND status IN ('pending','rps','in_progress','sudden_death')
               ORDER BY created_at DESC LIMIT 1""",
            (player_id, player_id),
        )
        row = _row_to_dict(await cur.fetchone())
    if not row:
        return None
    match = _dict_to_match(row)
    match.rounds = await db_get_rounds(match.id)
    return match


async def db_get_all_matches(limit: int = 20, offset: int = 0) -> List[Match]:
    async with db_cursor() as cur:
        await cur.execute(
            "SELECT * FROM matches ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cur.fetchall()
    result = []
    for row in rows:
        m = _dict_to_match(dict(row))
        m.rounds = await db_get_rounds(m.id)
        result.append(m)
    return result


async def db_get_finished_matches_for_player(player_id: int) -> List[Match]:
    async with db_cursor() as cur:
        await cur.execute(
            """SELECT * FROM matches
               WHERE (player1_id = ? OR player2_id = ?)
               AND status = 'finished'
               ORDER BY finished_at DESC LIMIT 10""",
            (player_id, player_id),
        )
        rows = await cur.fetchall()
    result = []
    for row in rows:
        m = _dict_to_match(dict(row))
        m.rounds = await db_get_rounds(m.id)
        result.append(m)
    return result


async def db_update_match(match_id: int, **kwargs: Any) -> None:
    """Generic match updater — pass column=value keyword args."""
    if not kwargs:
        return
    columns = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [match_id]
    async with db_cursor() as cur:
        await cur.execute(
            f"UPDATE matches SET {columns} WHERE id = ?", values
        )


async def db_cancel_match(match_id: int) -> None:
    await db_update_match(match_id, status="cancelled", finished_at=time.time())


def _dict_to_match(d: Dict[str, Any]) -> Match:
    return Match(
        id=d["id"],
        player1_id=d["player1_id"],
        player2_id=d["player2_id"],
        player1_team=d["player1_team"],
        player2_team=d["player2_team"],
        player1_flag=d["player1_flag"],
        player2_flag=d["player2_flag"],
        channel_id=d.get("channel_id", ""),
        status=MatchStatus(d.get("status", "pending")),
        max_rounds=d.get("max_rounds", 5),
        player1_rps=RPSChoice(d["player1_rps"]) if d.get("player1_rps") else None,
        player2_rps=RPSChoice(d["player2_rps"]) if d.get("player2_rps") else None,
        rps_winner_id=d.get("rps_winner_id"),
        current_round=d.get("current_round", 0),
        player1_score=d.get("player1_score", 0),
        player2_score=d.get("player2_score", 0),
        winner_id=d.get("winner_id"),
        channel_message_id=d.get("channel_message_id"),
        player1_message_id=d.get("player1_message_id"),
        player2_message_id=d.get("player2_message_id"),
        created_at=d.get("created_at", 0.0),
        started_at=d.get("started_at"),
        finished_at=d.get("finished_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ROUND QUERIES
# ═══════════════════════════════════════════════════════════════════════════════

async def db_get_rounds(match_id: int) -> List[Round]:
    async with db_cursor() as cur:
        await cur.execute(
            "SELECT * FROM rounds WHERE match_id = ? ORDER BY round_number",
            (match_id,),
        )
        rows = await cur.fetchall()
    return [_dict_to_round(dict(r)) for r in rows]


async def db_get_current_round(match_id: int, round_number: int) -> Optional[Round]:
    async with db_cursor() as cur:
        await cur.execute(
            "SELECT * FROM rounds WHERE match_id = ? AND round_number = ?",
            (match_id, round_number),
        )
        row = _row_to_dict(await cur.fetchone())
    return _dict_to_round(row) if row else None


async def db_create_round(
    match_id: int,
    round_number: int,
    shooter_id: int,
    goalkeeper_id: int,
    is_sudden_death: bool = False,
) -> None:
    async with db_cursor() as cur:
        await cur.execute(
            """INSERT OR IGNORE INTO rounds
               (match_id, round_number, shooter_id, goalkeeper_id, is_sudden_death)
               VALUES (?, ?, ?, ?, ?)""",
            (match_id, round_number, shooter_id, goalkeeper_id, int(is_sudden_death)),
        )


async def db_set_shooter_direction(
    match_id: int, round_number: int, direction: Direction
) -> None:
    async with db_cursor() as cur:
        await cur.execute(
            """UPDATE rounds SET shooter_direction = ?
               WHERE match_id = ? AND round_number = ?""",
            (direction.value, match_id, round_number),
        )


async def db_set_goalkeeper_direction(
    match_id: int, round_number: int, direction: Direction
) -> None:
    async with db_cursor() as cur:
        await cur.execute(
            """UPDATE rounds SET goalkeeper_direction = ?
               WHERE match_id = ? AND round_number = ?""",
            (direction.value, match_id, round_number),
        )


async def db_complete_round(
    match_id: int, round_number: int, result: RoundResult
) -> None:
    async with db_cursor() as cur:
        await cur.execute(
            """UPDATE rounds SET result = ?, completed_at = ?
               WHERE match_id = ? AND round_number = ?""",
            (result.value, time.time(), match_id, round_number),
        )


def _dict_to_round(d: Dict[str, Any]) -> Round:
    return Round(
        round_number=d["round_number"],
        shooter_id=d["shooter_id"],
        goalkeeper_id=d["goalkeeper_id"],
        shooter_direction=Direction(d["shooter_direction"]) if d.get("shooter_direction") else None,
        goalkeeper_direction=Direction(d["goalkeeper_direction"]) if d.get("goalkeeper_direction") else None,
        result=RoundResult(d.get("result", "pending")),
        is_sudden_death=bool(d.get("is_sudden_death", 0)),
        completed_at=d.get("completed_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# LEAGUE QUERIES
# ═══════════════════════════════════════════════════════════════════════════════

async def db_get_league_table() -> List[LeagueEntry]:
    async with db_cursor() as cur:
        await cur.execute(
            """SELECT l.*, p.full_name as p_full_name FROM league l
               JOIN players p ON l.player_id = p.id
               WHERE p.is_active = 1
               ORDER BY points DESC, (goals_for - goals_against) DESC, goals_for DESC"""
        )
        rows = await cur.fetchall()
    return [
        LeagueEntry(
            player_id=r["player_id"],
            team_name=r["team_name"],
            team_flag=r["team_flag"],
            full_name=r["full_name"],
            played=r["played"],
            wins=r["wins"],
            draws=r["draws"],
            losses=r["losses"],
            goals_for=r["goals_for"],
            goals_against=r["goals_against"],
            points=r["points"],
        )
        for r in rows
    ]


async def db_update_league(
    player_id: int,
    *,
    win: bool = False,
    draw: bool = False,
    loss: bool = False,
    goals_for: int = 0,
    goals_against: int = 0,
) -> None:
    points_delta = 3 if win else (1 if draw else 0)
    async with db_cursor() as cur:
        await cur.execute(
            """UPDATE league SET
               played        = played + 1,
               wins          = wins + ?,
               draws         = draws + ?,
               losses        = losses + ?,
               goals_for     = goals_for + ?,
               goals_against = goals_against + ?,
               points        = points + ?
               WHERE player_id = ?""",
            (
                int(win), int(draw), int(loss),
                goals_for, goals_against, points_delta,
                player_id,
            ),
        )


async def db_sync_league_player_info(player_id: int) -> None:
    """Keep league table in sync with player's team info."""
    player = await db_get_player(player_id)
    if not player:
        return
    async with db_cursor() as cur:
        await cur.execute(
            """INSERT INTO league (player_id, team_name, team_flag, full_name)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(player_id) DO UPDATE SET
               team_name = excluded.team_name,
               team_flag = excluded.team_flag,
               full_name = excluded.full_name""",
            (player_id, player.team_name, player.team_flag, player.full_name),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# STATISTICS QUERIES
# ═══════════════════════════════════════════════════════════════════════════════

async def db_get_statistics(player_id: int) -> Optional[Statistics]:
    async with db_cursor() as cur:
        await cur.execute("SELECT * FROM statistics WHERE player_id = ?", (player_id,))
        row = _row_to_dict(await cur.fetchone())
    if not row:
        return None
    return Statistics(
        player_id=row["player_id"],
        total_matches=row.get("total_matches", 0),
        total_wins=row.get("total_wins", 0),
        total_losses=row.get("total_losses", 0),
        total_draws=row.get("total_draws", 0),
        total_goals_scored=row.get("total_goals_scored", 0),
        total_goals_conceded=row.get("total_goals_conceded", 0),
        total_saves=row.get("total_saves", 0),
        total_shots=row.get("total_shots", 0),
        best_win_streak=row.get("best_win_streak", 0),
        current_win_streak=row.get("current_win_streak", 0),
        last_match_result=row.get("last_match_result"),
    )


async def db_update_statistics(
    player_id: int,
    *,
    win: bool = False,
    loss: bool = False,
    draw: bool = False,
    goals_scored: int = 0,
    goals_conceded: int = 0,
    saves: int = 0,
    shots: int = 0,
) -> None:
    result_str = "win" if win else ("loss" if loss else "draw")
    async with db_cursor() as cur:
        await cur.execute(
            """INSERT INTO statistics (player_id) VALUES (?) ON CONFLICT DO NOTHING""",
            (player_id,),
        )
        await cur.execute(
            """UPDATE statistics SET
               total_matches        = total_matches + 1,
               total_wins           = total_wins + ?,
               total_losses         = total_losses + ?,
               total_draws          = total_draws + ?,
               total_goals_scored   = total_goals_scored + ?,
               total_goals_conceded = total_goals_conceded + ?,
               total_saves          = total_saves + ?,
               total_shots          = total_shots + ?,
               current_win_streak   = CASE WHEN ? THEN current_win_streak + 1 ELSE 0 END,
               best_win_streak      = MAX(best_win_streak,
                                         CASE WHEN ? THEN current_win_streak + 1
                                              ELSE best_win_streak END),
               last_match_result    = ?
               WHERE player_id = ?""",
            (
                int(win), int(loss), int(draw),
                goals_scored, goals_conceded, saves, shots,
                int(win), int(win),
                result_str,
                player_id,
            ),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS QUERIES
# ═══════════════════════════════════════════════════════════════════════════════

async def db_get_setting(key: str, default: str = "") -> str:
    async with db_cursor() as cur:
        await cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cur.fetchone()
    return row["value"] if row else default


async def db_set_setting(key: str, value: str) -> None:
    async with db_cursor() as cur:
        await cur.execute(
            """INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
            (key, value, time.time()),
        )


async def db_get_all_settings() -> List[Setting]:
    async with db_cursor() as cur:
        await cur.execute("SELECT * FROM settings")
        rows = await cur.fetchall()
    return [
        Setting(key=r["key"], value=r["value"], updated_at=r["updated_at"])
        for r in rows
    ]
