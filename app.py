import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Environment Variables
BOT_TOKEN = os.getenv("8893031654:AAFbVqDnzF5z1rXpw7P8JFM_pHPwDT0592g")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1004481939466")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "my_secret_key")

def send_telegram(text: str) -> bool:
    if not BOT_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN environment variable missing!")
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
        data = res.json()
        if not data.get("ok"):
            print(f"❌ Telegram API Error: {data.get('description')} | Used Chat ID: {CHAT_ID}")
            return False
        return True
    except Exception as e:
        print(f"❌ Request Exception: {e}")
        return False

@app.route("/", methods=["GET", "HEAD"])
def home():
    return jsonify({"status": "online", "service": "Telegram Alert Webhook"}), 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # Browser GET Check
    if request.method == "GET":
        return jsonify({
            "status": "active",
            "message": "Webhook endpoint online! Post requests use karein."
        }), 200

    # Secret Verification (URL param ya Header se)
    client_secret = request.args.get("secret") or request.headers.get("X-Secret-Key")
    if WEBHOOK_SECRET and client_secret != WEBHOOK_SECRET:
        print(f"⚠️ Unauthorized attempt! Received secret: {client_secret}")
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    # Plain Text TradingView Payload
    if request.content_type == "text/plain":
        raw_msg = request.get_data(as_text=True)
        if send_telegram(f"<b>📢 Webhook Alert:</b>\n\n{raw_msg}"):
            return jsonify({"status": "success"}), 200
        return jsonify({"status": "error", "message": "Telegram send failed"}), 500

    # JSON Payload
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    
    if "message" in data:
        msg_text = f"<b>📢 Alert:</b>\n\n{data['message']}"
    else:
        symbol = data.get("symbol", "XAUUSD")
        action = str(data.get("action", "ALERT")).upper()
        price = data.get("price", "N/A")
        pnl = data.get("pnl")

        color = "🟢" if action in ["BUY", "LONG"] else "🔴"
        msg_text = (
            f"<b>{color} TRADE SIGNAL: {action}</b>\n"
            f"───────────────────\n"
            f"<b>Symbol:</b> <code>{symbol}</code>\n"
            f"<b>Price:</b> <code>{price}</code>\n"
        )
        if pnl:
            msg_text += f"<b>PnL:</b> <code>{pnl}</code>\n"
        msg_text += "───────────────────\n<i>Automated Webhook Alert</i>"

    if send_telegram(msg_text):
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to send to Telegram"}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
