"""
Handler for penalty direction callback queries during active matches.
Pattern: dir:{match_id}:{role}:{direction}
"""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from telegram_bot.models import Direction
from telegram_bot.services import match_engine
from telegram_bot.services.player_service import get_player
from telegram_bot.utils import texts

logger = logging.getLogger(__name__)
router = Router(name="match")


@router.callback_query(F.data.startswith("dir:"))
async def handle_direction_callback(callback: CallbackQuery, bot: Bot) -> None:
    """
    Handles direction button clicks during penalty rounds.
    Callback data format: dir:{match_id}:{role}:{direction}
    role: 'shoot' | 'save'
    direction: 'left' | 'center' | 'right'
    """
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) != 4:
        return

    _, match_id_str, role, dir_str = parts

    try:
        match_id = int(match_id_str)
        direction = Direction(dir_str)
    except (ValueError, KeyError):
        await callback.message.answer(texts.ERROR_GENERIC)
        return

    if role not in ("shoot", "save"):
        return

    user_id = callback.from_user.id
    player = await get_player(user_id)
    if not player:
        await callback.answer(texts.NOT_REGISTERED, show_alert=True)
        return

    # Remove keyboard to prevent double-click
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    ok, status = await match_engine.handle_direction_choice(
        bot, match_id, user_id, direction, role
    )

    if not ok:
        alert_map = {
            "match_not_found": "❌ مسابقه یافت نشد.",
            "wrong_status":    "⚠️ مسابقه در حال حاضر فعال نیست.",
            "round_not_found": "❌ دور مسابقه یافت نشد.",
            "wrong_role":      "⛔ این نوبت شما نیست!",
            "already_chose":   "⚠️ شما قبلاً انتخاب کرده‌اید!",
            "invalid_role":    "❌ نقش نامعتبر.",
        }
        msg = alert_map.get(status, texts.ERROR_GENERIC)
        await callback.message.answer(msg)
        return

    logger.info("Direction choice: user=%d, match=%d, role=%s, dir=%s, status=%s",
                user_id, match_id, role, dir_str, status)
