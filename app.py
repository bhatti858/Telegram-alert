import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.getenv("8893031654:AAFbVqDnzF5z1rXpw7P8JFM_pHPwDT0592g")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1004481939466")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "ZaheerGold2026")

def send_telegram_msg(text: str) -> tuple[bool, str]:
    if not BOT_TOKEN:
        print("LOG ERROR: TELEGRAM_BOT_TOKEN is missing!")
        return False, "Bot token missing"

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
        print(f"LOG TELEGRAM RESPONSE: {res_data}")  # Print exact response in Render Logs
        
        if res_data.get("ok"):
            return True, "Message sent"
        return False, res_data.get("description", "Telegram Error")
    except Exception as e:
        print(f"LOG EXCEPTION: {str(e)}")
        return False, str(e)

@app.route("/", methods=["GET", "HEAD"])
def home():
    return jsonify({"status": "online", "message": "Gold Signals Webhook Active!"}), 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"status": "active", "message": "Ready for alerts"}), 200

    data = request.get_json(silent=True) or request.form.to_dict() or {}

    client_secret = (
        request.args.get("secret") 
        or request.headers.get("X-Secret-Key") 
        or data.get("secret")
    )

    if WEBHOOK_SECRET and client_secret != WEBHOOK_SECRET:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    symbol = data.get("symbol") or data.get("ticker") or "XAUUSD"
    action = str(data.get("action") or data.get("side") or "BUY").upper()
    price = data.get("price", "0")

    formatted_msg = (
        f"<b>🟢 SIGNAL: {action}</b>\n"
        f"───────────────────\n"
        f"<b>Symbol:</b> <code>{symbol}</code>\n"
        f"<b>Price:</b> <code>{price}</code>\n"
        f"───────────────────"
    )

    success, log_msg = send_telegram_msg(formatted_msg)
    if success:
        return jsonify({"status": "success", "message": "Alert sent!"}), 200
    else:
        # Returns 200 to TradingView so it doesn't fail, but logs Telegram error
        print(f"LOG ERROR DETAILS: {log_msg}")
        return jsonify({"status": "telegram_failed", "reason": log_msg}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
