import telebot
import qrcode
import sqlite3
import io
import threading
import time
import os
from flask import Flask
from telebot import types
from datetime import datetime, timedelta

# ================= CONFIGURATION =================
TOKEN = "8637581331:AAHJonNLyJ_f5k5bfOnJgdVmtKWlPOnjmus"  # BotFather se lein
ADMIN_ID = 7634132457           # Apna numerical ID yahan dalein
UPI_ID = "rohit.hacrr@fam"     # Aapki UPI ID
ADMIN_USERNAME = "@RO4IT1"     # Aapka Username
# =================================================

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Render ke liye chota Web Server
@app.route('/')
def home():
    return "Bot is Running 24/7!"

def run_flask():
    # Render hamesha 'PORT' environment variable deta hai
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('bot_users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, expiry_time TEXT)''')
    conn.commit()
    conn.close()

def get_expiry(user_id):
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute("SELECT expiry_time FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else None

def set_expiry(user_id, hours=0, days=0):
    now = datetime.now()
    current_expiry = get_expiry(user_id)
    start_time = now
    if current_expiry:
        try:
            old_expiry = datetime.strptime(current_expiry, '%Y-%m-%d %H:%M:%S')
            if old_expiry > now:
                start_time = old_expiry
        except: pass
    new_expiry = start_time + timedelta(days=days, hours=hours)
    expiry_str = new_expiry.strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, expiry_time) VALUES (?, ?)", (user_id, expiry_str))
    conn.commit()
    conn.close()
    return expiry_str

# --- AUTO-EXPIRY CHECKER ---
def expiry_checker():
    while True:
        try:
            conn = sqlite3.connect('bot_users.db')
            c = conn.cursor()
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute("SELECT user_id FROM users WHERE expiry_time <= ?", (now_str,))
            expired_users = c.fetchall()
            for user in expired_users:
                u_id = user[0]
                try: bot.send_message(u_id, "⚠️ **Plan Expired!**\nNaya access lene ke liye points add karein.", parse_mode="Markdown")
                except: pass
                c.execute("DELETE FROM users WHERE user_id = ?", (u_id,))
            conn.commit()
            conn.close()
        except: pass
        time.sleep(60)

# --- BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💎 Buy Points', '⏳ My Validity', '📞 Contact Admin')
    bot.send_message(message.chat.id, f"👋 Welcome!\n\nPlan kharidne ke liye niche buttons use karein.\nAdmin: {ADMIN_USERNAME}", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '⏳ My Validity')
def check_val(message):
    expiry = get_expiry(message.from_user.id)
    if expiry:
        bot.send_message(message.chat.id, f"🕒 **Active Status:**\nValid Till: `{expiry}`", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ No active plan found.")

@bot.message_handler(func=lambda m: m.text == '💎 Buy Points')
def plans(message):
    text = ("📊 **Price List:**\n\n"
            "• 10 Pts -> 2 Hours\n"
            "• 50 Pts -> 12 Hours\n"
            "• 100 Pts -> 24 Hours\n"
            "• 200 Pts -> 2 Days\n"
            "• 399 Pts -> 7 Days\n\n"
            "🔢 **Kitne points chahiye? Sirf number likhein:**")
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    bot.register_next_step_handler(message, generate_qr)

def generate_qr(message):
    try:
        amount = int(message.text)
        pay_url = f"upi://pay?pa={UPI_ID}&pn=Admin&am={amount}&cu=INR"
        qr = qrcode.make(pay_url)
        buf = io.BytesIO()
        qr.save(buf)
        buf.seek(0)
        bot.send_photo(message.chat.id, buf, caption=f"💰 **Amount: ₹{amount}**\n\nQR Scan karke pay karein aur **UTR Number** bhein.")
        bot.register_next_step_handler(message, process_utr, amount)
    except:
        bot.send_message(message.chat.id, "❌ Sirf numbers bhejien.")

def process_utr(message, amount):
    utr = message.text
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"app_{message.from_user.id}_{amount}"),
               types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{message.from_user.id}"))
    try:
        bot.send_message(ADMIN_ID, f"🔔 **New Payment**\nID: `{message.from_user.id}`\nAmt: ₹{amount}\nUTR: `{utr}`", reply_markup=markup, parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ **UTR Received!**\nAdmin verification mein **30-60 min** lagenge.")
    except:
        bot.send_message(message.chat.id, "❌ Error: Admin not found. Admin must start the bot.")

@bot.callback_query_handler(func=lambda call: True)
def admin_action(call):
    data = call.data.split('_')
    action, u_id = data[0], int(data[1])
    if action == "app":
        amt = int(data[2])
        h, d = 0, 0
        if amt >= 399: d = 7
        elif amt >= 200: d = 2
        elif amt >= 100: h = 24
        elif amt >= 50: h = 12
        elif amt >= 10: h = 2
        expiry = set_expiry(u_id, hours=h, days=d)
        bot.send_message(u_id, f"🎉 **Approved!**\nAccess granted till: `{expiry}`", parse_mode="Markdown")
        bot.edit_message_text(f"✅ Approved: {u_id}", call.message.chat.id, call.message.message_id)
    elif action == "rej":
        bot.send_message(u_id, "❌ Your payment was rejected.")
        bot.edit_message_text(f"❌ Rejected: {u_id}", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == '📞 Contact Admin')
def contact(message):
    bot.send_message(message.chat.id, f"Custom deals: {ADMIN_USERNAME}")

# --- START ---
if __name__ == "__main__":
    init_db()
    # Flask ko alag thread mein chalana
    threading.Thread(target=run_flask, daemon=True).start()
    # Expiry checker ko alag thread mein chalana
    threading.Thread(target=expiry_checker, daemon=True).start()
    print("Bot is running...")
    bot.infinity_polling()
