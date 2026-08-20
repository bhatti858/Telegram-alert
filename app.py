import json
import os
import time
from datetime import datetime, timedelta, timezone

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ============================================================
# CONFIG
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv("8804297584:AAH3J1NTc4VhRS3ZQluDJZR7-K0grTrbOEg", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
BRAND_TAG = os.getenv("BRAND_TAG", "@bhatti3273")

# Secret for Render Cron Job
CRON_SECRET = os.getenv("CRON_SECRET", "")

MEMORY_FILE = "trade_memory.json"
HISTORY_FILE = "trade_history.json"


# ============================================================
# SETTINGS
# ============================================================

GOLD_TP_PIPS = [100, 250, 450, 700]
GOLD_SL_PIPS = 100

FOREX_TP_PIPS = [100, 250, 450, 700]
FOREX_SL_PIPS = 100


# ============================================================
# JSON STORAGE
# ============================================================

def load_json(filename, default):

    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        print(f"[LOAD ERROR] {filename}: {e}")
        return default


def save_json(filename, data):

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=2,
                ensure_ascii=False
            )

        return True

    except Exception as e:
        print(f"[SAVE ERROR] {filename}: {e}")
        return False


def load_memory():
    return load_json(MEMORY_FILE, {})


def save_memory(data):
    return save_json(MEMORY_FILE, data)


def load_history():
    return load_json(HISTORY_FILE, [])


def save_history(data):
    return save_json(HISTORY_FILE, data)


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    if not TELEGRAM_BOT_TOKEN:
        print("[TELEGRAM ERROR] Bot token missing")
        return False

    if not TELEGRAM_CHAT_ID:
        print("[TELEGRAM ERROR] Chat ID missing")
        return False

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=20
        )

        print(
            "[TELEGRAM]",
            response.status_code,
            response.text
        )

        return response.status_code == 200

    except Exception as e:

        print("[TELEGRAM ERROR]", e)

        return False


# ============================================================
# SYMBOL / PIP
# ============================================================

def is_gold(symbol):

    symbol = str(symbol).upper()

    return (
        "XAU" in symbol
        or "GOLD" in symbol
    )


def pip_size(symbol):

    symbol = str(symbol).upper()

    if is_gold(symbol):
        return 0.10

    if "JPY" in symbol:
        return 0.01

    return 0.0001


# ============================================================
# PIPS CALCULATION
# ============================================================

def calculate_pips(
    symbol,
    entry_price,
    exit_price,
    action
):

    size = pip_size(symbol)

    if action.upper() == "BUY":
        difference = exit_price - entry_price

    else:
        difference = entry_price - exit_price

    return round(
        difference / size
    )


# ============================================================
# DOLLAR PRICE MOVE
# ============================================================

def calculate_dollar_move(
    entry_price,
    exit_price,
    action
):

    if action.upper() == "BUY":
        move = exit_price - entry_price

    else:
        move = entry_price - exit_price

    return abs(move)


# ============================================================
# TP / SL LEVELS
# ============================================================

def calculate_levels(
    symbol,
    entry_price,
    action
):

    if is_gold(symbol):

        tp_pips = GOLD_TP_PIPS
        sl_pips = GOLD_SL_PIPS

    else:

        tp_pips = FOREX_TP_PIPS
        sl_pips = FOREX_SL_PIPS

    size = pip_size(symbol)

    if action.upper() == "BUY":

        tp1 = entry_price + (
            tp_pips[0] * size
        )

        tp2 = entry_price + (
            tp_pips[1] * size
        )

        tp3 = entry_price + (
            tp_pips[2] * size
        )

        tp4 = entry_price + (
            tp_pips[3] * size
        )

        sl = entry_price - (
            sl_pips * size
        )

    else:

        tp1 = entry_price - (
            tp_pips[0] * size
        )

        tp2 = entry_price - (
            tp_pips[1] * size
        )

        tp3 = entry_price - (
            tp_pips[2] * size
        )

        tp4 = entry_price - (
            tp_pips[3] * size
        )

        sl = entry_price + (
            sl_pips * size
        )

    return {
        "tp1": round(tp1, 5),
        "tp2": round(tp2, 5),
        "tp3": round(tp3, 5),
        "tp4": round(tp4, 5),
        "sl": round(sl, 5)
    }


# ============================================================
# CREATE TRADE
# ============================================================

def create_trade(
    symbol,
    action,
    entry_price
):

    levels = calculate_levels(
        symbol,
        entry_price,
        action
    )

    return {

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

        "timestamp": time.time(),

        "status": "OPEN"
    }


# ============================================================
# NEW SIGNAL ALERT
# ============================================================

def send_new_signal(trade):

    symbol = trade["symbol"]
    action = trade["action"]
    entry = trade["entry_price"]

    message = (
        "⚡ *NEW TRADE SIGNAL* ⚡\n"
        "───────────────────\n"
        f"📌 *Symbol:* `#{symbol}`\n"
        f"📈 *Action:* *{action}*\n"
        f"💵 *Entry Price:* `${entry:.2f}`\n"
        "───────────────────\n"
        f"🎯 *TP1:* `${trade['tp1']:.2f}` (+100 Pips)\n"
        f"🎯 *TP2:* `${trade['tp2']:.2f}` (+250 Pips)\n"
        f"🎯 *TP3:* `${trade['tp3']:.2f}` (+450 Pips)\n"
        f"🎯 *TP4:* `${trade['tp4']:.2f}` (+700 Pips)\n"
        f"🛑 *SL:* `${trade['sl']:.2f}` (-100 Pips)\n"
        "───────────────────\n"
        f"💎 `{BRAND_TAG}`"
    )

    return send_telegram(message)


# ============================================================
# TP ALERT
# ============================================================

def send_tp_alert(
    trade,
    tp_number,
    price
):

    symbol = trade["symbol"]
    action = trade["action"]

    entry = float(
        trade["entry_price"]
    )

    price = float(price)

    pips = calculate_pips(
        symbol,
        entry,
        price,
        action
    )

    pips = abs(pips)

    dollar_move = calculate_dollar_move(
        entry,
        price,
        action
    )

    # TP number mil gaya
    if tp_number in [1, 2, 3, 4]:

        title = (
            f"🔥 *TP{tp_number} HIT* 🔥"
        )

    # TP number nahi mila
    else:

        title = "🔥 *TP HIT* 🔥"

    message = (
        f"{title}\n"
        "───────────────────\n"
        f"📌 *#{symbol}*\n"
        f"📊 *Profit:* +{pips} Pips\n"
        f"💵 *Move:* +${dollar_move:.2f}\n"
        "───────────────────\n"
        f"💎 `{BRAND_TAG}`"
    )

    return send_telegram(message)


# ============================================================
# SL ALERT
# ============================================================

def send_sl_alert(
    trade,
    price
):

    symbol = trade["symbol"]
    action = trade["action"]
    entry = trade["entry_price"]

    pips = calculate_pips(
        symbol,
        entry,
        price,
        action
    )

    pips = -abs(pips)

    move = abs(
        price - entry
    )

    message = (
        "🛑 *STOP LOSS HIT* 🛑\n"
        "───────────────────\n"
        f"📌 *#{symbol}*\n"
        f"📉 *Loss:* {pips} Pips\n"
        f"💵 *Move:* -${move:.2f}\n"
        "───────────────────\n"
        f"🛡 `{BRAND_TAG}`"
    )

    return send_telegram(message)


# ============================================================
# TP DETECTION
# ============================================================

def detect_tp(comment):

    comment = str(
        comment or ""
    ).upper()

    if (
        "TP4" in comment
        or "TARGET 4" in comment
        or "TARGET4" in comment
        or "TP 4" in comment
        or "TAKE PROFIT 4" in comment
    ):
        return 4

    if (
        "TP3" in comment
        or "TARGET 3" in comment
        or "TARGET3" in comment
        or "TP 3" in comment
        or "TAKE PROFIT 3" in comment
    ):
        return 3

    if (
        "TP2" in comment
        or "TARGET 2" in comment
        or "TARGET2" in comment
        or "TP 2" in comment
        or "TAKE PROFIT 2" in comment
    ):
        return 2

    if (
        "TP1" in comment
        or "TARGET 1" in comment
        or "TARGET1" in comment
        or "TP 1" in comment
        or "TAKE PROFIT 1" in comment
    ):
        return 1

    # Generic TP
    if (
        "TP" in comment
        or "TARGET" in comment
        or "TAKE PROFIT" in comment
        or "PROFIT" in comment
    ):
        return None

    return None


# ============================================================
# SL DETECTION
# ============================================================

def detect_sl(comment):

    comment = str(
        comment or ""
    ).upper()

    terms = [
        "STOP LOSS",
        "STOPLOSS",
        "SL HIT",
        "SL",
        "STOP"
    ]

    return any(
        term in comment
        for term in terms
    )


# ============================================================
# SAVE CLOSED TRADE
# ============================================================

def save_closed_trade(
    trade,
    exit_price,
    result
):

    history = load_history()

    pips = calculate_pips(
        trade["symbol"],
        trade["entry_price"],
        exit_price,
        trade["action"]
    )

    if result == "SL":

        pips = -abs(pips)

    else:

        pips = abs(pips)

    now_utc = datetime.now(
        timezone.utc
    )

    record = {

        "date": now_utc.strftime(
            "%Y-%m-%d"
        ),

        "time": now_utc.strftime(
            "%H:%M:%S"
        ),

        "symbol": trade["symbol"],

        "action": trade["action"],

        "entry_price": trade["entry_price"],

        "exit_price": exit_price,

        "result": result,

        "pips": pips,

        "tp1_hit": trade.get(
            "tp1_hit",
            False
        ),

        "tp2_hit": trade.get(
            "tp2_hit",
            False
        ),

        "tp3_hit": trade.get(
            "tp3_hit",
            False
        ),

        "tp4_hit": trade.get(
            "tp4_hit",
            False
        ),

        "duration_seconds": int(
            time.time()
            - trade.get(
                "timestamp",
                time.time()
            )
        )
    }

    history.append(record)

    save_history(history)

    return record


# ============================================================
# WEEKLY REPORT
# ============================================================

def generate_weekly_report():

    history = load_history()

    # --------------------------------------------------------
    # UAE CURRENT TIME
    #
    # Python standard library:
    # UAE = UTC + 4
    # --------------------------------------------------------

    now_utc = datetime.now(
        timezone.utc
    )

    uae_now = (
        now_utc
        + timedelta(hours=4)
    )

    # Previous completed week:
    #
    # Monday 00:00
    # through Sunday 23:59
    #
    current_monday = (
        uae_now.date()
        - timedelta(
            days=uae_now.weekday()
        )
    )

    previous_monday = (
        current_monday
        - timedelta(days=7)
    )

    previous_sunday = (
        current_monday
        - timedelta(days=1)
    )

    weekly = []

    for trade in history:

        try:

            trade_date = datetime.strptime(
                trade["date"],
                "%Y-%m-%d"
            ).date()

            if (
                previous_monday
                <= trade_date
                <= previous_sunday
            ):

                weekly.append(
                    trade
                )

        except Exception:
            continue

    # --------------------------------------------------------
    # NO TRADES
    # --------------------------------------------------------

    if not weekly:

        return (
            "📊 *WEEKLY TRADING REPORT*\n"
            "───────────────────\n"
            f"📅 *Week:* "
            f"{previous_monday.strftime('%d %b')} - "
            f"{previous_sunday.strftime('%d %b %Y')}\n\n"
            "📈 *Total Trades:* 0\n"
            "No completed trades this week.\n"
            "───────────────────\n"
            f"💎 `{BRAND_TAG}`"
        )

    # --------------------------------------------------------
    # STATS
    # --------------------------------------------------------

    total = len(weekly)

    wins = 0
    losses = 0

    tp1 = 0
    tp2 = 0
    tp3 = 0
    tp4 = 0

    sl = 0

    net_pips = 0

    for trade in weekly:

        result = str(
            trade.get(
                "result",
                ""
            )
        ).upper()

        pips = float(
            trade.get(
                "pips",
                0
            )
        )

        net_pips += pips

        if result.startswith("TP"):
            wins += 1

        elif result == "SL":
            losses += 1

        if trade.get("tp1_hit"):
            tp1 += 1

        if trade.get("tp2_hit"):
            tp2 += 1

        if trade.get("tp3_hit"):
            tp3 += 1

        if trade.get("tp4_hit"):
            tp4 += 1

        if result == "SL":
            sl += 1

    win_rate = (
        (wins / total) * 100
        if total
        else 0
    )

    best = max(
        weekly,
        key=lambda x: float(
            x.get("pips", 0)
        )
    )

    worst = min(
        weekly,
        key=lambda x: float(
            x.get("pips", 0)
        )
    )

    net_sign = (
        "+"
        if net_pips >= 0
        else ""
    )

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    report = (
        "📊 *WEEKLY TRADING REPORT*\n"
        "───────────────────\n"

        f"📅 *Week:* "
        f"{previous_monday.strftime('%d %b')} - "
        f"{previous_sunday.strftime('%d %b %Y')}\n\n"

        f"📈 *Total Trades:* {total}\n"
        f"✅ *Wins:* {wins}\n"
        f"❌ *Losses:* {losses}\n"
        f"📊 *Win Rate:* {win_rate:.1f}%\n\n"

        f"🎯 *TP1 Hits:* {tp1}\n"
        f"🎯 *TP2 Hits:* {tp2}\n"
        f"🎯 *TP3 Hits:* {tp3}\n"
        f"🎯 *TP4 Hits:* {tp4}\n"
        f"🛑 *SL Hits:* {sl}\n\n"

        f"💰 *Net Pips:* "
        f"{net_sign}{net_pips:.0f}\n\n"

        f"🥇 *Best Trade:* "
        f"#{best['symbol']} "
        f"{best['action']} "
        f"{float(best['pips']):+.0f} Pips\n"

        f"📉 *Worst Trade:* "
        f"#{worst['symbol']} "
        f"{worst['action']} "
        f"{float(worst['pips']):+.0f} Pips\n"

        "───────────────────\n"
        f"💎 `{BRAND_TAG}`"
    )

    return report


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return jsonify({
        "status": "online",
        "service": "TradingView Telegram Bot",
        "brand": BRAND_TAG
    })


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status": "healthy",

        "telegram_configured": bool(
            TELEGRAM_BOT_TOKEN
        ),

        "chat_configured": bool(
            TELEGRAM_CHAT_ID
        )
    })


# ============================================================
# TELEGRAM TEST
# ============================================================

@app.route("/test-telegram")
def test_telegram():

    success = send_telegram(
        "✅ *Telegram Test Successful!*\n\n"
        "TradingView Telegram bot is working."
    )

    return jsonify({
        "success": success
    })


# ============================================================
# TEST WEEKLY REPORT
# ============================================================

@app.route("/test-weekly-report")
def test_weekly_report():

    report = generate_weekly_report()

    success = send_telegram(
        report
    )

    return jsonify({

        "success": success,

        "report": report
    })


# ============================================================
# CRON WEEKLY REPORT
# ============================================================

@app.route("/weekly-report")
def weekly_report():

    # --------------------------------------------------------
    # SECURITY
    # --------------------------------------------------------

    supplied_secret = request.args.get(
        "secret",
        ""
    )

    if CRON_SECRET:

        if supplied_secret != CRON_SECRET:

            return jsonify({
                "error": "Unauthorized"
            }), 401

    # --------------------------------------------------------
    # GENERATE REPORT
    # --------------------------------------------------------

    report = generate_weekly_report()

    # --------------------------------------------------------
    # SEND TELEGRAM
    # --------------------------------------------------------

    success = send_telegram(
        report
    )

    if not success:

        return jsonify({
            "success": False,
            "error": "Telegram send failed"
        }), 500

    return jsonify({

        "success": True,

        "message": (
            "Weekly report sent successfully"
        ),

        "timezone": "Asia/Dubai",

        "schedule": (
            "Every Saturday 03:00 AM UAE"
        )
    })


# ============================================================
# HISTORY
# ============================================================

@app.route("/history")
def history():

    return jsonify(
        load_history()
    )


# ============================================================
# MEMORY
# ============================================================

@app.route("/memory")
def memory():

    return jsonify(
        load_memory()
    )


# ============================================================
# TRADINGVIEW WEBHOOK
# ============================================================

@app.route(
    "/webhook",
    methods=["GET", "POST"]
)
def webhook():

    if request.method == "GET":

        return jsonify({
            "status": "Webhook Active"
        })

    try:

        data = request.get_json(
            silent=True
        )

        if not data:

            return jsonify({
                "error": "No JSON received"
            }), 400

        print(
            "\n========== WEBHOOK =========="
        )

        print(
            json.dumps(
                data,
                indent=2
            )
        )

        print(
            "=============================\n"
        )

        # ----------------------------------------------------
        # SYMBOL
        # ----------------------------------------------------

        ticker = str(
            data.get(
                "ticker",
                data.get(
                    "symbol",
                    "XAUUSD"
                )
            )
        ).upper()

        # ----------------------------------------------------
        # PRICE
        # ----------------------------------------------------

        try:

            price = float(
                data.get(
                    "price",
                    data.get(
                        "close",
                        0
                    )
                )
            )

        except Exception:

            price = 0

        if price <= 0:

            return jsonify({
                "error": "Invalid price"
            }), 400

        # ----------------------------------------------------
        # ACTION
        # ----------------------------------------------------

        action_raw = str(
            data.get(
                "action",
                ""
            )
        ).lower()

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

        comment = str(
            data.get(
                "comment",
                ""
            )
        )

        # ----------------------------------------------------
        # MEMORY
        # ----------------------------------------------------

        memory = load_memory()

        existing_trade = memory.get(
            ticker
        )

        # ----------------------------------------------------
        # ACTION
        # ----------------------------------------------------

        if (
            "buy" in action_raw
            or position == "long"
        ):

            action = "BUY"

        elif (
            "sell" in action_raw
            or position == "short"
        ):

            action = "SELL"

        elif prev_position == "long":

            action = "BUY"

        elif prev_position == "short":

            action = "SELL"

        else:

            action = "BUY"

        # ====================================================
        # SL
        # ====================================================

        if existing_trade and detect_sl(
            comment
        ):

            if not existing_trade.get(
                "sl_hit",
                False
            ):

                existing_trade[
                    "sl_hit"
                ] = True

                existing_trade[
                    "status"
                ] = "CLOSED"

                send_sl_alert(
                    existing_trade,
                    price
                )

                save_closed_trade(
                    existing_trade,
                    price,
                    "SL"
                )

                memory.pop(
                    ticker,
                    None
                )

                save_memory(
                    memory
                )

            return jsonify({
                "status": "SL processed"
            })

        # ====================================================
        # TP
        # ====================================================

        if existing_trade:

            tp_number = detect_tp(
                comment
            )

            comment_upper = comment.upper()

            is_tp = (
                tp_number is not None
                or "TP" in comment_upper
                or "TARGET" in comment_upper
                or "TAKE PROFIT"
                in comment_upper
                or "PROFIT"
                in comment_upper
            )

            if is_tp:

                # --------------------------------------------
                # Known TP
                # --------------------------------------------

                if tp_number in [1, 2, 3, 4]:

                    key = (
                        f"tp{tp_number}_hit"
                    )

                    # Prevent duplicate
                    # TP alerts

                    if not existing_trade.get(
                        key,
                        False
                    ):

                        existing_trade[
                            key
                        ] = True

                        send_tp_alert(
                            existing_trade,
                            tp_number,
                            price
                        )

                # --------------------------------------------
                # Unknown TP
                # --------------------------------------------

                else:

                    send_tp_alert(
                        existing_trade,
                        None,
                        price
                    )

                # --------------------------------------------
                # TP4 FINAL
                # --------------------------------------------

                if tp_number == 4:

                    existing_trade[
                        "status"
                    ] = "CLOSED"

                    save_closed_trade(
                        existing_trade,
                        price,
                        "TP4"
                    )

                    memory.pop(
                        ticker,
                        None
                    )

                save_memory(
                    memory
                )

                return jsonify({

                    "status": "TP processed",

                    "tp_number": tp_number
                })

        # ====================================================
        # FLAT / CLOSE
        # ====================================================

        if (
            existing_trade
            and position == "flat"
        ):

            existing_trade[
                "status"
            ] = "CLOSED"

            tp_number = detect_tp(
                comment
            )

            if tp_number:

                result = (
                    f"TP{tp_number}"
                )

            else:

                result = "CLOSE"

            save_closed_trade(
                existing_trade,
                price,
                result
            )

            memory.pop(
                ticker,
                None
            )

            save_memory(
                memory
            )

            return jsonify({
                "status": "Trade closed"
            })

        # ====================================================
        # NEW SIGNAL
        # ====================================================

        trade = create_trade(
            ticker,
            action,
            price
        )

        memory[ticker] = trade

        save_memory(
            memory
        )

        send_new_signal(
            trade
        )

        return jsonify({

            "status": "New signal processed",

            "symbol": ticker,

            "action": action,

            "entry": price,

            "tp1": trade["tp1"],
            "tp2": trade["tp2"],
            "tp3": trade["tp3"],
            "tp4": trade["tp4"],

            "sl": trade["sl"]
        })

    except Exception as e:

        print(
            "[WEBHOOK ERROR]",
            str(e)
        )

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
