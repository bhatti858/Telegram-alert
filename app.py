import json
import os
from flask import Flask, request
import requests

app = Flask(__name__)

# ----------------------------------------------------
# TELEGRAM CREDENTIALS
# ----------------------------------------------------
TELEGRAM_BOT_TOKEN = "8804297584:AAHSSJ9VwCk3dIZlVvh3p6YjP0J5i0B5gi0"  # Replace with your @BotFather token
TELEGRAM_CHAT_ID = "-1004481939466"         # Your Chat ID

MEMORY_FILE = "trade_memory.json"


def load_memory():
    """Disk se saved trade positions load karta hai"""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_memory(data):
    """Disk par trade position save karta hai taake Render restart par delete na ho"""
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving memory: {e}")


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)


def calculate_pips(symbol, entry_price, exit_price, trade_type):
    """
    100% Precise Pip Calculation Engine
    For Gold (XAUUSD): $0.10 price difference = 1 pip
    """
    trade_type_upper = trade_type.upper()
    
    if trade_type_upper == "BUY":
        diff = exit_price - entry_price
    else:  # SELL
        diff = entry_price - exit_price

    symbol_upper = symbol.upper()
    if "XAU" in symbol_upper or "GOLD" in symbol_upper:
        pips = diff / 0.10
    elif "JPY" in symbol_upper:
        pips = diff / 0.01
    else:
        pips = diff / 0.0001

    return round(pips)


@app.route('/')
def home():
    return "Persistent Trade Memory & Accurate Pips Bot Active!", 200


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
            tv_entry_price = float(data.get('entry_price', 0))
        except (ValueError, TypeError):
            tv_entry_price = 0

        comment = str(data.get('comment', '')).upper()
        position = str(data.get('position', '')).lower()
        prev_position = str(data.get('prev_position', '')).lower()
        raw_action = str(data.get('action', '')).lower()

        memory = load_memory()
        
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

        # Partial TP Hit
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
        # 2. FULL TRADE CLOSE / SL HIT / REVERSAL EXIT
        # ----------------------------------------------------
        is_sl_hit = any(sl_term in comment for sl_term in ["SL", "STOP LOSS", "STOPLOSS"])
        is_close = position == "flat" or (prev_position in ["long", "short"] and position != prev_position) or is_sl_hit

        if is_close:
            stored_pos = memory.get(ticker, {})
            
            # Memory file se real stored entry price extract karein
            if stored_pos and stored_pos.get('entry_price', 0) > 0:
                entry_price = stored_pos['entry_price']
                act_action = stored_pos['action']
            else:
                entry_price = tv_entry_price if (tv_entry_price > 0 and tv_entry_price != price) else price
                act_action = "BUY" if prev_position == "long" else "SELL"

            # Pip Calculation
            if entry_price > 0 and entry_price != price:
                pips = calculate_pips(ticker, entry_price, price, act_action)
            else:
                pips = 0

            # Ensure SL hit always registers negative pips
            if is_sl_hit and pips > 0:
                pips = -abs(pips)

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

            if position == "flat":
                memory.pop(ticker, None)
                save_memory(memory)
                return "Close alert processed", 200

        # ----------------------------------------------------
        # 3. NEW SIGNAL / REVERSAL OPEN (BUY / SELL)
        # ----------------------------------------------------
        new_action = "BUY" if position == "long" or "buy" in raw_action else "SELL"

        # Naye order ki exact price persistent memory me lock karein
        memory[ticker] = {
            'action': new_action,
            'entry_price': price
        }
        save_memory(memory)

        pip_step = 0.10 if "XAU" in ticker.upper() or "GOLD" in ticker.upper() else 0.0001
        sl_pips = 100
        tp1_pips = 100
        tp2_pips = 250
        tp3_pips = 450
        tp4_pips = 700

        if new_action == "BUY":
            sl_price = price - (sl_pips * pip_step)
            tp1_price = price + (tp1_pips * pip_step)
            tp2_price = price + (tp2_pips * pip_step)
            tp3_price = price + (tp3_pips * pip_step)
            tp4_price = price + (tp4_pips * pip_step)
        else:
            sl_price = price + (sl_pips * pip_step)
            tp1_price = price - (tp1_pips * pip_step)
            tp2_price = price - (tp2_pips * pip_step)
            tp3_price = price - (tp3_pips * pip_step)
            tp4_price = price - (tp4_pips * pip_step)

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
