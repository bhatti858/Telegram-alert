import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.getenv("8893031654:AAFbVqDnzF5z1rXpw7P8JFM_pHPwDT0592g")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1004481939466")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "ZaheerGold2026")

def send_telegram_msg(text: str) -> tuple[bool, str]:
    if not BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN environment variable is not set!")
        return False, "TELEGRAM_BOT_TOKEN missing in Render Environment"

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
        print(f"Telegram API Error: {res_data}")
        return False, res_data.get("description", "Telegram API Error")
    except Exception as e:
        print(f"Request Exception: {str(e)}")
        return False, str(e)

@app.route("/", methods=["GET", "HEAD"])
def home():
    return jsonify({"status": "online", "message": "Gold Signals Webhook Active!"}), 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"status": "active", "message": "Ready for alerts"}), 200

    data = request.get_json(silent=True) or request.form.to_dict() or {}

    # Secret check
    client_secret = (
        request.args.get("secret") 
        or request.headers.get("X-Secret-Key") 
        or data.get("secret")
    )

    if WEBHOOK_SECRET and client_secret != WEBHOOK_SECRET:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    try:
        if data:
            event = str(data.get("event", "SIGNAL")).upper()
            # Support both "symbol" and "ticker" keys from TradingView
            symbol = data.get("symbol") or data.get("ticker") or "XAUUSD"
            
            try:
                price = float(data.get("price", 0))
            except (ValueError, TypeError):
                price = 0.0

            # TP HIT
            if event in ["TP_HIT", "TP"]:
                target = str(data.get("target", "TP1")).upper()
                pips = data.get("pips", "100")
                
                formatted_msg = (
                    f"🎯 <b>TARGET HIT: {target}</b>\n"
                    f"───────────────────\n"
                    f"<b>Symbol:</b> <code>{symbol}</code>\n"
                    f"<b>Exit Price:</b> <code>{price:.2f}</code>\n"
                    f"<b>Profit:</b> <code>+{pips} PIPS 💰🔥</code>\n"
                    f"───────────────────"
                )

            # SL HIT
            elif event in ["SL_HIT", "SL"]:
                pips = data.get("pips", "100")
                formatted_msg = (
                    f"🛑 <b>STOP LOSS HIT</b>\n"
                    f"───────────────────\n"
                    f"<b>Symbol:</b> <code>{symbol}</code>\n"
                    f"<b>Exit Price:</b> <code>{price:.2f}</code>\n"
                    f"<b>Loss:</b> <code>-{pips} Pips ❌</code>\n"
                    f"───────────────────"
                )

            # SIGNALS
            else:
                action = str(data.get("action") or data.get("side") or "BUY").upper()
                color = "🟢" if action in ["BUY", "LONG"] else "🔴" if action in ["SELL", "SHORT"] else "🔵"

                formatted_msg = (
                    f"<b>{color} SIGNAL: {action}</b>\n"
                    f"───────────────────\n"
                    f"<b>Symbol:</b> <code>{symbol}</code>\n"
                    f"<b>Price:</b> <code>{price:.2f}</code>\n"
                    f"───────────────────\n"
                )

                if price > 0:
                    if action in ["BUY", "LONG"]:
                        sl = price - 10.0
                        tp1, tp2, tp3, tp4 = price + 10.0, price + 25.0, price + 45.0, price + 70.0
                    else:
                        sl = price + 10.0
                        tp1, tp2, tp3, tp4 = price - 10.0, price - 25.0, price - 45.0, price - 70.0

                    formatted_msg += (
                        f"<b>TP1:</b> <code>{tp1:.2f}</code> | +100 pips\n"
                        f"<b>TP2:</b> <code>{tp2:.2f}</code> | +250 pips\n"
                        f"<b>TP3:</b> <code>{tp3:.2f}</code> | +450 pips\n"
                        f"<b>TP4:</b> <code>{tp4:.2f}</code> | +700 pips\n\n"
                        f"<b>SL:</b> <code>{sl:.2f}</code> | -100 pips\n"
                        f"───────────────────"
                    )
                else:
                    formatted_msg += "───────────────────"
        else:
            raw_msg = request.get_data(as_text=True)
            formatted_msg = f"<b>📢 TRADINGVIEW ALERT</b>\n───────────────────\n{raw_msg}"

        success, log_msg = send_telegram_msg(formatted_msg)
        if success:
            return jsonify({"status": "success"}), 200
        
        # If Telegram fails, return error details instead of crashing
        return jsonify({"status": "error", "reason": log_msg}), 400

    except Exception as err:
        print(f"Internal Server Error: {str(err)}")
        return jsonify({"status": "error", "message": str(err)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
