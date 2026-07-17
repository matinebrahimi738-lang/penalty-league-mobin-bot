"""
Channel publishing service.
All Telegram channel messages go through this module.
The bot automatically posts every event to the configured channel.
"""

from __future__ import annotations

import logging
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from telegram_bot.config import config
from telegram_bot.models import Match, RoundResult
from telegram_bot.utils import texts

logger = logging.getLogger(__name__)


async def _safe_send(
    bot: Bot,
    chat_id: str,
    text: str,
    parse_mode: str = "HTML",
    reply_markup=None,
) -> Optional[int]:
    """Send a message; return message_id or None on failure."""
    if not chat_id:
        logger.warning("Channel ID not configured. Skipping channel message.")
        return None
    try:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        return msg.message_id
    except TelegramForbiddenError:
        logger.error("Bot is not a member of channel %s", chat_id)
    except TelegramBadRequest as e:
        logger.error("Bad request sending to channel %s: %s", chat_id, e)
    except Exception as e:
        logger.error("Unexpected error sending to channel %s: %s", chat_id, e)
    return None


async def _safe_edit(
    bot: Bot,
    chat_id: str,
    message_id: int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup=None,
) -> bool:
    """Edit an existing channel message."""
    if not chat_id or not message_id:
        return False
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        return True
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logger.error("Error editing channel message: %s", e)
    except Exception as e:
        logger.error("Unexpected error editing channel message: %s", e)
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC CHANNEL EVENTS
# ═══════════════════════════════════════════════════════════════════════════════

async def publish_match_start(bot: Bot, match: Match) -> Optional[int]:
    """Post the match announcement to the channel."""
    text = texts.CHANNEL_MATCH_START.format(
        p1_flag=match.player1_flag,
        p1_team=match.player1_team,
        p2_flag=match.player2_flag,
        p2_team=match.player2_team,
    )
    channel = match.channel_id or config.channel_id
    return await _safe_send(bot, channel, text)


async def publish_rps_result(
    bot: Bot,
    match: Match,
    winner_flag: str,
    winner_team: str,
    winner_name: str,
) -> Optional[int]:
    text = texts.CHANNEL_RPS_DONE.format(
        winner_flag=winner_flag,
        winner_team=winner_team,
        winner_name=winner_name,
    )
    channel = match.channel_id or config.channel_id
    return await _safe_send(bot, channel, text)


async def publish_round_start(
    bot: Bot,
    match: Match,
    round_num: int,
    shooter_flag: str,
    shooter_team: str,
    gk_flag: str,
    gk_team: str,
) -> Optional[int]:
    text = texts.CHANNEL_ROUND_START.format(
        round_num=round_num,
        shooter_flag=shooter_flag,
        shooter_team=shooter_team,
        gk_flag=gk_flag,
        gk_team=gk_team,
    )
    channel = match.channel_id or config.channel_id
    return await _safe_send(bot, channel, text)


async def publish_round_result(
    bot: Bot,
    match: Match,
    result: RoundResult,
    shooter_flag: str,
    shooter_team: str,
    gk_flag: str,
    gk_team: str,
    p1_form: str,
    p2_form: str,
) -> Optional[int]:
    if result == RoundResult.GOAL:
        text = texts.CHANNEL_GOAL.format(
            shooter_flag=shooter_flag,
            shooter_team=shooter_team,
            p1_flag=match.player1_flag,
            p1_team=match.player1_team,
            p1_form=p1_form,
            p2_flag=match.player2_flag,
            p2_team=match.player2_team,
            p2_form=p2_form,
            p1_score=match.player1_score,
            p2_score=match.player2_score,
        )
    else:
        text = texts.CHANNEL_SAVE.format(
            gk_flag=gk_flag,
            gk_team=gk_team,
            p1_flag=match.player1_flag,
            p1_team=match.player1_team,
            p1_form=p1_form,
            p2_flag=match.player2_flag,
            p2_team=match.player2_team,
            p2_form=p2_form,
            p1_score=match.player1_score,
            p2_score=match.player2_score,
        )
    channel = match.channel_id or config.channel_id
    return await _safe_send(bot, channel, text)


async def publish_sudden_death(bot: Bot, match: Match) -> Optional[int]:
    score = match.player1_score  # equal at this point
    text = texts.CHANNEL_SUDDEN_DEATH_START.format(
        p1_flag=match.player1_flag,
        p1_team=match.player1_team,
        p2_flag=match.player2_flag,
        p2_team=match.player2_team,
        score=score,
    )
    channel = match.channel_id or config.channel_id
    return await _safe_send(bot, channel, text)


async def publish_match_end(
    bot: Bot,
    match: Match,
    winner_flag: str,
    winner_team: str,
    winner_name: str,
    p1_form: str,
    p2_form: str,
) -> Optional[int]:
    if match.winner_id:
        text = texts.CHANNEL_MATCH_END.format(
            p1_flag=match.player1_flag,
            p1_team=match.player1_team,
            p1_score=match.player1_score,
            p2_score=match.player2_score,
            p2_team=match.player2_team,
            p2_flag=match.player2_flag,
            winner_flag=winner_flag,
            winner_team=winner_team,
            winner_name=winner_name,
            p1_form=p1_form,
            p2_form=p2_form,
        )
    else:
        score = match.player1_score
        text = texts.CHANNEL_MATCH_DRAW.format(
            p1_flag=match.player1_flag,
            p1_team=match.player1_team,
            p2_flag=match.player2_flag,
            p2_team=match.player2_team,
            score=score,
            p1_form=p1_form,
            p2_form=p2_form,
        )
    channel = match.channel_id or config.channel_id
    return await _safe_send(bot, channel, text)


async def publish_match_cancelled(bot: Bot, match: Match) -> None:
    text = texts.CHANNEL_MATCH_CANCELLED.format(
        p1_flag=match.player1_flag,
        p1_team=match.player1_team,
        p2_flag=match.player2_flag,
        p2_team=match.player2_team,
    )
    channel = match.channel_id or config.channel_id
    await _safe_send(bot, channel, text)


async def broadcast_to_channel(bot: Bot, message: str) -> Optional[int]:
    """Generic broadcast to the default channel."""
    return await _safe_send(bot, config.channel_id, message)


async def notify_player(
    bot: Bot,
    user_id: int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup=None,
) -> Optional[int]:
    """Send a private message to a player."""
    try:
        msg = await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        return msg.message_id
    except TelegramForbiddenError:
        logger.warning("Cannot send message to user %s (blocked bot)", user_id)
    except TelegramBadRequest as e:
        logger.error("Bad request sending to user %s: %s", user_id, e)
    except Exception as e:
        logger.error("Unexpected error notifying user %s: %s", user_id, e)
    return None


async def edit_player_message(
    bot: Bot,
    user_id: int,
    message_id: int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup=None,
) -> bool:
    """Edit a private message sent to a player."""
    try:
        await bot.edit_message_text(
            chat_id=user_id,
            message_id=message_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        return True
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logger.error("Error editing player message: %s", e)
    except Exception as e:
        logger.error("Error editing player message: %s", e)
    return False
