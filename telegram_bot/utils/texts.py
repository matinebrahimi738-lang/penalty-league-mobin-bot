"""
All Persian (Farsi) text templates for the PLM bot.
Centralised here so nothing is hard-coded in handlers.
Uses str.format() placeholders.
"""

from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════════
# GENERAL
# ═══════════════════════════════════════════════════════════════════════════════

WELCOME_ADMIN = (
    "👋 خوش آمدید، مدیر گرامی!\n\n"
    "🏆 <b>Penalty League Mobin</b>\n"
    "به پنل مدیریت لیگ پنالتی خوش آمدید.\n\n"
    "از دکمه‌های زیر برای مدیریت مسابقات استفاده کنید:"
)

WELCOME_PLAYER = (
    "👋 به <b>Penalty League Mobin</b> خوش آمدید!\n\n"
    "⚽ لیگ پنالتی تلگرام\n\n"
    "شما به عنوان بازیکن ثبت شده‌اید.\n"
    "از دکمه‌های زیر برای مشاهده اطلاعات خود استفاده کنید:"
)

WELCOME_NEW = (
    "👋 به <b>Penalty League Mobin</b> خوش آمدید!\n\n"
    "⚽ برای شرکت در مسابقات باید ثبت‌نام کنید.\n\n"
    "لطفاً با دکمه زیر تیم ملی خود را انتخاب کنید:"
)

NOT_REGISTERED = (
    "⛔ شما هنوز ثبت‌نام نکرده‌اید.\n\n"
    "برای ثبت‌نام دستور /start را ارسال کنید."
)

NOT_ADMIN = "⛔ شما دسترسی ادمین ندارید."

BOT_MAINTENANCE = (
    "🔧 ربات در حال تعمیر است.\n"
    "لطفاً بعداً دوباره تلاش کنید."
)

ERROR_GENERIC = "❌ خطایی رخ داد. لطفاً دوباره تلاش کنید."

CANCELLED = "✅ عملیات لغو شد."

# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════

REG_CHOOSE_TEAM = (
    "🌍 لطفاً تیم ملی خود را انتخاب کنید:\n\n"
    "هر تیم فقط می‌تواند توسط یک بازیکن انتخاب شود."
)

REG_TEAM_TAKEN = (
    "⛔ این تیم قبلاً توسط بازیکن دیگری انتخاب شده است.\n"
    "لطفاً تیم دیگری انتخاب کنید."
)

REG_CONFIRM = (
    "✅ تأیید ثبت‌نام\n\n"
    "👤 نام: <b>{full_name}</b>\n"
    "🏳️ تیم: <b>{team_flag} {team_name}</b>\n\n"
    "آیا مطمئن هستید؟"
)

REG_SUCCESS = (
    "🎉 ثبت‌نام موفق!\n\n"
    "👤 <b>{full_name}</b>\n"
    "🏳️ تیم: <b>{team_flag} {team_name}</b>\n\n"
    "اکنون می‌توانید در مسابقات شرکت کنید. 🏆"
)

REG_ALREADY = (
    "ℹ️ شما قبلاً ثبت‌نام کرده‌اید.\n\n"
    "تیم شما: <b>{team_flag} {team_name}</b>"
)

# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — MATCH CREATION
# ═══════════════════════════════════════════════════════════════════════════════

ADMIN_PANEL = (
    "⚙️ <b>پنل مدیریت</b>\n\n"
    "🏆 Penalty League Mobin\n"
    "از دکمه‌های زیر استفاده کنید:"
)

ADMIN_SELECT_PLAYER1 = (
    "👤 <b>ایجاد مسابقه جدید</b>\n\n"
    "مرحله ۱/۲ — بازیکن اول را انتخاب کنید:"
)

ADMIN_SELECT_PLAYER2 = (
    "👤 <b>ایجاد مسابقه جدید</b>\n\n"
    "مرحله ۲/۲ — بازیکن دوم را انتخاب کنید:\n\n"
    "بازیکن اول: <b>{p1_flag} {p1_team}</b>"
)

ADMIN_MATCH_CONFIRM = (
    "✅ <b>تأیید مسابقه جدید</b>\n\n"
    "🏳️ {p1_flag} <b>{p1_team}</b>\n"
    "     <b>({p1_name})</b>\n"
    "🆚\n"
    "🏳️ {p2_flag} <b>{p2_team}</b>\n"
    "     <b>({p2_name})</b>\n\n"
    "📢 کانال: {channel}\n"
    "🔢 تعداد دور: {rounds}\n\n"
    "آیا تأیید می‌کنید؟"
)

ADMIN_MATCH_CREATED = (
    "✅ مسابقه با موفقیت ایجاد شد!\n\n"
    "🆔 شناسه مسابقه: <code>{match_id}</code>\n"
    "{p1_flag} {p1_team} 🆚 {p2_flag} {p2_team}"
)

ADMIN_NO_PLAYERS = "⚠️ هیچ بازیکنی ثبت‌نام نکرده است."
ADMIN_SAME_PLAYER = "⛔ نمی‌توانید یک بازیکن را در هر دو طرف انتخاب کنید."
ADMIN_PLAYER_BUSY = "⛔ یک یا هر دو بازیکن در حال حاضر در مسابقه دیگری هستند."
ADMIN_NO_ACTIVE_MATCH = "⚠️ هیچ مسابقه فعالی وجود ندارد."

ADMIN_PLAYERS_LIST = "👥 <b>لیست بازیکنان</b>\n\n{players_text}"

ADMIN_PLAYER_DETAIL = (
    "👤 <b>پروفایل بازیکن</b>\n\n"
    "🆔 آی‌دی: <code>{user_id}</code>\n"
    "👤 نام: <b>{full_name}</b>\n"
    "🏳️ تیم: <b>{team_flag} {team_name}</b>\n"
    "🎮 مسابقات: <b>{matches}</b>\n"
    "✅ برد: <b>{wins}</b> | ❌ باخت: <b>{losses}</b>\n"
    "⚽ گل زده: <b>{goals}</b> | 🧤 سیو: <b>{saves}</b>\n"
    "📈 درصد برد: <b>{win_rate}%</b>"
)

ADMIN_CANCEL_MATCH = (
    "⛔ <b>لغو مسابقه</b>\n\n"
    "مسابقه زیر لغو می‌شود:\n"
    "{p1_flag} {p1_team} 🆚 {p2_flag} {p2_team}\n\n"
    "آیا مطمئن هستید؟"
)

ADMIN_MATCH_CANCELLED = "✅ مسابقه با موفقیت لغو شد."

ADMIN_BROADCAST_ENTER = "📢 متن اطلاعیه را ارسال کنید:"
ADMIN_BROADCAST_CONFIRM = (
    "📢 <b>تأیید ارسال اطلاعیه</b>\n\n"
    "متن:\n{message}\n\n"
    "این پیام برای <b>{count}</b> بازیکن ارسال می‌شود.\n"
    "آیا مطمئن هستید؟"
)
ADMIN_BROADCAST_DONE = "✅ اطلاعیه برای {sent} بازیکن ارسال شد. ({failed} ناموفق)"

ADMIN_SETTINGS = (
    "⚙️ <b>تنظیمات ربات</b>\n\n"
    "🔢 تعداد دور پیش‌فرض: <b>{max_rounds}</b>\n"
    "⏱ زمان سنگ‌کاغذقیچی: <b>{rps_timeout}</b> ثانیه\n"
    "⏱ زمان هر دور: <b>{round_timeout}</b> ثانیه\n"
    "🔧 حالت تعمیر: <b>{maintenance}</b>\n\n"
    "برای تغییر، روی هر گزینه کلیک کنید:"
)

ADD_ADMIN_ENTER_ID = "👤 آیدی تلگرام کاربر مورد نظر را وارد کنید:"
ADD_ADMIN_SUCCESS = "✅ کاربر <b>{user_id}</b> به عنوان ادمین اضافه شد."
ADD_ADMIN_FAIL = "❌ خطا: کاربر یافت نشد یا قبلاً ادمین بوده است."

# ═══════════════════════════════════════════════════════════════════════════════
# PLAYER PANEL
# ═══════════════════════════════════════════════════════════════════════════════

PLAYER_PANEL = (
    "🎮 <b>پنل بازیکن</b>\n\n"
    "{team_flag} <b>{team_name}</b>\n"
    "👤 {full_name}\n\n"
    "از دکمه‌های زیر استفاده کنید:"
)

PLAYER_STATS = (
    "📊 <b>آمار من</b>\n\n"
    "{team_flag} <b>{team_name}</b>\n\n"
    "🎮 مسابقات: <b>{matches}</b>\n"
    "✅ برد: <b>{wins}</b>\n"
    "❌ باخت: <b>{losses}</b>\n"
    "🤝 مساوی: <b>{draws}</b>\n\n"
    "⚽ گل زده: <b>{goals_scored}</b>\n"
    "🧤 سیو: <b>{saves}</b>\n"
    "📈 درصد برد: <b>{win_rate}%</b>\n"
    "🔥 بهترین سری برد: <b>{win_streak}</b>\n"
    "⚡ سری برد فعلی: <b>{current_streak}</b>"
)

NO_ACTIVE_MATCH = "🎮 شما در حال حاضر مسابقه فعالی ندارید."

MATCH_HISTORY_HEADER = "📜 <b>مسابقات اخیر شما</b>\n\n"
MATCH_HISTORY_EMPTY = "📜 شما هنوز هیچ مسابقه‌ای نداشته‌اید."
MATCH_HISTORY_ROW = (
    "{'✅' if won else '❌'} {date} — "
    "{your_flag} {your_team} {your_score}:{opp_score} {opp_flag} {opp_team}\n"
)

# ═══════════════════════════════════════════════════════════════════════════════
# MATCH FLOW — CHANNEL MESSAGES
# ═══════════════════════════════════════════════════════════════════════════════

CHANNEL_MATCH_START = (
    "🏆 <b>مسابقه جدید آغاز شد!</b>\n\n"
    "{p1_flag} <b>{p1_team}</b>\n"
    "🆚\n"
    "{p2_flag} <b>{p2_team}</b>\n\n"
    "🎲 مرحله سنگ کاغذ قیچی در حال انجام است...\n"
    "بازیکنان آماده باشند! 👇"
)

CHANNEL_RPS_DONE = (
    "🎲 <b>برنده سنگ کاغذ قیچی مشخص شد!</b>\n\n"
    "{winner_flag} <b>{winner_team}</b> برنده شد!\n"
    "{winner_name} اول شوت می‌زند. 🥅"
)

CHANNEL_ROUND_START = (
    "⚽ <b>Round {round_num}</b>\n\n"
    "🥅 دروازه‌بان: {gk_flag} <b>{gk_team}</b>\n"
    "⚽ شوت‌زننده: {shooter_flag} <b>{shooter_team}</b>\n\n"
    "👇 بازیکنان در حال انتخاب جهت هستند..."
)

CHANNEL_GOAL = (
    "⚽ <b>گللللل!!!</b>\n\n"
    "{shooter_flag} {shooter_team} گل زد! 🎉\n\n"
    "📊 <b>FORM</b>\n"
    "{p1_flag} {p1_team}\n"
    "{p1_form}\n"
    "{p2_flag} {p2_team}\n"
    "{p2_form}\n\n"
    "نتیجه: <b>{p1_score} - {p2_score}</b>"
)

CHANNEL_SAVE = (
    "🧤 <b>سیوووو!!!</b>\n\n"
    "{gk_flag} {gk_team} سیو کرد! 👏\n\n"
    "📊 <b>FORM</b>\n"
    "{p1_flag} {p1_team}\n"
    "{p1_form}\n"
    "{p2_flag} {p2_team}\n"
    "{p2_form}\n\n"
    "نتیجه: <b>{p1_score} - {p2_score}</b>"
)

CHANNEL_SUDDEN_DEATH_START = (
    "⚡ <b>Sudden Death!</b>\n\n"
    "مسابقه مساوی است! 🤝\n"
    "{p1_flag} {p1_team} {score} - {score} {p2_flag} {p2_team}\n\n"
    "🔥 حالا هر گل برنده را مشخص می‌کند!"
)

CHANNEL_MATCH_END = (
    "🏁 <b>پایان مسابقه!</b>\n\n"
    "{p1_flag} <b>{p1_team}</b> {p1_score} — {p2_score} <b>{p2_team}</b> {p2_flag}\n\n"
    "🏆 <b>برنده: {winner_flag} {winner_team}!</b>\n"
    "🎉 تبریک به {winner_name}!\n\n"
    "📊 <b>آمار نهایی</b>\n"
    "{p1_flag} {p1_team}\n"
    "{p1_form}\n"
    "{p2_flag} {p2_team}\n"
    "{p2_form}"
)

CHANNEL_MATCH_DRAW = (
    "🏁 <b>پایان مسابقه!</b>\n\n"
    "{p1_flag} <b>{p1_team}</b> {score} — {score} <b>{p2_team}</b> {p2_flag}\n\n"
    "🤝 <b>مساوی!</b>\n\n"
    "📊 <b>آمار نهایی</b>\n"
    "{p1_flag} {p1_team}\n"
    "{p1_form}\n"
    "{p2_flag} {p2_team}\n"
    "{p2_form}"
)

CHANNEL_MATCH_CANCELLED = (
    "⛔ <b>مسابقه لغو شد!</b>\n\n"
    "{p1_flag} {p1_team} 🆚 {p2_flag} {p2_team}\n\n"
    "توسط ادمین لغو گردید."
)

# ═══════════════════════════════════════════════════════════════════════════════
# MATCH FLOW — PRIVATE MESSAGES TO PLAYERS
# ═══════════════════════════════════════════════════════════════════════════════

MATCH_INVITE = (
    "⚽ <b>شما به یک مسابقه دعوت شده‌اید!</b>\n\n"
    "{p1_flag} <b>{p1_team}</b>\n"
    "🆚\n"
    "{p2_flag} <b>{p2_team}</b>\n\n"
    "🎲 ابتدا بازی سنگ کاغذ قیچی را انجام دهید\n"
    "تا مشخص شود چه کسی اول شوت می‌زند."
)

RPS_CHOOSE = (
    "🎲 <b>سنگ کاغذ قیچی</b>\n\n"
    "حریف شما: {opp_flag} <b>{opp_team}</b>\n\n"
    "انتخاب خود را کنید:"
)

RPS_WAITING = (
    "⏳ انتخاب شما ثبت شد!\n"
    "منتظر حریف هستیم..."
)

RPS_YOU_WIN = (
    "🎉 شما سنگ کاغذ قیچی را بردید!\n\n"
    "{your_choice} > {opp_choice}\n\n"
    "⚽ شما <b>اول شوت می‌زنید</b>!"
)

RPS_YOU_LOSE = (
    "😔 حریف سنگ کاغذ قیچی را برد!\n\n"
    "{opp_choice} > {your_choice}\n\n"
    "🥅 شما <b>اول دروازه‌بانی می‌کنید</b>."
)

RPS_DRAW = "🔄 مساوی! دوباره انتخاب کنید:"

RPS_TIMEOUT = (
    "⏰ زمان سنگ کاغذ قیچی تمام شد!\n"
    "مسابقه لغو شد."
)

SHOOTER_TURN = (
    "⚽ <b>Round {round_num} — نوبت شوت زدن شماست!</b>\n\n"
    "🥅 دروازه‌بان: {gk_flag} <b>{gk_team}</b>\n\n"
    "📊 <b>FORM</b>\n"
    "{p1_flag} {p1_team}\n"
    "{p1_form}\n"
    "{p2_flag} {p2_team}\n"
    "{p2_form}\n\n"
    "👇 جهت شوت خود را انتخاب کنید:"
)

GOALKEEPER_TURN = (
    "🥅 <b>Round {round_num} — نوبت دروازه‌بانی شماست!</b>\n\n"
    "⚽ شوت‌زننده: {shooter_flag} <b>{shooter_team}</b>\n\n"
    "📊 <b>FORM</b>\n"
    "{p1_flag} {p1_team}\n"
    "{p1_form}\n"
    "{p2_flag} {p2_team}\n"
    "{p2_form}\n\n"
    "👇 جهت دفاع خود را انتخاب کنید:"
)

WAITING_FOR_OPPONENT = "⏳ انتخاب شما ثبت شد! منتظر حریف هستیم..."

ROUND_RESULT_GOAL_SHOOTER = (
    "⚽ <b>گللللل!</b>\n\n"
    "شوت شما به سمت <b>{your_dir}</b> گل شد! 🎉\n"
    "دروازه‌بان به سمت <b>{opp_dir}</b> رفت."
)

ROUND_RESULT_SAVE_SHOOTER = (
    "😔 <b>سیو شد!</b>\n\n"
    "شوت شما به سمت <b>{your_dir}</b> سیو شد.\n"
    "دروازه‌بان هم به سمت <b>{opp_dir}</b> رفت."
)

ROUND_RESULT_GOAL_GK = (
    "😔 <b>گل خوردید!</b>\n\n"
    "شوت به سمت <b>{opp_dir}</b> آمد.\n"
    "شما به سمت <b>{your_dir}</b> رفتید."
)

ROUND_RESULT_SAVE_GK = (
    "🧤 <b>سیو کردید!</b>\n\n"
    "شوت به سمت <b>{opp_dir}</b> آمد.\n"
    "شما درست حدس زدید و سیو کردید! 🎉"
)

MATCH_YOU_WIN = (
    "🏆 <b>تبریک! شما برنده شدید!</b>\n\n"
    "{your_flag} <b>{your_team}</b> <b>{your_score}</b> - <b>{opp_score}</b> <b>{opp_team}</b> {opp_flag}\n\n"
    "📊 آمار شما:\n"
    "⚽ گل زده: {goals}\n"
    "🧤 سیو: {saves}"
)

MATCH_YOU_LOSE = (
    "😔 <b>متأسفانه باختید!</b>\n\n"
    "{your_flag} <b>{your_team}</b> <b>{your_score}</b> - <b>{opp_score}</b> <b>{opp_team}</b> {opp_flag}\n\n"
    "📊 آمار شما:\n"
    "⚽ گل زده: {goals}\n"
    "🧤 سیو: {saves}\n\n"
    "💪 در مسابقه بعدی بهتر خواهید شد!"
)

MATCH_DRAW_MSG = (
    "🤝 <b>مساوی!</b>\n\n"
    "{your_flag} <b>{your_team}</b> <b>{score}</b> - <b>{score}</b> <b>{opp_team}</b> {opp_flag}\n\n"
    "مسابقه به پایان رسید."
)

MATCH_CANCELLED_PLAYER = (
    "⛔ مسابقه شما توسط ادمین لغو شد.\n"
    "برای اطلاعات بیشتر با ادمین تماس بگیرید."
)

ROUND_TIMEOUT = (
    "⏰ <b>زمان تمام شد!</b>\n\n"
    "شما در زمان مقرر انتخاب نکردید.\n"
    "مسابقه به نفع حریف تمام شد."
)

SUDDEN_DEATH_NOTIFY = (
    "⚡ <b>Sudden Death!</b>\n\n"
    "مسابقه مساوی است!\n"
    "هر گل برنده را مشخص می‌کند. 🔥\n\n"
    "آماده باشید!"
)

# ═══════════════════════════════════════════════════════════════════════════════
# LEAGUE TABLE
# ═══════════════════════════════════════════════════════════════════════════════

LEAGUE_TABLE_HEADER = "🏆 <b>جدول لیگ Penalty League Mobin</b>\n\n"
LEAGUE_TABLE_COLS = (
    "<code>#{rank:<2} {flag} {team:<12} "
    "P:{pts:<3} W:{w} D:{d} L:{l} GD:{gd:+}</code>\n"
)
LEAGUE_TABLE_EMPTY = "📭 جدول لیگ خالی است. هنوز مسابقه‌ای ثبت نشده."

# ═══════════════════════════════════════════════════════════════════════════════
# DIRECTION LABELS
# ═══════════════════════════════════════════════════════════════════════════════

DIR_LEFT   = "چپ ⬅️"
DIR_CENTER = "وسط ⬆️"
DIR_RIGHT  = "راست ➡️"

RPS_ROCK     = "🪨 سنگ"
RPS_PAPER    = "📄 کاغذ"
RPS_SCISSORS = "✂️ قیچی"


def format_form_block(
    p1_flag: str, p1_team: str, p1_form: str,
    p2_flag: str, p2_team: str, p2_form: str,
    round_label: str,
) -> str:
    """Build the FORM display block shown in channel messages."""
    return (
        f"💯 <b>FORM</b>\n\n"
        f"{p1_flag} <b>{p1_team.upper()}</b>\n"
        f"{p1_form}\n\n"
        f"{p2_flag} <b>{p2_team.upper()}</b>\n"
        f"{p2_form}\n\n"
        f"{round_label} 🏆\n"
        f"👇 Give directions"
    )
