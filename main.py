"""
Penalty League Mobin (PLM) — Main Entry Point

Supports both polling (development) and webhook (Render production) modes.
Run with:
    python -m telegram_bot.main
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiohttp import web

from telegram_bot.config import config
from telegram_bot.database import close_db, get_db
from telegram_bot.handlers import admin, channel, league, match, player, rps

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Bot commands (shown in Telegram menu)
# ─────────────────────────────────────────────────────────────────────────────

BOT_COMMANDS = [
    BotCommand(command="start",   description="شروع / پنل اصلی"),
    BotCommand(command="help",    description="راهنما"),
    BotCommand(command="stats",   description="آمار من"),
    BotCommand(command="league",  description="جدول لیگ"),
    BotCommand(command="table",   description="جدول لیگ"),
    BotCommand(command="admin",   description="پنل ادمین"),
]


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeDefault())


# ─────────────────────────────────────────────────────────────────────────────
# Dispatcher setup
# ─────────────────────────────────────────────────────────────────────────────

def build_dispatcher() -> Dispatcher:
    """Build and configure the Aiogram Dispatcher with all routers."""
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register routers in priority order
    # rps and match must come before player to avoid callback conflicts
    dp.include_router(rps.router)
    dp.include_router(match.router)
    dp.include_router(admin.router)
    dp.include_router(channel.router)
    dp.include_router(league.router)
    dp.include_router(player.router)

    return dp


# ─────────────────────────────────────────────────────────────────────────────
# Startup / shutdown hooks
# ─────────────────────────────────────────────────────────────────────────────

async def on_startup(bot: Bot) -> None:
    """Initialize DB, set commands, log startup info."""
    logger.info("=" * 60)
    logger.info("  Penalty League Mobin (PLM) Bot Starting...")
    logger.info("=" * 60)

    # Initialize database
    await get_db()
    logger.info("Database initialized: %s", config.database_path)

    # Set bot commands
    await set_commands(bot)
    logger.info("Bot commands registered.")

    # Log bot info
    me = await bot.get_me()
    logger.info("Bot: @%s (ID: %d)", me.username, me.id)
    logger.info("Admins: %s", config.admin_ids)
    logger.info("Channel: %s", config.channel_id)
    logger.info("Mode: %s", config.bot_mode)
    logger.info("=" * 60)


async def on_shutdown(bot: Bot) -> None:
    """Clean up resources on shutdown."""
    logger.info("Shutting down PLM Bot...")
    await close_db()
    await bot.session.close()
    logger.info("Goodbye!")


# ─────────────────────────────────────────────────────────────────────────────
# POLLING MODE
# ─────────────────────────────────────────────────────────────────────────────

async def run_polling() -> None:
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher()

    dp.startup.register(lambda: on_startup(bot))
    dp.shutdown.register(lambda: on_shutdown(bot))

    logger.info("Starting in POLLING mode...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOK MODE (Render)
# ─────────────────────────────────────────────────────────────────────────────

async def run_webhook() -> None:
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher()

    await on_startup(bot)

    # Set webhook
    webhook_url = config.webhook_url
    await bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True,
        allowed_updates=dp.resolve_used_update_types(),
    )
    logger.info("Webhook set to: %s", webhook_url)

    # aiohttp application
    app = web.Application()
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path=config.webhook_path)
    setup_application(app, dp, bot=bot)

    # Health check endpoint (required by Render)
    async def health(request: web.Request) -> web.Response:
        return web.Response(text="PLM Bot is running! ⚽", status=200)

    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=config.webhook_port)
    await site.start()

    logger.info("Webhook server started on port %d", config.webhook_port)

    try:
        await asyncio.Event().wait()  # Run forever
    finally:
        await on_shutdown(bot)
        await runner.cleanup()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        if config.bot_mode == "webhook" and config.webhook_host:
            asyncio.run(run_webhook())
        else:
            asyncio.run(run_polling())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as exc:
        logger.critical("Fatal error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
