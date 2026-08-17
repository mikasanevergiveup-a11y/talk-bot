import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import bot


class FakeBot:
    def __init__(self):
        self.send_message = AsyncMock()


async def main() -> None:
    bot.active_jobs.clear()
    fake_bot = FakeBot()
    application = SimpleNamespace(bot=fake_bot)

    start_reply = AsyncMock()
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        effective_message=start_reply,
    )
    context = SimpleNamespace(
        args=["4", "Task", "do"],
        application=application,
    )

    await bot.talk_command(update, context)
    assert "Started repeating" in start_reply.reply_text.await_args.args[0]
    assert 123 in bot.active_jobs

    stop_reply = AsyncMock()
    stop_update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        effective_message=stop_reply,
    )
    stop_context = SimpleNamespace(args=["stop"], application=application)
    await bot.talk_command(stop_update, stop_context)
    assert "Stopped" in stop_reply.reply_text.await_args.args[0]
    assert 123 not in bot.active_jobs

    usage_reply = AsyncMock()
    usage_update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=456),
        effective_message=usage_reply,
    )
    usage_context = SimpleNamespace(args=["4"], application=application)
    await bot.talk_command(usage_update, usage_context)
    assert "Usage" in usage_reply.reply_text.await_args.args[0]


if __name__ == "__main__":
    asyncio.run(main())
    print("smoke test passed")
