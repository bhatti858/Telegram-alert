
import os
import requests

# =====================================================
# TELEGRAM SETTINGS
# =====================================================

TELEGRAM_BOT_TOKEN = os.environ.get("8804297584:AAH3J1NTc4VhRS3ZQluDJZR7-K0grTrbOEg", "").strip()

TELEGRAM_CHAT_ID = os.environ.get(
    "TELEGRAM_CHAT_ID",
    "-1004481939466"
).strip()

BRAND_TAG = "@bhatti3273"


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN:
        print("[TELEGRAM ERROR] TELEGRAM_BOT_TOKEN is missing")
        return False

    if not TELEGRAM_CHAT_ID:
        print("[TELEGRAM ERROR] TELEGRAM_CHAT_ID is missing")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=15
        )

        print(f"[TELEGRAM] HTTP {response.status_code}")

        if response.ok:
            print("[TELEGRAM] Message sent successfully")
            return True

        print(f"[TELEGRAM ERROR] {response.text}")
        return False

    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")
        return False
