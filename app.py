import json
import os
import time
from flask import Flask, request
import requests

app = Flask(__name__)

# ----------------------------------------------------
# TELEGRAM CREDENTIALS
# ----------------------------------------------------
TELEGRAM_BOT_TOKEN = "8804297584:AAHSSJ9VwCk3dIZlVvh3p6YjP0J5i0B5gi0"  # Replace with your @BotFather token
TELEGRAM_CHAT_ID = "-1004481939466"         # Your Chat ID
BRAND_TAG = "@bhatti3273"                   # Your Channel / Brand Tag

MEMORY_FILE = "trade_memory.json"


def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_memory(data):
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


def format_duration(start_time):
    if not start_time:
        return "N/A"
    
    seconds = int(time.time() - start_time)
    if seconds < 60:
        return "1 Min"
    
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} Mins"
    
    hours = minutes // 60
    rem_mins = minutes % 60
    return f"{hours}h {rem_mins}m"


@app.route('/')
def home():
    return f"Trading Bot Active for {BRAND_TAG}!", 200


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
        stored_pos = memory.get(ticker, {})

        if stored_pos and stored_pos.get('entry_price', 0) > 0:
            entry_price = stored_pos['entry_price']
            act_action = stored_pos['action']
            start_timestamp = stored_pos.get('timestamp')
        else:
            entry_price = tv_entry_price if (tv_entry_price > 0 and tv_entry_price != price) else price
            act_action = "BUY" if prev_position == "long" or position == "long" else "SELL"
            start_timestamp = None

        duration_str = format_duration(start_timestamp)

        # ----------------------------------------------------
        # 1. TP1 SE LE KAR TP4 TAK DETECTION
        # ----------------------------------------------------
        tp_label = "TP1"
        if any(t in comment for t in ["TP4", "TARGET 4", "TARGET4", "TP 4", "TAKE PROFIT 4"]):
            tp_label = "TP4"
        elif any(t in comment for t in ["TP3", "TARGET 3", "TARGET3", "TP 3", "TAKE PROFIT 3"]):
            tp_label = "TP3"
        elif any(t in comment for t in ["TP2", "TARGET 2", "TARGET2", "TP 2", "TAKE PROFIT 2"]):
            tp_label = "TP2"
        elif any(t in comment for t in ["TP1", "TARGET 1", "TARGET1", "TP 1", "TAKE PROFIT 1"]):
            tp_label = "TP1"

        if entry_price > 0 and entry_price != price:
            current_pips = calculate_pips(ticker, entry_price, price, act_action)
        else:
            current_pips = 0

        # Partial TP Hit Alert
        if any(t in comment for t in ["TP", "TARGET", "PROFIT"]) and position != "flat":
            tp_msg = (
                f"🔥 **TARGET SMASHED!** 🔥\n"
                f"───────────────────\n"
                f"🎯 **Status:** **{tp_label} HIT**\n"
                f"💵 **Price:** ${price:.2f}\n"
                f"📊 **Profit:** **+{current_pips} Pips 🎉**\n"
                f"⏱ **Duration:** {duration_str}\n"
                f"───────────────────\n"
                f"💎 `#{ticker.upper()}` | **{BRAND_TAG}**"
            )
            send_telegram(tp_msg)
            return "Partial TP Alert Sent", 200

        # ----------------------------------------------------
        # 2. FULL CLOSE / SL HIT / FINAL EXIT
        # ----------------------------------------------------
        is_sl_hit = any(sl_term in comment for sl_term in ["SL", "STOP LOSS", "STOPLOSS", "STOP"])
        is_close = position == "flat" or (prev_position in ["long", "short"] and position != prev_position) or is_sl_hit

        if is_close:
            if is_sl_hit and current_pips > 0:
                current_pips = -abs(current_pips)

            if is_sl_hit or current_pips < 0:
                close_msg = (
                    f"🛑 **STOP LOSS HIT** 🛑\n"
                    f"───────────────────\n"
                    f"📌 **Symbol:** `#{ticker.upper()}`\n"
                    f"💵 **Exit Price:** ${price:.2f}\n"
                    f"📉 **Result:** **{current_pips} Pips Loss 🛑**\n"
                    f"⏱ **Duration:** {duration_str}\n"
                    f"───────────────────\n"
                    f"🛡 `#{ticker.upper()}` | **{BRAND_TAG}**"
                )
            elif any(t in comment for t in ["TP", "TARGET", "PROFIT"]) or current_pips > 0:
                close_msg = (
                    f"🔥 **FINAL TARGET HIT** 🔥\n"
                    f"───────────────────\n"
                    f"🎯 **Status:** **{tp_label} HIT**\n"
                    f"💵 **Price:** ${price:.2f}\n"
                    f"📊 **Profit:** **+{current_pips} Pips 🎉**\n"
                    f"⏱ **Duration:** {duration_str}\n"
                    f"───────────────────\n"
                    f"💎 `#{ticker.upper()}` | **{BRAND_TAG}**"
                )
            else:
                close_msg = (
                    f"🟢 **TRADE CLOSED** 🟢\n"
                    f"───────────────────\n"
                    f"📌 **Symbol:** `#{ticker.upper()}`\n"
                    f"💵 **Exit Price:** ${price:.2f}\n"
                    f"⚖️ **Result:** **0 Pips (Break Even)**\n"
                    f"⏱ **Duration:** {duration_str}\n"
                    f"───────────────────\n"
                    f"🛡 `#{ticker.upper()}` | **{BRAND_TAG}**"
                )

            send_telegram(close_msg)

            if position == "flat":
                memory.pop(ticker, None)
                save_memory(memory)
                return "Close alert processed", 200

        # ----------------------------------------------------
        # 3. NEW SIGNAL OPEN (WITH CALCULATED TP & SL)
        # ----------------------------------------------------
        new_action = "BUY" if position == "long" or "buy" in raw_action else "SELL"

        memory[ticker] = {
            'action': new_action,
            'entry_price': price,
            'timestamp': time.time()
        }
        save_memory(memory)

        # Calculate TP / SL Levels for Gold/Forex
        is_gold = "XAU" in ticker.upper() or "GOLD" in ticker.upper()
        multiplier = 0.10 if is_gold else 0.0001

        if new_action == "BUY":
            tp1_val = price + (100 * multiplier)
            tp2_val = price + (250 * multiplier)
            tp3_val = price + (450 * multiplier)
            tp4_val = price + (700 * multiplier)
            sl_val = price - (100 * multiplier)
        else:  # SELL
            tp1_val = price - (100 * multiplier)
            tp2_val = price - (250 * multiplier)
            tp3_val = price - (450 * multiplier)
            tp4_val = price - (700 * multiplier)
            sl_val = price + (100 * multiplier)

        signal_msg = (
            f"⚡️ **NEW TRADE SIGNAL** ⚡️\n"
            f"───────────────────\n"
            f"📌 **Symbol:** `#{ticker.upper()}`\n"
            f"📈 **Action:** **{new_action}**\n"
            f"💵 **Entry Price:** ${price:.2f}\n"
            f"───────────────────\n"
            f"🎯 **TP1:** ${tp1_val:.2f} (+100 Pips)\n"
            f"🎯 **TP2:** ${tp2_val:.2f} (+250 Pips)\n"
            f"🎯 **TP3:** ${tp3_val:.2f} (+450 Pips)\n"
            f"🎯 **TP4:** ${tp4_val:.2f} (+700 Pips)\n"
            f"🛑 **SL:** ${sl_val:.2f} (-100 Pips)\n"
            f"───────────────────\n"
            f"💎 `#{ticker.upper()}` | **{BRAND_TAG}**"
        )
        send_telegram(signal_msg)
        return "OK", 200

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return f"Error: {e}", 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
