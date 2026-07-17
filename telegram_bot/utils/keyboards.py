"""
All Inline Keyboard builders for the PLM bot.
Returns InlineKeyboardMarkup objects ready to attach to messages.
"""

from __future__ import annotations

from typing import List, Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from telegram_bot.models import AVAILABLE_TEAMS, Match, Player


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _url_btn(text: str, url: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, url=url)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN MENUS
# ═══════════════════════════════════════════════════════════════════════════════

def admin_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(_btn("➕ مسابقه جدید",         "admin:new_match"))
    builder.row(_btn("👥 مدیریت بازیکنان",      "admin:players"))
    builder.row(_btn("🏆 جدول لیگ",             "admin:league"))
    builder.row(_btn("📊 آمار",                  "admin:stats"))
    builder.row(_btn("📢 ارسال اطلاعیه",         "admin:broadcast"))
    builder.row(_btn("⚙️ تنظیمات",               "admin:settings"))
    builder.row(_btn("⛔ پایان مسابقه فعلی",     "admin:cancel_match"))
    builder.row(_btn("👤 مدیریت ادمین‌ها",        "admin:manage_admins"))
    return builder.as_markup()


def player_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(_btn("🎮 مسابقه فعلی",   "player:current_match"))
    builder.row(_btn("📊 آمار من",        "player:my_stats"))
    builder.row(_btn("🏆 جدول لیگ",       "player:league"))
    builder.row(_btn("📜 مسابقات گذشته",  "player:history"))
    return builder.as_markup()


def back_to_admin() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(_btn("🔙 بازگشت به پنل ادمین", "admin:main"))
    return builder.as_markup()


def back_to_player() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(_btn("🔙 بازگشت", "player:main"))
    return builder.as_markup()


def confirm_cancel(confirm_data: str, cancel_data: str = "cancel") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        _btn("✅ بله، تأیید می‌کنم", confirm_data),
        _btn("❌ لغو",                cancel_data),
    )
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════

def team_selection_keyboard(taken_teams: Optional[List[str]] = None) -> InlineKeyboardMarkup:
    """Show all available national teams; grey out taken ones."""
    taken = set(taken_teams or [])
    builder = InlineKeyboardBuilder()

    for flag, name in AVAILABLE_TEAMS:
        if name in taken:
            # Show as taken but still display it (disabled visually)
            builder.button(text=f"🚫 {flag} {name}", callback_data="reg:taken")
        else:
            builder.button(text=f"{flag} {name}", callback_data=f"reg:team:{name}:{flag}")

    builder.adjust(2)
    return builder.as_markup()


def confirm_registration(team_name: str, team_flag: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        _btn("✅ تأیید", f"reg:confirm:{team_name}:{team_flag}"),
        _btn("🔄 تغییر تیم", "reg:change"),
    )
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — MATCH CREATION
# ═══════════════════════════════════════════════════════════════════════════════

def player_selection_keyboard(
    players: List[Player],
    step: int,
    exclude_id: Optional[int] = None,
) -> InlineKeyboardMarkup:
    """Select player 1 or 2 from registered players."""
    builder = InlineKeyboardBuilder()
    for p in players:
        if p.id == exclude_id:
            continue
        builder.button(
            text=f"{p.team_flag} {p.team_name} ({p.full_name})",
            callback_data=f"create:p{step}:{p.id}",
        )
    builder.adjust(1)
    builder.row(_btn("❌ لغو", "cancel"))
    return builder.as_markup()


def match_confirm_keyboard(match_data: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        _btn("✅ ایجاد مسابقه", f"create:confirm:{match_data}"),
        _btn("❌ لغو",           "cancel"),
    )
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — PLAYERS MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def players_management_keyboard(players: List[Player]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in players:
        builder.button(
            text=f"{p.team_flag} {p.team_name} — {p.full_name}",
            callback_data=f"admin:player:{p.id}",
        )
    builder.adjust(1)
    builder.row(
        _btn("➕ افزودن بازیکن", "admin:add_player"),
        _btn("🔙 بازگشت",        "admin:main"),
    )
    return builder.as_markup()


def player_action_keyboard(player_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(_btn("📊 آمار",              f"admin:pstats:{player_id}"))
    builder.row(_btn("🗑 حذف بازیکن",        f"admin:delete_player:{player_id}"))
    builder.row(_btn("🔙 بازگشت به لیست",    "admin:players"))
    return builder.as_markup()


def admin_management_keyboard(admins: List) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for a in admins:
        builder.button(
            text=f"{'👑' if a.is_super else '🔑'} {a.full_name} ({a.id})",
            callback_data=f"admin:admin_detail:{a.id}",
        )
    builder.adjust(1)
    builder.row(
        _btn("➕ افزودن ادمین", "admin:add_admin"),
        _btn("🔙 بازگشت",       "admin:main"),
    )
    return builder.as_markup()


def admin_detail_keyboard(admin_id: int, is_super: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_super:
        builder.row(_btn("🗑 حذف ادمین", f"admin:remove_admin:{admin_id}"))
    builder.row(_btn("🔙 بازگشت", "admin:manage_admins"))
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

def settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(_btn("🔢 تعداد دور پیش‌فرض", "settings:max_rounds"))
    builder.row(_btn("⏱ زمان سنگ‌کاغذقیچی",  "settings:rps_timeout"))
    builder.row(_btn("⏱ زمان هر دور",         "settings:round_timeout"))
    builder.row(_btn("🔧 حالت تعمیر",          "settings:toggle_maintenance"))
    builder.row(_btn("🔙 بازگشت",              "admin:main"))
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# RPS — ROCK PAPER SCISSORS
# ═══════════════════════════════════════════════════════════════════════════════

def rps_keyboard(match_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        _btn("🪨 سنگ",    f"rps:{match_id}:rock"),
        _btn("📄 کاغذ",   f"rps:{match_id}:paper"),
        _btn("✂️ قیچی",   f"rps:{match_id}:scissors"),
    )
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# PENALTY DIRECTION
# ═══════════════════════════════════════════════════════════════════════════════

def direction_keyboard(match_id: int, role: str) -> InlineKeyboardMarkup:
    """role: 'shoot' or 'save'"""
    builder = InlineKeyboardBuilder()
    builder.row(
        _btn("⬅️ چپ",    f"dir:{match_id}:{role}:left"),
        _btn("⬆️ وسط",   f"dir:{match_id}:{role}:center"),
        _btn("➡️ راست",  f"dir:{match_id}:{role}:right"),
    )
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# MATCH VIEW
# ═══════════════════════════════════════════════════════════════════════════════

def match_detail_keyboard(match_id: int, is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_admin:
        builder.row(_btn("⛔ لغو مسابقه", f"admin:cancel_match:{match_id}"))
    builder.row(_btn("🔙 بازگشت", "admin:main" if is_admin else "player:main"))
    return builder.as_markup()


def match_list_keyboard(matches: List[Match], is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in matches:
        label = (
            f"#{m.id} {m.player1_flag}{m.player1_team} "
            f"🆚 {m.player2_flag}{m.player2_team} [{m.status.value}]"
        )
        callback = f"admin:match_detail:{m.id}" if is_admin else f"player:match_detail:{m.id}"
        builder.button(text=label, callback_data=callback)
    builder.adjust(1)
    builder.row(_btn("🔙 بازگشت", "admin:main" if is_admin else "player:main"))
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# LEAGUE
# ═══════════════════════════════════════════════════════════════════════════════

def league_keyboard(show_back_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(_btn("🔄 بروزرسانی", "league:refresh"))
    if show_back_admin:
        builder.row(_btn("🔙 بازگشت", "admin:main"))
    else:
        builder.row(_btn("🔙 بازگشت", "player:main"))
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# BROADCAST CONFIRM
# ═══════════════════════════════════════════════════════════════════════════════

def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        _btn("📢 ارسال",  "broadcast:confirm"),
        _btn("❌ لغو",    "broadcast:cancel"),
    )
    return builder.as_markup()
