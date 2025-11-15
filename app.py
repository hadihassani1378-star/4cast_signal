import os
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ====== تنظیم متغیرها از ENV ======
BOT1_TOKEN = os.getenv("BOT1_TOKEN")
BOT1_WEBHOOK_SECRET = os.getenv("BOT1_WEBHOOK_SECRET", "bot1secret123")

CHANNEL_1_ID = int(os.getenv("CHANNEL_1_ID", "-1001111111111"))  # VIP
CHANNEL_2_ID = int(os.getenv("CHANNEL_2_ID", "-1002222222222"))  # General

# ====== ادمین‌ها (فقط این دو نفر اجازه ساخت سیگنال دارند) ======
ADMINS = [526350575, 7706851494]  # Hadi, Sepi


def is_admin(user_id: int) -> bool:
    return user_id in ADMINS


bot = telebot.TeleBot(BOT1_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ذخیره حالت کاربر
# user_state[chat_id] = {
#   "symbol", "tp1", "tp2", "tp3", "stop",
#   "direction", "risk",
#   "with_image": True/False,
#   "photo_file_id": "...",
# }
user_state = {}


# ====== شروع ربات ======
@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_admin(user_id):
        bot.send_message(chat_id, "❌ شما اجازه استفاده از این ربات را ندارید.")
        return

    print(f"START from {chat_id}")
    user_state[chat_id] = {}
    ask_symbol(chat_id)


# ====== مراحل گرفتن ورودی‌ها ======
def ask_symbol(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    symbols = ["XAUUSD", "EURUSD", "GBPUSD", "JPY", "BTCUSDT"]
    buttons = [InlineKeyboardButton(sym, callback_data=f"sym:{sym}") for sym in symbols]
    markup.add(*buttons)
    bot.send_message(chat_id, "نماد را انتخاب کن:", reply_markup=markup)


def ask_tp1(chat_id):
    msg = bot.send_message(chat_id, "TP1 را وارد کن:")
    bot.register_next_step_handler(msg, process_tp1)


def process_tp1(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    chat_id = message.chat.id
    user_state.setdefault(chat_id, {})
    user_state[chat_id]["tp1"] = message.text.strip()
    msg = bot.send_message(chat_id, "TP2 را وارد کن:")
    bot.register_next_step_handler(msg, process_tp2)


def process_tp2(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    chat_id = message.chat.id
    user_state[chat_id]["tp2"] = message.text.strip()
    msg = bot.send_message(chat_id, "TP3 را وارد کن:")
    bot.register_next_step_handler(msg, process_tp3)


def process_tp3(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    chat_id = message.chat.id
    user_state[chat_id]["tp3"] = message.text.strip()
    msg = bot.send_message(chat_id, "Stop Loss را وارد کن:")
    bot.register_next_step_handler(msg, process_stop)


def process_stop(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    chat_id = message.chat.id
    user_state[chat_id]["stop"] = message.text.strip()

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Buy", callback_data="dir:buy"),
        InlineKeyboardButton("Sell", callback_data="dir:sell"),
    )
    bot.send_message(chat_id, "جهت را انتخاب کن:", reply_markup=markup)


def ask_risk(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("High Risk", callback_data="risk:high"),
        InlineKeyboardButton("Low Risk", callback_data="risk:low"),
    )
    bot.send_message(chat_id, "ریسک را انتخاب کن:", reply_markup=markup)


def ask_with_image(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📸 با عکس", callback_data="img:yes"),
        InlineKeyboardButton("❌ بی‌عکس", callback_data="img:no"),
    )
    bot.send_message(chat_id, "سیگنال با عکس بفرستم یا بی‌عکس؟", reply_markup=markup)


def ask_photo(chat_id):
    msg = bot.send_message(chat_id, "حالا عکس سیگنال رو بفرست 📸")
    bot.register_next_step_handler(msg, process_photo)


def process_photo(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    chat_id = message.chat.id

    if not message.photo:
        # اگر عکس نفرستاد، دوباره بخواهیم
        msg = bot.send_message(chat_id, "این عکس نبود! لطفاً یک عکس بفرست 📸")
        bot.register_next_step_handler(msg, process_photo)
        return

    # بزرگ‌ترین سایز عکس
    file_id = message.photo[-1].file_id
    user_state.setdefault(chat_id, {})
    user_state[chat_id]["photo_file_id"] = file_id

    # حالا مقصد را بپرسیم
    ask_destination(chat_id)


# ====== ساخت کیبورد دکمه‌ای برای نمایش سیگنال ======
def build_signal_keyboard(data):
    """
    کیبورد دو ستونه فقط برای نمایش:
    [ Symbol ] [ XAUUSD ]
    ...
    دکمه‌ها غیر فعال (callback_data="x")
    """
    markup = InlineKeyboardMarkup(row_width=2)

    direction = "BUY" if data["direction"] == "buy" else "SELL"
    risk = "High Risk" if data["risk"] == "high" else "Low Risk"

    markup.add(
        InlineKeyboardButton("Symbol", callback_data="x"),
        InlineKeyboardButton(data["symbol"], callback_data="x"),
    )
    markup.add(
        InlineKeyboardButton("Direction", callback_data="x"),
        InlineKeyboardButton(direction, callback_data="x"),
    )
    markup.add(
        InlineKeyboardButton("Risk", callback_data="x"),
        InlineKeyboardButton(risk, callback_data="x"),
    )
    markup.add(
        InlineKeyboardButton("TP1", callback_data="x"),
        InlineKeyboardButton(data["tp1"], callback_data="x"),
    )
    markup.add(
        InlineKeyboardButton("TP2", callback_data="x"),
        InlineKeyboardButton(data["tp2"], callback_data="x"),
    )
    markup.add(
        InlineKeyboardButton("TP3", callback_data="x"),
        InlineKeyboardButton(data["tp3"], callback_data="x"),
    )
    markup.add(
        InlineKeyboardButton("STOP LOSS", callback_data="x"),
        InlineKeyboardButton(data["stop"], callback_data="x"),
    )

    return markup


# ====== انتخاب مقصد ======
def ask_destination(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("فقط همینجا", callback_data="dest:here"),
        InlineKeyboardButton("کانال VIP", callback_data="dest:ch1"),
    )
    markup.add(
        InlineKeyboardButton("کانال General", callback_data="dest:ch2"),
        InlineKeyboardButton("هر دو", callback_data="dest:both"),
    )
    bot.send_message(chat_id, "سیگنال را کجا بفرستم؟", reply_markup=markup)


# ====== هندل کال‌بک‌ها ======
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = call.data

    # دکمه‌های نمایشی (x) → هیچ کاری نکن
    if data == "x":
        bot.answer_callback_query(call.id)
        return

    # برای همه‌ی دکمه‌های منطقی، فقط ادمین اجازه دارد
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "❌ اجازه استفاده از این ربات را نداری.", show_alert=True)
        return

    user_state.setdefault(chat_id, {})

    # انتخاب نماد
    if data.startswith("sym:"):
        user_state[chat_id]["symbol"] = data.split(":")[1]
        bot.answer_callback_query(call.id, "نماد انتخاب شد ✅")
        ask_tp1(chat_id)

    # جهت
    elif data.startswith("dir:"):
        user_state[chat_id]["direction"] = data.split(":")[1]
        bot.answer_callback_query(call.id, "جهت انتخاب شد ✅")
        ask_risk(chat_id)

    # ریسک
    elif data.startswith("risk:"):
        user_state[chat_id]["risk"] = data.split(":")[1]
        bot.answer_callback_query(call.id, "ریسک انتخاب شد ✅")
        # حالا می‌پرسیم با عکس / بی‌عکس
        ask_with_image(chat_id)

    # انتخاب با عکس / بی‌عکس
    elif data.startswith("img:"):
        flag = data.split(":")[1]
        user_state[chat_id]["with_image"] = (flag == "yes")
        bot.answer_callback_query(call.id, "نوع ارسال انتخاب شد ✅")

        if flag == "yes":
            # باید عکس بفرسته
            ask_photo(chat_id)
        else:
            # بدون عکس، مستقیم مقصد را بپرس
            ask_destination(chat_id)

    # مقصد
    elif data.startswith("dest:"):
        which = data.split(":")[1]
        sig_data = user_state[chat_id]
        keyboard = build_signal_keyboard(sig_data)
        title = "📊 سیگنال جدید"

        photo_file_id = sig_data.get("photo_file_id")
        with_image = bool(photo_file_id) and sig_data.get("with_image", False)

        def send_to(target_chat_id):
            if with_image:
                bot.send_photo(
                    target_chat_id,
                    photo_file_id,
                    caption=title,
                    reply_markup=keyboard,
                )
            else:
                bot.send_message(
                    target_chat_id,
                    title,
                    reply_markup=keyboard,
                )

        if which == "here":
            send_to(chat_id)
        elif which == "ch1":
            send_to(CHANNEL_1_ID)
        elif which == "ch2":
            send_to(CHANNEL_2_ID)
        elif which == "both":
            send_to(CHANNEL_1_ID)
            send_to(CHANNEL_2_ID)

        bot.answer_callback_query(call.id, "سیگنال ارسال شد ✅")
        bot.send_message(chat_id, "سیگنال به مقصد انتخابی ارسال شد ✅")


# ====== وبهوک ======
@app.route(f"/webhook/{BOT1_WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.data.decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200


# ====== صفحه اصلی ======
@app.route("/")
def index():
    return "Signal bot running.", 200


# ====== اجرای Flask ======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
