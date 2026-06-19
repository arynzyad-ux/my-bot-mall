# handlers.py
import random
import config
import database
import stock_alert
import logging
import asyncio
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import (
    TOKEN, ADMIN_ID, ADMIN_IDS, REQUIRED_CHANNELS, CANCEL_KEYBOARD, CARD_NUMBERS, V2RAY_PLANS, EXPRESS_PLANS,
    GET_AMOUNT, GET_RECEIPT, save_all_storages, get_discounted_price, GLOBAL_DISCOUNT, set_global_discount,
    BLACKLISTED_USERS, toggle_blacklist_user, REFERRER_REWARD, REFERREE_REWARD, BOT_USERNAME,
    ADMIN_GET_USER, ADMIN_GET_BALANCE_CHNG, ADMIN_GET_DISCOUNT, ADMIN_GET_BROADCAST,
    ADMIN_GET_BLOCK_ID, ADMIN_GET_UNBLOCK_ID, ADMIN_CHOOSE_STOCK_TYPE, ADMIN_GET_STOCK_CONTENT,
    SUPPORT_MESSAGE, ADMIN_MANAGE_STORAGE_MENU, ADMIN_VIEW_STORAGE_ITEMS, ADMIN_ADD_STORAGE_ITEM, ADMIN_REMOVE_STORAGE_ITEM, ADMIN_EDIT_STORAGE_ITEM
)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def is_user_blacklisted(user_id: int) -> bool:
    return user_id in BLACKLISTED_USERS

async def check_joined_channels(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if user_id in ADMIN_IDS:
        return True
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["creator", "administrator", "member"]:
                return False
        except Exception:
            return False
    return True

async def send_join_request_message(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    query = update.callback_query
    user_id = query.from_user.id if is_callback else update.effective_user.id
    keyboard = []
    not_joined_count = 0

    for channel in REQUIRED_CHANNELS:
        is_member = False
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["creator", "administrator", "member"]:
                is_member = True
        except Exception:
            is_member = False

        if not is_member:
            not_joined_count += 1
            clean_username = channel.replace("@", "")
            keyboard.append([InlineKeyboardButton(f"📢 عضویت در کانال {channel}", url=f"https://t.me/{clean_username}")])

    if not_joined_count == 0:
        if is_callback:
            await query.answer("✅ عضویت شما تایید شد!")
        return await process_successful_entry(user_id, update, context)

    keyboard.append([InlineKeyboardButton("🔄 بررسی مجدد عضویت و ورود", callback_data="check_membership")])
    markup = InlineKeyboardMarkup(keyboard)
    text = (
        "⚠️ <b>دسترسی شما محدود شد!</b>\n\n"
        f"🔰 شما هنوز در <b>{not_joined_count}</b> کانال اسپانسر عضو نیستید.\n\n"
        "👇 لطفاً ابتدا در کانال‌های زیر عضو شوید و سپس دکمه بررسی مجدد را بزنید:"
    )
    if is_callback:
        await query.edit_message_text(text=text, reply_markup=markup, parse_mode="HTML")
    else:
        await update.message.reply_text(text=text, reply_markup=markup, parse_mode="HTML")

async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if is_user_blacklisted(user_id):
        await query.answer("❌ شما از دسترسی به این ربات محروم شده‌اید.", show_alert=True)
        return
    await query.answer("⏳ در حال راستی‌آزمایی...")
    is_joined = await check_joined_channels(user_id, context)
    if is_joined:
        return await process_successful_entry(user_id, update, context)
    else:
        await send_join_request_message(update, context, is_callback=True)

async def process_successful_entry(user_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = database.get_user_data(user_id)
    if user_data and not user_data.get("reward_claimed", False):
        referrer_id = user_data.get("referred_by")
        if referrer_id:
            database.update_user_balance(user_id, REFERREE_REWARD)
            database.update_user_field(user_id, "reward_claimed", True)
            database.update_user_balance(referrer_id, REFERRER_REWARD)
            ref_data = database.get_user_data(referrer_id)
            current_invites = ref_data.get("total_invited", 0) if ref_data else 0
            database.update_user_field(referrer_id, "total_invited", current_invites + 1)
            try:
                me_name = html.escape(update.effective_user.first_name) if update.effective_user else "یک کاربر جدید"
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 <b>تبریک! زیرمجموعه شما عضو شد</b>\n\n👤 کاربر <b>{me_name}</b> قفل کانال را باز کرد!\n💰 مبلغ <code>{REFERRER_REWARD:,}</code> تومان به عنوان هدیه معرفی به کیف پول شما واریز شد.",
                    parse_mode="HTML"
                )
            except: pass
            welcome_text = f"🎉 <b>خوش آمدید!</b>\n\n🎁 به دلیل ورود با لینک دعوت، مبلغ <code>{REFERREE_REWARD:,}</code> تومان هدیه ورود به کیف پول شما واریز شد!"
            return await show_main_menu(update, context, override_text=welcome_text)
    return await show_main_menu(update, context)

async def admin_menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return -1
    context.user_data.clear()
    text = (
        "⚙️ <b>به پنل مدیریت فوق پیشرفته ربات خوش آمدید</b>\n\n"
        f"📉 تخفیف عمومی فعلی: <code>% {config.GLOBAL_DISCOUNT}</code>\n"
        f"🚫 تعداد کاربران در لیست سیاه: <code>{len(config.BLACKLISTED_USERS)}</code> نفر\n\n"
        "👇 مدیریت بخش‌های مختلف ربات:"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 شارژ/کسر از موجودی کاربر", callback_data="admin_manage_wallet"), InlineKeyboardButton("📉 تنظیم درصد تخفیف", callback_data="admin_set_discount")],
        [InlineKeyboardButton("🚫 بلاک کردن کاربر", callback_data="admin_block_user"), InlineKeyboardButton("🟢 آن‌بلاک کردن کاربر", callback_data="admin_unblock_user")],
        [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast"), InlineKeyboardButton("📦 موجودی و آمار انبار", callback_data="admin_view_stock")],
        [InlineKeyboardButton("⭐ کاربران برتر و پاداش", callback_data="admin_top_users"), InlineKeyboardButton("📥 شارژ انبار", callback_data="admin_add_stock_menu")],
        [InlineKeyboardButton("🛠 مدیریت تفصیلی انبارها", callback_data="admin_storage_manager")],
        [InlineKeyboardButton("📊 گزارش پیشرفته ربات (Live)", callback_data="admin_full_report")]
    ])
    if update.message:
        await update.message.reply_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    return -1

async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: 
        await query.answer()
    context.user_data.clear()
    await admin_menu_cmd(update, context)
    return ConversationHandler.END

async def admin_wallet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="✍️ <b>لطفاً آیدی عددی (User ID) کاربر مورد نظر را ارسال کنید:</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin_back")]]), parse_mode="HTML")
    return ADMIN_GET_USER

async def admin_wallet_user_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if not user_input.isdigit():
        await update.message.reply_text("❌ آیدی عددی نامعتبر است. مجدداً ارسال کنید:")
        return ADMIN_GET_USER

    target_user_id = int(user_input)
    user_data = database.get_user_data(target_user_id)
    if not user_data:
        await update.message.reply_text("❌ کاربری با این آیدی در دیتابیس یافت نشد. مجدداً ارسال کنید:")
        return ADMIN_GET_USER

    action = context.user_data.get("admin_action", "wallet")

    if action == "search_user_reward":
        return await admin_user_reward_menu(update, context)

    # action == "wallet"
    current_bal = user_data.get("balance", 0)
    context.user_data["admin_target_user"] = target_user_id
    text = (
        f"👤 <b>کاربر پیدا شد:</b> <code>{target_user_id}</code>\n"
        f"💵 <b>موجودی فعلی حساب:</b> <code>{current_bal:,}</code> تومان\n\n"
        "✍️ <b>لطفاً مبلغ تغییر را به تومان وارد کنید:</b>\n"
        "🔹 مثال شارژ: <code>50000</code> | مثال کسر از حساب: <code>-30000</code>"
    )
    await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin_back")]]), parse_mode="HTML")
    return ADMIN_GET_BALANCE_CHNG

async def admin_wallet_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip().translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))
    is_negative = user_input.startswith("-")
    clean_num = user_input.replace("-", "").strip()
    if not clean_num.isdigit():
        await update.message.reply_text("❌ فقط عدد وارد کنید:")
        return ADMIN_GET_BALANCE_CHNG

    amount = int(clean_num)
    if is_negative:
        amount = -amount

    target_user_id = context.user_data.get("admin_target_user")
    action = context.user_data.get("admin_action", "wallet")

    database.update_user_balance(target_user_id, amount)
    new_bal = database.get_user_balance(target_user_id)

    if action == "reward_amount":
        await update.message.reply_text(
            f"✅ <b>پاداش دادن شد!</b>\n\n"
            f"👤 کاربر: <code>{target_user_id}</code>\n"
            f"💰 مبلغ: <code>{amount:,}</code> تومان\n"
            f"💵 موجودی جدید: <code>{new_bal:,}</code> تومان",
            parse_mode="HTML"
        )
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"🎁 <b>پاداش ویژه از مدیریت!</b>\n\n💰 مبلغ <code>{amount:,}</code> تومان به حساب شما اضافه شد.\n💵 موجودی: <code>{new_bal:,}</code> تومان",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Failed to send reward message: {e}")
    else:
        if amount > 0:
            await update.message.reply_text(f"✅ حساب کاربر <code>{target_user_id}</code> به مبلغ <code>{amount:,}</code> تومان شارژ شد.", parse_mode="HTML")
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"🎉 <b>کیف پول شما توسط مدیریت شارژ شد!</b>\n➕ مبلغ افزایش: <code>{amount:,}</code> تومان\n💵 موجودی جدید: <code>{new_bal:,}</code> تومان",
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Failed to send charge message: {e}")
        else:
            await update.message.reply_text(f"✅ به مبلغ <code>{abs(amount):,}</code> تومان از حساب کاربر <code>{target_user_id}</code> کسر شد.", parse_mode="HTML")
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"⚠️ <b>کیف پول شما توسط مدیریت تغییر کرد.</b>\n➖ مبلغ کسر شده: <code>{abs(amount):,}</code> تومان\n💵 موجودی جدید: <code>{new_bal:,}</code> تومان",
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Failed to send deduction message: {e}")

    return await admin_cancel(update, context)

async def admin_discount_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text=f"📉 <b>بخش تنظیم تخفیف عمومی ربات</b>\n\nتخفیف فعلی: <code>% {config.GLOBAL_DISCOUNT}</code> است.\n✍️ <b>یک عدد بین 0 تا 100 بفرستید (عدد 0 یعنی حذف تخفیف):</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin_back")]]), parse_mode="HTML")
    return ADMIN_GET_DISCOUNT

async def admin_discount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip().translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))
    if not user_input.isdigit() or not (0 <= int(user_input) <= 100):
        await update.message.reply_text("❌ درصد تخفیف نامعتبر است. یک عدد بین 0 تا 100 بفرستید:")
        return ADMIN_GET_DISCOUNT
    set_global_discount(int(user_input))
    await update.message.reply_text(f"✅ تخفیف عمومی ربات روی <code>% {user_input}</code> تنظیم شد.", parse_mode="HTML")
    return await admin_cancel(update, context)

async def admin_block_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🚫 <b>آیدی عددی کاربری که قصد بلاک کردنش را دارید بفرستید:</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin_back")]]), parse_mode="HTML")
    return ADMIN_GET_BLOCK_ID

async def admin_block_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if not user_input.isdigit():
        await update.message.reply_text("❌ آیدی عددی نامعتبر است:")
        return ADMIN_GET_BLOCK_ID
    target_id = int(user_input)
    toggle_blacklist_user(target_id, block=True)
    await update.message.reply_text(f"🔒 کاربر <code>{target_id}</code> با موفقیت بلاک شد و دسترسی او قطع گردید.", parse_mode="HTML")
    return await admin_cancel(update, context)

async def admin_unblock_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🟢 <b>آیدی عددی کاربری که قصد خارج کردن از لیست سیاه را دارید بفرستید:</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin_back")]]), parse_mode="HTML")
    return ADMIN_GET_UNBLOCK_ID

async def admin_unblock_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if not user_input.isdigit():
        await update.message.reply_text("❌ آیدی عددی نامعتبر است:")
        return ADMIN_GET_UNBLOCK_ID
    target_id = int(user_input)
    toggle_blacklist_user(target_id, block=False)
    await update.message.reply_text(f"🔓 کاربر <code>{target_id}</code> آزاد شد و مجدداً می‌تواند از ربات استفاده کند.", parse_mode="HTML")
    return await admin_cancel(update, context)

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="📢 <b>متن پیام همگانی خود را بنویسید و ارسال کنید:</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin_back")]]), parse_mode="HTML")
    return ADMIN_GET_BROADCAST

async def admin_broadcast_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    broadcast_text = update.message.text
    await update.message.reply_text("⏳ فرآیند ارسال آغاز شد...")
    user_ids = []
    try:
        users = database.get_all_users()
        if users and isinstance(users, dict):
            for k in users.keys():
                if str(k).isdigit() or isinstance(k, int):
                    user_ids.append(int(k))
    except Exception: pass
    user_ids = list(set(user_ids))
    if not user_ids:
        await update.message.reply_text("❌ کاربر فعالی یافت نشد.")
        return await admin_cancel(update, context)
    success, fail = 0, 0
    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=broadcast_text)
            success += 1
            await asyncio.sleep(0.04)
        except: fail += 1
    await update.message.reply_text(f"📢 <b>گزارش ارسال همگانی:</b>\n✅ موفق: <code>{success}</code>\n❌ مسدود: <code>{fail}</code>", parse_mode="HTML")
    return await admin_cancel(update, context)

async def admin_view_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # جمع‌آوری وضعیت هشدار برای هر انبار
    def stock_status_icon(count):
        if count == 0: return "🔴"
        elif count < stock_alert.LOW_STOCK_THRESHOLD: return "🟡"
        return "🟢"

    text = (
        "📦 <b>موجودی انبارها و ظرفیت فعلی مخازن:</b>\n\n"
        f"{stock_status_icon(len(config.V2RAY_STORAGE_5))} انبار ۵ گیگابایت: <code>{len(config.V2RAY_STORAGE_5)}</code> کانفیگ\n"
        f"{stock_status_icon(len(config.V2RAY_STORAGE_10))} انبار ۱۰ گیگابایت: <code>{len(config.V2RAY_STORAGE_10)}</code> کانفیگ\n"
        f"{stock_status_icon(len(config.V2RAY_STORAGE_15))} انبار ۱۵ گیگابایت: <code>{len(config.V2RAY_STORAGE_15)}</code> کانفیگ\n"
        f"{stock_status_icon(len(config.V2RAY_STORAGE_20))} انبار ۲۰ گیگابایت: <code>{len(config.V2RAY_STORAGE_20)}</code> کانفیگ\n"
        f"{stock_status_icon(len(config.V2RAY_STORAGE_25))} انبار ۲۵ گیگابایت: <code>{len(config.V2RAY_STORAGE_25)}</code> کانفیگ\n"
        f"{stock_status_icon(len(config.V2RAY_STORAGE_30))} انبار ۳۰ گیگابایت: <code>{len(config.V2RAY_STORAGE_30)}</code> کانفیگ\n"
        f"{stock_status_icon(len(config.V2RAY_STORAGE_40))} انبار ۴۰ گیگابایت: <code>{len(config.V2RAY_STORAGE_40)}</code> کانفیگ\n"
        f"{stock_status_icon(len(config.V2RAY_STORAGE_50))} انبار ۵۰ گیگابایت: <code>{len(config.V2RAY_STORAGE_50)}</code> کانفیگ\n"
        f"{stock_status_icon(len(config.V2RAY_STORAGE_60))} انبار ۶۰ گیگابایت: <code>{len(config.V2RAY_STORAGE_60)}</code> کانفیگ\n"
        f"{stock_status_icon(len(config.V2RAY_STORAGE_70))} انبار ۷۰ گیگابایت: <code>{len(config.V2RAY_STORAGE_70)}</code> کانفیگ\n"
        f"{stock_status_icon(len(config.V2RAY_STORAGE_80))} انبار ۸۰ گیگابایت: <code>{len(config.V2RAY_STORAGE_80)}</code> کانفیگ\n"
        f"{stock_status_icon(len(config.V2RAY_STORAGE_90))} انبار ۹۰ گیگابایت: <code>{len(config.V2RAY_STORAGE_90)}</code> کانفیگ\n"
        f"{stock_status_icon(len(config.V2RAY_STORAGE_100))} انبار ۱۰۰ گیگابایت: <code>{len(config.V2RAY_STORAGE_100)}</code> کانفیگ\n"
        f"{stock_status_icon(len(config.EXPRESS_CENTRAL_STORAGE))} مخزن مرکزی اکسپرس: <code>{len(config.EXPRESS_CENTRAL_STORAGE)}</code> اکانت\n\n"
        f"⏳ <b>صف‌های انتظار:</b>\n"
        f"◽ صف ۵ گیگ: <code>{len(config.WAITING_QUEUE['v2_5gb'])}</code> | صف ۱۰ گیگ: <code>{len(config.WAITING_QUEUE['v2_10gb'])}</code> | صف ۱۵ گیگ: <code>{len(config.WAITING_QUEUE['v2_15gb'])}</code>\n"
        f"◽ صف ۲۰ گیگ: <code>{len(config.WAITING_QUEUE['v2_20gb'])}</code> | صف ۲۵ گیگ: <code>{len(config.WAITING_QUEUE['v2_25gb'])}</code> | صف ۳۰ گیگ: <code>{len(config.WAITING_QUEUE['v2_30gb'])}</code>\n"
        f"◽ صف ۴۰ گیگ: <code>{len(config.WAITING_QUEUE['v2_40gb'])}</code> | صف ۵۰ گیگ: <code>{len(config.WAITING_QUEUE['v2_50gb'])}</code> | صف ۶۰ گیگ: <code>{len(config.WAITING_QUEUE['v2_60gb'])}</code>\n"
        f"◽ صف ۷۰ گیگ: <code>{len(config.WAITING_QUEUE['v2_70gb'])}</code> | صف ۸۰ گیگ: <code>{len(config.WAITING_QUEUE['v2_80gb'])}</code> | صف ۹۰ گیگ: <code>{len(config.WAITING_QUEUE['v2_90gb'])}</code>\n"
        f"◽ صف ۱۰۰ گیگ: <code>{len(config.WAITING_QUEUE['v2_100gb'])}</code>\n"
        f"◽ صف اکسپرس تک کاربره: <code>{len(config.WAITING_QUEUE['ex_1user'])}</code> | دو کاربره: <code>{len(config.WAITING_QUEUE['ex_2user'])}</code>"
    )
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]), parse_mode="HTML")

async def admin_add_stock_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "📥 <b>بخش شارژ هوشمند انبار ربات</b>\n\nلطفاً انتخاب کنید قصد دارید به کدام انبار کالا یا کانفیگ جدید اضافه کنید:"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 شارژ ۵ گیگ V2ray", callback_data="add_stock_v2_5"), InlineKeyboardButton("🚀 شارژ ۱۰ گیگ V2ray", callback_data="add_stock_v2_10")],
        [InlineKeyboardButton("🚀 شارژ ۱۵ گیگ V2ray", callback_data="add_stock_v2_15"), InlineKeyboardButton("🚀 شارژ ۲۰ گیگ V2ray", callback_data="add_stock_v2_20")],
        [InlineKeyboardButton("🚀 شارژ ۲۵ گیگ V2ray", callback_data="add_stock_v2_25"), InlineKeyboardButton("🚀 شارژ ۳۰ گیگ V2ray", callback_data="add_stock_v2_30")],
        [InlineKeyboardButton("🚀 شارژ ۴۰ گیگ V2ray", callback_data="add_stock_v2_40"), InlineKeyboardButton("🚀 شارژ ۵۰ گیگ V2ray", callback_data="add_stock_v2_50")],
        [InlineKeyboardButton("🚀 شارژ ۶۰ گیگ V2ray", callback_data="add_stock_v2_60"), InlineKeyboardButton("🚀 شارژ ۷۰ گیگ V2ray", callback_data="add_stock_v2_70")],
        [InlineKeyboardButton("🚀 شارژ ۸۰ گیگ V2ray", callback_data="add_stock_v2_80"), InlineKeyboardButton("🚀 شارژ ۹۰ گیگ V2ray", callback_data="add_stock_v2_90")],
        [InlineKeyboardButton("🚀 شارژ ۱۰۰ گیگ V2ray", callback_data="add_stock_v2_100")],
        [InlineKeyboardButton("🔐 شارژ مخزن اکسپرس", callback_data="add_stock_express")],
        [InlineKeyboardButton("🔙 بازگشت به پنل مدیریت", callback_data="admin_back")]
    ])
    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    return ADMIN_CHOOSE_STOCK_TYPE

async def admin_add_stock_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stock_type = query.data.replace("add_stock_", "")
    context.user_data["selected_stock_type"] = stock_type
    names_dict = {
        "v2_5": "🚀 انبار ۵ گیگابایت V2ray",
        "v2_10": "🚀 انبار ۱۰ گیگابایت V2ray",
        "v2_15": "🚀 انبار ۱۵ گیگابایت V2ray",
        "v2_20": "🚀 انبار ۲۰ گیگابایت V2ray",
        "v2_25": "🚀 انبار ۲۵ گیگابایت V2ray",
        "v2_30": "🚀 انبار ۳۰ گیگابایت V2ray",
        "v2_40": "🚀 انبار ۴۰ گیگابایت V2ray",
        "v2_50": "🚀 انبار ۵۰ گیگابایت V2ray",
        "v2_60": "🚀 انبار ۶۰ گیگابایت V2ray",
        "v2_70": "🚀 انبار ۷۰ گیگابایت V2ray",
        "v2_80": "🚀 انبار ۸۰ گیگابایت V2ray",
        "v2_90": "🚀 انبار ۹۰ گیگابایت V2ray",
        "v2_100": "🚀 انبار ۱۰۰ گیگابایت V2ray",
        "express": "🔐 مخزن مرکزی اکانت‌های اکسپرس",
    }
    text = f"✍️ <b>شما مخزن زیر را انتخاب کردید:</b>\n📍 {names_dict.get(stock_type)}\n\n"
    if stock_type == "express":
        text += "⚠️ <b>نکته بسیار مهم:</b> لطفاً اکانت را دقیقاً به فرمت <code>Username:Password</code> ارسال کنید تا تفکیک شود."
    else:
        text += "👇 لطفاً متن لینک کانفیگ یا لینک اتصال را بنویسید و ارسال کنید:"
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin_back")]]), parse_mode="HTML")
    return ADMIN_GET_STOCK_CONTENT

async def admin_add_stock_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    content = update.message.text.strip()
    stock_type = context.user_data.get("selected_stock_type")

    stock_save_map = {
        "v2_5":   (config.V2RAY_STORAGE_5,   "۵ گیگ",   "v2_5gb"),
        "v2_10":  (config.V2RAY_STORAGE_10,  "۱۰ گیگ",  "v2_10gb"),
        "v2_15":  (config.V2RAY_STORAGE_15,  "۱۵ گیگ",  "v2_15gb"),
        "v2_20":  (config.V2RAY_STORAGE_20,  "۲۰ گیگ",  "v2_20gb"),
        "v2_25":  (config.V2RAY_STORAGE_25,  "۲۵ گیگ",  "v2_25gb"),
        "v2_30":  (config.V2RAY_STORAGE_30,  "۳۰ گیگ",  "v2_30gb"),
        "v2_40":  (config.V2RAY_STORAGE_40,  "۴۰ گیگ",  "v2_40gb"),
        "v2_50":  (config.V2RAY_STORAGE_50,  "۵۰ گیگ",  "v2_50gb"),
        "v2_60":  (config.V2RAY_STORAGE_60,  "۶۰ گیگ",  "v2_60gb"),
        "v2_70":  (config.V2RAY_STORAGE_70,  "۷۰ گیگ",  "v2_70gb"),
        "v2_80":  (config.V2RAY_STORAGE_80,  "۸۰ گیگ",  "v2_80gb"),
        "v2_90":  (config.V2RAY_STORAGE_90,  "۹۰ گیگ",  "v2_90gb"),
        "v2_100": (config.V2RAY_STORAGE_100, "۱۰۰ گیگ", "v2_100gb"),
    }

    if stock_type in stock_save_map:
        storage, label, queue_key = stock_save_map[stock_type]
        storage.append(content)
        save_all_storages()
        await update.message.reply_text(f"✅ به انبار {label} اضافه شد.\n📦 موجودی: <code>{len(storage)}</code>", parse_mode="HTML")
        if queue_key:
            await check_and_deliver_queue(queue_key, context)
    elif stock_type == "express":
        config.EXPRESS_CENTRAL_STORAGE.append(content)
        save_all_storages()
        await update.message.reply_text(f"✅ به مخزن اکسپرس اضافه شد.\n📦 موجودی: <code>{len(config.EXPRESS_CENTRAL_STORAGE)}</code>", parse_mode="HTML")
        await check_and_deliver_queue("ex_1user", context)
        await check_and_deliver_queue("ex_2user", context)
    return await admin_cancel(update, context)

async def admin_full_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        users = database.get_all_users()
        total_users = len(users) if users else 0
    except: users, total_users = {}, 0
    total_balance, users_with_balance = 0, 0
    if users and isinstance(users, dict):
        for uid in users.keys():
            bal = database.get_user_balance(int(uid))
            if bal > 0:
                total_balance += bal
                users_with_balance += 1
    text = (
        "📊 <b>گزارش زنده عملکرد و حسابداری ربات:</b>\n\n"
        f"👥 <b>کل کاربران ثبت شده:</b> <code>{total_users}</code> نفر\n"
        f"💳 <b>کاربران دارای موجودی:</b> <code>{users_with_balance}</code> نفر\n"
        f"💰 <b>مجموع سرمایه امانت در کیف پول‌ها:</b> <code>{total_balance:,}</code> تومان\n"
        f"🚫 <b>تعداد کاربران مسدود شده (لیست سیاه):</b> <code>{len(config.BLACKLISTED_USERS)}</code> نفر"
    )
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]), parse_mode="HTML")

# =====================================================================
# 🛠 مدیریت تفصیلی انبارها (Detailed Storage Management)
# =====================================================================

async def admin_storage_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "🛠 <b>مدیریت تفصیلی انبارها</b>\n\nلطفاً انبار مورد نظر را انتخاب کنید:"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🚀 V2ray ۵ گیگ ({len(config.V2RAY_STORAGE_5)})", callback_data="manage_storage_v2_5")],
        [InlineKeyboardButton(f"🚀 V2ray ۱۰ گیگ ({len(config.V2RAY_STORAGE_10)})", callback_data="manage_storage_v2_10")],
        [InlineKeyboardButton(f"🚀 V2ray ۱۵ گیگ ({len(config.V2RAY_STORAGE_15)})", callback_data="manage_storage_v2_15")],
        [InlineKeyboardButton(f"🚀 V2ray ۲۰ گیگ ({len(config.V2RAY_STORAGE_20)})", callback_data="manage_storage_v2_20")],
        [InlineKeyboardButton(f"🚀 V2ray ۲۵ گیگ ({len(config.V2RAY_STORAGE_25)})", callback_data="manage_storage_v2_25")],
        [InlineKeyboardButton(f"🚀 V2ray ۳۰ گیگ ({len(config.V2RAY_STORAGE_30)})", callback_data="manage_storage_v2_30")],
        [InlineKeyboardButton(f"🚀 V2ray ۴۰ گیگ ({len(config.V2RAY_STORAGE_40)})", callback_data="manage_storage_v2_40")],
        [InlineKeyboardButton(f"🚀 V2ray ۵۰ گیگ ({len(config.V2RAY_STORAGE_50)})", callback_data="manage_storage_v2_50")],
        [InlineKeyboardButton(f"🚀 V2ray ۶۰ گیگ ({len(config.V2RAY_STORAGE_60)})", callback_data="manage_storage_v2_60")],
        [InlineKeyboardButton(f"🚀 V2ray ۷۰ گیگ ({len(config.V2RAY_STORAGE_70)})", callback_data="manage_storage_v2_70")],
        [InlineKeyboardButton(f"🚀 V2ray ۸۰ گیگ ({len(config.V2RAY_STORAGE_80)})", callback_data="manage_storage_v2_80")],
        [InlineKeyboardButton(f"🚀 V2ray ۹۰ گیگ ({len(config.V2RAY_STORAGE_90)})", callback_data="manage_storage_v2_90")],
        [InlineKeyboardButton(f"🚀 V2ray ۱۰۰ گیگ ({len(config.V2RAY_STORAGE_100)})", callback_data="manage_storage_v2_100")],
        [InlineKeyboardButton(f"🔐 اکسپرس ({len(config.EXPRESS_CENTRAL_STORAGE)})", callback_data="manage_storage_express")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
    ])
    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    return ADMIN_MANAGE_STORAGE_MENU

async def admin_storage_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    storage_type = query.data.replace("manage_storage_", "")
    context.user_data["selected_storage"] = storage_type

    storage_map = {
        "v2_5": config.V2RAY_STORAGE_5,
        "v2_10": config.V2RAY_STORAGE_10,
        "v2_15": config.V2RAY_STORAGE_15,
        "v2_20": config.V2RAY_STORAGE_20,
        "v2_25": config.V2RAY_STORAGE_25,
        "v2_30": config.V2RAY_STORAGE_30,
        "v2_40": config.V2RAY_STORAGE_40,
        "v2_50": config.V2RAY_STORAGE_50,
        "v2_60": config.V2RAY_STORAGE_60,
        "v2_70": config.V2RAY_STORAGE_70,
        "v2_80": config.V2RAY_STORAGE_80,
        "v2_90": config.V2RAY_STORAGE_90,
        "v2_100": config.V2RAY_STORAGE_100,
        "express": config.EXPRESS_CENTRAL_STORAGE,
    }

    names_map = {
        "v2_5": "🚀 V2ray ۵ گیگابایت",
        "v2_10": "🚀 V2ray ۱۰ گیگابایت",
        "v2_15": "🚀 V2ray ۱۵ گیگابایت",
        "v2_20": "🚀 V2ray ۲۰ گیگابایت",
        "v2_25": "🚀 V2ray ۲۵ گیگابایت",
        "v2_30": "🚀 V2ray ۳۰ گیگابایت",
        "v2_40": "🚀 V2ray ۴۰ گیگابایت",
        "v2_50": "🚀 V2ray ۵۰ گیگابایت",
        "v2_60": "🚀 V2ray ۶۰ گیگابایت",
        "v2_70": "🚀 V2ray ۷۰ گیگابایت",
        "v2_80": "🚀 V2ray ۸۰ گیگابایت",
        "v2_90": "🚀 V2ray ۹۰ گیگابایت",
        "v2_100": "🚀 V2ray ۱۰۰ گیگابایت",
        "express": "🔐 اکانت‌های اکسپرس",
    }

    storage = storage_map.get(storage_type, [])
    text = f"📍 <b>انبار انتخاب‌شده:</b> {names_map.get(storage_type)}\n\n"
    text += f"📊 <b>تعداد آیتم‌ها:</b> <code>{len(storage)}</code>\n\n"
    text += "👇 <b>عملیات موردنظر را انتخاب کنید:</b>"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 مشاهده آیتم‌ها", callback_data=f"view_storage_{storage_type}")],
        [InlineKeyboardButton("➕ اضافه کردن آیتم", callback_data=f"add_storage_item_{storage_type}")],
        [InlineKeyboardButton("➖ حذف آیتم", callback_data=f"remove_storage_item_{storage_type}")],
        [InlineKeyboardButton("🗑 خالی کردن کل انبار", callback_data=f"clear_storage_{storage_type}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_storage_manager")]
    ])

    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    return ADMIN_MANAGE_STORAGE_MENU

async def admin_view_storage_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    storage_type = query.data.replace("view_storage_", "")

    storage_map = {
        "v2_5": config.V2RAY_STORAGE_5,
        "v2_10": config.V2RAY_STORAGE_10,
        "v2_15": config.V2RAY_STORAGE_15,
        "v2_20": config.V2RAY_STORAGE_20,
        "v2_25": config.V2RAY_STORAGE_25,
        "v2_30": config.V2RAY_STORAGE_30,
        "v2_40": config.V2RAY_STORAGE_40,
        "v2_50": config.V2RAY_STORAGE_50,
        "v2_60": config.V2RAY_STORAGE_60,
        "v2_70": config.V2RAY_STORAGE_70,
        "v2_80": config.V2RAY_STORAGE_80,
        "v2_90": config.V2RAY_STORAGE_90,
        "v2_100": config.V2RAY_STORAGE_100,
        "express": config.EXPRESS_CENTRAL_STORAGE,
    }

    names_map = {
        "v2_5": "V2ray ۵ گیگابایت",
        "v2_10": "V2ray ۱۰ گیگابایت",
        "v2_15": "V2ray ۱۵ گیگابایت",
        "v2_20": "V2ray ۲۰ گیگابایت",
        "v2_25": "V2ray ۲۵ گیگابایت",
        "v2_30": "V2ray ۳۰ گیگابایت",
        "v2_40": "V2ray ۴۰ گیگابایت",
        "v2_50": "V2ray ۵۰ گیگابایت",
        "v2_60": "V2ray ۶۰ گیگابایت",
        "v2_70": "V2ray ۷۰ گیگابایت",
        "v2_80": "V2ray ۸۰ گیگابایت",
        "v2_90": "V2ray ۹۰ گیگابایت",
        "v2_100": "V2ray ۱۰۰ گیگابایت",
        "express": "اکانت‌های اکسپرس",
    }

    storage = storage_map.get(storage_type, [])

    if not storage:
        text = f"📋 <b>لیست آیتم‌های {names_map.get(storage_type)}</b>\n\n⚠️ انبار خالی است."
    else:
        text = f"📋 <b>لیست آیتم‌های {names_map.get(storage_type)}</b>\n\n<b>تعداد کل:</b> {len(storage)}\n\n"
        for idx, item in enumerate(storage[:50], 1):
            if len(item) > 60:
                preview = item[:57] + "..."
            else:
                preview = item
            text += f"{idx}. <code>{preview}</code>\n"
        if len(storage) > 50:
            text += f"\n... و {len(storage) - 50} آیتم دیگر"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"manage_storage_{storage_type}")]
    ])

    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")

async def admin_add_storage_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    storage_type = query.data.replace("add_storage_item_", "")
    context.user_data["selected_storage"] = storage_type

    names_map = {
        "v2_5": "V2ray ۵ گیگابایت",
        "v2_10": "V2ray ۱۰ گیگابایت",
        "v2_15": "V2ray ۱۵ گیگابایت",
        "v2_20": "V2ray ۲۰ گیگابایت",
        "v2_25": "V2ray ۲۵ گیگابایت",
        "v2_30": "V2ray ۳۰ گیگابایت",
        "v2_40": "V2ray ۴۰ گیگابایت",
        "v2_50": "V2ray ۵۰ گیگابایت",
        "v2_60": "V2ray ۶۰ گیگابایت",
        "v2_70": "V2ray ۷۰ گیگابایت",
        "v2_80": "V2ray ۸۰ گیگابایت",
        "v2_90": "V2ray ۹۰ گیگابایت",
        "v2_100": "V2ray ۱۰۰ گیگابایت",
        "express": "اکانت‌های اکسپرس",
    }

    text = f"➕ <b>اضافه کردن آیتم به {names_map.get(storage_type)}</b>\n\n"
    if storage_type == "express":
        text += "⚠️ لطفاً اکانت را به فرمت <code>Username:Password</code> ارسال کنید:"
    else:
        text += "لطفاً لینک یا متن اتصال را ارسال کنید:"

    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data=f"manage_storage_{storage_type}")]]), parse_mode="HTML")
    return ADMIN_ADD_STORAGE_ITEM

async def admin_add_storage_item_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    content = update.message.text.strip()
    storage_type = context.user_data.get("selected_storage")

    storage_map = {
        "v2_5": config.V2RAY_STORAGE_5,
        "v2_10": config.V2RAY_STORAGE_10,
        "v2_15": config.V2RAY_STORAGE_15,
        "v2_20": config.V2RAY_STORAGE_20,
        "v2_25": config.V2RAY_STORAGE_25,
        "v2_30": config.V2RAY_STORAGE_30,
        "v2_40": config.V2RAY_STORAGE_40,
        "v2_50": config.V2RAY_STORAGE_50,
        "v2_60": config.V2RAY_STORAGE_60,
        "v2_70": config.V2RAY_STORAGE_70,
        "v2_80": config.V2RAY_STORAGE_80,
        "v2_90": config.V2RAY_STORAGE_90,
        "v2_100": config.V2RAY_STORAGE_100,
        "express": config.EXPRESS_CENTRAL_STORAGE,
    }

    names_map = {
        "v2_5": "V2ray ۵ گیگابایت",
        "v2_10": "V2ray ۱۰ گیگابایت",
        "v2_15": "V2ray ۱۵ گیگابایت",
        "v2_20": "V2ray ۲۰ گیگابایت",
        "v2_25": "V2ray ۲۵ گیگابایت",
        "v2_30": "V2ray ۳۰ گیگابایت",
        "v2_40": "V2ray ۴۰ گیگابایت",
        "v2_50": "V2ray ۵۰ گیگابایت",
        "v2_60": "V2ray ۶۰ گیگابایت",
        "v2_70": "V2ray ۷۰ گیگابایت",
        "v2_80": "V2ray ۸۰ گیگابایت",
        "v2_90": "V2ray ۹۰ گیگابایت",
        "v2_100": "V2ray ۱۰۰ گیگابایت",
        "express": "اکانت‌های اکسپرس",
    }

    storage = storage_map.get(storage_type)
    if storage is not None:
        storage.append(content)
        save_all_storages()
        await update.message.reply_text(f"✅ <b>آیتم با موفقیت اضافه شد!</b>\n\nانبار {names_map.get(storage_type)}\n📊 تعداد فعلی: <code>{len(storage)}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ خطای نامشخص", parse_mode="HTML")

    return await admin_cancel(update, context)

async def admin_remove_storage_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    storage_type = query.data.replace("remove_storage_item_", "")
    context.user_data["selected_storage"] = storage_type

    storage_map = {
        "v2_5": config.V2RAY_STORAGE_5,
        "v2_10": config.V2RAY_STORAGE_10,
        "v2_15": config.V2RAY_STORAGE_15,
        "v2_20": config.V2RAY_STORAGE_20,
        "v2_25": config.V2RAY_STORAGE_25,
        "v2_30": config.V2RAY_STORAGE_30,
        "v2_40": config.V2RAY_STORAGE_40,
        "v2_50": config.V2RAY_STORAGE_50,
        "v2_60": config.V2RAY_STORAGE_60,
        "v2_70": config.V2RAY_STORAGE_70,
        "v2_80": config.V2RAY_STORAGE_80,
        "v2_90": config.V2RAY_STORAGE_90,
        "v2_100": config.V2RAY_STORAGE_100,
        "express": config.EXPRESS_CENTRAL_STORAGE,
    }

    names_map = {
        "v2_5": "V2ray ۵ گیگابایت",
        "v2_10": "V2ray ۱۰ گیگابایت",
        "v2_15": "V2ray ۱۵ گیگابایت",
        "v2_20": "V2ray ۲۰ گیگابایت",
        "v2_25": "V2ray ۲۵ گیگابایت",
        "v2_30": "V2ray ۳۰ گیگابایت",
        "v2_40": "V2ray ۴۰ گیگابایت",
        "v2_50": "V2ray ۵۰ گیگابایت",
        "v2_60": "V2ray ۶۰ گیگابایت",
        "v2_70": "V2ray ۷۰ گیگابایت",
        "v2_80": "V2ray ۸۰ گیگابایت",
        "v2_90": "V2ray ۹۰ گیگابایت",
        "v2_100": "V2ray ۱۰۰ گیگابایت",
        "express": "اکانت‌های اکسپرس",
    }

    storage = storage_map.get(storage_type, [])
    text = f"➖ <b>حذف آیتم از {names_map.get(storage_type)}</b>\n\n"
    text += f"📊 تعداد کل آیتم‌ها: <code>{len(storage)}</code>\n\n"
    text += "🔹 <b>شماره آیتم</b> را وارد کنید (مثلاً: 1, 2, 3)\n"
    text += "🔹 یا برای حذف آخرین آیتم عدد <code>0</code> را ارسال کنید:"

    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data=f"manage_storage_{storage_type}")]]), parse_mode="HTML")
    return ADMIN_REMOVE_STORAGE_ITEM

async def admin_remove_storage_item_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip().translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))

    if not user_input.isdigit():
        await update.message.reply_text("❌ فقط عدد وارد کنید:")
        return ADMIN_REMOVE_STORAGE_ITEM

    storage_type = context.user_data.get("selected_storage")
    storage_map = {
        "v2_5": config.V2RAY_STORAGE_5,
        "v2_10": config.V2RAY_STORAGE_10,
        "v2_15": config.V2RAY_STORAGE_15,
        "v2_20": config.V2RAY_STORAGE_20,
        "v2_25": config.V2RAY_STORAGE_25,
        "v2_30": config.V2RAY_STORAGE_30,
        "v2_40": config.V2RAY_STORAGE_40,
        "v2_50": config.V2RAY_STORAGE_50,
        "v2_60": config.V2RAY_STORAGE_60,
        "v2_70": config.V2RAY_STORAGE_70,
        "v2_80": config.V2RAY_STORAGE_80,
        "v2_90": config.V2RAY_STORAGE_90,
        "v2_100": config.V2RAY_STORAGE_100,
        "express": config.EXPRESS_CENTRAL_STORAGE,
    }

    names_map = {
        "v2_5": "V2ray ۵ گیگابایت",
        "v2_10": "V2ray ۱۰ گیگابایت",
        "v2_15": "V2ray ۱۵ گیگابایت",
        "v2_20": "V2ray ۲۰ گیگابایت",
        "v2_25": "V2ray ۲۵ گیگابایت",
        "v2_30": "V2ray ۳۰ گیگابایت",
        "v2_40": "V2ray ۴۰ گیگابایت",
        "v2_50": "V2ray ۵۰ گیگابایت",
        "v2_60": "V2ray ۶۰ گیگابایت",
        "v2_70": "V2ray ۷۰ گیگابایت",
        "v2_80": "V2ray ۸۰ گیگابایت",
        "v2_90": "V2ray ۹۰ گیگابایت",
        "v2_100": "V2ray ۱۰۰ گیگابایت",
        "express": "اکانت‌های اکسپرس",
    }

    storage = storage_map.get(storage_type, [])
    index = int(user_input)

    if index == 0:
        if storage:
            removed = storage.pop()
            save_all_storages()
            await update.message.reply_text(f"✅ <b>آخرین آیتم حذف شد!</b>\n\nانبار {names_map.get(storage_type)}\n📊 تعداد فعلی: <code>{len(storage)}</code>", parse_mode="HTML")
        else:
            await update.message.reply_text("⚠️ انبار خالی است", parse_mode="HTML")
    else:
        if 1 <= index <= len(storage):
            removed = storage.pop(index - 1)
            save_all_storages()
            await update.message.reply_text(f"✅ <b>آیتم شماره {index} حذف شد!</b>\n\nانبار {names_map.get(storage_type)}\n📊 تعداد فعلی: <code>{len(storage)}</code>", parse_mode="HTML")
        else:
            await update.message.reply_text(f"❌ شماره نامعتبر است. (۱ تا {len(storage)})", parse_mode="HTML")
            return ADMIN_REMOVE_STORAGE_ITEM

    return await admin_cancel(update, context)

async def admin_clear_storage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    storage_type = query.data.replace("clear_storage_", "")

    storage_map = {
        "v2_5": config.V2RAY_STORAGE_5,
        "v2_10": config.V2RAY_STORAGE_10,
        "v2_15": config.V2RAY_STORAGE_15,
        "v2_20": config.V2RAY_STORAGE_20,
        "v2_25": config.V2RAY_STORAGE_25,
        "v2_30": config.V2RAY_STORAGE_30,
        "v2_40": config.V2RAY_STORAGE_40,
        "v2_50": config.V2RAY_STORAGE_50,
        "v2_60": config.V2RAY_STORAGE_60,
        "v2_70": config.V2RAY_STORAGE_70,
        "v2_80": config.V2RAY_STORAGE_80,
        "v2_90": config.V2RAY_STORAGE_90,
        "v2_100": config.V2RAY_STORAGE_100,
        "express": config.EXPRESS_CENTRAL_STORAGE,
    }

    names_map = {
        "v2_5": "V2ray ۵ گیگابایت",
        "v2_10": "V2ray ۱۰ گیگابایت",
        "v2_15": "V2ray ۱۵ گیگابایت",
        "v2_20": "V2ray ۲۰ گیگابایت",
        "v2_25": "V2ray ۲۵ گیگابایت",
        "v2_30": "V2ray ۳۰ گیگابایت",
        "v2_40": "V2ray ۴۰ گیگابایت",
        "v2_50": "V2ray ۵۰ گیگابایت",
        "v2_60": "V2ray ۶۰ گیگابایت",
        "v2_70": "V2ray ۷۰ گیگابایت",
        "v2_80": "V2ray ۸۰ گیگابایت",
        "v2_90": "V2ray ۹۰ گیگابایت",
        "v2_100": "V2ray ۱۰۰ گیگابایت",
        "express": "اکانت‌های اکسپرس",
    }

    text = f"🗑 <b>تایید: خالی کردن کل انبار {names_map.get(storage_type)}</b>\n\n"
    text += f"⚠️ <b>این عملیات غیرقابل‌برگشت است!</b>\n"
    text += f"📊 تعداد آیتم‌هایی که حذف خواهند شد: <code>{len(storage_map.get(storage_type, []))}</code>"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تایید و حذف", callback_data=f"confirm_clear_{storage_type}"), InlineKeyboardButton("❌ انصراف", callback_data=f"manage_storage_{storage_type}")]
    ])

    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")

async def admin_confirm_clear_storage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    storage_type = query.data.replace("confirm_clear_", "")

    storage_map = {
        "v2_5": config.V2RAY_STORAGE_5,
        "v2_10": config.V2RAY_STORAGE_10,
        "v2_15": config.V2RAY_STORAGE_15,
        "v2_20": config.V2RAY_STORAGE_20,
        "v2_25": config.V2RAY_STORAGE_25,
        "v2_30": config.V2RAY_STORAGE_30,
        "v2_40": config.V2RAY_STORAGE_40,
        "v2_50": config.V2RAY_STORAGE_50,
        "v2_60": config.V2RAY_STORAGE_60,
        "v2_70": config.V2RAY_STORAGE_70,
        "v2_80": config.V2RAY_STORAGE_80,
        "v2_90": config.V2RAY_STORAGE_90,
        "v2_100": config.V2RAY_STORAGE_100,
        "express": config.EXPRESS_CENTRAL_STORAGE,
    }

    names_map = {
        "v2_5": "V2ray ۵ گیگابایت",
        "v2_10": "V2ray ۱۰ گیگابایت",
        "v2_15": "V2ray ۱۵ گیگابایت",
        "v2_20": "V2ray ۲۰ گیگابایت",
        "v2_25": "V2ray ۲۵ گیگابایت",
        "v2_30": "V2ray ۳۰ گیگابایت",
        "v2_40": "V2ray ۴۰ گیگابایت",
        "v2_50": "V2ray ۵۰ گیگابایت",
        "v2_60": "V2ray ۶۰ گیگابایت",
        "v2_70": "V2ray ۷۰ گیگابایت",
        "v2_80": "V2ray ۸۰ گیگابایت",
        "v2_90": "V2ray ۹۰ گیگابایت",
        "v2_100": "V2ray ۱۰۰ گیگابایت",
        "express": "اکانت‌های اکسپرس",
    }

    storage = storage_map.get(storage_type, [])
    count = len(storage)
    storage.clear()
    save_all_storages()

    await query.edit_message_text(text=f"🗑 <b>انبار {names_map.get(storage_type)} خالی شد!</b>\n\n✅ تعداد حذف‌شده: <code>{count}</code>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_storage_manager")]]), parse_mode="HTML")


def generate_account_username(first_name: str) -> str:
    clean_name = "".join(e for e in first_name if e.isalnum()) or "User"
    acc_user = f"{clean_name}_{config.ACCOUNT_COUNTER}"
    config.increment_account_counter() 
    return acc_user

def format_express_account(acc_string: str, index: int = None) -> str:
    prefix = f"🔹 <b>دستگاه شماره {index}</b>:\n" if index else ""
    if ":" in acc_string:
        username, password = acc_string.split(":", 1)
        return f"{prefix}👤 <b>یوزرنیم:</b>\n<code>{username.strip()}</code>\n🔑 <b>پسورد:</b>\n<code>{password.strip()}</code>\n"
    return f"{prefix}📄 <b>اطلاعات اکانت:</b>\n<code>{acc_string}</code>\n"

async def check_and_deliver_queue(plan_id: str, context: ContextTypes.DEFAULT_TYPE):
    v2ray_queue_storage_map = {
        "v2_5gb": config.V2RAY_STORAGE_5,
        "v2_10gb": config.V2RAY_STORAGE_10,
        "v2_15gb": config.V2RAY_STORAGE_15,
        "v2_20gb": config.V2RAY_STORAGE_20,
        "v2_25gb": config.V2RAY_STORAGE_25,
        "v2_30gb": config.V2RAY_STORAGE_30,
        "v2_40gb": config.V2RAY_STORAGE_40,
        "v2_50gb": config.V2RAY_STORAGE_50,
        "v2_60gb": config.V2RAY_STORAGE_60,
        "v2_70gb": config.V2RAY_STORAGE_70,
        "v2_80gb": config.V2RAY_STORAGE_80,
        "v2_90gb": config.V2RAY_STORAGE_90,
        "v2_100gb": config.V2RAY_STORAGE_100,
    }

    if plan_id in v2ray_queue_storage_map:
        storage = v2ray_queue_storage_map[plan_id]
        plan_name = V2RAY_PLANS[plan_id]["name"]
    elif plan_id in ["ex_1user", "ex_2user"]:
        plan_name = EXPRESS_PLANS[plan_id]["name"]
    else:
        return

    if plan_id in v2ray_queue_storage_map:
        while storage and config.WAITING_QUEUE[plan_id]:
            waiting_user_id = config.WAITING_QUEUE[plan_id].pop(0)
            delivered_item = storage.pop(0)
            save_all_storages()
            try:
                chat_member = await context.bot.get_chat(waiting_user_id)
                user_name_identifier = generate_account_username(chat_member.first_name)
                u_info = f"{chat_member.first_name}"
            except:
                user_name_identifier = generate_account_username("User")
                u_info = f"<code>{waiting_user_id}</code>"
            database.add_order(waiting_user_id, user_name_identifier, plan_name, 0, f"🔗 <b>لینک اتصال:</b>\n<code>{delivered_item}</code>")
            try:
                remaining = len(storage)
                await context.bot.send_message(chat_id=waiting_user_id, text=f"🎉 <b>اشتراک شما آماده شد!</b>\n\n📦 سرویس <b>{plan_name}</b> شارژ شد:\n🆔 <b>نام اشتراک:</b> <code>{user_name_identifier}</code>\n\n🔗 <b>لینک اتصال:</b>\n<code>{delivered_item}</code>\n\n📦 از انبار <b>{plan_name}</b> تحویل شد. موجودی باقی‌مانده: <code>{remaining}</code>", parse_mode="HTML")
                await context.bot.send_message(chat_id=ADMIN_ID, text=f"✅ <b>تحویل موفقیت‌آمیز از صف انتظار</b>\n\n📦 پلن <b>{plan_name}</b> با موفقیت به کاربر {u_info} (<code>{waiting_user_id}</code>) که در صف بود تحویل داده شد.\n📦 موجودی باقی‌مانده در انبار: <code>{remaining}</code>", parse_mode="HTML")
            except:
                pass
            await stock_alert.check_and_notify_low_stock(context, trigger_event=f"تحویل از صف {plan_name} به کاربر {u_info}")
    else:
        while config.WAITING_QUEUE[plan_id]:
            needed_count = 1 if plan_id == "ex_1user" else 2
            if len(config.EXPRESS_CENTRAL_STORAGE) < needed_count: break
            waiting_user_id = config.WAITING_QUEUE[plan_id].pop(0)
            items_to_deliver = [config.EXPRESS_CENTRAL_STORAGE.pop(0) for _ in range(needed_count)]
            save_all_storages()
            try:
                chat_member = await context.bot.get_chat(waiting_user_id)
                user_name_identifier = generate_account_username(chat_member.first_name)
                u_info = f"{chat_member.first_name}"
            except:
                user_name_identifier = generate_account_username("User")
                u_info = f"<code>{waiting_user_id}</code>"
            formatted_accounts = ""
            for idx, acc in enumerate(items_to_deliver, 1):
                formatted_accounts += format_express_account(acc, idx if needed_count > 1 else None) + "\n"
            database.add_order(waiting_user_id, user_name_identifier, plan_name, 0, formatted_accounts)
            try:
                remaining = len(config.EXPRESS_CENTRAL_STORAGE)
                await context.bot.send_message(chat_id=waiting_user_id, text=f"🎉 <b>اشتراک اکسپرس شما آماده شد!</b>\n\n📦 سرویس <b>{plan_name}</b> شارژ شد:\n🆔 <b>شناسه خرید:</b> <code>{user_name_identifier}</code>\n\n{formatted_accounts}\n📦 از مخزن اکسپرس تحویل شد. موجودی باقی‌مانده: <code>{remaining}</code>", parse_mode="HTML")
                await context.bot.send_message(chat_id=ADMIN_ID, text=f"✅ <b>تحویل موفقیت‌آمیز از صف اکسپرس</b>\n\n🔐 اکانت اکسپرس با موفقیت به کاربر {u_info} (<code>{waiting_user_id}</code>) تحویل داده شد.\n📦 موجودی باقی‌مانده در مخزن اکسپرس: <code>{remaining}</code>", parse_mode="HTML")
            except:
                pass
            await stock_alert.check_and_notify_low_stock(context, trigger_event=f"تحویل از صف اکسپرس {plan_name} به کاربر {u_info}")

# =====================================================================
# 👤 منوهای کاربری ربات (User Interface Commands)
# =====================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_user_blacklisted(user.id):
        if update.message: await update.message.reply_text("❌ شما مسدود شده‌اید.")
        return -1
    is_new_user = database.get_user_data(user.id) is None
    database.add_user(user.id) 
    if is_new_user and context.args:
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user.id:
                database.update_user_field(user.id, "referred_by", referrer_id)
        except ValueError: pass
    if not await check_joined_channels(user.id, context):
        await send_join_request_message(update, context, is_callback=bool(update.callback_query))
        return -1
    return await process_successful_entry(user.id, update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, override_text=None):
    user = update.effective_user
    welcome_text = override_text if override_text else f"👋 <b>سلام {user.first_name} عزیز</b>\nبه ربات خدمات ما خوش آمدید.\n\n🎯 لطفاً از منوی زیر انتخاب کنید:"
    keyboard = [
        [InlineKeyboardButton("🛒 خرید اشتراک ویژه", callback_data="buy_subscription"), InlineKeyboardButton("💰 کیف پول من", callback_data="wallet")],
        [InlineKeyboardButton("📚 بخش آموزش‌ها", callback_data="tutorials"), InlineKeyboardButton("📋 تاریخچه خریدها", callback_data="user_history")],
        [InlineKeyboardButton("🤝 دعوت از دوستان", callback_data="invite_friends"), InlineKeyboardButton("🆘 پشتیبانی آنلاین", callback_data="support")]
    ]
    if update.message:
        await update.message.reply_text(text=welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text=welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return -1

async def invite_friends_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if is_user_blacklisted(user_id) or not await check_joined_channels(user_id, context):
        return

    await query.answer()

    referral_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

    user_data = database.get_user_data(user_id)
    invited_count = user_data.get("total_invited", 0) if user_data else 0

    text = (
        "🎁 <b>برنامه هدیه‌های ویژه و مکافات دوستان</b>\n\n"
        "دوستان خود را به ربات ما دعوت کنید و هدیه‌های جذاب دریافت کنید!\n\n"
        f"💝 <b>سیستم مکافات:</b>\n"
        f"  🎯 برای هر دوستی که دعوت می‌کنید: <code>{REFERRER_REWARD:,}</code> تومان\n"
        f"  🎁 دوست شما دریافت می‌کند: <code>{REFERREE_REWARD:,}</code> تومان\n\n"
        f"⚡ <b>شرایط:</b>\n"
        f"  ✓ دوست شما باید وارد ربات شود\n"
        f"  ✓ دوست شما باید تمام کانال‌های اسپانسر را join کند\n"
        f"  ✓ خودکار برای هر دو نفر ثبت می‌شود!\n\n"
        f"📊 <b>آمار دعوت‌های شما:</b>\n"
        f"  تعداد دوستان دعوت شده: <code>{invited_count}</code> نفر\n"
        f"  درآمد کسب شده: <code>{invited_count * REFERRER_REWARD:,}</code> تومان\n\n"
        f"🔗 <b>لینک اختصاصی شما:</b>\n<code>{referral_link}</code>"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 کپی لینک دعوت", switch_inline_query=f"\n🚀 با لینک من وارد ربات شو و {REFERREE_REWARD:,} تومان هدیه بگیر:\n{referral_link}")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
    ])

    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")

async def buy_subscription_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if is_user_blacklisted(query.from_user.id) or not await check_joined_channels(query.from_user.id, context): return
    await query.answer()
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔐 Express VPN", callback_data="buy_express"), InlineKeyboardButton("🚀 V2ray", callback_data="buy_v2ray")],[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]])
    await query.edit_message_text(text="🛒 <b>بخش خرید اشتراک ویژه</b>\n\nلطفاً نوع سرویس خود را انتخاب کنید:", reply_markup=keyboard, parse_mode="HTML")

async def v2ray_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if is_user_blacklisted(query.from_user.id) or not await check_joined_channels(query.from_user.id, context): return
    await query.answer()
    text = "🚀 <b>سرویس‌های پرسرعت V2ray</b>\n\n⏱ زمان مانیتورینگ: <b>۳۰ روزه کامل</b>\n👥 تعداد کاربر: <b>نامحدود</b>\n\n👇 حجم پلن مورد نظر خود را جهت خرید انتخاب کنید:"
    if GLOBAL_DISCOUNT > 0: text = f"🔥 <b>جشنواره تخفیف فوق‌العاده ویژه (% {GLOBAL_DISCOUNT} تخفیف)</b> 🔥\n\n" + text
    keyboard = []
    for plan_id, plan_data in V2RAY_PLANS.items():
        final_price = get_discounted_price(plan_data['price'])
        if GLOBAL_DISCOUNT <= 0:
            price_text = f"قیمت: {final_price:,} تومان"
        else:
            discount_amount = plan_data['price'] - final_price
            price_text = f"اصلی: {plan_data['price']:,} | تخفیف: {discount_amount:,} | نهایی: {final_price:,}"
        keyboard.append([InlineKeyboardButton(f"{plan_data['name']} | {price_text}", callback_data=f"order_{plan_id}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="buy_subscription")])
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def express_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if is_user_blacklisted(query.from_user.id) or not await check_joined_channels(query.from_user.id, context): return
    await query.answer()
    text = "🔐 <b>سرویس‌های اورجینال Express VPN</b>\n\n⏱ اعتبار: <b>۳ ماهه کامل</b> | ترافیک: <b>نامحدود</b>\n\n👇 نوع اکانت خود را انتخاب کنید:"
    if GLOBAL_DISCOUNT > 0: text = f"🔥 <b>جشنواره تخفیف ویژه (% {GLOBAL_DISCOUNT} تخفیف)</b> 🔥\n\n" + text
    keyboard = []
    for plan_id, plan_data in EXPRESS_PLANS.items():
        final_price = get_discounted_price(plan_data['price'])
        if GLOBAL_DISCOUNT <= 0:
            price_text = f"قیمت: {final_price:,} تومان"
        else:
            discount_amount = plan_data['price'] - final_price
            price_text = f"اصلی: {plan_data['price']:,} | تخفیف: {discount_amount:,} | نهایی: {final_price:,}"
        keyboard.append([InlineKeyboardButton(f"{plan_data['name']} | {price_text}", callback_data=f"order_{plan_id}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="buy_subscription")])
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def process_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if is_user_blacklisted(user_id) or not await check_joined_channels(user_id, context): return
    await query.answer()
    first_name = html.escape(query.from_user.first_name)
    username = html.escape(f"@{query.from_user.username}" if query.from_user.username else "بدون یوزرنیم")
    plan_id = query.data.replace("order_", "")
    is_v2ray = plan_id in V2RAY_PLANS
    plan = V2RAY_PLANS.get(plan_id) if is_v2ray else EXPRESS_PLANS.get(plan_id)
    if not plan: return
    user_balance = database.get_user_balance(user_id)
    plan_price = get_discounted_price(plan["price"])
    if user_balance < plan_price:
        shortage = plan_price - user_balance
        await query.edit_message_text(text=f"❌ <b>موجودی کافی نیست!</b>\n\n💰 قیمت: <code>{plan_price:,}</code> تومان\n💵 موجودی: <code>{user_balance:,}</code> تومان\n📉 کسری: <code>{shortage:,}</code> تومان", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚡ شارژ حساب", callback_data="charge_wallet")],[InlineKeyboardButton("🔙 بازگشت", callback_data="buy_v2ray" if is_v2ray else "buy_express")]]), parse_mode="HTML")
        return

    if is_v2ray:
        v2ray_storage_map = {
            "v2_5gb": config.V2RAY_STORAGE_5,
            "v2_10gb": config.V2RAY_STORAGE_10,
            "v2_15gb": config.V2RAY_STORAGE_15,
            "v2_20gb": config.V2RAY_STORAGE_20,
            "v2_25gb": config.V2RAY_STORAGE_25,
            "v2_30gb": config.V2RAY_STORAGE_30,
            "v2_40gb": config.V2RAY_STORAGE_40,
            "v2_50gb": config.V2RAY_STORAGE_50,
            "v2_60gb": config.V2RAY_STORAGE_60,
            "v2_70gb": config.V2RAY_STORAGE_70,
            "v2_80gb": config.V2RAY_STORAGE_80,
            "v2_90gb": config.V2RAY_STORAGE_90,
            "v2_100gb": config.V2RAY_STORAGE_100,
        }
        storage = v2ray_storage_map.get(plan_id)
        if storage is not None and len(storage) > 0:
            delivered = storage.pop(0)
            save_all_storages()
            database.update_user_balance(user_id, -plan_price)
            new_balance = database.get_user_balance(user_id)
            user_name_identifier = generate_account_username(first_name)
            database.add_order(user_id, user_name_identifier, plan['name'], plan_price, f"🔗 <b>لینک اتصال:</b>\n<code>{delivered}</code>")
            balance_text = f"💵 موجودی: {new_balance:,} تومان\n" if plan_id == "v2_20gb" else ""
            remaining = len(storage)
            await query.edit_message_text(text=f"🎉 <b>خرید موفق:</b>\n\n{balance_text}🆔 <b>شناسه:</b> <code>{user_name_identifier}</code>\n\n<code>{delivered}</code>\n\n📦 از انبار <b>{plan['name']}</b> تحویل شد. موجودی باقی‌مانده: <code>{remaining}</code>", reply_markup=CANCEL_KEYBOARD, parse_mode="HTML")
            try: await context.bot.send_message(chat_id=ADMIN_ID, text=f"🛍 <b>گزارش خرید جدید</b>\n\n👤 خریدار: {first_name} ({username})\n📦 سرویس: <b>{plan['name']}</b>\n💵 قیمت: <code>{plan_price:,}</code> تومان\n📦 موجودی باقی‌مانده در انبار: <code>{remaining}</code>", parse_mode="HTML")
            except Exception as e: logging.error(f"Failed to send admin message: {e}")
            await stock_alert.check_and_notify_low_stock(context, trigger_event=f"خرید {plan['name']} توسط {first_name}")
        else:
            database.update_user_balance(user_id, -plan_price)
            config.WAITING_QUEUE[plan_id].append(user_id)
            save_all_storages()
            await query.edit_message_text(text=f"💸 مبلغ <code>{plan_price:,}</code> تومان از حساب شما کسر شد.\n\n⏳ شما در <b>صف انتظار</b> پلن <b>{plan['name']}</b> قرار گرفتید.\nبه محض شارژ انبار، اشتراک شما به صورت خودکار تحویل داده خواهد شد.", reply_markup=CANCEL_KEYBOARD, parse_mode="HTML")
            try: await context.bot.send_message(chat_id=ADMIN_ID, text=f"⚠️ <b>هشدار کمبود انبار و تشکیل صف!</b>\n\n👤 کاربر: {first_name} ({username})\n📦 پلن: <b>{plan['name']}</b>\n📥 کاربر وارد صف انتظار شد.", parse_mode="HTML")
            except Exception as e: logging.error(f"Failed to send queue alert: {e}")
    else:
        needed_count = 1 if plan_id == "ex_1user" else 2
        if len(config.EXPRESS_CENTRAL_STORAGE) >= needed_count:
            items_to_deliver = [config.EXPRESS_CENTRAL_STORAGE.pop(0) for _ in range(needed_count)]
            save_all_storages()
            user_name_identifier = generate_account_username(first_name)
            formatted_accounts = ""
            for idx, acc in enumerate(items_to_deliver, 1): formatted_accounts += format_express_account(acc, idx if needed_count > 1 else None) + "\n"
            database.add_order(user_id, user_name_identifier, plan['name'], plan_price, formatted_accounts)
            remaining = len(config.EXPRESS_CENTRAL_STORAGE)
            await query.edit_message_text(text=f"🎉 <b>خرید موفق:</b>\n\n🆔 <b>شناسه:</b> <code>{user_name_identifier}</code>\n\n{formatted_accounts}\n📦 از مخزن اکسپرس تحویل شد. موجودی باقی‌مانده: <code>{remaining}</code>", reply_markup=CANCEL_KEYBOARD, parse_mode="HTML")
            try: await context.bot.send_message(chat_id=ADMIN_ID, text=f"🛍 <b>گزارش خرید جدید Express</b>\n\n👤 خریدار: {first_name} ({username})\n📦 سرویس: <b>{plan['name']}</b>\n💵 قیمت: <code>{plan_price:,}</code> تومان\n📦 موجودی باقی‌مانده در مخزن اکسپرس: <code>{remaining}</code>", parse_mode="HTML")
            except: pass
            await stock_alert.check_and_notify_low_stock(context, trigger_event=f"خرید {plan['name']} توسط {first_name}")
        else:
            config.WAITING_QUEUE[plan_id].append(user_id)
            save_all_storages()
            await query.edit_message_text(text=f"💸 مبلغ <code>{plan_price:,}</code> تومان از حساب شما کسر شد.\n\n⏳ شما در <b>صف انتظار</b> پلن <b>{plan['name']}</b> قرار گرفتید.\nبه محض شارژ انبار، اشتراک شما به صورت خودکار تحویل داده خواهد شد.", reply_markup=CANCEL_KEYBOARD, parse_mode="HTML")
            try: await context.bot.send_message(chat_id=ADMIN_ID, text=f"⚠️ <b>هشدار کمبود انبار اکسپرس و تشکیل صف!</b>\n\n👤 کاربر: {first_name} ({username})\n📦 سرویس: <b>{plan['name']}</b>\n📥 کاربر وارد صف انتظار شد.", parse_mode="HTML")
            except: pass

async def my_subscriptions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if is_user_blacklisted(query.from_user.id) or not await check_joined_channels(query.from_user.id, context): return
    await query.answer()
    page = int(query.data.split("_")[-1])
    orders = database.get_user_orders(query.from_user.id)
    if not orders:
        await query.edit_message_text(text="📋 <b>شما هنوز هیچ اشتراکی خریداری نکرده‌اید.</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_to_main")]]), parse_mode="HTML")
        return
    ITEMS_PER_PAGE = 10
    total_pages = (len(orders) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    start_idx = page * ITEMS_PER_PAGE
    page_items = orders[start_idx:start_idx + ITEMS_PER_PAGE]
    keyboard = []
    for idx, order in enumerate(page_items):
        global_idx = start_idx + idx
        sub_name = order.get('subscription_name', '') or f"#{order['id']}"
        keyboard.append([InlineKeyboardButton(f"📋 {sub_name} ({order.get('plan_name', 'نامشخص')})", callback_data=f"view_sub_{global_idx}_{page}")])
    nav_row = []
    if page > 0: nav_row.append(InlineKeyboardButton("◀️ قبل", callback_data=f"my_subs_page_{page - 1}"))
    if page < total_pages - 1: nav_row.append(InlineKeyboardButton("بعد ▶️", callback_data=f"my_subs_page_{page + 1}"))
    if nav_row: keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_to_main")])
    await query.edit_message_text(text=f"📋 <b>لیست اشتراک‌ها (صفحه {page + 1} از {total_pages})</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def view_subscription_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if is_user_blacklisted(query.from_user.id): return
    await query.answer()
    # فرمت: view_sub_{global_index}_{page}
    parts = query.data.split("_", 3)  # ["view", "sub", "{index}", "{page}"]
    if len(parts) < 4: return
    try:
        global_idx = int(parts[2])
        page = int(parts[3])
    except ValueError: return

    orders = database.get_user_orders(query.from_user.id)
    if global_idx < 0 or global_idx >= len(orders): return
    order = orders[global_idx]

    content = order.get('content', '')
    sub_name = order.get('subscription_name', '') or f"#{order['id']}"
    plan_name = order.get('plan_name', 'نامشخص')
    amount = order.get('amount', 0)
    date = order.get('date', 'نامشخص')

    # ساخت هدر با اطلاعات جدید
    header = (
        f"📄 <b>جزئیات اشتراک</b>\n\n"
        f"🆔 <b>شناسه سفارش:</b> <code>{order['id']}</code>\n"
        f"📛 <b>نام اشتراک:</b> <code>{sub_name}</code>\n"
        f"📦 <b>نوع پلن:</b> {plan_name}\n"
        f"💰 <b>مبلغ:</b> <code>{amount:,}</code> تومان\n"
        f"📅 <b>تاریخ خرید:</b> <code>{date}</code>\n\n"
        f"─────────────────────\n\n"
    )

    if "://" in content:
        lines = content.split('\n')
        link_lines = [l.strip() for l in lines if "://" in l]
        other_lines = [l for l in lines if "://" not in l and l.strip()]
        copyable_link = link_lines[0] if link_lines else ""
        text = header + f"🔗 <b>لینک اتصال (قابل کپی):</b>\n<code>{copyable_link}</code>"
        if other_lines:
            text = header + '\n'.join(other_lines) + f"\n\n🔗 <b>لینک اتصال (قابل کپی):</b>\n<code>{copyable_link}</code>"
    elif "یوزرنیم" in content or "پسورد" in content or "Username" in content or "Password" in content:
        text = header + f"🔐 <b>اطلاعات اکانت:</b>\n\n{content}"
    else:
        text = header + content

    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 لیست اشتراک‌ها", callback_data=f"my_subs_page_{page}")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
    ]), parse_mode="HTML")

async def wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if is_user_blacklisted(query.from_user.id) or not await check_joined_channels(query.from_user.id, context): return -1
    await query.answer()
    balance = database.get_user_balance(query.from_user.id)
    text = (
        "💳 <b>مدیریت کیف پول</b>\n\n"
        f"💵 موجودی فعلی: <code>{balance:,}</code> تومان"
    )
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ افزایش موجودی", callback_data="charge_wallet")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_to_main")]
    ]), parse_mode="HTML")
    return -1

async def request_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if is_user_blacklisted(query.from_user.id): return ConversationHandler.END
    await query.answer()
    text = (
        "💰 <b>شارژ کیف پول</b>\n\n"
        "✍️ مبلغ شارژ مورد نظر را به تومان و به صورت عددی ارسال کنید:\n\n"
        "🔹 حداقل: <code>150,000</code> تومان\n"
        "🔹 حداکثر: <code>10,000,000</code> تومان"
    )
    await query.edit_message_text(text=text, reply_markup=CANCEL_KEYBOARD, parse_mode="HTML")
    return GET_AMOUNT
async def process_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))
    if not user_input.isdigit() or not (150000 <= int(user_input) <= 10000000):
        await update.message.reply_text("❌ <b>مبلغ نامعتبر!</b>\n\nمبلغ باید بین <code>150,000</code> تا <code>10,000,000</code> تومان باشد.\nدوباره وارد کنید:", reply_markup=CANCEL_KEYBOARD, parse_mode="HTML")
        return GET_AMOUNT
    
    context.user_data["charge_amount"] = int(user_input)
    chosen_card = random.choice(CARD_NUMBERS)
    context.user_data["target_owner"] = chosen_card["owner"]
    
    # متن جدید با استفاده از تگ‌های HTML
    text = (
        f"✅ <b>مبلغ: {int(user_input):,} تومان</b>\n\n"
        f"💳 <b>کارت به کارت:</b>\n<code>{chosen_card['card']}</code>\n"
        f"🏦 به نام: {chosen_card['owner']}\n\n"
        "👇 پس از واریز دکمه زیر را بزنید:"
    )
    
    await update.message.reply_text(
        text=text, 
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📸 ارسال تصویر رسید", callback_data="send_receipt")],
            [InlineKeyboardButton("❌ انصراف", callback_data="back_to_main")]
        ]), 
        parse_mode="HTML" # اینجا تغییر کرد
    )
    return GET_RECEIPT

async def request_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("📸 <b>لطفاً عکس فیش واریزی خود را ارسال کنید:</b>", reply_markup=CANCEL_KEYBOARD, parse_mode="HTML")
    return GET_RECEIPT

async def process_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    amount = context.user_data.get("charge_amount", 0)
    target_owner = context.user_data.get("target_owner", "نامشخص")
    await update.message.reply_text("⏳ <b>رسید دریافت شد.</b>\nفیش واریزی شما برای بررسی به مدیریت ارسال شد. لطفاً منتظر بمانید.", parse_mode="HTML")
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=f"🔔 <b>درخواست شارژ</b>\n\n👤 کاربر: {user.first_name}\n🆔 آیدی: <code>{user.id}</code>\n💰 مبلغ: <code>{amount:,}</code> تومان\n💳 حساب: {target_owner}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ تایید", callback_data=f"verify_yes_{user.id}_{amount}"), InlineKeyboardButton("❌ رد", callback_data=f"verify_no_{user.id}")]]) , parse_mode="HTML")
    return await cancel_and_main(update, context)

async def handle_admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("❌ شما اجازه این عملیات را ندارید.", show_alert=True)
        return
    await query.answer()
    data = query.data.split("_")
    action, user_id = data[1], int(data[2])
    if action == "yes":
        amount = int(data[3])
        database.update_user_balance(user_id, amount) 
        await query.edit_message_caption(caption=query.message.caption + f"\n\n🟢 تایید و شارژ شد.")
        try: await context.bot.send_message(chat_id=user_id, text=f"🎉 <b>رسید تایید شد!</b>\nمبلغ <code>{amount:,}</code> تومان به حساب شما اضافه شد.", parse_mode="HTML")
        except: pass
    elif action == "no": 
        await query.edit_message_caption(caption=query.message.caption + "\n\n🔴 رد شد.")

async def cancel_and_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query: await update.callback_query.answer()
    context.user_data.clear()
    await show_main_menu(update, context)
    return ConversationHandler.END

# =====================================================================
# 🆘 سیستم پشتیبانی (Support System)
# =====================================================================

async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if is_user_blacklisted(query.from_user.id):
        await query.answer("❌ شما مسدود شده‌اید.")
        return -1
    if not await check_joined_channels(query.from_user.id, context):
        return -1
    await query.answer()
    text = (
        "🆘 <b>پشتیبانی آنلاین</b>\n\n"
        "✍️ پیام خود را بنویسید و ارسال کنید.\n"
        "کارشناسان ما در اسرع وقت به شما پاسخ خواهند داد.\n\n"
        "🔹 سوالات مربوط به خرید، شارژ حساب، مشکلات اتصال و ... را می‌توانید مطرح کنید.\n\n"
        "💡 <b>توجه:</b> اگر امکان ارسال پیام در ربات را ندارید یا ترجیح می‌دهید به صورت مستقیم با پشتیبانی صحبت کنید، می‌توانید به آیدی زیر پیام دهید:\n\n"
        "📬 @vpn_mall_admin"
    )
    await query.edit_message_text(text=text, reply_markup=CANCEL_KEYBOARD, parse_mode="HTML")
    return SUPPORT_MESSAGE

async def support_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    user_text = update.message.text
    user_id = user.id
    user_name = html.escape(user.first_name)
    username = html.escape(f"@{user.username}" if user.username else "بدون یوزرنیم")

    # ذخیره آیدی کاربر و آخرین پیام در دیتابیس برای ریپلای ادمین
    database.save_system_data(f"support_user_{user_id}", {
        "user_id": user_id,
        "user_name": user_name,
        "username": username,
        "last_message": user_text,
        "message_id": update.message.message_id
    })
    # ذخیره آخرین کاربر پشتیبانی جهت ریپلای سریع
    database.save_system_data("last_support_user_id", user_id)

    # ارسال پیام کاربر به ادمین
    admin_text = (
        "🆘 <b>پیام پشتیبانی جدید</b>\n\n"
        f"👤 کاربر: {user_name} ({username})\n"
        f"🆔 آیدی: <code>{user_id}</code>\n\n"
        f"💬 <b>پیام:</b>\n{html.escape(user_text)}\n\n"
        "─ ─ ─ ─ ─ ─ ─ ─ ─\n"
        "💡 برای پاسخ، روی این پیام ریپلای بزنید."
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="HTML")

    # اطلاع به کاربر
    await update.message.reply_text(
        "✅ <b>پیام شما با موفقیت ارسال شد.</b>\n\n"
        "کارشناسان ما در اسرع وقت به شما پاسخ خواهند داد.\n"
        "لطفاً صبور باشید. 🙏",
        reply_markup=CANCEL_KEYBOARD,
        parse_mode="HTML"
    )
    return SUPPORT_MESSAGE

# 🎯 هندلر ریپلای ادمین روی پشتیبانی
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # فقط ادمین میتونه ریپلای بزنه
    if not is_admin(update.effective_user.id):
        return

    # چک کن آیا پیام ریپلای هست
    if not update.message.reply_to_message:
        return

    reply_text = update.message.text
    replied_message = update.message.reply_to_message

    # آیا پیام ریپلای شده از پیام‌های پشتیبانی است؟
    # بررسی کن که پیام اصلی از ربات بوده و مربوط به پشتیبانی هست
    support_user_id = None
    if replied_message.from_user and replied_message.from_user.is_bot:
        # پیام از ربات بوده، آیدی کاربر رو از دیتابیس بگیر
        last_user = database.load_system_data("last_support_user_id", None)
        if last_user:
            user_data = database.load_system_data(f"support_user_{last_user}", None)
            if user_data:
                support_user_id = user_data.get("user_id")
    else:
        # پیام مستقیم کاربر بوده
        support_user_id = replied_message.from_user.id if replied_message.from_user else None

    if not support_user_id:
        await update.message.reply_text(
            "⚠️ <b>نمی‌توان پاسخ را ارسال کرد.</b>\n\n"
            "لطفاً روی پیام پشتیبانی کاربر ریپلای بزنید (از بخش پشتیبانی).",
            parse_mode="HTML"
        )
        return

    # ارسال پاسخ به کاربر
    try:
        user_data = database.load_system_data(f"support_user_{support_user_id}", {})
        user_name = user_data.get("user_name", "کاربر")

        await context.bot.send_message(
            chat_id=support_user_id,
            text=(
                "💬 <b>پاسخ پشتیبانی</b>\n\n"
                f"👤 کاربر گرامی {user_name}، پیام شما دریافت شد.\n\n"
                f"📝 پاسخ:\n{html.escape(reply_text)}"
            ),
            parse_mode="HTML"
        )

        await update.message.reply_text(
            "✅ <b>پاسخ با موفقیت ارسال شد.</b>\n\n"
            f"📬 پیام شما به کاربر <code>{support_user_id}</code> ارسال شد.",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>خطا در ارسال پاسخ!</b>\n\n"
            f"کاربر پیدا نشد یا مشکلی رخ داده است.\n"
            f"Error: {e}",
            parse_mode="HTML"
        )

# 📚 بخش آموزش‌ها (Tutorials)
async def tutorials_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if is_user_blacklisted(query.from_user.id) or not await check_joined_channels(query.from_user.id, context): return
    await query.answer()
    text = "📚 <b>بخش آموزش‌ها</b>\n\nلطفاً سیستم‌عامل خود را انتخاب کنید:"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 اندروید", callback_data="tutorials_android")],
        [InlineKeyboardButton("🍎 آیفون (iOS)", callback_data="tutorials_ios")],
        [InlineKeyboardButton("💻 ویندوز", callback_data="tutorials_windows")],
        [InlineKeyboardButton("🍏 مک (macOS)", callback_data="tutorials_macos")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
    ])
    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")

async def tutorials_android_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if is_user_blacklisted(query.from_user.id) or not await check_joined_channels(query.from_user.id, context): return
    await query.answer()
    text = (
        "🤖 <b>آموزش نصب و اتصال در اندروید</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📱 <b>۱. دانلود اپلیکیشن V2rayNG</b>\n\n"
        "🔹 از گوگل پلی یا سایت رسمی GitHub اپلیکیشن <b>V2rayNG</b> را دانلود و نصب کنید.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📱 <b>۲. اضافه کردن کانفیگ</b>\n\n"
        "🔹 اپ را باز کنید و روی آیکون <b>➕</b> بزنید.\n"
        "🔹 گزینه <b>Import config from clipboard</b> را انتخاب کنید.\n"
        "🔹 لینک اتصال که از ربات دریافت کردید را کپی و وارد کنید.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📱 <b>۳. اتصال</b>\n\n"
        "🔹 کانفیگ اضافه شده را انتخاب کنید.\n"
        "🔹 روی دکمه <b>▶️ Connect</b> (یا آیکون V) بزنید.\n"
        "🔹 در صورت درخواست دسترسی VPN، تایید کنید.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 <b>نکته:</b> اگر اتصال برقرار نشد، از گزینه‌های مختلف پروتکل (Auto / System Proxy) استفاده کنید.\n\n"
        "🆘 در صورت نیاز به راهنمایی بیشتر با پشتیبانی تماس بگیرید."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت", callback_data="tutorials")]
    ])
    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")

async def tutorials_ios_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if is_user_blacklisted(query.from_user.id) or not await check_joined_channels(query.from_user.id, context): return
    await query.answer()
    text = (
        "🍎 <b>آموزش نصب و اتصال در آیفون (iOS)</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📱 <b>۱. دانلود اپلیکیشن</b>\n\n"
        "🔹 اپلیکیشن <b>V2Box</b> یا <b>Hiddify</b> را از اپ‌استور دانلود و نصب کنید.\n"
        "🔹 (در صورت نبود اپ در اپ‌استور ایران، از اکانت اپل آمریکا استفاده کنید)\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📱 <b>۲. اضافه کردن کانفیگ</b>\n\n"
        "🔹 اپ را باز کنید.\n"
        "🔹 روی آیکون <b>➕</b> بزنید.\n"
        "🔹 گزینه <b>Add from Clipboard</b> را بزنید.\n"
        "🔹 لینک اتصال که از ربات دریافت کردید را از قبل کپی کرده و وارد کنید.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📱 <b>۳. اتصال</b>\n\n"
        "🔹 کانفیگ را انتخاب کنید.\n"
        "🔹 روی دکمه <b>Connect</b> بزنید.\n"
        "🔹 VPN Profile را در تنظیمات تایید و فعال کنید.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 <b>نکته:</b> برای بهترین سرعت، پروتکل <b>Auto</b> را انتخاب کنید.\n\n"
        "🆘 در صورت نیاز به راهنمایی بیشتر با پشتیبانی تماس بگیرید."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت", callback_data="tutorials")]
    ])
    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")

async def tutorials_windows_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if is_user_blacklisted(query.from_user.id) or not await check_joined_channels(query.from_user.id, context): return
    await query.answer()
    text = (
        "💻 <b>آموزش نصب و اتصال در ویندوز</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🖥 <b>۱. دانلود نرم‌افزار</b>\n\n"
        "🔹 نرم‌افزار <b>V2rayN</b> را از سایت رسمی GitHub دانلود کنید.\n"
        "🔹 فایل zip را اکسترکت کنید و برنامه را اجرا کنید.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🖥 <b>۲. اضافه کردن کانفیگ</b>\n\n"
        "🔹 لینک اتصال که از ربات گرفتید را کپی کنید.\n"
        "🔹 روی آیکون کلیپ‌بورد در نوار وظیفه (System Tray) راست‌کلیک کنید.\n"
        "🔹 گزینه <b>Import subscription from clipboard</b> را بزنید.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🖥 <b>۳. اتصال</b>\n\n"
        "🔹 از لیست سرورها، یک سرور انتخاب کنید.\n"
        "🔹 روی آن راست‌کلیک و <b>Set as active server</b> را بزنید.\n"
        "🔹 مطمئن شوید <b>System Proxy</b> فعال است.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 <b>نکته:</b> حالت <b>Rule</b> را برای بهترین عملکرد انتخاب کنید.\n\n"
        "🆘 در صورت نیاز به راهنمایی بیشتر با پشتیبانی تماس بگیرید."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت", callback_data="tutorials")]
    ])
    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")

async def tutorials_macos_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if is_user_blacklisted(query.from_user.id) or not await check_joined_channels(query.from_user.id, context): return
    await query.answer()
    text = (
        "🍏 <b>آموزش نصب و اتصال در مک (macOS)</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🖥 <b>۱. دانلود نرم‌افزار</b>\n\n"
        "🔹 نرم‌افزار <b>V2rayU</b> یا <b>FoXray</b> را دانلود و نصب کنید.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🖥 <b>۲. اضافه کردن کانفیگ</b>\n\n"
        "🔹 لینک اتصال که از ربات گرفتید را کپی کنید.\n"
        "🔹 در اپ، روی <b>Subscribe</b> رفته و لینک را Paste کنید.\n"
        "🔹 یا از طریق <b>Import from clipboard</b> اضافه کنید.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🖥 <b>۳. اتصال</b>\n\n"
        "🔹 یک سرور از لیست انتخاب کنید.\n"
        "🔹 روی <b>Turn V2ray-Core On</b> بزنید.\n"
        "🔹 حالت <b>Global</b> یا <b>Rule</b> را فعال کنید.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 <b>نکته:</b> برای مرور سایت‌های ایرانی بدون VPN، حالت Rule بهترین گزینه است.\n\n"
        "🆘 در صورت نیاز به راهنمایی بیشتر با پشتیبانی تماس بگیرید."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت", callback_data="tutorials")]
    ])
    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")

async def admin_top_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش کاربران برتر برای ادمین"""
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("❌ دسترسی محدود", show_alert=True)
        return -1
    await query.answer()

    top_users = database.get_top_users(limit=15, sort_by="amount")

    if not top_users:
        text = "📊 <b>آمار کاربران برتر</b>\n\nهنوز سفارشی ثبت نشده است."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]])
        await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        return -1

    text = "📊 <b>۱۵ کاربر برتر (براساس مبلغ کل)</b>\n\n"
    for idx, user in enumerate(top_users, 1):
        user_id = user["user_id"]
        spent = user["total_spent"]
        count = user["purchase_count"]
        text += f"{idx}️⃣ <code>{user_id}</code> | <b>{spent:,}</b> تومان | {count} خرید\n"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="admin_search_user_reward")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
    ])
    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    return -1


async def admin_search_user_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ادمین می‌خواهد کاربر را جستجو کند برای دادن پاداش"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="🔍 <b>جستجوی کاربر</b>\n\nآیدی کاربری را که می‌خواهید پاداش بدهید وارد کنید:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin_back")]]),
        parse_mode="HTML"
    )
    context.user_data["admin_action"] = "search_user_reward"
    return ADMIN_GET_USER


async def admin_user_reward_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی پاداش‌دهی کاربر"""
    user_input = update.message.text.strip()
    if not user_input.isdigit():
        await update.message.reply_text("❌ آیدی نامعتبر است")
        return ADMIN_GET_USER

    target_user_id = int(user_input)
    user_data = database.get_user_data(target_user_id)
    if not user_data:
        await update.message.reply_text("❌ کاربر یافت نشد")
        return ADMIN_GET_USER

    stats = database.get_user_purchase_stats(target_user_id)
    context.user_data["reward_target_user"] = target_user_id

    text = (
        f"👤 <b>اطلاعات کاربر:</b>\n"
        f"🆔 آیدی: <code>{target_user_id}</code>\n"
        f"💵 موجودی: <code>{user_data['balance']:,}</code> تومان\n\n"
        f"📊 <b>آمار خرید:</b>\n"
        f"🛒 تعداد سفارش: <code>{stats['purchase_count']}</code>\n"
        f"💰 مجموع خرج: <code>{stats['total_spent']:,}</code> تومان\n\n"
        f"<b>پاداش دادن:</b>"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 شارژ حساب", callback_data="admin_reward_charge")],
        [InlineKeyboardButton("🔙 انصراف", callback_data="admin_back")]
    ])

    await update.message.reply_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    return -1


async def admin_reward_charge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ادمین مبلغ پاداش را وارد می‌کند"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="💰 <b>مبلغ پاداش (تومان):</b>\n\nمثال: 50000",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin_back")]]),
        parse_mode="HTML"
    )
    context.user_data["admin_action"] = "reward_amount"
    return ADMIN_GET_BALANCE_CHNG


# ─── منوی تاریخچه کاربران (برای کاربران عادی) ────────────────

async def user_history_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تاریخچه خریدهای کاربر"""
    query = update.callback_query
    user_id = query.from_user.id

    if is_user_blacklisted(user_id) or not await check_joined_channels(user_id, context):
        return

    await query.answer()

    orders = database.get_user_order_history(user_id, limit=10)
    stats = database.get_user_purchase_stats(user_id)

    if not orders:
        text = "📋 <b>تاریخچه خریدهای شما</b>\n\nهنوز هیچ سفارشی ثبت نشده است."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_to_main")]])
        await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        return

    text = (
        f"📋 <b>تاریخچه خریدهای شما</b>\n\n"
        f"🛒 <b>آمار:</b>\n"
        f"  تعداد کل سفارش: <code>{stats['purchase_count']}</code>\n"
        f"  مجموع خرج: <code>{stats['total_spent']:,}</code> تومان\n\n"
        f"<b>۱۰ سفارش اخیر:</b>\n\n"
    )

    for idx, order in enumerate(orders, 1):
        date = order['date'].split()[0] if order['date'] else "نامشخص"
        text += f"{idx}. {order['plan_name']} | {order['amount']:,} تومان | {date}\n"

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_to_main")]])
    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")


# 🔥 هندلر جامع مرکزی دکمه‌های شیشه‌ای برای حل مشکل هدایت دکمه‌ها
async def handle_main_menu_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query: return
    user_id = query.from_user.id
    if is_user_blacklisted(user_id):
        await query.answer("❌ شما مسدود شده‌اید.")
        return

    if query.data == "invite_friends":
        return await invite_friends_menu(update, context)
    elif query.data == "back_to_main":
        await query.answer()
        return await show_main_menu(update, context)
    elif query.data == "buy_subscription":
        return await buy_subscription_menu(update, context)
    elif query.data == "buy_v2ray":
        return await v2ray_menu(update, context)
    elif query.data == "buy_express":
        return await express_menu(update, context)
    elif query.data.startswith("order_"):
        return await process_order(update, context)
    elif query.data.startswith("my_subs_page_"):
        return await my_subscriptions_menu(update, context)
    elif query.data.startswith("view_sub_"):
        return await view_subscription_details(update, context)
    elif query.data == "wallet":
        return await wallet_menu(update, context)
    elif query.data == "check_membership":
        return await check_join_callback(update, context)
    elif query.data == "tutorials":
        return await tutorials_menu(update, context)
    elif query.data == "tutorials_android":
        return await tutorials_android_menu(update, context)
    elif query.data == "tutorials_windows":
        return await tutorials_windows_menu(update, context)
    elif query.data == "tutorials_macos":
        return await tutorials_macos_menu(update, context)
    elif query.data == "user_history":
        return await user_history_menu(update, context)
    elif query.data == "admin_top_users":
        return await admin_top_users(update, context)
    elif query.data == "admin_storage_manager":
        return await admin_storage_manager(update, context)
    elif query.data.startswith("manage_storage_"):
        return await admin_storage_select(update, context)
    elif query.data.startswith("view_storage_"):
        return await admin_view_storage_items(update, context)
    elif query.data.startswith("add_storage_item_"):
        return await admin_add_storage_item_start(update, context)
    elif query.data.startswith("remove_storage_item_"):
        return await admin_remove_storage_item_start(update, context)
    elif query.data.startswith("clear_storage_"):
        return await admin_clear_storage(update, context)
    elif query.data.startswith("confirm_clear_"):
        return await admin_confirm_clear_storage(update, context)