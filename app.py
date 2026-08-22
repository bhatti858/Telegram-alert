import requests
from flask import Flask, request

app = Flask(__name__)

# Aapki configuration details
TELEGRAM_TOKEN = "8219130500:AAEzWzqLuot7pyUhs0OPtyypRlAkebrrUs8"  # BotFather se mila hua API token yahan likhein
CHAT_ID = "-1004481939466"  # Aap ki Telegram Group Chat ID

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return "No data received", 400

    # TradingView JSON Payload se values extract ho rahi hain
    action = data.get('action', 'SIGNAL')
    symbol = data.get('symbol', 'N/A')
    price = data.get('price', 'N/A')
    tf = data.get('timeframe', 'N/A')
    tp = data.get('tp', 'N/A')
    sl = data.get('sl', 'N/A')

    # Telegram message ka format
    message = (
        f"🚨 <b>TRADINGVIEW SIGNAL</b> 🚨\n\n"
        f"📌 <b>Symbol:</b> {symbol}\n"
        f"📈 <b>Action:</b> {action}\n"
        f"💰 <b>Price:</b> {price}\n"
        f"⏱ <b>Timeframe:</b> {tf}\n"
        f"🎯 <b>TP:</b> {tp}\n"
        f"🛑 <b>SL:</b> {sl}"
    )

    # Telegram API URL
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    response = requests.post(url, json=payload)
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
