"""
Admin panel handlers:
  - 
Main admin panel
  - New match creation
  - Player management
  - Admin management
  - Broadcast
  - Settings
  - Match cancellation
"""

from __future__ import annotations

import logging
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from telegram_bot.config import config
from telegram_bot.database import (
    db_add_admin,
    db_get_all_admins,
    db_get_all_settings,
    db_get_match,
    db_get_player,
    db_get_setting,
    db_remove_admin,
    db_set_setting,
)
from telegram_bot.models import MatchStatus
from telegram_bot.services import match_engine
from telegram_bot.services.channel_service import notify_player
from telegram_bot.services.league_service import format_league_table
from telegram_bot.services.player_service import (
    build_player_profile_text,
    deactivate_player,
    get_all_players,
    get_player,
)
from telegram_bot.utils import keyboards, texts
from telegram_bot.utils.states import AddAdminStates, BroadcastStates, CreateMatchStates, SettingsStates

logger = logging.getLogger(__name__)
router = Router(name="admin")


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN CHECK FILTER
# ─────────────────────────────────────────────────────────────────────────────

async def _require_admin(user_id: int, message_or_callback) -> bool:
    """Return True if user is admin; otherwise send error and return False."""
    from telegram_bot.database import db_get_admin
    is_cfg_admin = config.is_admin(user_id)
    db_admin = await db_get_admin(user_id)
    if not is_cfg_admin and not db_admin:
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(texts.NOT_ADMIN)
        else:
            await message_or_callback.answer(texts.NOT_ADMIN, show_alert=True)
        return False
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    if not await _require_admin(message.from_user.id, message):
        return
    await state.clear()
    await message.answer(
        texts.ADMIN_PANEL,
        reply_markup=keyboards.admin_main_menu(),
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN MAIN PANEL (callback)
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:main")
async def admin_main_cb(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        texts.ADMIN_PANEL,
        reply_markup=keyboards.admin_main_menu(),
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# NEW MATCH — MULTI-STEP FSM
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:new_match")
async def admin_new_match(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()

    players = await get_all_players()
    if len(players) < 2:
        await callback.message.edit_text(
            texts.ADMIN_NO_PLAYERS,
            reply_markup=keyboards.back_to_admin(),
            parse_mode="HTML",
        )
        return

    await callback.message.edit_text(
        texts.ADMIN_SELECT_PLAYER1,
        reply_markup=keyboards.player_selection_keyboard(players, step=1),
        parse_mode="HTML",
    )
    await state.set_state(CreateMatchStates.waiting_player1)


@router.callback_query(CreateMatchStates.waiting_player1, F.data.startswith("create:p1:"))
async def admin_select_p1(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()

    p1_id = int(callback.data.split(":")[2])
    p1 = await get_player(p1_id)
    if not p1:
        await callback.message.edit_text(texts.ERROR_GENERIC, reply_markup=keyboards.back_to_admin())
        await state.clear()
        return

    await state.update_data(p1_id=p1_id, p1_team=p1.team_name, p1_flag=p1.team_flag, p1_name=p1.full_name)

    players = await get_all_players()
    await callback.message.edit_text(
        texts.ADMIN_SELECT_PLAYER2.format(p1_flag=p1.team_flag, p1_team=p1.team_name),
        reply_markup=keyboards.player_selection_keyboard(players, step=2, exclude_id=p1_id),
        parse_mode="HTML",
    )
    await state.set_state(CreateMatchStates.waiting_player2)


@router.callback_query(CreateMatchStates.waiting_player2, F.data.startswith("create:p2:"))
async def admin_select_p2(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()

    p2_id = int(callback.data.split(":")[2])
    data = await state.get_data()
    p1_id = data.get("p1_id")

    if p2_id == p1_id:
        await callback.message.edit_text(texts.ADMIN_SAME_PLAYER, reply_markup=keyboards.back_to_admin(), parse_mode="HTML")
        await state.clear()
        return

    p2 = await get_player(p2_id)
    if not p2:
        await callback.message.edit_text(texts.ERROR_GENERIC, reply_markup=keyboards.back_to_admin())
        await state.clear()
        return

    await state.update_data(p2_id=p2_id, p2_team=p2.team_name, p2_flag=p2.team_flag, p2_name=p2.full_name)

    max_rounds = await db_get_setting("max_rounds", str(config.default_rounds))

    text = texts.ADMIN_MATCH_CONFIRM.format(
        p1_flag=data["p1_flag"], p1_team=data["p1_team"], p1_name=data["p1_name"],
        p2_flag=p2.team_flag, p2_team=p2.team_name, p2_name=p2.full_name,
        channel=config.channel_id,
        rounds=max_rounds,
    )

    # Encode match data in callback
    match_data = f"{p1_id}:{p2_id}"
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.match_confirm_keyboard(match_data),
        parse_mode="HTML",
    )
    await state.set_state(CreateMatchStates.confirm)


@router.callback_query(CreateMatchStates.confirm, F.data.startswith("create:confirm:"))
async def admin_confirm_match(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()

    parts = callback.data.split(":", 3)

    logger.info(f"CALLBACK DATA = {callback.data}")

    match_data = parts[2] if len(parts) > 2 else ""
    ids = match_data.split(":")
    if len(ids) != 2:
        await callback.message.edit_text(texts.ERROR_GENERIC)
        await state.clear()
        return

    p1_id, p2_id = int(ids[0]), int(ids[1])
    data = await state.get_data()

    ok, reason, match_id = await match_engine.create_match(
        bot=bot,
        player1_id=p1_id,
        player2_id=p2_id,
        channel_id=config.channel_id,
    )

    await state.clear()

    if not ok:
        if reason == "player_busy":
            msg = "⚠️ یکی از بازیکنان در یک مسابقه فعال است."
        else:
            msg = f"❌ خطا: {reason}"

        await callback.message.edit_text(
            msg,
            reply_markup=keyboards.back_to_admin(),
            parse_mode="HTML"
        )
        return

    p1 = await get_player(p1_id)
    p2 = await get_player(p2_id)

    await callback.message.edit_text(

texts.ADMIN_MATCH_CREATED.format(
            match_id=match_id,
            p1_flag=p1.team_flag if p1 
else "",
            p1_team=p1.team_name if p1 else "",
            p2_flag=p2.team_flag if p2 else "",
            p2_team=p2.team_name if p2 else "",
    ),
    reply_markup=keyboards.back_to_admin(),
    parse_mode="HTML",
)


# ═══════════════════════════════════════════════════════════════════════════════
# PLAYER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:players")
async def admin_players_list(callback: CallbackQuery) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()

    players = await get_all_players()
    if not players:
        await callback.message.edit_text(
            texts.ADMIN_NO_PLAYERS,
            reply_markup=keyboards.back_to_admin(),
            parse_mode="HTML",
        )
        return

    await callback.message.edit_text(
        texts.ADMIN_PLAYERS_LIST.format(
            players_text=f"تعداد کل: <b>{len(players)}</b> بازیکن"
        ),
        reply_markup=keyboards.players_management_keyboard(players),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:player:"))
async def admin_player_detail(callback: CallbackQuery) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()

    player_id = int(callback.data.split(":")[2])
    player = await get_player(player_id)
    if not player:
        await callback.message.edit_text(texts.ERROR_GENERIC, reply_markup=keyboards.back_to_admin())
        return

    text = await build_player_profile_text(player)
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.player_action_keyboard(player_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:pstats:"))
async def admin_player_stats(callback: CallbackQuery) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()
    player_id = int(callback.data.split(":")[2])
    player = await get_player(player_id)
    if not player:
        await callback.message.edit_text(texts.ERROR_GENERIC)
        return
    text = await build_player_profile_text(player)
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.player_action_keyboard(player_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:delete_player:"))
async def admin_delete_player_confirm(callback: CallbackQuery) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()
    player_id = int(callback.data.split(":")[2])
    player = await get_player(player_id)
    if not player:
        await callback.message.edit_text(texts.ERROR_GENERIC)
        return

    await callback.message.edit_text(
        f"⚠️ آیا از حذف بازیکن <b>{player.full_name}</b> ({player.team_flag} {player.team_name}) مطمئن هستید؟",
        reply_markup=keyboards.confirm_cancel(f"admin:confirm_delete:{player_id}", "admin:players"),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:confirm_delete:"))
async def admin_confirm_delete_player(callback: CallbackQuery) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()
    player_id = int(callback.data.split(":")[2])
    success = await deactivate_player(player_id)
    if success:
        await callback.message.edit_text(
            "✅ بازیکن با موفقیت حذف شد.",
            reply_markup=keyboards.back_to_admin(),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(texts.ERROR_GENERIC, reply_markup=keyboards.back_to_admin())


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:manage_admins")
async def admin_manage_admins(callback: CallbackQuery) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()
    admins = await db_get_all_admins()
    await callback.message.edit_text(
        f"👤 <b>مدیران ربات</b>\n\nتعداد: <b>{len(admins)}</b>",
        reply_markup=keyboards.admin_management_keyboard(admins),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:admin_detail:"))
async def admin_admin_detail(callback: CallbackQuery) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()
    from telegram_bot.database import db_get_admin
    admin_id = int(callback.data.split(":")[2])
    admin = await db_get_admin(admin_id)
    if not admin:
        await callback.message.edit_text(texts.ERROR_GENERIC)
        return
    text = (
        f"👤 <b>اطلاعات ادمین</b>\n\n"
        f"🆔 آی‌دی: <code>{admin.id}</code>\n"
        f"👤 نام: <b>{admin.full_name}</b>\n"
        f"🔑 نقش: {'👑 سوپرادمین' if admin.is_super else '🔑 ادمین'}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.admin_detail_keyboard(admin.id, admin.is_super),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:add_admin")
async def admin_add_admin_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()
    await callback.message.edit_text(
        texts.ADD_ADMIN_ENTER_ID,
        reply_markup=keyboards.back_to_admin(),
        parse_mode="HTML",
    )
    await state.set_state(AddAdminStates.waiting_user_id)


@router.message(AddAdminStates.waiting_user_id)
async def admin_add_admin_receive_id(message: Message, state: FSMContext) -> None:
    if not await _require_admin(message.from_user.id, message):
        return

    raw = message.text.strip() if message.text else ""
    if not raw.isdigit():
        await message.answer("⚠️ آی‌دی باید عددی باشد.", reply_markup=keyboards.back_to_admin())
        return

    user_id = int(raw)

    # Try fetching info via Telegram API
    try:
        chat = await message.bot.get_chat(user_id)
        full_name = chat.full_name or str(user_id)
        username = chat.username or ""
    except Exception:
        full_name = str(user_id)
        username = ""

    await db_add_admin(user_id, username, full_name, is_super=False)
    await state.clear()
    await message.answer(
        texts.ADD_ADMIN_SUCCESS.format(user_id=user_id),
        reply_markup=keyboards.back_to_admin(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:remove_admin:"))
async def admin_remove_admin(callback: CallbackQuery) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()
    admin_id = int(callback.data.split(":")[2])
    await db_remove_admin(admin_id)
    await callback.message.edit_text(
        f"✅ ادمین <code>{admin_id}</code> حذف شد.",
        reply_markup=keyboards.back_to_admin(),
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MATCH CANCELLATION
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:cancel_match")
async def admin_cancel_match_select(callback: CallbackQuery, bot: Bot) -> None:
    """Admin clicks 'cancel match' — find active match."""
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()

    from telegram_bot.database import db_get_all_matches
    all_matches = await db_get_all_matches(limit=10)
    active = [m for m in all_matches if m.status in (
        MatchStatus.PENDING, MatchStatus.RPS,
        MatchStatus.IN_PROGRESS, MatchStatus.SUDDEN_DEATH
    )]

    if not active:
        await callback.message.edit_text(
            texts.ADMIN_NO_ACTIVE_MATCH,
            reply_markup=keyboards.back_to_admin(),
            parse_mode="HTML",
        )
        return

    await callback.message.edit_text(
        "⛔ مسابقه‌ای را برای لغو انتخاب کنید:",
        reply_markup=keyboards.match_list_keyboard(active, is_admin=True),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:cancel_match:"))
async def admin_cancel_specific_match(callback: CallbackQuery, bot: Bot) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()

    match_id = int(callback.data.split(":")[2])
    match = await db_get_match(match_id)
    if not match:
        await callback.message.edit_text(texts.ERROR_GENERIC, reply_markup=keyboards.back_to_admin())
        return

    await callback.message.edit_text(
        texts.ADMIN_CANCEL_MATCH.format(
            p1_flag=match.player1_flag, p1_team=match.player1_team,
            p2_flag=match.player2_flag, p2_team=match.player2_team,
        ),
        reply_markup=keyboards.confirm_cancel(
            f"admin:confirm_cancel_match:{match_id}", "admin:main"
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:confirm_cancel_match:"))
async def admin_confirm_cancel_match(callback: CallbackQuery, bot: Bot) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()
    match_id = int(callback.data.split(":")[2])

    ok, reason = await match_engine.admin_cancel_match(bot, match_id)
    if ok:
        await callback.message.edit_text(
            texts.ADMIN_MATCH_CANCELLED,
            reply_markup=keyboards.back_to_admin(),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            texts.ERROR_GENERIC if reason == "not_found" else texts.ADMIN_NO_ACTIVE_MATCH,
            reply_markup=keyboards.back_to_admin(),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("admin:match_detail:"))
async def admin_match_detail(callback: CallbackQuery) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()
    match_id = int(callback.data.split(":")[2])
    match = await db_get_match(match_id)
    if not match:
        await callback.message.edit_text(texts.ERROR_GENERIC)
        return

    p1_form = match.get_form(match.player1_id)
    p2_form = match.get_form(match.player2_id)

    text = (
        f"📋 <b>جزئیات مسابقه #{match.id}</b>\n\n"
        f"{match.player1_flag} {match.player1_team} <b>{match.player1_score}</b> "
        f"- <b>{match.player2_score}</b> {match.player2_team} {match.player2_flag}\n\n"
        f"📊 FORM\n{match.player1_flag} {match.player1_team}\n{p1_form}\n"
        f"{match.player2_flag} {match.player2_team}\n{p2_form}\n\n"
        f"وضعیت: <b>{match.status.value}</b>\n"
        f"دور: <b>{match.current_round}/{match.max_rounds}</b>"
    )

    is_active = match.status in (
        MatchStatus.PENDING, MatchStatus.RPS,
        MatchStatus.IN_PROGRESS, MatchStatus.SUDDEN_DEATH
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.match_detail_keyboard(match_id, is_admin=True) if is_active
        else keyboards.back_to_admin(),
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# BROADCAST
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()
    await callback.message.edit_text(
        texts.ADMIN_BROADCAST_ENTER,
        reply_markup=keyboards.back_to_admin(),
        parse_mode="HTML",
    )
    await state.set_state(BroadcastStates.waiting_message)


@router.message(BroadcastStates.waiting_message)
async def admin_broadcast_receive(message: Message, state: FSMContext) -> None:
    if not await _require_admin(message.from_user.id, message):
        return

    broadcast_text = message.text or message.caption or ""
    if not broadcast_text:
        await message.answer("⚠️ متن اطلاعیه نمی‌تواند خالی باشد.")
        return

    await state.update_data(broadcast_text=broadcast_text)
    players = await get_all_players()

    await message.answer(
        texts.ADMIN_BROADCAST_CONFIRM.format(
            message=broadcast_text[:200],
            count=len(players),
        ),
        reply_markup=keyboards.broadcast_confirm_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(BroadcastStates.confirm)


@router.callback_query(BroadcastStates.confirm, F.data == "broadcast:confirm")
async def admin_broadcast_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()

    data = await state.get_data()
    broadcast_text = data.get("broadcast_text", "")
    players = await get_all_players()

    sent = 0
    failed = 0
    for player in players:
        msg_id = await notify_player(bot, player.id, f"📢 <b>اطلاعیه</b>\n\n{broadcast_text}", parse_mode="HTML")
        if msg_id:
            sent += 1
        else:
            failed += 1

    await state.clear()
    await callback.message.edit_text(
        texts.ADMIN_BROADCAST_DONE.format(sent=sent, failed=failed),
        reply_markup=keyboards.back_to_admin(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "broadcast:cancel")
async def admin_broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        texts.CANCELLED,
        reply_markup=keyboards.back_to_admin(),
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()

    players = await get_all_players()
    from telegram_bot.database import db_get_all_matches
    all_matches = await db_get_all_matches(limit=1000)
    finished = [m for m in all_matches if m.status == MatchStatus.FINISHED]

    total_goals = sum(m.player1_score + m.player2_score for m in finished)

    text = (
        f"📊 <b>آمار کلی لیگ</b>\n\n"
        f"👥 تعداد بازیکنان: <b>{len(players)}</b>\n"
        f"🎮 کل مسابقات: <b>{len(all_matches)}</b>\n"
        f"✅ مسابقات پایان‌یافته: <b>{len(finished)}</b>\n"
        f"⚽ کل گل‌ها: <b>{total_goals}</b>\n\n"
    )

    if players:
        top = max(players, key=lambda p: p.wins)
        text += f"🏆 پربرنده‌ترین: <b>{top.team_flag} {top.team_name}</b> ({top.wins} برد)"

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.back_to_admin(),
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# LEAGUE (admin view)
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:league")
async def admin_league(callback: CallbackQuery) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()
    table = await format_league_table()
    await callback.message.edit_text(
        table,
        reply_markup=keyboards.league_keyboard(show_back_admin=True),
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:settings")
async def admin_settings_panel(callback: CallbackQuery) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()

    max_rounds    = await db_get_setting("max_rounds", "5")
    rps_timeout   = await db_get_setting("rps_timeout", "60")
    round_timeout = await db_get_setting("round_timeout", "60")
    maintenance   = await db_get_setting("maintenance_mode", "0")

    text = texts.ADMIN_SETTINGS.format(
        max_rounds=max_rounds,
        rps_timeout=rps_timeout,
        round_timeout=round_timeout,
        maintenance="✅ فعال" if maintenance == "1" else "❌ غیرفعال",
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.settings_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "settings:toggle_maintenance")
async def settings_toggle_maintenance(callback: CallbackQuery) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return
    await callback.answer()
    current = await db_get_setting("maintenance_mode", "0")
    new_val = "0" if current == "1" else "1"
    await db_set_setting("maintenance_mode", new_val)
    await admin_settings_panel(callback)


@router.callback_query(F.data.startswith("settings:"))
async def settings_change(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _require_admin(callback.from_user.id, callback):
        return

    key = callback.data.split(":")[1]
    if key == "toggle_maintenance":
        return  # handled above

    label_map = {
        "max_rounds":    ("🔢 تعداد دور پیش‌فرض", "عدد صحیح (مثلاً 5)"),
        "rps_timeout":   ("⏱ زمان سنگ‌کاغذقیچی (ثانیه)", "عدد صحیح (مثلاً 60)"),
        "round_timeout": ("⏱ زمان هر دور (ثانیه)", "عدد صحیح (مثلاً 60)"),
    }
    label, hint = label_map.get(key, (key, "مقدار"))

    await callback.answer()
    await state.update_data(settings_key=key)
    await callback.message.edit_text(
        f"⚙️ <b>تغییر {label}</b>\n\n"
        f"مقدار فعلی: <b>{await db_get_setting(key)}</b>\n\n"
        f"مقدار جدید را وارد کنید ({hint}):",
        reply_markup=keyboards.back_to_admin(),
        parse_mode="HTML",
    )
    await state.set_state(SettingsStates.waiting_value)


@router.message(SettingsStates.waiting_value)
async def settings_receive_value(message: Message, state: FSMContext) -> None:
    if not await _require_admin(message.from_user.id, message):
        return
    data = await state.get_data()
    key = data.get("settings_key", "")
    value = message.text.strip() if message.text else ""

    if not value.isdigit():
        await message.answer("⚠️ مقدار باید عدد صحیح باشد.")
        return

    await db_set_setting(key, value)
    await state.clear()
    await message.answer(
        f"✅ تنظیم <b>{key}</b> به <b>{value}</b> تغییر یافت.",
        reply_markup=keyboards.back_to_admin(),
        parse_mode="HTML",
    )
