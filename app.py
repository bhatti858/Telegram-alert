import os
import html
import json
import requests
from flask import Flask, request, jsonify

# =====================================================
# FLASK APP SETUP
# =====================================================
app = Flask(__name__)

# =====================================================
# TELEGRAM CONFIGURATION
# =====================================================
TELEGRAM_BOT_TOKEN = os.environ.get("8219130500:AAEzWzqLuot7pyUhs0OPtyypRlAkebrrUs8", "").strip()
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


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    """TradingView ya kisi bhi automated signal ka request receive karta hai."""
    # GET Request Handling (405 Method Not Allowed Fix)
    if request.method == "GET":
        return jsonify({
            "status": "online",
            "message": "Webhook endpoint is active. Send a POST request with payload to trigger alerts."
        }), 200

    # POST Request Handling (Crash-Proof Parsing)
    try:
        raw_bytes = request.get_data()
        raw_text = raw_bytes.decode("utf-8", errors="replace").strip()

        if not raw_text:
            print("[WEBHOOK ERROR] Request Body bilkul empty mili.")
            return jsonify({"status": "error", "message": "Empty body"}), 400

        data = None
        # 1. JSON Parse karne ki koshish karein
        try:
            data = json.loads(raw_text)
        except Exception:
            # Agar JSON broken hai ya raw text hai to string banayein
            data = {"message": raw_text}

        # 2. Message Formatting
        if isinstance(data, dict) and "message" in data and len(data) == 1:
            formatted_text = f"<b>📊 TRADINGVIEW ALERT</b>\n\n{html.escape(str(data['message']))}"
        elif isinstance(data, dict):
            lines = []
            for k, v in data.items():
                safe_val = html.escape(str(v))
                lines.append(f"<b>{html.escape(str(k)).capitalize()}:</b> {safe_val}")
            formatted_text = "<b>📊 TRADINGVIEW ALERT</b>\n\n" + "\n".join(lines)
        else:
            formatted_text = f"<b>📊 TRADINGVIEW ALERT</b>\n\n{html.escape(str(data))}"

        # 3. Telegram Alert Dispatch
        success = send_telegram(formatted_text)

        if success:
            return jsonify({"status": "success", "message": "Alert sent to Telegram"}), 200
        else:
            print("[WEBHOOK ERROR] Telegram dispatch failed. Check bot credentials or permissions.")
            return jsonify({"status": "error", "message": "Telegram delivery failed"}), 500

    except Exception as e:
        print(f"[WEBHOOK EXCEPTION CRASH PREVENTED] {e}")
        # Crash hone ke bajaye error log karega aur raw text bhejney ki try karega
        send_telegram(f"<b>⚠️ ALERT PARSE ERROR</b>\n\n<code>{html.escape(str(e))}</code>")
        return jsonify({"status": "error", "message": str(e)}), 200


@app.route("/weekly-report", methods=["GET", "POST"])
def weekly_report():
    """Cron-job se auto-trigger hone wala weekly report endpoint."""
    report_text = (
        "<b>📅 WEEKLY PERFORMANCE REPORT</b>\n\n"
        "<b>Status:</b> All trading systems active\n"
        "<b>Bot Monitor:</b> Webhook operational & monitoring signals\n\n"
        "<i>Have a great trading week ahead!</i>"
    )
    
    success = send_telegram(report_text)
    if success:
        return jsonify({"status": "success", "message": "Weekly report dispatched to Telegram"}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to send weekly report"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
