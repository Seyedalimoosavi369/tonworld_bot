import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

BOT_TOKEN = "8688031269:AAGkznT2odJXc64NlC1n9srC2QU90XrdYtA"
ADMIN_ID = 8030373785
bot = telebot.TeleBot(BOT_TOKEN)

CHANNEL = "@chat_chanelbot1"
GROUP = "@chat_groupbot1"

users = {}
waiting = []

def get_user(uid):
    if uid not in users:
        users[uid] = {"gender": None, "looking_for": None, "partner": None, "coins": 0, "referred_by": None, "referrals": [], "claimed_channel": False, "claimed_group": False, "messaging_admin": False}
    return users[uid]

def main_menu(uid):
    u = get_user(uid)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎲 چت شانسی (رایگان)", callback_data="find_any"))
    markup.add(InlineKeyboardButton("👧 چت با دختر (-2 سکه)", callback_data="find_female"))
    markup.add(InlineKeyboardButton("👦 چت با پسر (-2 سکه)", callback_data="find_male"))
    markup.add(InlineKeyboardButton(f"💰 سکه‌های من: {u['coins']}", callback_data="coins"))
    markup.add(InlineKeyboardButton("🎁 دعوت دوستان (+20 سکه)", callback_data="referral"))
    if not u["claimed_channel"] or not u["claimed_group"]:
        row = []
        if not u["claimed_channel"]:
            row.append(InlineKeyboardButton("📺 کانال (+10)", url="https://t.me/chat_chanelbot1"))
        if not u["claimed_group"]:
            row.append(InlineKeyboardButton("👥 گروه (+15)", url="https://t.me/chat_groupbot1"))
        markup.add(*row)
        markup.add(InlineKeyboardButton("✅ عضو شدم - سکه بگیر", callback_data="claim_coins"))
    markup.add(InlineKeyboardButton("📩 پیام به ادمین", callback_data="msg_admin"))
    return markup

def gender_menu():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("👦 پسر", callback_data="gender_male"),
        InlineKeyboardButton("👧 دختر", callback_data="gender_female")
    )
    return markup

def stop_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🔴 قطع چت"))
    return markup

def remove_keyboard():
    return ReplyKeyboardRemove()

def cancel_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("❌ انصراف"))
    return markup

def check_membership(uid):
    results = {"channel": False, "group": False}
    try:
        m = bot.get_chat_member(CHANNEL, uid)
        if m.status not in ["left", "kicked"]:
            results["channel"] = True
    except: pass
    try:
        m = bot.get_chat_member(GROUP, uid)
        if m.status not in ["left", "kicked"]:
            results["group"] = True
    except: pass
    return results

@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id
    args = message.text.split()
    u = get_user(uid)
    if len(args) > 1:
        try:
            ref_id = int(args[1])
            if ref_id != uid and u["referred_by"] is None:
                u["referred_by"] = ref_id
                ref_u = get_user(ref_id)
                if uid not in ref_u["referrals"]:
                    ref_u["referrals"].append(uid)
                    ref_u["coins"] += 20
                    u["coins"] += 20
                    bot.send_message(ref_id, f"🎉 یه نفر با لینک تو عضو شد!\n+20 سکه گرفتی!\n💰 سکه‌هات: {ref_u['coins']}")
        except: pass
    if u["gender"] is None:
        bot.send_message(uid, "👋 به ربات چت ناشناس خوش اومدی!\n\n🎁 با ثبت‌نام *20 سکه* هدیه میگیری!\n📺 عضویت کانال: +10 سکه\n👥 عضویت گروه: +15 سکه\n🎁 دعوت هر دوست: +20 سکه\n\nاول بگو تو *پسری یا دختر؟*", parse_mode="Markdown", reply_markup=gender_menu())
    else:
        bot.send_message(uid, f"💰 سکه‌هات: {u['coins']}\n\nچی میخوای؟", reply_markup=main_menu(uid))

@bot.callback_query_handler(func=lambda call: call.data.startswith("gender_"))
def set_gender(call):
    uid = call.from_user.id
    u = get_user(uid)
    gender = "male" if call.data == "gender_male" else "female"
    first_time = u["gender"] is None
    u["gender"] = gender
    label = "👦 پسر" if gender == "male" else "👧 دختر"
    if first_time:
        u["coins"] += 20
        bot.edit_message_text(f"جنسیت: {label}\n\n🎁 20 سکه هدیه گرفتی!\n💰 سکه‌هات: {u['coins']}\n\nحالا انتخاب کن:", uid, call.message.message_id, reply_markup=main_menu(uid))
    else:
        bot.edit_message_text(f"جنسیت: {label}\n\nانتخاب کن:", uid, call.message.message_id, reply_markup=main_menu(uid))

@bot.callback_query_handler(func=lambda call: call.data == "coins")
def show_coins(call):
    uid = call.from_user.id
    u = get_user(uid)
    bot.answer_callback_query(call.id, f"💰 سکه‌های تو: {u['coins']}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "referral")
def referral(call):
    uid = call.from_user.id
    u = get_user(uid)
    link = f"https://t.me/{bot.get_me().username}?start={uid}"
    bot.answer_callback_query(call.id)
    bot.send_message(uid, f"🎁 لینک دعوت تو:\n{link}\n\nهر کسی با این لینک بیاد، *هر دوتون 20 سکه* میگیرید!\n👥 دعوت‌هات: {len(u['referrals'])}", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "claim_coins")
def claim_coins(call):
    uid = call.from_user.id
    u = get_user(uid)
    membership = check_membership(uid)
    msg = ""
    if membership["channel"]:
        if not u["claimed_channel"]:
            u["claimed_channel"] = True
            u["coins"] += 10
            msg += "✅ کانال: +10 سکه\n"
        else:
            msg += "⚠️ کانال: قبلاً گرفتی\n"
    else:
        msg += "❌ کانال: هنوز عضو نشدی\n"
    if membership["group"]:
        if not u["claimed_group"]:
            u["claimed_group"] = True
            u["coins"] += 15
            msg += "✅ گروه: +15 سکه\n"
        else:
            msg += "⚠️ گروه: قبلاً گرفتی\n"
    else:
        msg += "❌ گروه: هنوز عضو نشدی\n"
    msg += f"\n💰 سکه‌هات: {u['coins']}"
    bot.answer_callback_query(call.id, msg, show_alert=True)
    try:
        bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=main_menu(uid))
    except: pass

@bot.callback_query_handler(func=lambda call: call.data == "msg_admin")
def msg_admin(call):
    uid = call.from_user.id
    u = get_user(uid)
    u["messaging_admin"] = True
    bot.answer_callback_query(call.id)
    bot.send_message(uid, "📩 پیامت رو بنویس، ناشناس به ادمین میرسه:", reply_markup=cancel_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("find_"))
def find_partner(call):
    uid = call.from_user.id
    u = get_user(uid)
    if u["gender"] is None:
        bot.answer_callback_query(call.id, "اول جنسیتت رو انتخاب کن!")
        return
    if u["partner"]:
        bot.answer_callback_query(call.id, "الان توی چتی! اول چت رو قطع کن.")
        return
    looking_for = {"find_any": "any", "find_female": "female", "find_male": "male"}[call.data]
    if looking_for != "any":
        if u["coins"] < 2:
            bot.answer_callback_query(call.id, "💰 سکه کافی نداری!\nچت شانسی رایگانه یا سکه بگیر.", show_alert=True)
            return
        u["coins"] -= 2
    u["looking_for"] = looking_for
    global waiting
    waiting = [w for w in waiting if w["id"] != uid]
    partner = None
    for w in waiting:
        wid = w["id"]
        if wid not in users: continue
        my_match = (looking_for == "any" or users[wid]["gender"] == looking_for)
        their_match = (w["looking_for"] == "any" or users[uid]["gender"] == w["looking_for"])
        if my_match and their_match:
            partner = w
            break
    if partner:
        pid = partner["id"]
        waiting.remove(partner)
        u["partner"] = pid
        users[pid]["partner"] = uid
        bot.edit_message_text("✅ پارتنر پیدا شد! شروع کن...", uid, call.message.message_id)
        bot.send_message(uid, "💬 چت شروع شد!", reply_markup=stop_keyboard())
        bot.send_message(pid, "✅ پارتنر پیدا شد! شروع کن...", reply_markup=stop_keyboard())
    else:
        waiting.append({"id": uid, "looking_for": looking_for})
        bot.edit_message_text(f"⏳ دنبال پارتنر میگردیم...\n💰 سکه‌هات: {u['coins']}\n\nبرای لغو: /stop", uid, call.message.message_id)

def do_stop(uid):
    global waiting
    waiting = [w for w in waiting if w["id"] != uid]
    u = get_user(uid)
    if u["partner"]:
        pid = u["partner"]
        u["partner"] = None
        if pid in users:
            users[pid]["partner"] = None
            bot.send_message(pid, "❌ پارتنرت چت رو قطع کرد.", reply_markup=remove_keyboard())
            bot.send_message(pid, "دوباره شروع کن؟", reply_markup=main_menu(pid))
        bot.send_message(uid, "❌ چت قطع شد.", reply_markup=remove_keyboard())
        bot.send_message(uid, "دوباره شروع کن؟", reply_markup=main_menu(uid))
    else:
        bot.send_message(uid, "چتی نداری.", reply_markup=main_menu(uid))

@bot.message_handler(commands=["stop"])
def stop(message):
    do_stop(message.from_user.id)

@bot.message_handler(commands=["coins"])
def coins_cmd(message):
    uid = message.from_user.id
    u = get_user(uid)
    bot.send_message(uid, f"💰 سکه‌هات: {u['coins']}\n👥 دعوت‌هات: {len(u['referrals'])}", reply_markup=main_menu(uid))

@bot.message_handler(content_types=["text"])
def forward_text(message):
    uid = message.from_user.id
    u = get_user(uid)

    if message.text == "🔴 قطع چت":
        do_stop(uid)
        return

    if message.text == "❌ انصراف":
        u["messaging_admin"] = False
        bot.send_message(uid, "انصراف دادی.", reply_markup=remove_keyboard())
        bot.send_message(uid, "چی میخوای؟", reply_markup=main_menu(uid))
        return

    if u["messaging_admin"]:
        u["messaging_admin"] = False
        bot.send_message(ADMIN_ID, f"📩 پیام ناشناس از ربات:\n\n{message.text}")
        bot.send_message(uid, "✅ پیامت به ادمین رسید!", reply_markup=remove_keyboard())
        bot.send_message(uid, "چی میخوای؟", reply_markup=main_menu(uid))
        return

    if not u["partner"]:
        bot.send_message(uid, "چتی نداری. /start بزن.", reply_markup=main_menu(uid))
        return
    bot.send_message(u["partner"], f"👤 ناشناس:\n{message.text}")

@bot.message_handler(content_types=["photo"])
def forward_photo(message):
    uid = message.from_user.id
    u = get_user(uid)
    if not u["partner"]: return
    bot.send_photo(u["partner"], message.photo[-1].file_id, caption="👤 ناشناس")

@bot.message_handler(content_types=["voice"])
def forward_voice(message):
    uid = message.from_user.id
    u = get_user(uid)
    if not u["partner"]: return
    bot.send_voice(u["partner"], message.voice.file_id)

@bot.message_handler(content_types=["video"])
def forward_video(message):
    uid = message.from_user.id
    u = get_user(uid)
    if not u["partner"]: return
    bot.send_video(u["partner"], message.video.file_id)

@bot.message_handler(content_types=["sticker"])
def forward_sticker(message):
    uid = message.from_user.id
    u = get_user(uid)
    if not u["partner"]: return
    bot.send_sticker(u["partner"], message.sticker.file_id)

print("ربات روشنه! ✅")
bot.polling(none_stop=True)
