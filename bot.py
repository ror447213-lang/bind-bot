import telebot
import requests
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
TOKEN = "8637581331:AAHJonNLyJ_f5k5bfOnJgdVmtKWlPOnjmus"      # BotFather se lein
ADMIN_ID = 7634132457          # Sahi numerical ID dalein
UPI_ID = "rohit.hacrr@fam"
ADMIN_USERNAME = "@RO4IT1"
API_URL = "https://bind-ff.vercel.app"
# =================================================

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect('bot_users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, expiry_time TEXT)')
    conn.commit()
    conn.close()

def get_expiry(user_id):
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute("SELECT expiry_time FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else None

def is_active(user_id):
    expiry = get_expiry(user_id)
    if not expiry: return False
    try:
        return datetime.strptime(expiry, '%Y-%m-%d %H:%M:%S') > datetime.now()
    except: return False

# --- MAIN API FEATURE (WITH PROTECTION) ---
@bot.message_handler(commands=['check'])
def check_info(message):
    user_id = message.from_user.id
    
    # 🛡️ PEHLE CHECK KARO PLAN HAI YA NAHI
    if not is_active(user_id):
        bot.reply_to(message, "❌ **Access Denied!**\nAapke paas active plan nahi hai. /start karke points add karein.")
        return

    # AGAR PLAN HAI TOH API CHALAYO
    try:
        user_token = message.text.split()[1]
        bot.reply_to(message, "⏳ Wait... Garena se info nikaal raha hoon.")
        
        # Aapki Vercel API Call
        response = requests.post(f"{API_URL}/get-bind-info", json={"access_token": user_token}, timeout=10)
        data = response.json()
        
        bot.reply_to(message, f"📦 **Result:**\n`{data}`", parse_mode="Markdown")
    except IndexError:
        bot.reply_to(message, "⚠️ Usage: `/check <token>`", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ API Error: {str(e)}")

# --- START MENU (DYNAMIC BUTTONS) ---
@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    if is_active(message.from_user.id):
        # Active User Buttons
        markup.add('🔍 Check Bind', '⏳ My Validity', '💎 Buy Points')
        msg = f"✅ **Welcome Back!**\nAapka subscription active hai. Aap `/check <token>` use kar sakte hain."
    else:
        # Normal User Buttons
        markup.add('💎 Buy Points', '⏳ My Validity', '📞 Contact Admin')
        msg = "👋 Welcome! Service use karne ke liye points add karein."
    
    bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")

# Button Click Handle for 'Check Bind'
@bot.message_handler(func=lambda m: m.text == '🔍 Check Bind')
def check_button_hint(message):
    bot.send_message(message.chat.id, "📝 Info nikaalne ke liye niche diye format mein message bhein:\n\n`/check YOUR_TOKEN_HERE`", parse_mode="Markdown")

# --- BAAKI RECHARGE LOGIC (QR, UTR, ADMIN) ---
# [Pehle wala sara code yahan rahega...]
# (Pichle reply ka Buy Points, Generate QR, Process UTR logic yahan add karein)

@app.route('/')
def home(): return "Bot Active"

if __name__ == "__main__":
    init_db()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000))), daemon=True).start()
    bot.infinity_polling()
