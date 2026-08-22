import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.getenv("8893031654:AAFbVqDnzF5z1rXpw7P8JFM_pHPwDT0592g")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1004481939466")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "my_secret_key")

def send_telegram_msg(text: str) -> tuple[bool, str]:
    if not BOT_TOKEN:
        return False, "TELEGRAM_BOT_TOKEN missing"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()
        if res_data.get("ok"):
            return True, "Message sent"
        return False, res_data.get("description", "Telegram Error")
    except Exception as e:
        return False, str(e)

@app.route("/", methods=["GET", "HEAD"])
def home():
    return jsonify({"status": "online", "message": "Server Active!"}), 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"status": "active"}), 200

    client_secret = request.args.get("secret") or request.headers.get("X-Secret-Key")
    if WEBHOOK_SECRET and client_secret != WEBHOOK_SECRET:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    if request.content_type == "text/plain":
        raw_msg = request.get_data(as_text=True)
        formatted_msg = f"<b>📢 TRADINGVIEW ALERT</b>\n───────────────────\n{raw_msg}"
    else:
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        if "message" in data:
            formatted_msg = f"<b>📢 TRADINGVIEW ALERT</b>\n───────────────────\n{data['message']}"
        elif data:
            symbol = data.get("symbol", "XAUUSD")
            action = str(data.get("action", "ALERT")).upper()
            price = data.get("price", "N/A")
            color = "🟢" if action in ["BUY", "LONG"] else "🔴" if action in ["SELL", "SHORT"] else "🔵"
            formatted_msg = (
                f"<b>{color} SIGNAL: {action}</b>\n"
                f"───────────────────\n"
                f"<b>Symbol:</b> <code>{symbol}</code>\n"
                f"<b>Price:</b> <code>{price}</code>\n"
                f"───────────────────"
            )
        else:
            raw_fallback = request.get_data(as_text=True)
            formatted_msg = f"<b>📢 TRADINGVIEW ALERT</b>\n───────────────────\n{raw_fallback or 'Empty Alert'}"

    success, log_msg = send_telegram_msg(formatted_msg)
    if success:
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error", "reason": log_msg}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
