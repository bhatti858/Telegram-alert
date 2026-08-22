import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Render Environment Variables
BOT_TOKEN = os.getenv("8893031654:AAFbVqDnzF5z1rXpw7P8JFM_pHPwDT0592g")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1004481939466")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "ZaheerGold2026")

@app.route("/", methods=["GET", "HEAD"])
def home():
    return jsonify({"status": "online", "message": "Bot is Running"}), 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"status": "active"}), 200

    # Payload read karein
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    
    # Secret Check (URL parameter ya JSON body se)
    client_secret = request.args.get("secret") or data.get("secret")
    if WEBHOOK_SECRET and client_secret != WEBHOOK_SECRET:
        print(f"Unauthorized access attempt! Provided secret: {client_secret}")
        return jsonify({"status": "unauthorized"}), 401

    # Signal details parse karein
    event = str(data.get("event", "SIGNAL")).upper()
    symbol = data.get("ticker") or data.get("symbol") or "XAUUSD"
    action = str(data.get("action") or data.get("side") or "BUY").upper()
    
    try:
        price = float(data.get("price", 0))
    except (ValueError, TypeError):
        price = 0.0

    # Message Formatting Logic
    if event in ["TP_HIT", "TP"]:
        target = str(data.get("target", "TP1")).upper()
        pips = data.get("pips", "100")
        msg = (
            f"🎯 <b>TARGET HIT: {target}</b>\n"
            f"───────────────────\n"
            f"<b>Symbol:</b> <code>{symbol}</code>\n"
            f"<b>Exit Price:</b> <code>{price:.2f}</code>\n"
            f"<b>Profit:</b> <code>+{pips} PIPS 💰🔥</code>\n"
            f"───────────────────"
        )
    elif event in ["SL_HIT", "SL"]:
        pips = data.get("pips", "100")
        msg = (
            f"🛑 <b>STOP LOSS HIT</b>\n"
            f"───────────────────\n"
            f"<b>Symbol:</b> <code>{symbol}</code>\n"
            f"<b>Exit Price:</b> <code>{price:.2f}</code>\n"
            f"<b>Loss:</b> <code>-{pips} Pips ❌</code>\n"
            f"───────────────────"
        )
    else:
        color = "🟢" if action in ["BUY", "LONG"] else "🔴" if action in ["SELL", "SHORT"] else "🔵"
        msg = (
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

            msg += (
                f"<b>TP1:</b> <code>{tp1:.2f}</code> | +100 pips\n"
                f"<b>TP2:</b> <code>{tp2:.2f}</code> | +250 pips\n"
                f"<b>TP3:</b> <code>{tp3:.2f}</code> | +450 pips\n"
                f"<b>TP4:</b> <code>{tp4:.2f}</code> | +700 pips\n\n"
                f"<b>SL:</b> <code>{sl:.2f}</code> | -100 pips\n"
                f"───────────────────"
            )

    # Telegram Send (Safely handled to prevent 500 errors)
    if BOT_TOKEN:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
            res = requests.post(url, json=payload, timeout=5)
            print(f"Telegram API Status: {res.status_code}, Response: {res.text}")
        except Exception as e:
            print(f"Telegram Exception: {e}")

    # Always return 200 OK so TradingView never shows failure status
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
