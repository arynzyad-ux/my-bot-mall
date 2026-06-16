# stock_alert.py
# سیستم هشدار کمبود موجودی انبار
# بعد از هر خرید یا تحویل از صف، تمام انبارها رو چک می‌کنه
# اگه موجودی هر انبار زیر ۲ بود، هشدار میده

import config
import html
from telegram import Bot

# آستانه هشدار (حداقل موجودی مجاز قبل از ارسال هشدار)
LOW_STOCK_THRESHOLD = 2

# نگاشت انبارها به نام نمایشی و کلید پلن
STOCK_MAP = {
    "v2_20gb": {
        "storage": lambda: config.V2RAY_STORAGE_20,
        "label": "🚀 انبار ۲۰ گیگابایت V2ray",
    },
    "v2_10gb": {
        "storage": lambda: config.V2RAY_STORAGE_10,
        "label": "🚀 انبار ۱۰ گیگابایت V2ray",
    },
    "v2_15gb": {
        "storage": lambda: config.V2RAY_STORAGE_15,
        "label": "🚀 انبار ۱۵ گیگابایت V2ray",
    },
    "v2_30gb": {
        "storage": lambda: config.V2RAY_STORAGE_30,
        "label": "🚀 انبار ۳۰ گیگابایت V2ray",
    },
    "v2_70gb": {
        "storage": lambda: config.V2RAY_STORAGE_70,
        "label": "🚀 انبار ۷۰ گیگابایت V2ray",
    },
    "v2_100gb": {
        "storage": lambda: config.V2RAY_STORAGE_100,
        "label": "🚀 انبار ۱۰۰ گیگابایت V2ray",
    },
    "express": {
        "storage": lambda: config.EXPRESS_CENTRAL_STORAGE,
        "label": "🔐 مخزن مرکزی اکسپرس",
    },
}


def get_all_stock_counts() -> dict:
    """شمارش موجودی تمام انبارها

    Returns:
        dict: {plan_id: {"label": str, "count": int}}
    """
    result = {}
    for plan_id, info in STOCK_MAP.items():
        result[plan_id] = {
            "label": info["label"],
            "count": len(info["storage"]()),
        }
    return result


def get_low_stock_items() -> list:
    """لیست انبارهایی که موجودیشون زیر آستانه هست

    Returns:
        list: [{"plan_id": str, "label": str, "count": int}]
    """
    low = []
    for plan_id, info in STOCK_MAP.items():
        count = len(info["storage"]())
        if count < LOW_STOCK_THRESHOLD:
            low.append({
                "plan_id": plan_id,
                "label": info["label"],
                "count": count,
            })
    return low


async def check_and_notify_low_stock(context, trigger_event: str = ""):
    """بررسی موجودی و ارسال هشدار به ادمین‌ها در صورت کمبود

    این تابع بعد از هر خرید یا تحویل از صف باید صدا زده بشه.

    Args:
        context: Context ربات تلگرام
        trigger_event: توضیح رویداد باعث بررسی (برای نمایش در هشدار)
    """
    low_items = get_low_stock_items()
    if not low_items:
        return  # همه انبارها بالای آستانه هستن، هشداری لازم نیست

    # ساخت متن هشدار
    event_desc = f"📌 رویداد: <b>{trigger_event}</b>\n" if trigger_event else ""

    items_text = ""
    for item in low_items:
        count_display = f"<code>{item['count']}</code>"
        if item["count"] == 0:
            count_display = "<code>0</code> 🔴 خالی"
        elif item["count"] == 1:
            count_display = "<code>1</code> 🟡 رو به اتمام"
        items_text += f"  ◽ {item['label']}: {count_display} کانفیگ\n"

    # موجودی کل انبارها برای اطلاع‌رسانی کامل
    all_counts = get_all_stock_counts()
    summary_text = (
        f"\n📦 <b>موجودی کلی انبارها:</b>\n"
            f"  ◽ ۱۰ گیگ: <code>{all_counts['v2_10gb']['count']}</code> | ۱۵ گیگ: <code>{all_counts['v2_15gb']['count']}</code> | ۲۰ گیگ: <code>{all_counts['v2_20gb']['count']}</code>\n"
            f"  ◽ ۳۰ گیگ: <code>{all_counts['v2_30gb']['count']}</code>\n"
            f"  ◽ ۷۰ گیگ: <code>{all_counts['v2_70gb']['count']}</code> | ۱۰۰ گیگ: <code>{all_counts['v2_100gb']['count']}</code>\n"
            f"  ◽ اکسپرس: <code>{all_counts['express']['count']}</code>\n"
    )

    alert_text = (
        "🚨 <b>هشدار کمبود موجودی انبار!</b>\n\n"
        f"{event_desc}"
        f"⚠️ <b>انبارهای زیر آستانه مجاز ({LOW_STOCK_THRESHOLD}) قرار گرفتند:</b>\n\n"
        f"{items_text}"
        f"{summary_text}\n"
        "⚡ لطفاً هرچه سریع‌تر انبارهای مربوطه را شارژ کنید."
    )

    # ارسال به تمام ادمین‌ها
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=alert_text,
                parse_mode="HTML",
            )
        except Exception:
            pass  # اگر ارسال به یک ادمین با خطا مواجه شد، به بقیه ارسال کن
