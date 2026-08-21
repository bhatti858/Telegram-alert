import os
import requests
from flask import Flask, request, jsonify

# =====================================================
# FLASK APP SETUP
# =====================================================
# Variable ka naam 'app' hona zaroori hai taake 'gunicorn app:app' kaam kar sakay
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
    if not TELEGRAM_BOT_TOKEN:
        print("[TELEGRAM ERROR] TELEGRAM_BOT_TOKEN is missing in environment variables")
        return False

    if not TELEGRAM_CHAT_ID:
        print("[TELEGRAM ERROR] TELEGRAM_CHAT_ID is missing")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # Markdown ki jagah HTML parse mode reliable rehta hai taake special characters error na dein
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=15
        )

        print(f"[TELEGRAM] HTTP Status: {response.status_code}")

        if response.ok:
            print("[TELEGRAM] Alert sent successfully!")
            return True

        print(f"[TELEGRAM ERROR] API Response: {response.text}")
        return False

    except Exception as e:
        print(f"[TELEGRAM ERROR] Exception: {e}")
        return False

# =====================================================
# FLASK ROUTES
# =====================================================

@app.route("/", methods=["GET"])
def home():
    """Health check route to verify server is alive."""
    return jsonify({
        "status": "online",
        "message": "Telegram Alert Server is running!"
    }), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    """Webhook endpoint to receive incoming alerts (e.g. from TradingView or custom signals)."""
    try:
        # Check if incoming data is JSON or raw text
        if request.is_json:
            data = request.get_json()
            message = data.get("message", str(data))
        else:
            message = request.get_data(as_text=True)

        if not message:
            return jsonify({"status": "error", "message": "Empty payload"}), 400

        # Formatted HTML message send kar rahay hain
        alert_text = f"<b>🚨 ALERT RECEIVED</b>\n\n{message}\n\n<i>@bhatti3273</i>"
        
        success = send_telegram(alert_text)

        if success:
            return jsonify({"status": "success", "message": "Telegram alert sent"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to send Telegram alert"}), 500

    except Exception as e:
        print(f"[WEBHOOK ERROR] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# Local testing ke liye (Render par Gunicorn isko handle karta hai)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
