import os
import html
import requests
from flask import Flask, request, jsonify

# =====================================================
# FLASK APP SETUP
# =====================================================
# Gunicorn 'app:app' command ke sath sync rakhne ke liye variable 'app' hai
app = Flask(__name__)

# =====================================================
# TELEGRAM CONFIGURATION
# =====================================================
TELEGRAM_BOT_TOKEN = os.environ.get("8804297584:AAH3J1NTc4VhRS3ZQluDJZR7-K0grTrbOEg", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1004481939466").strip()

# =====================================================
# HELPER FUNCTIONS
# =====================================================
def send_telegram(message):
    """Telegram API par message dispatch karta hai aur error log karta hai."""
    if not TELEGRAM_BOT_TOKEN:
        print("[TELEGRAM ERROR] TELEGRAM_BOT_TOKEN Environment Variable missing hai!")
        return False

    if not TELEGRAM_CHAT_ID:
        print("[TELEGRAM ERROR] TELEGRAM_CHAT_ID missing hai!")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        print(f"[TELEGRAM] HTTP Status: {response.status_code}")

        if response.ok:
            print("[TELEGRAM] Message successfully send ho gaya!")
            return True

        # Agar HTML parse error aaye to plain text me fallback bhejega
        print(f"[TELEGRAM API ERROR] {response.text}")
        if "can't parse entities" in response.text.lower():
            print("[TELEGRAM] HTML Parse failed, retrying as Plain Text...")
            payload.pop("parse_mode", None)
            retry_res = requests.post(url, json=payload, timeout=15)
            return retry_res.ok

        return False

    except Exception as e:
        print(f"[TELEGRAM EXCEPTION] {e}")
        return False

# =====================================================
# FLASK ROUTES
# =====================================================

@app.route("/", methods=["GET"])
def home():
    """Render health-check endpoint."""
    return jsonify({
        "status": "online",
        "service": "Telegram Alert Webhook Server"
    }), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    """TradingView ya kisi bhi automated signal ka POST request receive karta hai."""
    try:
        data = None

        # 1. JSON Payload extract karein (agar JSON format me ho)
        if request.is_json:
            data = request.get_json(silent=True)
            
        # 2. Agar JSON fail ho jaye to raw string try karein
        if not data:
            raw_text = request.get_data(as_text=True)
            if raw_text:
                data = {"message": raw_text}

        if not data:
            print("[WEBHOOK ERROR] Request Body bilkul empty mili.")
            return jsonify({"status": "error", "message": "Empty body"}), 400

        # 3. Message format karein
        if isinstance(data, dict) and "message" in data:
            formatted_text = str(data["message"])
        elif isinstance(data, dict):
            # Agar structured dict ho, to HTML list bana dein
            lines = []
            for k, v in data.items():
                safe_val = html.escape(str(v))
                lines.append(f"<b>{k.capitalize()}:</b> {safe_val}")
            formatted_text = "<b>📊 TRADINGVIEW ALERT</b>\n\n" + "\n".join(lines)
        else:
            formatted_text = str(data)

        # 4. Telegram Alert dispatch karein
        success = send_telegram(formatted_text)

        if success:
            return jsonify({"status": "success", "message": "Alert sent to Telegram"}), 200
        else:
            print("[WEBHOOK ERROR] Telegram dispatch failed. Check bot credentials.")
            return jsonify({"status": "error", "message": "Telegram delivery failed"}), 500

    except Exception as e:
        print(f"[WEBHOOK EXCEPTION CRASH] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
