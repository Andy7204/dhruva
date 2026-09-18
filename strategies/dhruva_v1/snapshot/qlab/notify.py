"""Send the daily call to Telegram (works locally and in the cron).

Set env vars TELEGRAM_TOKEN (from @BotFather) and TELEGRAM_CHAT (your chat id).
No-op if they're unset, so it never breaks a run.
"""
from __future__ import annotations

import os
import urllib.parse
import urllib.request


def send_telegram(text: str) -> bool:
    token = os.environ.get("TELEGRAM_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT")
    if not token or not chat:
        return False
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text[:4000],
                                       "disable_web_page_preview": "true"}).encode()
        urllib.request.urlopen(
            urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data),
            timeout=20).read()
        return True
    except Exception:
        return False
