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

        # Data extract kar rahe hain
        ticker = data.get('ticker', 'XAUUSD')
        action = str(data.get('action', 'BUY')).upper()
        price = data.get('price', 'N/A')
        
        sl = data.get('sl', 'N/A')
        sl_pips = data.get('sl_pips', '-100')

        tp1 = data.get('tp1', 'N/A')
        tp1_pips = data.get('tp1_pips', '+100')
        
        tp2 = data.get('tp2', 'N/A')
        tp2_pips = data.get('tp2_pips', '+250')
        
        tp3 = data.get('tp3', 'N/A')
        tp3_pips = data.get('tp3_pips', '+450')
        
        tp4 = data.get('tp4', 'N/A')
        tp4_pips = data.get('tp4_pips', '+700')

        # Telegram Message Template Layout
        message = (
            f"🚨 **NEW TRADING SIGNAL** 🚨\n\n"
            f"📌 **Symbol:** {ticker}\n"
            f"➡️ **Action:** {action}\n"
            f"💵 **Entry Price:** {price}\n\n"
            f"🎯 **TAKE PROFIT TARGETS**\n"
            f"• TP1 : {tp1} | {tp1_pips} pip | Secure Profit\n"
            f"• TP2 : {tp2} | {tp2_pips} pip | Momentum Target\n"
            f"• TP3 : {tp3} | {tp3_pips} pip | Smart Money Target\n"
            f"• TP4 : {tp4} | {tp4_pips} pip | Max Projection\n\n"
            f"🛑 **AI RISK CONTROL**\n"
            f"Stop Loss : {sl} | {sl_pips} pip\n\n"
            f"📌 **EXECUTION PLAN**\n"
            f"• Enter only within the given entry area\n"
            f"• Secure partial profit at TP1 / TP2\n"
            f"• Once in profit, activate Break Even at +3 pip\n"
            f"• Accept the stop loss if SL is hit - do not revenge trade"
        )

        # Telegram API ke zariye message bhej rahe hain
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
