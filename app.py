from flask import Flask, request
import requests

app = Flask(__name__)

# ----------------------------------------------------
# TELEGRAM CREDENTIALS
# ----------------------------------------------------
TELEGRAM_BOT_TOKEN = "8804297584:AAHSSJ9VwCk3dIZlVvh3p6YjP0J5i0B5gi0"  # Yahan apna @BotFather token paste karein
TELEGRAM_CHAT_ID = "-1004481939466"         # Aapki Chat ID


@app.route('/')
def home():
    return "Bot is alive and running!", 200


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "Webhook Endpoint is Active!", 200

    try:
        data = request.json
        if not data:
            return "No JSON received", 400

        ticker = data.get('ticker', 'XAUUSD')
        raw_action = str(data.get('action', '')).upper()
        price = float(data.get('price', 0))

        # 1. POSITION CLOSE / EXIT ALERT
        if any(term in raw_action for term in ["FLAT", "CLOSE", "EXIT"]):
            close_message = (
                f"ℹ️ **POSITION CLOSED / EXITED** ℹ️\n\n"
                f"📌 **Symbol:** {ticker}\n"
                f"💵 **Exit Price:** ${price:.2f}\n"
                f"📝 **Status:** Trade closed. Waiting for next signal."
            )
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": close_message, "parse_mode": "Markdown"})
            return "Closed alert sent", 200

        # 2. NEW BUY / SELL SIGNAL ALERT
        action = "BUY" if "BUY" in raw_action else "SELL"

        # Pips Config (XAUUSD: 1 Pip = $0.10)
        sl_pips = 100
        tp1_pips = 100
        tp2_pips = 250
        tp3_pips = 450
        tp4_pips = 700

        pip_value = 0.10

        if action == "BUY":
            sl_price = price - (sl_pips * pip_value)
            tp1_price = price + (tp1_pips * pip_value)
            tp2_price = price + (tp2_pips * pip_value)
            tp3_price = price + (tp3_pips * pip_value)
            tp4_price = price + (tp4_pips * pip_value)
        else:  # SELL / SHORT
            sl_price = price + (sl_pips * pip_value)
            tp1_price = price - (tp1_pips * pip_value)
            tp2_price = price - (tp2_pips * pip_value)
            tp3_price = price - (tp3_pips * pip_value)
            tp4_price = price - (tp4_pips * pip_value)

        # Telegram Signal Message
        message = (
            f"🚨 **TRADING SIGNAL** 🚨\n\n"
            f"📌 **Symbol:** {ticker}\n"
            f"➡️ **Action:** {action}\n"
            f"💵 **Entry Price:** ${price:.2f}\n\n"
            f"🎯 **TAKE PROFIT TARGETS**\n"
            f"• TP1 : {tp1_price:.2f} | +{tp1_pips} pips\n"
            f"• TP2 : {tp2_price:.2f} | +{tp2_pips} pips\n"
            f"• TP3 : {tp3_price:.2f} | +{tp3_pips} pips\n"
            f"• TP4 : {tp4_price:.2f} | +{tp4_pips} pips\n\n"
            f"🛑 **Stop Loss :** {sl_price:.2f} | -{sl_pips} pips\n\n"
            f"📌 **EXECUTION PLAN**\n"
            f"• Enter only within the given entry area\n"
            f"• Secure partial profit at TP1 / TP2\n"
            f"• Once in profit, activate Break Even at +3 pips\n"
            f"• Accept the stop loss if SL is hit - do not revenge trade"
        )

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
