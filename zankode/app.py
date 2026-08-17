# -*- coding: utf-8 -*-
"""Application bootstrap and Telegram handler registration."""

from . import config as cfg
from .config import *
from .utils import validate_config
from .storage import (
    init_db, database_integrity_check, recover_stale_reservations,
    recover_incomplete_gift_redemptions, setting,
)
from .services import operations_watch_loop
from .handlers.commands import (
    start, cmd_account, cmd_emoji, cmd_ref, cmd_id, cmd_admin, cmd_cancel, cmd_backup,
)
from .handlers.router import callbacks
from .handlers.messages import receipt_photo, messages

async def errors(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("Unhandled error", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(update.effective_chat.id, "⚠️ خطای موقت؛ دوباره امتحان کن.")
        except TelegramError: pass

async def post_init(app: Application):
    saved_pool = [
        x.strip()
        for x in setting("premium_emoji_pool", "").split(",")
        if x.strip()
    ]

    fallback_ids = [
        CUSTOM_EMOJI_SHOP_ID,
        CUSTOM_EMOJI_ACCOUNT_ID,
        CUSTOM_EMOJI_SERVICE_ID,
        CUSTOM_EMOJI_ORDERS_ID,
        CUSTOM_EMOJI_SUPPORT_ID,
        CUSTOM_EMOJI_RECEIPT_ID,
        CUSTOM_EMOJI_COUPON_ID,
    ]

    configured_emoji_ids = list(dict.fromkeys(saved_pool or fallback_ids))

    if USE_CUSTOM_EMOJI and configured_emoji_ids:
        try:
            stickers = await app.bot.get_custom_emoji_stickers(configured_emoji_ids)

            valid_custom_emoji_ids = {
                str(s.custom_emoji_id)
                for s in stickers
                if getattr(s, "custom_emoji_id", None)
            }

            animated_custom_emoji_ids = {
                str(s.custom_emoji_id)
                for s in stickers
                if getattr(s, "custom_emoji_id", None)
                and (
                    bool(getattr(s, "is_animated", False))
                    or bool(getattr(s, "is_video", False))
                )
            }

            animated_ordered = [
                eid for eid in configured_emoji_ids
                if eid in animated_custom_emoji_ids
            ]
            valid_ordered = [
                eid for eid in configured_emoji_ids
                if eid in valid_custom_emoji_ids
            ]
            premium_emoji_pool = animated_ordered or valid_ordered

            cfg.VALID_CUSTOM_EMOJI_IDS.clear()
            cfg.VALID_CUSTOM_EMOJI_IDS.update(valid_custom_emoji_ids)
            cfg.ANIMATED_CUSTOM_EMOJI_IDS.clear()
            cfg.ANIMATED_CUSTOM_EMOJI_IDS.update(animated_custom_emoji_ids)
            cfg.PREMIUM_EMOJI_POOL.clear()
            cfg.PREMIUM_EMOJI_POOL.extend(premium_emoji_pool)

            log.info(
                "Premium Emoji: %s valid, %s animated/video, %s configured",
                len(cfg.VALID_CUSTOM_EMOJI_IDS),
                len(cfg.ANIMATED_CUSTOM_EMOJI_IDS),
                len(configured_emoji_ids),
            )

            if not cfg.VALID_CUSTOM_EMOJI_IDS:
                log.warning(
                    "No configured Custom Emoji IDs were accepted. "
                    "Unicode fallback remains active."
                )
            elif not cfg.ANIMATED_CUSTOM_EMOJI_IDS:
                log.warning(
                    "Custom Emoji IDs are valid but none reported animated/video; "
                    "Premium static icons will be used."
                )

        except TelegramError:
            cfg.VALID_CUSTOM_EMOJI_IDS.clear()
            cfg.ANIMATED_CUSTOM_EMOJI_IDS.clear()
            cfg.PREMIUM_EMOJI_POOL.clear()
            log.exception(
                "Premium Custom Emoji validation failed; safe Unicode fallback enabled."
            )
    else:
        cfg.VALID_CUSTOM_EMOJI_IDS.clear()
        cfg.ANIMATED_CUSTOM_EMOJI_IDS.clear()
        cfg.PREMIUM_EMOJI_POOL.clear()

    # Maintenance must start even if an optional Telegram startup call fails.
    if "operations_task" not in app.bot_data:
        app.bot_data["operations_task"] = asyncio.create_task(operations_watch_loop(app), name="operations-watch")

    try:
        # Only /start is visible in Telegram's command menu.
        # Hidden handlers remain registered; no functionality is removed.
        await app.bot.set_my_commands([
            BotCommand("start", "شروع ربات"),
        ])
        me = await app.bot.get_me()
        log.info("Bot started @%s id=%s | Premium Everything Mode=ON", me.username, me.id)
    except TelegramError:
        log.warning("post_init telegram call failed; maintenance loop is still active")

async def _stop_operations_task(app: Application):
    task = app.bot_data.get("operations_task")
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def post_stop(app: Application):
    # Stop our raw maintenance task before the Bot request layer is shut down.
    await _stop_operations_task(app)


async def post_shutdown(app: Application):
    # Idempotent safety net for unusual shutdown paths.
    await _stop_operations_task(app)


def main():
    """Initialize the database, register Telegram handlers, and start polling."""
    if os.name != "nt":
        try:
            os.umask(0o077)
        except OSError:
            pass

    validate_config()
    init_db()
    database_integrity_check()
    recover_stale_reservations()
    recovered_gifts = recover_incomplete_gift_redemptions()
    if recovered_gifts:
        log.warning("Recovered %s crash-interrupted gift redemption(s)", recovered_gifts)
    database_integrity_check()

    app = (
        Application.builder()
        .token(BOT_TOKEN.strip())
        .post_init(post_init)
        .post_stop(post_stop)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("account", cmd_account))
    app.add_handler(CommandHandler("emoji", cmd_emoji))
    app.add_handler(CommandHandler("ref", cmd_ref))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("backup", cmd_backup))

    app.add_handler(CallbackQueryHandler(callbacks))

    # Receipt photos must be handled before generic messages.
    app.add_handler(MessageHandler(filters.PHOTO, receipt_photo), group=0)

    # Other messages: text, documents, videos, and similar content.
    app.add_handler(
        MessageHandler(~filters.COMMAND & ~filters.PHOTO, messages),
        group=1,
    )

    app.add_error_handler(errors)

    log.info("Starting polling...")
    app.run_polling(
        drop_pending_updates=False,
        allowed_updates=["message", "callback_query"],
    )
