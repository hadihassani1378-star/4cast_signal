import os
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ===== تنظیمات =====
BOT1_TOKEN = os.getenv("BOT1_TOKEN", "PUT_SIGNAL_BOT_TOKEN_HERE")
BOT1_WEBHOOK_SECRET = os.getenv("BOT1_WEBHOOK_SECRET", "bot1secret123")

CHANNEL_1_ID = int(os.getenv("CHANNEL_1_ID", "-1001111111111"))
CHANNEL_2_ID = int(os.getenv("CHANNEL_2_ID", "-1002222222222"))

bot1 = telebot.TeleBot(BOT1_TOKEN)
app = Flask(__name__)

# برای ذخیره پاسخ‌های کاربر
user_state = {}   # chat_id → dict(data)


# ===== شروع =====
@bot1.message_handler(commands=['start'])
def bot1_start(message):
    chat_id = message.chat.id
    user_state[chat_id] = {}
    ask_symbol(message)


# ===== مراحل گرفتن اطلاعات =====
def ask_symbol(message):
    chat_id = message.chat.id
    markup = InlineKeyboardMarkup(row_width=2)
    symbols = ["XAUUSD", "EURUSD", "GBPUSD", "JPY", "BTCUSDT"]
    buttons = [InlineKeyboardButton(sym, callback_data=f"sym:{sym}") for sym in symbols]
    markup.add(*buttons)
    bot1.send_message(chat_id, "نماد رو انتخاب کن:", reply_markup=markup)


def ask_tp1(chat_id):
    msg = bot1.send_message(chat_id, "TP1 رو بفرست:")
    bot1.register_next_step_handler(msg, process_tp1)


def process_tp1(message):
    chat_id = message.chat.id
    user_state[chat_id]["tp1"] = message.text.strip()
    msg = bot1.send_message(chat_id, "TP2 رو بفرست:")
    bot1.register_next_step_handler(msg, process_tp2)


def process_tp2(message):
    chat_id = message.chat.id
    user_state[chat_id]["tp2"] = message.text.strip()
    msg = bot1.send_message(chat_id, "TP3 رو بفرست:")
    bot1.register_next_step_handler(msg, process_tp3)


def process_tp3(message):
    chat_id = message.chat.id
    user_state[chat_id]["tp3"] = message.text.strip()
    msg = bot1.send_message(chat_id, "Stop (SL) رو بفرست:")
    bot1.register_next_step_handler(msg, process_stop)


def process_stop(message):
    chat_id = message.chat.id
    user_state[chat_id]["stop"] = message.text.strip()

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Buy (Long)", callback_data="dir:buy"),
        InlineKeyboardButton("Sell (Short)", callback_data="dir:sell")
    )
    bot1.send_message(chat_id, "جهت رو انتخاب کن:", reply_markup=markup)


def ask_risk(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("High Risk", callback_data="risk:high"),
        InlineKeyboardButton("Low Risk", callback_data="risk:low")
    )
    bot1.send_message(chat_id, "ریسک رو انتخاب کن:", reply_markup=markup)


# ===== ساخت متن نهایی =====
def build_signal_text(data):
    direction_text = "BUY / LONG" if data["direction"] == "buy" else "SELL / SHORT"
    risk_text = "High Risk" if data["risk"] == "high" else "Low Risk"

    text = (
        f"📊 سیگنال جدید\n\n"
        f"🔹 Symbol: {data['symbol']}\n"
        f"🔹 Direction: {direction_text}\n"
        f"🔹 Risk: {risk_text}\n\n"
        f"🎯 Targets:\n"
        f"TP1 → {data['tp1']}\n"
        f"TP2 → {data['tp2']}\n"
        f"TP3 → {data['tp3']}\n\n"
        f"⛔ Stop Loss: {data['stop']}"
    )
    return text


# ===== انتخاب مقصد =====
def ask_destination(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("فقط همینجا", callback_data="dest:here"),
        InlineKeyboardButton("کانال ۱", callback_data="dest:ch1"),
        InlineKeyboardButton("کانال ۲", callback_data="dest:ch2"),
        InlineKeyboardButton("هردو کانال", callback_data="dest:both"),
    )
    bot1.send_message(chat_id, "سیگنال رو کجا بفرستم؟", reply_markup=markup)


# ===== هندل کال‌بک‌ها =====
@bot1.callback_query_handler(func=lambda c: True)
def callbacks(callback_query):
    data = callback_query.data
    chat_id = callback_query.message.chat.id

    if data.startswith("sym:"):
        user_state[chat_id]["symbol"] = data.split(":")[1]
        ask_tp1(chat_id)

    elif data.startswith("dir:"):
        user_state[chat_id]["direction"] = data.split(":")[1]
        ask_risk(chat_id)

    elif data.startswith("risk:"):
        user_state[chat_id]["risk"] = data.split(":")[1]

        text = build_signal_text(user_state[chat_id])
        bot1.send_message(chat_id, text)

        ask_destination(chat_id)

    elif data.startswith("dest:"):
        which = data.split(":")[1]
        text = build_signal_text(user_state[chat_id])

        if which == "ch1":
            bot1.send_message(CHANNEL_1_ID, text)
        elif which == "ch2":
            bot1.send_message(CHANNEL_2_ID, text)
        elif which == "both":
            bot1.send_message(CHANNEL_1_ID, text)
            bot1.send_message(CHANNEL_2_ID, text)

        bot1.send_message(chat_id, "سیگنال ارسال شد ✅")


# ===== وبهوک =====
@app.route(f"/webhook/{BOT1_WEBHOOK_SECRET}", methods=['POST'])
def webhook_bot1():
    json_str = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot1.process_new_updates([update])
    return "OK", 200


@app.route("/")
def index():
    return "Signal bot running.", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
