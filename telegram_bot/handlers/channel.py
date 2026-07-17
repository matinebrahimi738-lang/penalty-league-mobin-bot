"""
Channel-related admin commands.
Allows admin to manually trigger channel posts if needed.
"""

from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bot.config import config
from telegram_bot.services.channel_service import broadcast_to_channel
from telegram_bot.services.league_service import format_league_table
from telegram_bot.utils import texts

logger = logging.getLogger(__name__)
router = Router(name="channel")


@router.message(Command("post_league"))
async def cmd_post_league(message: Message, bot: Bot) -> None:
    """Admin command: post league table to channel."""
    if not config.is_admin(message.from_user.id):
        await message.answer(texts.NOT_ADMIN)
        return

    table = await format_league_table()
    msg_id = await broadcast_to_channel(bot, table)
    if msg_id:
        await message.answer("✅ جدول لیگ در کانال منتشر شد.")
    else:
        await message.answer("❌ خطا در ارسال به کانال. کانال را بررسی کنید.")


@router.message(Command("post_message"))
async def cmd_post_message(message: Message, bot: Bot) -> None:
    """Admin command: post custom message to channel.
    Usage: /post_message <text>
    """
    if not config.is_admin(message.from_user.id):
        await message.answer(texts.NOT_ADMIN)
        return

    # Extract message after command
    parts = message.text.split(None, 1) if message.text else []
    if len(parts) < 2:
        await message.answer("استفاده: /post_message <متن پیام>")
        return

    post_text = parts[1]
    msg_id = await broadcast_to_channel(bot, post_text)
    if msg_id:
        await message.answer("✅ پیام در کانال منتشر شد.")
    else:
        await message.answer("❌ خطا در ارسال به کانال.")
