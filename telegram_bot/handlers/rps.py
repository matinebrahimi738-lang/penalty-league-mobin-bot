"""
Handler for Rock-Paper-Scissors callback queries.
Pattern: rps:{match_id}:{choice}
"""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from telegram_bot.models import RPSChoice
from telegram_bot.services import match_engine
from telegram_bot.services.player_service import get_player
from telegram_bot.utils import texts

logger = logging.getLogger(__name__)
router = Router(name="rps")


@router.callback_query(F.data.startswith("rps:"))
async def handle_rps_callback(callback: CallbackQuery, bot: Bot) -> None:
    """
    Handles RPS button clicks.
    Callback data format: rps:{match_id}:{choice}
    """
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) != 3:
        return

    _, match_id_str, choice_str = parts

    try:
        match_id = int(match_id_str)
        choice = RPSChoice(choice_str)
    except (ValueError, KeyError):
        await callback.message.answer(texts.ERROR_GENERIC)
        return

    user_id = callback.from_user.id
    player = await get_player(user_id)
    if not player:
        await callback.answer(texts.NOT_REGISTERED, show_alert=True)
        return

    # Remove the inline keyboard to prevent double-clicking
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    ok, status = await match_engine.handle_rps_choice(bot, match_id, user_id, choice)

    if not ok:
        alert_map = {
            "match_not_found": "❌ مسابقه یافت نشد.",
            "wrong_status":    "⚠️ مرحله سنگ‌کاغذقیچی به پایان رسیده است.",
            "not_in_match":    "⛔ شما در این مسابقه نیستید.",
            "already_chose":   "⚠️ شما قبلاً انتخاب کرده‌اید!",
        }
        msg = alert_map.get(status, texts.ERROR_GENERIC)
        await callback.message.answer(msg)
        return

    if status == "waiting":
        # Already notified in engine
        pass
    elif status == "draw_retry":
        # Already notified in engine (new keyboard sent)
        pass
    # "resolved" is handled inside match_engine

    logger.info("RPS choice: user=%d, match=%d, choice=%s, status=%s",
                user_id, match_id, choice_str, status)
