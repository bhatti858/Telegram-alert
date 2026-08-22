import os
import sys
import requests
from flask import Flask, request, jsonify

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8893031654:AAFbVqDnzF5z1rXpw7P8JFM_pHPwDT0592g")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1004481939466")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "my_secret_key")

# Flask Webhook Server Instance
app = Flask(__name__)

# ==========================================
# TELEGRAM NOTIFIER FUNCTION
# ==========================================
def send_telegram_alert(message: str, parse_mode: str = "HTML") -> bool:
    """Telegram API par message bhejne ka main function."""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Error: TELEGRAM_BOT_TOKEN missing!")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        if data.get("ok"):
            print("✅ Alert successfully sent to Telegram!")
            return True
        else:
            print(f"❌ Telegram API Error: {data.get('description')}")
            return False
    except Exception as e:
        print(f"❌ Network/Request Error: {e}")
        return False

def send_formatted_trade(symbol: str, action: str, price: str, pnl: str = None):
    """Formatted Trading Alert Template."""
    icon = "🟢" if action.upper() in ["BUY", "LONG"] else "🔴"
    text = (
        f"<b>{icon} TRADE ALERT: {action.upper()}</b>\n"
        f"───────────────────\n"
        f"<b>Symbol:</b> <code>{symbol}</code>\n"
        f"<b>Price:</b> <code>{price}</code>\n"
    )
    if pnl:
        text += f"<b>PnL:</b> <code>{pnl}</code>\n"
    
    text += "───────────────────\n<i>Automated GitHub Alert</i>"
    return send_telegram_alert(text)

# ==========================================
# FLASK WEBHOOK ROUTES (Server Usage)
# ==========================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "active", "service": "Telegram Alert Webhook"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    # Security Key Check
    secret = request.headers.get("X-Secret-Key") or request.args.get("secret")
    if secret != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or request.form.to_dict()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Payload Handling
    if "message" in data:
        send_telegram_alert(f"📢 <b>Incoming Alert:</b>\n\n{data['message']}")
    else:
        symbol = data.get("symbol", "XAUUSD")
        action = data.get("action", "BUY")
        price = data.get("price", "N/A")
        pnl = data.get("pnl", None)
        send_formatted_trade(symbol, action, price, pnl)

    return jsonify({"status": "success"}), 200

# ==========================================
# MAIN EXECUTION ENTRY POINT
# ==========================================
if __name__ == "__main__":
    # Agar argument "--server" paas karenge to Flask server chalayega, 
    # warna direct test alert bhejega.
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        print("🚀 Starting Webhook Server on port 5000...")
        app.run(host="0.0.0.0", port=5000)
    else:
        print("📤 Sending Test Alert...")
        send_formatted_trade(
            symbol="XAUUSD",
            action="BUY",
            price="2450.50",
            pnl="+150 USD"
        )
