"""
Player-facing handlers:
  - /start → registration or player panel
  - Player panel callbacks (current match, stats, league, history)
  - Registration flow
"""

from __future__ import annotations

import logging
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from telegram_bot.config import config
from telegram_bot.database import db_get_finished_matches_for_player
from telegram_bot.models import MatchStatus
from telegram_bot.services import match_engine
from telegram_bot.services.league_service import format_league_table, get_player_rank
from telegram_bot.services.player_service import (
    build_player_profile_text,
    get_player,
    get_taken_teams,
    is_registered,
    register_player,
)
from telegram_bot.utils import keyboards, texts
from telegram_bot.utils.states import RegisterStates

logger = logging.getLogger(__name__)
router = Router(name="player")


# ═══════════════════════════════════════════════════════════════════════════════
# /start
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot) -> None:
    """Entry point — routes to admin panel, player panel, or registration."""
    await state.clear()
    user_id = message.from_user.id

    # Admin shortcut
    if config.is_admin(user_id):
        await message.answer(texts.WELCOME_ADMIN, reply_markup=keyboards.admin_main_menu(), parse_mode="HTML")
        return

    player = await get_player(user_id)

    if player:
        # Check maintenance mode
        from telegram_bot.database import db_get_setting
        if await db_get_setting("maintenance_mode", "0") == "1":
            await message.answer(texts.BOT_MAINTENANCE)
            return

        await message.answer(
            texts.WELCOME_PLAYER,
            reply_markup=keyboards.player_main_menu(),
            parse_mode="HTML",
        )
    else:
        # Start registration
        taken = await get_taken_teams()
        await message.answer(
            texts.WELCOME_NEW,
            reply_markup=keyboards.team_selection_keyboard(taken),
            parse_mode="HTML",
        )
        await state.set_state(RegisterStates.waiting_team)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    help_text = (
        "🏆 <b>Penalty League Mobin — راهنما</b>\n\n"
        "دستورات:\n"
        "/start — شروع / پنل اصلی\n"
        "/help — این راهنما\n"
        "/stats — آمار من\n"
        "/league — جدول لیگ\n\n"
        "برای شرکت در مسابقات باید ثبت‌نام کرده باشید.\n"
        "مسابقات توسط ادمین ایجاد می‌شوند."
    )
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer(texts.NOT_REGISTERED, parse_mode="HTML")
        return
    text = await build_player_profile_text(player)
    await message.answer(text, reply_markup=keyboards.back_to_player(), parse_mode="HTML")


@router.message(Command("league"))
async def cmd_league(message: Message) -> None:
    table = await format_league_table()
    await message.answer(table, reply_markup=keyboards.league_keyboard(), parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRATION FSM
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(RegisterStates.waiting_team, F.data.startswith("reg:team:"))
async def reg_team_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Player selected a team during registration."""
    await callback.answer()
    parts = callback.data.split(":", 3)
    # reg:team:{name}:{flag}
    if len(parts) < 4:
        return
    _, _, team_name, team_flag = parts

    # Verify not taken
    taken = await get_taken_teams()
    if team_name in taken:
        await callback.message.edit_text(
            texts.REG_TEAM_TAKEN,
            reply_markup=keyboards.team_selection_keyboard(taken),
            parse_mode="HTML",
        )
        return

    await state.update_data(team_name=team_name, team_flag=team_flag)

    full_name = callback.from_user.full_name or callback.from_user.username or str(callback.from_user.id)
    text = texts.REG_CONFIRM.format(
        full_name=full_name,
        team_flag=team_flag,
        team_name=team_name,
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.confirm_registration(team_name, team_flag),
        parse_mode="HTML",
    )
    await state.set_state(RegisterStates.confirm)


@router.callback_query(RegisterStates.waiting_team, F.data == "reg:taken")
async def reg_taken_click(callback: CallbackQuery) -> None:
    await callback.answer("⛔ این تیم قبلاً انتخاب شده!", show_alert=True)


@router.callback_query(F.data.startswith("reg:confirm:"))
async def reg_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Final registration confirmation."""
    await callback.answer()
    parts = callback.data.split(":", 3)
    if len(parts) < 4:
        return
    _, _, team_name, team_flag = parts

    user = callback.from_user
    full_name = user.full_name or user.username or str(user.id)
    username = user.username or ""

    success, msg = await register_player(
        user_id=user.id,
        username=username,
        full_name=full_name,
        team_name=team_name,
        team_flag=team_flag,
    )

    if success:
        await callback.message.edit_text(
            texts.REG_SUCCESS.format(
                full_name=full_name,
                team_flag=team_flag,
                team_name=team_name,
            ),
            reply_markup=keyboards.player_main_menu(),
            parse_mode="HTML",
        )
        await state.clear()
    elif msg.startswith("already_registered"):
        parts2 = msg.split(":")
        await callback.message.edit_text(
            texts.REG_ALREADY.format(
                team_flag=parts2[2] if len(parts2) > 2 else team_flag,
                team_name=parts2[1] if len(parts2) > 1 else team_name,
            ),
            reply_markup=keyboards.player_main_menu(),
            parse_mode="HTML",
        )
        await state.clear()
    elif msg == "team_taken":
        taken = await get_taken_teams()
        await callback.message.edit_text(
            texts.REG_TEAM_TAKEN,
            reply_markup=keyboards.team_selection_keyboard(taken),
            parse_mode="HTML",
        )
        await state.set_state(RegisterStates.waiting_team)
    else:
        await callback.message.edit_text(texts.ERROR_GENERIC, parse_mode="HTML")
        await state.clear()


@router.callback_query(F.data == "reg:change")
async def reg_change_team(callback: CallbackQuery, state: FSMContext) -> None:
    """Player wants to pick a different team."""
    await callback.answer()
    taken = await get_taken_teams()
    await callback.message.edit_text(
        texts.REG_CHOOSE_TEAM,
        reply_markup=keyboards.team_selection_keyboard(taken),
        parse_mode="HTML",
    )
    await state.set_state(RegisterStates.waiting_team)


# ═══════════════════════════════════════════════════════════════════════════════
# PLAYER PANEL CALLBACKS
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "player:main")
async def player_main(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    player = await get_player(callback.from_user.id)
    if not player:
        await callback.message.edit_text(texts.NOT_REGISTERED, parse_mode="HTML")
        return
    text = texts.PLAYER_PANEL.format(
        team_flag=player.team_flag,
        team_name=player.team_name,
        full_name=player.full_name,
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.player_main_menu(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "player:current_match")
async def player_current_match(callback: CallbackQuery) -> None:
    await callback.answer()
    player = await get_player(callback.from_user.id)
    if not player:
        await callback.message.edit_text(texts.NOT_REGISTERED, parse_mode="HTML")
        return

    match = await match_engine.get_player_active_match(player.id)
    if not match:
        await callback.message.edit_text(
            texts.NO_ACTIVE_MATCH,
            reply_markup=keyboards.back_to_player(),
            parse_mode="HTML",
        )
        return

    p1_form = match.get_form(match.player1_id)
    p2_form = match.get_form(match.player2_id)

    status_labels = {
        MatchStatus.PENDING:      "⏳ در انتظار",
        MatchStatus.RPS:          "🎲 سنگ‌کاغذقیچی",
        MatchStatus.IN_PROGRESS:  "⚽ در حال بازی",
        MatchStatus.SUDDEN_DEATH: "⚡ Sudden Death",
        MatchStatus.FINISHED:     "🏁 پایان",
        MatchStatus.CANCELLED:    "⛔ لغو شده",
    }

    text = (
        f"🎮 <b>مسابقه فعلی شما</b>\n\n"
        f"🆔 شناسه: <code>{match.id}</code>\n"
        f"{match.player1_flag} <b>{match.player1_team}</b> "
        f"<b>{match.player1_score}</b> - <b>{match.player2_score}</b> "
        f"<b>{match.player2_team}</b> {match.player2_flag}\n\n"
        f"📊 <b>FORM</b>\n"
        f"{match.player1_flag} {match.player1_team}\n{p1_form}\n"
        f"{match.player2_flag} {match.player2_team}\n{p2_form}\n\n"
        f"🔄 وضعیت: {status_labels.get(match.status, match.status.value)}\n"
        f"🔢 دور فعلی: {match.current_round}/{match.max_rounds}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.back_to_player(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "player:my_stats")
async def player_my_stats(callback: CallbackQuery) -> None:
    await callback.answer()
    player = await get_player(callback.from_user.id)
    if not player:
        await callback.message.edit_text(texts.NOT_REGISTERED, parse_mode="HTML")
        return

    rank = await get_player_rank(player.id) or "-"
    text = texts.PLAYER_STATS.format(
        team_flag=player.team_flag,
        team_name=player.team_name,
        matches=player.matches_played,
        wins=player.wins,
        losses=player.losses,
        draws=player.draws,
        goals_scored=player.goals_scored,
        saves=player.saves_made,
        win_rate=player.win_rate,
        win_streak=player.win_streak,
        current_streak=player.current_streak,
    ) + f"\n\n🏆 رتبه لیگ: <b>{rank}</b>"

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.back_to_player(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "player:league")
async def player_league(callback: CallbackQuery) -> None:
    await callback.answer()
    table = await format_league_table()
    await callback.message.edit_text(
        table,
        reply_markup=keyboards.league_keyboard(show_back_admin=False),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "league:refresh")
async def league_refresh(callback: CallbackQuery) -> None:
    await callback.answer("🔄 در حال بروزرسانی...")
    table = await format_league_table()
    try:
        await callback.message.edit_text(
            table,
            reply_markup=keyboards.league_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        pass


@router.callback_query(F.data == "player:history")
async def player_history(callback: CallbackQuery) -> None:
    await callback.answer()
    player = await get_player(callback.from_user.id)
    if not player:
        await callback.message.edit_text(texts.NOT_REGISTERED, parse_mode="HTML")
        return

    matches = await db_get_finished_matches_for_player(player.id)
    if not matches:
        await callback.message.edit_text(
            texts.MATCH_HISTORY_EMPTY,
            reply_markup=keyboards.back_to_player(),
            parse_mode="HTML",
        )
        return

    lines = [texts.MATCH_HISTORY_HEADER]
    for m in matches:
        won = m.winner_id == player.id
        draw = m.winner_id is None

        if player.id == m.player1_id:
            your_flag = m.player1_flag
            your_team = m.player1_team
            your_score = m.player1_score
            opp_flag = m.player2_flag
            opp_team = m.player2_team
            opp_score = m.player2_score
        else:
            your_flag = m.player2_flag
            your_team = m.player2_team
            your_score = m.player2_score
            opp_flag = m.player1_flag
            opp_team = m.player1_team
            opp_score = m.player1_score

        result_icon = "🤝" if draw else ("✅" if won else "❌")
        date_str = datetime.fromtimestamp(m.finished_at or m.created_at).strftime("%Y/%m/%d")
        line = (
            f"{result_icon} {date_str}\n"
            f"  {your_flag} {your_team} <b>{your_score}</b> - "
            f"<b>{opp_score}</b> {opp_flag} {opp_team}\n"
        )
        lines.append(line)

    await callback.message.edit_text(
        "".join(lines),
        reply_markup=keyboards.back_to_player(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "cancel")
async def generic_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    player = await get_player(callback.from_user.id)
    if player:
        await callback.message.edit_text(
            texts.CANCELLED,
            reply_markup=keyboards.player_main_menu(),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(texts.CANCELLED)
