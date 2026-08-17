# Talk Bot

A small Telegram group bot that repeats a message at a chosen interval. The bot token is read only from the `BOT_TOKEN` environment variable, so no secret is committed to GitHub.

## Command

The public command is:

```text
/talk <seconds> <message>
```

For example:

```text
/talk 4 Task do
```

The bot replies that the job started and then sends `Task do` to the same chat every four seconds. Only one repeating job is allowed per chat. Stop it with:

```text
/talk stop
```

The interval cannot be lower than `MIN_INTERVAL_SECONDS`, which defaults to four seconds. The `/talk` command is available in groups and private chats; Telegram permissions still determine whether the bot can send messages in a group.

## Environment variables

| Variable | Required | Default | Purpose |
|---|---:|---:|---|
| `BOT_TOKEN` | Yes | None | Telegram bot token from BotFather. |
| `MIN_INTERVAL_SECONDS` | No | `4` | Minimum accepted interval for `/talk`. |
| `PORT` | No | `10000` | Port used by the Render health server. Render supplies this automatically. |
| `SELF_PING_URL` | No | Automatic | Optional public URL to ping. |
| `RENDER_EXTERNAL_URL` | No | Automatic | Render's external URL, used when `SELF_PING_URL` is not set. |
| `SELF_PING_INTERVAL` | No | `180` | Health self-ping interval in seconds. |
| `SELF_PING_START_DELAY` | No | `10` | Startup delay before the first self-ping. |
| `SELF_PING_TIMEOUT` | No | `10` | Self-ping request timeout in seconds. |

## Local run

Use Python 3.11 or newer. Create a virtual environment, install the dependencies, set the token, and start the bot:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN='put-your-telegram-bot-token-here'
python bot.py
```

The health endpoint is available at `http://127.0.0.1:10000/healthz` unless `PORT` is changed.

## Deploy on Render

1. Create a new GitHub repository and push this project.
2. In Render, choose **New → Blueprint** and select the GitHub repository. The included `render.yaml` describes the Web Service.
3. When Render asks for `BOT_TOKEN`, enter the Telegram bot token as a secret value. Do not put it in `render.yaml`, source files, or Git history.
4. Deploy the service. Render runs `pip install -r requirements.txt`, starts `python bot.py`, and checks `/healthz`.
5. Add the bot to the Telegram group and grant it permission to send messages. Send `/talk 4 Task do` in the group.

The included `keep_alive.py` provides the Flask health endpoint and a rate-limited self-ping loop. A self-ping can confirm that the HTTP process is reachable, but it cannot guarantee a hosting provider's free-tier uptime policy.

## Security notes

Never commit a real bot token. If a token is exposed, revoke it in BotFather and issue a replacement. The repository intentionally contains no `.env` file and no hard-coded credential.

## Files

| File | Purpose |
|---|---|
| `bot.py` | Telegram command and repeating-message logic. |
| `keep_alive.py` | Shared Render health server and self-ping implementation. |
| `render.yaml` | Render Web Service Blueprint. |
| `requirements.txt` | Python dependencies. |
| `.env.example` | Local environment variable template without secrets. |
