"""
Core Match Engine for Penalty League Mobin.

Orchestrates the full match lifecycle:
  1. Match creation
  2. RPS phase
  3. Round-by-round penalty flow
  4. Sudden death
  5. Match conclusion & stat updates

All database writes happen here. Channel/player notifications
are delegated to channel_service.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Optional, Tuple

from aiogram import Bot

from telegram_bot.config import config
from telegram_bot.database import (
    db_cancel_match,
    db_complete_round,
    db_create_match,
    db_create_round,
    db_get_active_match_for_player,
    db_get_current_round,
    db_get_match,
    db_get_player,
    db_get_setting,
    db_set_goalkeeper_direction,
    db_set_shooter_direction,
    db_update_match,
    db_update_player_stats,
    db_update_statistics,
)
from telegram_bot.models import (
    Direction,
    Match,
    MatchStatus,
    RPSChoice,
    RPSResult,
    RoundResult,
    evaluate_rps,
)
from telegram_bot.services import channel_service
from telegram_bot.services.league_service import update_league_after_match
from telegram_bot.utils import keyboards, texts

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# In-memory lock store to prevent race conditions
# key: match_id, value: asyncio.Lock
# ─────────────────────────────────────────────────────────────────────────────
_match_locks: Dict[int, asyncio.Lock] = {}


def _get_lock(match_id: int) -> asyncio.Lock:
    if match_id not in _match_locks:
        _match_locks[match_id] = asyncio.Lock()
    return _match_locks[match_id]


def _cleanup_lock(match_id: int) -> None:
    _match_locks.pop(match_id, None)


# ═══════════════════════════════════════════════════════════════════════════════
# MATCH CREATION
# ═══════════════════════════════════════════════════════════════════════════════

async def create_match(
    bot: Bot,
    player1_id: int,
    player2_id: int,
    channel_id: str,
) -> Tuple[bool, str, Optional[int]]:
    """
    Create a new match between two players.
    Returns (success, error_msg, match_id).
    """
    # Validate players are not already in a match
    p1_match = await db_get_active_match_for_player(player1_id)
    p2_match = await db_get_active_match_for_player(player2_id)
    if p1_match or p2_match:
        return False, "player_busy", None

    p1 = await db_get_player(player1_id)
    p2 = await db_get_player(player2_id)
    if not p1 or not p2:
        return False, "player_not_found", None

    max_rounds = int(await db_get_setting("max_rounds", str(config.default_rounds)))

    match_id = await db_create_match(
        player1_id=p1.id,
        player2_id=p2.id,
        player1_team=p1.team_name,
        player2_team=p2.team_name,
        player1_flag=p1.team_flag,
        player2_flag=p2.team_flag,
        channel_id=channel_id or config.channel_id,
        max_rounds=max_rounds,
    )

    # Update status to RPS and announce
    await db_update_match(match_id, status=MatchStatus.RPS.value, started_at=time.time())
    match = await db_get_match(match_id)

    # Publish to channel
    ch_msg_id = await channel_service.publish_match_start(bot, match)
    if ch_msg_id:
        await db_update_match(match_id, channel_message_id=ch_msg_id)

    # Notify both players
    timeout = int(await db_get_setting("rps_timeout", "60"))
    rps_kb = keyboards.rps_keyboard(match_id)

    p1_msg_id = await channel_service.notify_player(
        bot, p1.id,
        texts.MATCH_INVITE.format(
            p1_flag=p1.team_flag, p1_team=p1.team_name,
            p2_flag=p2.team_flag, p2_team=p2.team_name,
        ),
        reply_markup=None,
    )
    await channel_service.notify_player(
        bot, p1.id,
        texts.RPS_CHOOSE.format(opp_flag=p2.team_flag, opp_team=p2.team_name),
        reply_markup=rps_kb,
    )

    p2_msg_id = await channel_service.notify_player(
        bot, p2.id,
        texts.MATCH_INVITE.format(
            p1_flag=p1.team_flag, p1_team=p1.team_name,
            p2_flag=p2.team_flag, p2_team=p2.team_name,
        ),
        reply_markup=None,
    )
    await channel_service.notify_player(
        bot, p2.id,
        texts.RPS_CHOOSE.format(opp_flag=p1.team_flag, opp_team=p1.team_name),
        reply_markup=rps_kb,
    )

    logger.info("Match %d created: P1=%d vs P2=%d", match_id, player1_id, player2_id)

    # Schedule RPS timeout
    asyncio.create_task(_rps_timeout(bot, match_id, timeout))

    return True, "success", match_id


# ═══════════════════════════════════════════════════════════════════════════════
# RPS PHASE
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_rps_choice(
    bot: Bot,
    match_id: int,
    player_id: int,
    choice: RPSChoice,
) -> Tuple[bool, str]:
    """
    Record a player's RPS choice.
    If both have chosen, resolve and start rounds.
    Returns (processed, message).
    """
    async with _get_lock(match_id):
        match = await db_get_match(match_id)
        if not match:
            return False, "match_not_found"
        if match.status != MatchStatus.RPS:
            return False, "wrong_status"

        is_p1 = player_id == match.player1_id
        is_p2 = player_id == match.player2_id
        if not is_p1 and not is_p2:
            return False, "not_in_match"

        # Check if already chose
        if is_p1 and match.player1_rps:
            return False, "already_chose"
        if is_p2 and match.player2_rps:
            return False, "already_chose"

        # Save choice
        field = "player1_rps" if is_p1 else "player2_rps"
        await db_update_match(match_id, **{field: choice.value})

        # Re-fetch
        match = await db_get_match(match_id)

        # Wait if opponent hasn't chosen yet
        if not match.player1_rps or not match.player2_rps:
            return True, "waiting"

        # Both chose — resolve
        result = evaluate_rps(
            RPSChoice(match.player1_rps),
            RPSChoice(match.player2_rps),
        )

        if result == RPSResult.DRAW:
            # Clear and ask again
            await db_update_match(match_id, player1_rps=None, player2_rps=None)
            rps_kb = keyboards.rps_keyboard(match_id)
            p1 = await db_get_player(match.player1_id)
            p2 = await db_get_player(match.player2_id)
            await channel_service.notify_player(bot, p1.id, texts.RPS_DRAW, reply_markup=rps_kb)
            await channel_service.notify_player(bot, p2.id, texts.RPS_DRAW, reply_markup=rps_kb)
            return True, "draw_retry"

        # Determine winner
        if result == RPSResult.PLAYER1_WINS:
            winner_id = match.player1_id
            loser_id = match.player2_id
        else:
            winner_id = match.player2_id
            loser_id = match.player1_id

        await db_update_match(
            match_id,
            rps_winner_id=winner_id,
            status=MatchStatus.IN_PROGRESS.value,
            current_round=1,
        )

        match = await db_get_match(match_id)
        winner = await db_get_player(winner_id)
        loser = await db_get_player(loser_id)

        # RPS choice labels
        def choice_label(c: RPSChoice) -> str:
            return {
                RPSChoice.ROCK: "🪨 سنگ",
                RPSChoice.PAPER: "📄 کاغذ",
                RPSChoice.SCISSORS: "✂️ قیچی",
            }[c]

        w_choice = choice_label(RPSChoice(match.player1_rps if winner_id == match.player1_id else match.player2_rps))
        l_choice = choice_label(RPSChoice(match.player2_rps if winner_id == match.player1_id else match.player1_rps))

        # Notify players
        await channel_service.notify_player(
            bot, winner_id,
            texts.RPS_YOU_WIN.format(your_choice=w_choice, opp_choice=l_choice),
        )
        await channel_service.notify_player(
            bot, loser_id,
            texts.RPS_YOU_LOSE.format(opp_choice=w_choice, your_choice=l_choice),
        )

        # Publish to channel
        await channel_service.publish_rps_result(
            bot, match,
            winner_flag=winner.team_flag,
            winner_team=winner.team_name,
            winner_name=winner.full_name,
        )

        # Start Round 1
        await _start_round(bot, match)
        return True, "resolved"


async def _rps_timeout(bot: Bot, match_id: int, timeout: int) -> None:
    """Cancel a match if RPS isn't resolved within timeout seconds."""
    await asyncio.sleep(timeout)
    match = await db_get_match(match_id)
    if not match or match.status != MatchStatus.RPS:
        return
    logger.warning("RPS timeout for match %d. Cancelling.", match_id)
    await _force_cancel(bot, match, reason="rps_timeout")


# ═══════════════════════════════════════════════════════════════════════════════
# ROUND FLOW
# ═══════════════════════════════════════════════════════════════════════════════

async def _start_round(bot: Bot, match: Match) -> None:
    """
    Initialize a new round: create DB record, determine roles, notify players.
    """
    round_num = match.current_round
    is_sd = match.status == MatchStatus.SUDDEN_DEATH

    # Determine shooter and goalkeeper
    if match.rps_winner_id is None:
        return

    # Shooter alternates: winner shoots odd rounds, loser shoots even
    if round_num % 2 == 1:
        shooter_id = match.rps_winner_id
        gk_id = match.player2_id if shooter_id == match.player1_id else match.player1_id
    else:
        gk_id = match.rps_winner_id
        shooter_id = match.player2_id if gk_id == match.player1_id else match.player1_id

    await db_create_round(match.match_id if hasattr(match, 'match_id') else match.id,
                          round_num, shooter_id, gk_id, is_sd)

    shooter = await db_get_player(shooter_id)
    gk = await db_get_player(gk_id)

    if not shooter or not gk:
        return

    # Publish round start to channel
    await channel_service.publish_round_start(
        bot, match, round_num,
        shooter_flag=shooter.team_flag,
        shooter_team=shooter.team_name,
        gk_flag=gk.team_flag,
        gk_team=gk.team_name,
    )

    # Refresh match for form display
    match = await db_get_match(match.id)
    p1_form = match.get_form(match.player1_id)
    p2_form = match.get_form(match.player2_id)

    # Notify shooter
    shoot_kb = keyboards.direction_keyboard(match.id, "shoot")
    await channel_service.notify_player(
        bot, shooter_id,
        texts.SHOOTER_TURN.format(
            round_num=round_num,
            gk_flag=gk.team_flag,
            gk_team=gk.team_name,
            p1_flag=match.player1_flag,
            p1_team=match.player1_team,
            p1_form=p1_form,
            p2_flag=match.player2_flag,
            p2_team=match.player2_team,
            p2_form=p2_form,
        ),
        reply_markup=shoot_kb,
    )

    # Notify goalkeeper
    gk_kb = keyboards.direction_keyboard(match.id, "save")
    await channel_service.notify_player(
        bot, gk_id,
        texts.GOALKEEPER_TURN.format(
            round_num=round_num,
            shooter_flag=shooter.team_flag,
            shooter_team=shooter.team_name,
            p1_flag=match.player1_flag,
            p1_team=match.player1_team,
            p1_form=p1_form,
            p2_flag=match.player2_flag,
            p2_team=match.player2_team,
            p2_form=p2_form,
        ),
        reply_markup=gk_kb,
    )

    # Schedule round timeout
    timeout = int(await db_get_setting("round_timeout", "60"))
    asyncio.create_task(_round_timeout(bot, match.id, round_num, timeout))

    logger.info("Round %d started in match %d: shooter=%d, gk=%d",
                round_num, match.id, shooter_id, gk_id)


async def handle_direction_choice(
    bot: Bot,
    match_id: int,
    player_id: int,
    direction: Direction,
    role: str,  # "shoot" or "save"
) -> Tuple[bool, str]:
    """
    Record a player's direction choice for the current round.
    If both have chosen, resolve the round.
    """
    async with _get_lock(match_id):
        match = await db_get_match(match_id)
        if not match:
            return False, "match_not_found"

        if match.status not in (MatchStatus.IN_PROGRESS, MatchStatus.SUDDEN_DEATH):
            return False, "wrong_status"

        round_num = match.current_round
        rnd = await db_get_current_round(match_id, round_num)
        if not rnd:
            return False, "round_not_found"

        # Anti-cheat: verify role matches actual role
        if role == "shoot":
            if player_id != rnd.shooter_id:
                return False, "wrong_role"
            if rnd.shooter_direction is not None:
                return False, "already_chose"
            await db_set_shooter_direction(match_id, round_num, direction)
        elif role == "save":
            if player_id != rnd.goalkeeper_id:
                return False, "wrong_role"
            if rnd.goalkeeper_direction is not None:
                return False, "already_chose"
            await db_set_goalkeeper_direction(match_id, round_num, direction)
        else:
            return False, "invalid_role"

        # Notify waiting
        await channel_service.notify_player(bot, player_id, texts.WAITING_FOR_OPPONENT)

        # Re-fetch round
        rnd = await db_get_current_round(match_id, round_num)
        if not rnd or not rnd.is_complete:
            return True, "waiting"

        # Both chose — evaluate
        await _resolve_round(bot, match_id, round_num)
        return True, "resolved"


async def _resolve_round(bot: Bot, match_id: int, round_num: int) -> None:
    """Evaluate a completed round, update scores, and proceed."""
    rnd = await db_get_current_round(match_id, round_num)
    if not rnd:
        return

    result = rnd.evaluate()
    await db_complete_round(match_id, round_num, result)

    match = await db_get_match(match_id)
    if not match:
        return

    # Update score
    if result == RoundResult.GOAL:
        if rnd.shooter_id == match.player1_id:
            new_p1 = match.player1_score + 1
            new_p2 = match.player2_score
        else:
            new_p1 = match.player1_score
            new_p2 = match.player2_score + 1
        await db_update_match(match_id, player1_score=new_p1, player2_score=new_p2)
    else:
        new_p1 = match.player1_score
        new_p2 = match.player2_score

    match = await db_get_match(match_id)

    shooter = await db_get_player(rnd.shooter_id)
    gk = await db_get_player(rnd.goalkeeper_id)
    p1_form = match.get_form(match.player1_id)
    p2_form = match.get_form(match.player2_id)

    # Notify players of round result
    dir_labels = {
        Direction.LEFT: "⬅️ چپ",
        Direction.CENTER: "⬆️ وسط",
        Direction.RIGHT: "➡️ راست",
    }

    if result == RoundResult.GOAL:
        await channel_service.notify_player(
            bot, rnd.shooter_id,
            texts.ROUND_RESULT_GOAL_SHOOTER.format(
                your_dir=dir_labels[rnd.shooter_direction],
                opp_dir=dir_labels[rnd.goalkeeper_direction],
            ),
        )
        await channel_service.notify_player(
            bot, rnd.goalkeeper_id,
            texts.ROUND_RESULT_GOAL_GK.format(
                opp_dir=dir_labels[rnd.shooter_direction],
                your_dir=dir_labels[rnd.goalkeeper_direction],
            ),
        )
    else:
        await channel_service.notify_player(
            bot, rnd.shooter_id,
            texts.ROUND_RESULT_SAVE_SHOOTER.format(
                your_dir=dir_labels[rnd.shooter_direction],
                opp_dir=dir_labels[rnd.goalkeeper_direction],
            ),
        )
        await channel_service.notify_player(
            bot, rnd.goalkeeper_id,
            texts.ROUND_RESULT_SAVE_GK.format(
                opp_dir=dir_labels[rnd.shooter_direction],
                your_dir=dir_labels[rnd.goalkeeper_direction],
            ),
        )

    # Publish round result to channel
    if shooter and gk:
        await channel_service.publish_round_result(
            bot, match, result,
            shooter_flag=shooter.team_flag,
            shooter_team=shooter.team_name,
            gk_flag=gk.team_flag,
            gk_team=gk.team_name,
            p1_form=p1_form,
            p2_form=p2_form,
        )

    # Check for early win
    remaining = match.max_rounds - round_num
    p1_s = match.player1_score
    p2_s = match.player2_score

    if match.status == MatchStatus.IN_PROGRESS:
        if p1_s > p2_s + remaining:
            await _finish_match(bot, match_id, winner_id=match.player1_id)
            return
        if p2_s > p1_s + remaining:
            await _finish_match(bot, match_id, winner_id=match.player2_id)
            return

    # Check if all normal rounds done
    if match.status == MatchStatus.IN_PROGRESS and round_num >= match.max_rounds:
        if p1_s != p2_s:
            winner = match.player1_id if p1_s > p2_s else match.player2_id
            await _finish_match(bot, match_id, winner_id=winner)
        else:
            # Tie — start sudden death
            await _start_sudden_death(bot, match_id)
        return

    # Sudden death resolution
    if match.status == MatchStatus.SUDDEN_DEATH:
        # In SD, rounds come in pairs (both players shoot once per SD round)
        # Check after every 2 sub-rounds if there's a winner
        sd_base = match.max_rounds
        sd_rounds_done = round_num - sd_base
        if sd_rounds_done > 0 and sd_rounds_done % 2 == 0:
            if p1_s != p2_s:
                winner = match.player1_id if p1_s > p2_s else match.player2_id
                await _finish_match(bot, match_id, winner_id=winner)
                return

    # Continue to next round
    next_round = round_num + 1
    await db_update_match(match_id, current_round=next_round)
    match = await db_get_match(match_id)
    await _start_round(bot, match)


async def _start_sudden_death(bot: Bot, match_id: int) -> None:
    match = await db_get_match(match_id)
    if not match:
        return

    await db_update_match(match_id, status=MatchStatus.SUDDEN_DEATH.value)
    match = await db_get_match(match_id)

    # Notify players
    await channel_service.notify_player(bot, match.player1_id, texts.SUDDEN_DEATH_NOTIFY)
    await channel_service.notify_player(bot, match.player2_id, texts.SUDDEN_DEATH_NOTIFY)

    # Publish to channel
    await channel_service.publish_sudden_death(bot, match)

    # Continue next round
    next_round = match.current_round + 1
    await db_update_match(match_id, current_round=next_round)
    match = await db_get_match(match_id)
    await _start_round(bot, match)

    logger.info("Sudden Death started for match %d", match_id)


async def _round_timeout(bot: Bot, match_id: int, round_num: int, timeout: int) -> None:
    """Cancel match if round isn't resolved in time."""
    await asyncio.sleep(timeout)
    match = await db_get_match(match_id)
    if not match or match.status not in (MatchStatus.IN_PROGRESS, MatchStatus.SUDDEN_DEATH):
        return
    if match.current_round != round_num:
        return  # Round already moved on

    rnd = await db_get_current_round(match_id, round_num)
    if not rnd or rnd.is_complete:
        return

    logger.warning("Round %d timeout in match %d", round_num, match_id)

    # Determine who didn't respond and give win to other player
    if rnd.shooter_direction is None:
        winner_id = rnd.goalkeeper_id
    else:
        winner_id = rnd.shooter_id

    timed_out_id = rnd.shooter_id if winner_id == rnd.goalkeeper_id else rnd.goalkeeper_id

    await channel_service.notify_player(bot, timed_out_id, texts.ROUND_TIMEOUT)
    await _finish_match(bot, match_id, winner_id=winner_id)


# ═══════════════════════════════════════════════════════════════════════════════
# MATCH CONCLUSION
# ═══════════════════════════════════════════════════════════════════════════════

async def _finish_match(
    bot: Bot,
    match_id: int,
    winner_id: Optional[int] = None,
) -> None:
    """
    Conclude the match: update DB, update stats, publish to channel.
    """
    match = await db_get_match(match_id)
    if not match or match.status == MatchStatus.FINISHED:
        return

    await db_update_match(
        match_id,
        status=MatchStatus.FINISHED.value,
        winner_id=winner_id,
        finished_at=time.time(),
    )

    match = await db_get_match(match_id)
    p1 = await db_get_player(match.player1_id)
    p2 = await db_get_player(match.player2_id)

    if not p1 or not p2:
        return

    # Determine per-player stats
    p1_won = winner_id == match.player1_id
    p2_won = winner_id == match.player2_id
    is_draw = winner_id is None

    # Count goals and saves from rounds
    p1_goals = p1_saves = p2_goals = p2_saves = 0
    for r in match.rounds:
        if r.result == RoundResult.PENDING:
            continue
        if r.shooter_id == match.player1_id:
            if r.result == RoundResult.GOAL:
                p1_goals += 1
            else:
                p2_saves += 1
        else:
            if r.result == RoundResult.GOAL:
                p2_goals += 1
            else:
                p1_saves += 1

    # Update player stats
    await db_update_player_stats(
        match.player1_id,
        wins=1 if p1_won else 0,
        losses=1 if p2_won else 0,
        draws=1 if is_draw else 0,
        goals_scored=p1_goals,
        goals_missed=p2_goals,
        saves_made=p1_saves,
        streak_reset=not p1_won,
    )
    await db_update_player_stats(
        match.player2_id,
        wins=1 if p2_won else 0,
        losses=1 if p1_won else 0,
        draws=1 if is_draw else 0,
        goals_scored=p2_goals,
        goals_missed=p1_goals,
        saves_made=p2_saves,
        streak_reset=not p2_won,
    )

    # Update statistics table
    await db_update_statistics(
        match.player1_id,
        win=p1_won, loss=p2_won, draw=is_draw,
        goals_scored=p1_goals, goals_conceded=p2_goals,
        saves=p1_saves, shots=len([r for r in match.rounds if r.shooter_id == match.player1_id]),
    )
    await db_update_statistics(
        match.player2_id,
        win=p2_won, loss=p1_won, draw=is_draw,
        goals_scored=p2_goals, goals_conceded=p1_goals,
        saves=p2_saves, shots=len([r for r in match.rounds if r.shooter_id == match.player2_id]),
    )

    # Update league
    await update_league_after_match(match)

    # Build forms
    p1_form = match.get_form(match.player1_id)
    p2_form = match.get_form(match.player2_id)

    # Notify winner/loser personally
    if winner_id:
        loser_id = match.player2_id if winner_id == match.player1_id else match.player1_id
        winner = p1 if winner_id == match.player1_id else p2
        loser = p2 if winner_id == match.player1_id else p1
        w_score = match.player1_score if winner_id == match.player1_id else match.player2_score
        l_score = match.player2_score if winner_id == match.player1_id else match.player1_score

        await channel_service.notify_player(
            bot, winner_id,
            texts.MATCH_YOU_WIN.format(
                your_flag=winner.team_flag, your_team=winner.team_name,
                your_score=w_score, opp_score=l_score,
                opp_flag=loser.team_flag, opp_team=loser.team_name,
                goals=p1_goals if winner_id == match.player1_id else p2_goals,
                saves=p1_saves if winner_id == match.player1_id else p2_saves,
            ),
        )
        await channel_service.notify_player(
            bot, loser_id,
            texts.MATCH_YOU_LOSE.format(
                your_flag=loser.team_flag, your_team=loser.team_name,
                your_score=l_score, opp_score=w_score,
                opp_flag=winner.team_flag, opp_team=winner.team_name,
                goals=p2_goals if winner_id == match.player1_id else p1_goals,
                saves=p2_saves if winner_id == match.player1_id else p1_saves,
            ),
        )

        winner_flag = winner.team_flag
        winner_team = winner.team_name
        winner_name = winner.full_name
    else:
        # Draw
        score = match.player1_score
        for pid in (match.player1_id, match.player2_id):
            player = p1 if pid == match.player1_id else p2
            opp = p2 if pid == match.player1_id else p1
            await channel_service.notify_player(
                bot, pid,
                texts.MATCH_DRAW_MSG.format(
                    your_flag=player.team_flag, your_team=player.team_name,
                    score=score,
                    opp_flag=opp.team_flag, opp_team=opp.team_name,
                ),
            )
        winner_flag = "🤝"
        winner_team = "مساوی"
        winner_name = "مساوی"

    # Publish to channel
    await channel_service.publish_match_end(
        bot, match,
        winner_flag=winner_flag,
        winner_team=winner_team,
        winner_name=winner_name,
        p1_form=p1_form,
        p2_form=p2_form,
    )

    _cleanup_lock(match_id)
    logger.info(
        "Match %d finished. Winner: %s. Score: %d-%d",
        match_id, winner_id, match.player1_score, match.player2_score,
    )


async def _force_cancel(bot: Bot, match: Match, reason: str = "admin") -> None:
    """Force-cancel a match."""
    if match.status == MatchStatus.FINISHED or match.status == MatchStatus.CANCELLED:
        return

    await db_cancel_match(match.id)

    # Notify players
    for pid in (match.player1_id, match.player2_id):
        await channel_service.notify_player(bot, pid, texts.MATCH_CANCELLED_PLAYER)

    await channel_service.publish_match_cancelled(bot, match)
    _cleanup_lock(match.id)
    logger.info("Match %d force-cancelled. Reason: %s", match.id, reason)


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC ADMIN ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def admin_cancel_match(bot: Bot, match_id: int) -> Tuple[bool, str]:
    """Admin-initiated match cancellation."""
    match = await db_get_match(match_id)
    if not match:
        return False, "not_found"
    if not match.is_active:
        return False, "not_active"
    await _force_cancel(bot, match, reason="admin")
    return True, "cancelled"


async def get_active_match(match_id: int) -> Optional[Match]:
    return await db_get_match(match_id)


async def get_player_active_match(player_id: int) -> Optional[Match]:
    return await db_get_active_match_for_player(player_id)
