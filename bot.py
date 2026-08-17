"""Telegram group bot for repeating a message at a configured interval."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress
from typing import Final

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from keep_alive import keep_alive


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
logger = logging.getLogger(__name__)

BOT_TOKEN_ENV: Final[str] = "BOT_TOKEN"
MIN_INTERVAL_SECONDS: Final[float] = float(os.getenv("MIN_INTERVAL_SECONDS", "4"))

# Only one repeating message job is allowed per chat. This prevents accidental
# duplicate loops when the same command is sent more than once.
active_jobs: dict[int, asyncio.Task[None]] = {}


async def send_repeatedly(
    application: Application,
    chat_id: int,
    interval_seconds: float,
    text: str,
) -> None:
    """Send ``text`` to ``chat_id`` every ``interval_seconds`` until cancelled."""
    try:
        while True:
            await asyncio.sleep(interval_seconds)
            await application.bot.send_message(chat_id=chat_id, text=text)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Repeating job failed for chat %s", chat_id)


async def talk_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle `/talk <seconds> <message>` and `/talk stop`."""
    if update.effective_chat is None or update.effective_message is None:
        return

    chat_id = update.effective_chat.id
    args = context.args

    if args and args[0].lower() == "stop":
        job = active_jobs.pop(chat_id, None)
        if job is None or job.done():
            await update.effective_message.reply_text("No active /talk message in this chat.")
            return
        job.cancel()
        with suppress(asyncio.CancelledError):
            await job
        await update.effective_message.reply_text("Stopped the active /talk message.")
        return

    if len(args) < 2:
        await update.effective_message.reply_text(
            "Usage: /talk <seconds> <message>\nExample: /talk 4 Task do\nStop: /talk stop"
        )
        return

    try:
        interval_seconds = float(args[0])
    except ValueError:
        await update.effective_message.reply_text("The first value must be a number of seconds.")
        return

    if interval_seconds < MIN_INTERVAL_SECONDS:
        await update.effective_message.reply_text(
            f"The minimum interval is {MIN_INTERVAL_SECONDS:g} seconds."
        )
        return

    text = " ".join(args[1:]).strip()
    if not text:
        await update.effective_message.reply_text("Please provide the message to repeat.")
        return

    old_job = active_jobs.get(chat_id)
    if old_job is not None and not old_job.done():
        await update.effective_message.reply_text(
            "A /talk message is already active in this chat. Use /talk stop first."
        )
        return

    job = asyncio.create_task(
        send_repeatedly(context.application, chat_id, interval_seconds, text),
        name=f"talk-{chat_id}",
    )
    active_jobs[chat_id] = job
    await update.effective_message.reply_text(
        f"Started repeating every {interval_seconds:g} seconds. Use /talk stop to stop it."
    )


def build_application() -> Application:
    """Create the Telegram application and register the single public command."""
    token = os.getenv(BOT_TOKEN_ENV, "").strip()
    if not token:
        raise RuntimeError(
            f"Missing {BOT_TOKEN_ENV}. Set the Telegram bot token as an environment variable."
        )

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("talk", talk_command))
    return application


def ensure_event_loop() -> None:
    """Ensure the main thread has an active loop for python-telegram-bot."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("event loop is closed")
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


def main() -> None:
    """Start the Render health server and the Telegram polling loop."""
    keep_alive()
    application = build_application()
    ensure_event_loop()
    logger.info("Starting Telegram polling")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
