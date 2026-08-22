import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# --- CONFIGURATION ---
# Replace with your actual Bot Token from @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "8893031654:AAFbVqDnzF5z1rXpw7P8JFM_pHPwDT0592g")

# Target Channel ID with -100 prefix (e.g., -1001608807600) or Username (e.g., "@Hello")
CHAT_ID = os.getenv("CHAT_ID", "-1001608807600")


def send_telegram_message(text: str) -> bool:
    """Sends a formatted message to the target Telegram Channel via HTTP POST."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()

        if res_data.get("ok"):
            print("[SUCCESS] Alert dispatched to Telegram.")
            return True
        else:
            print(f"[ERROR] Telegram API Error: {res_data.get('description')}")
            return False
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return False


@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint to verify server status."""
    return jsonify({"status": "online", "target_chat": CHAT_ID}), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    """Webhook endpoint to receive signals and dispatch Telegram notifications."""
    try:
        # Handle JSON payloads (TradingView / Automated webhook signals)
        if request.is_json:
            data = request.get_json()

            # Extract fields with fallbacks
            symbol = data.get("symbol", "N/A")
            action = data.get("action", data.get("side", "ALERT")).upper()
            price = data.get("price", "N/A")
            tp = data.get("tp", "N/A")
            sl = data.get("sl", "N/A")
            message_custom = data.get("message", "")

            # Format signal into HTML string
            formatted_alert = (
                f"<b>🚨 TRADING SIGNAL</b>\n\n"
                f"<b>Symbol:</b> {symbol}\n"
                f"<b>Action:</b> {action}\n"
                f"<b>Price:</b> {price}\n"
            )

            if tp != "N/A" or sl != "N/A":
                formatted_alert += (
                    f"<code>TP: {tp} | SL: {sl}</code>\n"
                )

            if message_custom:
                formatted_alert += f"\n<b>Note:</b> {message_custom}"

        # Handle Raw Text payloads
        else:
            raw_text = request.get_data(as_text=True)
            formatted_alert = f"<b>🚨 ALERT NOTIFICATION</b>\n\n{raw_text}"

        # Dispatch alert
        success = send_telegram_message(formatted_alert)

        if success:
            return (
                jsonify({"status": "success", "message": "Alert sent"}),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Failed to send to Telegram",
                    }
                ),
                500,
            )

    except Exception as e:
        print(f"[ERROR] Webhook processing failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == "__main__":
    # Runs server locally on port 5000
    app.run(host="0.0.0.0", port=5000, debug=True)
