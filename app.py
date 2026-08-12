from flask import Flask, request
import requests

app = Flask(__name__)

# ----------------------------------------------------
# TELEGRAM CREDENTIALS
# ----------------------------------------------------
TELEGRAM_BOT_TOKEN = "8804297584:AAHSSJ9VwCk3dIZlVvh3p6YjP0J5i0B5gi0"  # Replace with your @BotFather token
TELEGRAM_CHAT_ID = "-1004481939466"         # Your Chat ID


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)


@app.route('/')
def home():
    return "English Multi-TP Trading Bot Active!", 200


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "Webhook Active!", 200

    try:
        data = request.json
        if not data:
            return "No JSON received", 400

        ticker = data.get('ticker', 'XAUUSD')
        price = float(data.get('price', 0))
        
        try:
            entry_price = float(data.get('entry_price', price))
        except (ValueError, TypeError):
            entry_price = price

        comment = str(data.get('comment', '')).upper()
        position = str(data.get('position', '')).lower()
        prev_position = str(data.get('prev_position', '')).lower()
        raw_action = str(data.get('action', '')).lower()

        pip_value = 0.10  # XAUUSD Pip value
        
        # ----------------------------------------------------
        # 1. SPECIFIC TAKE PROFIT (TP1, TP2, TP3, TP4) DETECTION
        # ----------------------------------------------------
        tp_target = None
        if "TP1" in comment or "TARGET 1" in comment:
            tp_target = "TP1 (+100 Pips)"
        elif "TP2" in comment or "TARGET 2" in comment:
            tp_target = "TP2 (+250 Pips)"
        elif "TP3" in comment or "TARGET 3" in comment:
            tp_target = "TP3 (+450 Pips)"
        elif "TP4" in comment or "TARGET 4" in comment:
            tp_target = "TP4 (+700 Pips)"

        # Partial TP Hit (Position is not fully closed yet)
        if tp_target and position != "flat":
            act_type = "BUY" if position == "long" else "SELL"
            tp_msg = (
                f"🎯 **TAKE PROFIT HIT ({tp_target})** 🎯\n\n"
                f"📌 **Symbol:** {ticker}\n"
                f"➡️ **Type:** {act_type}\n"
                f"💵 **Current Price:** ${price:.2f}\n"
                f"───────────────────\n"
                f"📊 **Status:** Partial Profit Secured 🎉\n"
                f"💡 **Tip:** Shift Stop Loss to Break Even!"
            )
            send_telegram(tp_msg)
            return "TP Alert Sent", 200

        # ----------------------------------------------------
        # 2. FULL TRADE CLOSE / SL HIT / FINAL EXIT
        # ----------------------------------------------------
        is_sl_hit = any(sl_term in comment for sl_term in ["SL", "STOP LOSS", "STOPLOSS"])
        is_close = position == "flat" or (prev_position in ["long", "short"] and position != prev_position) or is_sl_hit

        if is_close:
            act_action = "BUY" if prev_position == "long" else "SELL"

            if entry_price > 0 and entry_price != price:
                if act_action == "BUY":
                    pips = round((price - entry_price) / pip_value)
                else:
                    pips = round((entry_price - price) / pip_value)
            else:
                pips = 0

            if is_sl_hit or pips < 0:
                status_title = "🛑 **STOP LOSS HIT** 🛑" if is_sl_hit else "🔴 **TRADE CLOSED** 🔴"
                pnl_text = f"**{pips} Pips Loss** 🛑"
            elif tp_target or pips > 0:
                status_title = f"🎯 **TAKE PROFIT HIT ({tp_target if tp_target else ''})** 🎯" if tp_target else "🟢 **TRADE CLOSED** 🟢"
                pnl_text = f"**+{pips} Pips Profit** 🎉"
            else:
                status_title = "🟢 **TRADE CLOSED** 🟢"
                pnl_text = f"**0 Pips (Break Even)** ⚖️"

            close_msg = (
                f"{status_title}\n\n"
                f"📌 **Symbol:** {ticker}\n"
                f"➡️ **Type:** {act_action}\n"
                f"💵 **Entry Price:** ${entry_price:.2f}\n"
                f"💵 **Exit Price:** ${price:.2f}\n"
                f"───────────────────\n"
                f"📊 **Result:** {pnl_text}"
            )
            
            send_telegram(close_msg)

            if position == "flat" or is_sl_hit:
                return "Close alert processed", 200

        # ----------------------------------------------------
        # 3. NEW SIGNAL (BUY / SELL)
        # ----------------------------------------------------
        new_action = "BUY" if position == "long" or "buy" in raw_action else "SELL"

        sl_pips = 100
        tp1_pips = 100
        tp2_pips = 250
        tp3_pips = 450
        tp4_pips = 700

        if new_action == "BUY":
            sl_price = price - (sl_pips * pip_value)
            tp1_price = price + (tp1_pips * pip_value)
            tp2_price = price + (tp2_pips * pip_value)
            tp3_price = price + (tp3_pips * pip_value)
            tp4_price = price + (tp4_pips * pip_value)
        else:
            sl_price = price + (sl_pips * pip_value)
            tp1_price = price - (tp1_pips * pip_value)
            tp2_price = price - (tp2_pips * pip_value)
            tp3_price = price - (tp3_pips * pip_value)
            tp4_price = price - (tp4_pips * pip_value)

        message = (
            f"🚨 **TRADING SIGNAL** 🚨\n\n"
            f"📌 **Symbol:** {ticker}\n"
            f"➡️ **Action:** {new_action}\n"
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
            f"• Once in profit, activate Break Even\n"
            f"• Accept the stop loss if SL is hit - do not revenge trade"
        )

        send_telegram(message)
        return "OK", 200

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return f"Error: {e}", 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
