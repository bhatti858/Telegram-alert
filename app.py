import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Environment variables se read karega, agar missing hua to direct hardcoded Chat ID use karega
TELEGRAM_BOT_TOKEN = os.getenv('8219130500:AAEzWzqLuot7pyUhs0OPtyypRlAkebrrUs8')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '-1004481939466')

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "message": "Webhook server is running live!"
    }), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(silent=True)
        if not data:
            data = request.get_data(as_text=True)

        if not TELEGRAM_BOT_TOKEN:
            print("[ERROR] TELEGRAM_BOT_TOKEN missing hai! Render Dashboard par Environment settings check karein.")
            return jsonify({"status": "error", "message": "Bot token not configured"}), 200

        # Message Formatting
        if isinstance(data, dict):
            ticker = data.get("ticker", "N/A")
            action = data.get("action", "ALERT")
            price = data.get("price", "N/A")
            message_text = f"🚨 **TradingView Alert** 🚨\n\n📌 **Ticker:** {ticker}\n🎬 **Action:** {action}\n💵 **Price:** {price}"
        else:
            message_text = f"🚨 **TradingView Alert** 🚨\n\n{data}"

        # Telegram API Request
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message_text,
            "parse_mode": "Markdown"
        }

        response = requests.post(telegram_url, json=payload, timeout=10)
        
        if response.status_code != 200:
            print(f"[TELEGRAM API ERROR] Code: {response.status_code}, Response: {response.text}")
            return jsonify({"status": "error", "message": "Failed to send to Telegram"}), 200

        return jsonify({"status": "success", "message": "Alert sent to Telegram successfully"}), 200

    except Exception as e:
        print(f"[WEBHOOK CRASH PREVENTED] Error: {str(e)}")
        # Hamesha 200 OK return karein taake TradingView par 500 Error na aaye
        return jsonify({"status": "error", "message": str(e)}), 200


@app.route('/weekly-report', methods=['GET', 'POST'])
def weekly_report():
    try:
        if not TELEGRAM_BOT_TOKEN:
            return jsonify({"status": "error", "message": "Bot token missing"}), 500

        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": "📊 **Weekly Performance Report**\n\nAll automated systems operating normally.",
            "parse_mode": "Markdown"
        }

        response = requests.post(telegram_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return jsonify({"status": "success", "message": "Weekly report sent"}), 200
        else:
            print(f"[WEEKLY REPORT ERROR] {response.text}")
            return jsonify({"status": "error", "message": response.text}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
