from flask import Flask, request
import requests

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = "bot8804297584:AAHSSJ9VwCk3dIZlVvh3p6YjP0J5i0B5gi0"
TELEGRAM_CHAT_ID = "-1004481939466"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        ticker = data.get('ticker', 'N/A')
        action = str(data.get('action', 'BUY')).upper()
        price = float(data.get('price', 0))

        sl_usd = 10.0  # $10 Stop Loss
        tp_usd = 20.0  # $20 Take Profit

        if "BUY" in action:
            sl_price = price - sl_usd
            tp_price = price + tp_usd
        else:
            sl_price = price + sl_usd
            tp_price = price - tp_usd

        message = (
            f"🚨 **NEW TRADING SIGNAL** 🚨\n\n"
            f"📌 **Symbol:** {ticker}\n"
            f"➡️ **Action:** {action}\n"
            f"💵 **Entry Price:** ${price:.2f}\n"
            f"🎯 **Take Profit:** ${tp_price:.2f}\n"
            f"🛑 **Stop Loss:** ${sl_price:.2f}"
        )

        url = f"https://api.telegram.org/bot8804297584:AAHSSJ9VwCk3dIZlVvh3p6YjP0J5i0B5gi0/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "-1004481939466": message, "parse_mode": "Markdown"})
        return "OK", 200
    except Exception as e:
        return f"Error: {e}", 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
