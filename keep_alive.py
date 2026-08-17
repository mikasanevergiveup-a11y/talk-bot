import logging
import os
import threading
import time
from typing import Optional

import requests
from flask import Flask, jsonify


# Keep Flask request logs quiet while preserving application logs.
logging.getLogger("werkzeug").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Render provides PORT at runtime. The fallback keeps local Docker runs usable.
PORT = int(os.getenv("PORT", "10000"))
SELF_PING_INTERVAL = max(60, int(os.getenv("SELF_PING_INTERVAL", "180")))
SELF_PING_START_DELAY = max(0, int(os.getenv("SELF_PING_START_DELAY", "10")))
SELF_PING_TIMEOUT = max(3, int(os.getenv("SELF_PING_TIMEOUT", "10")))


def _service_url() -> str:
    """Return the externally reachable URL when Render provides one."""
    configured = os.getenv("SELF_PING_URL", "").strip()
    if configured:
        return configured.rstrip("/")

    render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip()
    if render_url:
        return render_url.rstrip("/")

    return f"http://127.0.0.1:{PORT}"


@app.get("/")
@app.get("/healthz")
@app.get("/<path:path>")
def health(path: str = ""):
    """Lightweight health endpoint used by Render and the self-ping loop."""
    return jsonify(
        {
            "status": "ok",
            "service": "telegram-music-bot",
            "self_ping": "enabled",
        }
    ), 200


def self_ping_loop() -> None:
    """Ping the public Render URL, falling back to localhost when needed.

    The loop is deliberately rate-limited and retries transient failures without
    terminating the bot process. Self-ping confirms the HTTP process is alive;
    it cannot override a hosting provider's free-tier sleep policy.
    """
    if SELF_PING_START_DELAY:
        time.sleep(SELF_PING_START_DELAY)

    target = f"{_service_url()}/healthz"
    session = requests.Session()

    while True:
        try:
            response = session.get(
                target,
                timeout=SELF_PING_TIMEOUT,
                headers={"User-Agent": "telegram-music-bot-self-ping/1.0"},
            )
            response.raise_for_status()
            logger.info("[Self-Ping Success] %s -> HTTP %s", target, response.status_code)
        except requests.RequestException as exc:
            logger.warning("[Self-Ping Error] %s: %s", target, exc)
        except Exception:
            logger.exception("[Self-Ping Error] Unexpected failure")

        time.sleep(SELF_PING_INTERVAL)


def run_flask() -> None:
    """Run the health server in a daemon thread."""
    try:
        app.run(
            host="0.0.0.0",
            port=PORT,
            threaded=True,
            use_reloader=False,
        )
    except Exception:
        logger.exception("[Flask Server Error]")


def keep_alive() -> None:
    """Start the health server and self-ping loop exactly once per process."""
    flask_thread = threading.Thread(target=run_flask, name="flask-health", daemon=True)
    flask_thread.start()

    ping_thread = threading.Thread(target=self_ping_loop, name="self-ping", daemon=True)
    ping_thread.start()

    logger.info(
        "Keep-Alive Web Server started on Port %s; self-ping interval=%ss; target=%s",
        PORT,
        SELF_PING_INTERVAL,
        _service_url(),
    )
