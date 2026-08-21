import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Render Environment Variables se keys read karega
TELEGRAM_BOT_TOKEN = os.getenv('8219130500:AAEzWzqLuot7pyUhs0OPtyypRlAkebrrUs8')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '-1004481939466')

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "message": "TradingView Webhook Server is Live!"
    }), 200

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return jsonify({
            "status": "online",
            "message": "Webhook endpoint is active."
        }), 200

    try:
        data = request.get_json(silent=True)
        if not data:
            data = request.get_data(as_text=True)

        if not TELEGRAM_BOT_TOKEN:
            print("[ERROR] TELEGRAM_BOT_TOKEN Render Environment Variables mein missing hai!")
            return jsonify({"status": "error", "message": "Bot token not configured"}), 200

        # Message Format
        if isinstance(data, dict):
            ticker = data.get("ticker", "N/A")
            action = data.get("action", "ALERT")
            price = data.get("price", "N/A")
            message_text = f"🚨 **TradingView Alert** 🚨\n\n📌 **Ticker:** {ticker}\n🎬 **Action:** {action}\n💵 **Price:** {price}"
        else:
            message_text = f"🚨 **TradingView Alert** 🚨\n\n{data}"

        # Telegram Request
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message_text,
            "parse_mode": "Markdown"
        }

        response = requests.post(telegram_url, json=payload, timeout=10)

        if response.status_code != 200:
            print(f"[TELEGRAM ERROR] {response.text}")
            return jsonify({"status": "error", "message": "Telegram API Error"}), 200

        return jsonify({"status": "success", "message": "Alert sent successfully"}), 200

    except Exception as e:
        print(f"[EXCEPTION] {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
