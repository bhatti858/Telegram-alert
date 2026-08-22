import os
import requests
from flask import Flask, request, jsonify

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8893031654:AAFbVqDnzF5z1rXpw7P8JFM_pHPwDT0592g")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1004481939466")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "my_secret_key")

app = Flask(__name__)

# ==========================================
# TELEGRAM NOTIFIER FUNCTION
# ==========================================
def send_telegram(text: str) -> bool:
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Error: TELEGRAM_BOT_TOKEN set nahi hai!")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.json().get("ok", False)
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False

# ==========================================
# HOME ENDPOINT (Browser Check)
# ==========================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "message": "Telegram Webhook Server Active Hai!"
    }), 200

# ==========================================
# WEBHOOK ENDPOINT (GET & POST Supported)
# ==========================================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # Browser Test Check (GET Method Error Stop)
    if request.method == "GET":
        return jsonify({
            "status": "active",
            "message": "Webhook Endpoint Online Hai! Alerts bhejne ke liye POST request use karein."
        }), 200

    # Security Token Check
    client_secret = request.headers.get("X-Secret-Key") or request.args.get("secret")
    if client_secret and client_secret != WEBHOOK_SECRET:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    # Plain Text Alerts (e.g., TradingView Text Alert)
    if request.content_type == "text/plain":
        raw_msg = request.get_data(as_text=True)
        send_telegram(f"<b>📢 Webhook Alert:</b>\n\n{raw_msg}")
        return jsonify({"status": "success"}), 200

    # JSON Payload Alerts
    data = request.get_json(silent=True) or request.form.to_dict()
    if not data:
        return jsonify({"status": "error", "message": "No payload received"}), 400

    # Direct Message Payload
    if "message" in data:
        send_telegram(f"<b>📢 Notification Alert:</b>\n\n{data['message']}")
        return jsonify({"status": "success"}), 200

    # Structured Trading Payload (XAUUSD, etc.)
    symbol = data.get("symbol", "XAUUSD")
    action = str(data.get("action", "BUY")).upper()
    price = data.get("price", "N/A")
    pnl = data.get("pnl")

    color = "🟢" if action in ["BUY", "LONG"] else "🔴"
    formatted_msg = (
        f"<b>{color} TRADE SIGNAL: {action}</b>\n"
        f"───────────────────\n"
        f"<b>Symbol:</b> <code>{symbol}</code>\n"
        f"<b>Price:</b> <code>{price}</code>\n"
    )
    if pnl:
        formatted_msg += f"<b>PnL:</b> <code>{pnl}</code>\n"
    
    formatted_msg += "───────────────────\n<i>Automated Webhook Alert</i>"

    send_telegram(formatted_msg)
    return jsonify({"status": "success"}), 200

# ==========================================
# SERVER RUNNER
# ==========================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
