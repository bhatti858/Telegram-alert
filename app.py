import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request
import requests

app = Flask(__name__)

# ----------------------------------------------------
# TELEGRAM CREDENTIALS
# ----------------------------------------------------
TELEGRAM_BOT_TOKEN = "8804297584:AAHSSJ9VwCk3dIZlVvh3p6YjP0J5i0B5gi0"  # Yahan apna @BotFather token paste karein
TELEGRAM_CHAT_ID = "-1004481939466"         # Aapki Chat ID


# ----------------------------------------------------
# DATABASE SETUP
# ----------------------------------------------------
def init_db():
    conn = sqlite3.connect('pips_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ticker TEXT,
            event_type TEXT,
            pips REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_position (
            ticker TEXT PRIMARY KEY,
            action TEXT,
            entry_price REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def log_pips(ticker, event_type, pips):
    try:
        conn = sqlite3.connect('pips_data.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trade_logs (ticker, event_type, pips)
            VALUES (?, ?, ?)
        ''', (ticker, event_type, pips))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database Error: {e}")

def save_active_position(ticker, action, entry_price):
    try:
        conn = sqlite3.connect('pips_data.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO active_position (ticker, action, entry_price, timestamp)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (ticker, action, entry_price))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving active position: {e}")

def get_active_position(ticker):
    try:
        conn = sqlite3.connect('pips_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT action, entry_price FROM active_position WHERE ticker = ?', (ticker,))
        row = cursor.fetchone()
        conn.close()
        return row
    except Exception as e:
        print(f"Error fetching active position: {e}")
        return None

def clear_active_position(ticker):
    try:
        conn = sqlite3.connect('pips_data.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM active_position WHERE ticker = ?', (ticker,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error clearing active position: {e}")

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
    return "Bot with Duplicate Prevention & Custom Formatting Active!", 200


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
        comment = str(data.get('comment', '')).upper()
        position = str(data.get('position', '')).lower()
        prev_position = str(data.get('prev_position', '')).lower()
        raw_action = str(data.get('action', '')).lower()

        pip_value = 0.10  # XAUUSD Pip value

        active_trade = get_active_position(ticker)
        is_sl_hit = any(sl_term in comment for sl_term in ["SL", "STOP LOSS", "STOPLOSS"])

        # Determine incoming new action
        new_action = "BUY" if position == "long" or "buy" in raw_action else "SELL"

        # ----------------------------------------------------
        # 1. TRADE CLOSE / EXIT / SL HIT / REVERSAL
        # ----------------------------------------------------
        if position == "flat" or (prev_position in ["long", "short"] and prev_position != position) or is_sl_hit:
            if active_trade:
                act_action, entry_price = active_trade

                # Calculate Pips
                if act_action == "BUY":
                    pips = round((price - entry_price) / pip_value)
                else:  # SELL
                    pips = round((entry_price - price) / pip_value)

                log_pips(ticker, "CLOSED_TRADE", pips)
                clear_active_position(ticker)

                # Format Message Title
                if is_sl_hit or pips < 0:
                    status_title = "🛑 **STOPLOSS HIT** 🛑" if is_sl_hit else "🔴 **TRADE CLOSED** 🔴"
                    pnl_text = f"**{pips} Pips Loss** 🛑"
                elif pips > 0:
                    status_title = "🟢 **TRADE CLOSED** 🟢"
                    pnl_text = f"**+{pips} Pips Profit** 🎉"
                else:
                    status_title = "⚪ **TRADE CLOSED** ⚪"
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
                    return "Closed/SL alert sent", 200

                # Reversal tracking logic update
                active_trade = None

        # ----------------------------------------------------
        # 2. DUPLICATE CHECK (Same trade active ho toh skip karain)
        # ----------------------------------------------------
        if active_trade and active_trade[0] == new_action:
            return "Duplicate signal ignored", 200

        # ----------------------------------------------------
        # 3. NEW SIGNAL (BUY / SELL)
        # ----------------------------------------------------
        save_active_position(ticker, new_action, price)

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
            f"• Once in profit, activate Break Even at +3 pips\n"
            f"• Accept the stop loss if SL is hit - do not revenge trade"
        )

        send_telegram(message)
        return "OK", 200

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return f"Error: {e}", 400


# ----------------------------------------------------
# 4. WEEKLY REPORT ROUTE
# ----------------------------------------------------
@app.route('/weekly-report', methods=['GET'])
def weekly_report():
    try:
        conn = sqlite3.connect('pips_data.db')
        cursor = conn.cursor()

        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('SELECT pips FROM trade_logs WHERE timestamp >= ?', (seven_days_ago,))
        records = cursor.fetchall()
        conn.close()

        total_profit_pips = sum(r[0] for r in records if r[0] > 0)
        total_loss_pips = abs(sum(r[0] for r in records if r[0] < 0))
        net_pips = total_profit_pips - total_loss_pips

        report_message = (
            f"📊 **WEEKLY PERFORMANCE REPORT** 📊\n\n"
            f"🗓️ **Period:** Last 7 Days\n"
            f"📈 **Total Profit:** +{total_profit_pips} pips\n"
            f"📉 **Total Loss:** -{total_loss_pips} pips\n"
            f"───────────────────\n"
            f"⚖️ **NET P&L:** {'+' if net_pips >= 0 else ''}{net_pips} pips\n"
            f"🏆 **Status:** {'PROFITABLE WEEK 🎉' if net_pips >= 0 else 'LOSS WEEK ⚠️'}"
        )

        send_telegram(report_message)
        return "Weekly report sent successfully!", 200

    except Exception as e:
        return f"Error generating report: {e}", 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
