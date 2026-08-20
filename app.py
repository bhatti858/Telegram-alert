import json
import os
import time
import threading
from datetime import datetime, timedelta

from flask import Flask, request
import requests
import MetaTrader5 as mt5


app = Flask(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

# IMPORTANT:
# Do NOT put your real Telegram token directly in this file.
# Set it as an environment variable instead.

TELEGRAM_BOT_TOKEN = os.getenv("8804297584:AAH3J1NTc4VhRS3ZQluDJZR7-K0grTrbOEg", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1004481939466")

BRAND_TAG = "@bhatti3273"

MEMORY_FILE = "trade_memory.json"
HISTORY_FILE = "trade_history.json"

# Weekly report day/time
# Monday = 0
# Sunday = 6
REPORT_DAY = 6
REPORT_HOUR = 23
REPORT_MINUTE = 0

# How often MT5 price is checked
PRICE_CHECK_INTERVAL = 1.0

# ============================================================
# TP/SL SETTINGS
# ============================================================

# Gold:
# 100 pips = $10
# 250 pips = $25
# 450 pips = $45
# 700 pips = $70

GOLD_TP_PIPS = [100, 250, 450, 700]
GOLD_SL_PIPS = 100

# Forex default
FOREX_TP_PIPS = [100, 250, 450, 700]
FOREX_SL_PIPS = 100


# ============================================================
# FILE HELPERS
# ============================================================

def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[FILE ERROR] {filename}: {e}")
        return default


def save_json(filename, data):
    try:
        temp_file = filename + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        os.replace(temp_file, filename)

    except Exception as e:
        print(f"[FILE SAVE ERROR] {filename}: {e}")


def load_memory():
    return load_json(MEMORY_FILE, {})


def save_memory(data):
    save_json(MEMORY_FILE, data)


def load_history():
    return load_json(HISTORY_FILE, [])


def save_history(data):
    save_json(HISTORY_FILE, data)


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN:
        print("[TELEGRAM ERROR] TELEGRAM_BOT_TOKEN is not configured.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=15
        )

        if response.status_code != 200:
            print("[TELEGRAM ERROR]", response.text)
            return False

        return True

    except Exception as e:
        print("[TELEGRAM ERROR]", e)
        return False


# ============================================================
# MT5
# ============================================================

def connect_mt5():
    try:
        if mt5.initialize():
            print("[MT5] Connected successfully.")
            return True

        print("[MT5 ERROR]", mt5.last_error())
        return False

    except Exception as e:
        print("[MT5 ERROR]", e)
        return False


def get_mt5_price(symbol):
    """
    Gets current bid/ask from MT5.

    For BUY positions:
        SL/TP are generally checked using BID.

    For SELL positions:
        SL/TP are generally checked using ASK.
    """

    try:
        tick = mt5.symbol_info_tick(symbol)

        if tick is None:
            # Try to select the symbol
            if not mt5.symbol_select(symbol, True):
                print(f"[MT5] Symbol unavailable: {symbol}")
                return None

            tick = mt5.symbol_info_tick(symbol)

        if tick is None:
            return None

        return {
            "bid": float(tick.bid),
            "ask": float(tick.ask),
            "time": int(tick.time)
        }

    except Exception as e:
        print(f"[MT5 PRICE ERROR] {symbol}: {e}")
        return None


# ============================================================
# PIP CALCULATION
# ============================================================

def is_gold(symbol):
    symbol_upper = symbol.upper()

    return (
        "XAU" in symbol_upper
        or "GOLD" in symbol_upper
    )


def pip_size(symbol):
    """
    Gold:
        1 pip = 0.10

    Forex:
        1 pip = 0.0001

    JPY:
        1 pip = 0.01
    """

    symbol_upper = symbol.upper()

    if is_gold(symbol):
        return 0.10

    if "JPY" in symbol_upper:
        return 0.01

    return 0.0001


def calculate_pips(symbol, entry_price, exit_price, trade_type):
    size = pip_size(symbol)

    if trade_type.upper() == "BUY":
        difference = exit_price - entry_price
    else:
        difference = entry_price - exit_price

    return round(difference / size)


# ============================================================
# DURATION
# ============================================================

def format_duration(start_timestamp):
    if not start_timestamp:
        return "N/A"

    try:
        seconds = max(
            0,
            int(time.time() - float(start_timestamp))
        )

        if seconds < 60:
            return "1 Min"

        minutes = seconds // 60

        if minutes < 60:
            return f"{minutes} Mins"

        hours = minutes // 60
        mins = minutes % 60

        return f"{hours}h {mins}m"

    except Exception:
        return "N/A"


# ============================================================
# PRICE LEVELS
# ============================================================

def calculate_levels(symbol, entry_price, action):

    if is_gold(symbol):
        tp_pips = GOLD_TP_PIPS
        sl_pips = GOLD_SL_PIPS
    else:
        tp_pips = FOREX_TP_PIPS
        sl_pips = FOREX_SL_PIPS

    size = pip_size(symbol)

    action = action.upper()

    if action == "BUY":

        tp1 = entry_price + tp_pips[0] * size
        tp2 = entry_price + tp_pips[1] * size
        tp3 = entry_price + tp_pips[2] * size
        tp4 = entry_price + tp_pips[3] * size

        sl = entry_price - sl_pips * size

    else:

        tp1 = entry_price - tp_pips[0] * size
        tp2 = entry_price - tp_pips[1] * size
        tp3 = entry_price - tp_pips[2] * size
        tp4 = entry_price - tp_pips[3] * size

        sl = entry_price + sl_pips * size

    return {
        "tp1": round(tp1, 5),
        "tp2": round(tp2, 5),
        "tp3": round(tp3, 5),
        "tp4": round(tp4, 5),
        "sl": round(sl, 5)
    }


# ============================================================
# NEW TRADE
# ============================================================

def create_trade(symbol, action, entry_price):

    levels = calculate_levels(
        symbol,
        entry_price,
        action
    )

    trade = {
        "symbol": symbol.upper(),
        "action": action.upper(),

        "entry_price": entry_price,

        "tp1": levels["tp1"],
        "tp2": levels["tp2"],
        "tp3": levels["tp3"],
        "tp4": levels["tp4"],

        "sl": levels["sl"],

        "tp1_hit": False,
        "tp2_hit": False,
        "tp3_hit": False,
        "tp4_hit": False,

        "sl_hit": False,

        "tp1_time": None,
        "tp2_time": None,
        "tp3_time": None,
        "tp4_time": None,

        "timestamp": time.time(),

        "status": "OPEN"
    }

    return trade


# ============================================================
# TP ALERT
# ============================================================

def send_tp_alert(trade, tp_number, current_price):

    symbol = trade["symbol"]
    action = trade["action"]
    entry = trade["entry_price"]

    pip_profit = calculate_pips(
        symbol,
        entry,
        current_price,
        action
    )

    duration = format_duration(
        trade.get("timestamp")
    )

    tp_price = trade[f"tp{tp_number}"]

    message = (
        f"🔥 *TARGET SMASHED!* 🔥\n"
        f"───────────────────\n"
        f"🎯 *Status:* *TP{tp_number} HIT*\n"
        f"📌 *Symbol:* `#{symbol}`\n"
        f"📈 *Direction:* *{action}*\n"
        f"💵 *Price:* `${current_price:.2f}`\n"
        f"🎯 *Target:* `${tp_price:.2f}`\n"
        f"📊 *Profit:* *+{pip_profit} Pips* 🎉\n"
        f"⏱ *Duration:* {duration}\n"
        f"───────────────────\n"
        f"💎 `{BRAND_TAG}`"
    )

    return send_telegram(message)


# ============================================================
# SL ALERT
# ============================================================

def send_sl_alert(trade, current_price):

    symbol = trade["symbol"]
    action = trade["action"]
    entry = trade["entry_price"]

    pip_result = calculate_pips(
        symbol,
        entry,
        current_price,
        action
    )

    pip_result = -abs(pip_result)

    duration = format_duration(
        trade.get("timestamp")
    )

    message = (
        f"🛑 *STOP LOSS HIT* 🛑\n"
        f"───────────────────\n"
        f"📌 *Symbol:* `#{symbol}`\n"
        f"📈 *Direction:* *{action}*\n"
        f"💵 *Exit Price:* `${current_price:.2f}`\n"
        f"📉 *Result:* *{pip_result} Pips*\n"
        f"⏱ *Duration:* {duration}\n"
        f"───────────────────\n"
        f"🛡 `{BRAND_TAG}`"
    )

    return send_telegram(message)


# ============================================================
# TRADE HISTORY
# ============================================================

def add_closed_trade(trade, exit_price, result_type):

    history = load_history()

    action = trade["action"]
    symbol = trade["symbol"]
    entry = trade["entry_price"]

    pips = calculate_pips(
        symbol,
        entry,
        exit_price,
        action
    )

    if result_type == "SL":
        pips = -abs(pips)

    elif result_type == "TP":
        pips = abs(pips)

    record = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),

        "symbol": symbol,
        "action": action,

        "entry_price": entry,
        "exit_price": exit_price,

        "result": result_type,

        "pips": pips,

        "tp1_hit": trade.get("tp1_hit", False),
        "tp2_hit": trade.get("tp2_hit", False),
        "tp3_hit": trade.get("tp3_hit", False),
        "tp4_hit": trade.get("tp4_hit", False),

        "duration": format_duration(
            trade.get("timestamp")
        )
    }

    history.append(record)

    save_history(history)

    return record


# ============================================================
# TP/SL MONITOR
# ============================================================

def check_trade_price(symbol, trade):

    tick = get_mt5_price(symbol)

    if not tick:
        return

    action = trade["action"]

    # Important:
    # BUY position closes against BID.
    # SELL position closes against ASK.

    if action == "BUY":
        current_price = tick["bid"]
    else:
        current_price = tick["ask"]

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    if action == "BUY":

        # SL
        if (
            not trade.get("sl_hit", False)
            and current_price <= trade["sl"]
        ):

            trade["sl_hit"] = True
            trade["status"] = "CLOSED"
            trade["close_price"] = current_price
            trade["close_time"] = time.time()

            send_sl_alert(
                trade,
                current_price
            )

            add_closed_trade(
                trade,
                current_price,
                "SL"
            )

            return

        # TP1
        if (
            not trade.get("tp1_hit", False)
            and current_price >= trade["tp1"]
        ):

            trade["tp1_hit"] = True
            trade["tp1_time"] = time.time()

            send_tp_alert(
                trade,
                1,
                current_price
            )

        # TP2
        if (
            not trade.get("tp2_hit", False)
            and current_price >= trade["tp2"]
        ):

            trade["tp2_hit"] = True
            trade["tp2_time"] = time.time()

            send_tp_alert(
                trade,
                2,
                current_price
            )

        # TP3
        if (
            not trade.get("tp3_hit", False)
            and current_price >= trade["tp3"]
        ):

            trade["tp3_hit"] = True
            trade["tp3_time"] = time.time()

            send_tp_alert(
                trade,
                3,
                current_price
            )

        # TP4
        if (
            not trade.get("tp4_hit", False)
            and current_price >= trade["tp4"]
        ):

            trade["tp4_hit"] = True
            trade["tp4_time"] = time.time()

            send_tp_alert(
                trade,
                4,
                current_price
            )

            trade["status"] = "CLOSED"
            trade["close_price"] = current_price
            trade["close_time"] = time.time()

            add_closed_trade(
                trade,
                current_price,
                "TP4"
            )

            return

    # --------------------------------------------------------
    # SELL
    # --------------------------------------------------------

    else:

        # SL
        if (
            not trade.get("sl_hit", False)
            and current_price >= trade["sl"]
        ):

            trade["sl_hit"] = True
            trade["status"] = "CLOSED"
            trade["close_price"] = current_price
            trade["close_time"] = time.time()

            send_sl_alert(
                trade,
                current_price
            )

            add_closed_trade(
                trade,
                current_price,
                "SL"
            )

            return

        # TP1
        if (
            not trade.get("tp1_hit", False)
            and current_price <= trade["tp1"]
        ):

            trade["tp1_hit"] = True
            trade["tp1_time"] = time.time()

            send_tp_alert(
                trade,
                1,
                current_price
            )

        # TP2
        if (
            not trade.get("tp2_hit", False)
            and current_price <= trade["tp2"]
        ):

            trade["tp2_hit"] = True
            trade["tp2_time"] = time.time()

            send_tp_alert(
                trade,
                2,
                current_price
            )

        # TP3
        if (
            not trade.get("tp3_hit", False)
            and current_price <= trade["tp3"]
        ):

            trade["tp3_hit"] = True
            trade["tp3_time"] = time.time()

            send_tp_alert(
                trade,
                3,
                current_price
            )

        # TP4
        if (
            not trade.get("tp4_hit", False)
            and current_price <= trade["tp4"]
        ):

            trade["tp4_hit"] = True
            trade["tp4_time"] = time.time()

            send_tp_alert(
                trade,
                4,
                current_price
            )

            trade["status"] = "CLOSED"
            trade["close_price"] = current_price
            trade["close_time"] = time.time()

            add_closed_trade(
                trade,
                current_price,
                "TP4"
            )

            return


# ============================================================
# PRICE MONITOR THREAD
# ============================================================

def price_monitor():

    print("[MONITOR] Starting MT5 price monitor...")

    while True:

        try:

            if not mt5.terminal_info():

                print("[MONITOR] MT5 disconnected. Reconnecting...")

                connect_mt5()

            memory = load_memory()

            changed = False

            for symbol in list(memory.keys()):

                trade = memory.get(symbol)

                if not trade:
                    continue

                if trade.get("status") != "OPEN":
                    continue

                try:

                    check_trade_price(
                        symbol,
                        trade
                    )

                    if trade.get("status") == "CLOSED":
                        memory.pop(symbol, None)

                    changed = True

                except Exception as e:

                    print(
                        f"[MONITOR ERROR] "
                        f"{symbol}: {e}"
                    )

            if changed:
                save_memory(memory)

        except Exception as e:

            print(
                f"[MONITOR LOOP ERROR] {e}"
            )

        time.sleep(
            PRICE_CHECK_INTERVAL
        )


# ============================================================
# WEEKLY REPORT
# ============================================================

def get_week_start():

    today = datetime.now().date()

    return today - timedelta(
        days=today.weekday()
    )


def generate_weekly_report():

    history = load_history()

    if not history:
        return (
            "📊 *WEEKLY TRADING REPORT*\n\n"
            "No trades recorded this week."
        )

    week_start = get_week_start()

    week_end = week_start + timedelta(
        days=6
    )

    week_trades = []

    for trade in history:

        try:

            trade_date = datetime.strptime(
                trade["date"],
                "%Y-%m-%d"
            ).date()

            if week_start <= trade_date <= week_end:
                week_trades.append(trade)

        except Exception:
            continue

    if not week_trades:

        return (
            f"📊 *WEEKLY TRADING REPORT*\n"
            f"───────────────────\n"
            f"📅 {week_start} → {week_end}\n\n"
            f"No completed trades this week.\n"
            f"───────────────────\n"
            f"💎 `{BRAND_TAG}`"
        )

    total_trades = len(week_trades)

    wins = 0
    losses = 0

    tp1_count = 0
    tp2_count = 0
    tp3_count = 0
    tp4_count = 0
    sl_count = 0

    total_pips = 0

    for trade in week_trades:

        result = str(
            trade.get("result", "")
        ).upper()

        pips = float(
            trade.get("pips", 0)
        )

        total_pips += pips

        if result.startswith("TP"):
            wins += 1

        if result == "SL":
            losses += 1

        if trade.get("tp1_hit"):
            tp1_count += 1

        if trade.get("tp2_hit"):
            tp2_count += 1

        if trade.get("tp3_hit"):
            tp3_count += 1

        if trade.get("tp4_hit"):
            tp4_count += 1

        if trade.get("result") == "SL":
            sl_count += 1

    win_rate = (
        wins / total_trades * 100
        if total_trades
        else 0
    )

    best_trade = max(
        week_trades,
        key=lambda x: float(
            x.get("pips", 0)
        )
    )

    worst_trade = min(
        week_trades,
        key=lambda x: float(
            x.get("pips", 0)
        )
    )

    report = (
        f"📊 *WEEKLY TRADING REPORT*\n"
        f"───────────────────\n"
        f"📅 *Week:* "
        f"{week_start.strftime('%d %b')} - "
        f"{week_end.strftime('%d %b %Y')}\n\n"

        f"📈 *Total Trades:* {total_trades}\n"
        f"✅ *Wins:* {wins}\n"
        f"❌ *Losses:* {losses}\n"
        f"📊 *Win Rate:* {win_rate:.1f}%\n\n"

        f"🎯 *TP1:* {tp1_count}\n"
        f"🎯 *TP2:* {tp2_count}\n"
        f"🎯 *TP3:* {tp3_count}\n"
        f"🎯 *TP4:* {tp4_count}\n"
        f"🛑 *SL:* {sl_count}\n\n"

        f"💰 *Net Pips:* "
        f"{'+' if total_pips >= 0 else ''}"
        f"{total_pips:.0f}\n\n"

        f"🥇 *Best Trade:* "
        f"#{best_trade.get('symbol')} "
        f"{best_trade.get('action')} "
        f"+{float(best_trade.get('pips', 0)):.0f} Pips\n"

        f"📉 *Worst Trade:* "
        f"#{worst_trade.get('symbol')} "
        f"{worst_trade.get('action')} "
        f"{float(worst_trade.get('pips', 0)):.0f} Pips\n"

        f"───────────────────\n"
        f"💎 `{BRAND_TAG}`"
    )

    return report


# ============================================================
# WEEKLY REPORT SCHEDULER
# ============================================================

def weekly_report_scheduler():

    print("[REPORT] Weekly report scheduler started.")

    last_report_week = None

    while True:

        try:

            now = datetime.now()

            current_week = (
                now.isocalendar().year,
                now.isocalendar().week
            )

            if (
                now.weekday() == REPORT_DAY
                and now.hour == REPORT_HOUR
                and now.minute == REPORT_MINUTE
            ):

                if last_report_week != current_week:

                    print(
                        "[REPORT] Sending weekly report..."
                    )

                    report = generate_weekly_report()

                    send_telegram(report)

                    last_report_week = current_week

        except Exception as e:

            print(
                f"[REPORT ERROR] {e}"
            )

        time.sleep(30)


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return (
        f"Trading Bot Active for {BRAND_TAG}!",
        200
    )


# ============================================================
# TEST TELEGRAM
# ============================================================

@app.route("/test-telegram")
def test_telegram():

    success = send_telegram(
        "✅ *Telegram Test Successful!*\n\n"
        "Trading bot Telegram connection is working."
    )

    if success:
        return "Telegram test sent.", 200

    return "Telegram test failed.", 500


# ============================================================
# TEST WEEKLY REPORT
# ============================================================

@app.route("/test-weekly-report")
def test_weekly_report():

    report = generate_weekly_report()

    success = send_telegram(report)

    if success:
        return "Weekly report test sent.", 200

    return "Weekly report test failed.", 500


# ============================================================
# WEBHOOK
# ============================================================

@app.route(
    "/webhook",
    methods=["GET", "POST"]
)
def webhook():

    if request.method == "GET":
        return "Webhook Active!", 200

    try:

        data = request.get_json(
            silent=True
        )

        if not data:
            return "No JSON received", 400

        print(
            "[WEBHOOK RECEIVED]",
            json.dumps(
                data,
                indent=2
            )
        )

        ticker = str(
            data.get(
                "ticker",
                "XAUUSD"
            )
        ).upper()

        price = float(
            data.get(
                "price",
                0
            )
        )

        if price <= 0:
            return "Invalid price", 400

        position = str(
            data.get(
                "position",
                ""
            )
        ).lower()

        prev_position = str(
            data.get(
                "prev_position",
                ""
            )
        ).lower()

        raw_action = str(
            data.get(
                "action",
                ""
            )
        ).lower()

        comment = str(
            data.get(
                "comment",
                ""
            )
        ).upper()

        memory = load_memory()

        # ====================================================
        # DETERMINE ACTION
        # ====================================================

        if (
            position == "long"
            or "buy" in raw_action
        ):

            new_action = "BUY"

        elif (
            position == "short"
            or "sell" in raw_action
        ):

            new_action = "SELL"

        else:

            new_action = (
                "BUY"
                if prev_position == "long"
                else "SELL"
            )

        # ====================================================
        # CLOSE EVENT
        # ====================================================

        is_sl_hit = any(
            term in comment
            for term in [
                "SL",
                "STOP LOSS",
                "STOPLOSS",
                "STOP"
            ]
        )

        is_flat = (
            position == "flat"
        )

        position_changed = (
            prev_position
            in ["long", "short"]
            and
            position
            not in [
                prev_position,
                ""
            ]
        )

        is_close = (
            is_flat
            or position_changed
            or is_sl_hit
        )

        if is_close and ticker in memory:

            trade = memory[ticker]

            exit_price = price

            if is_sl_hit:

                trade["sl_hit"] = True
                trade["status"] = "CLOSED"

                send_sl_alert(
                    trade,
                    exit_price
                )

                add_closed_trade(
                    trade,
                    exit_price,
                    "SL"
                )

            else:

                # If TradingView explicitly tells us TP
                # we can record it too.
                if "TP4" in comment:
                    result = "TP4"

                elif "TP3" in comment:
                    result = "TP3"

                elif "TP2" in comment:
                    result = "TP2"

                elif "TP1" in comment:
                    result = "TP1"

                else:
                    result = "CLOSE"

                trade["status"] = "CLOSED"

                add_closed_trade(
                    trade,
                    exit_price,
                    result
                )

            memory.pop(
                ticker,
                None
            )

            save_memory(memory)

            return (
                "Close processed",
                200
            )

        # ====================================================
        # NEW SIGNAL
        # ====================================================

        # If same symbol already has an open trade,
        # replace it with the new signal.
        if ticker in memory:

            old_trade = memory[ticker]

            print(
                f"[NEW SIGNAL] Replacing existing "
                f"{ticker} trade."
            )

        trade = create_trade(
            ticker,
            new_action,
            price
        )

        memory[ticker] = trade

        save_memory(memory)

        # ====================================================
        # TELEGRAM NEW SIGNAL
        # ====================================================

        signal_message = (
            f"⚡ *NEW TRADE SIGNAL* ⚡\n"
            f"───────────────────\n"
            f"📌 *Symbol:* `#{ticker}`\n"
            f"📈 *Action:* *{new_action}*\n"
            f"💵 *Entry:* `${price:.2f}`\n"
            f"───────────────────\n"

            f"🎯 *TP1:* "
            f"${trade['tp1']:.2f} "
            f"(+100 Pips)\n"

            f"🎯 *TP2:* "
            f"${trade['tp2']:.2f} "
            f"(+250 Pips)\n"

            f"🎯 *TP3:* "
            f"${trade['tp3']:.2f} "
            f"(+450 Pips)\n"

            f"🎯 *TP4:* "
            f"${trade['tp4']:.2f} "
            f"(+700 Pips)\n"

            f"🛑 *SL:* "
            f"${trade['sl']:.2f} "
            f"(-100 Pips)\n"

            f"───────────────────\n"
            f"💎 `{BRAND_TAG}`"
        )

        send_telegram(
            signal_message
        )

        return "OK", 200

    except Exception as e:

        print(
            f"[WEBHOOK ERROR] {e}"
        )

        return (
            f"Error: {e}",
            400
        )


# ============================================================
# START BACKGROUND THREADS
# ============================================================

def start_background_services():

    # MT5 connection
    connect_mt5()

    # Price monitor
    monitor_thread = threading.Thread(
        target=price_monitor,
        daemon=True
    )

    monitor_thread.start()

    # Weekly report
    report_thread = threading.Thread(
        target=weekly_report_scheduler,
        daemon=True
    )

    report_thread.start()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "=========================================="
    )

    print(
        "TRADINGVIEW → FLASK → MT5 → TELEGRAM"
    )

    print(
        "=========================================="
    )

    start_background_services()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True
    )
