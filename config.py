# config.py
import os

# 🎫 توکن ربات تلگرام و آیدی عددی مدیر اصلی
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")  # از environment variable بخوان
if TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise ValueError("❌ متغیر BOT_TOKEN در محیط تعریف نشده است")
ADMIN_IDS = [6074037196, 6482904591] # لیست ادمین‌ها
ADMIN_ID = ADMIN_IDS[0]  # ادمین اصلی (برای ارسال نوتیفیکیشن‌ها)

# 📢 کانال‌های اسپانسر جهت قفل عضویت اجباری (آیدی‌ها را دقیق وارد کنید)
REQUIRED_CHANNELS = ["@vpn_mall", "@proxy_mall", "@config_mall"]

# 💳 اطلاعات کارت‌های بانکی جهت شارژ حساب
CARD_NUMBERS = [
    {"card": "6219861942773275", "owner": "آرین زیاد"},
    {"card": "5022291566660930", "owner": "شیدا نوری"},
    {"card": "5022291543179590", "owner": "محمد ونائی"},
    {"card": "6219861442253760", "owner": "مهران زیاد"},
]

# 💰 مبالغ هدیه دعوت (به تومان)
REFERRER_REWARD = 30000   # سهم میزبان
REFERREE_REWARD = 20000  # سهم مهمان

# 📉 تنظیمات تخفیف عمومی ربات
GLOBAL_DISCOUNT = 0
BLACKLISTED_USERS = set()

# 🆔 وضعیت‌های گفت‌وگو (Conversation States)
GET_AMOUNT, GET_RECEIPT = range(2)
ADMIN_GET_USER, ADMIN_GET_BALANCE_CHNG, ADMIN_GET_DISCOUNT, ADMIN_GET_BROADCAST = range(2, 6)
ADMIN_GET_BLOCK_ID, ADMIN_GET_UNBLOCK_ID, ADMIN_CHOOSE_STOCK_TYPE, ADMIN_GET_STOCK_CONTENT = range(6, 10)
SUPPORT_MESSAGE = 10

# 🤖 یوزنیم ربات به صورت کاملاً دقیق و اصلاح شده
BOT_USERNAME = "vpn_mall_bot"

# 📦 تعرفه و مخازن پلن‌های V2ray
V2RAY_PLANS = {
    "v2_10gb":  {"name": "🚀 پلن ۱۰ گیگابایت",  "price": 100000},
    "v2_15gb":  {"name": "🚀 پلن ۱۵ گیگابایت",  "price": 147000},
    "v2_20gb":  {"name": "🚀 پلن ۲۰ گیگابایت",  "price": 191000},
    "v2_30gb":  {"name": "🚀 پلن ۳۰ گیگابایت",  "price": 273000},
    "v2_70gb":  {"name": "🚀 پلن ۷۰ گیگابایت",  "price": 513000},
    "v2_100gb": {"name": "🚀 پلن ۱۰۰ گیگابایت", "price": 600000},
    "v2_unlimited": {"name": "🚀 پلن نامحدود", "price": 700000}
}
V2RAY_STORAGE_10 = []
V2RAY_STORAGE_15 = []
V2RAY_STORAGE_20 = []
# 25GB plan removed
V2RAY_STORAGE_30 = []
V2RAY_STORAGE_70 = []
V2RAY_STORAGE_100 = []

# 🔐 تعرفه و مخازن پلن‌های اکسپرس
EXPRESS_PLANS = {
    "ex_1user": {"name": "🔐 اکسپرس ۱ کاربره", "price": 700000},
    "ex_2user": {"name": "🔐 اکسپرس ۲ کاربره", "price": 1000000}
}
EXPRESS_CENTRAL_STORAGE = []

# ⏳ صف‌های انتظار در صورت اتمام موجودی انبارها
WAITING_QUEUE = {
    "v2_10gb": [],
    "v2_15gb": [],
    "v2_20gb": [],
    # 25GB queue removed
    "v2_30gb": [],
    "v2_70gb": [],
    "v2_100gb": [],
    "ex_1user": [],
    "ex_2user": []
}

ACCOUNT_COUNTER = 1000
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
CANCEL_KEYBOARD = InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف و بازگشت", callback_data="back_to_main")]])

def increment_account_counter():
    global ACCOUNT_COUNTER
    ACCOUNT_COUNTER += 1

def set_global_discount(amount: int):
    global GLOBAL_DISCOUNT
    GLOBAL_DISCOUNT = amount

def toggle_blacklist_user(user_id: int, block: bool):
    if block:
        BLACKLISTED_USERS.add(user_id)
    else:
        BLACKLISTED_USERS.discard(user_id)

def get_discounted_price(original_price: int) -> int:
    if GLOBAL_DISCOUNT <= 0:
        return original_price
    return int(original_price * (1 - GLOBAL_DISCOUNT / 100))

def save_all_storages():
    # این تابع برای شبیه‌سازی متد ذخیره‌سازی انبار شما قرار داده شده است
    pass