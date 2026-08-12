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
# DATABASE SETUP (Pips Record Store Karne Ke Liye)
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
            pips INTEGER
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
    return "Bot & Weekly Reporter Active!", 200


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

        # ----------------------------------------------------
        # 1. AGAR TP YA SL HIT HOTA HAI
        # ----------------------------------------------------
        if any(target in comment for target in ["TP1", "TP2", "TP3", "TP4", "SL", "TAKE PROFIT", "STOP LOSS"]):
            pips = 0
            if "TP1" in comment:
                pips = 100
            elif "TP2" in comment:
                pips = 250
            elif "TP3" in comment:
                pips = 450
            elif "TP4" in comment:
                pips = 700
            elif "SL" in comment or "STOP LOSS" in comment:
                pips = -100

            # DB me save karein
            log_pips(ticker, comment, pips)

            status_icon = "🎯" if pips > 0 else "🛑"
            tp_sl_msg = (
                f"{status_icon} **TARGET UPDATE / EXIT** {status_icon}\n\n"
                f"📌 **Symbol:** {ticker}\n"
                f"⚡ **Event:** {comment}\n"
                f"💵 **Exit Price:** ${price:.2f}\n"
                f"📊 **Result:** {'+' if pips > 0 else ''}{pips} Pips"
            )
            send_telegram(tp_sl_msg)
            return "TP/SL alert sent", 200

        # ----------------------------------------------------
        # 2. FULL POSITION CLOSE (FLAT)
        # ----------------------------------------------------
        if position == "flat":
            close_message = (
                f"ℹ️ **POSITION CLOSED** ℹ️\n\n"
                f"📌 **Symbol:** {ticker}\n"
                f"💵 **Exit Price:** ${price:.2f}\n"
                f"📝 **Status:** Trade exited."
            )
            send_telegram(close_message)
            return "Closed alert sent", 200

        # ----------------------------------------------------
        # 3. POSITION REVERSAL (Buy closed & Sell opened)
        # ----------------------------------------------------
        if prev_position in ["long", "short"] and prev_position != position:
            prev_text = "BUY" if prev_position == "long" else "SELL"
            close_msg = (
                f"ℹ️ **PREVIOUS TRADE CLOSED** ℹ️\n\n"
                f"📌 **Symbol:** {ticker}\n"
                f"💵 **Exit Price:** ${price:.2f}\n"
                f"📝 **Status:** {prev_text} closed due to signal reversal."
            )
            send_telegram(close_msg)

        # ----------------------------------------------------
        # 4. NEW TRADE SIGNAL (BUY / SELL)
        # ----------------------------------------------------
        action = "BUY" if position == "long" or "buy" in raw_action else "SELL"

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
        else:
            sl_price = price + (sl_pips * pip_value)
            tp1_price = price - (tp1_pips * pip_value)
            tp2_price = price - (tp2_pips * pip_value)
            tp3_price = price - (tp3_pips * pip_value)
            tp4_price = price - (tp4_pips * pip_value)

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

        send_telegram(message)
        return "OK", 200

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return f"Error: {e}", 400


# ----------------------------------------------------
# 5. WEEKLY REPORT ROUTE
# ----------------------------------------------------
@app.route('/weekly-report', methods=['GET'])
def weekly_report():
    try:
        conn = sqlite3.connect('pips_data.db')
        cursor = conn.cursor()

        # Pichle 7 dino ka data extract karna
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
