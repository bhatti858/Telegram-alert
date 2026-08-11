from flask import Flask, request
import requests

app = Flask(__name__)

# ----------------------------------------------------
# TELEGRAM CREDENTIALS
# ----------------------------------------------------
# Yahan sirf BotFather wala token paste karein (bina "https://" aur bina "bot" ke)
# Example: TELEGRAM_BOT_TOKEN = "8804297584:AAHSSJ9VwCk3dIZlVvh3p6YjP0J5i0B5gi0"
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Aapki Telegram Group/Channel Chat ID (Pehele se added hai)
TELEGRAM_CHAT_ID = "-1004481939466"


# 1. Home route (UptimeRobot se server ko 24/7 active rakhne ke liye)
@app.route('/')
def home():
    return "Bot is alive and running!", 200


# 2. Webhook route (TradingView alerts receive karne ke liye)
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    # Browser test link open karne par yeh message dikhega
    if request.method == 'GET':
        return "Webhook Endpoint is Active!", 200

    # TradingView se alert aane par yeh execute hoga
    try:
        data = request.json
        if not data:
            return "No JSON received", 400

        ticker = data.get('ticker', 'N/A')
        action = str(data.get('action', 'BUY')).upper()
        price = float(data.get('price', 0))

        # Risk parameters ($10 SL, $20 TP)
        sl_usd = 10.0
        tp_usd = 20.0

        # TP & SL calculation
        if "BUY" in action:
            sl_price = price - sl_usd
            tp_price = price + tp_usd
        else:  # SELL
            sl_price = price + sl_usd
            tp_price = price - tp_usd

        # Telegram Message Formatting
        message = (
            f"🚨 **NEW TRADING SIGNAL** 🚨\n\n"
            f"📌 **Symbol:** {ticker}\n"
            f"➡️ **Action:** {action}\n"
            f"💵 **Entry Price:** ${price:.2f}\n"
            f"🎯 **Take Profit:** ${tp_price:.2f}\n"
            f"🛑 **Stop Loss:** ${sl_price:.2f}"
        )

        # Telegram API Call
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }

        requests.post(url, json=payload)
        return "OK", 200

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return f"Error: {e}", 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
