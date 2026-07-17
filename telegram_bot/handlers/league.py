"""
League-related handlers (standalone commands).
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bot.services.league_service import format_league_table
from telegram_bot.utils import keyboards

logger = logging.getLogger(__name__)
router = Router(name="league")


@router.message(Command("table"))
async def cmd_table(message: Message) -> None:
    """Show the current league table."""
    table = await format_league_table()
    await message.answer(
        table,
        reply_markup=keyboards.league_keyboard(),
        parse_mode="HTML",
    )
