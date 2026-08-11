from flask import Flask, request
import requests

app = Flask(__name__)

# ----------------------------------------------------
# TELEGRAM CREDENTIALS
# ----------------------------------------------------
TELEGRAM_BOT_TOKEN = "8804297584:AAHSSJ9VwCk3dIZlVvh3p6YjP0J5i0B5gi0"  # Yahan apna @BotFather wala token paste karein
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
        action = str(data.get('action', 'BUY')).upper()
        price = float(data.get('price', 0))

        # ----------------------------------------------------
        # PIPS CONFIGURATION (Gold / XAUUSD: 1 Pip = $0.10)
        # ----------------------------------------------------
        sl_pips = 100   # 100 pips ($10 stoploss)
        tp1_pips = 100  # 100 pips ($10 TP1)
        tp2_pips = 250  # 250 pips ($25 TP2)
        tp3_pips = 450  # 450 pips ($45 TP3)
        tp4_pips = 700  # 700 pips ($70 TP4)

        pip_value = 0.10  # 1 Pip = $0.10 on XAUUSD

        # AUTOMATIC CALCULATION FOR BUY & SELL
        if "BUY" in action:
            sl_price = price - (sl_pips * pip_value)
            tp1_price = price + (tp1_pips * pip_value)
            tp2_price = price + (tp2_pips * pip_value)
            tp3_price = price + (tp3_pips * pip_value)
            tp4_price = price + (tp4_pips * pip_value)
        else:  # SELL
            sl_price = price + (sl_pips * pip_value)
            tp1_price = price - (tp1_pips * pip_value)
            tp2_price = price - (tp2_pips * pip_value)
            tp3_price = price - (tp3_pips * pip_value)
            tp4_price = price - (tp4_pips * pip_value)

        # Telegram Message Formatting
        message = (
            f"🚨 **NEW TRADING SIGNAL** 🚨\n\n"
            f"📌 **Symbol:** {ticker}\n"
            f"➡️ **Action:** {action}\n"
            f"💵 **Entry Price:** ${price:.2f}\n\n"
            f"🎯 **TAKE PROFIT TARGETS**\n"
            f"• TP1 : {tp1_price:.2f} | +{tp1_pips} pip | Secure Profit\n"
            f"• TP2 : {tp2_price:.2f} | +{tp2_pips} pip | Momentum Target\n"
            f"• TP3 : {tp3_price:.2f} | +{tp3_pips} pip | Smart Money Target\n"
            f"• TP4 : {tp4_price:.2f} | +{tp4_pips} pip | Max Projection\n\n"
            f"🛑 **AI RISK CONTROL**\n"
            f"Stop Loss : {sl_price:.2f} | -{sl_pips} pip\n\n"
            f"📌 **EXECUTION PLAN**\n"
            f"• Enter only within the given entry area\n"
            f"• Secure partial profit at TP1 / TP2\n"
            f"• Once in profit, activate Break Even at +3 pip\n"
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
