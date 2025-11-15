import os
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ====== تنظیم متغیرها ======
BOT1_TOKEN = os.getenv("BOT1_TOKEN")
BOT1_WEBHOOK_SECRET = os.getenv("BOT1_WEBHOOK_SECRET", "bot1secret123")

CHANNEL_1_ID = int(os.getenv("CHANNEL_1_ID", "-1001111111111"))
CHANNEL_2_ID = int(os.getenv("CHANNEL_2_ID", "-1002222222222"))

bot = telebot.TeleBot(BOT1_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ذخیره حالت کاربر
user_state = {}   # chat_id → dict


# ====== شروع ربات ======
@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    print(f"START from {chat_id}")  # برای Railway Log
    user_state[chat_id] = {}

    markup = InlineKeyboardMarkup(row_width=2)
    symbols = ["XAUUSD", "EURUSD", "GBPUSD", "JPY", "BTCUSDT"]
    buttons = [InlineKeyboardButton(sym, callback_data=f"sym:{sym}") for sym in symbols]
    markup.add(*buttons)

    bot.send_message(chat_id, "نماد را انتخاب کن:", reply_markup=markup)


# ====== گرفتن مرحله به مرحله ======
def ask_tp1(chat_id):
    msg = bot.send_message(chat_id, "TP1 را وارد کن:")
    bot.register_next_step_handler(msg, process_tp1)

def process_tp1(message):
    chat_id = message.chat.id
    user_state[chat_id]["tp1"] = message.text.strip()
    msg = bot.send_message(chat_id, "TP2 را وارد کن:")
    bot.register_next_step_handler(msg, process_tp2)

def process_tp2(message):
    chat_id = message.chat.id
    user_state[chat_id]["tp2"] = message.text.strip()
    msg = bot.send_message(chat_id, "TP3 را وارد کن:")
    bot.register_next_step_handler(msg, process_tp3)

def process_tp3(message):
    chat_id = message.chat.id
    user_state[chat_id]["tp3"] = message.text.strip()
    msg = bot.send_message(chat_id, "Stop Loss را وارد کن:")
    bot.register_next_step_handler(msg, process_stop)

def process_stop(message):
    chat_id = message.chat.id
    user_state[chat_id]["stop"] = message.text.strip()

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Buy", callback_data="dir:buy"),
        InlineKeyboardButton("Sell", callback_data="dir:sell")
    )
    bot.send_message(chat_id, "جهت را انتخاب کن:", reply_markup=markup)


def ask_risk(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("High Risk", callback_data="risk:high"),
        InlineKeyboardButton("Low Risk", callback_data="risk:low"),
    )
    bot.send_message(chat_id, "ریسک را انتخاب کن:", reply_markup=markup)


# ====== ساخت پیام نهایی ======
def build_signal(data):
    direction = "BUY" if data["direction"] == "buy" else "SELL"
    risk = "High Risk" if data["risk"] == "high" else "Low Risk"

    return (
        f"📊 <b>سیگنال جدید</b>\n\n"
        f"🔹 <b>Symbol:</b> {data['symbol']}\n"
        f"🔹 <b>Direction:</b> {direction}\n"
        f"🔹 <b>Risk:</b> {risk}\n\n"
        f"🎯 <b>Targets</b>\n"
        f"TP1 → {data['tp1']}\n"
        f"TP2 → {data['tp2']}\n"
        f"TP3 → {data['tp3']}\n\n"
        f"⛔ <b>Stop Loss:</b> {data['stop']}"
    )


# ====== انتخاب مقصد ======
def ask_destination(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("فقط همینجا", callback_data="dest:here"),
        InlineKeyboardButton("کانال VIP", callback_data="dest:ch1"),
        InlineKeyboardButton("کانال General", callback_data="dest:ch2"),
        InlineKeyboardButton("هر دو", callback_data="dest:both"),
    )
    bot.send_message(chat_id, "سیگنال را کجا بفرستم؟", reply_markup=markup)


# ====== هندل کال‌بک‌ها ======
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data.startswith("sym:"):
        user_state[chat_id]["symbol"] = data.split(":")[1]
        bot.answer_callback_query(call.id, "نماد انتخاب شد")
        ask_tp1(chat_id)

    elif data.startswith("dir:"):
        user_state[chat_id]["direction"] = data.split(":")[1]
        bot.answer_callback_query(call.id, "جهت انتخاب شد")
        ask_risk(chat_id)

    elif data.startswith("risk:"):
        user_state[chat_id]["risk"] = data.split(":")[1]
        bot.answer_callback_query(call.id, "ریسک انتخاب شد")

        signal_text = build_signal(user_state[chat_id])
        bot.send_message(chat_id, signal_text)

        ask_destination(chat_id)

    elif data.startswith("dest:"):
        signal_text = build_signal(user_state[chat_id])
        which = data.split(":")[1]

        if which == "here":
            bot.send_message(chat_id, signal_text)

        if which == "ch1":
            bot.send_message(CHANNEL_1_ID, signal_text)

        if which == "ch2":
            bot.send_message(CHANNEL_2_ID, signal_text)

        if which == "both":
            bot.send_message(CHANNEL_1_ID, signal_text)
            bot.send_message(CHANNEL_2_ID, signal_text)

        bot.answer_callback_query(call.id, "سیگنال ارسال شد")
        bot.send_message(chat_id, "سیگنال ارسال شد ✅")


# ====== وبهوک ======
@app.route(f"/webhook/{BOT1_WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.data.decode("utf-8"))
        bot.process_new_updates([update])
    except Exception as e:
        print("WEBHOOK ERROR:", e)
    return "OK", 200


# ====== صفحه اصلی ======
@app.route("/")
def index():
    return "Signal bot running.", 200


# ====== اجرای Flask ======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
